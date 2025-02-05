# api/fastapi_app/routers/reports.py

from fastapi import APIRouter, Depends, HTTPException, Security, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
import logging

from api.fastapi_app.dependencies.database import get_db_session
from api.fastapi_app.dependencies.auth import get_current_user, require_permission
from api.fastapi_app.dependencies.services import get_report_service, get_staging_manager
from core.services.reports import ReportService
from core.managers.staging import StagingManager
from api.fastapi_app.schemas.staging.reports import (
    ReportStagingRequest,
    ReportStagingResponse,
    ReportGenerationStatus,
    ReportTemplateRequest,
    ReportTemplateResponse,
    ReportSectionsResponse
)
from core.messaging.event_types import ComponentType

logger = logging.getLogger(__name__)
router = APIRouter()

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