from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
from app.services.db_operations import (
    get_dashboard_stats, get_registration_trend, get_application_status_counts,
    get_application_type_counts, get_all_voters, update_voter_status, get_voter_profile_with_user,
    get_all_applications, update_application_status, get_user_applications,
    create_election as db_create_election, get_elections, get_election, update_election, update_election_status, delete_election,
    create_candidate, get_all_candidates, get_candidate, update_candidate, delete_candidate, get_candidates_for_election,
    get_all_polling_stations, create_polling_station, update_polling_station, delete_polling_station,
    get_all_grievances, update_grievance_status,
    get_audit_logs, get_user_notifications, mark_notification_read, create_notification, create_user, get_user_by_email,
    get_total_voters, get_total_votes, get_votes_by_election,
)
from app.utils.helpers import log_user_action
from werkzeug.security import generate_password_hash
import csv, io
from functools import wraps

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'ADMIN':
            flash('Access denied.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated


# ─── Dashboard ───────────────────────────────────────────────
@admin_bp.route('/')
@admin_required
def dashboard():
    stats = get_dashboard_stats()
    trend = get_registration_trend()
    app_status = get_application_status_counts()
    votes_data = get_votes_by_election()
    from datetime import datetime
    now = datetime.now()

    # Recent apps and logs
    recent_apps_list, _ = get_all_applications(per_page=5)
    recent_logs_list, _ = get_audit_logs(per_page=5)

    return render_template('admin/dashboard.html',
                           stats=stats, trend=trend, app_status=app_status,
                           votes_data=votes_data, now=now,
                           recent_apps=recent_apps_list, recent_logs=recent_logs_list)


# ─── Voter Management ───────────────────────────────────────
@admin_bp.route('/voters')
@admin_required
def voters():
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    voter_list, total = get_all_voters(per_page=100, search=search or None)
    return render_template('admin/voters.html', voters=voter_list, search=search)


@admin_bp.route('/voter/add', methods=['GET', 'POST'])
@admin_required
def add_voter():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        mobile = request.form.get('mobile', '').strip()
        password = request.form.get('password', '')
        dob = request.form.get('dob', '')
        gender = request.form.get('gender', '')
        address = request.form.get('address', '')
        state = request.form.get('state', '')
        district = request.form.get('district', '')
        constituency = request.form.get('constituency', '')
        pincode = request.form.get('pincode', '')
        role = request.form.get('role', 'voter').upper()

        if not name or not email or not password:
            flash('Name, email, and password are required.', 'warning')
            return render_template('admin/add_voter.html')

        if get_user_by_email(email):
            flash('Email already registered.', 'warning')
            return render_template('admin/add_voter.html')

        user_id = create_user(name, email, mobile, password, role=role)
        if user_id:
            from app.services.db_operations import create_voter_profile
            create_voter_profile(user_id, dob, gender, address, state, district, constituency, pincode)
            log_user_action(current_user.id, 'VOTER_ADDED', 'user', user_id)
            flash(f'Voter "{name}" created successfully.', 'success')
            return redirect(url_for('admin.voters'))
        else:
            flash('Failed to create voter.', 'danger')
    return render_template('admin/add_voter.html')


@admin_bp.route('/voter/<int:user_id>')
@admin_required
def view_voter(user_id):
    profile = get_voter_profile_with_user(user_id)
    if not profile:
        flash('Voter not found.', 'warning')
        return redirect(url_for('admin.voters'))
    applications = get_user_applications(user_id)
    return render_template('admin/view_voter.html', voter=profile, applications=applications)


@admin_bp.route('/voter/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_voter(user_id):
    profile = get_voter_profile_with_user(user_id)
    if not profile:
        flash('Voter not found.', 'warning')
        return redirect(url_for('admin.voters'))
    if request.method == 'POST':
        # Update user fields
        from app.services.db_operations import update_voter_profile
        update_voter_profile(user_id, {
            'name': request.form.get('name', profile['name']),
            'email': request.form.get('email', profile['email']),
            'mobile': request.form.get('mobile', profile.get('mobile', '')),
            'dob': request.form.get('dob', ''),
            'gender': request.form.get('gender', ''),
            'address': request.form.get('address', ''),
            'state': request.form.get('state', ''),
            'district': request.form.get('district', ''),
            'constituency': request.form.get('constituency', ''),
            'pincode': request.form.get('pincode', ''),
            'role': request.form.get('role', profile['role']),
            'status': request.form.get('status', profile['status']),
        })
        log_user_action(current_user.id, 'VOTER_UPDATED', 'user', user_id)
        flash('Voter updated successfully.', 'success')
        return redirect(url_for('admin.view_voter', user_id=user_id))
    return render_template('admin/edit_voter.html', voter=profile)


@admin_bp.route('/voter/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def deactivate_voter(user_id):
    profile = get_voter_profile_with_user(user_id)
    if profile:
        new_status = 'inactive' if profile['status'] == 'active' else 'active'
        update_voter_status(user_id, new_status)
        log_user_action(current_user.id, f'VOTER_STATUS_CHANGED_{new_status.upper()}', 'user', user_id)
        flash(f'Voter status updated to {new_status}.', 'success')
    return redirect(url_for('admin.voters'))


# ─── Application Management ─────────────────────────────────
@admin_bp.route('/applications')
@admin_required
def applications():
    status_filter = request.args.get('status', '').strip()
    type_filter = request.args.get('type', '').strip()
    app_list, total = get_all_applications(per_page=50, status=status_filter or None, app_type=type_filter or None)
    return render_template('admin/applications.html', applications=app_list)


@admin_bp.route('/application/<int:app_id>/approve', methods=['POST'])
@admin_required
def approve_application(app_id):
    update_application_status(app_id, 'Approved', 'Approved by admin')
    log_user_action(current_user.id, 'APPLICATION_APPROVED', 'application', app_id)
    flash('Application approved.', 'success')
    return redirect(url_for('admin.applications'))


@admin_bp.route('/application/<int:app_id>/reject', methods=['POST'])
@admin_required
def reject_application(app_id):
    update_application_status(app_id, 'Rejected', 'Rejected by admin')
    log_user_action(current_user.id, 'APPLICATION_REJECTED', 'application', app_id)
    flash('Application rejected.', 'danger')
    return redirect(url_for('admin.applications'))


@admin_bp.route('/application/<int:app_id>/request-info', methods=['POST'])
@admin_required
def request_info(app_id):
    remarks = request.form.get('remarks', '').strip()
    update_application_status(app_id, 'Under Review', remarks or 'More information requested')
    log_user_action(current_user.id, 'APPLICATION_INFO_REQUESTED', 'application', app_id)
    flash('Information request sent.', 'info')
    return redirect(url_for('admin.applications'))


# ─── Election Management ────────────────────────────────────
@admin_bp.route('/elections')
@admin_required
def elections_list():
    all_elections = get_elections()
    return render_template('admin/elections.html', elections=all_elections)


@admin_bp.route('/election/create', methods=['GET', 'POST'])
@admin_required
def create_election():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        election_type = request.form.get('election_type', '').strip()
        constituency = request.form.get('constituency', '').strip()
        start_time = request.form.get('start_time', '')
        end_time = request.form.get('end_time', '')
        status = request.form.get('status', 'Draft')

        if not name or not start_time or not end_time:
            flash('Please fill all required fields.', 'warning')
            return render_template('admin/create_election.html')

        election_id = db_create_election(name, description, election_type, constituency, start_time, end_time)
        if status and status != 'Draft':
            update_election_status(election_id, status)
        log_user_action(current_user.id, 'ELECTION_CREATED', 'election', election_id)
        flash('Election created successfully.', 'success')
        return redirect(url_for('admin.elections_list'))
    return render_template('admin/create_election.html')


@admin_bp.route('/election/<int:election_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_election(election_id):
    election = get_election(election_id)
    if not election:
        flash('Election not found.', 'warning')
        return redirect(url_for('admin.elections_list'))
    if request.method == 'POST':
        update_election(
            election_id,
            request.form.get('name', ''),
            request.form.get('description', ''),
            request.form.get('election_type', ''),
            request.form.get('constituency', ''),
            request.form.get('start_time', ''),
            request.form.get('end_time', ''),
            request.form.get('status', election['status']),
        )
        log_user_action(current_user.id, 'ELECTION_UPDATED', 'election', election_id)
        flash('Election updated successfully.', 'success')
        return redirect(url_for('admin.elections_list'))
    return render_template('admin/edit_election.html', election=election)


@admin_bp.route('/election/<int:election_id>/activate', methods=['POST'])
@admin_required
def activate_election(election_id):
    election = get_election(election_id)
    if election:
        new_status = 'Active' if election['status'] in ('Draft', 'Upcoming') else election['status']
        update_election_status(election_id, new_status)
        log_user_action(current_user.id, 'ELECTION_ACTIVATED', 'election', election_id)
        flash(f'Election activated.', 'success')
    return redirect(url_for('admin.elections_list'))


@admin_bp.route('/election/<int:election_id>/close', methods=['POST'])
@admin_required
def close_election(election_id):
    election = get_election(election_id)
    if election:
        update_election_status(election_id, 'Completed')
        log_user_action(current_user.id, 'ELECTION_COMPLETED', 'election', election_id)
        flash('Election closed. Results are now final.', 'success')
    return redirect(url_for('admin.elections_list'))


@admin_bp.route('/election/<int:election_id>/candidates')
@admin_required
def manage_candidates(election_id):
    election = get_election(election_id)
    if not election:
        flash('Election not found.', 'warning')
        return redirect(url_for('admin.elections_list'))
    candidates = get_candidates_for_election(election_id)
    return render_template('admin/manage_candidates.html', election=election, candidates=candidates)


@admin_bp.route('/election/<int:election_id>/add-candidate', methods=['POST'])
@admin_required
def add_candidate(election_id):
    name = request.form.get('name', '').strip()
    party_name = request.form.get('party_name', '').strip()
    symbol = request.form.get('symbol', '').strip()
    description = request.form.get('description', '').strip()
    if not name:
        flash('Candidate name is required.', 'warning')
        return redirect(url_for('admin.manage_candidates', election_id=election_id))
    candidate_id = create_candidate(election_id, name, party_name, symbol, description)
    log_user_action(current_user.id, 'CANDIDATE_ADDED', 'candidate', candidate_id)
    flash('Candidate added successfully.', 'success')
    return redirect(url_for('admin.manage_candidates', election_id=election_id))


@admin_bp.route('/candidate/<int:candidate_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_candidate(candidate_id):
    candidate = get_candidate(candidate_id)
    if not candidate:
        flash('Candidate not found.', 'warning')
        return redirect(url_for('admin.elections_list'))
    if request.method == 'POST':
        update_candidate(
            candidate_id,
            request.form.get('name', ''),
            request.form.get('party_name', ''),
            request.form.get('symbol', ''),
            request.form.get('description', ''),
        )
        log_user_action(current_user.id, 'CANDIDATE_UPDATED', 'candidate', candidate_id)
        flash('Candidate updated.', 'success')
        return redirect(url_for('admin.manage_candidates', election_id=candidate['election_id']))
    return render_template('admin/edit_candidate.html', candidate=candidate)


@admin_bp.route('/candidate/<int:candidate_id>/remove', methods=['POST'])
@admin_required
def remove_candidate(candidate_id):
    candidate = get_candidate(candidate_id)
    election_id = candidate['election_id'] if candidate else None
    delete_candidate(candidate_id)
    log_user_action(current_user.id, 'CANDIDATE_DELETED', 'candidate', candidate_id)
    flash('Candidate removed.', 'success')
    return redirect(url_for('admin.manage_candidates', election_id=election_id) if election_id else url_for('admin.elections_list'))


# ─── Polling Station Management ─────────────────────────────
@admin_bp.route('/polling-stations')
@admin_required
def polling_stations_list():
    stations, total = get_all_polling_stations(per_page=100)
    return render_template('admin/polling_stations.html', stations=stations)


@admin_bp.route('/polling-station/add', methods=['GET', 'POST'])
@admin_required
def add_polling_station():
    if request.method == 'POST':
        station_id = create_polling_station(
            request.form.get('name', ''),
            request.form.get('address', ''),
            request.form.get('state', ''),
            request.form.get('district', ''),
            request.form.get('constituency', ''),
            request.form.get('booth_number', ''),
            request.form.get('capacity', 500, type=int),
            request.form.get('accessibility', ''),
            request.form.get('facilities', ''),
        )
        log_user_action(current_user.id, 'POLLING_STATION_CREATED', 'polling_station', station_id)
        flash('Polling station created.', 'success')
        return redirect(url_for('admin.polling_stations_list'))
    return render_template('admin/add_polling_station.html')


@admin_bp.route('/polling-station/<int:station_id>/delete', methods=['POST'])
@admin_required
def remove_polling_station(station_id):
    delete_polling_station(station_id)
    log_user_action(current_user.id, 'POLLING_STATION_DELETED', 'polling_station', station_id)
    flash('Polling station deleted.', 'success')
    return redirect(url_for('admin.polling_stations_list'))


# ─── Grievance Management ───────────────────────────────────
@admin_bp.route('/grievances')
@admin_required
def grievances_list():
    status_filter = request.args.get('status', '').strip()
    grv_list, total = get_all_grievances(per_page=50, status=status_filter or None)
    return render_template('admin/grievances.html', grievances=grv_list)


@admin_bp.route('/grievance/<int:grievance_id>/update', methods=['POST'])
@admin_required
def update_grievance(grievance_id):
    new_status = request.form.get('status', '')
    if new_status:
        update_grievance_status(grievance_id, new_status)
        log_user_action(current_user.id, f'GRIEVANCE_{new_status.upper()}', 'grievance', grievance_id)
        flash(f'Grievance updated to {new_status}.', 'success')
    return redirect(url_for('admin.grievances_list'))


# ─── Notifications ──────────────────────────────────────────
@admin_bp.route('/notifications')
@admin_required
def notifications_list():
    notifications = get_user_notifications(current_user.id)
    return render_template('admin/notifications.html', notifications=notifications)


@admin_bp.route('/notification/<int:notif_id>/read', methods=['POST'])
@admin_required
def mark_read(notif_id):
    from app.services.db_operations import mark_notification_read
    mark_notification_read(notif_id, current_user.id)
    return redirect(url_for('admin.notifications_list'))


@admin_bp.route('/notifications/send', methods=['POST'])
@admin_required
def send_notification():
    user_id = request.form.get('user_id', type=int)
    title = request.form.get('title', '').strip()
    message = request.form.get('message', '').strip()
    if user_id and title and message:
        create_notification(user_id, title, message)
        log_user_action(current_user.id, 'NOTIFICATION_SENT', 'notification', user_id)
        flash('Notification sent.', 'success')
    else:
        flash('Please fill all fields.', 'warning')
    return redirect(url_for('admin.dashboard'))


# ─── Votes ──────────────────────────────────────────────────
@admin_bp.route('/votes')
@admin_required
def votes():
    from app.services.db_operations import get_all_votes
    vote_list = get_all_votes()
    return render_template('admin/votes.html', votes=vote_list)


# ─── Audit Logs ─────────────────────────────────────────────
@admin_bp.route('/audit-logs')
@admin_required
def audit_logs():
    search = request.args.get('search', '').strip()
    entity = request.args.get('entity', '').strip()
    logs, total = get_audit_logs(per_page=50, search=search or None, entity=entity or None)
    return render_template('admin/audit_logs.html', logs=logs)


# ─── Reports ────────────────────────────────────────────────
@admin_bp.route('/reports')
@admin_required
def reports():
    stats = get_dashboard_stats()
    return render_template('admin/reports.html', stats=stats)


@admin_bp.route('/reports/export/<report_type>')
@admin_required
def export_report(report_type):
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == 'voters':
        writer.writerow(['ID', 'Name', 'Email', 'Mobile', 'Voter ID', 'Role', 'Status', 'Created'])
        voters, _ = get_all_voters(per_page=10000)
        for v in voters:
            writer.writerow([v['id'], v['name'], v['email'], v.get('mobile', ''), v.get('voter_id', ''), v['role'], v['status'], v['created_at']])
    elif report_type == 'applications':
        writer.writerow(['ID', 'Reference', 'Type', 'Status', 'Submitted', 'Updated'])
        apps, _ = get_all_applications(per_page=10000)
        for a in apps:
            writer.writerow([a['id'], a['reference_number'], a['application_type'], a['status'], a['submitted_at'], a['updated_at']])
    elif report_type == 'elections':
        writer.writerow(['ID', 'Name', 'Type', 'Constituency', 'Start', 'End', 'Status'])
        elections = get_elections()
        for e in elections:
            writer.writerow([e['id'], e['name'], e['election_type'], e['constituency'], e['start_time'], e['end_time'], e['status']])
    elif report_type == 'results':
        writer.writerow(['Election', 'Candidate', 'Party', 'Votes'])
        from app.services.db_operations import get_all_votes
        votes = get_all_votes()
        for v in votes:
            writer.writerow([v.get('election_name', ''), v.get('voter_name', ''), '', ''])
    elif report_type == 'grievances':
        writer.writerow(['ID', 'Reference', 'Category', 'Subject', 'Status', 'Created'])
        grv, _ = get_all_grievances(per_page=10000)
        for g in grv:
            writer.writerow([g['id'], g['reference_number'], g['category'], g['subject'], g['status'], g['created_at']])
    elif report_type == 'audit':
        writer.writerow(['Date', 'Action', 'Entity', 'Entity ID', 'IP Address'])
        logs, _ = get_audit_logs_fn(per_page=10000)
        for log in logs:
            writer.writerow([log['created_at'], log['action'], log.get('entity', ''), log.get('entity_id', ''), log.get('ip_address', '')])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={report_type}_report.csv'}
    )


# ─── Results ────────────────────────────────────────────────
@admin_bp.route('/results')
@admin_required
def results():
    completed_elections = get_elections('Completed')
    results_data = []
    for election in completed_elections:
        from app.services.db_operations import get_election_results
        er = get_election_results(election['id'])
        if er:
            election_results = er.get('candidates', [])
            total_voters = get_total_voters()
            total_votes = er.get('total_votes', 0)
            turnout = round((total_votes / total_voters * 100) if total_voters > 0 else 0, 1)
            winner = er.get('winner', {})
            winner_name = winner['name'] if winner else 'N/A'
            results_data.append({
                **election,
                'results': election_results,
                'total_voters': total_voters,
                'total_votes': total_votes,
                'turnout': turnout,
                'winner': winner_name,
            })
    return render_template('admin/results.html', elections=results_data)


# ─── Settings ───────────────────────────────────────────────
@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        flash('Settings saved.', 'success')
        return redirect(url_for('admin.settings'))
    return render_template('admin/settings.html', settings={})
