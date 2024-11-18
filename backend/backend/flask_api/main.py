"""
Main application file for the data pipeline API.

This file serves as the entry point for the Flask application.
It creates and runs the application instance.
"""

import os
from flask_cors import CORS
from backend.flask_api.app import create_app

def configure_logging():
    """
    Configure logging for the application.

    This function sets up both console and file-based logging.
    """
    import logging
    from flask import Flask

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

    CORS(flask_app, supports_credentials=True, resources={
        r"/file-system/*": {
            "origins": ["http://localhost:3000", "http://localhost:3001"],
            "methods": ["POST", "OPTIONS", "GET"],
            "allow_headers": ["Content-Type"],
        },
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:3001"],
            "methods": ["POST", "OPTIONS", "GET"],
            "allow_headers": ["Content-Type"],
        }
    })

    return flask_app

if __name__ == '__main__':
    configure_logging()
    create_flask_app().run(debug=True)
