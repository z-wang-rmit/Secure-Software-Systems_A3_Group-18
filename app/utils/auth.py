# Login sessions, JWT tokens and access control (other files call these: keep names and parameters)
# Pages use a session cookie (like the Week 6 sample); the REST API uses a JWT (like the Week 8 sample).
# PLACEHOLDER (R01-R04): password-only login, no MFA, no lockout.
# PLACEHOLDER (R05): a route is only protected if someone adds @role_required to it.
from functools import wraps
from flask import session, redirect, url_for, request, abort
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app import db
from app.models.user import User


def login_user(user):
    """Start a session for this user (the user's id is stored in the signed session cookie)"""
    session.clear()
    session['user_id'] = user.id


def logout_user():
    session.clear()


def current_user():
    """Return the logged-in User, or None"""
    if request.path.startswith('/api/'):
        # API: read the user id from the JWT in the "Authorization: Bearer ..." header
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    else:
        # Pages: read the user id from the session cookie
        user_id = session.get('user_id')
    if user_id is None:
        return None
    return db.session.get(User, int(user_id))


def login_required(f):
    """Decorator to require a logged-in user"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user() is None:
            if request.path.startswith('/api/'):
                abort(401)
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """Decorator to require one of the given roles, e.g. @role_required('auditor')"""
    # Three functions inside each other, because this decorator takes arguments:
    #   role_required('auditor')  -> saves the allowed roles and returns `decorator`
    #   decorator(f)              -> wraps the route function f and returns `decorated_function`
    #   decorated_function(...)   -> runs on every request: checks login, then the role
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user().role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# R05: deny-by-default access control (idea from the Week 5 rbac.py sample)
# Pages anyone can open, even without logging in
PUBLIC_ENDPOINTS = {
    'static', 'main.index', 'main.health_check',
    'auth.login', 'auth.register', 'auth.api_login',
    'auth.mfa_setup',
    'results.view', 'results.api_results', 'results.api_verify',
    'ballot.bulletin', 'ballot.api_bulletin', 'auth.mfa_verify',
}

# Every role and the pages it may open. A page that is not listed here is blocked.
ROLE_PERMISSIONS = {
    'voter': {
        'auth.logout',
        'roll.enrolment', 'roll.api_get_enrolment', 'roll.api_update_enrolment',
        'ballot.ballot_list', 'ballot.ballot', 'ballot.api_candidates', 'ballot.api_cast_ballot',
    },
    'aec_staff': {'auth.logout', 'roll.staff_electors', 'roll.api_register_elector'},
    'delegate': {'auth.logout', 'candidates.manage', 'candidates.api_add_candidate'},
    'auditor': {'auth.logout', 'audit.audit_log', 'results.auditor_count',
                'results.close', 'results.count'},
}


def check_access():
    """Runs before every request. Blocks anything not explicitly allowed."""
    endpoint = request.endpoint
    if endpoint is None or endpoint in PUBLIC_ENDPOINTS:
        return None  # unknown URL (Flask gives 404) or a public page
    user = current_user()
    if user is None:
        if request.path.startswith('/api/'):
            abort(401)
        return redirect(url_for('auth.login'))
    if endpoint not in ROLE_PERMISSIONS.get(user.role, set()):
        abort(403)
    return None


def init_access_control(app):
    app.before_request(check_access)

    