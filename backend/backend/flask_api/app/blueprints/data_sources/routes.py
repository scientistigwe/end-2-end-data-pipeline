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
from ...middleware.auth_middleware import jwt_required_with_user
import logging

logger = logging.getLogger(__name__)

def create_data_source_blueprint(
    file_service: FileSourceService,
    db_service: DatabaseSourceService,
    s3_service: S3SourceService,
    api_service: APISourceService,
    stream_service: StreamSourceService,
    db_session
):
    """Create data source blueprint with all routes."""
    data_source_bp = Blueprint('data_sources', __name__)

    def get_service_by_type(source_type: str):
        """Helper function to get appropriate service by type."""
        services = {
            'file': file_service,
            'database': db_service,
            's3': s3_service,
            'api': api_service,
            'stream': stream_service
        }
        return services.get(source_type)

    def find_source_and_service(source_id: str):
        """Helper function to find source and its corresponding service."""
        for service in [file_service, db_service, s3_service, api_service, stream_service]:
            try:
                source = service.get_source(source_id)
                if source:
                    return source, service
            except Exception:
                continue
        return None, None

    # General Data Source Routes
    @data_source_bp.route('/', methods=['GET'])
    @jwt_required_with_user()
    def list_sources():
        """List all data sources."""
        try:
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

    @data_source_bp.route('/', methods=['POST'])
    @jwt_required_with_user()
    def create_source():
        """Create a new data source."""
        try:
            schema = DataSourceRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id  # Now g.current_user should be available
            
            service = get_service_by_type(data['type'])
            if not service:
                return ResponseBuilder.error(f"Invalid source type: {data['type']}", status_code=400)
                
            result = service.connect(data)
            return ResponseBuilder.success({
                'source': DataSourceResponseSchema().dump(result)
            })
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Source creation error: {str(e)}")
            return ResponseBuilder.error("Failed to create source", status_code=500)
        
    @data_source_bp.route('/<source_id>', methods=['GET'])
    @jwt_required_with_user()
    def get_source(source_id):
        """Get specific data source details."""
        try:
            source, _ = find_source_and_service(source_id)
            if not source:
                return ResponseBuilder.error("Source not found", status_code=404)
                
            return ResponseBuilder.success({
                'source': DataSourceResponseSchema().dump(source)
            })
        except Exception as e:
            logger.error(f"Error getting source: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get source", status_code=500)

    @data_source_bp.route('/<source_id>', methods=['PUT'])
    @jwt_required_with_user()
    def update_source(source_id):
        """Update a data source."""
        try:
            schema = DataSourceRequestSchema()
            data = schema.load(request.get_json())
            
            service = get_service_by_type(data['type'])
            if not service:
                return ResponseBuilder.error(f"Invalid source type: {data['type']}", status_code=400)
                
            result = service.update(source_id, data)
            return ResponseBuilder.success({
                'source': DataSourceResponseSchema().dump(result)
            })
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Source update error: {str(e)}")
            return ResponseBuilder.error("Failed to update source", status_code=500)

    @data_source_bp.route('/<source_id>', methods=['DELETE'])
    @jwt_required_with_user()
    def delete_source(source_id):
        """Delete a data source."""
        try:
            source, service = find_source_and_service(source_id)
            if not source:
                return ResponseBuilder.error("Source not found", status_code=404)
            
            service.disconnect(source_id)
            return ResponseBuilder.success({
                'message': f"Successfully deleted source {source_id}"
            })
        except Exception as e:
            logger.error(f"Source deletion error: {str(e)}")
            return ResponseBuilder.error("Failed to delete source", status_code=500)

    # File Source Routes
    @data_source_bp.route('/file/upload', methods=['POST'])
    @jwt_required_with_user()
    def upload_file():
        """Upload file(s) as data source."""
        try:
            current_user_id = g.current_user.id
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

    @data_source_bp.route('/file/<file_id>/parse', methods=['POST'])
    @jwt_required_with_user()
    def parse_file(file_id):
        """Parse uploaded file."""
        try:
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
    @jwt_required_with_user()
    def connect_database():
        """Connect to database source."""
        try:
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
    @jwt_required_with_user()
    def test_database_connection(connection_id):
        """Test database connection."""
        try:
            result = db_service.test_connection(connection_id)
            return ResponseBuilder.success({'status': result})
        except Exception as e:
            logger.error(f"Database test error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Connection test failed", status_code=500)

    @data_source_bp.route('/database/<connection_id>/schema', methods=['GET'])
    def get_database_schema(connection_id):
        """Get database schema."""
        try:
            schema = db_service.get_schema(connection_id)
            return ResponseBuilder.success({'schema': schema})
        except Exception as e:
            logger.error(f"Schema fetch error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to fetch schema", status_code=500)

    # S3 Source Routes
    @data_source_bp.route('/s3/connect', methods=['POST'])
    @jwt_required_with_user()
    def connect_s3():
        """Connect to S3 bucket."""
        try:
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
    @jwt_required_with_user()
    def list_s3_objects(connection_id):
        """List objects in S3 bucket."""
        try:
            prefix = request.args.get('prefix', '')
            objects = s3_service.list_objects(connection_id, prefix)
            return ResponseBuilder.success({'objects': objects})
        except Exception as e:
            logger.error(f"S3 list error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to list objects", status_code=500)

    # API Source Routes
    @data_source_bp.route('/api/connect', methods=['POST'])
    @jwt_required_with_user()
    def connect_api():
        """Connect to API source."""
        try:
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
    @jwt_required_with_user()
    def execute_api_request(connection_id):
        """Execute API request."""
        try:
            request_data = request.get_json()
            result = api_service.execute_request(connection_id, request_data)
            return ResponseBuilder.success({'result': result})
        except Exception as e:
            logger.error(f"API execution error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Request failed", status_code=500)

    # Stream Source Routes
    @data_source_bp.route('/stream/connect', methods=['POST'])
    @jwt_required_with_user()
    def connect_stream():
        """Connect to stream source."""
        try:
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
    @jwt_required_with_user()
    def get_stream_status(connection_id):
        """Get stream connection status."""
        try:
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

    @data_source_bp.route('/<source_id>/validate', methods=['POST'])
    @jwt_required_with_user()
    def validate_source(source_id):
        """Validate a data source configuration."""
        try:
            source, service = find_source_and_service(source_id)
            if not source:
                return ResponseBuilder.error("Source not found", status_code=404)
            
            result = service.validate_config(source.config)
            return ResponseBuilder.success({'validation': result})
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return ResponseBuilder.error("Failed to validate source", status_code=500)

    @data_source_bp.route('/<source_id>/preview', methods=['GET'])
    @jwt_required_with_user()
    def preview_source(source_id):
        """Preview data from a source."""
        try:
            limit = request.args.get('limit', 100, type=int)
            source, service = find_source_and_service(source_id)
            
            if not source:
                return ResponseBuilder.error("Source not found", status_code=404)
            
            preview_data = service.preview_data(source_id, limit)
            return ResponseBuilder.success({'preview': preview_data})
        except Exception as e:
            logger.error(f"Preview error: {str(e)}")
            return ResponseBuilder.error("Failed to preview source", status_code=500)

    @data_source_bp.route('/<source_id>/sync', methods=['POST'])
    @jwt_required_with_user()
    def sync_source(source_id):
        """Synchronize a data source."""
        try:
            source, service = find_source_and_service(source_id)
            if not source:
                return ResponseBuilder.error("Source not found", status_code=404)
            
            sync_result = service.sync_source(source_id)
            return ResponseBuilder.success({'sync': sync_result})
        except Exception as e:
            logger.error(f"Sync error: {str(e)}")
            return ResponseBuilder.error("Failed to sync source", status_code=500)

    # Test connection route
    @data_source_bp.route('/<source_id>/test', methods=['POST'])
    def test_source(source_id):
        """Test source connection."""
        try:
            source, service = find_source_and_service(source_id)
            if not source:
                return ResponseBuilder.error("Source not found", status_code=404)
            
            test_result = service.test_connection(source_id)
            return ResponseBuilder.success({'test': test_result})
        except Exception as e:
            logger.error(f"Test connection error: {str(e)}")
            return ResponseBuilder.error("Failed to test connection", status_code=500)

    # Common routes for all source types
    @data_source_bp.route('/<source_id>/metadata', methods=['GET'])
    @jwt_required_with_user()
    def get_source_metadata(source_id):
        """Get source metadata."""
        try:
            source, service = find_source_and_service(source_id)
            if not source:
                return ResponseBuilder.error("Source not found", status_code=404)
            
            metadata = service.get_metadata(source_id)
            return ResponseBuilder.success({'metadata': metadata})
        except Exception as e:
            logger.error(f"Metadata fetch error: {str(e)}")
            return ResponseBuilder.error("Failed to fetch metadata", status_code=500)

    @data_source_bp.route('/<source_id>/logs', methods=['GET'])
    @jwt_required_with_user()
    def get_source_logs(source_id):
        """Get source logs."""
        try:
            limit = request.args.get('limit', 100, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            source, service = find_source_and_service(source_id)
            if not source:
                return ResponseBuilder.error("Source not found", status_code=404)
            
            logs = service.get_logs(source_id, limit, offset)
            return ResponseBuilder.success({'logs': logs})
        except Exception as e:
            logger.error(f"Logs fetch error: {str(e)}")
            return ResponseBuilder.error("Failed to fetch logs", status_code=500)

    @data_source_bp.route('/<source_id>/metrics', methods=['GET'])
    @jwt_required_with_user()
    def get_source_metrics(source_id):
        """Get source metrics."""
        try:
            start_time = request.args.get('start_time', type=str)
            end_time = request.args.get('end_time', type=str)
            
            source, service = find_source_and_service(source_id)
            if not source:
                return ResponseBuilder.error("Source not found", status_code=404)
            
            metrics = service.get_metrics(source_id, start_time, end_time)
            return ResponseBuilder.success({'metrics': metrics})
        except Exception as e:
            logger.error(f"Metrics fetch error: {str(e)}")
            return ResponseBuilder.error("Failed to fetch metrics", status_code=500)

    @data_source_bp.route('/<source_id>/health', methods=['GET'])
    @jwt_required_with_user()
    def get_source_health(source_id):
        """Get source health status."""
        try:
            source, service = find_source_and_service(source_id)
            if not source:
                return ResponseBuilder.error("Source not found", status_code=404)
            
            health = service.get_health(source_id)
            return ResponseBuilder.success({'health': health})
        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return ResponseBuilder.error("Failed to check health", status_code=500)

    @data_source_bp.route('/<source_id>/refresh', methods=['POST'])
    @jwt_required_with_user()
    def refresh_source(source_id):
        """Refresh source metadata and configuration."""
        try:
            source, service = find_source_and_service(source_id)
            if not source:
                return ResponseBuilder.error("Source not found", status_code=404)
            
            refresh_result = service.refresh(source_id)
            return ResponseBuilder.success({'refresh': refresh_result})
        except Exception as e:
            logger.error(f"Refresh error: {str(e)}")
            return ResponseBuilder.error("Failed to refresh source", status_code=500)

    return data_source_bp