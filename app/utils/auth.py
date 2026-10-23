# Login sessions, JWT tokens and access control (other files call these: keep names and parameters)
# Pages use a session cookie (like the Week 6 sample); the REST API uses a JWT (like the Week 8 sample).
# PLACEHOLDER (R01-R04): password-only login, no MFA, no lockout.
# PLACEHOLDER (R05): a route is only protected if someone adds @role_required to it.
from functools import wraps
from flask import session, redirect, url_for, request, abort
from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt_identity,
    get_jwt,
)
from app import db
from app.models.user import User
from app.utils.helpers import utcnow

def login_user(user):
    """Start a session and record the successful password verification time."""
    session.clear()
    session['user_id'] = user.id
    session['password_verified_at'] = int(utcnow().timestamp())


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


def recent_login_required(f):
    """Require password verification within the last five minutes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = current_user()

        if user is None:
            if request.path.startswith('/api/'):
                abort(401)
            return redirect(url_for('auth.login'))

        # This re-authentication flow uses a web session.
        if request.path.startswith('/api/'):
            abort(403)

        # Viewing a page is not a critical action.
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return f(*args, **kwargs)
        verified_at = session.get('password_verified_at')
        try:
            verified_at = int(verified_at)
        except (TypeError, ValueError):
            verified_at = 0


        if utcnow().timestamp() - verified_at > 300:
            from urllib.parse import urlencode, urlparse

            # Return to the referring page so the user can retry the action.
            next_url = request.referrer or url_for('main.index')
            parsed = urlparse(next_url)

            # Prevent redirects to external URLs.
            if (
                parsed.scheme
                or parsed.netloc
                or not next_url.startswith('/')
                or next_url.startswith('//')
            ):
                next_url = url_for('main.index')

            return redirect(
                url_for('auth.reauthenticate')
                + '?' + urlencode({'next': next_url})
            )

        return f(*args, **kwargs)

    return decorated_function

def recent_api_authentication_required():
    """Require a fresh JWT issued within the last five minutes."""
    verify_jwt_in_request()
    claims = get_jwt()

    if not claims.get('fresh', False):
        abort(401, description='Recent authentication required')

    verified_at = claims.get('password_verified_at')

    try:
        verified_at = int(verified_at)
    except (TypeError, ValueError):
        abort(401, description='Recent authentication required')

    if utcnow().timestamp() - verified_at > 300:
        abort(401, description='Recent authentication required')

# R05: deny-by-default access control (idea from the Week 5 rbac.py sample)
# Pages anyone can open, even without logging in
PUBLIC_ENDPOINTS = {
    'static', 'main.index', 'main.health_check',
    'auth.login', 'auth.register', 'auth.api_login',
    'auth.mfa_setup',
    'results.view', 'results.api_results', 'results.api_verify', 'results.api_public_key',
    'ballot.bulletin', 'ballot.api_bulletin', 'auth.mfa_verify',
}

# Every role and the pages it may open. A page that is not listed here is blocked.
ROLE_PERMISSIONS = {
    'voter': {
        'auth.logout',
        'roll.enrolment', 'roll.api_get_enrolment', 'roll.api_update_enrolment',
        'ballot.ballot_list', 'ballot.ballot', 'ballot.api_candidates', 'ballot.api_cast_ballot',
    },

    'aec_staff': {
        'auth.logout', 'auth.reauthenticate', 'auth.api_reauthenticate',
        'roll.staff_electors', 'roll.api_register_elector'
    },
    'delegate': {
        'auth.logout', 'auth.reauthenticate', 'auth.api_reauthenticate',
        'candidates.manage', 'candidates.approve', 'candidates.api_add_candidate'
    },

    'auditor': {
        'auth.logout', 'auth.reauthenticate',
        'audit.audit_log', 'results.auditor_count',
        'results.close', 'results.count'
    },

}



def check_access():
    """Enforce login, staff MFA enrollment, and role-based access."""
    endpoint = request.endpoint

    if endpoint is None or endpoint in PUBLIC_ENDPOINTS:
        return None

    user = current_user()

    if user is None:
        if request.path.startswith('/api/'):
            abort(401)
        return redirect(url_for('auth.login'))

    # R02: staff roles must enrol in MFA before accessing protected pages.
    staff_roles = {'aec_staff', 'delegate', 'auditor'}

    if user.role in staff_roles and not user.totp_secret:
        if request.path.startswith('/api/'):
            abort(403)

        # Permit logout and MFA setup so users can complete enrollment.
        if endpoint not in {'auth.logout', 'auth.mfa_setup'}:
            return redirect(url_for('auth.mfa_setup'))

    if endpoint not in ROLE_PERMISSIONS.get(user.role, set()):
        abort(403)

    return None

def init_access_control(app):
    app.before_request(check_access)
