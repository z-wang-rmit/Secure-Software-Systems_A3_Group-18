# Web security settings applied to every request
# PLACEHOLDER (R15-R16): does nothing yet. Security headers (R15), CSRF and cookies (R16) go here.
# After editing the placeholder, i have added CSRF protection.

from flask import request, session
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta #for the 15min cookies

csrf = CSRFProtect()

def init_security(app):
    # this is so the session cookies are set
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

    @app.before_request
    def make_session_expire():
        session.permanent = True #this makes it so flask only applies lifetime to 'permanent' sessions. each request will refresh the cookies so this works as a 15min inactivity timeout

    # calling csrf.protect() so that /api/ routes can be skipped
    app.config['WTF_CSRF_CHECK_DEFAULT'] = False
    csrf.init_app(app)

    @app.before_request
    def csrf_check_pages():
        # the api authenticates with a JWT in the authorisation header, which a malicious site cant make the browser send so it doesnt need csrf tokens
        if request.path.startswith('/api/'):
            return
        if not app.config.get('WTF_CSRF_ENABLED', True):
            return
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            csrf.protect()