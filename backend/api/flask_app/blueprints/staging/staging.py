# backend/api/flask_app/blueprints/staging/routes.py

from flask import Blueprint, request, g, current_app
from marshmallow import ValidationError
from uuid import UUID
import logging
from datetime import datetime
from typing import Dict, Any

from ...schemas.staging.staging import (
    StagedOutputRequestSchema,
    StagedOutputResponseSchema,
    StagedOutputSchemas
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
    ProcessingStatus
)

logger = logging.getLogger(__name__)


def validate_output_id(func):
    """Decorator to validate staged output ID format."""

    def wrapper(output_id, *args, **kwargs):
        try:
            validated_id = UUID(output_id)
            return func(validated_id, *args, **kwargs)
        except ValueError:
            return ResponseBuilder.error(
                "Invalid output ID format",
                status_code=400
            )

    return wrapper


def create_staging_blueprint(staging_service):
    """
    Create staging blueprint with comprehensive schema integration.

    Args:
        staging_service: Service for staging operations

    Returns:
        Blueprint: Configured staging blueprint
    """
    staging_bp = Blueprint('staging', __name__)

    @staging_bp.route('/outputs', methods=['GET'])
    async def list_outputs():
        """List staged outputs with comprehensive filtering."""
        try:
            filters = request.args.to_dict()
            page = int(filters.pop('page', 1))
            per_page = int(filters.pop('per_page', 10))

            # Add component type filtering
            if 'component_type' in filters:
                try:
                    filters['component_type'] = ComponentType(filters['component_type'])
                except ValueError:
                    return ResponseBuilder.error(
                        "Invalid component type",
                        status_code=400
                    )

            outputs = await staging_service.list_outputs(
                filters=filters,
                page=page,
                per_page=per_page
            )

            # Get appropriate schema for each output
            response_data = []
            for output in outputs['items']:
                schema = StagedOutputSchemas.get_schema(
                    output.component_type,
                    'response'
                )
                response_data.append(schema().dump(output))

            return ResponseBuilder.success({
                'outputs': response_data,
                'total': outputs['total'],
                'page': page,
                'per_page': per_page
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to list staged outputs",
                logger
            )

    @staging_bp.route('/outputs/<output_id>', methods=['GET'])
    @validate_output_id
    async def get_output(output_id):
        """Get staged output with component-specific details."""
        try:
            output = await staging_service.get_output(output_id)

            # Use component-specific schema
            schema = StagedOutputSchemas.get_schema(
                output.component_type,
                'response'
            )
            return ResponseBuilder.success(schema().dump(output))

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to get staged output",
                logger
            )

    @staging_bp.route('/outputs/<output_id>/history', methods=['GET'])
    @validate_output_id
    async def get_output_history(output_id):
        """Get comprehensive output processing history."""
        try:
            history = await staging_service.get_output_history(output_id)

            # Enrich with component-specific details
            for entry in history['entries']:
                schema = StagedOutputSchemas.get_schema(
                    entry['component_type'],
                    'response'
                )
                entry['details'] = schema().dump(entry.get('details', {}))

            return ResponseBuilder.success({
                'history': history['entries'],
                'summary': history['summary']
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to get output history",
                logger
            )

    @staging_bp.route('/outputs/<output_id>/archive', methods=['POST'])
    @validate_output_id
    async def archive_output(output_id):
        """Archive staged output with retention policy."""
        try:
            archive_data = {
                'user_id': g.current_user.id,
                'archive_time': datetime.utcnow().isoformat(),
                'ttl_days': request.get_json().get('ttl_days'),
                'reason': request.get_json().get('reason')
            }

            result = await staging_service.archive_output(
                output_id,
                archive_data
            )

            return ResponseBuilder.success({
                'status': 'archived',
                'output_id': str(output_id),
                'archive_time': archive_data['archive_time'],
                'retention_until': result.get('retention_until')
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to archive output",
                logger
            )

    @staging_bp.route('/metrics', methods=['GET'])
    async def get_metrics():
        """Get comprehensive staging system metrics."""
        try:
            metrics = await staging_service.get_metrics(
                component_type=request.args.get('component_type'),
                time_range=request.args.get('time_range', '24h')
            )

            return ResponseBuilder.success({
                'storage_metrics': metrics.storage_metrics,
                'performance_metrics': metrics.performance_metrics,
                'component_metrics': metrics.component_metrics,
                'collection_time': datetime.utcnow().isoformat()
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to get staging metrics",
                logger
            )

    @staging_bp.route('/cleanup', methods=['POST'])
    async def trigger_cleanup():
        """Trigger staged data cleanup with policy enforcement."""
        try:
            cleanup_config = request.get_json() or {}
            cleanup_config.update({
                'triggered_by': g.current_user.id,
                'trigger_time': datetime.utcnow().isoformat()
            })

            result = await staging_service.run_cleanup(cleanup_config)

            return ResponseBuilder.success({
                'status': 'cleanup_initiated',
                'config': cleanup_config,
                'affected_outputs': result.get('affected_outputs', 0),
                'space_reclaimed': result.get('space_reclaimed', 0)
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to trigger cleanup",
                logger
            )

    @staging_bp.errorhandler(404)
    def not_found_error(error):
        """Handle resource not found errors."""
        return ResponseBuilder.error(
            "Resource not found",
            status_code=404
        )

    @staging_bp.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return ResponseBuilder.error(
            "Internal server error",
            status_code=500
        )

    return staging_bp