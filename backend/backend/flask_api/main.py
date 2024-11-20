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

    # Apply CORS configuration only once
    CORS(flask_app, supports_credentials=True, resources={
        r"/pipeline-api/*": {
            "origins": ["http://localhost:3000", "http://localhost:3001"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    })

    @flask_app.route('/pipeline-api/<path:path>', methods=['OPTIONS'])
    def handle_preflight(path):
        response = jsonify({'status': 'Preflight request'})
        response.status_code = 200
        return response

    return flask_app

if __name__ == '__main__':
    configure_logging()
    app = create_flask_app()
    app.run(debug=True)
