# api/fastapi_app/routers/data_sources.py

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
import logging
import asyncio
from uuid import UUID, uuid4
from pathlib import Path
import json
from config.database import get_db_session
from api.fastapi_app.middleware.auth_middleware import get_current_user
from core.control.cpm import ControlPointManager
from core.messaging.broker import MessageBroker
from core.managers.staging_manager import StagingManager
from db.repository.staging import StagingRepository
from api.fastapi_app.schemas.data_sources import (
    FileUploadRequestSchema,
    FileUploadResponseSchema,
    FileSourceResponseSchema,
    DatabaseSourceResponseSchema,
    S3SourceResponseSchema,
    APISourceResponseSchema,
    StreamSourceResponseSchema,
    DatabaseSourceConfigSchema,
    S3SourceConfigSchema,
    APISourceConfigSchema,
    StreamSourceConfigSchema,
    DataSourceRequestSchema,
    DataSourceResponseSchema
)

from data.source.file.file_service import FileService
from data.source.database.db_service import DatabaseService
from data.source.cloud.cloud_service import S3Service
from data.source.api.api_service import APIService
from data.source.stream.stream_service import StreamService

logger = logging.getLogger(__name__)
router = APIRouter()

# Global singleton instances
_message_broker_instance = None
_staging_repository_instance = None
_staging_manager_instance = None
_cpm_instance = None


# Dependency injection functions
def get_message_broker():
    """Get or create MessageBroker instance"""
    global _message_broker_instance
    if not _message_broker_instance:
        _message_broker_instance = MessageBroker()
    return _message_broker_instance


def get_staging_repository(db: AsyncSession = Depends(get_db_session)):
    """Get or create StagingRepository instance"""
    global _staging_repository_instance
    if not _staging_repository_instance:
        _staging_repository_instance = StagingRepository(db)
    return _staging_repository_instance


def get_staging_manager(
        message_broker=Depends(get_message_broker),
        repository=Depends(get_staging_repository),
        db: AsyncSession = Depends(get_db_session)
):
    """Get or create StagingManager instance"""
    global _staging_manager_instance
    if not _staging_manager_instance:
        # Create storage path if not exists
        storage_path = Path("./staged_data")
        storage_path.mkdir(parents=True, exist_ok=True)

        _staging_manager_instance = StagingManager(
            message_broker=message_broker,
            repository=repository,
            storage_path=storage_path,
            component_name="staging_manager",
            domain_type="staging"
        )
        # Initialize staging manager (non-blocking)
    return _staging_manager_instance


def get_control_point_manager(
        message_broker=Depends(get_message_broker),
        staging_manager=Depends(get_staging_manager)
):
    """Get or create ControlPointManager instance"""
    global _cpm_instance
    if not _cpm_instance:
        _cpm_instance = ControlPointManager(message_broker, staging_manager)
    return _cpm_instance


# Service dependency injection
def get_services(
        cpm: ControlPointManager = Depends(get_control_point_manager),
        staging_manager: StagingManager = Depends(get_staging_manager),
        db: AsyncSession = Depends(get_db_session)
):
    """Get all required services"""
    return {
        'file': FileService(staging_manager, cpm),  # Corrected order and removed unnecessary db parameter
        'db': DatabaseService(db, cpm),
        's3': S3Service(db, cpm),
        'api': APIService(db, cpm),
        'stream': StreamService(db, cpm)
    }

def get_service_by_type(services: Dict[str, Any], source_type: str):
    """Get appropriate service by type"""
    return services.get(source_type)

async def validate_source_access(
        source_id: UUID,
        current_user: dict,
        services: Dict[str, Any],
        require_owner: bool = True
) -> tuple[Any, Any]:
    """Validate source access and return source with service"""
    for service in services.values():
        try:
            source = await service.get_source(str(source_id))
            if source:
                if require_owner and source.get('owner_id') != current_user['id']:
                    raise HTTPException(
                        status_code=403,
                        detail="Not authorized to access this source"
                    )
                return source, service
        except Exception:
            continue

    raise HTTPException(status_code=404, detail="Source not found")

