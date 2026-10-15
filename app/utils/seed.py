# Demo data, loaded when the database is empty and SEED_PASSWORD is set in .env
from app import db
from app.models import User, Elector, Division, Election, Candidate
from app.utils.helpers import generate_enrolment_number
from app.utils.roll_crypto import encrypt_field

CANDIDATES = {
    'Melbourne': [('A. Nguyen', 'Greens'), ('B. Smith', 'Labor'),
                  ('C. Brown', 'Liberal'), ('D. Wilson', 'Independent')],
    'Sydney': [('E. Taylor', 'Labor'), ('F. Martin', 'Liberal'),
               ('G. Lee', 'Greens'), ('H. Walker', 'Independent')],
}


def seed_if_empty(password):
    if User.query.first():
        return

    melbourne = Division(name='Melbourne', state='VIC')
    sydney = Division(name='Sydney', state='NSW')
    election = Election(name='2026 Federal Election - House of Representatives', status='open')
    db.session.add_all([melbourne, sydney, election])
    db.session.flush()   # gives the new rows their ids

    for division in (melbourne, sydney):
        for order, (name, party) in enumerate(CANDIDATES[division.name], start=1):
            db.session.add(Candidate(election_id=election.id, division_id=division.id,
                                     name=name, party=party, ballot_order=order))

    # One account per staff role
    for username, role, state in [('staff1', 'aec_staff', None),
                                  ('delegate1', 'delegate', 'VIC'), ('delegate2', 'delegate', 'VIC'),
                                  ('auditor1', 'auditor', None)]:
        user = User(username=username, role=role, state=state)
        user.set_password(password)
        db.session.add(user)

    # Five enrolled voters with online accounts: voter1-3 in Melbourne, voter4-5 in Sydney
    for i in range(1, 6):
        user = User(username=f'voter{i}', role='voter')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(Elector(
            user_id=user.id,
            enrolment_no=generate_enrolment_number(),
            given_name=encrypt_field(f'Voter{i}'),
            family_name=encrypt_field('Example'),
            dob=encrypt_field('1990-01-01'),
            address=encrypt_field(f'{i} Example St'),
            division_id=(melbourne if i <= 3 else sydney).id,
        ))

    db.session.commit()
