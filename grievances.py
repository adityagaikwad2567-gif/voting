from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services.db_operations import (
    create_grievance, get_grievance_by_ref, get_user_grievances
)
from app.utils.helpers import log_user_action

grievances_bp = Blueprint('grievances', __name__)


@grievances_bp.route('/')
@login_required
def index():
    """Grievance hub."""
    grievances = get_user_grievances(current_user.id)
    return render_template('grievances/index.html', grievances=grievances)


@grievances_bp.route('/submit', methods=['GET', 'POST'])
@login_required
def submit():
    """Submit a new grievance."""
    if request.method == 'POST':
        category = request.form.get('category', '')
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        contact_info = request.form.get('contact_info', '').strip()
        
        if not category or not subject or not description:
            flash('Please fill all required fields.', 'warning')
            return render_template('grievances/submit.html')
        
        grievance_id, ref_number = create_grievance(
            current_user.id, category, subject, description, contact_info
        )
        
        log_user_action(current_user.id, 'GRIEVANCE_SUBMITTED', 'grievance', grievance_id)
        
        return render_template('grievances/success.html', reference_number=ref_number)
    
    return render_template('grievances/submit.html')


@grievances_bp.route('/track', methods=['GET', 'POST'])
def track():
    """Track grievance by reference number."""
    grievance = None
    if request.method == 'POST':
        ref_number = request.form.get('reference_number', '').strip()
        if ref_number:
            grievance = get_grievance_by_ref(ref_number)
            if not grievance:
                flash('Grievance not found. Please check your reference number.', 'warning')
        else:
            flash('Please enter a reference number.', 'warning')
    
    return render_template('grievances/track.html', grievance=grievance)