@router.get("/", response_model=Dict[str, List[DataSourceResponseSchema]])
async def list_sources(
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """List all data sources for the current user"""
    try:
        sources = {
            'files': await services['file'].list_sources(current_user['id']),
            'databases': await services['db'].list_sources(current_user['id']),
            's3': await services['s3'].list_sources(current_user['id']),
            'apis': await services['api'].list_sources(current_user['id']),
            'streams': await services['stream'].list_sources(current_user['id'])
        }
        return {'sources': sources}
    except Exception as e:
        logger.error(f"Error listing sources: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list sources")

@router.post("/", response_model=DataSourceResponseSchema)
async def create_source(
        data: DataSourceRequestSchema,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Create a new data source"""
    try:
        logger.info(f"Received create source request: {data.dict()}")

        # Get appropriate service
        service = get_service_by_type(services, data.type)
        if not service:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source type: {data.type}"
            )

        # Create source
        source_data = data.dict()
        source_data['user_id'] = current_user['id']
        result = await service.process_connection_request(source_data)

        return result
    except Exception as e:
        logger.error(f"Source creation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create source")

@router.get("/{source_id}", response_model=DataSourceResponseSchema)
async def get_source(
        source_id: UUID,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Get specific data source details"""
    try:
        source, _ = await validate_source_access(
            source_id, current_user, services, require_owner=False
        )
        return source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting source: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get source")

@router.put("/{source_id}", response_model=DataSourceResponseSchema)
async def update_source(
        source_id: UUID,
        data: DataSourceRequestSchema,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Update a data source"""
    try:
        source, service = await validate_source_access(source_id, current_user, services)

        update_data = data.dict()
        updated_source = await service.process_connection_request({
            **source,
            **update_data
        })

        return updated_source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Source update error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update source")

@router.delete("/{source_id}")
async def delete_source(
        source_id: UUID,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Delete a data source"""
    try:
        source, service = await validate_source_access(source_id, current_user, services)
        await service.close_connection(str(source_id))
        return {"message": f"Successfully deleted source {source_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Source deletion error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete source")


@router.post("/file/upload")
async def upload_file(
        file: UploadFile = File(...),
        metadata: Optional[str] = Form(None),
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Upload a file as a data source with enhanced error handling"""
    try:
        # Log incoming request details
        logger.info(f"File upload request: filename={file.filename}, content_type={file.content_type}")

        # Process metadata with robust error handling
        metadata_dict = {}
        if metadata:
            try:
                logger.info(f"Raw metadata received: {metadata[:200]}...")  # Log first 200 chars
                metadata_dict = json.loads(metadata)
                logger.info(f"Parsed metadata: {json.dumps(metadata_dict, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"Metadata JSON decode error: {str(e)}")
                # Continue with empty dict instead of failing

        # Extract file extension and type
        file_extension = file.filename.split(".")[-1].lower() if "." in file.filename else ""

        # Map file extension to type expected by backend
        file_type_map = {
            'csv': 'csv',
            'xlsx': 'excel',
            'xls': 'excel',
            'json': 'json',
            'parquet': 'parquet',
            'txt': 'csv'  # Default txt files to CSV
        }

        # Build normalized metadata with defaults
        normalized_metadata = {
            'file_type': metadata_dict.get('file_type', file_type_map.get(file_extension, 'csv')),
            'encoding': metadata_dict.get('encoding', 'utf-8'),
            'skip_rows': metadata_dict.get('skip_rows', 0),
            'tags': metadata_dict.get('tags', ['data']),
        }

        # Add type-specific fields
        if normalized_metadata['file_type'] == 'csv':
            normalized_metadata.update({
                'delimiter': metadata_dict.get('delimiter', ','),
                'has_header': metadata_dict.get('has_header', True),
            })

        if normalized_metadata['file_type'] == 'excel':
            normalized_metadata.update({
                'sheet_name': metadata_dict.get('sheet_name', 'Sheet1'),
                'has_header': metadata_dict.get('has_header', True),
            })

        # Ensure parse_options exists
        if 'parse_options' in metadata_dict:
            normalized_metadata['parse_options'] = metadata_dict['parse_options']
        else:
            normalized_metadata['parse_options'] = {
                'date_format': 'YYYY-MM-DD',
                'null_values': ['', 'null', 'NA', 'N/A'],
            }

        logger.info(f"Normalized metadata: {json.dumps(normalized_metadata, indent=2)}")

        # Process file upload
        try:
            file_service = services['file']
            result = await file_service.process_file_upload(
                file=file,
                metadata=normalized_metadata,
                user_id=current_user['id']
            )

            if result.get('status') == 'error':
                error_detail = result.get('error', 'Unknown error')
                logger.error(f"File service error: {error_detail}")
                return JSONResponse(
                    status_code=422,
                    content={
                        "status": "error",
                        "message": str(error_detail)
                    }
                )

            # Return successful result without validation
            logger.info(f"File upload successful: {result}")
            return result

        except Exception as service_err:
            logger.exception(f"File service error: {str(service_err)}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"File processing error: {str(service_err)}"
                }
            )

    except Exception as e:
        logger.exception(f"Unexpected upload error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            }
        )

# Database connections
@router.post("/db/connect", response_model=DatabaseSourceResponseSchema)
async def connect_database(
        config: DatabaseSourceConfigSchema,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Connect to database source"""
    try:
        config_data = config.dict()
        config_data['user_id'] = current_user['id']

        result = await services['db'].process_connection_request(config_data)
        return result
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Connection failed")

@router.post("/s3/connect", response_model=S3SourceResponseSchema)
async def connect_s3(
        config: S3SourceConfigSchema,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Connect to S3 bucket"""
    try:
        config_data = config.dict()
        config_data['user_id'] = current_user['id']

        result = await services['s3'].process_connection_request(config_data)
        return result
    except Exception as e:
        logger.error(f"S3 connection error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Connection failed")

@router.post("/api/connect", response_model=APISourceResponseSchema)
async def connect_api(
        config: APISourceConfigSchema,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Connect to API source"""
    try:
        config_data = config.dict()
        config_data['user_id'] = current_user['id']

        result = await services['api'].process_connection_request(config_data)
        return result
    except Exception as e:
        logger.error(f"API connection error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Connection failed")

@router.post("/stream/connect", response_model=StreamSourceResponseSchema)
async def connect_stream(
        config: StreamSourceConfigSchema,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Connect to stream source"""
    try:
        config_data = config.dict()
        config_data['user_id'] = current_user['id']

        result = await services['stream'].process_connection_request(config_data)
        return result
    except Exception as e:
        logger.error(f"Stream connection error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Connection failed")

@router.post("/db/{connection_id}/query", response_model=Dict[str, Any])
async def execute_database_query(
        connection_id: UUID,
        query_data: Dict[str, Any],
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Execute database query"""
    try:
        source, _ = await validate_source_access(connection_id, current_user, services)
        result = await services['db'].process_query_request(str(connection_id), query_data)
        return {'result': result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Query failed")

@router.post("/api/{connection_id}/execute", response_model=Dict[str, Any])
async def execute_api_request(
        connection_id: UUID,
        request_data: Dict[str, Any],
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Execute API request"""
    try:
        source, _ = await validate_source_access(connection_id, current_user, services)
        result = await services['api'].process_query_request(str(connection_id), request_data)
        return {'result': result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API execution error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Request failed")

@router.get("/s3/{connection_id}/list", response_model=Dict[str, Any])
async def list_s3_objects(
        connection_id: UUID,
        prefix: str = "",
        max_keys: int = 1000,
        delimiter: str = "/",
        continuation_token: Optional[str] = None,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """List objects in S3 bucket"""
    try:
        source, _ = await validate_source_access(connection_id, current_user, services)

        params = {
            'prefix': prefix,
            'max_keys': max_keys,
            'delimiter': delimiter,
            'continuation_token': continuation_token
        }

        objects = await services['s3'].list_objects(str(connection_id), params)
        return {'objects': objects}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"S3 list error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list objects")

@router.get("/stream/{connection_id}/status", response_model=Dict[str, Any])
async def get_stream_status(
        connection_id: UUID,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Get stream connection status"""
    try:
        source, _ = await validate_source_access(connection_id, current_user, services)
        status = await services['stream'].get_metrics(str(connection_id))
        return {'status': status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stream status error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get status")

@router.post("/stream/{connection_id}/consume", response_model=Dict[str, Any])
async def start_stream_consumption(
        connection_id: UUID,
        config: Dict[str, Any],
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Start consuming from stream"""
    try:
        source, _ = await validate_source_access(connection_id, current_user, services)
        result = await services['stream'].process_consumer_request(str(connection_id), config)
        return {'consumption': result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stream consumption error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start consumption")

@router.get("/{source_id}/preview", response_model=Dict[str, Any])
async def preview_source(
        source_id: UUID,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Preview data from a source"""
    try:
        source, service = await validate_source_access(source_id, current_user, services)

        params = {
            'limit': limit,
            'offset': offset,
            'filters': filters or {}
        }

        # Get preview data based on service type
        if hasattr(service, 'preview_file_data'):
            preview_data = await service.preview_file_data(str(source_id), params)
        else:
            preview_data = await service.get_schema_info(str(source_id), params)

        return {'preview': preview_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Preview error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to preview source")

# Add schema info endpoints
@router.get("/{source_id}/schema", response_model=Dict[str, Any])
async def get_source_schema(
        source_id: UUID,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Get schema information for a data source"""
    try:
        source, service = await validate_source_access(source_id, current_user, services)
        schema_info = await service.get_schema_info(str(source_id))
        return {'schema': schema_info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Schema info error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get schema information")

# Add validation endpoints
@router.post("/{source_id}/validate", response_model=Dict[str, Any])
async def validate_source_data(
        source_id: UUID,
        validation_rules: Dict[str, Any],
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Validate data source against specified rules"""
    try:
        source, service = await validate_source_access(source_id, current_user, services)
        validation_result = await service.validate_source(str(source_id), validation_rules)
        return {'validation_result': validation_result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate source")

# Add metadata endpoints
@router.get("/{source_id}/metadata", response_model=Dict[str, Any])
async def get_source_metadata(
        source_id: UUID,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Get metadata for a data source"""
    try:
        source, service = await validate_source_access(source_id, current_user, services)
        metadata = await service.get_metadata(str(source_id))
        return {'metadata': metadata}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metadata error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get source metadata")