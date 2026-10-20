# Web security settings applied to every request
# PLACEHOLDER (R15-R16): does nothing yet. Security headers (R15), CSRF and cookies (R16) go here.
# After editing the placeholder, i have added CSRF protection for R16
# i then edit it for R15, adding the security headers and no caching of private pages in add_security_headers

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

    @app.after_request
    def add_security_headers(response): 
        response.headers['X-Content-Type-Options'] = 'nosniff'   # browser must trust our Content-Type
        response.headers['X-Frame-Options'] = 'DENY'             # page can't be shown in an iframe (clickjacking)

        logged_in = session.get('user_id') is not None or request.headers.get('Authorization') #checks if users are logged in
        if logged_in and not request.path.startswith('/static/'): # makes sure we're in a page and user is logged in)
            response.headers['Cache-Control'] = 'no-store' #sets cache-control to no-store
        return response