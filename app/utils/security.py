# Web security settings applied to every request
# PLACEHOLDER (R15-R16): does nothing yet. Security headers (R15), CSRF and cookies (R16) go here.
# After editing the placeholder, i have added CSRF protection.

from flask import request
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

def init_security(app):
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