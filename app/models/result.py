from app import db
from app.utils.helpers import utcnow


class Result(db.Model):
    """The published result for one division. Owner: WS-E (R18)."""
    __tablename__ = 'results'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    division_id = db.Column(db.Integer, db.ForeignKey('divisions.id'), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    signature = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    division = db.relationship('Division')
