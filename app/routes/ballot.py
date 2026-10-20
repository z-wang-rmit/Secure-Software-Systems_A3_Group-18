# Casting votes. Owner: WS-C (R09-R12)
import hashlib
import uuid
from datetime import date
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from app import db
from sqlalchemy.exc import IntegrityError
from app.models import Elector, Election, Candidate, Participation, Ballot
from app.utils.auth import current_user,role_required 
from app.utils.helpers import validate_preferences
from app.utils.audit import log_event
from app.utils.ballot_crypto import seal_ballot

ballot_bp = Blueprint('ballot', __name__)


def candidates_for(election_id, division_id):
    """The candidates on the ballot for one division, in ballot order"""
    query = Candidate.query.filter_by(election_id=election_id, division_id=division_id, excluded=False)
    return query.order_by(Candidate.ballot_order).all()


def check_eligible(election):
    """Return (elector, None) if the logged-in voter can vote, or (None, error message)"""
    elector = Elector.query.filter_by(user_id=current_user().id).first()
    if elector is None or not elector.enrolled:
        return None, 'You are not enrolled to vote.'
    if election.status != 'open':
        return None, 'This election is not open.'
    already_voted = Participation.query.filter_by(election_id=election.id, elector_id=elector.id).first()
    if already_voted:
        return None, 'You have already voted in this election.'
    return elector, None


def cast_ballot(election, prefs):
    """Store the vote. Returns (receipt, None), or (None, error message)"""
    # R09: even if two requests pass check_eligible together, the DB primary key stops a second vote
    elector, error = check_eligible(election)
    if elector is None:
        return None, error

    # Every candidate on this voter's ballot must be numbered
    candidate_ids = set()
    for candidate in candidates_for(election.id, elector.division_id):
        candidate_ids.add(str(candidate.id))
    if set(prefs.keys()) != candidate_ids:
        return None, 'Please number every candidate.'
    is_valid, error = validate_preferences(prefs)   # R08: numbers 1..N, no repeats
    if not is_valid:
        return None, error

    # Seal the ballot and make the receipt (R18's integrity check relies on this hash)
    sealed = seal_ballot(prefs)
    receipt = hashlib.sha256(sealed).hexdigest()

    # Save WHO voted and WHAT was voted as two unconnected rows
    db.session.add(Participation(election_id=election.id, elector_id=elector.id,
                                 voted_on=date.today()))
    db.session.add(Ballot(id=str(uuid.uuid4()), election_id=election.id,
                          division_id=elector.division_id, sealed=sealed, receipt=receipt))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None, 'You have already voted in this election.'

    # No voter id in the audit entry: it must not link a voter to a ballot (R10)
    log_event(None, 'ballot_cast', f'election:{election.id}')
    return receipt, None


@ballot_bp.route('/ballot')
@role_required('voter')
def ballot_list():
    elections = Election.query.filter_by(status='open').all()
    return render_template('ballot_list.html', elections=elections)


@ballot_bp.route('/ballot/<int:election_id>', methods=['GET', 'POST'])
@role_required('voter')
def ballot(election_id):
    election = db.get_or_404(Election, election_id)
    elector, error = check_eligible(election)
    if elector is None:
        flash(error, 'danger')
        return redirect(url_for('ballot.ballot_list'))
    candidates = candidates_for(election.id, elector.division_id)

    if request.method == 'POST':
        # Read the number the voter typed next to each candidate
        prefs = {}
        for candidate in candidates:
            number = request.form.get(f'pref_{candidate.id}', type=int)
            if number:
                prefs[str(candidate.id)] = number

        receipt, error = cast_ballot(election, prefs)
        if error:
            flash(error, 'danger')
            return redirect(url_for('ballot.ballot', election_id=election.id))
        return render_template('receipt.html', election=election, receipt=receipt)

    return render_template('ballot.html', election=election, candidates=candidates,
                           division=elector.division)


# ---- REST API ----

@ballot_bp.route('/api/v1/elections/<int:election_id>/candidates', methods=['GET'])
@role_required('voter')
def api_candidates(election_id):
    """The candidates on the logged-in voter's ballot"""
    election = db.get_or_404(Election, election_id)
    try:
        elector, error = check_eligible(election)
        if elector is None:
            return jsonify({'error': error}), 403

        result = []
        for candidate in candidates_for(election.id, elector.division_id):
            result.append(candidate.to_dict())
        return jsonify(result), 200

    except Exception as e:
        print(f'Failed to get candidates: {type(e).__name__}')
        return jsonify({'error': 'Failed to get candidates'}), 500


@ballot_bp.route('/api/v1/ballots', methods=['POST'])
@role_required('voter')
def api_cast_ballot():
    """The logged-in voter casts their vote"""
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get('election_id'), int) or not isinstance(data.get('preferences'), dict):
        return jsonify({'error': 'election_id (number) and preferences (object) are required'}), 400
    election = db.get_or_404(Election, data['election_id'])

    try:
        # Preferences arrive as {"candidate id": number}
        prefs = {}
        for candidate_id, number in data['preferences'].items():
            if not isinstance(number, int):
                return jsonify({'error': 'Each preference must be a number'}), 400
            prefs[str(candidate_id)] = number

        receipt, error = cast_ballot(election, prefs)
        if error:
            return jsonify({'error': error}), 400
        return jsonify({'receipt': receipt}), 201

    except Exception as e:
        db.session.rollback()
        print(f'Voting failed: {type(e).__name__}')
        return jsonify({'error': 'Voting failed'}), 500