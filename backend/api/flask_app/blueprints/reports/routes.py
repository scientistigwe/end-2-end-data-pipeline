# flask_app/blueprints/reports/routes.py

from flask import Blueprint, request, g, current_app, send_file
from marshmallow import ValidationError
from uuid import UUID
import logging
from datetime import datetime
from typing import Dict, Any

from ...schemas.staging.reports import (
    ReportStagingRequestSchema,
    ReportStagingResponseSchema
)
from ...utils.error_handlers import (
    handle_validation_error,
    handle_service_error,
    handle_not_found_error
)
from ...utils.response_builder import ResponseBuilder
from api.flask_app.auth.jwt_manager import JWTTokenManager

from core.messaging.event_types import (
    ComponentType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage
)

logger = logging.getLogger(__name__)


def validate_report_id(func):
    """Decorator to validate report ID format."""
    def wrapper(report_id, *args, **kwargs):
        try:
            validated_id = UUID(report_id)
            return func(validated_id, *args, **kwargs)
        except ValueError:
            return ResponseBuilder.error(
                "Invalid report ID format",
                status_code=400
            )
    wrapper.__name__ = func.__name__
    return wrapper


def create_reports_blueprint(report_service, staging_manager, jwt_manager):
    """
    Create reports blueprint with comprehensive staging integration.

    Args:
        report_service: Service for report operations
        staging_manager: Manager for staging operations

    Returns:
        Blueprint: Configured reports routes
    """
    reports_bp = Blueprint('reports', __name__)

    @reports_bp.route('/generate', methods=['POST'], endpoint='reports_generate')
    @jwt_manager.permission_required('reports:generate')
    async def generate_report():
        """Generate a report with staging integration."""
        try:
            schema = ReportStagingRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id

            staging_ref = await staging_manager.stage_data(
                data=data,
                component_type=ComponentType.REPORT_MANAGER,
                pipeline_id=data.get('pipeline_id'),
                metadata={
                    'report_type': data['report_type'],
                    'format': data['format'],
                    'generation_time': datetime.utcnow().isoformat()
                }
            )

            generation_result = await report_service.generate_report(data, staging_ref)

            return ResponseBuilder.success({
                'generation_id': str(generation_result.id),
                'status': generation_result.status.value,
                'staging_reference': staging_ref
            })

        except ValidationError as ve:
            return handle_validation_error(ve)
        except Exception as e:
            return handle_service_error(e, "Failed to generate report", logger)

    @reports_bp.route('/<generation_id>/status', methods=['GET'], endpoint='reports_generation_status')
    @validate_report_id
    @jwt_manager.permission_required('reports:read')
    async def get_generation_status(generation_id):
        """Get report generation status with progress tracking."""
        try:
            status = await report_service.get_generation_status(generation_id)

            if status.staging_reference:
                staging_status = await staging_manager.get_status(
                    status.staging_reference
                )
                status.staging_details = staging_status

            return ResponseBuilder.success({
                'status': status.status.value,
                'progress': status.progress,
                'staging_details': status.staging_details,
                'estimated_completion': status.estimated_completion
            })

        except Exception as e:
            return handle_service_error(e, "Failed to get generation status", logger)

    @reports_bp.route('/<generation_id>/download', methods=['GET'], endpoint='reports_download')
    @validate_report_id
    @jwt_manager.permission_required('reports:download')
    async def download_report(generation_id):
        """Download generated report with proper format handling."""
        try:
            format_type = request.args.get('format', 'pdf')
            report_details = await report_service.get_report_details(generation_id)

            if not report_details.is_complete:
                return ResponseBuilder.error("Report generation not complete", status_code=400)

            report_content = await staging_manager.get_report_content(
                report_details.staging_reference,
                format_type
            )

            return send_file(
                report_content,
                mimetype=f'application/{format_type}',
                as_attachment=True,
                download_name=f'report_{generation_id}.{format_type}'
            )

        except Exception as e:
            return handle_service_error(e, "Failed to download report", logger)

    @reports_bp.route('/templates', methods=['POST'], endpoint='reports_create_template')
    @jwt_manager.permission_required('reports:templates:create')
    async def create_template():
        """Create a report template with staging integration."""
        try:
            template_data = request.get_json()
            template_data['user_id'] = g.current_user.id

            staging_ref = await staging_manager.stage_data(
                data=template_data,
                component_type=ComponentType.REPORT_MANAGER,
                metadata={
                    'operation': 'template_creation',
                    'template_type': template_data.get('type'),
                    'created_by': g.current_user.id
                }
            )

            template = await report_service.create_template(template_data, staging_ref)

            return ResponseBuilder.success({
                'template_id': str(template.id),
                'status': 'created',
                'staging_reference': staging_ref
            })

        except Exception as e:
            return handle_service_error(e, "Failed to create template", logger)

    @reports_bp.route('/templates/<template_id>/preview', methods=['GET'], endpoint='reports_preview_template')
    @validate_report_id
    @jwt_manager.permission_required('reports:templates:read')
    async def preview_template(template_id):
        """Preview a report template with sample data."""
        try:
            preview_data = await report_service.generate_template_preview(
                template_id,
                sample_data=request.args.get('sample_data', 'default')
            )

            return ResponseBuilder.success({'preview': preview_data})

        except Exception as e:
            return handle_service_error(e, "Failed to preview template", logger)

    @reports_bp.route('/<generation_id>/sections', methods=['GET'], endpoint='reports_get_sections')
    @validate_report_id
    @jwt_manager.permission_required('reports:sections:read')
    async def get_report_sections(generation_id):
        """Get detailed report sections with metrics."""
        try:
            sections = await report_service.get_report_sections(generation_id)

            if sections.staging_reference:
                section_metrics = await staging_manager.get_section_metrics(
                    sections.staging_reference
                )
                sections.metrics = section_metrics

            return ResponseBuilder.success({
                'sections': sections.sections,
                'metrics': sections.metrics
            })

        except Exception as e:
            return handle_service_error(e, "Failed to get report sections", logger)

    @reports_bp.errorhandler(404)
    def not_found_error(error):
        """Handle resource not found errors."""
        return ResponseBuilder.error("Resource not found", status_code=404)

    @reports_bp.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return ResponseBuilder.error("Internal server error", status_code=500)

    return reports_bp