# api/fastapi_app/routers/pipeline.py

from fastapi import APIRouter, Depends, HTTPException, Security, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from uuid import UUID
import logging
from datetime import datetime

from config.database import get_db_session
from api.fastapi_app.middleware.auth_middleware import get_current_user, require_permission
from api.fastapi_app.dependencies.services import get_pipeline_service, get_staging_manager
from core.services.pipeline.pipeline_service import PipelineService
from core.managers.staging_manager import StagingManager
from api.fastapi_app.schemas.staging import (
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

from core.services.monitoring import MonitoringService
from api.fastapi_app.schemas.staging import (
    MonitoringStagingRequestSchema,
    MonitoringStagingResponseSchema,
    AlertStagingRequestSchema,
    AlertStagingResponseSchema
)
from .data_sources import validate_source_access

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

# ================ Monitoring Routes =================================

def get_services(db: AsyncSession = Depends(get_db_session)):
    """Get required services"""
    return {
        'monitoring_service': MonitoringService(db),
        'staging_manager': StagingManager(db)
    }

@router.post("/{pipeline_id}/metrics", response_model=Dict[str, Any])
async def collect_metrics(
    pipeline_id: UUID,
    data: MonitoringStagingRequestSchema,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """Collect and store metrics with staging integration"""
    try:
        metrics_data = data.dict()
        metrics_data['pipeline_id'] = str(pipeline_id)

        # Stage metrics collection request
        staging_ref = await services['staging_manager'].stage_data(
            data=metrics_data,
            component_type=ComponentType.MONITORING_MANAGER,
            pipeline_id=str(pipeline_id),
            metadata={
                'metrics': data.metrics,
                'time_window': data.time_window,
                'aggregation': data.aggregation
            }
        )

        collection_result = await services['monitoring_service'].collect_metrics(
            metrics_data,
            staging_ref
        )

        return {
            'collection_id': str(collection_result.id),
            'status': collection_result.status.value,
            'staging_reference': staging_ref
        }
    except Exception as e:
        logger.error(f"Failed to collect metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to collect metrics")

@router.get("/{pipeline_id}/metrics/aggregated", response_model=MonitoringStagingResponseSchema)
async def get_aggregated_metrics(
    pipeline_id: UUID,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """Get aggregated metrics with comprehensive analysis"""
    try:
        metrics_data = await services['monitoring_service'].get_aggregated_metrics(pipeline_id)

        if metrics_data.staging_reference:
            historical_data = await services['staging_manager'].get_historical_metrics(
                metrics_data.staging_reference
            )
            metrics_data.historical_context = historical_data

        return metrics_data
    except Exception as e:
        logger.error(f"Failed to get aggregated metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get aggregated metrics")

@router.post("/{pipeline_id}/alerts/configure", response_model=Dict[str, Any])
async def configure_alerts(
    pipeline_id: UUID,
    config: AlertStagingRequestSchema,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """Configure alert rules with staging integration"""
    try:
        config_data = config.dict()
        config_data['pipeline_id'] = str(pipeline_id)

        staging_ref = await services['staging_manager'].stage_data(
            data=config_data,
            component_type=ComponentType.MONITORING_MANAGER,
            pipeline_id=str(pipeline_id),
            metadata={
                'alert_type': config.alert_type,
                'severity': config.severity,
                'config_time': datetime.utcnow().isoformat()
            }
        )

        config_result = await services['monitoring_service'].configure_alerts(
            config_data,
            staging_ref
        )

        return {
            'config_id': str(config_result.id),
            'status': 'configured',
            'staging_reference': staging_ref
        }
    except Exception as e:
        logger.error(f"Failed to configure alerts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to configure alerts")

@router.get("/{pipeline_id}/alerts", response_model=List[AlertStagingResponseSchema])
async def get_active_alerts(
    pipeline_id: UUID,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """Get active alerts with context"""
    try:
        alerts = await services['monitoring_service'].get_active_alerts(pipeline_id)

        # Add context from staging
        for alert in alerts:
            if alert.staging_reference:
                alert_context = await services['staging_manager'].get_alert_context(
                    alert.staging_reference
                )
                alert.context = alert_context

        return alerts
    except Exception as e:
        logger.error(f"Failed to get active alerts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get active alerts")

@router.post("/{pipeline_id}/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    pipeline_id: UUID,
    alert_id: UUID,
    notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """Acknowledge an alert with staging update"""
    try:
        acknowledgment_data = {
            'acknowledged_by': current_user['id'],
            'acknowledged_at': datetime.utcnow().isoformat(),
            'notes': notes
        }

        staging_ref = await services['staging_manager'].stage_data(
            data=acknowledgment_data,
            component_type=ComponentType.MONITORING_MANAGER,
            pipeline_id=str(pipeline_id),
            metadata={
                'operation': 'alert_acknowledgment',
                'alert_id': str(alert_id)
            }
        )

        result = await services['monitoring_service'].acknowledge_alert(
            alert_id,
            acknowledgment_data,
            staging_ref
        )

        return {
            'status': 'acknowledged',
            'alert_id': str(alert_id),
            'staging_reference': staging_ref
        }
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")

@router.get("/{pipeline_id}/performance")
async def get_performance_metrics(
    pipeline_id: UUID,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """Get comprehensive performance metrics"""
    try:
        metrics = await services['monitoring_service'].get_performance_metrics(pipeline_id)

        if metrics.staging_reference:
            historical_data = await services['staging_manager'].get_historical_performance(
                metrics.staging_reference
            )
            metrics.historical_performance = historical_data

        return {'performance': metrics}
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")

@router.get("/{pipeline_id}/resources")
async def get_resource_usage(
    pipeline_id: UUID,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """Get detailed resource usage statistics"""
    try:
        resources = await services['monitoring_service'].get_resource_usage(pipeline_id)

        if resources.staging_reference:
            resource_metrics = await services['staging_manager'].get_resource_metrics(
                resources.staging_reference
            )
            resources.detailed_metrics = resource_metrics

        return {'resources': resources}
    except Exception as e:
        logger.error(f"Failed to get resource usage: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get resource usage")

# Health check endpoints
@router.get("/{source_id}/health", response_model=Dict[str, Any])
async def check_source_health(
        source_id: UUID,
        current_user: dict = Depends(get_current_user),
        services: Dict[str, Any] = Depends(get_services)
):
    """Check health status of a data source"""
    try:
        source, service = await validate_source_access(source_id, current_user, services)
        health_status = await service.check_health(str(source_id))
        return {'health_status': health_status}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check source health")
