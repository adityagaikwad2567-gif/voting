from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash
from app.services.db_operations import (
    create_user, get_user_by_email, verify_password, update_user_last_login, get_user_by_id
)
from app.utils.helpers import log_user_action
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

login_manager = LoginManager()


def init_login_manager(app):
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    login_manager.user_loader(User.get)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Please enter email and password.', 'warning')
            return render_template('auth/login.html')
        
        user_data = get_user_by_email(email)
        if user_data and verify_password(user_data, password):
            user = User(user_data)
            if user.status != 'active':
                flash('Your account has been suspended. Please contact support.', 'danger')
                return render_template('auth/login.html')
            
            login_user(user, remember=bool(remember))
            update_user_last_login(user.id)
            log_user_action(user.id, 'LOGIN', 'user', user.id)
            
            flash(f'Welcome back, {user.name}!', 'success')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.role == 'ADMIN':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('voter.dashboard'))
        
        flash('Invalid email or password.', 'danger')
        log_user_action(None, 'LOGIN_FAILED', 'user', None)
    
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        mobile = request.form.get('mobile', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        errors = []
        if not name or len(name) < 2:
            errors.append('Name must be at least 2 characters.')
        if not email or '@' not in email:
            errors.append('Please enter a valid email address.')
        if not mobile or len(mobile) < 10:
            errors.append('Please enter a valid mobile number (10+ digits).')
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if get_user_by_email(email):
            errors.append('Email already registered.')
        
        if errors:
            for e in errors:
                flash(e, 'warning')
            return render_template('auth/register.html', name=name, email=email, mobile=mobile)
        
        user_id = create_user(name, email, mobile, password, role='VOTER')
        if user_id:
            log_user_action(user_id, 'REGISTER', 'user', user_id)
            flash('Registration successful! Please login with your credentials.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    log_user_action(current_user.id, 'LOGOUT', 'user', current_user.id)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))
