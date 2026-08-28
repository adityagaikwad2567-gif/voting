import os
import secrets
import string
from functools import wraps
from flask import session, redirect, url_for, flash, request
from app.services.db_operations import get_user_by_id, log_audit
from werkzeug.utils import secure_filename


def login_required(f):
    """Decorator to require login."""
    from flask_login import login_required as flask_login_required
    return flask_login_required(f)


def admin_required(f):
    """Decorator to require admin role."""
    from flask_login import login_required, current_user
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'ADMIN':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


def official_required(f):
    """Decorator to require election official or admin role."""
    from flask_login import login_required, current_user
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role not in ('ADMIN', 'ELECTION_OFFICIAL'):
            flash('Access denied. Official privileges required.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


def generate_reference_number(prefix, count):
    """Generate a formatted reference number."""
    import datetime
    year = datetime.datetime.now().year
    return f"DEMO-{year}-{prefix}{str(count).zfill(6)}"


def allowed_file(filename, allowed_extensions=None):
    """Check if file extension is allowed."""
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_client_ip():
    """Get client IP address."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    return request.remote_addr


def mask_mobile(mobile):
    """Mask mobile number for display."""
    if mobile and len(mobile) >= 10:
        return mobile[:3] + '****' + mobile[-3:]
    return '****'


def log_user_action(user_id, action, entity, entity_id=None):
    """Log a user action to audit log."""
    ip = get_client_ip()
    log_audit(user_id, action, entity, entity_id, ip)
