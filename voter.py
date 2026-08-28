from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services.db_operations import (
    create_application, get_application_by_ref, get_user_applications,
    create_voter_profile, get_voter_profile, get_voter_profile_with_user,
    search_voters, get_user_by_voter_id, get_polling_station
)
from app.utils.helpers import log_user_action

voter_bp = Blueprint('voter', __name__)


@voter_bp.route('/dashboard')
@login_required
def dashboard():
    """Voter dashboard."""
    profile = get_voter_profile_with_user(current_user.id)
    applications = get_user_applications(current_user.id)
    
    from app.services.db_operations import get_active_elections, get_elections
    active_elections = get_active_elections()
    upcoming = [e for e in get_elections('Upcoming')]
    completed = [e for e in get_elections('Completed')]
    
    from app.services.db_operations import get_voter_vote_history
    vote_history = get_voter_vote_history(current_user.id)
    
    return render_template('voter/dashboard.html',
                           profile=profile,
                           applications=applications,
                           active_elections=active_elections,
                           upcoming_elections=upcoming,
                           completed_elections=completed,
                           vote_history=vote_history)


@voter_bp.route('/profile')
@login_required
def profile():
    """View voter profile."""
    profile = get_voter_profile_with_user(current_user.id)
    applications = get_user_applications(current_user.id)
    return render_template('voter/profile.html', profile=profile, applications=applications)


@voter_bp.route('/register-new', methods=['GET', 'POST'])
def new_registration():
    """New voter registration (multi-step form)."""
    if request.method == 'POST':
        step = request.form.get('step', '1')
        
        # Store form data in session
        if 'reg_data' not in request.session:
            request.session['reg_data'] = {}
        
        reg_data = request.session.get('reg_data', {})
        
        if step == '1':  # Personal Info
            reg_data['full_name'] = request.form.get('full_name', '').strip()
            reg_data['dob'] = request.form.get('dob', '')
            reg_data['gender'] = request.form.get('gender', '')
            request.session['reg_data'] = reg_data
            return render_template('voter/registration_step2.html', data=reg_data)
        
        elif step == '2':  # Contact Info
            reg_data['mobile'] = request.form.get('mobile', '').strip()
            reg_data['email'] = request.form.get('email', '').strip()
            request.session['reg_data'] = reg_data
            return render_template('voter/registration_step3.html', data=reg_data)
        
        elif step == '3':  # Address
            reg_data['address'] = request.form.get('address', '').strip()
            reg_data['state'] = request.form.get('state', '')
            reg_data['district'] = request.form.get('district', '')
            reg_data['constituency'] = request.form.get('constituency', '')
            reg_data['pincode'] = request.form.get('pincode', '').strip()
            request.session['reg_data'] = reg_data
            return render_template('voter/registration_step4.html', data=reg_data)
        
        elif step == '4':  # Identity & Declaration
            reg_data['id_type'] = request.form.get('id_type', '')
            reg_data['id_number'] = request.form.get('id_number', '').strip()
            reg_data['declaration'] = request.form.get('declaration', '')
            request.session['reg_data'] = reg_data
            
            # Create application
            user_id = current_user.id if current_user.is_authenticated else None
            
            # If not logged in, create a user account first
            if not user_id:
                from app.services.db_operations import create_user, get_user_by_email
                if get_user_by_email(reg_data.get('email', '')):
                    flash('Email already registered. Please login.', 'warning')
                    return redirect(url_for('auth.login'))
                
                temp_password = reg_data.get('dob', '2000-01-01').replace('-', '')
                user_id = create_user(
                    reg_data.get('full_name', ''),
                    reg_data.get('email', ''),
                    reg_data.get('mobile', ''),
                    f'Demo@{temp_password}',
                    role='VOTER'
                )
            
            # Create profile
            create_voter_profile(
                user_id,
                reg_data.get('dob'),
                reg_data.get('gender'),
                reg_data.get('address'),
                reg_data.get('state'),
                reg_data.get('district'),
                reg_data.get('constituency'),
                reg_data.get('pincode')
            )
            
            # Create application
            app_id, ref_number = create_application(
                user_id, 'new_registration',
                remarks=f"New registration for {reg_data.get('full_name', '')}"
            )
            
            log_user_action(user_id, 'APPLICATION_SUBMITTED', 'application', app_id)
            
            # Clear session data
            request.session.pop('reg_data', None)
            
            return render_template('voter/registration_success.html',
                                   reference_number=ref_number,
                                   data=reg_data)
    
    return render_template('voter/registration_step1.html')


@voter_bp.route('/search', methods=['GET', 'POST'])
def search_electoral_roll():
    """Search electoral roll demo data."""
    results = []
    search_performed = False
    
    if request.method == 'POST':
        search_performed = True
        search_type = request.form.get('search_type', 'details')
        
        if search_type == 'details':
            results = search_voters(
                name=request.form.get('name', '').strip() or None,
                state=request.form.get('state', '').strip() or None,
                district=request.form.get('district', '').strip() or None,
                constituency=request.form.get('constituency', '').strip() or None,
                age=request.form.get('age', '').strip() or None,
            )
        elif search_type == 'voter_id':
            voter_id = request.form.get('voter_id', '').strip()
            if voter_id:
                results = search_voters(voter_id=voter_id)
        elif search_type == 'mobile':
            mobile = request.form.get('mobile', '').strip()
            if mobile:
                results = search_voters(mobile=mobile)
        
        if not results:
            flash('No matching records found.', 'info')
    
    return render_template('voter/search.html', results=results, search_performed=search_performed)


