from flask import Blueprint

pipeline_bp = Blueprint('pipeline_api', __name__)

from .routes.ingestion import file_routes
from .routes.processing import create_pipeline_routes
