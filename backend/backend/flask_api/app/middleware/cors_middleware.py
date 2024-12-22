# flask_api/app/middleware/cors_middleware.py

from functools import wraps
from flask import request

def handle_options_requests(app):
    """Middleware to handle OPTIONS requests properly"""
    
    @app.before_request
    def before_request():
        if request.method == 'OPTIONS':
            # Don't redirect OPTIONS requests
            return '', 200

    return app