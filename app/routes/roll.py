# The electoral roll: enrolment and citizen registration. Owner: WS-B (R05, R06, R08, R14)
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from app import db
from app.models import Elector, Division
from app.utils.auth import current_user, role_required, recent_login_required, recent_api_authentication_required
from app.utils.audit import log_event
from app.utils.helpers import generate_enrolment_number, validate_address, validate_elector
from app.utils.roll_crypto import encrypt_field

roll_bp = Blueprint('roll', __name__)

ELECTOR_FIELDS = ['given_name', 'family_name', 'dob', 'address', 'division_id']


def my_elector():
    """The roll entry linked to the logged-in voter, or None."""
    return Elector.query.filter_by(user_id=current_user().id).first()


def register_elector(data):
    """Add a citizen to the roll. Callers must run validate_elector(data) first (R08)."""
    elector = Elector(
        enrolment_no=generate_enrolment_number(),
        given_name=encrypt_field(str(data['given_name'])),
        family_name=encrypt_field(str(data['family_name'])),
        dob=encrypt_field(str(data['dob'])),
        address=encrypt_field(str(data['address'])),
        division_id=int(data['division_id']),
    )
    db.session.add(elector)
    db.session.commit()
    log_event(current_user().id, 'elector_registered', f'elector:{elector.id}')
    return elector


@roll_bp.route('/enrolment', methods=['GET', 'POST'])
@role_required('voter')
def enrolment():
    """A voter checks their enrolment and updates their address."""
    elector = my_elector()
    if request.method == 'POST' and elector:
        # R08: validate on the server before saving (stored encrypted, R06)
        address = request.form.get('address', '')
        is_valid, error_message = validate_address(address)
        if not is_valid:
            flash(error_message, 'danger')
            return redirect(url_for('roll.enrolment'))
        elector.address = encrypt_field(address.strip())
        db.session.commit()
        log_event(current_user().id, 'address_updated', f'elector:{elector.id}')
        flash('Address updated.', 'success')
        return redirect(url_for('roll.enrolment'))
    return render_template('enrolment.html', elector=elector.to_dict() if elector else None)


@roll_bp.route('/staff/electors', methods=['GET', 'POST'])
@role_required('aec_staff')
@recent_login_required
def staff_electors():
    """AEC staff register citizens to vote."""
    if request.method == 'POST':
        is_valid, error_message = validate_elector(request.form)
        if not is_valid:
            flash(error_message, 'danger')
        else:
            elector = register_elector(request.form)
            flash(f'Registered. Enrolment number: {elector.enrolment_no}', 'success')
        return redirect(url_for('roll.staff_electors'))
    return render_template('staff_electors.html',
                           electors=[e.to_dict() for e in Elector.query.all()],
                           divisions=Division.query.all())


# ---- REST API ----

@roll_bp.route('/api/v1/enrolment', methods=['GET'])
@role_required('voter')
def api_get_enrolment():
    """The logged-in voter's enrolment details"""
    try:
        elector = my_elector()
        if elector is None:
            return jsonify({'enrolled': False}), 200
        return jsonify(elector.to_dict()), 200

    except Exception as e:
        print(f'Failed to get enrolment: {e}')
        return jsonify({'error': 'Failed to get enrolment'}), 500


@roll_bp.route('/api/v1/enrolment', methods=['PUT'])
@role_required('voter')
def api_update_enrolment():
    """The logged-in voter updates their address"""
    try:
        elector = my_elector()
        if elector is None:
            return jsonify({'error': 'Not enrolled'}), 404

        # Validate required fields
        data = request.get_json(silent=True) or {}
        is_valid, error_message = validate_address(data.get('address'))
        if not is_valid:
            return jsonify({'error': error_message}), 400

        elector.address = encrypt_field(data['address'].strip())
        db.session.commit()
        log_event(current_user().id, 'address_updated', f'elector:{elector.id}', {'via': 'api'})
        return jsonify({'message': 'Address updated'}), 200

    except Exception as e:
        db.session.rollback()
        print(f'Address update failed: {e}')
        return jsonify({'error': 'Address update failed'}), 500


@roll_bp.route('/api/v1/electors', methods=['POST'])
@role_required('aec_staff')
def api_register_elector():
    """AEC staff add a citizen to the roll"""
    recent_api_authentication_required()

    try:
        # Validate required fields
        data = request.get_json(silent=True) or {}
        is_valid, error_message = validate_elector(data)
        if not is_valid:
            return jsonify({'error': error_message}), 400

        elector = register_elector(data)
        return jsonify({'enrolment_no': elector.enrolment_no}), 201

    except Exception as e:
        db.session.rollback()
        print(f'Registration failed: {e}')
        return jsonify({'error': 'Registration failed'}), 500
