"""Startup verification script for Digital Voter Services Portal.
Tests that the app can be created, imports work, and routes resolve.
Does NOT require a MySQL database running - mocks the DB connection.
"""

import sys
import os

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Digital Voter Services Portal - Startup Verification")
print("=" * 60)
print()

# ─── Step 1: Test basic imports ─────────────────────────────
print("[1/5] Testing basic imports...")
try:
    from config import Config
    print("  [OK] config.py loaded")
except Exception as e:
    print(f"  [FAIL] config.py FAILED: {e}")
    sys.exit(1)

try:
    from app.utils.database import query_db, execute_db
    print("  [OK] app/utils/database.py loaded")
except Exception as e:
    print(f"  [FAIL] database.py FAILED: {e}")

try:
    from app.utils.helpers import log_user_action, mask_mobile
    print("  [OK] app/utils/helpers.py loaded")
except Exception as e:
    print(f"  [FAIL] helpers.py FAILED: {e}")

try:
    from app.utils.translations import get_translation
    print("  [OK] app/utils/translations.py loaded")
except Exception as e:
    print(f"  [FAIL] translations.py FAILED: {e}")

try:
    from app.services.db_operations import (
        create_user, get_user_by_email, verify_password,
        create_voter_profile, get_voter_profile,
        create_application, get_application_by_ref,
        create_election, get_elections, get_election,
        create_candidate, get_candidates_for_election,
        cast_vote, has_voted, get_election_results,
        get_all_voters, get_all_applications,
        get_all_polling_stations, create_polling_station,
        get_all_grievances, create_grievance,
        get_audit_logs,
        create_notification, get_user_notifications,
        mark_notification_read, get_unread_notification_count,
        get_dashboard_stats, get_registration_trend,
        get_application_status_counts, get_application_type_counts,
        get_total_voters, get_total_votes, get_votes_by_election,
        get_all_votes, update_voter_profile,
        search_voters, search_polling_station,
        update_voter_status, update_application_status,
        update_election_status, update_election, delete_election,
        update_candidate, delete_candidate,
        update_polling_station, delete_polling_station,
        update_grievance_status,
        get_user_applications, get_user_grievances,
        get_grievance_by_ref, get_voter_profile_with_user,
        get_voter_vote_history, get_candidate,
        get_all_candidates, get_active_elections,
        get_polling_station, generate_application_number,
        log_audit, get_user_by_id, get_user_by_voter_id,
        get_notifications,
    )
    print("  [OK] app/services/db_operations.py loaded (all functions)")
except ImportError as e:
    print(f"  [FAIL] db_operations.py FAILED import: {e}")
    sys.exit(1)
except Exception as e:
    print(f"  [FAIL] db_operations.py FAILED: {e}")

try:
    from app.models.user import User
    print("  [OK] app/models/user.py loaded")
except Exception as e:
    print(f"  [FAIL] user.py FAILED: {e}")

print()

# ─── Step 2: Test route module imports ───────────────────────
print("[2/5] Testing route module imports...")
route_modules = [
    ("app.routes.main", "main_bp"),
    ("app.routes.auth", "auth_bp"),
    ("app.routes.voter", "voter_bp"),
    ("app.routes.elections", "elections_bp"),
    ("app.routes.voting", "voting_bp"),
    ("app.routes.grievances", "grievances_bp"),
    ("app.routes.info", "info_bp"),
    ("app.routes.admin", "admin_bp"),
    ("app.routes.errors", "register_error_handlers"),
]
for mod_name, attr_name in route_modules:
    try:
        mod = __import__(mod_name, fromlist=[attr_name])
        getattr(mod, attr_name)
        print(f"  [OK] {mod_name}.{attr_name}")
    except ImportError as e:
        print(f"  [FAIL] {mod_name} IMPORT FAILED: {e}")
    except AttributeError as e:
        print(f"  [FAIL] {mod_name} ATTR FAILED: {e}")
    except Exception as e:
        print(f"  [FAIL] {mod_name} FAILED: {e}")

print()

# ─── Step 3: Test Flask app creation ────────────────────────
print("[3/5] Testing Flask app creation...")
try:
    from app import create_app, csrf
    print("  [OK] create_app imported from app/__init__.py")
except Exception as e:
    print(f"  [FAIL] FAILED to import create_app: {e}")
    sys.exit(1)

# Monkey-patch the database to avoid needing MySQL
import app.utils.database as db_mod
original_query = db_mod.query_db
original_execute = db_mod.execute_db

def mock_query(query, args=None, one=False):
    """Return empty results for all queries during startup test."""
    if 'COUNT(*)' in query.upper() or 'count' in query.lower():
        if one:
            return {'c': 0}
        return []
    if one:
        return None
    return []

def mock_execute(query, args=None):
    """Mock execute - return dummy ID."""
    return 1

db_mod.query_db = mock_query
db_mod.execute_db = mock_execute

try:
    app = create_app()
    print("  [OK] Flask app created successfully")
