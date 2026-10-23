# Viewing the audit log. Owner: WS-E (R17)
from flask import Blueprint, render_template, request
from app.models import AuditLog
from app.utils.audit import log_event
from app.utils.auth import current_user, role_required

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/auditor/audit')
@role_required('auditor')
def audit_log():
    entries = AuditLog.query.order_by(AuditLog.id.desc()).limit(200).all()
    return render_template('audit_log.html', entries=entries)


@audit_bp.app_errorhandler(403)
def log_access_denied(error):
    """R17: every refused request is a security event (who tried, and which page)"""
    try:
        user = current_user()
    except Exception:
        user = None   # e.g. a broken token: still log it, just without an actor
    actor_id = None
    if user is not None:
        actor_id = user.id
    log_event(actor_id, 'access_denied', f'page:{request.path}', {'method': request.method})
    return error   # Flask shows its normal 403 page
