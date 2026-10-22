# Audit logging (R17)
# Secure Logger pattern (Week 5 lecture s22-24): every event goes through log_event(),
# and protected data is removed before anything is saved.
# Never log passwords, ballot choices, or anything linking a voter to a ballot.
from sqlalchemy import text
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


# ---- R17: the database refuses edits and deletes (Week 7 lecture s17-18, Week 7 lab s5-6) ----
# Triggers run inside the database, so even someone with direct SQL access can't
# quietly change the log through these statements.
MYSQL_TRIGGERS = [
    """CREATE TRIGGER IF NOT EXISTS audit_log_no_update BEFORE UPDATE ON audit_log
       FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_log is append-only'""",
    """CREATE TRIGGER IF NOT EXISTS audit_log_no_delete BEFORE DELETE ON audit_log
       FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_log is append-only'""",
]

# SQLite (local runs and the tests) supports triggers too, with a different syntax
SQLITE_TRIGGERS = [
    """CREATE TRIGGER IF NOT EXISTS audit_log_no_update BEFORE UPDATE ON audit_log
       BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS audit_log_no_delete BEFORE DELETE ON audit_log
       BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END""",
]


def count_audit_triggers():
    """How many triggers audit_log has right now"""
    if db.engine.dialect.name == 'mysql':
        sql = """SELECT COUNT(*) FROM information_schema.TRIGGERS
                 WHERE TRIGGER_SCHEMA = DATABASE() AND EVENT_OBJECT_TABLE = 'audit_log'"""
    else:
        sql = "SELECT COUNT(*) FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'audit_log'"
    return db.session.execute(text(sql)).scalar()


def protect_audit_log():
    """Create the triggers. Called once at start-up, right after db.create_all()."""
    # init_db.py creates them before gunicorn starts. The gunicorn workers then skip
    # this, because 3 workers running CREATE TRIGGER at once can clash in MySQL.
    if count_audit_triggers() >= 2:
        return
    if db.engine.dialect.name == 'mysql':
        statements = MYSQL_TRIGGERS
    else:
        statements = SQLITE_TRIGGERS
    for statement in statements:
        db.session.execute(text(statement))
    db.session.commit()
