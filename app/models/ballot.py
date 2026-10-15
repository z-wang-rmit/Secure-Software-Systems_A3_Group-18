from app import db


class Participation(db.Model):
    """Records THAT an elector voted, never HOW (R09)"""
    # The primary key (election_id, elector_id) stops a second vote at the database level
    __tablename__ = 'participation'

    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), primary_key=True)
    elector_id = db.Column(db.Integer, db.ForeignKey('electors.id'), primary_key=True)
    voted_on = db.Column(db.Date, nullable=False)


class Ballot(db.Model):
    """A sealed ballot (R10-R12)"""
    # Deliberately NO voter or elector column: nothing links a ballot to a person (R10)
    __tablename__ = 'ballots'

    id = db.Column(db.String(36), primary_key=True)           # random UUID
    election_id = db.Column(db.Integer, nullable=False)
    division_id = db.Column(db.Integer, nullable=False)
    sealed = db.Column(db.LargeBinary, nullable=False)        # output of seal_ballot()
    receipt = db.Column(db.String(64), unique=True, nullable=False)  # SHA-256 of sealed
