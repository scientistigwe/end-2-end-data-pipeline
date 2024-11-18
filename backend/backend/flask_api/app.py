"""
Application factory function for creating Flask instances.

This module defines the create_app() function which returns an instance of
the Flask application.
"""

import os
from flask import Flask, Blueprint, jsonify
from backend.flask_api.bp_routes import file_system_bp
import logging

def create_app(config_name='default'):
    """
    Create and configure the Flask application instance.

    Args:
        config_name (str): Name of the configuration to use. Defaults to 'default'.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)

    # Set up basic logging to the terminal
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    # Ensure app logger inherits the basic configuration
    app.logger.setLevel(logging.INFO)

    # Configure the app (default settings; adjust as needed)
    if config_name == 'development':
        app.config['DEBUG'] = True
    else:
        app.config['DEBUG'] = False

    # Set configurations for file handling
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['ALLOWED_EXTENSIONS'] = {'csv', 'json', 'xlsx', 'parquet'}

    # Ensure upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Register blueprints
    app.register_blueprint(file_system_bp, url_prefix='/file-system')

    # Define a simple route for testing
    @app.route('/')
    def index():
        return "Welcome to the Data Pipeline API!"

    # Configure app logger
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # Add handler to Flask app logger
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    # Ensure logs are propagated
    app.logger.propagate = True

    return app

if __name__ == '__main__':
    create_app().run(debug=True)
