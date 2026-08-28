from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import datetime
from app.utils.database import query_db, execute_db, execute_transaction


def _safe_count(query, params=None):
    """Execute a COUNT query safely, returning 0 on any failure."""
    try:
        row = query_db(query, params, one=True)
        if row and isinstance(row, dict):
            return row.get('c', row.get('total', 0))
    except Exception:
        pass
    return 0


# ─── User Operations ────────────────────────────────────────

def create_user(name, email, mobile, password, role='VOTER'):
    """Create a new user account."""
    password_hash = generate_password_hash(password)
    user_id = execute_db(
        "INSERT INTO users (name, email, mobile, password_hash, role, status) VALUES (%s, %s, %s, %s, %s, %s)",
        (name, email, mobile, password_hash, role, 'active')
    )
    return user_id


def get_user_by_email(email):
    """Get user by email."""
    return query_db("SELECT * FROM users WHERE email = %s", (email,), one=True)


def get_user_by_id(user_id):
    """Get user by ID."""
    return query_db("SELECT * FROM users WHERE id = %s", (user_id,), one=True)


def get_user_by_voter_id(voter_id):
    """Get user by demo EPIC/voter_id."""
    return query_db("SELECT * FROM users WHERE voter_id = %s", (voter_id,), one=True)


def verify_password(user, password):
    """Verify password against hash."""
    if user and user.get('password_hash'):
        return check_password_hash(user['password_hash'], password)
    return False


