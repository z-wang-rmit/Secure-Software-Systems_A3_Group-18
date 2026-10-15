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
