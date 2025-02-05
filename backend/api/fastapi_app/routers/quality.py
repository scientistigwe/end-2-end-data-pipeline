# api/fastapi_app/routers/quality.py

from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import logging

from api.fastapi_app.dependencies.database import get_db_session
from api.fastapi_app.dependencies.auth import get_current_user, require_permission
from api.fastapi_app.dependencies.services import get_quality_service, get_staging_manager
from core.services.quality import QualityService
from core.managers.staging import StagingManager
from api.fastapi_app.schemas.staging.quality import (
    QualityCheckRequest,
    QualityCheckResponse,
    QualityStagingRequest,
    QualityStagingResponse,
    QualityIssuesResponse,
    QualityRemediationResponse,
    ValidationRulesRequest
)
from core.messaging.event_types import (
    ComponentType,
    ProcessingStage,
    ProcessingStatus
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/analyze", response_model=Dict[str, Any])
async def start_quality_analysis(
    data: QualityCheckRequest,
    current_user: dict = Security(require_permission("quality:analyze")),
    quality_service: QualityService = Depends(get_quality_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Initiate quality analysis with comprehensive validation"""
    try:
        # Prepare analysis data
        analysis_data = data.dict()
        analysis_data.update({
            'user_id': current_user['id'],
            'request_time': datetime.utcnow().isoformat()
        })

        # Stage quality analysis request
        staging_ref = await staging_manager.stage_data(
            data=analysis_data,
            component_type=ComponentType.QUALITY_MANAGER,
            pipeline_id=data.pipeline_id,
            metadata={
                'analysis_type': 'quality_check',
                'validation_count': len(data.validation_rules),
                'columns_validated': list(data.column_rules.keys()),
                'sampling_enabled': bool(data.sampling_config),
                'advanced_options': data.advanced_options or {}
            }
        )

        # Initialize analysis
        analysis = await quality_service.start_analysis(analysis_data, staging_ref)

        # Track analysis configuration
        await quality_service.track_analysis_start({
            'analysis_id': str(analysis.id),
            'staging_ref': staging_ref,
            'config_summary': {
                'rules_count': len(data.validation_rules),
                'columns_count': len(data.column_rules),
                'thresholds': len(data.quality_thresholds or {})
            }
        })

        return {
            'analysis_id': str(analysis.id),
            'status': analysis.status.value,
            'staging_reference': staging_ref,
            'estimated_duration': analysis.estimated_duration
        }

    except Exception as e:
        logger.error(f"Failed to start quality analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start quality analysis")

@router.get("/{analysis_id}/status", response_model=QualityCheckResponse)
async def get_analysis_status(
    analysis_id: UUID,
    current_user: dict = Security(require_permission("quality:read")),
    quality_service: QualityService = Depends(get_quality_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Get detailed quality analysis status with progress tracking"""
    try:
        analysis_status = await quality_service.get_analysis_status(analysis_id)

        # Retrieve and enrich staging status
        staging_status = None
        if analysis_status.staging_reference:
            staging_status = await staging_manager.get_status(
                analysis_status.staging_reference
            )
            execution_metrics = await staging_manager.get_execution_metrics(
                analysis_status.staging_reference
            )
            staging_status['execution_metrics'] = execution_metrics

        return {
            **analysis_status,
            'staging_status': staging_status,
            'progress': {
                'current_stage': analysis_status.current_stage,
                'completed_rules': analysis_status.completed_rules,
                'total_rules': analysis_status.total_rules,
                'estimated_completion': analysis_status.estimated_completion,
                'performance_metrics': analysis_status.performance_metrics
            }
        }

    except Exception as e:
        logger.error(f"Failed to get analysis status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get analysis status")

@router.get("/{analysis_id}/results", response_model=QualityCheckResponse)
async def get_analysis_results(
    analysis_id: UUID,
    current_user: dict = Security(require_permission("quality:read")),
    quality_service: QualityService = Depends(get_quality_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Get comprehensive quality analysis results"""
    try:
        results = await quality_service.get_analysis_results(analysis_id)
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No results found for analysis {analysis_id}"
            )

        # Retrieve column profiles if available
        column_profiles = None
        if results.staging_reference:
            column_profiles = await staging_manager.get_column_profiles(
                results.staging_reference
            )

        return {
            **results,
            'data_profile': column_profiles,
            'execution_summary': {
                'start_time': results.start_time,
                'end_time': results.end_time,
                'duration': results.duration,
                'rules_evaluated': results.rules_evaluated
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis results: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get analysis results")

@router.get("/{analysis_id}/issues", response_model=QualityIssuesResponse)
async def get_quality_issues(
    analysis_id: UUID,
    current_user: dict = Security(require_permission("quality:issues:read")),
    quality_service: QualityService = Depends(get_quality_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Get detailed quality issues with full context"""
    try:
        issues = await quality_service.get_quality_issues(analysis_id)

        # Enrich with historical context
        if issues.staging_reference:
            historical_context = await staging_manager.get_historical_issues(
                issues.staging_reference
            )
            for issue in issues.issues_found:
                issue['historical_context'] = historical_context.get(
                    issue['issue_id'],
                    {}
                )

        return {
            'issues': issues.issues_found,
            'summary': issues.issue_summary,
            'remediation_suggestions': issues.remediation_suggestions
        }

    except Exception as e:
        logger.error(f"Failed to get quality issues: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get quality issues")

@router.get("/{analysis_id}/remediation", response_model=QualityRemediationResponse)
async def get_remediation_plan(
    analysis_id: UUID,
    current_user: dict = Security(require_permission("quality:remediation:read")),
    quality_service: QualityService = Depends(get_quality_service)
):
    """Get detailed remediation plan with impact analysis"""
    try:
        remediation_plan = await quality_service.get_remediation_plan(analysis_id)
        if not remediation_plan:
            raise HTTPException(
                status_code=404,
                detail=f"No remediation plan found for analysis {analysis_id}"
            )

        return {
            'remediation_plan': {
                'suggestions': remediation_plan.suggestions,
                'priorities': remediation_plan.priorities,
                'effort_estimates': remediation_plan.effort_estimates,
                'impact_analysis': remediation_plan.impact_analysis
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get remediation plan: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get remediation plan")

@router.post("/config/rules")
async def update_validation_rules(
    rules: ValidationRulesRequest,
    current_user: dict = Security(require_permission("quality:rules:update")),
    quality_service: QualityService = Depends(get_quality_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Update quality validation rules with tracking"""
    try:
        # Stage updated rules
        staging_ref = await staging_manager.stage_data(
            data=rules.dict(),
            component_type=ComponentType.QUALITY_MANAGER,
            pipeline_id=rules.pipeline_id,
            metadata={
                'operation': 'rule_update',
                'update_time': datetime.utcnow().isoformat(),
                'updated_by': current_user['id']
            }
        )

        # Apply rule updates
        update_result = await quality_service.update_validation_rules(
            rules.dict(),
            staging_ref
        )

        return {
            'status': 'updated',
            'rule_count': len(rules.rules),
            'staging_reference': staging_ref,
            'effective_time': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to update validation rules: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update validation rules")