# api/fastapi_app/routers/decisions.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import logging

from api.fastapi_app.dependencies.database import get_db_session
from api.fastapi_app.dependencies.auth import get_current_user
from core.services.decisions import DecisionService
from core.managers.staging import StagingManager
from api.fastapi_app.schemas.staging.decisions import (
    DecisionStagingRequest,
    DecisionStagingResponse,
    DecisionListResponse,
    DecisionHistoryResponse,
    DecisionImpactResponse,
    DecisionFeedbackRequest
)
from core.messaging.event_types import ComponentType

logger = logging.getLogger(__name__)
router = APIRouter()

def get_services(db: AsyncSession = Depends(get_db_session)):
    """Get required services"""
    return {
        'decision_service': DecisionService(db),
        'staging_manager': StagingManager(db)
    }

@router.get("/", response_model=DecisionListResponse)
async def list_decisions(
    page: int = Query(1, gt=0),
    per_page: int = Query(10, gt=0, le=100),
    filters: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """List decisions with filtering and pagination"""
    try:
        decisions = await services['decision_service'].list_decisions(
            filters=filters or {},
            page=page,
            per_page=per_page
        )

        # Enrich with staging status
        for decision in decisions['items']:
            if decision.get('staging_reference'):
                staging_status = await services['staging_manager'].get_status(
                    decision['staging_reference']
                )
                decision['staging_status'] = staging_status

        return {
            'decisions': decisions['items'],
            'total': decisions['total'],
            'page': page,
            'per_page': per_page
        }
    except Exception as e:
        logger.error(f"Failed to list decisions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list decisions")

@router.get("/{pipeline_id}/pending", response_model=DecisionListResponse)
async def get_pending_decisions(
    pipeline_id: UUID,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """Get pending decisions for a pipeline with staging details"""
    try:
        decisions = await services['decision_service'].get_pending_decisions(pipeline_id)

        # Enrich with staging information
        for decision in decisions:
            if decision.get('staging_reference'):
                staging_info = await services['staging_manager'].get_staging_info(
                    decision['staging_reference']
                )
                decision['staging_details'] = staging_info

        return {'decisions': decisions}
    except Exception as e:
        logger.error(f"Failed to get pending decisions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get pending decisions")

@router.post("/{decision_id}/make", response_model=DecisionStagingResponse)
async def make_decision(
    decision_id: UUID,
    data: DecisionStagingRequest,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """Make a decision with staging integration"""
    try:
        # Stage decision data
        decision_data = data.dict()
        decision_data['user_id'] = current_user['id']

        staging_ref = await services['staging_manager'].stage_data(
            data=decision_data,
            component_type=ComponentType.DECISION_MANAGER,
            pipeline_id=str(decision_id),
            metadata={
                'decision_type': data.decision_type,
                'user_id': current_user['id'],
                'deadline': data.deadline
            }
        )

        # Process decision
        result = await services['decision_service'].make_decision(
            decision_id,
            decision_data,
            staging_ref
        )

        return result
    except Exception as e:
        logger.error(f"Failed to process decision: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process decision")

@router.post("/{decision_id}/feedback", response_model=Dict[str, Any])
async def provide_feedback(
    decision_id: UUID,
    data: DecisionFeedbackRequest,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """Provide decision feedback with impact tracking"""
    try:
        feedback_data = data.dict()
        feedback_data['user_id'] = current_user['id']
        feedback_data['feedback_time'] = datetime.utcnow()

        # Record feedback with staging
        staging_ref = await services['staging_manager'].stage_data(
            data=feedback_data,
            component_type=ComponentType.DECISION_MANAGER,
            pipeline_id=str(decision_id),
            metadata={
                'feedback_type': data.feedback_type,
                'user_id': current_user['id']
            }
        )

        result = await services['decision_service'].process_feedback(
            decision_id,
            feedback_data,
            staging_ref
        )

        return {
            'status': 'feedback_recorded',
            'feedback_id': str(result['id']),
            'staging_reference': staging_ref
        }
    except Exception as e:
        logger.error(f"Failed to process feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process feedback")

@router.get("/{pipeline_id}/history", response_model=DecisionHistoryResponse)
async def get_decision_history(
    pipeline_id: UUID,
    filters: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """Get comprehensive decision history"""
    try:
        history = await services['decision_service'].get_decision_history(
            pipeline_id,
            filters or {}
        )

        # Enrich with staging history
        for item in history:
            if item.get('staging_reference'):
                staging_history = await services['staging_manager'].get_staging_history(
                    item['staging_reference']
                )
                item['staging_history'] = staging_history

        return {'history': history}
    except Exception as e:
        logger.error(f"Failed to retrieve decision history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve decision history")

@router.get("/{decision_id}/impact", response_model=DecisionImpactResponse)
async def analyze_impact(
    decision_id: UUID,
    current_user: dict = Depends(get_current_user),
    services: Dict[str, Any] = Depends(get_services)
):
    """Analyze decision impact with comprehensive metrics"""
    try:
        impact = await services['decision_service'].analyze_decision_impact(decision_id)

        # Get related staging metrics
        if impact.get('staging_reference'):
            staging_metrics = await services['staging_manager'].get_metrics(
                impact['staging_reference']
            )
            impact['staging_metrics'] = staging_metrics

        return {
            'impact': impact,
            'analysis_time': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to analyze decision impact: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to analyze decision impact")