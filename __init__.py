from flask import Flask
from flask_wtf.csrf import CSRFProtect
from config import Config
import os
import datetime


csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(Config)
    
    # Initialize CSRF
    csrf.init_app(app)
    
    # Ensure upload folder exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'static/uploads'), exist_ok=True)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.voter import voter_bp
    from app.routes.elections import elections_bp
    from app.routes.voting import voting_bp
    from app.routes.grievances import grievances_bp
    from app.routes.info import info_bp
    from app.routes.admin import admin_bp
    from app.routes.main import main_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(voter_bp, url_prefix='/voter')
    app.register_blueprint(elections_bp, url_prefix='/elections')
    app.register_blueprint(voting_bp, url_prefix='/voting')
    app.register_blueprint(grievances_bp, url_prefix='/grievances')
    app.register_blueprint(info_bp, url_prefix='/info')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Register error handlers
    from app.routes.errors import register_error_handlers
    register_error_handlers(app)
    
    # Template context processor
    from app.services.db_operations import get_unread_notification_count
    from flask_login import current_user
    
    @app.context_processor
    def inject_globals():
        notif_count = 0
        try:
            if current_user.is_authenticated:
                notif_count = get_unread_notification_count(current_user.id)
        except:
            pass
        return {
            'academic_disclaimer': Config.ACADEMIC_DISCLAIMER,
            'unread_notifications': notif_count
        }
    
    # Register translations
    from app.utils.translations import get_translation
    app.jinja_env.globals.update(get_translation=get_translation)
    
    # Jinja2 filter: format date regardless of whether it's str or datetime
    def format_date(value, fmt='%d %b %Y'):
        if value is None:
            return 'N/A'
        if isinstance(value, str):
            # Try to parse the string to a datetime, then format
            for pattern in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                try:
                    value = datetime.datetime.strptime(value, pattern)
                    break
                except ValueError:
                    continue
            else:
                return value  # can't parse, return raw string
        if isinstance(value, datetime.datetime):
            return value.strftime(fmt)
        if isinstance(value, datetime.date):
            return value.strftime(fmt)
        return str(value)
    
    app.jinja_env.filters['format_date'] = format_date
    
    return app
