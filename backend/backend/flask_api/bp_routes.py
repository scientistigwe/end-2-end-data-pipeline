from flask import Blueprint

file_system_bp = Blueprint('file_system', __name__)

from .routes.ingestion import file_routes
