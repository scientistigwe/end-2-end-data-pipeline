# flask_app/blueprints/recommendations/routes.py

from flask import Blueprint, request, g, current_app
from marshmallow import ValidationError
from uuid import UUID
import logging
from datetime import datetime
from typing import Dict, Any

from ...schemas.staging.recommendations import (
    RecommendationStagingRequestSchema,
    RecommendationStagingResponseSchema
)
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


def validate_recommendation_id(func):
    """Decorator to validate recommendation ID format."""

    def wrapper(recommendation_id, *args, **kwargs):
        try:
            validated_id = UUID(recommendation_id)
            return func(validated_id, *args, **kwargs)
        except ValueError:
            return ResponseBuilder.error(
                "Invalid recommendation ID format",
                status_code=400
            )

    return wrapper


def create_recommendation_blueprint(recommendation_service, staging_manager):
    """
    Create recommendation blueprint with comprehensive staging integration.

    Args:
        recommendation_service: Service for recommendation operations
        staging_manager: Manager for staging operations

    Returns:
        Blueprint: Configured recommendation routes
    """
    recommendation_bp = Blueprint('recommendations', __name__)

    @recommendation_bp.route('/generate', methods=['POST'])
    async def generate_recommendations():
        """Generate recommendations with staging integration."""
        try:
            schema = RecommendationStagingRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id

            # Stage recommendation request
            staging_ref = await staging_manager.stage_data(
                data=data,
                component_type=ComponentType.RECOMMENDATION_MANAGER,
                pipeline_id=data.get('pipeline_id'),
                metadata={
                    'recommendation_type': data['type'],
                    'priority': data.get('priority', 'medium'),
                    'context': data['context']
                }
            )

            # Generate recommendations
            generation_result = await recommendation_service.generate_recommendations(
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
                "Failed to generate recommendations",
                logger
            )

    @recommendation_bp.route('/list', methods=['GET'])
    async def list_recommendations():
        """List recommendations with filtering and priority sorting."""
        try:
            filters = request.args.to_dict()
            page = int(filters.pop('page', 1))
            per_page = int(filters.pop('per_page', 10))

            recommendations = await recommendation_service.list_recommendations(
                filters=filters,
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

            return ResponseBuilder.success({
                'recommendations': recommendations['items'],
                'total': recommendations['total'],
                'page': page,
                'per_page': per_page
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to list recommendations",
                logger
            )

    @recommendation_bp.route('/<recommendation_id>/apply', methods=['POST'])
    @validate_recommendation_id
    async def apply_recommendation(recommendation_id):
        """Apply a recommendation with proper tracking."""
        try:
            application_data = {
                'user_id': g.current_user.id,
                'applied_at': datetime.utcnow().isoformat(),
                'context': request.get_json()
            }

            # Stage application data
            staging_ref = await staging_manager.stage_data(
                data=application_data,
                component_type=ComponentType.RECOMMENDATION_MANAGER,
                pipeline_id=str(recommendation_id),
                metadata={
                    'operation': 'recommendation_application',
                    'user_id': g.current_user.id
                }
            )

            # Apply recommendation
            result = await recommendation_service.apply_recommendation(
                recommendation_id,
                application_data,
                staging_ref
            )

            return ResponseBuilder.success({
                'status': 'applied',
                'recommendation_id': str(recommendation_id),
                'staging_reference': staging_ref,
                'application_time': application_data['applied_at']
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to apply recommendation",
                logger
            )

    @recommendation_bp.route('/<recommendation_id>/dismiss', methods=['POST'])
    @validate_recommendation_id
    async def dismiss_recommendation(recommendation_id):
        """Dismiss a recommendation with reason tracking."""
        try:
            dismissal_data = {
                'user_id': g.current_user.id,
                'dismissed_at': datetime.utcnow().isoformat(),
                'reason': request.get_json().get('reason'),
                'feedback': request.get_json().get('feedback')
            }

            # Stage dismissal data
            staging_ref = await staging_manager.stage_data(
                data=dismissal_data,
                component_type=ComponentType.RECOMMENDATION_MANAGER,
                pipeline_id=str(recommendation_id),
                metadata={
                    'operation': 'recommendation_dismissal',
                    'user_id': g.current_user.id
                }
            )

            # Process dismissal
            result = await recommendation_service.dismiss_recommendation(
                recommendation_id,
                dismissal_data,
                staging_ref
            )

            return ResponseBuilder.success({
                'status': 'dismissed',
                'recommendation_id': str(recommendation_id),
                'staging_reference': staging_ref,
                'dismissal_time': dismissal_data['dismissed_at']
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to dismiss recommendation",
                logger
            )

    @recommendation_bp.route('/<recommendation_id>/impact', methods=['GET'])
    @validate_recommendation_id
    async def analyze_impact(recommendation_id):
        """Analyze recommendation impact with comprehensive metrics."""
        try:
            impact_analysis = await recommendation_service.analyze_impact(
                recommendation_id
            )

            # Get historical impact data
            if impact_analysis.staging_reference:
                historical_data = await staging_manager.get_historical_impact(
                    impact_analysis.staging_reference
                )
                impact_analysis.historical_context = historical_data

            return ResponseBuilder.success({
                'impact': impact_analysis.impact_metrics,
                'confidence': impact_analysis.confidence_score,
                'historical_context': impact_analysis.historical_context
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to analyze impact",
                logger
            )

    @recommendation_bp.errorhandler(404)
    def not_found_error(error):
        """Handle resource not found errors."""
        return ResponseBuilder.error(
            "Resource not found",
            status_code=404
        )

    @recommendation_bp.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return ResponseBuilder.error(
            "Internal server error",
            status_code=500
        )

    return recommendation_bp