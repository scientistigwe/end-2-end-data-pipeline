# api/fastapi_app/routers/analytics.py

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Dict, Any, Optional
import logging

from api.fastapi_app.dependencies.database import get_db_session
from api.fastapi_app.dependencies.auth import get_current_user
from api.fastapi_app.schemas.staging import (
    QualityCheckRequest,
    QualityCheckResponse,
    AnalyticsStagingRequest,
    AnalyticsStagingResponse,
    ReportStagingRequest,
    ReportStagingResponse
)
from core.services.quality import QualityService
from core.services.analytics import AnalyticsService
from core.managers.staging import StagingManager
from core.messaging.event_types import (
    ComponentType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage
)

logger = logging.getLogger(__name__)
router = APIRouter()


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