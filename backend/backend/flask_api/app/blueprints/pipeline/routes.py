# app/blueprints/pipeline/routes.py
from flask import Blueprint, request, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from ...schemas.pipeline import (
    PipelineListResponseSchema,
    PipelineRequestSchema,
    PipelineResponseSchema,
    PipelineUpdateRequestSchema,
    PipelineStatusResponseSchema,
    PipelineLogsRequestSchema,
    PipelineLogsResponseSchema,
    PipelineMetricsResponseSchema,
    PipelineConfigValidationRequestSchema,
    PipelineConfigValidationResponseSchema,
    PipelineStartRequestSchema,
    PipelineStartResponseSchema
)
from ...services.pipeline.pipeline_service import PipelineService
from ...utils.response_builder import ResponseBuilder
import logging
from uuid import UUID

logger = logging.getLogger(__name__)
pipeline_bp = Blueprint('pipeline', __name__)

def get_pipeline_service():
    """Get pipeline service instance."""
    if 'pipeline_service' not in g:
        g.pipeline_service = PipelineService(g.db)
    return g.pipeline_service

@pipeline_bp.route('/', methods=['GET'])
@jwt_required()
def list_pipelines():
    """List all pipelines."""
    try:
        pipeline_service = get_pipeline_service()
        filters = request.args.to_dict()
        pipelines = pipeline_service.list_pipelines(filters)
        return ResponseBuilder.success(
            PipelineListResponseSchema().dump({'pipelines': pipelines})
        )
    except Exception as e:
        logger.error(f"Error listing pipelines: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to list pipelines", status_code=500)

