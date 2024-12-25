# app/blueprints/data_sources/routes.py
from flask import Blueprint, request, g, current_app
from marshmallow import ValidationError
from ...schemas.data_sources.file_source import (
    FileSourceConfigSchema, 
    FileSourceResponseSchema,
    FileUploadRequestSchema,
    FileMetadataResponseSchema
)
from ...schemas.data_sources.database_source import (
    DatabaseSourceConfigSchema,
    DatabaseSourceResponseSchema
)
from ...schemas.data_sources.s3_source import (
    S3SourceConfigSchema,
    S3SourceResponseSchema
)
from ...schemas.data_sources.api_source import (
    APISourceConfigSchema,
    APISourceResponseSchema
)
from ...schemas.data_sources.stream_source import (
    StreamSourceConfigSchema,
    StreamSourceResponseSchema
)
from ...schemas.data_source import (
    DataSourceRequestSchema,
    DataSourceResponseSchema
)
from ...services.data_sources import (
    FileSourceService,
    DatabaseSourceService,
    S3SourceService,
    APISourceService,
    StreamSourceService
)
from ...utils.response_builder import ResponseBuilder
import logging

logger = logging.getLogger(__name__)
data_source_bp = Blueprint('data_sources', __name__)

def get_services():
    """Get data source service instances."""
    if 'file_service' not in g:
        g.file_service = FileSourceService(g.db)
    if 'db_service' not in g:
        g.db_service = DatabaseSourceService(g.db)
    if 's3_service' not in g:
        g.s3_service = S3SourceService(g.db)
    if 'api_service' not in g:
        g.api_service = APISourceService(g.db)
    if 'stream_service' not in g:
        g.stream_service = StreamSourceService(g.db)
    return (g.file_service, g.db_service, g.s3_service, g.api_service, g.stream_service)

# General Data Source Routes
@data_source_bp.route('/', methods=['GET'])
def list_sources():
    """List all data sources."""
    try:
        file_service, db_service, s3_service, api_service, stream_service = get_services()
        sources = {
            'files': DataSourceResponseSchema(many=True).dump(file_service.list_sources()),
            'databases': DataSourceResponseSchema(many=True).dump(db_service.list_sources()),
            's3': DataSourceResponseSchema(many=True).dump(s3_service.list_sources()),
            'api': DataSourceResponseSchema(many=True).dump(api_service.list_sources()),
            'stream': DataSourceResponseSchema(many=True).dump(stream_service.list_sources())
        }
        return ResponseBuilder.success({'sources': sources})
    except Exception as e:
        logger.error(f"Error listing sources: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to list sources", status_code=500)

@data_source_bp.route('/<source_id>', methods=['GET'])
def get_source(source_id):
    """Get specific data source details."""
    try:
        file_service, db_service, s3_service, api_service, stream_service = get_services()
        source = file_service.get_source(source_id) or \
                db_service.get_source(source_id) or \
                s3_service.get_source(source_id) or \
                api_service.get_source(source_id) or \
                stream_service.get_source(source_id)
        
        if not source:
            return ResponseBuilder.error("Source not found", status_code=404)
            
        return ResponseBuilder.success({
            'source': DataSourceResponseSchema().dump(source)
        })
    except Exception as e:
        logger.error(f"Error getting source: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to get source", status_code=500)

# File Source Routes
@data_source_bp.route('/file/upload', methods=['POST'])
def upload_file():
    """Upload file(s) as data source."""
    try:
        file_service, *_ = get_services()
        current_user_id = g.current_user.id  # Get user ID from global context
        files = request.files.getlist('files')
        metadata = request.form.get('metadata', '{}')
        
        upload_schema = FileUploadRequestSchema()
        results = []
        
        for file in files:
            data = upload_schema.load({
                'filename': file.filename, 
                'content_type': file.content_type,
                'user_id': current_user_id
            })
            result = file_service.handle_file_upload(file, data)
            results.append(FileMetadataResponseSchema().dump(result))
        
        return ResponseBuilder.success({'results': results})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"File upload error: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Upload failed", status_code=500)

# Error Handling
@data_source_bp.errorhandler(404)
def not_found_error(error):
    return ResponseBuilder.error("Resource not found", status_code=404)

@data_source_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}", exc_info=True)
    return ResponseBuilder.error("Internal server error", status_code=500)

