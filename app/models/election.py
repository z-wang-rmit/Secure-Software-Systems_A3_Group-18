from app import db


class Division(db.Model):
    """An electoral division, e.g. Melbourne (VIC)."""
    __tablename__ = 'divisions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    state = db.Column(db.String(3), nullable=False)


class Election(db.Model):
    """An election. Status moves one way: draft -> open -> closed -> counted."""
    __tablename__ = 'elections'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(10), nullable=False, default='draft')


class Candidate(db.Model):
    """A candidate standing in one division of one election."""
    __tablename__ = 'candidates'

    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    division_id = db.Column(db.Integer, db.ForeignKey('divisions.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    party = db.Column(db.String(200))
    ballot_order = db.Column(db.Integer, nullable=False)
    excluded = db.Column(db.Boolean, nullable=False, default=False)

    division = db.relationship('Division')

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'party': self.party,
                'ballot_order': self.ballot_order}
