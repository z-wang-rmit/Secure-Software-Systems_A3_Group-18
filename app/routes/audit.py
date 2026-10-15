# Viewing the audit log. Owner: WS-E (R17)
from flask import Blueprint, render_template
from app.models import AuditLog
from app.utils.auth import role_required

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/auditor/audit')
@role_required('auditor')
def audit_log():
    entries = AuditLog.query.order_by(AuditLog.id.desc()).limit(200).all()
    return render_template('audit_log.html', entries=entries)
