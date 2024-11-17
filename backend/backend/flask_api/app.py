from flask import Flask
from backend.backend.flask_api.bp_routes import file_system_bp
import os

def create_app(config_name='default'):
    """Application factory function to create and configure the Flask app."""
    flask_app = Flask(__name__)

    # Configure the app (default settings; adjust as needed)
    if config_name == 'development':
        flask_app.config['DEBUG'] = True
    else:
        flask_app.config['DEBUG'] = False

    # Set configurations for file handling
    flask_app.config['UPLOAD_FOLDER'] = 'uploads'
    flask_app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    flask_app.config['ALLOWED_EXTENSIONS'] = {'csv', 'json', 'xlsx', 'parquet'}

    # Ensure upload folder exists
    if not os.path.exists(flask_app.config['UPLOAD_FOLDER']):
        os.makedirs(flask_app.config['UPLOAD_FOLDER'])

    # Register blueprints
    flask_app.register_blueprint(file_system_bp, url_prefix='/file-system')

    # Define a simple route for testing
    @flask_app.route('/')
    def index():
        return "Welcome to the Data Pipeline API!"

    return flask_app
