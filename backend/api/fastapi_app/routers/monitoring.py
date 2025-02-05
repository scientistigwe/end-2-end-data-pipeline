# api/fastapi_app/routers/monitoring.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import logging

from api.fastapi_app.dependencies.database import get_db_session
from api.fastapi_app.dependencies.auth import get_current_user
from core.services.monitoring import MonitoringService
from core.managers.staging import StagingManager
from api.fastapi_app.schemas.staging.monitoring import (
    MonitoringStagingRequest,
    MonitoringStagingResponse,
    AlertStagingRequest,
    AlertStagingResponse
)
from core.messaging.event_types import ComponentType

logger = logging.getLogger(__name__)
router = APIRouter()

def get_services(db: AsyncSession = Depends(get_db_session)):
    """Get required services"""
    return {
        'monitoring_service': MonitoringService(db),
        'staging_manager': StagingManager(db)
    }

@router.post("/{pipeline_id}/metrics", response_model=Dict[str, Any])
async def collect_metrics(
    pipeline_id: UUID,
    data: MonitoringStagingRequest,
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

@router.get("/{pipeline_id}/metrics/aggregated", response_model=MonitoringStagingResponse)
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
    config: AlertStagingRequest,
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

@router.get("/{pipeline_id}/alerts", response_model=List[AlertStagingResponse])
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