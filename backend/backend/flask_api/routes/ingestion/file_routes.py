from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
from backend.backend.flask_api.bp_routes import file_system_bp
from backend.backend.data_pipeline.source.file.file_service import handle_file_upload, get_file_metadata
from backend.backend.data_pipeline.source.file.file_config import Config  # Import the Config class


@file_system_bp.route('/file-source', methods=['POST', 'OPTIONS'])
def handle_file_source():
    if request.method == 'OPTIONS':
        return '', 204

    if 'files' not in request.files:
        return jsonify({'status': 'error', 'message': 'No files provided'}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({'status': 'error', 'message': 'No files selected'}), 400

    file_results = []
    for file in files:
        if file and Config.allowed_file(file.filename):  # Using the static method from Config
            try:
                # Read the file content into memory
                filename = secure_filename(file.filename)
                file_content = file.read()

                # Delegate the file upload logic to the service, using file content directly
                result = handle_file_upload(file_content, filename)

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
    """Get metadata for the uploaded file content."""
    file_content = request.files.get('file')

    if not file_content:
        return jsonify({
            'status': 'error',
            'message': 'No file content provided'
        }), 400

    try:
        # Process the file content directly for metadata
        file_content_data = file_content.read()
        metadata_response = get_file_metadata(file_content_data)

        return jsonify(metadata_response)

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400
