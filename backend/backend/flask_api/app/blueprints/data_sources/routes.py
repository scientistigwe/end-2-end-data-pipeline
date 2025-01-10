from flask import Blueprint, request, g, current_app
from marshmallow import ValidationError
from typing import Tuple, Any
import logging
from ...schemas.data_sources import (
    FileSourceConfigSchema, FileSourceResponseSchema,
    FileUploadRequestSchema, FileMetadataResponseSchema,
    DatabaseSourceConfigSchema, DatabaseSourceResponseSchema,
    S3SourceConfigSchema, S3SourceResponseSchema,
    APISourceConfigSchema, APISourceResponseSchema,
    StreamSourceConfigSchema, StreamSourceResponseSchema,
    DataSourceRequestSchema, DataSourceResponseSchema
)
from ...services.data_sources import (
    FileSourceService, DatabaseSourceService,
    S3SourceService, APISourceService, StreamSourceService
)
from ...utils.response_builder import ResponseBuilder
from ...middleware.auth_middleware import jwt_required_with_user

logger = logging.getLogger(__name__)

def create_data_source_blueprint(
    file_service: FileSourceService,
    db_service: DatabaseSourceService,
    s3_service: S3SourceService,
    api_service: APISourceService,
    stream_service: StreamSourceService,
    db_session
) -> Blueprint:
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

    def find_source_and_service(source_id: str) -> Tuple[Any, Any]:
        """Helper function to find source and its corresponding service."""
        for service in [file_service, db_service, s3_service, api_service, stream_service]:
            try:
                source = service.get_source(source_id)
                if source:
                    return source, service
            except Exception:
                continue
        return None, None

    def validate_source_access(source_id: str, require_owner: bool = True) -> Tuple[Any, Any]:
        """Validate source access and return source with service."""
        source, service = find_source_and_service(source_id)
        if not source:
            raise ValueError("Source not found")
        if require_owner and source.owner_id != g.current_user.id:
            raise ValueError("Not authorized to access this source")
        return source, service

    # Common CRUD Routes
    @data_source_bp.route('/', methods=['GET'])
    @jwt_required_with_user()
    def list_sources():
        """List all data sources."""
        try:
            # Get sources by type
            sources = {
                'files': DataSourceResponseSchema(many=True).dump(
                    file_service.list_sources()
                ),
                'databases': DataSourceResponseSchema(many=True).dump(
                    db_service.list_sources()
                ),
                's3': DataSourceResponseSchema(many=True).dump(
                    s3_service.list_sources()
                ),
                'api': DataSourceResponseSchema(many=True).dump(
                    api_service.list_sources()
                ),
                'stream': DataSourceResponseSchema(many=True).dump(
                    stream_service.list_sources()
                )
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
            # Log the raw request data for debugging
            request_data = request.get_json()
            logger.info(f"[DEBUG]: Received create source request: {request_data}")

            # 1. Validate request data
            schema = DataSourceRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id

            # 2. Get appropriate service
            service = get_service_by_type(data['type'])
            if not service:
                return ResponseBuilder.error(
                    f"Invalid source type: {data['type']}", 
                    status_code=400
                )

            # 3. Process configuration before saving
            processed_config = service.process_config(data)
            
            # 4. Create source with processed config
            result = service.create_source(processed_config)

            return ResponseBuilder.success({
                'source': DataSourceResponseSchema().dump(result)
            })
        except ValidationError as e:
            # Log specific validation errors
            logger.error(f"Validation errors: {e.messages}")
            return ResponseBuilder.error(
                "Validation error",
                details=e.messages,
                status_code=400
            )

        except Exception as e:
            logger.error(f"Source creation error: {str(e)}")
            return ResponseBuilder.error("Failed to create source", status_code=500)

    @data_source_bp.route('/<source_id>', methods=['GET'])
    @jwt_required_with_user()
    def get_source(source_id):
        """Get specific data source details."""
        try:
            # 1. Validate access
            source, _ = validate_source_access(source_id, require_owner=False)
            
            # 2. Return source details
            return ResponseBuilder.success({
                'source': DataSourceResponseSchema().dump(source)
            })
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Error getting source: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get source", status_code=500)

    @data_source_bp.route('/<source_id>', methods=['PUT'])
    @jwt_required_with_user()
    def update_source(source_id):
        """Update a data source."""
        try:
            # 1. Validate request data
            schema = DataSourceRequestSchema()
            update_data = schema.load(request.get_json())

            # 2. Validate access and get service
            source, service = validate_source_access(source_id)

            # 3. Process update data
            processed_update = service.process_update(source, update_data)

            # 4. Apply update
            updated_source = service.update_source(source_id, processed_update)

            return ResponseBuilder.success({
                'source': DataSourceResponseSchema().dump(updated_source)
            })
        except ValidationError as e:
            return ResponseBuilder.error(
                "Validation error", 
                details=e.messages, 
                status_code=400
            )
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=400)
        except Exception as e:
            logger.error(f"Source update error: {str(e)}")
            return ResponseBuilder.error("Failed to update source", status_code=500)

    @data_source_bp.route('/<source_id>', methods=['DELETE'])
    @jwt_required_with_user()
    def delete_source(source_id):
        """Delete a data source."""
        try:
            # 1. Validate access
            source, service = validate_source_access(source_id)

            # 2. Process deletion (cleanup any resources)
            service.process_deletion(source)
            
            # 3. Delete source
            service.delete_source(source_id)

            return ResponseBuilder.success({
                'message': f"Successfully deleted source {source_id}"
            })
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Source deletion error: {str(e)}")
            return ResponseBuilder.error("Failed to delete source", status_code=500)

    # File Source Routes
    @data_source_bp.route('/file/upload', methods=['POST'])
    @jwt_required_with_user()
    def upload_file():
        """Upload file(s) to pipeline."""
        try:
            # Only collect necessary data
            files = request.files.getlist('files')
            metadata = {
                'user_id': g.current_user.id,
                **request.form.get('metadata', {})
            }
            
            results = []
            for file in files:
                # Pass to pipeline service
                result = file_service.handle_file_upload({
                    'file': file,
                    'metadata': metadata
                })
                results.append(result)
            
            return ResponseBuilder.success({'results': results})
        except Exception as e:
            logger.error(f"File upload error: {str(e)}")
            return ResponseBuilder.error("Upload failed", status_code=500)
        
    @data_source_bp.route('/file/<file_id>/parse', methods=['POST'])
    @jwt_required_with_user()
    def parse_file(file_id):
        """Parse uploaded file."""
        try:
            # 1. Validate access
            source, _ = validate_source_access(file_id)
            
            # 2. Process parse options
            parse_options = request.get_json()
            
            # 3. Parse file
            result = file_service.parse_file(file_id, parse_options)
            
            # 4. Update source with parsed info
            file_service.update_source_after_parse(file_id, result)
            
            return ResponseBuilder.success({
                'result': FileSourceResponseSchema().dump(result)
            })
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=400)
        except Exception as e:
            logger.error(f"File parsing error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Parsing failed", status_code=500)

    # Database Source Routes
    @data_source_bp.route('/database/connect', methods=['POST'])
    @jwt_required_with_user()
    def connect_database():
        """Connect to database source."""
        try:
            # 1. Validate request
            schema = DatabaseSourceConfigSchema()
            config = schema.load(request.get_json())

            # 2. Process connection
            processed_config = db_service.process_connection_config(config)
            
            # 3. Test connection before saving
            db_service.test_connection_config(processed_config)
            
            # 4. Create source after successful test
            result = db_service.create_source(processed_config)
            
            return ResponseBuilder.success(
                DatabaseSourceResponseSchema().dump(result)
            )
        except ValidationError as e:
            return ResponseBuilder.error(
                "Validation error", 
                details=e.messages, 
                status_code=400
            )
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Connection failed", status_code=500)

    @data_source_bp.route('/database/<connection_id>/test', methods=['POST'])
    @jwt_required_with_user()
    def test_database_connection(connection_id):
        """Test database connection."""
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Test connection
            result = db_service.test_connection(connection_id)
            
            # 3. Update source status based on test
            db_service.update_connection_status(connection_id, result)
            
            return ResponseBuilder.success({'status': result})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Database test error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Connection test failed", status_code=500)

    @data_source_bp.route('/database/<connection_id>/schema', methods=['GET'])
    @jwt_required_with_user()
    def get_database_schema(connection_id):
        """Get database schema."""
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id, require_owner=False)
            
            # 2. Fetch schema
            schema = db_service.get_schema(connection_id)
            
            # 3. Update source metadata with schema info
            db_service.update_schema_metadata(connection_id, schema)
            
            return ResponseBuilder.success({'schema': schema})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Schema fetch error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to fetch schema", status_code=500)

    @data_source_bp.route('/database/<connection_id>/query', methods=['POST'])
    @jwt_required_with_user()
    def execute_database_query(connection_id):
        """Execute database query."""
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Get query data
            query_data = request.get_json()
            
            # 3. Validate and process query
            processed_query = db_service.process_query(query_data)
            
            # 4. Execute query
            result = db_service.execute_query(connection_id, processed_query)
            
            return ResponseBuilder.success({'result': result})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=400)
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Query failed", status_code=500)
        
    # API Source Routes
    @data_source_bp.route('/api/connect', methods=['POST'])
    @jwt_required_with_user()
    def connect_api():
        """Pass API connection request to pipeline."""
        try:
            api_data = {
                'config': request.get_json(),
                'user_id': g.current_user.id
            }
            
            result = api_service.handle_api_connection(api_data)
            return ResponseBuilder.success({'result': result})
        except Exception as e:
            logger.error(f"API connection error: {str(e)}")
            return ResponseBuilder.error("Connection failed", status_code=500)
        
    @data_source_bp.route('/api/<connection_id>/execute', methods=['POST'])
    @jwt_required_with_user()
    def execute_api_request(connection_id):
        """Execute API request."""
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Process request data
            request_data = request.get_json()
            processed_request = api_service.process_api_request(request_data)
            
            # 3. Execute request
            result = api_service.execute_request(connection_id, processed_request)
            
            # 4. Update source metrics after execution
            api_service.update_execution_metrics(connection_id, result)
            
            return ResponseBuilder.success({'result': result})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=400)
        except Exception as e:
            logger.error(f"API execution error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Request failed", status_code=500)

    @data_source_bp.route('/api/<connection_id>/test', methods=['POST'])
    @jwt_required_with_user()
    def test_api_connection(connection_id):
        """Test API connection."""
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Test connection
            result = api_service.test_connection(connection_id)
            
            # 3. Update source status
            api_service.update_connection_status(connection_id, result)
            
            return ResponseBuilder.success({'status': result})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"API test error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Connection test failed", status_code=500)

    # S3 Source Routes
    @data_source_bp.route('/s3/connect', methods=['POST'])
    @jwt_required_with_user()
    def connect_s3():
        """Connect to S3 bucket."""
        try:
            # 1. Validate request
            schema = S3SourceConfigSchema()
            config = schema.load(request.get_json())
            config['user_id'] = g.current_user.id

            # 2. Process S3 configuration
            processed_config = s3_service.process_s3_config(config)
            
            # 3. Test S3 connection
            s3_service.test_s3_connection(processed_config)
            
            # 4. Create source after successful test
            result = s3_service.create_source(processed_config)
            
            return ResponseBuilder.success(
                S3SourceResponseSchema().dump(result)
            )
        except ValidationError as e:
            return ResponseBuilder.error(
                "Validation error", 
                details=e.messages, 
                status_code=400
            )
        except Exception as e:
            logger.error(f"S3 connection error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Connection failed", status_code=500)

    @data_source_bp.route('/s3/<connection_id>/list', methods=['GET'])
    @jwt_required_with_user()
    def list_s3_objects(connection_id):
        """List objects in S3 bucket."""
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Get and process listing parameters
            prefix = request.args.get('prefix', '')
            processed_params = s3_service.process_listing_params({
                'prefix': prefix,
                'max_keys': request.args.get('max_keys', 1000),
                'delimiter': request.args.get('delimiter', '/'),
                'continuation_token': request.args.get('continuation_token')
            })
            
            # 3. List objects
            objects = s3_service.list_objects(connection_id, processed_params)
            
            # 4. Update source metadata with listing info
            s3_service.update_listing_metadata(connection_id, objects)
            
            return ResponseBuilder.success({'objects': objects})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"S3 list error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to list objects", status_code=500)

    @data_source_bp.route('/s3/<connection_id>/download', methods=['POST'])
    @jwt_required_with_user()
    def initiate_s3_download(connection_id):
        """Initiate S3 object download."""
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Process download request
            request_data = request.get_json()
            processed_request = s3_service.process_download_request(request_data)
            
            # 3. Generate download URL/credentials
            download_info = s3_service.initiate_download(
                connection_id, 
                processed_request
            )
            
            # 4. Update source metrics
            s3_service.update_download_metrics(connection_id, download_info)
            
            return ResponseBuilder.success({'download': download_info})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=400)
        except Exception as e:
            logger.error(f"S3 download error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to initiate download", status_code=500)

    @data_source_bp.route('/s3/<connection_id>/upload', methods=['POST'])
    @jwt_required_with_user()
    def initiate_s3_upload(connection_id):
        """Initiate S3 object upload."""
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Process upload request
            request_data = request.get_json()
            processed_request = s3_service.process_upload_request(request_data)
            
            # 3. Generate upload URL/credentials
            upload_info = s3_service.initiate_upload(
                connection_id, 
                processed_request
            )
            
            # 4. Update source metrics
            s3_service.update_upload_metrics(connection_id, upload_info)
            
            return ResponseBuilder.success({'upload': upload_info})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=400)
        except Exception as e:
            logger.error(f"S3 upload error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to initiate upload", status_code=500)

