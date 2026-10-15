import secrets
import string
from datetime import datetime, timezone


def utcnow():
    """Current UTC time (stored without timezone info)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_enrolment_number():
    """Generate an enrolment number (adapted from the Week 8 generate_account_number)"""
    # Uses secrets, not random: the number is used to claim an account, so it must be
    # unguessable (Week 5 lecture s39)
    digits = ''
    for i in range(9):
        digits += secrets.choice(string.digits)
    return 'E' + digits


def validate_required_fields(data, required_fields):
    """Validate that all required fields are present in the data (from the Week 8 sample)"""
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)

    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    return True, None