def update_user_last_login(user_id):
    """Update user last login timestamp."""
    execute_db("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))


# ─── Voter Profile Operations ───────────────────────────────

def create_voter_profile(user_id, dob, gender, address, state, district, constituency, pincode, photo=None):
    """Create or update voter profile."""
    existing = query_db("SELECT id FROM voter_profiles WHERE user_id = %s", (user_id,), one=True)
    if existing:
        execute_db(
            """UPDATE voter_profiles SET dob=%s, gender=%s, address=%s, state=%s, 
               district=%s, constituency=%s, pincode=%s, photo=%s WHERE user_id=%s""",
            (dob, gender, address, state, district, constituency, pincode, photo, user_id)
        )
    else:
        execute_db(
            """INSERT INTO voter_profiles (user_id, dob, gender, address, state, district, constituency, pincode, photo) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, dob, gender, address, state, district, constituency, pincode, photo)
        )


def get_voter_profile(user_id):
    """Get voter profile by user ID."""
    return query_db("SELECT * FROM voter_profiles WHERE user_id = %s", (user_id,), one=True)


def get_voter_profile_with_user(user_id):
    """Get voter profile joined with user info."""
    return query_db(
        """SELECT u.*, vp.dob, vp.gender, vp.address, vp.state, vp.district, 
           vp.constituency, vp.pincode, vp.photo 
           FROM users u LEFT JOIN voter_profiles vp ON u.id = vp.user_id 
           WHERE u.id = %s""",
        (user_id,), one=True
    )


def search_voters(name=None, state=None, district=None, constituency=None, age=None, voter_id=None, mobile=None):
    """Search electoral roll demo data."""
    conditions = []
    params = []
    
    if name:
        conditions.append("u.name LIKE %s")
        params.append(f"%{name}%")
    if state:
        conditions.append("vp.state = %s")
        params.append(state)
    if district:
        conditions.append("vp.district = %s")
        params.append(district)
    if constituency:
        conditions.append("vp.constituency = %s")
        params.append(constituency)
    if age:
        conditions.append("TIMESTAMPDIFF(YEAR, vp.dob, CURDATE()) = %s")
        params.append(int(age))
    if voter_id:
        conditions.append("u.voter_id = %s")
        params.append(voter_id)
    if mobile:
        conditions.append("u.mobile = %s")
        params.append(mobile)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    results = query_db(
        f"""SELECT u.id, u.name, u.voter_id, u.email, u.mobile, u.status,
            vp.dob, vp.gender, vp.address, vp.state, vp.district, 
            vp.constituency, vp.pincode
            FROM users u 
            LEFT JOIN voter_profiles vp ON u.id = vp.user_id 
            WHERE {where_clause} AND u.role = 'VOTER'""",
        params
    )
    return results or []


def update_voter_status(user_id, status):
    """Update voter account status."""
    execute_db("UPDATE users SET status = %s WHERE id = %s", (status, user_id))


def get_all_voters(page=1, per_page=20, search=None):
    """Get paginated list of all voters for admin."""
    offset = (page - 1) * per_page
    params = []
    where = ""
    
    if search:
        where = "WHERE (u.name LIKE %s OR u.email LIKE %s OR u.voter_id LIKE %s)"
        params = [f"%{search}%", f"%{search}%", f"%{search}%"]
    
    count_query = f"SELECT COUNT(*) as total FROM users u LEFT JOIN voter_profiles vp ON u.id = vp.user_id {where}"
    total = _safe_count(count_query, params)
    
    params.extend([per_page, offset])
    results = query_db(
        f"""SELECT u.*, vp.state, vp.district, vp.constituency, vp.dob, vp.gender
            FROM users u 
            LEFT JOIN voter_profiles vp ON u.id = vp.user_id 
            {where}
            ORDER BY u.created_at DESC LIMIT %s OFFSET %s""",
        params
    )
    return results or [], total


# ─── Application Operations ─────────────────────────────────

def generate_application_number(app_type='APP'):
    """Generate unique application reference number."""
    prefix_map = {
        'new_registration': 'REG',
        'correction': 'CORR',
        'address_transfer': 'ADDR',
    }
    prefix = prefix_map.get(app_type, 'APP')
    year = datetime.datetime.now().year
    count = _safe_count(
        "SELECT COUNT(*) as c FROM applications WHERE application_type = %s",
        (app_type,)
    )
    return f"DEMO-{year}-{prefix}{str(count + 1).zfill(6)}"


def create_application(user_id, app_type, details=None, remarks=None):
    """Create a new application."""
    ref_number = generate_application_number(app_type)
    app_id = execute_db(
        """INSERT INTO applications (user_id, application_type, reference_number, status, remarks, submitted_at, updated_at) 
           VALUES (%s, %s, %s, 'Submitted', %s, NOW(), NOW())""",
        (user_id, app_type, ref_number, remarks)
    )
    return app_id, ref_number


def get_application_by_ref(ref_number):
    """Get application by reference number."""
    return query_db(
        """SELECT a.*, u.name as applicant_name, u.email as applicant_email 
           FROM applications a JOIN users u ON a.user_id = u.id 
           WHERE a.reference_number = %s""",
        (ref_number,), one=True
    )


def get_user_applications(user_id):
    """Get all applications for a user."""
    return query_db(
        "SELECT * FROM applications WHERE user_id = %s ORDER BY submitted_at DESC",
        (user_id,)
    ) or []


def get_all_applications(page=1, per_page=20, search=None, status=None, app_type=None):
    """Get paginated applications for admin."""
    offset = (page - 1) * per_page
    conditions = []
    params = []
    
    if search:
        conditions.append("(a.reference_number LIKE %s OR u.name LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    if status:
        conditions.append("a.status = %s")
        params.append(status)
    if app_type:
        conditions.append("a.application_type = %s")
        params.append(app_type)
    
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    total = _safe_count(
        f"SELECT COUNT(*) as c FROM applications a JOIN users u ON a.user_id = u.id {where}",
        params
    )
    
    params.extend([per_page, offset])
    results = query_db(
        f"""SELECT a.*, u.name as applicant_name, u.email as applicant_email
            FROM applications a JOIN users u ON a.user_id = u.id 
            {where} ORDER BY a.submitted_at DESC LIMIT %s OFFSET %s""",
        params
    )
    return results or [], total


def update_application_status(app_id, status, remarks=None):
    """Update application status."""
    execute_db(
        "UPDATE applications SET status = %s, remarks = %s, updated_at = NOW() WHERE id = %s",
        (status, remarks, app_id)
    )


# ─── Election Operations ────────────────────────────────────

def create_election(name, description, election_type, constituency, start_time, end_time):
    """Create a new election."""
    election_id = execute_db(
        """INSERT INTO elections (name, description, election_type, constituency, start_time, end_time, status, created_at) 
           VALUES (%s, %s, %s, %s, %s, %s, 'Upcoming', NOW())""",
        (name, description, election_type, constituency, start_time, end_time)
    )
    return election_id


def get_election(election_id):
    """Get election by ID."""
    return query_db("SELECT * FROM elections WHERE id = %s", (election_id,), one=True)


def get_elections(status=None):
    """Get elections, optionally filtered by status."""
    if status:
        return query_db(
            "SELECT * FROM elections WHERE status = %s ORDER BY start_time DESC",
            (status,)
        ) or []
    return query_db("SELECT * FROM elections ORDER BY start_time DESC") or []


def get_active_elections():
    """Get currently active elections."""
    return query_db(
        "SELECT * FROM elections WHERE status = 'Active' AND NOW() BETWEEN start_time AND end_time ORDER BY start_time"
    ) or []


def update_election_status(election_id, status):
    """Update election status."""
    execute_db("UPDATE elections SET status = %s WHERE id = %s", (status, election_id))


def update_election(election_id, name, description, election_type, constituency, start_time, end_time, status):
    """Update election details."""
    execute_db(
        """UPDATE elections SET name=%s, description=%s, election_type=%s, constituency=%s, 
           start_time=%s, end_time=%s, status=%s WHERE id=%s""",
        (name, description, election_type, constituency, start_time, end_time, status, election_id)
    )


def delete_election(election_id):
    """Delete an election (only if not completed/active)."""
    election = get_election(election_id)
    if election and election['status'] not in ('Active', 'Completed'):
        execute_db("DELETE FROM candidates WHERE election_id = %s", (election_id,))
        execute_db("DELETE FROM elections WHERE id = %s", (election_id,))
        return True
    return False


# ─── Candidate Operations ───────────────────────────────────

def create_candidate(election_id, name, party_name, symbol=None, description=None, image=None):
    """Add a candidate to an election."""
    candidate_id = execute_db(
        """INSERT INTO candidates (election_id, name, party_name, symbol, description, image, created_at) 
           VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
        (election_id, name, party_name, symbol, description, image)
    )
    return candidate_id


def get_candidates_for_election(election_id):
    """Get all candidates for an election."""
    return query_db(
        "SELECT * FROM candidates WHERE election_id = %s ORDER BY name",
        (election_id,)
    ) or []


def get_candidate(candidate_id):
    """Get a specific candidate."""
    return query_db(
        """SELECT c.*, e.name as election_name, e.status as election_status 
           FROM candidates c JOIN elections e ON c.election_id = e.id 
           WHERE c.id = %s""",
        (candidate_id,), one=True
    )


def update_candidate(candidate_id, name, party_name, symbol=None, description=None, image=None):
    """Update candidate details."""
    execute_db(
        """UPDATE candidates SET name=%s, party_name=%s, symbol=%s, description=%s, image=%s 
           WHERE id=%s""",
        (name, party_name, symbol, description, image, candidate_id)
    )


def delete_candidate(candidate_id):
    """Delete a candidate."""
    execute_db("DELETE FROM candidates WHERE id = %s", (candidate_id,))


def get_all_candidates(page=1, per_page=20, search=None, election_id=None):
    """Get paginated candidates for admin."""
    offset = (page - 1) * per_page
    conditions = []
    params = []
    
    if search:
        conditions.append("(c.name LIKE %s OR c.party_name LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])
    if election_id:
        conditions.append("c.election_id = %s")
        params.append(election_id)
    
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    total_row = query_db(
        f"SELECT COUNT(*) as c FROM candidates c {where}",
        params, one=True
    )
    total = total_row['c'] if total_row else 0
    
    params.extend([per_page, offset])
    results = query_db(
        f"""SELECT c.*, e.name as election_name 
            FROM candidates c LEFT JOIN elections e ON c.election_id = e.id 
            {where} ORDER BY c.created_at DESC LIMIT %s OFFSET %s""",
        params
    )
    return results or [], total


# ─── Vote Operations ────────────────────────────────────────

def cast_vote(election_id, voter_id, candidate_id):
    """Cast a vote in a transaction with duplicate prevention."""
    # Check duplicate
    existing = query_db(
        "SELECT id FROM votes WHERE voter_id = %s AND election_id = %s",
        (voter_id, election_id), one=True
    )
    if existing:
        return None, "You have already voted in this election."
    
    # Check election is active
    election = get_election(election_id)
    if not election or election['status'] != 'Active':
        return None, "This election is not currently active."
    
    # Check candidate belongs to election
    candidate = query_db(
        "SELECT id FROM candidates WHERE id = %s AND election_id = %s",
        (candidate_id, election_id), one=True
    )
    if not candidate:
        return None, "Invalid candidate for this election."
    
    ref_code = f"VOTE-{election_id}-{voter_id}-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    vote_id = execute_db(
        """INSERT INTO votes (election_id, voter_id, candidate_id, voted_at, reference_code) 
           VALUES (%s, %s, %s, NOW(), %s)""",
        (election_id, voter_id, candidate_id, ref_code)
    )
    
    return vote_id, ref_code if vote_id else "Failed to record vote."


def has_voted(election_id, voter_id):
    """Check if a voter has already voted in an election."""
    result = query_db(
        "SELECT id FROM votes WHERE voter_id = %s AND election_id = %s",
        (voter_id, election_id), one=True
    )
    return result is not None


def get_voter_vote_history(voter_id):
    """Get voting history for a voter."""
    return query_db(
        """SELECT v.*, e.name as election_name, e.status as election_status,
           c.name as candidate_name, c.party_name 
           FROM votes v 
           JOIN elections e ON v.election_id = e.id 
           JOIN candidates c ON v.candidate_id = c.id 
           WHERE v.voter_id = %s ORDER BY v.voted_at DESC""",
        (voter_id,)
    ) or []


def get_election_results(election_id):
    """Get election results with candidate totals."""
    election = get_election(election_id)
    if not election:
        return None
    
    candidates = query_db(
        """SELECT c.id, c.name, c.party_name, c.symbol, c.image,
           COUNT(v.id) as vote_count
           FROM candidates c 
           LEFT JOIN votes v ON c.id = v.candidate_id AND v.election_id = c.election_id 
           WHERE c.election_id = %s 
           GROUP BY c.id, c.name, c.party_name, c.symbol, c.image 
           ORDER BY vote_count DESC""",
        (election_id,)
    ) or []
    
    # Convert sqlite3.Row objects to dicts so we can modify them
    candidates = [dict(c) if not isinstance(c, dict) else c for c in candidates]
    total_votes = sum(c['vote_count'] for c in candidates)
    
    for c in candidates:
        c['percentage'] = round((c['vote_count'] / total_votes * 100), 1) if total_votes > 0 else 0
    
    winner = candidates[0] if candidates and candidates[0]['vote_count'] > 0 else None
    
    return {
        'election': election,
        'candidates': candidates,
        'total_votes': total_votes,
        'winner': winner
    }


def get_total_voters():
    """Get total registered voters."""
    result = query_db("SELECT COUNT(*) as c FROM users WHERE role = 'VOTER'", one=True)
    return result['c'] if result else 0


def get_total_votes():
    """Get total votes cast."""
    result = query_db("SELECT COUNT(*) as c FROM votes", one=True)
    return result['c'] if result else 0


def get_votes_by_election():
    """Get vote counts grouped by election."""
    return query_db(
        """SELECT e.id, e.name, COUNT(v.id) as vote_count 
           FROM elections e LEFT JOIN votes v ON e.id = v.election_id 
           GROUP BY e.id, e.name ORDER BY e.start_time DESC"""
    ) or []


# ─── Polling Station Operations ─────────────────────────────

def create_polling_station(name, address, state, district, constituency, booth_number, capacity=500, accessibility=None, facilities=None):
    """Create a polling station."""
    station_id = execute_db(
        """INSERT INTO polling_stations (name, address, state, district, constituency, booth_number, capacity, accessibility, facilities) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (name, address, state, district, constituency, booth_number, capacity, accessibility, facilities)
    )
    return station_id


def search_polling_station(voter_id=None, name=None, district=None, constituency=None):
    """Search for polling stations."""
    conditions = []
    params = []
    
    if voter_id:
        # Find polling station via voter's constituency
        user = query_db(
            """SELECT vp.constituency, vp.district, vp.state 
               FROM users u JOIN voter_profiles vp ON u.id = vp.user_id 
               WHERE u.voter_id = %s""",
            (voter_id,), one=True
        )
        if user:
            if user.get('constituency'):
                conditions.append("ps.constituency = %s")
                params.append(user['constituency'])
            if user.get('district'):
                conditions.append("ps.district = %s")
                params.append(user['district'])
        else:
            return []
    
    if name:
        conditions.append("ps.name LIKE %s")
        params.append(f"%{name}%")
    if district:
        conditions.append("ps.district = %s")
        params.append(district)
    if constituency:
        conditions.append("ps.constituency = %s")
        params.append(constituency)
    
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    return query_db(
        f"SELECT * FROM polling_stations ps {where} ORDER BY ps.name",
        params
    ) or []


def get_polling_station(station_id):
    """Get a specific polling station."""
    return query_db("SELECT * FROM polling_stations WHERE id = %s", (station_id,), one=True)


def get_all_polling_stations(page=1, per_page=20, search=None):
    """Get paginated polling stations for admin."""
    offset = (page - 1) * per_page
    params = []
    where = ""
    
    if search:
        where = "WHERE (name LIKE %s OR district LIKE %s OR constituency LIKE %s)"
        params = [f"%{search}%", f"%{search}%", f"%{search}%"]
    
    total = _safe_count(f"SELECT COUNT(*) as c FROM polling_stations {where}", params)
    
    params.extend([per_page, offset])
    results = query_db(
        f"SELECT * FROM polling_stations {where} ORDER BY name LIMIT %s OFFSET %s",
        params
    )
    return results or [], total


def update_polling_station(station_id, **kwargs):
    """Update a polling station."""
    fields = []
    values = []
    for key, value in kwargs.items():
        if key in ('name', 'address', 'state', 'district', 'constituency', 'booth_number', 'capacity', 'accessibility', 'facilities'):
            fields.append(f"{key} = %s")
            values.append(value)
    if fields:
        values.append(station_id)
        execute_db(f"UPDATE polling_stations SET {', '.join(fields)} WHERE id = %s", values)


def delete_polling_station(station_id):
    """Delete a polling station."""
    execute_db("DELETE FROM polling_stations WHERE id = %s", (station_id,))


# ─── Grievance Operations ───────────────────────────────────

def generate_grievance_number():
    """Generate unique grievance reference number."""
    year = datetime.datetime.now().year
    count = _safe_count("SELECT COUNT(*) as c FROM grievances")
    return f"GRV-{year}-{str(count + 1).zfill(6)}"


def create_grievance(user_id, category, subject, description, contact_info=None):
    """Create a new grievance."""
    ref_number = generate_grievance_number()
    grievance_id = execute_db(
        """INSERT INTO grievances (user_id, reference_number, category, subject, description, contact_info, status, created_at, updated_at) 
           VALUES (%s, %s, %s, %s, %s, %s, 'Submitted', NOW(), NOW())""",
        (user_id, ref_number, category, subject, description, contact_info)
    )
    return grievance_id, ref_number


def get_grievance_by_ref(ref_number):
    """Get grievance by reference number."""
    return query_db(
        """SELECT g.*, u.name as user_name 
           FROM grievances g JOIN users u ON g.user_id = u.id 
           WHERE g.reference_number = %s""",
        (ref_number,), one=True
    )


def get_user_grievances(user_id):
    """Get all grievances for a user."""
    return query_db(
        "SELECT * FROM grievances WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,)
    ) or []


def get_all_grievances(page=1, per_page=20, search=None, status=None, category=None):
    """Get paginated grievances for admin."""
    offset = (page - 1) * per_page
    conditions = []
    params = []
    
    if search:
        conditions.append("(g.reference_number LIKE %s OR g.subject LIKE %s OR u.name LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if status:
        conditions.append("g.status = %s")
        params.append(status)
    if category:
        conditions.append("g.category = %s")
        params.append(category)
    
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    total = _safe_count(
        f"SELECT COUNT(*) as c FROM grievances g JOIN users u ON g.user_id = u.id {where}",
        params
    )
    
    params.extend([per_page, offset])
    results = query_db(
        f"""SELECT g.*, u.name as user_name 
            FROM grievances g JOIN users u ON g.user_id = u.id 
            {where} ORDER BY g.created_at DESC LIMIT %s OFFSET %s""",
        params
    )
    return results or [], total


def update_grievance_status(grievance_id, status, remarks=None):
    """Update grievance status."""
    execute_db(
        "UPDATE grievances SET status = %s, updated_at = NOW() WHERE id = %s",
        (status, grievance_id)
    )


# ─── Notification Operations ────────────────────────────────

def create_notification(user_id, title, message):
    """Create a notification."""
    execute_db(
        "INSERT INTO notifications (user_id, title, message, is_read, created_at) VALUES (%s, %s, %s, 0, NOW())",
        (user_id, title, message)
    )


def get_user_notifications(user_id, unread_only=False):
    """Get user notifications."""
    if unread_only:
        return query_db(
            "SELECT * FROM notifications WHERE user_id = %s AND is_read = 0 ORDER BY created_at DESC",
            (user_id,)
        ) or []
    return query_db(
        "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT 50",
        (user_id,)
    ) or []


def get_unread_notification_count(user_id):
    """Get count of unread notifications."""
    result = query_db(
        "SELECT COUNT(*) as c FROM notifications WHERE user_id = %s AND is_read = 0",
        (user_id,), one=True
    )
    return result['c'] if result else 0


def mark_notification_read(notification_id, user_id):
    """Mark a notification as read."""
    execute_db(
        "UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s",
        (notification_id, user_id)
    )


def mark_all_notifications_read(user_id):
    """Mark all notifications as read."""
    execute_db(
        "UPDATE notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0",
        (user_id,)
    )


# ─── Audit Log Operations ───────────────────────────────────

def log_audit(user_id, action, entity, entity_id=None, ip_address=None):
    """Log an audit event."""
    execute_db(
        """INSERT INTO audit_logs (user_id, action, entity, entity_id, ip_address, created_at) 
           VALUES (%s, %s, %s, %s, %s, NOW())""",
        (user_id, action, entity, entity_id, ip_address)
    )


def get_audit_logs(page=1, per_page=50, search=None, action=None, entity=None, user_id=None):
    """Get paginated audit logs for admin."""
    offset = (page - 1) * per_page
    conditions = []
    params = []
    
    if search:
        conditions.append("(al.action LIKE %s OR al.entity LIKE %s OR u.name LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if action:
        conditions.append("al.action = %s")
        params.append(action)
    if entity:
        conditions.append("al.entity = %s")
        params.append(entity)
    if user_id:
        conditions.append("al.user_id = %s")
        params.append(user_id)
    
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    total = _safe_count(
        f"SELECT COUNT(*) as c FROM audit_logs al LEFT JOIN users u ON al.user_id = u.id {where}",
        params
    )
    
    params.extend([per_page, offset])
    results = query_db(
        f"""SELECT al.*, u.name as user_name, u.role as user_role
            FROM audit_logs al LEFT JOIN users u ON al.user_id = u.id 
            {where} ORDER BY al.created_at DESC LIMIT %s OFFSET %s""",
        params
    )
    return results or [], total


# ─── Statistics Operations ───────────────────────────────────

def get_dashboard_stats():
    """Get admin dashboard statistics."""
    return {
        'total_voters': get_total_voters(),
        'pending_applications': _safe_count(
            "SELECT COUNT(*) as c FROM applications WHERE status IN ('Submitted', 'Under Review')"
        ),
        'active_elections': _safe_count(
            "SELECT COUNT(*) as c FROM elections WHERE status = 'Active'"
        ),
        'upcoming_elections': _safe_count(
            "SELECT COUNT(*) as c FROM elections WHERE status = 'Upcoming'"
        ),
        'completed_elections': _safe_count(
            "SELECT COUNT(*) as c FROM elections WHERE status = 'Completed'"
        ),
        'total_votes': get_total_votes(),
        'pending_grievances': _safe_count(
            "SELECT COUNT(*) as c FROM grievances WHERE status IN ('Submitted', 'In Progress')"
        ),
        'total_applications': _safe_count(
            "SELECT COUNT(*) as c FROM applications"
        ),
    }


def get_registration_trend():
    """Get voter registration trend data (last 12 months)."""
    return query_db(
        """SELECT DATE_FORMAT(created_at, '%Y-%m') as month, COUNT(*) as count 
           FROM users WHERE role = 'VOTER' 
           GROUP BY DATE_FORMAT(created_at, '%Y-%m') 
           ORDER BY month DESC LIMIT 12"""
    ) or []


def get_application_status_counts():
    """Get application counts by status."""
    return query_db(
        "SELECT status, COUNT(*) as count FROM applications GROUP BY status"
    ) or []


def get_application_type_counts():
    """Get application counts by type."""
    return query_db(
        "SELECT application_type, COUNT(*) as count FROM applications GROUP BY application_type"
    ) or []


def get_all_votes():
    """Get all vote records with election and voter info."""
    return query_db(
        """SELECT v.*, e.name as election_name, u.name as voter_name
           FROM votes v
           JOIN elections e ON v.election_id = e.id
           JOIN users u ON v.voter_id = u.id
           ORDER BY v.voted_at DESC"""
    ) or []


def update_voter_profile(user_id, data):
    """Update voter profile and user fields."""
    # Update user table
    if 'name' in data or 'email' in data or 'mobile' in data:
        execute_db(
            "UPDATE users SET name = %s, email = %s, mobile = %s WHERE id = %s",
            (data.get('name', ''), data.get('email', ''), data.get('mobile', ''), user_id)
        )
    if 'role' in data:
        execute_db("UPDATE users SET role = %s WHERE id = %s", (data['role'].upper(), user_id))
    if 'status' in data:
        execute_db("UPDATE users SET status = %s WHERE id = %s", (data['status'], user_id))
    # Update voter_profiles table
    execute_db(
        """UPDATE voter_profiles SET dob = %s, gender = %s, address = %s,
           state = %s, district = %s, constituency = %s, pincode = %s
           WHERE user_id = %s""",
        (data.get('dob', ''), data.get('gender', ''), data.get('address', ''),
         data.get('state', ''), data.get('district', ''), data.get('constituency', ''),
         data.get('pincode', ''), user_id)
    )


def get_notifications(user_id):
    """Get notifications (alias)."""
    return get_user_notifications(user_id)
