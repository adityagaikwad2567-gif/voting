"""Initialize SQLite database with schema and demo data."""
import os, sys, sqlite3, datetime
from werkzeug.security import generate_password_hash

os.chdir(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voter_portal.db')

# Remove old DB if exists
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("Removed old database.")

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys=ON")
cur = conn.cursor()

# ── Schema ──────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    mobile VARCHAR(15),
    voter_id VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'VOTER',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);

CREATE TABLE voter_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    dob DATE,
    gender VARCHAR(10),
    address TEXT,
    state VARCHAR(100),
    district VARCHAR(100),
    constituency VARCHAR(150),
    pincode VARCHAR(10),
    photo VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    application_type VARCHAR(30) NOT NULL,
    reference_number VARCHAR(30) NOT NULL UNIQUE,
    status VARCHAR(30) NOT NULL DEFAULT 'Submitted',
    submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remarks TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE elections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    election_type VARCHAR(100),
    constituency VARCHAR(150),
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Draft',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id INTEGER NOT NULL,
    name VARCHAR(150) NOT NULL,
    party_name VARCHAR(200),
    symbol VARCHAR(100),
    description TEXT,
    image VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
);

CREATE TABLE votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id INTEGER NOT NULL,
    voter_id INTEGER NOT NULL,
    candidate_id INTEGER NOT NULL,
    voted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reference_code VARCHAR(100) NOT NULL UNIQUE,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
    FOREIGN KEY (voter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    UNIQUE(voter_id, election_id)
);

CREATE TABLE polling_stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    address TEXT NOT NULL,
    state VARCHAR(100),
    district VARCHAR(100),
    constituency VARCHAR(150),
    booth_number VARCHAR(50),
    capacity INTEGER DEFAULT 500,
    accessibility VARCHAR(200),
    facilities TEXT
);

CREATE TABLE grievances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    reference_number VARCHAR(30) NOT NULL UNIQUE,
    category VARCHAR(30) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    contact_info VARCHAR(200),
    status VARCHAR(20) NOT NULL DEFAULT 'Submitted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    entity VARCHAR(100) NOT NULL,
    entity_id INTEGER,
    ip_address VARCHAR(45),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
