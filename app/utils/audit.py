# Audit logging
# PLACEHOLDER (R17): plain insert; old entries can still be edited. Keep the function name.
# Never log passwords, ballot choices, or anything linking a voter to a ballot.
from app import db
from app.models.audit_log import AuditLog


def log_event(actor_id, action, target, detail=None):
    """Record a security event, e.g. log_event(user.id, 'login_ok', f'user:{user.id}')"""
    db.session.add(AuditLog(actor_id=actor_id, action=action, target=target, detail=detail or {}))
    db.session.commit()
