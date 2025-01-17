# backend/api/app/routes/data_sources/data_source_routes.py
from flask import Blueprint, request, g, current_app, send_file
from marshmallow import ValidationError
from typing import Dict, Any, Tuple
import logging
import os

from backend.data_pipeline.source.file.file_service import FileService
from backend.data_pipeline.source.database.db_service import DBService
from backend.data_pipeline.source.cloud.s3_service import S3Service
from backend.data_pipeline.source.api.api_service import APIService
from backend.data_pipeline.source.stream.stream_service import StreamService

from ...schemas.data_sources import (
    FileUploadRequestSchema,
    DatabaseSourceConfigSchema,
    S3SourceConfigSchema,
    APISourceConfigSchema,
    StreamSourceConfigSchema,
    DataSourceRequestSchema,
    DataSourceResponseSchema,
    FileSourceResponseSchema,
    DatabaseSourceResponseSchema,
    S3SourceResponseSchema,
    APISourceResponseSchema,
    StreamSourceResponseSchema
)
from ...utils.response_builder import ResponseBuilder
from ...middleware.auth_middleware import jwt_required_with_user

logger = logging.getLogger(__name__)

def create_data_source_blueprint(
    file_service: FileService,
    db_service: DBService,
    s3_service: S3Service,
    api_service: APIService,
    stream_service: StreamService
) -> Blueprint:
    """
    Create comprehensive data source blueprint with routes for all source types
    
    Args:
        file_service (FileService): File service
        db_service (DBService): Database service
        s3_service (S3Service): S3 service
        api_service (APIService): API service
        stream_service (StreamService): Stream service
    
    Returns:
        Blueprint: Flask blueprint with data source routes
    """
    data_source_bp = Blueprint('data_sources', __name__)

    def get_service_by_type(source_type: str):
        """
        Helper function to get appropriate service by type
        
        Args:
            source_type (str): Type of data source
        
        Returns:
            Service object for the given source type
        """
        services = {
            'file': file_service,
            'db': db_service,
            's3': s3_service,
            'api': api_service,
            'stream': stream_service
        }
        return services.get(source_type)

    def get_response_schema_by_type(source_type: str):
        """
        Get appropriate response schema by source type
        
        Args:
            source_type (str): Type of data source
        
        Returns:
            Marshmallow schema for the given source type
        """
        schemas = {
            'file': FileSourceResponseSchema,
            'db': DatabaseSourceResponseSchema,
            's3': S3SourceResponseSchema,
            'api': APISourceResponseSchema,
            'stream': StreamSourceResponseSchema
        }
        return schemas.get(source_type, DataSourceResponseSchema)

    def validate_source_access(source_id: str, require_owner: bool = True) -> Tuple[Any, Any]:
        """
        Validate source access and return source with service
        
        Args:
            source_id (str): Unique source identifier
            require_owner (bool, optional): Whether to check owner. Defaults to True.
        
        Returns:
            Tuple of (source, service)
        
        Raises:
            ValueError: If source not found or not authorized
        """
        # Attempt to find source across all services
        services = [file_service, db_service, s3_service, api_service, stream_service]
        for service in services:
            try:
                source = service.get_source(source_id)
                if source:
                    # Check owner if required
                    if require_owner and source.get('owner_id') != g.current_user.id:
                        raise ValueError("Not authorized to access this source")
                    return source, service
            except Exception:
                continue
        
        raise ValueError("Source not found")

    @data_source_bp.route('/', methods=['GET'])
    @jwt_required_with_user()
    def list_sources():
        """
        List all data sources for the current user
        
        Returns:
            JSON response with list of sources by type
        """
        try:
            # Get sources by type for current user
            sources = {
                'files': file_service.list_sources(g.current_user.id),
                'databases': db_service.list_sources(g.current_user.id),
                's3': s3_service.list_sources(g.current_user.id),
                'apis': api_service.list_sources(g.current_user.id),
                'streams': stream_service.list_sources(g.current_user.id)
            }

            return ResponseBuilder.success({'sources': sources})
        except Exception as e:
            logger.error(f"Error listing sources: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to list sources", status_code=500)

    @data_source_bp.route('/', methods=['POST'])
    @jwt_required_with_user()
    def create_source():
        """
        Create a new data source
        
        Returns:
            JSON response with created source details
        """
        try:
            # Log the raw request data for debugging
            request_data = request.get_json()
            logger.info(f"Received create source request: {request_data}")

            # 1. Validate request data
            schema = DataSourceRequestSchema()
            data = schema.load(request_data)
            data['user_id'] = g.current_user.id

            # 2. Get appropriate service
            service = get_service_by_type(data['type'])
            if not service:
                return ResponseBuilder.error(
                    f"Invalid source type: {data['type']}", 
                    status_code=400
                )

            # 3. Get appropriate response schema
            response_schema = get_response_schema_by_type(data['type'])

            # 4. Create source 
            result = service.process_connection_request(data)

            return ResponseBuilder.success({
                'source': response_schema().dump(result)
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
        """
        Get specific data source details
        
        Args:
            source_id (str): Unique source identifier
        
        Returns:
            JSON response with source details
        """
        try:
            # 1. Validate access
            source, service = validate_source_access(source_id, require_owner=False)
            
            # 2. Get appropriate response schema
            response_schema = get_response_schema_by_type(source.get('type'))
            
            # 3. Return source details
            return ResponseBuilder.success({
                'source': response_schema().dump(source)
            })
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Error getting source: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get source", status_code=500)

    @data_source_bp.route('/<source_id>', methods=['PUT'])
    @jwt_required_with_user()
    def update_source(source_id):
        """
        Update a data source
        
        Args:
            source_id (str): Unique source identifier
        
        Returns:
            JSON response with updated source details
        """
        try:
            # 1. Validate request data
            schema = DataSourceRequestSchema()
            update_data = schema.load(request.get_json())

            # 2. Validate access and get service
            source, service = validate_source_access(source_id)

            # 3. Get appropriate response schema
            response_schema = get_response_schema_by_type(source.get('type'))

            # 4. Apply update
            updated_source = service.process_connection_request({
                **source,
                **update_data
            })

            return ResponseBuilder.success({
                'source': response_schema().dump(updated_source)
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
        """
        Delete a data source
        
        Args:
            source_id (str): Unique source identifier
        
        Returns:
            JSON response with deletion status
        """
        try:
            # 1. Validate access
            source, service = validate_source_access(source_id)

            # 2. Delete source
            service.close_connection(source_id)

            return ResponseBuilder.success({
                'message': f"Successfully deleted source {source_id}"
            })
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Source deletion error: {str(e)}")
            return ResponseBuilder.error("Failed to delete source", status_code=500)

    @data_source_bp.route('/<source_id>/preview', methods=['GET'])
    @jwt_required_with_user()
    def preview_source(source_id):
        """
        Preview data from a source
        
        Args:
            source_id (str): Unique source identifier
        
        Returns:
            JSON response with source preview
        """
        try:
            # 1. Validate access
            source, service = validate_source_access(source_id)
            
            # 2. Process preview parameters
            params = {
                'limit': request.args.get('limit', 100, type=int),
                'offset': request.args.get('offset', 0, type=int),
                'filters': request.args.get('filters', {})
            }
            
            # 3. Get preview data
            if hasattr(service, 'preview_file_data'):
                preview_data = service.preview_file_data(source_id, params)
            else:
                preview_data = service.get_schema_info(source_id, params)
            
            return ResponseBuilder.success({'preview': preview_data})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Preview error: {str(e)}")
            return ResponseBuilder.error("Failed to preview source", status_code=500)

    @data_source_bp.route('/db/connect', methods=['POST'])
    @jwt_required_with_user()
    def connect_database():
        """
        Connect to db source
        
        Returns:
            JSON response with db connection details
        """
        try:
            # 1. Validate request
            schema = DatabaseSourceConfigSchema()
            config = schema.load(request.get_json())
            config['user_id'] = g.current_user.id

            # 2. Process connection
            result = db_service.process_connection_request(config)
            
            return ResponseBuilder.success({
                'source': DatabaseSourceResponseSchema().dump(result)
            })
        except ValidationError as e:
            return ResponseBuilder.error(
                "Validation error", 
                details=e.messages, 
                status_code=400
            )
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Connection failed", status_code=500)

    @data_source_bp.route('/s3/connect', methods=['POST'])
    @jwt_required_with_user()
    def connect_s3():
        """
        Connect to S3 bucket
        
        Returns:
            JSON response with S3 connection details
        """
        try:
            # 1. Validate request
            schema = S3SourceConfigSchema()
            config = schema.load(request.get_json())
            config['user_id'] = g.current_user.id

            # 2. Process S3 configuration and connection
            result = s3_service.process_connection_request(config)
            
            return ResponseBuilder.success({
                'source': S3SourceResponseSchema().dump(result)
            })
        except ValidationError as e:
            return ResponseBuilder.error(
                "Validation error", 
                details=e.messages, 
                status_code=400
            )
        except Exception as e:
            logger.error(f"S3 connection error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Connection failed", status_code=500)

    @data_source_bp.route('/api/connect', methods=['POST'])
    @jwt_required_with_user()
    def connect_api():
        """
        Connect to API source
        
        Returns:
            JSON response with API connection details
        """
        try:
            # 1. Validate request
            schema = APISourceConfigSchema()
            config = schema.load(request.get_json())
            config['user_id'] = g.current_user.id

            # 2. Process API configuration and connection
            result = api_service.process_connection_request(config)
            
            return ResponseBuilder.success({
                'source': APISourceResponseSchema().dump(result)
            })
        except ValidationError as e:
            return ResponseBuilder.error(
                "Validation error", 
                details=e.messages, 
                status_code=400
            )
        except Exception as e:
            logger.error(f"API connection error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Connection failed", status_code=500)

    @data_source_bp.route('/stream/connect', methods=['POST'])
    @jwt_required_with_user()
    def connect_stream():
        """
        Connect to stream source
        
        Returns:
            JSON response with stream connection details
        """
        try:
            # 1. Validate request
            schema = StreamSourceConfigSchema()
            config = schema.load(request.get_json())
            config['user_id'] = g.current_user.id

            # 2. Process stream configuration and connection
            result = stream_service.process_connection_request(config)
            
            return ResponseBuilder.success({
                'source': StreamSourceResponseSchema().dump(result)
            })
        except ValidationError as e:
            return ResponseBuilder.error(
                "Validation error", 
                details=e.messages, 
                status_code=400
            )
        except Exception as e:
            logger.error(f"Stream connection error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Connection failed", status_code=500)

    @data_source_bp.route('/db/<connection_id>/query', methods=['POST'])
    @jwt_required_with_user()
    def execute_database_query(connection_id):
        """
        Execute db query
        
        Args:
            connection_id (str): Database connection identifier

        Returns:
            JSON response with query results
        """
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Get query data
            query_data = request.get_json()
            
            # 3. Execute query
            result = db_service.process_query_request(connection_id, query_data)
            
            return ResponseBuilder.success({'result': result})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=400)
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Query failed", status_code=500)

    @data_source_bp.route('/api/<connection_id>/execute', methods=['POST'])
    @jwt_required_with_user()
    def execute_api_request(connection_id):
        """
        Execute API request
        
        Args:
            connection_id (str): API connection identifier
        
        Returns:
            JSON response with API request results
        """
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Process request data
            request_data = request.get_json()
            
            # 3. Execute request
            result = api_service.process_query_request(connection_id, request_data)
            
            return ResponseBuilder.success({'result': result})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=400)
        except Exception as e:
            logger.error(f"API execution error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Request failed", status_code=500)

    @data_source_bp.route('/s3/<connection_id>/list', methods=['GET'])
    @jwt_required_with_user()
    def list_s3_objects(connection_id):
        """
        List objects in S3 bucket
        
        Args:
            connection_id (str): S3 connection identifier
        
        Returns:
            JSON response with S3 object list
        """
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Get and process listing parameters
            params = {
                'prefix': request.args.get('prefix', ''),
                'max_keys': request.args.get('max_keys', 1000, type=int),
                'delimiter': request.args.get('delimiter', '/'),
                'continuation_token': request.args.get('continuation_token')
            }
            
            # 3. List objects
            objects = s3_service.list_objects(connection_id, params)
            
            return ResponseBuilder.success({'objects': objects})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"S3 list error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to list objects", status_code=500)

    @data_source_bp.route('/stream/<connection_id>/status', methods=['GET'])
    @jwt_required_with_user()
    def get_stream_status(connection_id):
        """
        Get stream connection status
        
        Args:
            connection_id (str): Stream connection identifier
        
        Returns:
            JSON response with stream status
        """
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Get status 
            status = stream_service.get_metrics(connection_id)
            
            return ResponseBuilder.success({'status': status})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=404)
        except Exception as e:
            logger.error(f"Stream status error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get status", status_code=500)

    @data_source_bp.route('/stream/<connection_id>/consume', methods=['POST'])
    @jwt_required_with_user()
    def start_stream_consumption(connection_id):
        """
        Start consuming from stream
        
        Args:
            connection_id (str): Stream connection identifier
        
        Returns:
            JSON response with consumption details
        """
        try:
            # 1. Validate access
            source, _ = validate_source_access(connection_id)
            
            # 2. Process consumption config
            config = request.get_json()
            
            # 3. Start consumption
            result = stream_service.process_consumer_request(connection_id, config)
            
            return ResponseBuilder.success({'consumption': result})
        except ValueError as e:
            return ResponseBuilder.error(str(e), status_code=400)
        except Exception as e:
            logger.error(f"Stream consumption error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to start consumption", status_code=500)

    # Error Handlers
    @data_source_bp.errorhandler(400)
    def bad_request_error(error):
        """
        Handle bad request errors
        
        Args:
            error: Error object
        
        Returns:
            JSON response with error details
        """
        logger.error(f"Bad request error: {str(error)}")
        return ResponseBuilder.error(
            "Bad request",
            details=str(error),
            status_code=400
        )

    @data_source_bp.errorhandler(404)
    def not_found_error(error):
        """
        Handle resource not found errors
        
        Args:
            error: Error object
        
        Returns:
            JSON response with error details
        """
        logger.error(f"Resource not found: {str(error)}")
        return ResponseBuilder.error(
            "Resource not found",
            details=str(error),
            status_code=404
        )

    @data_source_bp.errorhandler(500)
    def internal_server_error(error):
        """
        Handle internal server errors
        
        Args:
            error: Error object
        
        Returns:
            JSON response with error details
        """
        logger.error(f"Internal server error: {str(error)}", exc_info=True)
        return ResponseBuilder.error(
            "Internal server error",
            details=str(error),
            status_code=500
        )

    return data_source_bp