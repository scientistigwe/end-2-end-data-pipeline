from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from pathlib import Path
import tempfile
import yaml
from werkzeug.utils import secure_filename

# Import from our data ingestion system
from data_ingestion_system import DataIngestionManager, DataSourceType, ValidationResult

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = Path(tempfile.gettempdir()) / 'data_ingestion'
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'parquet'}

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX