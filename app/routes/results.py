# Closing elections, counting votes and publishing results. Owner: WS-E (R18)
import hashlib
from flask import Blueprint, jsonify, render_template, redirect, url_for, flash
from app import db
from app.models import Ballot, Candidate, Division, Election, Result
from app.utils.auth import current_user, role_required, recent_login_required
from app.utils.audit import log_event
from app.utils.ballot_crypto import open_ballot
from app.utils.helpers import utcnow
from app.utils.signing import sign_results, verify_results

results_bp = Blueprint('results', __name__)


def find_tampered_ballots(election):
    """R18: ids of ballots whose sha256(sealed) no longer matches the receipt (W9 L s26)"""
    bad = []
    for ballot in Ballot.query.filter_by(election_id=election.id).all():
        if hashlib.sha256(ballot.sealed).hexdigest() != ballot.receipt:
            bad.append(ballot.id)
    return bad


def count_division(election, division):
    """Count one division and return the result payload"""
    # Ballots are checked with find_tampered_ballots() before this runs.
    # Counts first preferences only (a full preferential count is a stretch goal).
    # Start every candidate on 0 votes
    tally = {}
    names = {}
    for candidate in Candidate.query.filter_by(election_id=election.id, division_id=division.id):
        tally[candidate.name] = 0
        names[str(candidate.id)] = candidate.name

    # Give each ballot to the candidate numbered 1
    ballots = Ballot.query.filter_by(election_id=election.id, division_id=division.id).all()
    for ballot in ballots:
        prefs = open_ballot(ballot.sealed)
        for candidate_id, number in prefs.items():
            if number == 1:
                tally[names[candidate_id]] += 1

    # The candidate with the most first preferences
    elected = None
    for name, votes in tally.items():
        if votes > 0 and (elected is None or votes > tally[elected]):
            elected = name

    return {
        'election': election.name,
        'division': division.name,
        'ballots_total': len(ballots),
        'first_preferences': tally,
        'elected': elected,
        'counted_at': utcnow().isoformat(timespec='seconds'),
    }


@results_bp.route('/auditor/count')
@role_required('auditor')
def auditor_count():
    return render_template('auditor_count.html', elections=Election.query.all())


@results_bp.route('/auditor/elections/<int:election_id>/close', methods=['POST'])
@role_required('auditor')
@recent_login_required
def close(election_id):
    election = db.get_or_404(Election, election_id)
    if election.status != 'open':
        flash('Only an open election can be closed.', 'danger')
    else:
        election.status = 'closed'
        db.session.commit()
        log_event(current_user().id, 'election_closed', f'election:{election.id}')
    return redirect(url_for('results.auditor_count'))


@results_bp.route('/auditor/elections/<int:election_id>/count', methods=['POST'])
@role_required('auditor')
@recent_login_required
def count(election_id):
    election = db.get_or_404(Election, election_id)
    if election.status != 'closed':
        flash('Close the election before counting.', 'danger')
        return redirect(url_for('results.auditor_count'))
    # R18: refuse to count if any ballot was changed after it was cast
    bad_ballots = find_tampered_ballots(election)
    if bad_ballots:
        log_event(current_user().id, 'count_refused', f'election:{election.id}',
                  {'bad_ballots': bad_ballots})
        flash(f'Count refused: {len(bad_ballots)} ballot(s) failed the integrity check.', 'danger')
        return redirect(url_for('results.auditor_count'))
    # Count each division, sign the result and store it
    for division in Division.query.all():
        payload = count_division(election, division)
        db.session.add(Result(election_id=election.id, division_id=division.id,
                              payload=payload, signature=sign_results(payload)))
    election.status = 'counted'
    db.session.commit()
    log_event(current_user().id, 'election_counted', f'election:{election.id}')
    return redirect(url_for('results.view', election_id=election.id))


@results_bp.route('/results/<int:election_id>')
def view(election_id):
    election = db.get_or_404(Election, election_id)
    return render_template('results.html', election=election,
                           results=Result.query.filter_by(election_id=election.id).all())


# ---- REST API (public, so other systems can fetch and check the results) ----

@results_bp.route('/api/v1/results/<int:election_id>', methods=['GET'])
def api_results(election_id):
    """Published results, so other systems can fetch them"""
    try:
        output = []
        for result in Result.query.filter_by(election_id=election_id).all():
            output.append({'payload': result.payload, 'signature': result.signature})
        return jsonify(output), 200

    except Exception as e:
        print(f'Failed to get results: {e}')
        return jsonify({'error': 'Failed to get results'}), 500


@results_bp.route('/api/v1/results/<int:election_id>/verify', methods=['GET'])
def api_verify(election_id):
    """Check the signatures on the published results"""
    try:
        results = Result.query.filter_by(election_id=election_id).all()
        if not results:
            return jsonify({'error': 'No results'}), 404

        valid = True
        for result in results:
            if not verify_results(result.payload, result.signature):
                valid = False
        return jsonify({'valid': valid}), 200

    except Exception as e:
        print(f'Verifying results failed: {e}')
        return jsonify({'error': 'Verifying results failed'}), 500
