# api/fastapi_app/routers/insights.py

from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import logging

from api.fastapi_app.dependencies.database import get_db_session
from api.fastapi_app.dependencies.auth import get_current_user, require_permission
from core.services.insights import InsightService
from core.managers.staging import StagingManager
from api.fastapi_app.schemas.staging.insight import (
    InsightStagingRequest,
    InsightStagingResponse
)
from core.messaging.event_types import ComponentType

logger = logging.getLogger(__name__)
router = APIRouter()

def get_services(db: AsyncSession = Depends(get_db_session)):
    """Get required services"""
    return {
        'insight_service': InsightService(db),
        'staging_manager': StagingManager(db)
    }

@router.post("/generate", response_model=Dict[str, Any])
async def generate_insights(
    data: InsightStagingRequest,
    current_user: dict = Security(require_permission("insights:generate")),
    services: Dict[str, Any] = Depends(get_services)
):
    """Generate insights with staging integration"""
    try:
        insight_data = data.dict()
        insight_data['user_id'] = current_user['id']

        # Stage insight configuration
        staging_ref = await services['staging_manager'].stage_data(
            data=insight_data,
            component_type=ComponentType.INSIGHT_MANAGER,
            pipeline_id=data.pipeline_id,
            metadata={
                'insight_types': data.insight_types,
                'target_metrics': data.target_metrics,
                'time_window': data.time_window
            }
        )

        # Generate insights
        generation_result = await services['insight_service'].generate_insights(
            insight_data,
            staging_ref
        )

        return {
            'generation_id': str(generation_result.id),
            'status': generation_result.status.value,
            'staging_reference': staging_ref
        }
    except Exception as e:
        logger.error(f"Failed to generate insights: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate insights")

@router.get("/{generation_id}/status")
async def get_generation_status(
    generation_id: UUID,
    current_user: dict = Security(require_permission("insights:read")),
    services: Dict[str, Any] = Depends(get_services)
):
    """Get insight generation status with staging details"""
    try:
        generation_status = await services['insight_service'].get_generation_status(generation_id)

        if generation_status.staging_reference:
            staging_status = await services['staging_manager'].get_status(
                generation_status.staging_reference
            )
            generation_status.staging_status = staging_status

        return {
            'status': generation_status.status.value,
            'progress': generation_status.progress,
            'staging_status': generation_status.staging_status
        }
    except Exception as e:
        logger.error(f"Failed to get generation status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get generation status")

@router.get("/{generation_id}/results", response_model=InsightStagingResponse)
async def get_insights(
    generation_id: UUID,
    current_user: dict = Security(require_permission("insights:read")),
    services: Dict[str, Any] = Depends(get_services)
):
    """Get generated insights with comprehensive details"""
    try:
        # Get insights by type
        insights_by_type = {}
        for insight_type in ['trend', 'anomaly', 'correlation', 'pattern']:
            insights = await services['insight_service'].get_insights_by_type(
                generation_id,
                insight_type
            )
            if insights:
                insights_by_type[insight_type] = insights

        # Get supporting data from staging
        generation_info = await services['insight_service'].get_generation_info(generation_id)
        supporting_data = None
        if generation_info.staging_reference:
            supporting_data = await services['staging_manager'].get_data(
                generation_info.staging_reference
            )

        return {
            'insights': insights_by_type,
            'confidence_scores': generation_info.confidence_scores,
            'supporting_metrics': supporting_data.get('metrics', {}) if supporting_data else {},
            'impact_analysis': generation_info.impact_analysis
        }
    except Exception as e:
        logger.error(f"Failed to get insights: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get insights")

@router.get("/{generation_id}/trends")
async def get_trend_insights(
    generation_id: UUID,
    current_user: dict = Security(require_permission("insights:trends:read")),
    services: Dict[str, Any] = Depends(get_services)
):
    """Get trend-specific insights with details"""
    try:
        trends = await services['insight_service'].get_insights_by_type(
            generation_id,
            'trend'
        )

        # Enrich with time series data
        generation_info = await services['insight_service'].get_generation_info(generation_id)
        if generation_info.staging_reference:
            time_series_data = await services['staging_manager'].get_time_series_data(
                generation_info.staging_reference
            )
            for trend in trends:
                trend['time_series'] = time_series_data.get(
                    trend['metric_id'],
                    []
                )

        return {'trends': trends}
    except Exception as e:
        logger.error(f"Failed to get trend insights: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get trend insights")

@router.get("/{generation_id}/anomalies")
async def get_anomaly_insights(
    generation_id: UUID,
    current_user: dict = Security(require_permission("insights:anomalies:read")),
    services: Dict[str, Any] = Depends(get_services)
):
    """Get anomaly-specific insights with context"""
    try:
        anomalies = await services['insight_service'].get_insights_by_type(
            generation_id,
            'anomaly'
        )

        # Add historical context
        generation_info = await services['insight_service'].get_generation_info(generation_id)
        if generation_info.staging_reference:
            historical_data = await services['staging_manager'].get_historical_data(
                generation_info.staging_reference
            )
            for anomaly in anomalies:
                anomaly['historical_context'] = historical_data.get(
                    anomaly['metric_id'],
                    {}
                )

        return {'anomalies': anomalies}
    except Exception as e:
        logger.error(f"Failed to get anomaly insights: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get anomaly insights")

@router.get("/{generation_id}/correlations")
async def get_correlation_insights(
    generation_id: UUID,
    current_user: dict = Security(require_permission("insights:correlations:read")),
    services: Dict[str, Any] = Depends(get_services)
):
    """Get correlation insights with supporting data"""
    try:
        correlations = await services['insight_service'].get_insights_by_type(
            generation_id,
            'correlation'
        )

        # Add statistical support
        generation_info = await services['insight_service'].get_generation_info(generation_id)
        if generation_info.staging_reference:
            statistical_data = await services['staging_manager'].get_statistical_data(
                generation_info.staging_reference
            )
            for correlation in correlations:
                correlation['statistical_support'] = statistical_data.get(
                    correlation['correlation_id'],
                    {}
                )

        return {'correlations': correlations}
    except Exception as e:
        logger.error(f"Failed to get correlation insights: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get correlation insights")

@router.post("/{generation_id}/validate")
async def validate_insights(
    generation_id: UUID,
    validation_rules: Dict[str, Any],
    current_user: dict = Security(require_permission("insights:validate")),
    services: Dict[str, Any] = Depends(get_services)
):
    """Validate generated insights with business rules"""
    try:
        # Stage validation rules
        validation_ref = await services['staging_manager'].stage_data(
            data=validation_rules,
            component_type=ComponentType.INSIGHT_MANAGER,
            pipeline_id=str(generation_id),
            metadata={
                'operation': 'validation',
                'user_id': current_user['id']
            }
        )

        validation_results = await services['insight_service'].validate_insights(
            generation_id,
            validation_rules,
            validation_ref
        )

        return {
            'validation_results': validation_results,
            'staging_reference': validation_ref
        }
    except Exception as e:
        logger.error(f"Failed to validate insights: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to validate insights")