from app import db
from app.utils.roll_crypto import decrypt_field


class Elector(db.Model):
    """A citizen on the electoral roll (R06, R08)"""
    # Personal details are stored encrypted: write with encrypt_field(), read with to_dict()
    __tablename__ = 'electors'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    enrolment_no = db.Column(db.String(20), unique=True, nullable=False)
    given_name = db.Column(db.LargeBinary, nullable=False)
    family_name = db.Column(db.LargeBinary, nullable=False)
    dob = db.Column(db.LargeBinary, nullable=False)
    address = db.Column(db.LargeBinary, nullable=False)
    division_id = db.Column(db.Integer, db.ForeignKey('divisions.id'), nullable=False)
    enrolled = db.Column(db.Boolean, nullable=False, default=True)

    division = db.relationship('Division')

    def to_dict(self):
        return {
            'enrolment_no': self.enrolment_no,
            'given_name': decrypt_field(self.given_name),
            'family_name': decrypt_field(self.family_name),
            'dob': decrypt_field(self.dob),
            'address': decrypt_field(self.address),
            'division': self.division.name,
            'state': self.division.state,
            'enrolled': self.enrolled,
            'has_account': self.user_id is not None,
        }
