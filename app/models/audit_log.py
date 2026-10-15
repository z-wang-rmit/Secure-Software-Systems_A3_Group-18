from app import db
from app.utils.helpers import utcnow


class AuditLog(db.Model):
    """One security-relevant event. Owner: WS-E (R17)."""
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    ts = db.Column(db.DateTime, nullable=False, default=utcnow)
    actor_id = db.Column(db.Integer)           # None for anonymous events (e.g. ballot cast)
    action = db.Column(db.String(64), nullable=False)
    target = db.Column(db.String(128), nullable=False)
    detail = db.Column(db.JSON, nullable=False, default=dict)