@pipeline_bp.route('/', methods=['POST'])
@jwt_required()
def create_pipeline():
    """Create a new pipeline."""
    try:
        pipeline_service = get_pipeline_service()
        schema = PipelineRequestSchema()
        data = schema.load(request.get_json())
        data['owner_id'] = get_jwt_identity()
        
        pipeline = pipeline_service.create_pipeline(data)
        return ResponseBuilder.success(
            PipelineResponseSchema().dump({'pipeline': pipeline})
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Error creating pipeline: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to create pipeline", status_code=500)

@pipeline_bp.route('/<pipeline_id>', methods=['GET'])
@jwt_required()
def get_pipeline(pipeline_id):
    """Get pipeline details."""
    try:
        pipeline_service = get_pipeline_service()
        pipeline = pipeline_service.get_pipeline(UUID(pipeline_id))
        return ResponseBuilder.success(
            PipelineResponseSchema().dump({'pipeline': pipeline})
        )
    except ValueError:
        return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
    except Exception as e:
        logger.error(f"Error getting pipeline: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to get pipeline", status_code=500)

@pipeline_bp.route('/<pipeline_id>', methods=['PUT'])
@jwt_required()
def update_pipeline(pipeline_id):
    """Update pipeline configuration."""
    try:
        pipeline_service = get_pipeline_service()
        schema = PipelineUpdateRequestSchema()
        data = schema.load(request.get_json())
        
        pipeline = pipeline_service.update_pipeline(UUID(pipeline_id), data)
        return ResponseBuilder.success(
            PipelineResponseSchema().dump({'pipeline': pipeline})
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Error updating pipeline: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to update pipeline", status_code=500)

@pipeline_bp.route('/<pipeline_id>/start', methods=['POST'])
@jwt_required()
def start_pipeline(pipeline_id):
    """Start pipeline execution."""
    try:
        pipeline_service = get_pipeline_service()
        schema = PipelineStartRequestSchema()
        config = schema.load(request.get_json() or {})
        
        result = pipeline_service.start_pipeline(UUID(pipeline_id), config)
        return ResponseBuilder.success(
            PipelineStartResponseSchema().dump(result)
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except ValueError:
        return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
    except Exception as e:
        logger.error(f"Error starting pipeline: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to start pipeline", status_code=500)

@pipeline_bp.route('/<pipeline_id>/stop', methods=['POST'])
@jwt_required()
def stop_pipeline(pipeline_id):
    """Stop pipeline execution."""
    try:
        pipeline_service = get_pipeline_service()
        result = pipeline_service.stop_pipeline(UUID(pipeline_id))
        return ResponseBuilder.success(
            PipelineStatusResponseSchema().dump({
                'status': result,
                'message': 'Pipeline stopped successfully'
            })
        )
    except ValueError:
        return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
    except Exception as e:
        logger.error(f"Error stopping pipeline: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to stop pipeline", status_code=500)

@pipeline_bp.route('/<pipeline_id>/pause', methods=['POST'])
@jwt_required()
def pause_pipeline(pipeline_id):
    """Pause pipeline execution."""
    try:
        pipeline_service = get_pipeline_service()
        result = pipeline_service.pause_pipeline(UUID(pipeline_id))
        return ResponseBuilder.success(
            PipelineStatusResponseSchema().dump({
                'status': result,
                'message': 'Pipeline paused successfully'
            })
        )
    except ValueError:
        return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
    except Exception as e:
        logger.error(f"Error pausing pipeline: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to pause pipeline", status_code=500)

@pipeline_bp.route('/<pipeline_id>/resume', methods=['POST'])
@jwt_required()
def resume_pipeline(pipeline_id):
    """Resume pipeline execution."""
    try:
        pipeline_service = get_pipeline_service()
        result = pipeline_service.resume_pipeline(UUID(pipeline_id))
        return ResponseBuilder.success(
            PipelineStatusResponseSchema().dump({
                'status': result,
                'message': 'Pipeline resumed successfully'
            })
        )
    except ValueError:
        return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
    except Exception as e:
        logger.error(f"Error resuming pipeline: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to resume pipeline", status_code=500)

@pipeline_bp.route('/<pipeline_id>/retry', methods=['POST'])
@jwt_required()
def retry_pipeline(pipeline_id):
    """Retry failed pipeline."""
    try:
        pipeline_service = get_pipeline_service()
        result = pipeline_service.retry_pipeline(UUID(pipeline_id))
        return ResponseBuilder.success(
            PipelineStatusResponseSchema().dump(result)
        )
    except ValueError:
        return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
    except Exception as e:
        logger.error(f"Error retrying pipeline: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to retry pipeline", status_code=500)

@pipeline_bp.route('/<pipeline_id>/status', methods=['GET'])
@jwt_required()
def get_pipeline_status(pipeline_id):
    """Get pipeline execution status."""
    try:
        pipeline_service = get_pipeline_service()
        status = pipeline_service.get_pipeline_status(UUID(pipeline_id))
        return ResponseBuilder.success(
            PipelineStatusResponseSchema().dump({'status': status})
        )
    except ValueError:
        return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
    except Exception as e:
        logger.error(f"Error getting pipeline status: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to get pipeline status", status_code=500)

@pipeline_bp.route('/<pipeline_id>/logs', methods=['GET'])
@jwt_required()
def get_pipeline_logs(pipeline_id):
    """Get pipeline execution logs."""
    try:
        pipeline_service = get_pipeline_service()
        schema = PipelineLogsRequestSchema()
        filters = schema.load(request.args)
        
        logs = pipeline_service.get_pipeline_logs(
            UUID(pipeline_id),
            start_time=filters.get('start_time'),
            end_time=filters.get('end_time'),
            level=filters.get('level')
        )
        return ResponseBuilder.success(
            PipelineLogsResponseSchema().dump({'logs': logs})
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except ValueError:
        return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
    except Exception as e:
        logger.error(f"Error getting pipeline logs: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to get pipeline logs", status_code=500)

@pipeline_bp.route('/<pipeline_id>/metrics', methods=['GET'])
@jwt_required()
def get_pipeline_metrics(pipeline_id):
    """Get pipeline performance metrics."""
    try:
        pipeline_service = get_pipeline_service()
        metrics = pipeline_service.get_pipeline_metrics(UUID(pipeline_id))
        return ResponseBuilder.success(
            PipelineMetricsResponseSchema().dump({'metrics': metrics})
        )
    except ValueError:
        return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
    except Exception as e:
        logger.error(f"Error getting pipeline metrics: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to get pipeline metrics", status_code=500)

@pipeline_bp.route('/validate', methods=['POST'])
@jwt_required()
def validate_pipeline():
    """Validate pipeline configuration."""
    try:
        pipeline_service = get_pipeline_service()
        schema = PipelineConfigValidationRequestSchema()
        config = schema.load(request.get_json())
        
        result = pipeline_service.validate_pipeline_config(config)
        return ResponseBuilder.success(
            PipelineConfigValidationResponseSchema().dump({'result': result})
        )
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
    except Exception as e:
        logger.error(f"Error validating pipeline: {str(e)}", exc_info=True)
        return ResponseBuilder.error("Failed to validate pipeline", status_code=500)

# Error handlers
@pipeline_bp.errorhandler(404)
def not_found_error(error):
    return ResponseBuilder.error("Resource not found", status_code=404)

@pipeline_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}", exc_info=True)
    return ResponseBuilder.error("Internal server error", status_code=500)