@voter_bp.route('/polling-station', methods=['GET', 'POST'])
def polling_station_search():
    """Find polling station."""
    stations = []
    search_performed = False
    
    if request.method == 'POST':
        search_performed = True
        voter_id = request.form.get('voter_id', '').strip()
        name = request.form.get('name', '').strip()
        district = request.form.get('district', '').strip()
        constituency = request.form.get('constituency', '').strip()
        
        from app.services.db_operations import search_polling_station
        stations = search_polling_station(
            voter_id=voter_id or None,
            name=name or None,
            district=district or None,
            constituency=constituency or None
        )
        
        if not stations:
            flash('No matching polling stations found.', 'info')
    
    return render_template('voter/polling_station.html', stations=stations, search_performed=search_performed)


@voter_bp.route('/digital-card')
@login_required
def digital_card():
    """Digital voter card."""
    profile = get_voter_profile_with_user(current_user.id)
    if not profile:
        flash('Please complete your voter profile first.', 'warning')
        return redirect(url_for('voter.dashboard'))
    
    # Generate QR data (safe demo identifier)
    qr_data = f"DEMO-VOTER-{profile.get('voter_id', current_user.id)}"
    
    return render_template('voter/digital_card.html', profile=profile, qr_data=qr_data)


@voter_bp.route('/update', methods=['GET', 'POST'])
@login_required
def update_correction():
    """Update/correction request."""
    if request.method == 'POST':
        correction_type = request.form.get('correction_type', '')
        current_value = request.form.get('current_value', '').strip()
        new_value = request.form.get('new_value', '').strip()
        reason = request.form.get('reason', '').strip()
        
        if not correction_type or not new_value:
            flash('Please fill all required fields.', 'warning')
            return render_template('voter/update_correction.html')
        
        app_id, ref_number = create_application(
            current_user.id, 'correction',
            remarks=f"Correction request: {correction_type}. Current: {current_value}, New: {new_value}. Reason: {reason}"
        )
        
        log_user_action(current_user.id, 'CORRECTION_SUBMITTED', 'application', app_id)
        
        return render_template('voter/correction_success.html', reference_number=ref_number,
                               correction_type=correction_type)
    
    return render_template('voter/update_correction.html')


@voter_bp.route('/transfer', methods=['GET', 'POST'])
@login_required
def address_transfer():
    """Address transfer request."""
    if request.method == 'POST':
        new_address = request.form.get('new_address', '').strip()
        new_state = request.form.get('new_state', '')
        new_district = request.form.get('new_district', '')
        new_constituency = request.form.get('new_constituency', '')
        new_pincode = request.form.get('new_pincode', '').strip()
        reason = request.form.get('reason', '').strip()
        
        if not new_address or not new_district:
            flash('Please fill all required fields.', 'warning')
            return render_template('voter/address_transfer.html')
        
        remarks = (f"Address transfer: New Address: {new_address}, "
                   f"State: {new_state}, District: {new_district}, "
                   f"Constituency: {new_constituency}, Pincode: {new_pincode}. "
                   f"Reason: {reason}")
        
        app_id, ref_number = create_application(
            current_user.id, 'address_transfer', remarks=remarks
        )
        
        log_user_action(current_user.id, 'ADDRESS_TRANSFER_SUBMITTED', 'application', app_id)
        
        return render_template('voter/transfer_success.html', reference_number=ref_number)
    
    profile = get_voter_profile(current_user.id)
    return render_template('voter/address_transfer.html', profile=profile)


@voter_bp.route('/track-application', methods=['GET', 'POST'])
def track_application():
    """Track application status."""
    application = None
    if request.method == 'POST':
        ref_number = request.form.get('reference_number', '').strip()
        if ref_number:
            application = get_application_by_ref(ref_number)
            if not application:
                flash('Application not found. Please check your reference number.', 'warning')
        else:
            flash('Please enter a reference number.', 'warning')
    
    return render_template('voter/track_application.html', application=application)


@voter_bp.route('/eligibility', methods=['GET', 'POST'])
def eligibility_checker():
    """Eligibility checker."""
    result = None
    if request.method == 'POST':
        dob = request.form.get('dob', '')
        citizenship = request.form.get('citizenship', '')
        existing = request.form.get('existing_registration', '')
        residence = request.form.get('residence', '')
        
        eligible = True
        reasons = []
        
        if not dob:
            eligible = False
            reasons.append('Date of birth is required.')
        
        if citizenship != 'yes':
            eligible = False
            reasons.append('Citizenship declaration is required.')
        
        if existing == 'yes':
            reasons.append('You may already be registered. Please search the electoral roll.')
        
        if not residence:
            eligible = False
            reasons.append('Residence information is required.')
        
        result = {
            'eligible': eligible,
            'reasons': reasons if reasons else ['You appear to be eligible for voter registration.']
        }
    
    return render_template('voter/eligibility.html', result=result)
