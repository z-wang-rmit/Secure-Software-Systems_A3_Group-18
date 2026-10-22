from app import db
from app.utils.helpers import utcnow


class MFAEnrollment(db.Model):
    """Temporary MFA enrollment; secret is not active until verified."""
    __tablename__ = 'mfa_enrollments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        unique=True,
    )
    pending_secret = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)