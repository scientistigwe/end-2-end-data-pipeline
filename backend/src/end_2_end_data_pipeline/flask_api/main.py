import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from flask import Flask
from .bp_routes import file_system_bp

# Initialize Flask application
app = Flask(__name__)

# Register blueprints
app.register_blueprint(file_system_bp, url_prefix='/file-system')
# app.register_blueprint(api_source_bp, url_prefix='/api-source')
# app.register_blueprint(stream_source_bp, url_prefix='/stream-source')

# Add any necessary configurations (e.g., for debugging, testing, etc.)
app.config['DEBUG'] = True  # Example configuration for development

@app.route('/')
def index():
    """
    A simple test route to verify the Flask app is running.
    """
    return "Welcome to the Data Pipeline API!"

if __name__ == '__main__':
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000)  # You can change the host/port if needed
