import re
import secrets
import string
from datetime import date, datetime, timezone


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


# ---- R08: server-side input validation (allow-lists, Week 5 L s31 and s36) ----
# HTML required/maxlength are only a convenience; these checks are what count.
NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z '\-]{0,49}$")   # letters, space, hyphen, apostrophe
ADDRESS_PATTERN = re.compile(r"^[A-Za-z0-9 ,.'/#\-]{1,200}$")
MIN_VOTING_AGE = 18


def validate_name(value, field='name'):
    if not isinstance(value, str) or not NAME_PATTERN.match(value.strip()):
        return False, f'{field} must be 1-50 letters (spaces, hyphens and apostrophes allowed)'
    return True, None


def validate_address(value):
    if not isinstance(value, str) or not ADDRESS_PATTERN.match(value.strip()):
        return False, 'address must be 1-200 characters: letters, numbers, spaces and , . \' / # -'
    return True, None


def validate_dob(value):
    """A real date in YYYY-MM-DD format, and the person is 18 or older"""
    try:
        born = date.fromisoformat(str(value))
    except ValueError:
        return False, 'dob must be a real date in YYYY-MM-DD format'
    today = date.today()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    if born > today or age > 130:
        return False, 'dob is not a realistic date of birth'
    if age < MIN_VOTING_AGE:
        return False, 'must be 18 or older to enrol'
    return True, None


def validate_division_id(value):
    from app import db
    from app.models import Division  # imported here to avoid a circular import
    try:
        division_id = int(value)
    except (TypeError, ValueError):
        return False, 'division_id must be a number'
    if division_id < 1 or db.session.get(Division, division_id) is None:
        return False, 'division_id does not exist'
    return True, None


def validate_elector(data):
    """Check every field of a new roll entry. Returns (True, None) or (False, message)."""
    is_valid, error = validate_required_fields(
        data, ['given_name', 'family_name', 'dob', 'address', 'division_id'])
    if not is_valid:
        return is_valid, error
    for check in (lambda: validate_name(data['given_name'], 'given_name'),
                  lambda: validate_name(data['family_name'], 'family_name'),
                  lambda: validate_dob(data['dob']),
                  lambda: validate_address(data['address']),
                  lambda: validate_division_id(data['division_id'])):
        is_valid, error = check()
        if not is_valid:
            return is_valid, error
    return True, None


def validate_preferences(prefs):
    """Ballot numbers must be exactly 1..N with no repeats (N = number of candidates)."""
    numbers = list(prefs.values())
    if not all(isinstance(n, int) and not isinstance(n, bool) for n in numbers):
        return False, 'Each preference must be a whole number'
    if sorted(numbers) != list(range(1, len(numbers) + 1)):
        return False, 'Number the candidates 1 to N, using each number once.'
    return True, None
