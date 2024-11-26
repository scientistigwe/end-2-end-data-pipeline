from flask import Blueprint

pipeline_bp = Blueprint('pipeline_bp', __name__)

from .ingestion import file_routes
from .processing import pipeline_routes