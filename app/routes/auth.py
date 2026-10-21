# Login, logout and account registration. Owner: WS-A (R01-R04)
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_jwt_extended import create_access_token
from app import db
from app.models import User, Elector
from app.utils.auth import login_user, logout_user
from app.utils.audit import log_event
from app.utils.helpers import validate_required_fields, validate_password

auth_bp = Blueprint('auth', __name__)


def check_credentials(username, password):
    """Return the user if username and password are correct, else None"""
    # PLACEHOLDER (R01-R04): no MFA, no lockout, no rate limiting
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user
    return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Check the username and password
        username = request.form.get('username', '').strip()
        user = check_credentials(username, request.form.get('password', ''))
        if user is None:
            log_event(None, 'login_failed', f'username:{username}')
            flash('Invalid username or password', 'danger')
            return render_template('login.html'), 401
        # Start the session and record the login
        login_user(user)
        log_event(user.id, 'login_ok', f'user:{user.id}')
        return redirect(url_for('main.index'))
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
        password_valid, password_error = validate_password(
            request.form.get('password', '')
        )
        if not password_valid:
            flash(password_error, 'danger')
            return render_template('register.html'), 400
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
    """Check username and password and return a JWT token (as in the Week 8 sample)"""
    try:
        data = request.get_json(silent=True) or {}

        # Validate required fields
        is_valid, error_message = validate_required_fields(data, ['username', 'password'])
        if not is_valid:
            return jsonify({'error': error_message}), 400

        user = check_credentials(str(data['username']), str(data['password']))
        if user is None:
            log_event(None, 'login_failed', f"username:{data['username']}", {'via': 'api'})
            return jsonify({'error': 'Invalid username or password'}), 401

        # Create access token
        access_token = create_access_token(identity=str(user.id))
        log_event(user.id, 'login_ok', f'user:{user.id}', {'via': 'api'})
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token
        }), 200

    except Exception as e:
        # Log the real error on the server, but don't send it to the user (Week 5 lecture s40)
        print(f'Login failed: {e}')
        return jsonify({'error': 'Login failed'}), 500
