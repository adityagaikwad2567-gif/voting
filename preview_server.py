"""Preview server — uses SQLite backend so the UI renders without MySQL."""
import os, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Force SQLite backend by making MySQL unavailable in Config
os.environ['DATABASE_HOST'] = 'localhost'
os.environ['DATABASE_PORT'] = '9999'  # Wrong port so MySQL probe fails

from app import create_app
from app.routes.auth import init_login_manager

app = create_app()
init_login_manager(app)

if __name__ == '__main__':
    print("Preview server starting on http://127.0.0.1:5000")
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
