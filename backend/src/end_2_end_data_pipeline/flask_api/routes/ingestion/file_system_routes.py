from flask import request, jsonify
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_manager import FileManager
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_fetcher import FileFetcher
from . import file_system_bp  # Import the file system blueprint

# Allowed file extensions
ALLOWED_EXTENSIONS = {'csv', 'json', 'xlsx', 'parquet'}


@file_system_bp.route('/file-source', methods=['POST'])
def handle_file_source():
    """
    Handle file upload or file path processing based on user input.
    """
    # Check if files are being uploaded
    if 'files' in request.files:
        files = request.files.getlist('files')
        file_metadata = []
        messages = []

        # Process each uploaded file
        for file in files:
            file_path = file.filename  # Get the file name (assuming file is uploaded directly)

            # Initialize FileFetcher to handle file validation and loading
            fetcher = FileFetcher(file_path=file_path,
                                  required_columns=['column1', 'column2'])  # Adjust columns as needed

            # Fetch and validate the file
            df, fetcher_message = fetcher.fetch_file()

            if df is None:
                messages.append({
                    'status': 'error',
                    'message': f"Error fetching file {file_path}: {fetcher_message}"
                })
                continue  # Skip further processing for this file

            # Initialize FileManager for metadata extraction and orchestration preparation
            manager = FileManager(file_path=file_path,
                                  required_columns=['column1', 'column2'])  # Same required columns if needed

            # Extract file metadata
            metadata = manager.get_file_metadata()
            file_metadata.append(metadata)

            if 'error' not in metadata:
                # Prepare the file for orchestration or staging
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

        # Return the metadata and messages to the frontend
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

    # If no files are uploaded, return an error response
    return jsonify({
        'status': 'error',
        'message': 'No files uploaded.'
    }), 400
