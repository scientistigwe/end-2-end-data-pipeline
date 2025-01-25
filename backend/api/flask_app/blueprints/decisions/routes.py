# flask_app/blueprints/decisions/routes.py

from flask import Blueprint, request, g, current_app
from marshmallow import ValidationError
from uuid import UUID
import logging
from typing import Dict, Any
from datetime import datetime

from ...schemas.staging.decisions import (
    DecisionStagingRequestSchema,
    DecisionStagingResponseSchema
)
from ...schemas.staging.decisions import (
    DecisionListResponseSchema,
    DecisionHistoryResponseSchema,
    DecisionImpactResponseSchema,
    DecisionFeedbackRequestSchema
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


def validate_uuid(func):
    """Decorator to validate UUID format parameters."""

    def wrapper(*args, **kwargs):
        try:
            # Convert all UUID string parameters to UUID objects
            converted_kwargs = {}
            for key, value in kwargs.items():
                if any(key.endswith(suffix) for suffix in ['_id', 'Id', 'ID']):
                    converted_kwargs[key] = UUID(value)
                else:
                    converted_kwargs[key] = value
            return func(*args, **converted_kwargs)
        except ValueError:
            return ResponseBuilder.error(
                "Invalid ID format provided",
                status_code=400
            )

    return wrapper


def create_decision_blueprint(decision_service, staging_manager):
    """
    Create decision blueprint with enhanced staging integration.

    Args:
        decision_service: Service for decision operations
        staging_manager: Manager for staging operations

    Returns:
        Blueprint: Configured decision routes
    """
    decision_bp = Blueprint('decisions', __name__)

    @decision_bp.route('/', methods=['GET'])
    async def list_decisions():
        """List decisions with filtering and pagination."""
        try:
            filters = request.args.to_dict()
            page = int(filters.pop('page', 1))
            per_page = int(filters.pop('per_page', 10))

            decisions = await decision_service.list_decisions(
                filters=filters,
                page=page,
                per_page=per_page
            )

            # Enrich with staging status
            for decision in decisions['items']:
                if decision.get('staging_reference'):
                    staging_status = await staging_manager.get_status(
                        decision['staging_reference']
                    )
                    decision['staging_status'] = staging_status

            return ResponseBuilder.success(
                DecisionListResponseSchema().dump({
                    'decisions': decisions['items'],
                    'total': decisions['total'],
                    'page': page,
                    'per_page': per_page
                })
            )

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to list decisions",
                logger
            )

    @decision_bp.route('/<pipeline_id>/pending', methods=['GET'])
    @validate_uuid
    async def get_pending_decisions(pipeline_id: UUID):
        """Get pending decisions for a pipeline with staging details."""
        try:
            decisions = await decision_service.get_pending_decisions(pipeline_id)

            # Enrich with staging information
            for decision in decisions:
                if decision.get('staging_reference'):
                    staging_info = await staging_manager.get_staging_info(
                        decision['staging_reference']
                    )
                    decision['staging_details'] = staging_info

            return ResponseBuilder.success(
                DecisionListResponseSchema().dump({'decisions': decisions})
            )

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to get pending decisions",
                logger
            )

    @decision_bp.route('/<decision_id>/make', methods=['POST'])
    @validate_uuid
    async def make_decision(decision_id: UUID):
        """Make a decision with staging integration."""
        try:
            schema = DecisionStagingRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id

            # Stage decision data
            staging_ref = await staging_manager.stage_data(
                data=data,
                component_type=ComponentType.DECISION_MANAGER,
                pipeline_id=str(decision_id),
                metadata={
                    'decision_type': data['decision_type'],
                    'user_id': g.current_user.id,
                    'deadline': data.get('deadline')
                }
            )

            # Process decision
            result = await decision_service.make_decision(
                decision_id,
                data,
                staging_ref
            )

            return ResponseBuilder.success(
                DecisionStagingResponseSchema().dump(result)
            )

        except ValidationError as ve:
            return handle_validation_error(ve)
        except Exception as e:
            return handle_service_error(
                e,
                "Failed to process decision",
                logger
            )

    @decision_bp.route('/<decision_id>/feedback', methods=['POST'])
    @validate_uuid
    async def provide_feedback(decision_id: UUID):
        """Provide decision feedback with impact tracking."""
        try:
            schema = DecisionFeedbackRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id
            data['feedback_time'] = datetime.utcnow()

            # Record feedback with staging
            staging_ref = await staging_manager.stage_data(
                data=data,
                component_type=ComponentType.DECISION_MANAGER,
                pipeline_id=str(decision_id),
                metadata={
                    'feedback_type': data.get('feedback_type', 'general'),
                    'user_id': g.current_user.id
                }
            )

            result = await decision_service.process_feedback(
                decision_id,
                data,
                staging_ref
            )

            return ResponseBuilder.success({
                'status': 'feedback_recorded',
                'feedback_id': str(result['id']),
                'staging_reference': staging_ref
            })

        except ValidationError as ve:
            return handle_validation_error(ve)
        except Exception as e:
            return handle_service_error(
                e,
                "Failed to process feedback",
                logger
            )

    @decision_bp.route('/<pipeline_id>/history', methods=['GET'])
    @validate_uuid
    async def get_decision_history(pipeline_id: UUID):
        """Get comprehensive decision history."""
        try:
            filters = request.args.to_dict()
            history = await decision_service.get_decision_history(
                pipeline_id,
                filters
            )

            # Enrich with staging history
            for item in history:
                if item.get('staging_reference'):
                    staging_history = await staging_manager.get_staging_history(
                        item['staging_reference']
                    )
                    item['staging_history'] = staging_history

            return ResponseBuilder.success(
                DecisionHistoryResponseSchema().dump({'history': history})
            )

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to retrieve decision history",
                logger
            )

    @decision_bp.route('/<decision_id>/impact', methods=['GET'])
    @validate_uuid
    async def analyze_impact(decision_id: UUID):
        """Analyze decision impact with comprehensive metrics."""
        try:
            impact = await decision_service.analyze_decision_impact(decision_id)

            # Get related staging metrics
            if impact.get('staging_reference'):
                staging_metrics = await staging_manager.get_metrics(
                    impact['staging_reference']
                )
                impact['staging_metrics'] = staging_metrics

            return ResponseBuilder.success(
                DecisionImpactResponseSchema().dump({
                    'impact': impact,
                    'analysis_time': datetime.utcnow().isoformat()
                })
            )

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to analyze decision impact",
                logger
            )

    @decision_bp.errorhandler(404)
    def not_found_error(error):
        """Handle resource not found errors."""
        return ResponseBuilder.error(
            "Resource not found",
            status_code=404
        )

    @decision_bp.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return ResponseBuilder.error(
            "Internal server error",
            status_code=500
        )

    return decision_bp