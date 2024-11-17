from flask import request, jsonify
from end_2_end_data_pipeline.data_pipeline.source.file.file_manager import FileManager  # Absolute import for FileManager
from end_2_end_data_pipeline.data_pipeline.source.file.file_fetcher import FileFetcher  # Absolute import for FileFetcher
from end_2_end_data_pipeline.flask_api.bp_routes import file_system_bp  # Absolute import for file_system_bp

# Allowed file extensions
ALLOWED_EXTENSIONS = {'csv', 'json', 'xlsx', 'parquet'}

@file_system_bp.route('/file-source', methods=['POST'])
def handle_file_source():
    """
    Handle file upload or file path processing based on user input.
    """
    if 'files' in request.files:
        files = request.files.getlist('files')
        file_metadata = []
        messages = []

        # Process each uploaded file
        for file in files:
            file_path = file.filename

            # Initialize FileFetcher to handle file validation and loading
            fetcher = FileFetcher(file_path=file_path, required_columns=['column1', 'column2'])

            df, fetcher_message = fetcher.fetch_file()

            if df is None:
                messages.append({
                    'status': 'error',
                    'message': f"Error fetching file {file_path}: {fetcher_message}"
                })
                continue

            # Initialize FileManager for metadata extraction
            manager = FileManager(file_path=file_path, required_columns=['column1', 'column2'])

            metadata = manager.get_file_metadata()
            file_metadata.append(metadata)

            if 'error' not in metadata:
                preparation_result = manager.prepare_for_orchestrator(df)

                if 'error' in preparation_result:
                    messages.append({
                        'status': 'error',
                        'message': f"Error processing {file_path}: {preparation_result['error']}"
                    })
                else:
                    messages.append({
                        'status': 'success',
                        'message': f"File {file_path} processed successfully."
                    })
            else:
                messages.append({
                    'status': 'error',
                    'message': f"Error extracting metadata for {file_path}: {metadata['error']}"
                })

        if all(msg['status'] == 'success' for msg in messages):
            return jsonify({
                'status': 'success',
                'fileMetadata': file_metadata,
                'messages': messages
            })
        else:
            return jsonify({
                'status': 'error',
                'messages': messages
            }), 400

    return jsonify({
        'status': 'error',
        'message': 'No files uploaded.'
    }), 400

@file_system_bp.route('/get-metadata', methods=['GET'])
def get_metadata():
    """
    Endpoint to get metadata for a specified file path.
    """
    file_path = request.args.get('file_path')
    
    if not file_path:
        return jsonify({
            'status': 'error',
            'message': 'No file path provided.'
        }), 400

    # Initialize FileManager to extract metadata
    manager = FileManager(file_path=file_path)

    metadata = manager.get_file_metadata()
    
    if 'error' in metadata:
        return jsonify({
            'status': 'error',
            'message': metadata['error']
        }), 400

    return jsonify({
        'status': 'success',
        'metadata': metadata
    })
