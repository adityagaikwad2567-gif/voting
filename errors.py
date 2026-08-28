from flask import render_template


def register_error_handlers(app):
    """Register error handlers for the application."""
    
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(401)
    def unauthorized(e):
        return render_template('errors/401.html'), 401
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(429)
    def rate_limited(e):
        return render_template('errors/429.html'), 429
    
    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500
