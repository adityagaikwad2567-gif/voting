import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DATABASE_HOST = os.environ.get('DATABASE_HOST', 'localhost')
    DATABASE_USER = os.environ.get('DATABASE_USER', 'root')
    DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD', 'root')
    DATABASE_NAME = os.environ.get('DATABASE_NAME', 'digital_voter_portal')
    DATABASE_PORT = int(os.environ.get('DATABASE_PORT', 3306))
    SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 30))
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    APPLICATION_NAME = 'Digital Voter Services Portal'
    ACADEMIC_DISCLAIMER = 'Academic Demonstration Project — Not an Official Government Website'
