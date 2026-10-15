# Candidate administration by state delegates. Owner: WS-E (R19)
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from app import db
from app.models import Candidate, Division, Election
from app.utils.auth import current_user, role_required
from app.utils.audit import log_event
from app.utils.helpers import validate_required_fields

candidates_bp = Blueprint('candidates', __name__)

CANDIDATE_FIELDS = ['election_id', 'division_id', 'name', 'ballot_order']


def add_candidate(data):
    """PLACEHOLDER (R19): one delegate changes candidates alone. R19 requires a second delegate's approval."""
    candidate = Candidate(election_id=int(data['election_id']), division_id=int(data['division_id']),
                          name=str(data['name']), party=str(data.get('party', '')),
                          ballot_order=int(data['ballot_order']))
    db.session.add(candidate)
    db.session.commit()
    log_event(current_user().id, 'candidate_added', f'candidate:{candidate.id}')
    return candidate


@candidates_bp.route('/delegate/candidates', methods=['GET', 'POST'])
@role_required('delegate')
def manage():
    if request.method == 'POST':
        is_valid, error_message = validate_required_fields(request.form, CANDIDATE_FIELDS)
        if not is_valid:
            flash(error_message, 'danger')
        else:
            add_candidate(request.form)
            flash('Candidate added.', 'success')
        return redirect(url_for('candidates.manage'))
    return render_template('candidates.html',
                           candidates=Candidate.query.order_by(Candidate.division_id,
                                                               Candidate.ballot_order).all(),
                           elections=Election.query.all(), divisions=Division.query.all())


# ---- REST API ----

@candidates_bp.route('/api/v1/candidates', methods=['POST'])
@role_required('delegate')
def api_add_candidate():
    """A delegate adds a candidate"""
    try:
        # Validate required fields
        data = request.get_json(silent=True) or {}
        is_valid, error_message = validate_required_fields(data, CANDIDATE_FIELDS)
        if not is_valid:
            return jsonify({'error': error_message}), 400

        candidate = add_candidate(data)
        return jsonify(candidate.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        print(f'Adding candidate failed: {e}')
        return jsonify({'error': 'Adding candidate failed'}), 500
