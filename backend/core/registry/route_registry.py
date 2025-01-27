# backend/api/routes/staging.py

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_staging_manager, get_db
from backend.core.managers.staging_manager import StagingManager
from backend.db.models.staging import ComponentType, OutputType

router = APIRouter(prefix="/api/staging", tags=["staging"])


# Output Retrieval Endpoints
@router.get("/outputs/{output_id}")
async def get_output(
        output_id: str,
        component_type: Optional[str] = None,
        staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Get staged output by ID"""
    comp_type = ComponentType(component_type) if component_type else None
    output = await staging_manager.get_component_output(output_id, comp_type)
    if not output:
        raise HTTPException(404, "Output not found")
    return output


@router.get("/pipeline/{pipeline_id}/outputs")
async def get_pipeline_outputs(
        pipeline_id: str,
        component_type: Optional[str] = None,
        output_type: Optional[str] = None,
        db: AsyncSession = Depends(get_db)
):
    """Get all outputs for a pipeline"""
    query = select(BaseStagedOutput).where(
        BaseStagedOutput.pipeline_id == pipeline_id
    )

    if component_type:
        query = query.where(BaseStagedOutput.component_type == ComponentType(component_type))
    if output_type:
        query = query.where(BaseStagedOutput.output_type == OutputType(output_type))

    result = await db.execute(query)
    outputs = result.scalars().all()

    return [
        {
            'id': output.id,
            'component_type': output.component_type.value,
            'output_type': output.output_type.value,
            'status': output.status.value,
            'created_at': output.created_at.isoformat(),
            'metadata': output.metadata
        }
        for output in outputs
    ]


@router.get("/outputs/{output_id}/history")
async def get_output_history(
        output_id: str,
        staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Get processing history for output"""
    history = await staging_manager.get_output_history(output_id)
    return history


# Component-Specific Endpoints
@router.get("/quality/{pipeline_id}")
async def get_quality_outputs(
        pipeline_id: str,
        db: AsyncSession = Depends(get_db)
):
    """Get quality insight outputs"""
    query = select(StagedQualityOutput).where(
        StagedQualityOutput.pipeline_id == pipeline_id
    )
    result = await db.execute(query)
    outputs = result.scalars().all()

    return [
        {
            'id': output.id,
            'quality_score': output.quality_score,
            'issues_count': output.issues_count,
            'critical_issues_count': output.critical_issues_count,
            'status': output.status.value,
            'created_at': output.created_at.isoformat()
        }
        for output in outputs
    ]


@router.get("/insights/{pipeline_id}")
async def get_insight_outputs(
        pipeline_id: str,
        db: AsyncSession = Depends(get_db)
):
    """Get insight insight outputs"""
    query = select(StagedInsightOutput).where(
        StagedInsightOutput.pipeline_id == pipeline_id
    )
    result = await db.execute(query)
    outputs = result.scalars().all()

    return [
        {
            'id': output.id,
            'insight_count': output.insight_count,
            'goal_alignment_score': output.goal_alignment_score,
            'business_impact_score': output.business_impact_score,
            'status': output.status.value,
            'created_at': output.created_at.isoformat()
        }
        for output in outputs
    ]


@router.get("/analytics/{pipeline_id}")
async def get_analytics_outputs(
        pipeline_id: str,
        db: AsyncSession = Depends(get_db)
):
    """Get analytics outputs"""
    query = select(StagedAnalyticsOutput).where(
        StagedAnalyticsOutput.pipeline_id == pipeline_id
    )
    result = await db.execute(query)
    outputs = result.scalars().all()

    return [
        {
            'id': output.id,
            'model_type': output.model_type,
            'performance_metrics': output.performance_metrics,
            'status': output.status.value,
            'created_at': output.created_at.isoformat()
        }
        for output in outputs
    ]


# Report Access Endpoints
@router.get("/reports/{pipeline_id}")
async def get_pipeline_reports(
        pipeline_id: str,
        report_type: Optional[str] = None,
        format: Optional[str] = None,
        db: AsyncSession = Depends(get_db)
):
    """Get reports for pipeline"""
    query = select(StagedReportOutput).where(
        StagedReportOutput.pipeline_id == pipeline_id
    )

    if report_type:
        query = query.where(StagedReportOutput.report_type == report_type)
    if format:
        query = query.where(StagedReportOutput.format == format)

    result = await db.execute(query)
    reports = result.scalars().all()

    return [
        {
            'id': report.id,
            'report_type': report.report_type,
            'format': report.format,
            'version': report.version,
            'status': report.status.value,
            'created_at': report.created_at.isoformat(),
            'metadata': report.metadata
        }
        for report in reports
    ]


@router.get("/reports/{report_id}/content")
async def get_report_content(
        report_id: str,
        staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Get report content"""
    output = await staging_manager.get_component_output(
        report_id,
        ComponentType.REPORT
    )
    if not output:
        raise HTTPException(404, "Report not found")
    return output['data']


# Management Endpoints
@router.post("/outputs/{output_id}/archive")
async def archive_output(
        output_id: str,
        ttl_days: Optional[int] = None,
        staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Archive output"""
    success = await staging_manager.archive_output(output_id, ttl_days)
    if not success:
        raise HTTPException(400, "Failed to archive output")
    return {"message": "Output archived successfully"}


@router.get("/metrics")
async def get_staging_metrics(
        component_type: Optional[str] = None,
        staging_manager: StagingManager = Depends(get_staging_manager)
):
    """Get staging metrics"""
    comp_type = ComponentType(component_type) if component_type else None
    metrics = await staging_manager.get_component_metrics(comp_type)
    return metrics


# Frontend Helper Endpoints
@router.get("/latest/{pipeline_id}/{component_type}")
async def get_latest_output(
        pipeline_id: str,
        component_type: str,
        db: AsyncSession = Depends(get_db)
):
    """Get latest output for component"""
    query = select(BaseStagedOutput).where(
        BaseStagedOutput.pipeline_id == pipeline_id,
        BaseStagedOutput.component_type == ComponentType(component_type)
    ).order_by(BaseStagedOutput.created_at.desc()).limit(1)

    result = await db.execute(query)
    output = result.scalar_one_or_none()

    if not output:
        raise HTTPException(404, "No output found")

    return {
        'id': output.id,
        'component_type': output.component_type.value,
        'output_type': output.output_type.value,
        'status': output.status.value,
        'created_at': output.created_at.isoformat(),
        'metadata': output.metadata
    }


@router.get("/status/{pipeline_id}")
async def get_pipeline_staging_status(
        pipeline_id: str,
        db: AsyncSession = Depends(get_db)
):
    """Get staging status for all components"""
    # Get latest output for each component type
    status = {}
    for comp_type in ComponentType:
        query = select(BaseStagedOutput).where(
            BaseStagedOutput.pipeline_id == pipeline_id,
            BaseStagedOutput.component_type == comp_type
        ).order_by(BaseStagedOutput.created_at.desc()).limit(1)

        result = await db.execute(query)
        output = result.scalar_one_or_none()

        if output:
            status[comp_type.value] = {
                'status': output.status.value,
                'last_updated': output.updated_at.isoformat(),
                'output_id': output.id
            }
        else:
            status[comp_type.value] = {
                'status': 'not_started',
                'last_updated': None,
                'output_id': None
            }

    return status