except Exception as e:
    print(f"  [FAIL] FAILED to create app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from app.routes.auth import init_login_manager
    init_login_manager(app)
    print("  [OK] Login manager initialized")
except Exception as e:
    print(f"  [FAIL] Login manager FAILED: {e}")

print()

# ─── Step 4: Test all registered routes ─────────────────────
print("[4/5] Testing registered routes...")
with app.app_context():
    rules = sorted(app.url_map.iter_rules(), key=lambda r: r.rule)
    print(f"  Total routes registered: {len(rules)}")
    print()
    
    # Group routes by blueprint
    blueprints = {}
    for rule in rules:
        bp = rule.endpoint.split('.')[0] if '.' in rule.endpoint else 'main'
        if bp not in blueprints:
            blueprints[bp] = []
        methods = sorted(rule.methods - {'OPTIONS', 'HEAD'})
        blueprints[bp].append((rule.rule, methods, rule.endpoint))
    
    for bp_name in sorted(blueprints.keys()):
        routes = blueprints[bp_name]
        print(f"  [{bp_name.upper()}] ({len(routes)} routes)")
        for path, methods, endpoint in routes:
            method_str = ', '.join(methods)
            print(f"    {method_str:12s} {path:50s} -> {endpoint}")
        print()

print()

# ─── Step 5: Test template resolution ───────────────────────
print("[5/5] Testing template resolution...")
templates_to_check = [
    "base.html",
    "index.html",
    "auth/login.html",
    "auth/register.html",
    "voter/dashboard.html",
    "voter/profile.html",
    "voter/registration_step1.html",
    "voter/registration_step2.html",
    "voter/registration_step3.html",
    "voter/registration_step4.html",
    "voter/registration_success.html",
    "voter/search.html",
    "voter/polling_station.html",
    "voter/digital_card.html",
    "voter/update_correction.html",
    "voter/correction_success.html",
    "voter/address_transfer.html",
    "voter/transfer_success.html",
    "voter/track_application.html",
    "voter/eligibility.html",
    "elections/list.html",
    "elections/detail.html",
    "elections/schedule.html",
    "elections/candidates.html",
    "elections/candidate_detail.html",
    "elections/results_list.html",
    "elections/results_detail.html",
    "voting/index.html",
    "voting/active.html",
    "voting/cast.html",
    "voting/confirm.html",
    "voting/success.html",
    "voting/status.html",
    "voting/history.html",
    "grievances/index.html",
    "grievances/submit.html",
    "grievances/success.html",
    "grievances/track.html",
    "info/how_to_vote.html",
    "info/eligibility.html",
    "info/documents.html",
    "info/faq.html",
    "info/contact.html",
    "info/about.html",
    "info/privacy.html",
    "info/terms.html",
    "admin/dashboard.html",
    "admin/voters.html",
    "admin/add_voter.html",
    "admin/view_voter.html",
    "admin/edit_voter.html",
    "admin/applications.html",
    "admin/elections.html",
    "admin/create_election.html",
    "admin/edit_election.html",
    "admin/manage_candidates.html",
    "admin/edit_candidate.html",
    "admin/polling_stations.html",
    "admin/add_polling_station.html",
    "admin/grievances.html",
    "admin/audit_logs.html",
    "admin/reports.html",
    "admin/notifications.html",
    "admin/settings.html",
    "admin/votes.html",
    "admin/results.html",
    "errors/400.html",
    "errors/401.html",
    "errors/403.html",
    "errors/404.html",
    "errors/429.html",
    "errors/500.html",
]

found = 0
missing = 0
with app.app_context():
    from jinja2 import TemplateNotFound
    for tpl in templates_to_check:
        try:
            app.jinja_env.get_template(tpl)
            found += 1
        except TemplateNotFound:
            print(f"  [MISS] {tpl}")
            missing += 1
        except Exception as e:
            print(f"  [ERROR] {tpl} -> {e}")
            missing += 1

print(f"  Templates found: {found}/{found + missing}")
if missing == 0:
    print("  [OK] All templates resolved successfully!")
print()

# ─── Test rendering a simple route ──────────────────────────
print("BONUS: Testing homepage render...")
with app.test_client() as client:
    try:
        response = client.get('/')
        print(f"  GET / -> {response.status_code}")
        if response.status_code == 200:
            print("  [OK] Homepage renders successfully")
        else:
            print(f"  [FAIL] Homepage returned {response.status_code}")
    except Exception as e:
        print(f"  [FAIL] Homepage FAILED: {e}")

# Test a few more routes
test_routes = [
    '/info/faq',
    '/info/about',
    '/info/how-to-vote',
    '/info/eligibility',
    '/info/documents',
    '/info/privacy',
    '/info/terms',
    '/info/contact',
    '/elections/',
    '/elections/schedule',
    '/elections/candidates',
    '/elections/results',
    '/voter/eligibility',
    '/voter/track-application',
    '/auth/login',
    '/auth/register',
]

print()
print("Testing public routes:")
with app.test_client() as client:
    for route in test_routes:
        try:
            response = client.get(route)
            status = "[OK]" if response.status_code == 200 else f"[FAIL] ({response.status_code})"
            print(f"  {status} GET {route}")
        except Exception as e:
            print(f"  [FAIL] GET {route} -> {type(e).__name__}: {e}")

# Restore original DB functions
db_mod.query_db = original_query
db_mod.execute_db = original_execute

print()
print("=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
