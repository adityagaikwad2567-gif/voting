from flask_login import UserMixin
from app.services.db_operations import get_user_by_id


class User(UserMixin):
    """User model for Flask-Login."""
    
    def __init__(self, user_data):
        self.id = user_data['id']
        self.name = user_data['name']
        self.email = user_data['email']
        self.mobile = user_data.get('mobile')
        self.voter_id = user_data.get('voter_id')
        self.role = user_data['role']
        self.status = user_data['status']
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')
    
    @staticmethod
    def get(user_id):
        """Load user by ID for Flask-Login."""
        user_data = get_user_by_id(user_id)
        if user_data:
            return User(user_data)
        return None
