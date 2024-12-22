# app/blueprints/monitoring/routes.py
from flask import Blueprint, request, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from ...schemas.monitoring import (
    MetricsRequestSchema,
    MetricsResponseSchema,
    HealthStatusResponseSchema,
    PerformanceMetricsResponseSchema,
    AlertConfigRequestSchema,
    AlertConfigResponseSchema,
    AlertHistoryResponseSchema,
    ResourceUsageResponseSchema,
    AggregatedMetricsResponseSchema
)
from ...services.monitoring import MonitoringService
from ...utils.response_builder import ResponseBuilder
import logging

logger = logging.getLogger(__name__)
monitoring_bp = Blueprint('monitoring', __name__)

def get_monitoring_service():
    """Get monitoring service instance."""
    if 'monitoring_service' not in g:
        g.monitoring_service = MonitoringService(g.db)
    return g.monitoring_service

# Pipeline Monitoring Routes
@monitoring_bp.route('/<pipeline_id>/metrics', methods=['GET'])
@jwt_required()
def get_metrics(pipeline_id):
    """Get metrics for a pipeline."""
    try:
        monitoring_service = get_monitoring_service()
        schema = MetricsRequestSchema()
        filters = schema.load(request.args)
        metrics = monitoring_service.get_metrics(pipeline_id, filters)
        return ResponseBuilder.success(
            MetricsResponseSchema().dump({'metrics': metrics})
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to fetch metrics", status_code=500)

@monitoring_bp.route('/<pipeline_id>/health', methods=['GET'])
@jwt_required()
def get_health_status(pipeline_id):
    """Get health status of a pipeline."""
    try:
        monitoring_service = get_monitoring_service()
        health_status = monitoring_service.get_health_status(pipeline_id)
        return ResponseBuilder.success(
            HealthStatusResponseSchema().dump({'health_status': health_status})
        )
    except Exception as e:
        logger.error(f"Error fetching health status: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to fetch health status", status_code=500)

@monitoring_bp.route('/<pipeline_id>/performance', methods=['GET'])
@jwt_required()
def get_performance_metrics(pipeline_id):
    """Get performance metrics for a pipeline."""
    try:
        monitoring_service = get_monitoring_service()
        metrics = monitoring_service.get_performance_metrics(pipeline_id)
        return ResponseBuilder.success(
            PerformanceMetricsResponseSchema().dump({'performance': metrics})
        )
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to fetch performance metrics", status_code=500)

# Alert Management Routes
@monitoring_bp.route('/<pipeline_id>/alerts/config', methods=['GET', 'POST'])
@jwt_required()
def manage_alert_config(pipeline_id):
    """Get or update alert configuration."""
    try:
        monitoring_service = get_monitoring_service()
        
        if request.method == 'GET':
            config = monitoring_service.get_alert_config(pipeline_id)
            return ResponseBuilder.success(
                AlertConfigResponseSchema().dump({'config': config})
            )
            
        schema = AlertConfigRequestSchema()
        data = schema.load(request.get_json())
        config = monitoring_service.update_alert_config(pipeline_id, data)
        return ResponseBuilder.success(
            AlertConfigResponseSchema().dump({'config': config})
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Alert config error: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Alert configuration failed", status_code=500)

@monitoring_bp.route('/<pipeline_id>/alerts/history', methods=['GET'])
@jwt_required()
def get_alert_history(pipeline_id):
    """Get alert history for a pipeline."""
    try:
        monitoring_service = get_monitoring_service()
        history = monitoring_service.get_alert_history(pipeline_id)
        return ResponseBuilder.success(
            AlertHistoryResponseSchema().dump({'history': history})
        )
    except Exception as e:
        logger.error(f"Error fetching alert history: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to fetch alert history", status_code=500)

# Resource Monitoring Routes
@monitoring_bp.route('/<pipeline_id>/resources', methods=['GET'])
@jwt_required()
def get_resource_usage(pipeline_id):
    """Get resource usage statistics."""
    try:
        monitoring_service = get_monitoring_service()
        resources = monitoring_service.get_resource_usage(pipeline_id)
        return ResponseBuilder.success(
            ResourceUsageResponseSchema().dump({'resources': resources})
        )
    except Exception as e:
        logger.error(f"Error fetching resource usage: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to fetch resource usage", status_code=500)

@monitoring_bp.route('/<pipeline_id>/metrics/aggregated', methods=['GET'])
@jwt_required()
def get_aggregated_metrics(pipeline_id):
    """Get aggregated metrics for a pipeline."""
    try:
        monitoring_service = get_monitoring_service()
        metrics = monitoring_service.get_aggregated_metrics(pipeline_id)
        return ResponseBuilder.success(
            AggregatedMetricsResponseSchema().dump({'metrics': metrics})
        )
    except Exception as e:
        logger.error(f"Error fetching aggregated metrics: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to fetch aggregated metrics", status_code=500)

# Error handlers
@monitoring_bp.errorhandler(404)
def not_found_error(error):
    return ResponseBuilder.error("Resource not found", status_code=404)

@monitoring_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}", exc_info=True)
    return ResponseBuilder.error("Internal server error", status_code=500)