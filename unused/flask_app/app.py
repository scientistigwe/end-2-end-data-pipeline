# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Load configuration
app.config.from_object(Config)

# Initialize components
validator = DataValidator(app.config['VALIDATION_SCHEMAS_PATH'])
ingestion_manager = DataIngestionManager(validator)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename, app.config['ALLOWED_EXTENSIONS']):
        return jsonify({"error": "File type not allowed"}), 400

    try:
        # Save file
        filepath = save_uploaded_file(file, app.config['UPLOAD_FOLDER'])
        if not filepath:
            return jsonify({"error": "Error saving file"}), 500

        # Determine source type
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        source_type = DataSourceType[file_extension.upper()]

        # Process data
        result = ingestion_manager.process_data(
            filepath,
            source_type,
            request.form.get('schema', 'default')
        )

        # Clean up
        os.remove(filepath)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/schemas', methods=['GET'])
def list_schemas():
    try:
        schemas = os.listdir(app.config['VALIDATION_SCHEMAS_PATH'])
        return jsonify({"schemas": schemas})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)