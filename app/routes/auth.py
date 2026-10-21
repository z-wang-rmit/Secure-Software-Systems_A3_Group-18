# Login, logout and account registration. Owner: WS-A (R01-R04)
from datetime import timedelta
import io
import base64
import pyotp
import qrcode
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session, current_app
from app.models import MFAEnrollment
from app.utils.helpers import utcnow
from flask_jwt_extended import create_access_token
from app import db
from app.models import User, Elector
from app.utils.auth import login_user, logout_user
from app.utils.audit import log_event
from app.utils.helpers import validate_required_fields

auth_bp = Blueprint('auth', __name__)
def make_qr_data_uri(otpauth_uri):
    """Create a QR code as an in-memory PNG data URI."""
    image = qrcode.make(otpauth_uri)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def check_credentials(username, password):
    """Return the user if username and password are correct, else None"""
    # PLACEHOLDER (R01-R04): no MFA, no lockout, no rate limiting
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user
    return None

@auth_bp.route('/mfa/setup', methods=['GET', 'POST'])
def mfa_setup():
    """Display an MFA QR code and activate MFA after code verification."""
    pending_user_id = session.get('mfa_pending_user_id')
    if pending_user_id is None:
        flash('Please log in with your password first.', 'warning')
        return redirect(url_for('auth.login'))

    user = db.session.get(User, pending_user_id)
    if user is None:
        session.clear()
        return redirect(url_for('auth.login'))

    enrollment = MFAEnrollment.query.filter_by(user_id=user.id).first()
    now = utcnow()

    if enrollment is None or enrollment.expires_at <= now:
        if enrollment is not None:
            db.session.delete(enrollment)

        secret = pyotp.random_base32()
        enrollment = MFAEnrollment(
            user_id=user.id,
            pending_secret=secret,
            expires_at=now + timedelta(minutes=10),
        )
        db.session.add(enrollment)
        db.session.commit()

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if not pyotp.TOTP(enrollment.pending_secret).verify(code, valid_window=1):
            log_event(user.id, 'mfa_setup_failed', f'user:{user.id}')
            flash('Invalid code. Please try again.', 'danger')
        else:
            user.totp_secret = enrollment.pending_secret
            db.session.delete(enrollment)
            db.session.commit()
            session.clear()
            log_event(user.id, 'mfa_setup_success', f'user:{user.id}')
            flash('MFA is enabled. Please log in again.', 'success')
            return redirect(url_for('auth.login'))
        uri = pyotp.TOTP(enrollment.pending_secret).provisioning_uri(
        name=user.username,
        issuer_name='Secure Voting',
    )
    return render_template(
        'mfa_setup.html',
        qr_data_uri=make_qr_data_uri(uri),
    )

@auth_bp.route('/mfa/verify', methods=['GET', 'POST'])
def mfa_verify():
    """Complete login only after verifying the authenticator code."""
    pending_user_id = session.get('mfa_pending_user_id')
    pending_at = session.get('mfa_pending_at')

    if pending_user_id is None or pending_at is None:
        session.clear()
        flash('Please log in with your username and password first.', 'warning')
        return redirect(url_for('auth.login'))

    # Expire the pending login after five minutes.
    try:
        started_at = int(pending_at)
    except (TypeError, ValueError):
        session.clear()
        return redirect(url_for('auth.login'))

    if utcnow().timestamp() - started_at > 300:
        session.clear()
        flash('Login verification expired. Please log in again.', 'warning')
        return redirect(url_for('auth.login'))

    user = db.session.get(User, pending_user_id)
    if user is None or not user.totp_secret:
        session.clear()
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()

        if len(code) != 6 or not code.isdigit() or not pyotp.TOTP(
            user.totp_secret
        ).verify(code, valid_window=1):
            log_event(user.id, 'mfa_login_failed', f'user:{user.id}')
            flash('Invalid authenticator code. Please try again.', 'danger')
            return render_template('mfa_verify.html'), 401

        # Establish the authenticated session only after MFA succeeds.
        login_user(user)
        log_event(user.id, 'login_ok', f'user:{user.id}', {'via': 'web_mfa'})
        return redirect(url_for('main.index'))

    return render_template('mfa_verify.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = check_credentials(username, password)

        if user is None:
            log_event(None, 'login_failed', f'username:{username}')
            flash('Invalid username or password', 'danger')
            return render_template('login.html'), 401

        # Password is valid, but the user is not fully authenticated yet.
        session.clear()
        session['mfa_pending_user_id'] = user.id
        session['mfa_pending_at'] = int(utcnow().timestamp())

        # First-time users must enrol and verify MFA.
        if not user.totp_secret:
            return redirect(url_for('auth.mfa_setup'))

        # Existing users must verify their authenticator code.
        return redirect(url_for('auth.mfa_verify'))

    return render_template('login.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """A citizen who is already on the roll creates an online account."""
    if request.method == 'POST':
        # Validate required fields
        is_valid, error_message = validate_required_fields(
            request.form, ['enrolment_no', 'username', 'password'])
        username = request.form.get('username', '').strip()
        elector = Elector.query.filter_by(enrolment_no=request.form.get('enrolment_no', '').strip()).first()
        if (not is_valid or elector is None or elector.user_id is not None
                or User.query.filter_by(username=username).first()):
            flash('Registration failed. Check your details or contact the AEC.', 'danger')
            return render_template('register.html'), 400

        # Create the account and link it to the roll entry
        user = User(username=username, role='voter')
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.flush()
        elector.user_id = user.id
        db.session.commit()
        log_event(user.id, 'voter_registered', f'user:{user.id}')
        flash('Account created. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')


# ---- REST API ----

@auth_bp.route('/api/v1/auth/login', methods=['POST'])
def api_login():
    """Issue a JWT only after password and MFA verification."""
    try:
        data = request.get_json(silent=True) or {}

        is_valid, error_message = validate_required_fields(
            data, ['username', 'password', 'code']
        )
        if not is_valid:
            return jsonify({'error': error_message}), 400

        user = check_credentials(
            str(data['username']), str(data['password'])
        )
        if user is None:
            log_event(
                None, 'login_failed',
                f"username:{data['username']}", {'via': 'api'}
            )
            return jsonify({'error': 'Invalid credentials'}), 401

        # API login requires MFA to have been enrolled through the web flow.
        if not user.totp_secret:
            return jsonify({
                'error': 'MFA setup is required before API login'
            }), 403

        code = str(data['code']).strip()
        if (
            len(code) != 6
            or not code.isdigit()
            or not pyotp.TOTP(user.totp_secret).verify(
                code, valid_window=1
            )
        ):
            log_event(
                user.id, 'mfa_login_failed',
                f'user:{user.id}', {'via': 'api'}
            )
            return jsonify({'error': 'Invalid credentials'}), 401

        # Issue a token only after both factors are verified.
        access_token = create_access_token(identity=str(user.id))
        log_event(
            user.id, 'login_ok',
            f'user:{user.id}', {'via': 'api_mfa'}
        )

        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token
        }), 200

    except Exception:
        # Keep internal exception details out of the API response.
        current_app.logger.exception('API login failed')
        return jsonify({'error': 'Login failed'}), 500
