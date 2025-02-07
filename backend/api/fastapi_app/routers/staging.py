# api/fastapi_app/main_routes/staging.py

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Security,
    Query,
    Request,
    Response
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import logging

# Core Dependencies
from api.fastapi_app.dependencies.database import get_db_session
from api.fastapi_app.dependencies.auth import (
    get_current_user,
    require_permission
)
from api.fastapi_app.dependencies.services import (
    get_quality_service,
    get_staging_service,
    get_report_service,
    get_recommendation_service,
    get_staging_manager
)

# Services
from core.services.quality import QualityService
from core.services.analytics import AnalyticsService
from core.services.insights import InsightService
from core.services.reports import ReportService
from core.services.decisions import DecisionService
from core.services.recommendations import RecommendationService
from core.managers.staging import StagingManager

# Schema Imports
from api.fastapi_app.schemas.staging import (
    # Base schemas
    StagedOutputRequest,
    StagedOutputResponse,
    StagedOutputSchemas,
    ArchiveRequest,
    CleanupRequest,
    MetricsResponse,

    # Quality schemas
    QualityCheckRequest,
    QualityCheckResponse,
    QualityStagingRequest,
    QualityStagingResponse,
    QualityIssuesResponse,
    QualityRemediationResponse,
    ValidationRulesRequest,

    # Analytics schemas
    AnalyticsStagingRequest,
    AnalyticsStagingResponse,

    # Report schemas
    ReportStagingRequest,
    ReportStagingResponse,
    ReportGenerationStatus,
    ReportTemplateRequest,
    ReportTemplateResponse,
    ReportSectionsResponse,

    # Insight schemas
    InsightStagingRequest,
    InsightStagingResponse,

    # Decision schemas
    DecisionStagingRequest,
    DecisionStagingResponse,
    DecisionListResponse,
    DecisionHistoryResponse,
    DecisionImpactResponse,
    DecisionFeedbackRequest,

    # Recommendation schemas
    RecommendationStagingRequest,
    RecommendationStagingResponse,
    RecommendationApplyRequest,
    RecommendationDismissRequest,
    RecommendationListResponse,
    RecommendationImpactResponse
)

