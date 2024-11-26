from flask import Blueprint, request, jsonify
from werkzeug.datastructures import FileStorage
import logging
from flask_cors import CORS  # Import flask_cors
from backend.data_pipeline.source.file.file_service import FileService
from backend.flask_api.config import Config
from typing import Dict, Any

logger = logging.getLogger(__name__)

def create_file_routes(file_service: FileService) -> Blueprint:
    """
    Create file upload routes blueprint.

    Args:
        file_service (FileService): Service for handling file operations

    Returns:
        Blueprint: Flask blueprint with file routes
    """
    file_bp = Blueprint('file_bp', __name__)

    def process_file(file: FileStorage) -> Dict[str, Any]:
        """
        Process a single uploaded file.

        Args:
            file (FileStorage): Uploaded file object

        Returns:
            Dict: Processing result
        """
        try:
            # Basic file validation
            if not file or not file.filename:
                return {'status': 'error', 'message': 'Invalid file'}

            # Check file type (ensure extension is in allowed extensions)
            file_extension = file.filename.split('.')[-1].lower()
            if file_extension not in Config.ALLOWED_EXTENSIONS:
                return {
                    'status': 'error',
                    'message': f'Unsupported file type: {file.filename}'
                }

            # Process file
            result = file_service.handle_file_upload(file)
            return result

        except Exception as e:
            logger.error(f"File processing error: {e}")
            return {
                'filename': file.filename,
                'status': 'error',
                'message': str(e)
            }

    @file_bp.route('/upload', methods=['POST'])
    def upload_files():
        """
        Handle multiple file uploads.

        Returns:
            JSON response with upload results
        """
        try:
            files = request.files.getlist('files')

            if not files:
                return jsonify({
                    'status': 'error',
                    'message': 'No files provided'
                }), 400

            # Process files
            results = [process_file(file) for file in files]

            # Check overall processing status
            if all(result['status'] == 'error' for result in results):
                return jsonify({
                    'status': 'error',
                    'message': 'All file processing failed',
                    'details': results
                }), 400

            return jsonify({
                'status': 'success',
                'message': f'Processed {len(files)} files',
                'results': results
            }), 200

        except Exception as e:
            logger.error(f"Upload processing error: {e}")
            return jsonify({
                'status': 'error',
                'message': 'Server error during upload',
                'error': str(e)
            }), 500

    @file_bp.route('/metadata', methods=['GET'])
    def get_metadata():
        """
        Retrieve metadata for processed files.

        Returns:
            JSON response with file metadata
        """
        try:
            metadata = file_service.get_metadata()
            return jsonify({
                'status': 'success',
                'metadata': metadata
            }), 200
        except Exception as e:
            logger.error(f"Metadata retrieval error: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Metadata retrieval failed: {e}'
            }), 500

    @file_bp.route('/upload', methods=['OPTIONS'])
    def handle_options():
        return '', 200  # Ensure OPTIONS requests are accepted

    return file_bp

