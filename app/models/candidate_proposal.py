from app import db
from app.utils.helpers import utcnow


class CandidateProposal(db.Model):
    """A new candidate waiting for a second delegate to approve it (R19)"""
    # A separate table, so existing databases get it from db.create_all() without a migration
    __tablename__ = 'candidate_proposals'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    division_id = db.Column(db.Integer, db.ForeignKey('divisions.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    party = db.Column(db.String(200))
    ballot_order = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')   # pending / approved
    proposed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=utcnow)

    division = db.relationship('Division')
