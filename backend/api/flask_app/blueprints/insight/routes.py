# flask_app/blueprints/insights/routes.py

from flask import Blueprint, request, g, current_app
from marshmallow import ValidationError
from uuid import UUID
import logging
from datetime import datetime
from typing import Dict, Any

from ...schemas.staging.insight import (
    InsightStagingRequestSchema,
    InsightStagingResponseSchema
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


def validate_insight_id(func):
    """Decorator to validate insight ID format."""
    def wrapper(insight_id, *args, **kwargs):
        try:
            validated_id = UUID(insight_id)
            return func(validated_id, *args, **kwargs)
        except ValueError:
            return ResponseBuilder.error(
                "Invalid insight ID format",
                status_code=400
            )
    wrapper.__name__ = func.__name__
    return wrapper


def create_insight_blueprint(insight_service, staging_manager, jwt_manager):
    """
    Create insight blueprint with comprehensive staging integration.

    Args:
        insight_service: Service for insight operations
        staging_manager: Manager for staging operations

    Returns:
        Blueprint: Configured insight routes
    """
    insight_bp = Blueprint('insights', __name__)

    @insight_bp.route('/generate', methods=['POST'], endpoint='insights_generate')
    @jwt_manager.permission_required('insights:generate')
    async def generate_insights():
        """Generate insights with staging integration."""
        try:
            # Validate request
            schema = InsightStagingRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id

            # Stage insight configuration
            staging_ref = await staging_manager.stage_data(
                data=data,
                component_type=ComponentType.INSIGHT_MANAGER,
                pipeline_id=data.get('pipeline_id'),
                metadata={
                    'insight_types': data['insight_types'],
                    'target_metrics': data['target_metrics'],
                    'time_window': data['time_window']
                }
            )

            # Generate insights
            generation_result = await insight_service.generate_insights(
                data,
                staging_ref
            )

            return ResponseBuilder.success({
                'generation_id': str(generation_result.id),
                'status': generation_result.status.value,
                'staging_reference': staging_ref
            })

        except ValidationError as ve:
            return handle_validation_error(ve)
        except Exception as e:
            return handle_service_error(
                e,
                "Failed to generate insights",
                logger
            )

    @insight_bp.route('/<generation_id>/status', methods=['GET'], endpoint='insights_generation_status')
    @validate_insight_id
    @jwt_manager.permission_required('insights:read')
    async def get_generation_status(generation_id):
        """Get insight generation status with staging details."""
        try:
            generation_status = await insight_service.get_generation_status(generation_id)

            if generation_status.staging_reference:
                staging_status = await staging_manager.get_status(
                    generation_status.staging_reference
                )
                generation_status.staging_status = staging_status

            return ResponseBuilder.success({
                'status': generation_status.status.value,
                'progress': generation_status.progress,
                'staging_status': generation_status.staging_status
            })

        except Exception as e:
            return handle_service_error(e, "Failed to get generation status", logger)

    @insight_bp.route('/<generation_id>/results', methods=['GET'], endpoint='insights_get_results')
    @validate_insight_id
    @jwt_manager.permission_required('insights:read')
    async def get_insights(generation_id):
        """Get generated insights with comprehensive details."""
        try:
            # Get insights with categories
            insights_by_type = {}
            for insight_type in ['trend', 'anomaly', 'correlation', 'pattern']:
                insights = await insight_service.get_insights_by_type(
                    generation_id,
                    insight_type
                )
                if insights:
                    insights_by_type[insight_type] = insights

            # Get supporting data from staging
            generation_info = await insight_service.get_generation_info(generation_id)
            if generation_info.staging_reference:
                supporting_data = await staging_manager.get_data(
                    generation_info.staging_reference
                )

            response_data = InsightStagingResponseSchema().dump({
                'insights': insights_by_type,
                'confidence_scores': generation_info.confidence_scores,
                'supporting_metrics': supporting_data.get('metrics', {}),
                'impact_analysis': generation_info.impact_analysis
            })

            return ResponseBuilder.success(response_data)

        except Exception as e:
            return handle_service_error(e, "Failed to get insights", logger)

    @insight_bp.route('/<generation_id>/trends', methods=['GET'], endpoint='insights_get_trends')
    @validate_insight_id
    @jwt_manager.permission_required('insights:trends:read')
    async def get_trend_insights(generation_id):
        """Get trend-specific insights with details."""
        try:
            trends = await insight_service.get_insights_by_type(generation_id, 'trend')

            # Enrich with time series data from staging
            generation_info = await insight_service.get_generation_info(generation_id)
            if generation_info.staging_reference:
                time_series_data = await staging_manager.get_time_series_data(
                    generation_info.staging_reference
                )
                for trend in trends:
                    trend['time_series'] = time_series_data.get(
                        trend['metric_id'],
                        []
                    )

            return ResponseBuilder.success({'trends': trends})

        except Exception as e:
            return handle_service_error(e, "Failed to get trend insights", logger)

    @insight_bp.route('/<generation_id>/anomalies', methods=['GET'], endpoint='insights_get_anomalies')
    @validate_insight_id
    @jwt_manager.permission_required('insights:anomalies:read')
    async def get_anomaly_insights(generation_id):
        """Get anomaly-specific insights with context."""
        try:
            anomalies = await insight_service.get_insights_by_type(generation_id, 'anomaly')

            # Add historical context from staging
            generation_info = await insight_service.get_generation_info(generation_id)
            if generation_info.staging_reference:
                historical_data = await staging_manager.get_historical_data(
                    generation_info.staging_reference
                )
                for anomaly in anomalies:
                    anomaly['historical_context'] = historical_data.get(
                        anomaly['metric_id'],
                        {}
                    )

            return ResponseBuilder.success({'anomalies': anomalies})

        except Exception as e:
            return handle_service_error(e, "Failed to get anomaly insights", logger)

    @insight_bp.route('/<generation_id>/correlations', methods=['GET'], endpoint='insights_get_correlations')
    @validate_insight_id
    @jwt_manager.permission_required('insights:correlations:read')
    async def get_correlation_insights(generation_id):
        """Get correlation insights with supporting data."""
        try:
            correlations = await insight_service.get_insights_by_type(
                generation_id,
                'correlation'
            )

            # Add statistical support from staging
            generation_info = await insight_service.get_generation_info(generation_id)
            if generation_info.staging_reference:
                statistical_data = await staging_manager.get_statistical_data(
                    generation_info.staging_reference
                )
                for correlation in correlations:
                    correlation['statistical_support'] = statistical_data.get(
                        correlation['correlation_id'],
                        {}
                    )

            return ResponseBuilder.success({'correlations': correlations})

        except Exception as e:
            return handle_service_error(e, "Failed to get correlation insights", logger)

    @insight_bp.route('/<generation_id>/validate', methods=['POST'], endpoint='insights_validate')
    @validate_insight_id
    @jwt_manager.permission_required('insights:validate')
    async def validate_insights(generation_id):
        """Validate generated insights with business rules."""
        try:
            validation_rules = request.get_json() or {}

            # Stage validation rules
            validation_ref = await staging_manager.stage_data(
                data=validation_rules,
                component_type=ComponentType.INSIGHT_MANAGER,
                pipeline_id=str(generation_id),
                metadata={
                    'operation': 'validation',
                    'user_id': g.current_user.id
                }
            )

            validation_results = await insight_service.validate_insights(
                generation_id,
                validation_rules,
                validation_ref
            )

            return ResponseBuilder.success({
                'validation_results': validation_results,
                'staging_reference': validation_ref
            })

        except Exception as e:
            return handle_service_error(e, "Failed to validate insights", logger)

    @insight_bp.errorhandler(404)
    def not_found_error(error):
        """Handle resource not found errors."""
        return ResponseBuilder.error("Resource not found", status_code=404)

    @insight_bp.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return ResponseBuilder.error("Internal server error", status_code=500)

    return insight_bp