# Stream Source Routes
    @data_source_bp.route('/stream/connect', methods=['POST'])
    @jwt_required_with_user()
    def connect_stream():
        """Connect to stream source."""
        try:
            # 1. Validate request
            schema = StreamSourceConfigSchema()
            config = schema.load(request.get_json())
            config['user_id'] = g.current_user.id

            # 2. Process stream configuration
            processed_config = stream_service.process_stream_config(config)
            
            # 3. Test stream connection
            stream_service.test_stream_connection(processed_config)
            
            # 4. Create source after successful test
            result = stream_service.create_source(processed_config)
            
            return ResponseBuilder.success(
                StreamSourceResponseSchema().dump(result)
            )
        except ValidationError as e:
            return ResponseBuilder.error(
                "Validation error", 
                details=e.messages, 
                status_code=400
            )
        except Exception as e:
            logger.error(f"Stream connection error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Connection failed", status_code=500)

    @data_source_bp.route('/stream/<connection_id>/status', methods=['GET'])
    @jwt_required_with_user()
    def get_stream_status(connection_id):
        """Get stream connection status."""
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Get status with metrics
            status = stream_service.get_status_with_metrics(connection_id)
            
            # 3. Update source metrics
            stream_service.update_status_metrics(connection_id, status)
            
            return ResponseBuilder.success({'status': status})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Stream status error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get status", status_code=500)

    @data_source_bp.route('/stream/<connection_id>/consume', methods=['POST'])
    @jwt_required_with_user()
    def start_stream_consumption(connection_id):
        """Start consuming from stream."""
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Process consumption config
            config = request.get_json()
            processed_config = stream_service.process_consumption_config(config)
            
            # 3. Start consumption
            result = stream_service.start_consumption(connection_id, processed_config)
            
            # 4. Update source status
            stream_service.update_consumption_status(connection_id, result)
            
            return ResponseBuilder.success({'consumption': result})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=400)
        except Exception as e:
            logger.error(f"Stream consumption error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to start consumption", status_code=500)

    # Utility Routes
    @data_source_bp.route('/<source_id>/validate', methods=['POST'])
    @jwt_required_with_user()
    def validate_source(source_id):
        """Validate a data source configuration."""
        try:
            # 1. Validate access
            source, service = validate_source_access(source_id)
            
            # 2. Process validation rules
            validation_config = request.get_json() or {}
            processed_rules = service.process_validation_rules(validation_config)
            
            # 3. Perform validation
            result = service.validate_source(source_id, processed_rules)
            
            # 4. Update source validation status
            service.update_validation_status(source_id, result)
            
            return ResponseBuilder.success({'validation': result})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return ResponseBuilder.error("Failed to validate source", status_code=500)

    @data_source_bp.route('/<source_id>/preview', methods=['GET'])
    @jwt_required_with_user()
    def preview_source(source_id):
        """Preview data from a source."""
        try:
            # 1. Validate access
            source, service = validate_source_access(source_id)
            
            # 2. Process preview parameters
            params = {
                'limit': request.args.get('limit', 100, type=int),
                'offset': request.args.get('offset', 0, type=int),
                'filters': request.args.get('filters', {})
            }
            processed_params = service.process_preview_params(params)
            
            # 3. Get preview data
            preview_data = service.preview_data(source_id, processed_params)
            
            # 4. Update preview metrics
            service.update_preview_metrics(source_id, preview_data)
            
            return ResponseBuilder.success({'preview': preview_data})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Preview error: {str(e)}")
            return ResponseBuilder.error("Failed to preview source", status_code=500)

    @data_source_bp.route('/<source_id>/health', methods=['GET'])
    @jwt_required_with_user()
    def get_source_health(source_id):
        """Get source health status."""
        try:
            # 1. Validate access
            source, service = validate_source_access(source_id)
            
            # 2. Get health metrics
            health = service.get_health_with_metrics(source_id)
            
            # 3. Update health status
            service.update_health_status(source_id, health)
            
            return ResponseBuilder.success({'health': health})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return ResponseBuilder.error("Failed to check health", status_code=500)

    @data_source_bp.route('/<source_id>/sync', methods=['POST'])
    @jwt_required_with_user()
    def sync_source(source_id):
        """Synchronize a data source."""
        try:
            # 1. Validate access
            source, service = validate_source_access(source_id)
            
            # 2. Process sync parameters
            sync_config = request.get_json() or {}
            processed_config = service.process_sync_config(sync_config)
            
            # 3. Perform sync
            sync_result = service.sync_source(source_id, processed_config)
            
            # 4. Update sync status
            service.update_sync_status(source_id, sync_result)
            
            return ResponseBuilder.success({'sync': sync_result})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Sync error: {str(e)}")
            return ResponseBuilder.error("Failed to sync source", status_code=500)

    # Error handlers
    @data_source_bp.errorhandler(404)
    def not_found_error(error):
        return ResponseBuilder.error("Resource not found", status_code=404)

    @data_source_bp.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}", exc_info=True)
        return ResponseBuilder.error("Internal server error", status_code=500)

    return data_source_bp