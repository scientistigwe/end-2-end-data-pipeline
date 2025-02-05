# api/fastapi_app/routers/pipeline.py

from fastapi import APIRouter, Depends, HTTPException, Security, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from uuid import UUID
import logging
from datetime import datetime

from api.fastapi_app.dependencies.database import get_db_session
from api.fastapi_app.dependencies.auth import get_current_user, require_permission
from api.fastapi_app.dependencies.services import get_pipeline_service, get_staging_manager
from core.services.pipeline import PipelineService
from core.managers.staging import StagingManager
from api.fastapi_app.schemas.staging.pipeline import (
    PipelineRequest,
    PipelineResponse,
    PipelineStatusResponse,
    PipelineLogsResponse,
    PipelineMetricsResponse,
    PipelineListResponse
)
from core.messaging.event_types import (
    ComponentType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingContext
)

logger = logging.getLogger(__name__)
router = APIRouter()

async def validate_pipeline_exists(
    pipeline_id: UUID,
    pipeline_service: PipelineService = Depends(get_pipeline_service)
) -> None:
    """Validate if pipeline exists"""
    if not await pipeline_service.pipeline_exists(pipeline_id):
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline {pipeline_id} not found"
        )

@router.get("/", response_model=PipelineListResponse)
async def list_pipelines(
    page: int = Query(1, gt=0),
    per_page: int = Query(10, gt=0, le=100),
    filters: Optional[Dict[str, Any]] = None,
    current_user: dict = Security(require_permission("pipeline:list")),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    pipeline_manager: Any = Depends(get_pipeline_service)
):
    """List pipelines with filtering and pagination"""
    try:
        # Get pipelines with runtime status
        pipelines = await pipeline_service.list_pipelines(
            filters=filters or {},
            page=page,
            per_page=per_page
        )

        # Enrich with runtime status
        for pipeline in pipelines['pipelines']:
            runtime_status = await pipeline_manager.get_pipeline_status(
                str(pipeline['id'])
            )
            if runtime_status:
                pipeline['runtime_status'] = runtime_status

        return {
            'pipelines': pipelines['pipelines'],
            'total_count': pipelines['total_count'],
            'page': page,
            'per_page': per_page
        }
    except Exception as e:
        logger.error(f"Error retrieving pipelines: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving pipelines")

