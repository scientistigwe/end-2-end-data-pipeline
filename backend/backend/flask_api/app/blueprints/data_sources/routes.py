# app/blueprints/data_sources/routes.py
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from ...schemas.data_sources import (
    FileSourceSchema, DBSourceSchema, S3SourceSchema,
    APISourceSchema, StreamSourceSchema
)
from ...utils.response_builder import ResponseBuilder
import logging

logger = logging.getLogger(__name__)
data_source_bp = Blueprint('data_sources', __name__)

# File Source Routes
@data_source_bp.route('/file/upload', methods=['POST'])
@jwt_required()
def upload_file():
    try:
        files = request.files.getlist('files')
        schema = FileSourceSchema()
        results = []
        for file in files:
            data = schema.load({'filename': file.filename})
            result = file_service.handle_file_upload(file)
            results.append(result)
        return ResponseBuilder.success({'results': results})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

# Database Source Routes
@data_source_bp.route('/database/connect', methods=['POST'])
@jwt_required()
def connect_database():
    try:
        schema = DBSourceSchema()
        data = schema.load(request.get_json())
        result = db_service.connect(data)
        return ResponseBuilder.success(result)
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@data_source_bp.route('/database/query', methods=['POST'])
@jwt_required()
def execute_query():
    try:
        data = request.get_json()
        result = db_service.execute_query(data['query'])
        return ResponseBuilder.success(result)
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

# S3 Source Routes
@data_source_bp.route('/s3/connect', methods=['POST'])
@jwt_required()
def connect_s3():
    try:
        schema = S3SourceSchema()
        data = schema.load(request.get_json())
        result = s3_service.connect(data)
        return ResponseBuilder.success(result)
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@data_source_bp.route('/s3/list', methods=['GET'])
@jwt_required()
def list_s3_objects():
    try:
        bucket = request.args.get('bucket')
        objects = s3_service.list_objects(bucket)
        return ResponseBuilder.success({'objects': objects})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

# API Source Routes
@data_source_bp.route('/api/connect', methods=['POST'])
@jwt_required()
def connect_api():
    try:
        schema = APISourceSchema()
        data = schema.load(request.get_json())
        result = api_service.connect(data)
        return ResponseBuilder.success(result)
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@data_source_bp.route('/api/fetch', methods=['POST'])
@jwt_required()
def fetch_api_data():
    try:
        data = request.get_json()
        result = api_service.fetch_data(data)
        return ResponseBuilder.success(result)
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

# Stream Source Routes
@data_source_bp.route('/stream/connect', methods=['POST'])
@jwt_required()
def connect_stream():
    try:
        schema = StreamSourceSchema()
        data = schema.load(request.get_json())
        result = stream_service.connect(data)
        return ResponseBuilder.success(result)
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@data_source_bp.route('/stream/status', methods=['GET'])
@jwt_required()
def get_stream_status():
    try:
        stream_id = request.args.get('stream_id')
        status = stream_service.get_status(stream_id)
        return ResponseBuilder.success({'status': status})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)