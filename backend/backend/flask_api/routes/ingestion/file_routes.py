from flask import request, jsonify
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from backend.flask_api.bp_routes import pipeline_bp
from backend.data_pipeline.source.file.file_service import FileService
from backend.data_pipeline.source.file.file_config import Config
import logging
from typing import Dict, List, Any, Union
from io import BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

service = FileService()


class FileWrapper:
    """Wrapper class for file objects to provide consistent interface."""

    def __init__(self, file: FileStorage):
        self._file = file
        self._content: Union[bytes, None] = None
        self.filename = secure_filename(file.filename)

    def read(self) -> bytes:
        """Read file content, caching it for multiple reads."""
        if self._content is None:
            self._content = self._file.read()
            self._file.seek(0)  # Reset file pointer
        return self._content

    def seek(self, offset: int) -> None:
        """Implement seek for compatibility."""
        self._file.seek(offset)

    @property
    def stream(self) -> BytesIO:
        """Provide stream access to file content."""
        return BytesIO(self.read())


def process_single_file(file: FileStorage) -> Dict[str, Any]:
    """
    Process a single file upload.

    Args:
        file: The uploaded file object

    Returns:
        Dict containing processing results
    """
    try:
        if not file or not file.filename:
            return {
                'status': 'error',
                'message': 'Invalid file object'
            }

        if not Config.allowed_file(file.filename):
            return {
                'status': 'error',
                'message': f'File type not allowed: {file.filename}'
            }

        file_wrapper = FileWrapper(file)
        result = service.handle_file_upload(file_wrapper)

        logger.info(f"Successfully processed file: {file.filename}")
        return result

    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}", exc_info=True)
        return {
            'filename': file.filename,
            'status': 'error',
            'message': str(e)
        }


@pipeline_bp.route('/file-source', methods=['POST', 'OPTIONS'])
def handle_file_source() -> tuple[Any, int]:
    """
    Handle multiple file uploads with comprehensive processing.

    Returns:
        Tuple of (response_json, status_code)
    """
    logger.info('Handle File Source started')

    if request.method == 'OPTIONS':
        return '', 204

    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({
                'status': 'error',
                'message': 'No files provided in request'
            }), 400

        file_results: List[Dict[str, Any]] = []

        for file in files:
            result = process_single_file(file)
            file_results.append(result)

        # Check if all files failed processing
        if all(result['status'] == 'error' for result in file_results):
            return jsonify({
                'status': 'error',
                'message': 'All file processing attempts failed',
                'details': file_results
            }), 400

        # Return success if at least one file was processed
        return jsonify({
            'status': 'success',
            'message': f'Processed {len(files)} files',
            'results': file_results
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error in file processing: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Server error during file processing',
            'error': str(e)
        }), 500


@pipeline_bp.route('/get-metadata', methods=['GET'])
def get_metadata() -> tuple[Any, int]:
    """
    Retrieve metadata for the last processed file.

    Returns:
        Tuple of (response_json, status_code)
    """
    try:
        metadata = service.file_manager.get_metadata()

        if 'error' in metadata:
            return jsonify({
                'status': 'error',
                'message': metadata['error']
            }), 400

        return jsonify({
            'status': 'success',
            'metadata': metadata
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving metadata: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve metadata: {str(e)}'
        }), 500