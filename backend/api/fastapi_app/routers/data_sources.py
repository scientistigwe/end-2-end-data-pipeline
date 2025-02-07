# api/fastapi_app/routers/data_sources.py

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
import logging
from uuid import UUID

from api.fastapi_app.dependencies.database import get_db_session
from api.fastapi_app.dependencies.auth import get_current_user
from api.fastapi_app.schemas.data_sources import (
    FileUploadRequest,
    FileUploadResponse,
    FileSourceResponse,
    DatabaseSourceResponse,
    S3SourceResponse,
    APISourceResponse,
    StreamSourceResponse,
    DatabaseSourceConfig,
    S3SourceConfig,
    APISourceConfig,
    StreamSourceConfig,
    DataSourceRequest,
    DataSourceResponse
)

from data.source.file import FileService
from data.source.database import DatabaseService
from data.source.cloud import S3Service
from data.source.api import APIService
from data.source.stream import StreamService

logger = logging.getLogger(__name__)
router = APIRouter()


# Service dependency injection
def get_services(db: AsyncSession = Depends(get_db_session)):
    """Get all required services"""
    return {
        'file': FileService(db),
        'db': DatabaseService(db),
        's3': S3Service(db),
        'api': APIService(db),
        'stream': StreamService(db)
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


@router.get("/", response_model=Dict[str, List[DataSourceResponse]])
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


@router.post("/", response_model=DataSourceResponse)
async def create_source(
        data: DataSourceRequest,
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


@router.get("/{source_id}", response_model=DataSourceResponse)
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


@router.put("/{source_id}", response_model=DataSourceResponse)
async def update_source(
        source_id: UUID,
        data: DataSourceRequest,
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


@router.post("/file/upload", response_model=FileUploadResponse)
async def upload_file(
        file: UploadFile = File(...),
        metadata: str = Form(...),
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Upload a file as a data source"""
    try:
        result = await services['file'].process_file_upload(
            file=file,
            metadata=metadata,
            user_id=current_user['id']
        )

        if result.get('status') == 'error':
            raise HTTPException(
                status_code=400,
                detail=result.get('message', 'Upload failed')
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Upload failed")


# Database connections
@router.post("/db/connect", response_model=DatabaseSourceResponse)
async def connect_database(
        config: DatabaseSourceConfig,
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


@router.post("/s3/connect", response_model=S3SourceResponse)
async def connect_s3(
        config: S3SourceConfig,
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


@router.post("/api/connect", response_model=APISourceResponse)
async def connect_api(
        config: APISourceConfig,
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


@router.post("/stream/connect", response_model=StreamSourceResponse)
async def connect_stream(
        config: StreamSourceConfig,
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