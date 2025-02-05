# api/fastapi_app/routers/recommendations.py

from fastapi import APIRouter, Depends, HTTPException, Security, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import logging

from api.fastapi_app.dependencies.database import get_db_session
from api.fastapi_app.dependencies.auth import get_current_user, require_permission
from api.fastapi_app.dependencies.services import get_recommendation_service, get_staging_manager
from core.services.recommendations import RecommendationService
from core.managers.staging import StagingManager
from api.fastapi_app.schemas.staging.recommendations import (
    RecommendationStagingRequest,
    RecommendationStagingResponse,
    RecommendationApplyRequest,
    RecommendationDismissRequest,
    RecommendationListResponse,
    RecommendationImpactResponse
)
from core.messaging.event_types import ComponentType

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/generate", response_model=Dict[str, Any])
async def generate_recommendations(
    data: RecommendationStagingRequest,
    current_user: dict = Security(require_permission("recommendations:generate")),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Generate recommendations with staging integration"""
    try:
        # Prepare data
        recommendation_data = data.dict()
        recommendation_data['user_id'] = current_user['id']

        # Stage recommendation request
        staging_ref = await staging_manager.stage_data(
            data=recommendation_data,
            component_type=ComponentType.RECOMMENDATION_MANAGER,
            pipeline_id=data.pipeline_id,
            metadata={
                'recommendation_type': data.type,
                'priority': data.priority or 'medium',
                'context': data.context
            }
        )

        # Generate recommendations
        generation_result = await recommendation_service.generate_recommendations(
            recommendation_data,
            staging_ref
        )

        return {
            'generation_id': str(generation_result.id),
            'status': generation_result.status.value,
            'staging_reference': staging_ref
        }

    except Exception as e:
        logger.error(f"Failed to generate recommendations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")

@router.get("/list", response_model=RecommendationListResponse)
async def list_recommendations(
    page: int = Query(1, gt=0),
    per_page: int = Query(10, gt=0, le=100),
    filters: Optional[Dict[str, Any]] = None,
    current_user: dict = Security(require_permission("recommendations:list")),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """List recommendations with filtering and priority sorting"""
    try:
        recommendations = await recommendation_service.list_recommendations(
            filters=filters or {},
            page=page,
            per_page=per_page
        )

        # Enrich with impact analysis
        for recommendation in recommendations['items']:
            if recommendation.get('staging_reference'):
                impact_data = await staging_manager.get_impact_analysis(
                    recommendation['staging_reference']
                )
                recommendation['impact_analysis'] = impact_data

        return {
            'recommendations': recommendations['items'],
            'total': recommendations['total'],
            'page': page,
            'per_page': per_page
        }

    except Exception as e:
        logger.error(f"Failed to list recommendations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list recommendations")

@router.post("/{recommendation_id}/apply")
async def apply_recommendation(
    recommendation_id: UUID,
    data: RecommendationApplyRequest,
    current_user: dict = Security(require_permission("recommendations:apply")),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Apply a recommendation with proper tracking"""
    try:
        application_data = {
            'user_id': current_user['id'],
            'applied_at': datetime.utcnow().isoformat(),
            'context': data.dict()
        }

        # Stage application data
        staging_ref = await staging_manager.stage_data(
            data=application_data,
            component_type=ComponentType.RECOMMENDATION_MANAGER,
            pipeline_id=str(recommendation_id),
            metadata={
                'operation': 'recommendation_application',
                'user_id': current_user['id']
            }
        )

        # Apply recommendation
        result = await recommendation_service.apply_recommendation(
            recommendation_id,
            application_data,
            staging_ref
        )

        return {
            'status': 'applied',
            'recommendation_id': str(recommendation_id),
            'staging_reference': staging_ref,
            'application_time': application_data['applied_at']
        }

    except Exception as e:
        logger.error(f"Failed to apply recommendation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to apply recommendation")

@router.post("/{recommendation_id}/dismiss")
async def dismiss_recommendation(
    recommendation_id: UUID,
    data: RecommendationDismissRequest,
    current_user: dict = Security(require_permission("recommendations:dismiss")),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Dismiss a recommendation with reason tracking"""
    try:
        dismissal_data = {
            'user_id': current_user['id'],
            'dismissed_at': datetime.utcnow().isoformat(),
            'reason': data.reason,
            'feedback': data.feedback
        }

        # Stage dismissal data
        staging_ref = await staging_manager.stage_data(
            data=dismissal_data,
            component_type=ComponentType.RECOMMENDATION_MANAGER,
            pipeline_id=str(recommendation_id),
            metadata={
                'operation': 'recommendation_dismissal',
                'user_id': current_user['id']
            }
        )

        # Process dismissal
        result = await recommendation_service.dismiss_recommendation(
            recommendation_id,
            dismissal_data,
            staging_ref
        )

        return {
            'status': 'dismissed',
            'recommendation_id': str(recommendation_id),
            'staging_reference': staging_ref,
            'dismissal_time': dismissal_data['dismissed_at']
        }

    except Exception as e:
        logger.error(f"Failed to dismiss recommendation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to dismiss recommendation")

@router.get("/{recommendation_id}/impact", response_model=RecommendationImpactResponse)
async def analyze_impact(
    recommendation_id: UUID,
    current_user: dict = Security(require_permission("recommendations:impacts:read")),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Analyze recommendation impact with comprehensive metrics"""
    try:
        impact_analysis = await recommendation_service.analyze_impact(recommendation_id)

        # Get historical impact data
        if impact_analysis.staging_reference:
            historical_data = await staging_manager.get_historical_impact(
                impact_analysis.staging_reference
            )
            impact_analysis.historical_context = historical_data

        return {
            'impact': impact_analysis.impact_metrics,
            'confidence': impact_analysis.confidence_score,
            'historical_context': impact_analysis.historical_context
        }

    except Exception as e:
        logger.error(f"Failed to analyze impact: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze impact")