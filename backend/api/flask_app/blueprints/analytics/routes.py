# flask_app/blueprints/analytics/routes.py

from flask import Blueprint, request, send_file, g, current_app
from marshmallow import ValidationError
from uuid import UUID
import logging
from typing import Dict, Any

from ...schemas.staging import (
    QualityCheckRequestSchema,
    QualityCheckResponseSchema,
    AnalyticsStagingRequestSchema,
    AnalyticsStagingResponseSchema
)

from ...schemas.staging.reports import ReportStagingRequestSchema, ReportStagingResponseSchema
from ...utils.error_handlers import (
    handle_validation_error,
    handle_service_error,
    handle_not_found_error
)
from ...utils.response_builder import ResponseBuilder

from core.messaging.event_types import (
    ComponentType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage
)

logger = logging.getLogger(__name__)


def validate_analysis_id(func):
    """Decorator to validate analysis ID format."""

    def wrapper(analysis_id, *args, **kwargs):
        try:
            validated_id = UUID(analysis_id)
            return func(validated_id, *args, **kwargs)
        except ValueError:
            return ResponseBuilder.error(
                "Invalid analysis ID format",
                status_code=400
            )

    return wrapper


def create_analytics_blueprint(quality_service, analytics_service, staging_manager):
    """
    Create analytics blueprint with enhanced staging integration.

    Args:
        quality_service: Service for quality analysis
        analytics_service: Service for advanced analytics
        staging_manager: Manager for staging operations

    Returns:
        Blueprint: Configured analytics routes
    """
    analytics_bp = Blueprint('analytics', __name__)

    @analytics_bp.route('/quality/analyze', methods=['POST'])
    async def start_quality_analysis():
        """Start quality analysis with staging integration."""
        try:
            # Validate request
            schema = QualityCheckRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id

            # Stage input data
            staging_ref = await staging_manager.stage_data(
                data=data,
                component_type=ComponentType.QUALITY_MANAGER,
                pipeline_id=data.get('pipeline_id'),
                metadata={
                    'analysis_type': 'quality_check',
                    'user_id': g.current_user.id
                }
            )

            # Start analysis
            analysis = await quality_service.start_analysis(data, staging_ref)

            return ResponseBuilder.success({
                'analysis_id': str(analysis.id),
                'status': analysis.status.value,
                'staging_reference': staging_ref
            })

        except ValidationError as ve:
            return handle_validation_error(ve)
        except Exception as e:
            return handle_service_error(
                e,
                "Failed to start quality analysis",
                logger
            )

    @analytics_bp.route('/quality/<analysis_id>/status', methods=['GET'])
    @validate_analysis_id
    async def get_quality_status(analysis_id):
        """Get quality analysis status with staging information."""
        try:
            # Get analysis status
            analysis_status = await quality_service.get_analysis_status(analysis_id)

            # Get staging status if available
            staging_status = None
            if analysis_status.staging_reference:
                staging_status = await staging_manager.get_status(
                    analysis_status.staging_reference
                )

            response_data = QualityCheckResponseSchema().dump({
                **analysis_status,
                'staging_status': staging_status
            })

            return ResponseBuilder.success({'status': response_data})

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to get quality status",
                logger
            )

    @analytics_bp.route('/analytics/start', methods=['POST'])
    async def start_analytics():
        """Start advanced analytics processing."""
        try:
            schema = AnalyticsStagingRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id

            # Stage analytics configuration
            staging_ref = await staging_manager.stage_data(
                data=data,
                component_type=ComponentType.ANALYTICS_MANAGER,
                pipeline_id=data.get('pipeline_id'),
                metadata={
                    'model_type': data['model_type'],
                    'features': data['features']
                }
            )

            # Start analytics processing
            analytics_job = await analytics_service.start_analytics(
                data,
                staging_ref
            )

            return ResponseBuilder.success({
                'job_id': str(analytics_job.id),
                'status': analytics_job.status.value,
                'staging_reference': staging_ref
            })

        except ValidationError as ve:
            return handle_validation_error(ve)
        except Exception as e:
            return handle_service_error(
                e,
                "Failed to start analytics processing",
                logger
            )

    @analytics_bp.route('/analytics/<job_id>/status', methods=['GET'])
    @validate_analysis_id
    async def get_analytics_status(job_id):
        """Get analytics job status with comprehensive details."""
        try:
            # Get job status
            job_status = await analytics_service.get_job_status(job_id)

            # Get staging status
            staging_status = await staging_manager.get_status(
                job_status.staging_reference
            )

            response_data = AnalyticsStagingResponseSchema().dump({
                **job_status,
                'staging_status': staging_status
            })

            return ResponseBuilder.success({'status': response_data})

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to get analytics status",
                logger
            )

    @analytics_bp.route('/analytics/<job_id>/results', methods=['GET'])
    @validate_analysis_id
    async def get_analytics_results(job_id):
        """Get analytics processing results."""
        try:
            results = await analytics_service.get_job_results(job_id)

            if not results:
                return handle_not_found_error(
                    Exception("Results not found"),
                    f"No results found for job {job_id}",
                    logger
                )

            response_data = AnalyticsStagingResponseSchema().dump(results)
            return ResponseBuilder.success({'results': response_data})

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to get analytics results",
                logger
            )

    @analytics_bp.route('/analytics/<job_id>/model', methods=['GET'])
    @validate_analysis_id
    async def get_model_details(job_id):
        """Get trained model details and metrics."""
        try:
            model_info = await analytics_service.get_model_info(job_id)

            if not model_info:
                return handle_not_found_error(
                    Exception("Model not found"),
                    f"No model found for job {job_id}",
                    logger
                )

            return ResponseBuilder.success({'model': model_info})

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to get model details",
                logger
            )

    @analytics_bp.route('/export/<job_id>', methods=['GET'])
    @validate_analysis_id
    async def export_results(job_id):
        """Export analytics results in requested format."""
        try:
            format_type = request.args.get('format', 'pdf')

            export_file = await analytics_service.export_results(
                job_id,
                format_type
            )

            return send_file(
                export_file,
                as_attachment=True,
                download_name=f'analytics_results_{job_id}.{format_type}'
            )

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to export results",
                logger
            )

    # Error Handlers
    @analytics_bp.errorhandler(404)
    def not_found_error(error):
        return ResponseBuilder.error(
            "Resource not found",
            status_code=404
        )

    @analytics_bp.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}", exc_info=True)
        return ResponseBuilder.error(
            "Internal server error",
            status_code=500
        )

    return analytics_bp