# Audit logging (R17)
# Secure Logger pattern (Week 5 lecture s22-24): every event goes through log_event(),
# and protected data is removed before anything is saved.
# Never log passwords, ballot choices, or anything linking a voter to a ballot.
from app import db
from app.models.audit_log import AuditLog

# Keys that must never be stored in the detail of a log entry
PROTECTED_KEYS = ['password', 'new_password', 'code', 'totp', 'totp_secret',
                  'secret', 'token', 'access_token', 'prefs', 'preferences']

TARGET_MAX = 128   # same as the length of the target column


def clean_text(value, max_length):
    """Remove newlines (so nobody can fake a log line) and cut to max_length"""
    value = str(value).replace('\r', ' ').replace('\n', ' ')
    return value[:max_length]


def clean_detail(detail):
    """Copy of detail without protected keys"""
    cleaned = {}
    for key, value in detail.items():
        if key.lower() in PROTECTED_KEYS:
            cleaned[key] = '[removed]'
        else:
            cleaned[key] = value
    return cleaned


def log_event(actor_id, action, target, detail=None):
    """Record a security event, e.g. log_event(user.id, 'login_ok', f'user:{user.id}')"""
    entry = AuditLog(actor_id=actor_id,
                     action=action,
                     target=clean_text(target, TARGET_MAX),
                     detail=clean_detail(detail or {}))
    db.session.add(entry)
    db.session.commit()
