"""Comprehensive admin route and template validation test."""
import os, sys, re, glob

os.environ['DATABASE_HOST'] = 'localhost'
os.environ['DATABASE_PORT'] = '9999'

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.routes.auth import init_login_manager

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
app.config['SERVER_NAME'] = 'localhost'
init_login_manager(app)

# ── Step 1: Test all endpoint functions exist ────────────────
print("=" * 70)
print("STEP 1: Checking all endpoint functions exist")
print("=" * 70)

admin_endpoints = set()
all_endpoints = set()
with app.app_context():
    for rule in app.url_map.iter_rules():
        ep = rule.endpoint
        all_endpoints.add(ep)
        if ep.startswith('admin.'):
            admin_endpoints.add(ep)
            assert ep in app.view_functions, f"Missing view function: {ep}"

print(f"  Total endpoints: {len(all_endpoints)}")
print(f"  Admin endpoints: {len(admin_endpoints)}")
print("  All admin view functions exist: OK")

# ── Step 2: Test url_for resolution for all template refs ───
print()
print("=" * 70)
print("STEP 2: Checking all template url_for references resolve")
print("=" * 70)

all_template_eps = set()
for f in glob.glob('templates/**/*.html', recursive=True):
    with open(f, encoding='utf-8') as fh:
        content = fh.read()
    for m in re.finditer(r"url_for\('(\w+)\.(\w+)'", content):
        ep = f'{m.group(1)}.{m.group(2)}'
        all_template_eps.add(ep)

# Group by whether they need params
needs_params = set()
no_params = set()
for ep in all_template_eps:
    # Check if any template passes params
    needs_params.add(ep)

missing = []
with app.app_context():
    for ep in sorted(all_template_eps):
        with app.test_request_context():
            from flask import url_for
            try:
                # Try without params first
                url_for(ep)
                no_params.add(ep)
            except TypeError:
                # Needs params — just verify function exists
                if ep not in app.view_functions:
                    missing.append(ep)
            except Exception as e:
                if ep not in app.view_functions:
                    missing.append(ep)

if missing:
    print(f"  MISSING endpoints referenced by templates:")
    for ep in missing:
        print(f"    - {ep}")
else:
    print(f"  All {len(all_template_eps)} template endpoint references resolve OK")

# ── Step 3: Login as admin and test all GET routes ──────────
print()
print("=" * 70)
print("STEP 3: Testing all GET routes as admin")
print("=" * 70)

client = app.test_client()

with app.app_context():
    r = client.post('/auth/login', data={
        'email': 'admin@demo.local', 'password': 'Admin@12345'
    }, follow_redirects=False)
    assert r.status_code == 302, f"Login failed: {r.status_code}"

get_routes = [
    '/admin/',
    '/admin/voters',
    '/admin/voter/add',
    '/admin/voter/2',
    '/admin/voter/2/edit',
    '/admin/applications',
    '/admin/elections',
    '/admin/election/create',
    '/admin/election/1/edit',
    '/admin/election/1/candidates',
    '/admin/candidate/1/edit',
    '/admin/polling-stations',
    '/admin/polling-station/add',
    '/admin/grievances',
    '/admin/audit-logs',
    '/admin/reports',
    '/admin/reports/export/voters',
    '/admin/reports/export/elections',
    '/admin/reports/export/votes',
    '/admin/notifications',
    '/admin/settings',
    '/admin/votes',
    '/admin/results',
]

failures = []
for url in get_routes:
    with app.app_context():
        r = client.get(url, follow_redirects=True)
        data = r.data.decode('utf-8', errors='replace')
        has_traceback = 'Traceback' in data or 'Internal Server Error' in data
        if r.status_code != 200 or has_traceback:
            failures.append((url, r.status_code, 'TRACEBACK' if has_traceback else ''))
        else:
            print(f"  OK  {r.status_code} {url}")

if failures:
    print()
    print("  FAILURES:")
    for url, status, extra in failures:
        print(f"    FAIL {status} {url} {extra}")
else:
    print(f"\n  All {len(get_routes)} GET routes pass!")

# ── Step 4: Test key POST routes ────────────────────────────
print()
print("=" * 70)
print("STEP 4: Testing key POST routes")
print("=" * 70)

post_tests = [
    ('/admin/election/1/activate', {}, 'activate_election'),
    ('/admin/election/1/close', {}, 'close_election'),
    ('/admin/election/create', {
        'name': 'Test Post Election', 'description': 'Test', 'election_type': 'Test',
        'constituency': 'All', 'start_time': '2026-10-01T09:00', 'end_time': '2026-10-07T17:00',
    }, 'create_election'),
    ('/admin/election/1/add-candidate', {
        'name': 'Test Post Candidate', 'party_name': 'Post Party', 'symbol': 'Z', 'description': 'Test',
    }, 'add_candidate'),
    ('/admin/candidate/1/edit', {
        'name': 'Updated Candidate', 'party_name': 'Party A', 'symbol': 'Star', 'description': 'Updated',
    }, 'edit_candidate'),
    ('/admin/voter/add', {
        'name': 'Post Test', 'email': 'posttest@demo.local', 'mobile': '8888888888',
        'password': 'TestPass@123', 'dob': '2003-06-15', 'gender': 'Male',
        'address': '123 St', 'state': 'Maharashtra', 'district': 'Pune',
        'constituency': 'Test', 'pincode': '411001', 'role': 'VOTER',
    }, 'add_voter'),
    ('/admin/voter/2/edit', {
        'name': 'Edited', 'email': 'voter@demo.local', 'mobile': '9100000001',
        'status': 'active', 'dob': '2004-05-15', 'gender': 'Male',
        'address': '123 St', 'state': 'Maharashtra', 'district': 'Akola',
        'constituency': 'Test', 'pincode': '444001', 'role': 'VOTER',
    }, 'edit_voter'),
    ('/admin/polling-station/add', {
        'name': 'Post Station', 'address': '123 Post St', 'state': 'Maharashtra',
        'district': 'Pune', 'constituency': 'Post', 'booth_number': '99',
        'capacity': 300, 'accessibility': 'Ramp', 'facilities': 'Water',
    }, 'add_station'),
    ('/admin/grievance/1/update', {'status': 'In Progress'}, 'update_grievance'),
    ('/admin/settings', {'site_name': 'Demo Portal'}, 'update_settings'),
]

post_failures = []
for url, data, name in post_tests:
    with app.app_context():
        r = client.post(url, data=data, follow_redirects=True)
        resp = r.data.decode('utf-8', errors='replace')
        has_traceback = 'Traceback' in resp or 'Internal Server Error' in resp
        if r.status_code not in (200, 302) or has_traceback:
            post_failures.append((name, url, r.status_code, 'TRACEBACK' if has_traceback else ''))
        else:
            print(f"  OK  {r.status_code} POST {name:30s} {url}")

if post_failures:
    print()
    print("  FAILURES:")
    for name, url, status, extra in post_failures:
        print(f"    FAIL {status} POST {name:30s} {url} {extra}")
else:
    print(f"\n  All {len(post_tests)} POST routes pass!")

# ── Summary ─────────────────────────────────────────────────
print()
print("=" * 70)
total_get = len(get_routes)
total_post = len(post_tests)
total_ok = total_get + total_post - len(failures) - len(post_failures)
total = total_get + total_post
print(f"RESULTS: {total_ok}/{total} routes OK")
if failures or post_failures:
    print(f"  {len(failures)} GET failures, {len(post_failures)} POST failures")
else:
    print("  All routes and templates pass!")
print("=" * 70)
