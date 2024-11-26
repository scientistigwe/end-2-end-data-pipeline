from flask import Flask
from flask_cors import CORS
import logging

from backend.flask_api.config import get_config
from backend.flask_api.routes.ingestion.file_routes import create_file_routes
from backend.flask_api.routes.processing.pipeline_routes import create_pipeline_routes
from backend.data_pipeline.source.file.file_service import FileService
from backend.data_pipeline.pipeline_service import PipelineService

def create_app(config_name='development'):
    """
    Application factory for creating Flask application.
    """
    # Load configuration
    config = get_config(config_name)

    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(config)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize services
    file_service = FileService()
    pipeline_service = PipelineService()

    # Create blueprints
    file_bp = create_file_routes(file_service)
    pipeline_bp = create_pipeline_routes(pipeline_service)

    # Register blueprints
    app.register_blueprint(file_bp, url_prefix='/api/files')
    app.register_blueprint(pipeline_bp, url_prefix='/api/pipelines')

    # Apply CORS with detailed configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": config.CORS_SETTINGS.get('origins', ['*']),
            "methods": config.CORS_SETTINGS.get('methods', ['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE']),
            "allow_headers": config.CORS_SETTINGS.get('allow_headers', ['Content-Type', 'Authorization']),
            "supports_credentials": True
        }
    })

    return app