# Event Types
from core.messaging.event_types import (
    ComponentType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ====================== Base Staging Routes ======================
@router.get("/outputs", response_model=Dict[str, Any])
async def list_outputs(
    page: int = Query(1, gt=0),
    per_page: int = Query(10, gt=0, le=100),
    component_type: Optional[ComponentType] = None,
    filters: Optional[Dict[str, Any]] = None,
    current_user: dict = Security(require_permission("staging:outputs:list")),
    staging_service: StagingService = Depends(get_staging_service)
):
    """List staged outputs with comprehensive filtering"""
    try:
        # Process filters
        filter_dict = filters or {}
        if component_type:
            filter_dict['component_type'] = component_type

        outputs = await staging_service.list_outputs(
            filters=filter_dict,
            page=page,
            per_page=per_page
        )

        # Process output schemas
        response_data = []
        for output in outputs['items']:
            schema = StagedOutputSchemas.get_schema(output.component_type, 'response')
            response_data.append(schema().dump(output))

        return {
            'outputs': response_data,
            'total': outputs['total'],
            'page': page,
            'per_page': per_page
        }

    except Exception as e:
        logger.error(f"Failed to list staged outputs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list staged outputs")

@router.get("/outputs/{output_id}", response_model=StagedOutputResponse)
async def get_output(
    output_id: UUID,
    current_user: dict = Security(require_permission("staging:outputs:read")),
    staging_service: StagingService = Depends(get_staging_service)
):
    """Get staged output with component-specific details"""
    try:
        output = await staging_service.get_output(output_id)
        schema = StagedOutputSchemas.get_schema(output.component_type, 'response')
        return schema().dump(output)

    except Exception as e:
        logger.error(f"Failed to get staged output: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get staged output")

@router.get("/outputs/{output_id}/history", response_model=Dict[str, Any])
async def get_output_history(
    output_id: UUID,
    current_user: dict = Security(require_permission("staging:outputs:history:read")),
    staging_service: StagingService = Depends(get_staging_service)
):
    """Get comprehensive output processing history"""
    try:
        history = await staging_service.get_output_history(output_id)

        # Process each history entry with appropriate schema
        for entry in history['entries']:
            schema = StagedOutputSchemas.get_schema(entry['component_type'], 'response')
            entry['details'] = schema().dump(entry.get('details', {}))

        return {
            'history': history['entries'],
            'summary': history['summary']
        }

    except Exception as e:
        logger.error(f"Failed to get output history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get output history")

@router.post("/outputs/{output_id}/archive")
async def archive_output(
    output_id: UUID,
    archive_request: ArchiveRequest,
    current_user: dict = Security(require_permission("staging:outputs:archive")),
    staging_service: StagingService = Depends(get_staging_service)
):
    """Archive staged output with retention policy"""
    try:
        archive_data = {
            'user_id': current_user['id'],
            'archive_time': datetime.utcnow().isoformat(),
            'ttl_days': archive_request.ttl_days,
            'reason': archive_request.reason
        }

        result = await staging_service.archive_output(output_id, archive_data)

        return {
            'status': 'archived',
            'output_id': str(output_id),
            'archive_time': archive_data['archive_time'],
            'retention_until': result.get('retention_until')
        }

    except Exception as e:
        logger.error(f"Failed to archive output: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to archive output")

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    component_type: Optional[ComponentType] = None,
    time_range: str = Query("24h", regex="^(1h|6h|12h|24h|7d|30d)$"),
    current_user: dict = Security(require_permission("staging:metrics:read")),
    staging_service: StagingService = Depends(get_staging_service)
):
    """Get comprehensive staging system metrics"""
    try:
        metrics = await staging_service.get_metrics(
            component_type=component_type,
            time_range=time_range
        )

        return {
            'storage_metrics': metrics.storage_metrics,
            'performance_metrics': metrics.performance_metrics,
            'component_metrics': metrics.component_metrics,
            'collection_time': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get staging metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get staging metrics")

@router.post("/cleanup")
async def trigger_cleanup(
    cleanup_config: Optional[CleanupRequest] = None,
    current_user: dict = Security(require_permission("staging:cleanup")),
    staging_service: StagingService = Depends(get_staging_service)
):
    """Trigger staged data cleanup with policy enforcement"""
    try:
        config_data = cleanup_config.dict() if cleanup_config else {}
        config_data.update({
            'triggered_by': current_user['id'],
            'trigger_time': datetime.utcnow().isoformat()
        })

        result = await staging_service.run_cleanup(config_data)

        return {
            'status': 'cleanup_initiated',
            'config': config_data,
            'affected_outputs': result.get('affected_outputs', 0),
            'space_reclaimed': result.get('space_reclaimed', 0)
        }

    except Exception as e:
        logger.error(f"Failed to trigger cleanup: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to trigger cleanup")

# ====================== Quality Routes ======================
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

# ====================== Analytics Routes ======================
def get_services(
        db: AsyncSession = Depends(get_db_session)
) -> tuple[QualityService, AnalyticsService, StagingManager]:
    """Get required services with dependency injection"""
    quality_service = QualityService(db)
    analytics_service = AnalyticsService(db)
    staging_manager = StagingManager(db)
    return quality_service, analytics_service, staging_manager


@router.post("/quality/analyze", response_model=Dict[str, Any])
async def start_quality_analysis(
        request: Request,
        data: QualityCheckRequest,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Start quality analysis with staging integration."""
    try:
        quality_service, _, staging_manager = get_services(db)

        # Add user ID to data
        analysis_data = data.dict()
        analysis_data['user_id'] = current_user['id']

        # Stage input data
        staging_ref = await staging_manager.stage_data(
            data=analysis_data,
            component_type=ComponentType.QUALITY_MANAGER,
            pipeline_id=data.pipeline_id,
            metadata={
                'analysis_type': 'quality_check',
                'user_id': current_user['id'],
                'source': request.headers.get('X-Request-Source', 'api')
            }
        )

        # Start analysis
        analysis = await quality_service.start_analysis(analysis_data, staging_ref)

        return {
            'analysis_id': str(analysis.id),
            'status': analysis.status.value,
            'staging_reference': staging_ref
        }

    except Exception as e:
        logger.error(f"Failed to start quality analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start quality analysis")


@router.get("/quality/{analysis_id}/status", response_model=QualityCheckResponse)
async def get_quality_status(
        analysis_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Get quality analysis status with staging information."""
    try:
        quality_service, _, staging_manager = get_services(db)

        # Get analysis status
        analysis_status = await quality_service.get_analysis_status(analysis_id)
        if not analysis_status:
            raise HTTPException(status_code=404, detail=f"No analysis found with ID {analysis_id}")

        # Get staging status if available
        staging_status = None
        if analysis_status.staging_reference:
            staging_status = await staging_manager.get_status(
                analysis_status.staging_reference
            )

        return {
            **analysis_status,
            'staging_status': staging_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quality status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get quality status")


@router.post("/analytics/start", response_model=Dict[str, Any])
async def start_analytics(
        request: Request,
        data: AnalyticsStagingRequest,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Start advanced analytics processing."""
    try:
        _, analytics_service, staging_manager = get_services(db)

        # Add user ID to data
        analytics_data = data.dict()
        analytics_data['user_id'] = current_user['id']

        # Stage analytics configuration
        staging_ref = await staging_manager.stage_data(
            data=analytics_data,
            component_type=ComponentType.ANALYTICS_MANAGER,
            pipeline_id=data.pipeline_id,
            metadata={
                'model_type': data.model_type,
                'features': data.features,
                'source': request.headers.get('X-Request-Source', 'api')
            }
        )

        # Start analytics processing
        analytics_job = await analytics_service.start_analytics(analytics_data, staging_ref)

        return {
            'job_id': str(analytics_job.id),
            'status': analytics_job.status.value,
            'staging_reference': staging_ref
        }

    except Exception as e:
        logger.error(f"Failed to start analytics processing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start analytics processing")


@router.get("/analytics/{job_id}/status", response_model=AnalyticsStagingResponse)
async def get_analytics_status(
        job_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Get analytics job status with comprehensive details."""
    try:
        _, analytics_service, staging_manager = get_services(db)

        # Get job status
        job_status = await analytics_service.get_job_status(job_id)
        if not job_status:
            raise HTTPException(status_code=404, detail=f"No job found with ID {job_id}")

        # Get staging status
        staging_status = await staging_manager.get_status(
            job_status.staging_reference
        )

        return {
            **job_status,
            'staging_status': staging_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analytics status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get analytics status")


@router.get("/analytics/{job_id}/results", response_model=AnalyticsStagingResponse)
async def get_analytics_results(
        job_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Get analytics processing results."""
    try:
        _, analytics_service, _ = get_services(db)

        results = await analytics_service.get_job_results(job_id)
        if not results:
            raise HTTPException(status_code=404, detail=f"No results found for job {job_id}")

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analytics results: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get analytics results")


@router.get("/analytics/{job_id}/model", response_model=Dict[str, Any])
async def get_model_details(
        job_id: UUID,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Get trained model details and metrics."""
    try:
        _, analytics_service, _ = get_services(db)

        model_info = await analytics_service.get_model_info(job_id)
        if not model_info:
            raise HTTPException(status_code=404, detail=f"No model found for job {job_id}")

        return {"model": model_info}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get model details")


@router.get("/export/{job_id}")
async def export_results(
        job_id: UUID,
        format_type: str = "pdf",
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Export analytics results in requested format."""
    try:
        if format_type not in ['pdf', 'csv', 'json', 'xlsx']:
            raise HTTPException(status_code=400, detail="Invalid export format")

        _, analytics_service, _ = get_services(db)

        export_file = await analytics_service.export_results(job_id, format_type)

        return FileResponse(
            path=export_file,
            filename=f'analytics_results_{job_id}.{format_type}',
            media_type=f'application/{format_type}'
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export results: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export results")

# ====================== Report Routes ======================
@router.post("/generate", response_model=Dict[str, Any])
async def generate_report(
    data: ReportStagingRequest,
    current_user: dict = Security(require_permission("reports:generate")),
    report_service: ReportService = Depends(get_report_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Generate a report with staging integration"""
    try:
        # Prepare report data
        report_data = data.dict()
        report_data['user_id'] = current_user['id']

        # Stage report request
        staging_ref = await staging_manager.stage_data(
            data=report_data,
            component_type=ComponentType.REPORT_MANAGER,
            pipeline_id=data.pipeline_id,
            metadata={
                'report_type': data.report_type,
                'format': data.format,
                'generation_time': datetime.utcnow().isoformat()
            }
        )

        # Generate report
        generation_result = await report_service.generate_report(report_data, staging_ref)

        return {
            'generation_id': str(generation_result.id),
            'status': generation_result.status.value,
            'staging_reference': staging_ref
        }

    except Exception as e:
        logger.error(f"Failed to generate report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate report")

@router.get("/{generation_id}/status", response_model=ReportGenerationStatus)
async def get_generation_status(
    generation_id: UUID,
    current_user: dict = Security(require_permission("reports:read")),
    report_service: ReportService = Depends(get_report_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Get report generation status with progress tracking"""
    try:
        status = await report_service.get_generation_status(generation_id)

        if status.staging_reference:
            staging_status = await staging_manager.get_status(
                status.staging_reference
            )
            status.staging_details = staging_status

        return {
            'status': status.status.value,
            'progress': status.progress,
            'staging_details': status.staging_details,
            'estimated_completion': status.estimated_completion
        }

    except Exception as e:
        logger.error(f"Failed to get generation status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get generation status")

@router.get("/{generation_id}/download")
async def download_report(
    generation_id: UUID,
    format_type: str = Query("pdf", regex="^(pdf|xlsx|csv|docx)$"),
    current_user: dict = Security(require_permission("reports:download")),
    report_service: ReportService = Depends(get_report_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Download generated report with proper format handling"""
    try:
        report_details = await report_service.get_report_details(generation_id)

        if not report_details.is_complete:
            raise HTTPException(status_code=400, detail="Report generation not complete")

        report_content = await staging_manager.get_report_content(
            report_details.staging_reference,
            format_type
        )

        return StreamingResponse(
            report_content,
            media_type=f'application/{format_type}',
            headers={
                'Content-Disposition': f'attachment; filename=report_{generation_id}.{format_type}'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to download report")

@router.post("/templates", response_model=Dict[str, Any])
async def create_template(
    template_data: ReportTemplateRequest,
    current_user: dict = Security(require_permission("reports:templates:create")),
    report_service: ReportService = Depends(get_report_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Create a report template with staging integration"""
    try:
        data = template_data.dict()
        data['user_id'] = current_user['id']

        staging_ref = await staging_manager.stage_data(
            data=data,
            component_type=ComponentType.REPORT_MANAGER,
            metadata={
                'operation': 'template_creation',
                'template_type': data.get('type'),
                'created_by': current_user['id']
            }
        )

        template = await report_service.create_template(data, staging_ref)

        return {
            'template_id': str(template.id),
            'status': 'created',
            'staging_reference': staging_ref
        }

    except Exception as e:
        logger.error(f"Failed to create template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create template")

@router.get("/templates/{template_id}/preview", response_model=Dict[str, Any])
async def preview_template(
    template_id: UUID,
    sample_data: str = Query("default"),
    current_user: dict = Security(require_permission("reports:templates:read")),
    report_service: ReportService = Depends(get_report_service)
):
    """Preview a report template with sample data"""
    try:
        preview_data = await report_service.generate_template_preview(
            template_id,
            sample_data=sample_data
        )

        return {'preview': preview_data}

    except Exception as e:
        logger.error(f"Failed to preview template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to preview template")

@router.get("/{generation_id}/sections", response_model=ReportSectionsResponse)
async def get_report_sections(
    generation_id: UUID,
    current_user: dict = Security(require_permission("reports:sections:read")),
    report_service: ReportService = Depends(get_report_service),
    staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Get detailed report sections with metrics"""
    try:
        sections = await report_service.get_report_sections(generation_id)

        if sections.staging_reference:
            section_metrics = await staging_manager.get_section_metrics(
                sections.staging_reference
            )
            sections.metrics = section_metrics

        return {
            'sections': sections.sections,
            'metrics': sections.metrics
        }

    except Exception as e:
        logger.error(f"Failed to get report sections: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get report sections")

# ====================== Insight Routes ======================
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

# ====================== Decision Routes ======================
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

# ====================== Recommendation Routes ======================
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