"""

cur.executescript(SCHEMA)
print("Schema created.")

# ── Seed Data ───────────────────────────────────────────────
now = datetime.datetime.now()

# Users
admin_pw = generate_password_hash('Admin@12345')
voter_pw = generate_password_hash('Demo@12345')
official_pw = generate_password_hash('Official@12345')

users = [
    ('System Administrator', 'admin@demo.local', '9000000000', None, admin_pw, 'ADMIN', 'active', '2026-01-01 00:00:00'),
    ('Aditya Gaikwad', 'aditya@demo.local', '9100000001', 'DEMO100001', voter_pw, 'VOTER', 'active', '2026-01-15 10:00:00'),
    ('Aditi Naik', 'aditi@demo.local', '9100000002', 'DEMO100002', voter_pw, 'VOTER', 'active', '2026-02-01 11:00:00'),
    ('Rahul Sharma', 'rahul@demo.local', '9100000003', 'DEMO100003', voter_pw, 'VOTER', 'active', '2026-02-15 09:30:00'),
    ('Priya Patil', 'priya@demo.local', '9100000004', 'DEMO100004', voter_pw, 'VOTER', 'active', '2026-03-01 14:00:00'),
    ('Sneha Deshmukh', 'sneha@demo.local', '9100000005', 'DEMO100005', voter_pw, 'VOTER', 'active', '2026-03-15 08:00:00'),
    ('Election Officer', 'official@demo.local', '9000000099', None, official_pw, 'ELECTION_OFFICIAL', 'active', '2026-01-01 00:00:00'),
]
cur.executemany(
    "INSERT INTO users (name, email, mobile, voter_id, password_hash, role, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
    users
)
print(f"Inserted {len(users)} users.")

# Voter profiles
profiles = [
    (2, '2004-05-15', 'Male', '123 Demo Street, Akola', 'Maharashtra', 'Akola', 'Demo Constituency', '444001', None),
    (3, '2004-08-22', 'Female', '456 Demo Nagar, Akola', 'Maharashtra', 'Akola', 'Demo Constituency', '444001', None),
    (4, '2003-12-10', 'Male', '789 Demo Road, Nagpur', 'Maharashtra', 'Nagpur', 'Demo Constituency North', '440001', None),
    (5, '2004-03-08', 'Female', '321 Demo Colony, Pune', 'Maharashtra', 'Pune', 'Demo Constituency Central', '411001', None),
    (6, '2004-01-25', 'Female', '654 Demo Lane, Mumbai', 'Maharashtra', 'Mumbai', 'Demo Constituency South', '400001', None),
]
cur.executemany(
    "INSERT INTO voter_profiles (user_id, dob, gender, address, state, district, constituency, pincode, photo) VALUES (?,?,?,?,?,?,?,?,?)",
    profiles
)
print(f"Inserted {len(profiles)} voter profiles.")

# Polling stations
stations = [
    ('Demo Government College', 'Example Road, Akola, Maharashtra', 'Maharashtra', 'Akola', 'Demo Constituency', 'Demo Booth 12', 500, 'Wheelchair Accessible', 'Drinking Water, Toilet, Help Desk, Waiting Area'),
    ('Demo Community Hall', 'Market Street, Nagpur, Maharashtra', 'Maharashtra', 'Nagpur', 'Demo Constituency North', 'Demo Booth 05', 400, 'Wheelchair Accessible', 'Drinking Water, Toilet, Help Desk'),
    ('Demo Public School', 'Station Road, Pune, Maharashtra', 'Maharashtra', 'Pune', 'Demo Constituency Central', 'Demo Booth 08', 350, 'Ramp Access', 'Drinking Water, Toilet, Waiting Area'),
    ('Demo Municipal Building', 'Main Road, Mumbai, Maharashtra', 'Maharashtra', 'Mumbai', 'Demo Constituency South', 'Demo Booth 15', 600, 'Wheelchair Accessible', 'Drinking Water, Toilet, Help Desk, Waiting Area, Parking'),
]
cur.executemany(
    "INSERT INTO polling_stations (name, address, state, district, constituency, booth_number, capacity, accessibility, facilities) VALUES (?,?,?,?,?,?,?,?,?)",
    stations
)
print(f"Inserted {len(stations)} polling stations.")

# Elections
active_start = (now - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
active_end = (now + datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
completed_start = (now - datetime.timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S')
completed_end = (now - datetime.timedelta(days=53)).strftime('%Y-%m-%d %H:%M:%S')

elections = [
    ('BCA Student Council Election 2026', 'Annual student council election for BCA department', 'Student Council', 'All Constituencies', active_start, active_end, 'Active', '2026-08-20 09:00:00'),
    ('BCA Tech Quiz Competition 2025', 'Annual tech quiz team election', 'Quiz Team', 'All Constituencies', completed_start, completed_end, 'Completed', '2026-06-20 09:00:00'),
]
cur.executemany(
    "INSERT INTO elections (name, description, election_type, constituency, start_time, end_time, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
    elections
)
print(f"Inserted {len(elections)} elections.")

# Candidates
candidates = [
    (1, 'Candidate A', 'Student Alliance', 'Star', 'Experienced student leader focused on academics and campus welfare.', None, '2026-08-20 09:00:00'),
    (1, 'Candidate B', 'Progress Forum', 'Building', 'Dedicated to improving campus infrastructure and student activities.', None, '2026-08-20 09:00:00'),
    (1, 'Candidate C', 'Independent', 'Handshake', 'Independent candidate committed to transparency and student rights.', None, '2026-08-20 09:00:00'),
    (2, 'Alpha Squad', 'Alpha Team', 'A', 'Previous winners of the inter-class competition.', None, '2026-06-20 09:00:00'),
    (2, 'Beta Warriors', 'Beta Team', 'B', 'Strong competitors in coding challenges.', None, '2026-06-20 09:00:00'),
    (2, 'Gamma Stars', 'Gamma Team', 'Star', 'New team with innovative ideas.', None, '2026-06-20 09:00:00'),
]
cur.executemany(
    "INSERT INTO candidates (election_id, name, party_name, symbol, description, image, created_at) VALUES (?,?,?,?,?,?,?)",
    candidates
)
print(f"Inserted {len(candidates)} candidates.")

# Demo applications
apps = [
    (2, 'new_registration', 'DEMO-2026-REG000001', 'Approved', '2026-01-15 10:30:00', '2026-01-20 14:00:00', 'New registration for Aditya Gaikwad'),
    (3, 'new_registration', 'DEMO-2026-REG000002', 'Approved', '2026-02-01 11:30:00', '2026-02-05 10:00:00', 'New registration for Aditi Naik'),
    (5, 'correction', 'DEMO-2026-CORR000001', 'Submitted', '2026-08-20 09:00:00', '2026-08-20 09:00:00', 'Correction request: name change'),
]
cur.executemany(
    "INSERT INTO applications (user_id, application_type, reference_number, status, submitted_at, updated_at, remarks) VALUES (?,?,?,?,?,?,?)",
    apps
)
print(f"Inserted {len(apps)} applications.")

# Audit logs
logs = [
    (1, 'LOGIN', 'user', 1, '127.0.0.1', '2026-08-26 08:00:00'),
    (1, 'ELECTION_CREATED', 'election', 1, '127.0.0.1', '2026-08-20 09:00:00'),
    (2, 'LOGIN', 'user', 2, '127.0.0.1', '2026-08-26 09:00:00'),
    (3, 'LOGIN', 'user', 3, '127.0.0.1', '2026-08-26 09:30:00'),
]
cur.executemany(
    "INSERT INTO audit_logs (user_id, action, entity, entity_id, ip_address, created_at) VALUES (?,?,?,?,?,?)",
    logs
)
print(f"Inserted {len(logs)} audit logs.")

conn.commit()
conn.close()

print(f"\nSQLite database created at: {DB_PATH}")
print("Demo credentials:")
print("  Admin:     admin@demo.local / Admin@12345")
print("  Voter:     aditya@demo.local / Demo@12345")
print("  Official:  official@demo.local / Official@12345")
