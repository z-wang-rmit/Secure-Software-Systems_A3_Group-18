# Candidate administration by state delegates. Owner: WS-E (R19)
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from app import db
from app.models import Candidate, CandidateProposal, Division, Election
from app.utils.auth import current_user, role_required, recent_login_required, recent_api_authentication_required
from app.utils.audit import log_event
from app.utils.helpers import validate_required_fields

candidates_bp = Blueprint('candidates', __name__)

CANDIDATE_FIELDS = ['election_id', 'division_id', 'name', 'ballot_order']


def propose_candidate(data):
    """R19: a delegate only proposes a candidate. It goes on the ballot once a
    different delegate approves it (separation of duties, Week 6 lecture s44)."""
    proposal = CandidateProposal(election_id=int(data['election_id']), division_id=int(data['division_id']),
                                 name=str(data['name']), party=str(data.get('party', '')),
                                 ballot_order=int(data['ballot_order']), proposed_by=current_user().id)
    db.session.add(proposal)
    db.session.commit()
    log_event(current_user().id, 'candidate_proposed', f'proposal:{proposal.id}')
    return proposal


@candidates_bp.route('/delegate/candidates', methods=['GET', 'POST'])
@role_required('delegate')
@recent_login_required
def manage():
    if request.method == 'POST':
        is_valid, error_message = validate_required_fields(request.form, CANDIDATE_FIELDS)
        if not is_valid:
            flash(error_message, 'danger')
        else:
            propose_candidate(request.form)
            flash('Candidate proposed. Another delegate must approve it before it goes on the ballot.', 'success')
        return redirect(url_for('candidates.manage'))
    return render_template('candidates.html',
                           candidates=Candidate.query.order_by(Candidate.division_id,
                                                               Candidate.ballot_order).all(),
                           elections=Election.query.all(), divisions=Division.query.all())


# ---- REST API ----

@candidates_bp.route('/api/v1/candidates', methods=['POST'])
@role_required('delegate')
def api_add_candidate():
    """A delegate proposes a candidate (R19: another delegate must approve it)"""
    recent_api_authentication_required()
    try:
        # Validate required fields
        data = request.get_json(silent=True) or {}
        is_valid, error_message = validate_required_fields(data, CANDIDATE_FIELDS)
        if not is_valid:
            return jsonify({'error': error_message}), 400

        proposal = propose_candidate(data)
        return jsonify({'proposal_id': proposal.id, 'status': proposal.status}), 201

    except Exception as e:
        db.session.rollback()
        print(f'Adding candidate failed: {e}')
        return jsonify({'error': 'Adding candidate failed'}), 500
