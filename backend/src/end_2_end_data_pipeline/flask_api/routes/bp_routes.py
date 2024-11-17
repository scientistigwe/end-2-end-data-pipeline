from flask import Blueprint

file_system_bp = Blueprint('file_system', __name__)

from .ingestion import file_system_routes