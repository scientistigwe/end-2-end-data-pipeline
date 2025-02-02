# flask_app/blueprints/monitoring/routes.py

from flask import Blueprint, request, g, current_app
from marshmallow import ValidationError
from uuid import UUID
import logging
from datetime import datetime
from typing import Dict, Any

from ...schemas.staging.monitoring import (
    MonitoringStagingRequestSchema,
    MonitoringStagingResponseSchema,
    AlertStagingRequestSchema,
    AlertStagingResponseSchema
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


# flask_app/blueprints/monitoring/routes.py

def validate_pipeline_id(func):
    """Decorator to validate pipeline ID format."""
    def wrapper(pipeline_id, *args, **kwargs):
        try:
            validated_id = UUID(pipeline_id)
            return func(validated_id, *args, **kwargs)
        except ValueError:
            return ResponseBuilder.error(
                "Invalid pipeline ID format",
                status_code=400
            )
    wrapper.__name__ = func.__name__
    return wrapper


def create_monitoring_blueprint(monitoring_service, staging_manager, jwt_manager):
    """
    Create monitoring blueprint with comprehensive staging integration.
    """
    monitoring_bp = Blueprint('monitoring', __name__)

    @monitoring_bp.route('/<pipeline_id>/metrics', methods=['POST'], endpoint='monitoring_collect_metrics')
    @validate_pipeline_id
    @jwt_manager.permission_required('monitoring:metrics:write')
    async def collect_metrics(pipeline_id):
        """Collect and store metrics with staging integration."""
        try:
            schema = MonitoringStagingRequestSchema()
            data = schema.load(request.get_json())
            data['pipeline_id'] = str(pipeline_id)

            # Stage metrics collection request
            staging_ref = await staging_manager.stage_data(
                data=data,
                component_type=ComponentType.MONITORING_MANAGER,
                pipeline_id=str(pipeline_id),
                metadata={
                    'metrics': data['metrics'],
                    'time_window': data['time_window'],
                    'aggregation': data.get('aggregation')
                }
            )

            collection_result = await monitoring_service.collect_metrics(data, staging_ref)

            return ResponseBuilder.success({
                'collection_id': str(collection_result.id),
                'status': collection_result.status.value,
                'staging_reference': staging_ref
            })

        except ValidationError as ve:
            return handle_validation_error(ve)
        except Exception as e:
            return handle_service_error(e, "Failed to collect metrics", logger)

    @monitoring_bp.route('/<pipeline_id>/metrics/aggregated', methods=['GET'], endpoint='monitoring_get_aggregated')
    @validate_pipeline_id
    @jwt_manager.permission_required('monitoring:metrics:read')
    async def get_aggregated_metrics(pipeline_id):
        """Get aggregated metrics with comprehensive analysis."""
        try:
            metrics_data = await monitoring_service.get_aggregated_metrics(pipeline_id)

            if metrics_data.staging_reference:
                historical_data = await staging_manager.get_historical_metrics(
                    metrics_data.staging_reference
                )
                metrics_data.historical_context = historical_data

            return ResponseBuilder.success(MonitoringStagingResponseSchema().dump(metrics_data))

        except Exception as e:
            return handle_service_error(e, "Failed to get aggregated metrics", logger)

    @monitoring_bp.route('/<pipeline_id>/alerts/configure', methods=['POST'], endpoint='monitoring_configure_alerts')
    @validate_pipeline_id
    @jwt_manager.permission_required('monitoring:alerts:configure')
    async def configure_alerts(pipeline_id):
        """Configure alert rules with staging integration."""
        try:
            schema = AlertStagingRequestSchema()
            config_data = schema.load(request.get_json())
            config_data['pipeline_id'] = str(pipeline_id)

            staging_ref = await staging_manager.stage_data(
                data=config_data,
                component_type=ComponentType.MONITORING_MANAGER,
                pipeline_id=str(pipeline_id),
                metadata={
                    'alert_type': config_data['alert_type'],
                    'severity': config_data['severity'],
                    'config_time': datetime.utcnow().isoformat()
                }
            )

            config_result = await monitoring_service.configure_alerts(config_data, staging_ref)

            return ResponseBuilder.success({
                'config_id': str(config_result.id),
                'status': 'configured',
                'staging_reference': staging_ref
            })

        except ValidationError as ve:
            return handle_validation_error(ve)
        except Exception as e:
            return handle_service_error(e, "Failed to configure alerts", logger)

    @monitoring_bp.route('/<pipeline_id>/alerts', methods=['GET'], endpoint='monitoring_get_alerts')
    @validate_pipeline_id
    @jwt_manager.permission_required('monitoring:alerts:read')
    async def get_active_alerts(pipeline_id):
        """Get active alerts with context."""
        try:
            alerts = await monitoring_service.get_active_alerts(pipeline_id)

            for alert in alerts:
                if alert.staging_reference:
                    alert_context = await staging_manager.get_alert_context(
                        alert.staging_reference
                    )
                    alert.context = alert_context

            return ResponseBuilder.success({
                'alerts': AlertStagingResponseSchema(many=True).dump(alerts)
            })

        except Exception as e:
            return handle_service_error(e, "Failed to get active alerts", logger)

    @monitoring_bp.route('/<pipeline_id>/alerts/<alert_id>/acknowledge', methods=['POST'], endpoint='monitoring_acknowledge_alert')
    @validate_pipeline_id
    @jwt_manager.permission_required('monitoring:alerts:acknowledge')
    async def acknowledge_alert(pipeline_id, alert_id):
        """Acknowledge an alert with staging update."""
        try:
            acknowledgment_data = {
                'acknowledged_by': g.current_user.id,
                'acknowledged_at': datetime.utcnow().isoformat(),
                'notes': request.get_json().get('notes')
            }

            staging_ref = await staging_manager.stage_data(
                data=acknowledgment_data,
                component_type=ComponentType.MONITORING_MANAGER,
                pipeline_id=str(pipeline_id),
                metadata={
                    'operation': 'alert_acknowledgment',
                    'alert_id': alert_id
                }
            )

            result = await monitoring_service.acknowledge_alert(
                alert_id,
                acknowledgment_data,
                staging_ref
            )

            return ResponseBuilder.success({
                'status': 'acknowledged',
                'alert_id': alert_id,
                'staging_reference': staging_ref
            })

        except Exception as e:
            return handle_service_error(e, "Failed to acknowledge alert", logger)

    @monitoring_bp.route('/<pipeline_id>/performance', methods=['GET'], endpoint='monitoring_get_performance')
    @validate_pipeline_id
    @jwt_manager.permission_required('monitoring:performance:read')
    async def get_performance_metrics(pipeline_id):
        """Get comprehensive performance metrics."""
        try:
            metrics = await monitoring_service.get_performance_metrics(pipeline_id)

            if metrics.staging_reference:
                historical_data = await staging_manager.get_historical_performance(
                    metrics.staging_reference
                )
                metrics.historical_performance = historical_data

            return ResponseBuilder.success({'performance': metrics})

        except Exception as e:
            return handle_service_error(e, "Failed to get performance metrics", logger)

    @monitoring_bp.route('/<pipeline_id>/resources', methods=['GET'], endpoint='monitoring_get_resources')
    @validate_pipeline_id
    @jwt_manager.permission_required('monitoring:resources:read')
    async def get_resource_usage(pipeline_id):
        """Get detailed resource usage statistics."""
        try:
            resources = await monitoring_service.get_resource_usage(pipeline_id)

            if resources.staging_reference:
                resource_metrics = await staging_manager.get_resource_metrics(
                    resources.staging_reference
                )
                resources.detailed_metrics = resource_metrics

            return ResponseBuilder.success({'resources': resources})

        except Exception as e:
            return handle_service_error(e, "Failed to get resource usage", logger)

    @monitoring_bp.errorhandler(404)
    def not_found_error(error):
        """Handle resource not found errors."""
        return ResponseBuilder.error("Resource not found", status_code=404)

    @monitoring_bp.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return ResponseBuilder.error("Internal server error", status_code=500)

    return monitoring_bp