@router.post("/", response_model=PipelineResponse, status_code=201)
async def create_pipeline(
    pipeline_data: PipelineRequest,
    current_user: dict = Security(require_permission("pipeline:create")),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Create new pipeline with staging integration"""
    try:
        # Add user context
        pipeline_data_dict = pipeline_data.dict()
        pipeline_data_dict['user_id'] = current_user['id']

        # Stage initial configuration
        staging_ref = await staging_manager.stage_data(
            data=pipeline_data_dict,
            component_type=ComponentType.PIPELINE_SERVICE,
            pipeline_id=None,  # Will be set after creation
            metadata={
                'request_type': 'pipeline_creation',
                'user_id': current_user['id']
            }
        )

        # Create pipeline with staging reference
        pipeline = await pipeline_service.create_pipeline(
            pipeline_data_dict,
            staging_ref=staging_ref
        )

        # Update staging reference with pipeline ID
        await staging_manager.update_reference(
            staging_ref,
            {'pipeline_id': str(pipeline['id'])}
        )

        return pipeline

    except Exception as e:
        logger.error(f"Pipeline creation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Pipeline creation failed")

@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: UUID,
    current_user: dict = Security(require_permission("pipeline:read")),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    staging_manager: StagingManager = Depends(get_staging_manager),
    pipeline_manager: Any = Depends(get_pipeline_service)
):
    """Get comprehensive pipeline details"""
    try:
        await validate_pipeline_exists(pipeline_id, pipeline_service)

        # Get base pipeline data
        pipeline = await pipeline_service.get_pipeline(pipeline_id)

        # Enrich with runtime status
        runtime_status = await pipeline_manager.get_pipeline_status(
            str(pipeline_id)
        )
        if runtime_status:
            pipeline['runtime_status'] = runtime_status

        # Get staged outputs if available
        staged_outputs = await staging_manager.get_pipeline_outputs(
            str(pipeline_id)
        )
        if staged_outputs:
            pipeline['staged_outputs'] = staged_outputs

        return pipeline

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving pipeline {pipeline_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving pipeline {pipeline_id}")

@router.post("/{pipeline_id}/start")
async def start_pipeline(
    pipeline_id: UUID,
    config: Optional[PipelineRequest] = None,
    current_user: dict = Security(require_permission("pipeline:execute")),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """Start pipeline execution"""
    try:
        await validate_pipeline_exists(pipeline_id, pipeline_service)

        # Create processing context
        context = ProcessingContext(
            pipeline_id=str(pipeline_id),
            stage=ProcessingStage.RECEPTION,
            status=ProcessingStatus.PENDING,
            metadata={
                'start_config': config.dict() if config else {},
                'user_id': current_user['id']
            }
        )

        # Start pipeline with context
        result = await pipeline_service.start_pipeline(
            pipeline_id,
            context=context
        )

        return {
            'status': 'started',
            'pipeline_id': str(pipeline_id),
            'context_id': str(context.request_id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start pipeline {pipeline_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline {pipeline_id}")

@router.get("/{pipeline_id}/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(
    pipeline_id: UUID,
    current_user: dict = Security(require_permission("pipeline:read")),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    staging_manager: StagingManager = Depends(get_staging_manager),
    pipeline_manager: Any = Depends(get_pipeline_service)
):
    """Get comprehensive pipeline status"""
    try:
        await validate_pipeline_exists(pipeline_id, pipeline_service)

        # Get persisted status
        db_status = await pipeline_service.get_pipeline_status(pipeline_id)

        # Get runtime status
        runtime_status = await pipeline_manager.get_pipeline_status(
            str(pipeline_id)
        )

        # Get staging status
        staging_status = await staging_manager.get_pipeline_status(
            str(pipeline_id)
        )

        # Combine all status information
        return {
            **db_status,
            'runtime_status': runtime_status or {},
            'staging_status': staging_status or {}
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for pipeline {pipeline_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status for pipeline {pipeline_id}"
        )

@router.get("/{pipeline_id}/logs", response_model=PipelineLogsResponse)
async def get_pipeline_logs(
    pipeline_id: UUID,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    level: Optional[str] = None,
    component: Optional[str] = None,
    current_user: dict = Security(require_permission("pipeline:read")),
    pipeline_service: PipelineService = Depends(get_pipeline_service)
):
    """Get filtered pipeline logs"""
    try:
        await validate_pipeline_exists(pipeline_id, pipeline_service)

        logs = await pipeline_service.get_pipeline_logs(
            pipeline_id,
            start_time=start_time,
            end_time=end_time,
            level=level,
            component=component
        )

        return {'logs': logs}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve logs for pipeline {pipeline_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve logs for pipeline {pipeline_id}"
        )

@router.get("/{pipeline_id}/metrics", response_model=PipelineMetricsResponse)
async def get_pipeline_metrics(
    pipeline_id: UUID,
    current_user: dict = Security(require_permission("pipeline:read")),
    pipeline_service: PipelineService = Depends(get_pipeline_service),
    staging_manager: StagingManager = Depends(get_staging_manager),
    pipeline_manager: Any = Depends(get_pipeline_service)
):
    """Get comprehensive pipeline metrics"""
    try:
        await validate_pipeline_exists(pipeline_id, pipeline_service)

        # Get metrics from multiple sources
        service_metrics = await pipeline_service.get_pipeline_metrics(pipeline_id)
        runtime_metrics = await pipeline_manager.get_pipeline_metrics(
            str(pipeline_id)
        )
        staging_metrics = await staging_manager.get_pipeline_metrics(
            str(pipeline_id)
        )

        # Combine metrics
        return {
            **service_metrics,
            'runtime_metrics': runtime_metrics or {},
            'staging_metrics': staging_metrics or {}
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve metrics for pipeline {pipeline_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metrics for pipeline {pipeline_id}"
        )