@data_source_bp.route('/file/<file_id>/parse', methods=['POST'])
def parse_file(file_id):
    """Parse uploaded file."""
    try:
        file_service, *_ = get_services()
        parse_options = request.get_json()
        result = file_service.parse_file(file_id, parse_options)
        return ResponseBuilder.success({
            'result': FileSourceResponseSchema().dump(result)
        })
    except Exception as e:
        logger.error(f"File parsing error: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Parsing failed", status_code=500)

# Database Source Routes
@data_source_bp.route('/database/connect', methods=['POST'])
def connect_database():
    """Connect to database source."""
    try:
        _, db_service, *_ = get_services()
        schema = DatabaseSourceConfigSchema()
        data = schema.load(request.get_json())
        result = db_service.connect(data)
        return ResponseBuilder.success(
            DatabaseSourceResponseSchema().dump(result)
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Connection failed", status_code=500)

@data_source_bp.route('/database/<connection_id>/test', methods=['POST'])
def test_database_connection(connection_id):
    """Test database connection."""
    try:
        _, db_service, *_ = get_services()
        result = db_service.test_connection(connection_id)
        return ResponseBuilder.success({'status': result})
    except Exception as e:
        logger.error(f"Database test error: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Connection test failed", status_code=500)

@data_source_bp.route('/database/<connection_id>/schema', methods=['GET'])
def get_database_schema(connection_id):
    """Get database schema."""
    try:
        _, db_service, *_ = get_services()
        schema = db_service.get_schema(connection_id)
        return ResponseBuilder.success({'schema': schema})
    except Exception as e:
        logger.error(f"Schema fetch error: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to fetch schema", status_code=500)

# S3 Source Routes
@data_source_bp.route('/s3/connect', methods=['POST'])
def connect_s3():
    """Connect to S3 bucket."""
    try:
        _, _, s3_service, *_ = get_services()
        schema = S3SourceConfigSchema()
        data = schema.load(request.get_json())
        result = s3_service.connect(data)
        return ResponseBuilder.success(
            S3SourceResponseSchema().dump(result)
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"S3 connection error: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Connection failed", status_code=500)

@data_source_bp.route('/s3/<connection_id>/list', methods=['GET'])
def list_s3_objects(connection_id):
    """List objects in S3 bucket."""
    try:
        _, _, s3_service, *_ = get_services()
        prefix = request.args.get('prefix', '')
        objects = s3_service.list_objects(connection_id, prefix)
        return ResponseBuilder.success({'objects': objects})
    except Exception as e:
        logger.error(f"S3 list error: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to list objects", status_code=500)

# API Source Routes
@data_source_bp.route('/api/connect', methods=['POST'])
def connect_api():
    """Connect to API source."""
    try:
        _, _, _, api_service, _ = get_services()
        schema = APISourceConfigSchema()
        data = schema.load(request.get_json())
        result = api_service.connect(data)
        return ResponseBuilder.success(
            APISourceResponseSchema().dump(result)
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"API connection error: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Connection failed", status_code=500)

@data_source_bp.route('/api/<connection_id>/execute', methods=['POST'])
def execute_api_request(connection_id):
    """Execute API request."""
    try:
        _, _, _, api_service, _ = get_services()
        request_data = request.get_json()
        result = api_service.execute_request(connection_id, request_data)
        return ResponseBuilder.success({'result': result})
    except Exception as e:
        logger.error(f"API execution error: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Request failed", status_code=500)

# Stream Source Routes
@data_source_bp.route('/stream/connect', methods=['POST'])
def connect_stream():
    """Connect to stream source."""
    try:
        _, _, _, _, stream_service = get_services()
        schema = StreamSourceConfigSchema()
        data = schema.load(request.get_json())
        result = stream_service.connect(data)
        return ResponseBuilder.success(
            StreamSourceResponseSchema().dump(result)
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Stream connection error: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Connection failed", status_code=500)

@data_source_bp.route('/stream/<connection_id>/status', methods=['GET'])
def get_stream_status(connection_id):
    """Get stream connection status."""
    try:
        _, _, _, _, stream_service = get_services()
        status = stream_service.get_status(connection_id)
        return ResponseBuilder.success({'status': status})
    except Exception as e:
        logger.error(f"Stream status error: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to get status", status_code=500)

# Error handlers
@data_source_bp.errorhandler(404)
def not_found_error(error):
    return ResponseBuilder.error("Resource not found", status_code=404)

@data_source_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}", exc_info=True)
    return ResponseBuilder.error("Internal server error", status_code=500)