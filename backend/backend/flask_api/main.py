"""
Main application file for the data pipeline API.

This file serves as the entry point for the Flask application.
It creates and runs the application instance.
"""

import os
from flask_cors import CORS
from backend.flask_api.app import create_app
import logging
from flask import Flask, jsonify

def configure_logging():
    """
    Configure logging for the application.

    This function sets up both console and file-based logging.
    """
    handler = logging.StreamHandler()
    file_handler = logging.FileHandler('app.log')

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    app_logger = logging.getLogger(__name__)
    app_logger.addHandler(handler)
    app_logger.addHandler(file_handler)

    app_logger.setLevel(logging.INFO)

def create_flask_app():
    """
    Create and configure the Flask application instance.

    Returns:
        Flask: The configured Flask application instance.
    """
    env = os.getenv('FLASK_ENV', 'development')
    flask_app = create_app(env)

    # More comprehensive CORS configuration
    CORS(flask_app,
         supports_credentials=True,
         expose_headers=['Cache-Control', 'Content-Type'],
         resources={
        r"/pipeline-api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            # Include all potential headers
            "allow_headers": [
                "Content-Type",
                "Authorization",
                "X-Requested-With",
                "Accept",
                "Origin",
                "Cache-Control"
            ],
        }
    })

    # Explicit preflight handler
    @flask_app.route('/pipeline-api/<path:path>', methods=['OPTIONS'])
    def handle_preflight(path):
        response = jsonify({'status': 'Preflight request'})
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = (
            'Content-Type, Authorization, X-Requested-With, '
            'Accept, Origin, Cache-Control'
        )
        response.headers['Access-Control-Max-Age'] = '3600'
        response.status_code = 200
        return response

    return flask_app

if __name__ == '__main__':
    configure_logging()
    app = create_flask_app()
    app.run(debug=True)
