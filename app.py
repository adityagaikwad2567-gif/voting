"""Digital Voter Services & Online Voting Portal
Academic Demonstration Project
Students: Aditya Gaikwad & Aditi Naik
BCA Second Year — Waterfall Model
"""

from app import create_app, csrf
from app.routes.auth import init_login_manager
from app.services.db_operations import (
    create_user, create_voter_profile, create_election, create_candidate,
    get_user_by_email, get_all_polling_stations
)
from werkzeug.security import generate_password_hash
import datetime

app = create_app()
init_login_manager(app)


def seed_demo_data():
    """Seed database with demo data if not already present."""
    from app.utils.database import query_db, execute_db
    
    # Check if admin exists
    admin = get_user_by_email('admin@demo.local')
    if admin:
        return  # Already seeded
    
    print("Seeding demo data...")
    
    # Create admin
    admin_pw = generate_password_hash('Admin@12345')
    execute_db(
        "INSERT INTO users (name, email, mobile, voter_id, password_hash, role, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        ('System Administrator', 'admin@demo.local', '9000000000', None, admin_pw, 'ADMIN', 'active')
    )
    
    # Create demo voters
    demo_voters = [
        ('Aditya Gaikwad', 'aditya@demo.local', '9100000001', 'DEMO100001'),
        ('Aditi Naik', 'aditi@demo.local', '9100000002', 'DEMO100002'),
        ('Rahul Sharma', 'rahul@demo.local', '9100000003', 'DEMO100003'),
        ('Priya Patil', 'priya@demo.local', '9100000004', 'DEMO100004'),
        ('Sneha Deshmukh', 'sneha@demo.local', '9100000005', 'DEMO100005'),
    ]
    
    voter_pw = generate_password_hash('Demo@12345')
    for name, email, mobile, vid in demo_voters:
        uid = execute_db(
            "INSERT INTO users (name, email, mobile, voter_id, password_hash, role, status) VALUES (%s, %s, %s, %s, %s, 'VOTER', 'active')",
            (name, email, mobile, vid, voter_pw)
        )
    
    # Election official
    off_pw = generate_password_hash('Official@12345')
    execute_db(
        "INSERT INTO users (name, email, mobile, voter_id, password_hash, role, status) VALUES (%s, %s, %s, %s, %s, 'ELECTION_OFFICIAL', 'active')",
        ('Election Officer', 'official@demo.local', '9000000099', None, off_pw)
    )
    
    # Polling stations (check if exists)
    existing_stations = query_db("SELECT COUNT(*) as c FROM polling_stations")
    if existing_stations and existing_stations[0]['c'] == 0:
        stations = [
            ('Demo Government College', 'Example Road, Akola, Maharashtra', 'Maharashtra', 'Akola', 'Demo Constituency', 'Demo Booth 12', 500, 'Wheelchair Accessible', 'Drinking Water, Toilet, Help Desk, Waiting Area'),
            ('Demo Community Hall', 'Market Street, Nagpur, Maharashtra', 'Maharashtra', 'Nagpur', 'Demo Constituency North', 'Demo Booth 05', 400, 'Wheelchair Accessible', 'Drinking Water, Toilet, Help Desk'),
            ('Demo Public School', 'Station Road, Pune, Maharashtra', 'Maharashtra', 'Pune', 'Demo Constituency Central', 'Demo Booth 08', 350, 'Ramp Access', 'Drinking Water, Toilet, Waiting Area'),
            ('Demo Municipal Building', 'Main Road, Mumbai, Maharashtra', 'Maharashtra', 'Mumbai', 'Demo Constituency South', 'Demo Booth 15', 600, 'Wheelchair Accessible', 'Drinking Water, Toilet, Help Desk, Waiting Area, Parking'),
        ]
        for s in stations:
            execute_db(
                "INSERT INTO polling_stations (name, address, state, district, constituency, booth_number, capacity, accessibility, facilities) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                s
            )
    
    # Demo election
    now = datetime.datetime.now()
    election_id = execute_db(
        "INSERT INTO elections (name, description, election_type, constituency, start_time, end_time, status) VALUES (%s, %s, %s, %s, %s, %s, 'Active')",
        ('BCA Student Council Election 2026', 'Annual student council election for BCA department', 'Student Council', 'All Constituencies', 
         now - datetime.timedelta(hours=1), now + datetime.timedelta(days=7), 'Active')
    )
    
    # Candidates
    if election_id:
        candidates_data = [
            (election_id, 'Candidate A', 'Student Alliance', '⭐', 'Experienced student leader focused on academics and campus welfare.'),
            (election_id, 'Candidate B', 'Progress Forum', '🏛️', 'Dedicated to improving campus infrastructure and student activities.'),
            (election_id, 'Candidate C', 'Independent', '🤝', 'Independent candidate committed to transparency and student rights.'),
        ]
        for c in candidates_data:
            execute_db(
                "INSERT INTO candidates (election_id, name, party_name, symbol, description, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
                c
            )
    
    # Completed election for results demo
    past_id = execute_db(
        "INSERT INTO elections (name, description, election_type, constituency, start_time, end_time, status) VALUES (%s, %s, %s, %s, %s, %s, 'Completed')",
        ('BCA Tech Quiz Competition 2025', 'Annual tech quiz team election', 'Quiz Team', 'All Constituencies',
         now - datetime.timedelta(days=60), now - datetime.timedelta(days=53), 'Completed')
    )
    
    if past_id:
        past_candidates = [
            (past_id, 'Alpha Squad', 'Alpha Team', '🅰️', 'Previous winners of the inter-class competition.'),
            (past_id, 'Beta Warriors', 'Beta Team', '🅱️', 'Strong competitors in coding challenges.'),
            (past_id, 'Gamma Stars', 'Gamma Team', '⭐', 'New team with innovative ideas.'),
        ]
        for c in past_candidates:
            execute_db(
                "INSERT INTO candidates (election_id, name, party_name, symbol, description, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
                c
            )
    
    print("Demo data seeded successfully!")


with app.app_context():
    try:
        seed_demo_data()
    except Exception as e:
        print(f"Note: Could not seed demo data (database may need schema import): {e}")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
