# app/blueprints/pipeline/routes.py
from flask import Blueprint, request, g, current_app
from marshmallow import ValidationError
from uuid import UUID
import logging
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
from ...utils.response_builder import ResponseBuilder

logger = logging.getLogger(__name__)


def create_pipeline_blueprint(pipeline_service, db_session):
    """Create pipeline blueprint with all routes.

    Args:
        pipeline_service: Instance of PipelineService
        db_session: Database session

    Returns:
        Blueprint: Configured pipeline blueprint
    """
    pipeline_bp = Blueprint('pipeline', __name__)

    @pipeline_bp.route('/', methods=['GET'])
    def list_pipelines():
        """List all pipelines."""
        try:
            filters = request.args.to_dict()
            pipelines = pipeline_service.list_pipelines(filters)
            return ResponseBuilder.success(
                PipelineListResponseSchema().dump({'pipelines': pipelines})
            )
        except Exception as e:
            logger.error(f"Error listing pipelines: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to list pipelines", status_code=500)

    @pipeline_bp.route('/', methods=['POST'])
    def create_pipeline():
        """Create a new pipeline."""
        try:
            schema = PipelineRequestSchema()
            data = schema.load(request.get_json())
            data['owner_id'] = g.current_user.id

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
    def get_pipeline(pipeline_id):
        """Get pipeline details."""
        try:
            # Get status from both service and manager
            pipeline_details = pipeline_service.get_pipeline(UUID(pipeline_id))
            runtime_status = current_app.pipeline_manager.get_pipeline_status(pipeline_id)

            # Merge the information
            if runtime_status:
                pipeline_details['runtime_status'] = runtime_status

            return ResponseBuilder.success(
                PipelineResponseSchema().dump({'pipeline': pipeline_details})
            )
        except ValueError:
            return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
        except Exception as e:
            logger.error(f"Error getting pipeline: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get pipeline", status_code=500)

    @pipeline_bp.route('/<pipeline_id>/start', methods=['POST'])
    def start_pipeline(pipeline_id):
        """Start pipeline execution."""
        try:
            schema = PipelineStartRequestSchema()
            config = schema.load(request.get_json() or {})

            # Start pipeline using core manager through service
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

    @pipeline_bp.route('/<pipeline_id>/status', methods=['GET'])
    def get_pipeline_status(pipeline_id):
        """Get pipeline execution status."""
        try:
            # Get both persistent and runtime status
            db_status = pipeline_service.get_pipeline_status(UUID(pipeline_id))
            runtime_status = current_app.pipeline_manager.get_pipeline_status(pipeline_id)

            # Merge statuses
            combined_status = {
                **db_status,
                'runtime_info': runtime_status if runtime_status else {}
            }

            return ResponseBuilder.success(
                PipelineStatusResponseSchema().dump({'status': combined_status})
            )
        except ValueError:
            return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
        except Exception as e:
            logger.error(f"Error getting pipeline status: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get pipeline status", status_code=500)

    @pipeline_bp.route('/<pipeline_id>/stop', methods=['POST'])
    def stop_pipeline(pipeline_id):
        """Stop pipeline execution."""
        try:
            # Stop in both service and manager
            pipeline_service.stop_pipeline(UUID(pipeline_id))
            current_app.pipeline_manager.stop_pipeline(pipeline_id)

            return ResponseBuilder.success({
                'status': 'stopped',
                'message': 'Pipeline stopped successfully'
            })
        except ValueError:
            return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
        except Exception as e:
            logger.error(f"Error stopping pipeline: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to stop pipeline", status_code=500)

    @pipeline_bp.route('/<pipeline_id>/pause', methods=['POST'])
    def pause_pipeline(pipeline_id):
        """Pause pipeline execution."""
        try:
            pipeline_service.pause_pipeline(UUID(pipeline_id))
            return ResponseBuilder.success({
                'status': 'paused',
                'message': 'Pipeline paused successfully'
            })
        except ValueError:
            return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
        except Exception as e:
            logger.error(f"Error pausing pipeline: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to pause pipeline", status_code=500)

    @pipeline_bp.route('/<pipeline_id>/resume', methods=['POST'])
    def resume_pipeline(pipeline_id):
        """Resume pipeline execution."""
        try:
            pipeline_service.resume_pipeline(UUID(pipeline_id))
            return ResponseBuilder.success({
                'status': 'running',
                'message': 'Pipeline resumed successfully'
            })
        except ValueError:
            return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
        except Exception as e:
            logger.error(f"Error resuming pipeline: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to resume pipeline", status_code=500)

    @pipeline_bp.route('/<pipeline_id>/retry', methods=['POST'])
    def retry_pipeline(pipeline_id):
        """Retry failed pipeline."""
        try:
            result = pipeline_service.retry_pipeline(UUID(pipeline_id))
            return ResponseBuilder.success(
                PipelineStatusResponseSchema().dump(result)
            )
        except ValueError:
            return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
        except Exception as e:
            logger.error(f"Error retrying pipeline: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to retry pipeline", status_code=500)

    @pipeline_bp.route('/<pipeline_id>', methods=['PUT'])
    def update_pipeline(pipeline_id):
        """Update pipeline configuration."""
        try:
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

    @pipeline_bp.route('/<pipeline_id>/status', methods=['GET'])
    def get_pipeline_status(pipeline_id):
        """Get pipeline execution status."""
        try:
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
    def get_pipeline_logs(pipeline_id):
        """Get pipeline execution logs."""
        try:
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
    def get_pipeline_metrics(pipeline_id):
        """Get pipeline performance metrics."""
        try:
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
    def validate_pipeline():
        """Validate pipeline configuration."""
        try:
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

    return pipeline_bp