from flask import current_app
from app import db
from app.utils.helpers import utcnow
import bcrypt

class User(db.Model):
    """A login account. Roles: voter, aec_staff, delegate, auditor (R01-R04)"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='voter')
    state = db.Column(db.String(3))            # delegates: the state they administer
    created_at = db.Column(db.DateTime, default=utcnow)
    # Used later by R01/R02 (MFA) and R04 (lockout):
    totp_secret = db.Column(db.String(64))
    failed_logins = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime)

    def set_password(self, password):
        """Hash and set password (bcrypt, from the Week 8 sample). R03 adds a password policy."""
        # 12 rounds normally; tests set BCRYPT_ROUNDS low so they run fast
        salt = bcrypt.gensalt(rounds=current_app.config.get('BCRYPT_ROUNDS', 12))
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password):
        """Check if provided password matches hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self):
        return {'id': self.id, 'username': self.username, 'role': self.role}

    def __repr__(self):
        return f'<User {self.username}>'
