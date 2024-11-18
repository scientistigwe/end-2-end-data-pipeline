from flask import request, jsonify
from werkzeug.utils import secure_filename
from backend.flask_api.bp_routes import file_system_bp
from backend.data_pipeline.source.file.file_service import FileService
from backend.data_pipeline.source.file.file_config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)

service = FileService()

@file_system_bp.route('/file-source', methods=['POST', 'OPTIONS'])
def handle_file_source():
    """
    Handle multiple file uploads with comprehensive processing.

    Returns:
        JSON response with upload results
    """
    logger.info('Handle File Source started')

    if request.method == 'OPTIONS':
        return '', 204

    files = request.files.getlist('files')
    if not files:
        return jsonify({'status': 'error', 'message': 'No files selected'}), 400

    file_results = []
    for file in files:
        if file and Config.allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                file_content = file.read()
                result = service.handle_file_upload(file_content, filename)
                file_results.append(result)
            except Exception as e:
                file_results.append({'filename': filename, 'status': 'error', 'message': str(e)})
        else:
            file_results.append({'filename': file.filename, 'status': 'error', 'message': 'Invalid file format'})

    if all(result['status'] == 'error' for result in file_results):
        return jsonify({'status': 'error', 'message': 'Failed to process all files', 'details': file_results}), 400

    return jsonify({'status': 'success', 'results': file_results})


@file_system_bp.route('/get-metadata', methods=['GET'])
def get_metadata():
    """
    Retrieve metadata for uploaded file.

    Returns:
        JSON response with file metadata
    """
    file_content = request.files.get('file')

    if not file_content:
        return jsonify({
            'status': 'error',
            'message': 'No file content provided'
        }), 400

    try:
        file_content_data = file_content.read()
        metadata_response = service.get_file_metadata(file_content_data, file_content.filename)

        return jsonify(metadata_response)

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400