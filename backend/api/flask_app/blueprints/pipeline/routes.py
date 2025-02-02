# flask_app/blueprints/pipeline/routes.py

from flask import Blueprint, request, g, current_app
from marshmallow import ValidationError
from uuid import UUID
import logging
from functools import wraps
from typing import Dict, Any, Union

from ...schemas.staging.pipeline import (
    PipelineRequestSchema,
    PipelineResponseSchema,
    PipelineStatusResponseSchema,
    PipelineLogsResponseSchema,
    PipelineMetricsResponseSchema,
    PipelineListResponseSchema
)

from core.messaging.event_types import (
    MessageType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage,
    ModuleIdentifier,
    ComponentType,
    ProcessingContext
)

from ...utils.response_builder import ResponseBuilder
from ...utils.error_handlers import (
    handle_validation_error,
    handle_service_error,
    handle_not_found_error
)

logger = logging.getLogger(__name__)


def validate_pipeline_id(func):
    """
    Decorator to validate pipeline ID format and handle common error scenarios.

    Args:
        func (callable): Route handler function

    Returns:
        callable: Wrapped route handler with ID validation
    """

    @wraps(func)
    def wrapper(pipeline_id, *args, **kwargs):
        try:
            # Convert to UUID to validate format
            validated_id = UUID(pipeline_id)

            # Validate if pipeline exists
            if not current_app.pipeline_service.pipeline_exists(validated_id):
                return ResponseBuilder.error(
                    f"Pipeline {pipeline_id} not found",
                    status_code=404
                )

            return func(validated_id, *args, **kwargs)
        except ValueError:
            return ResponseBuilder.error(
                "Invalid pipeline ID format",
                status_code=400
            )

    return wrapper


def create_pipeline_blueprint(pipeline_service, staging_manager, jwt_manager):
    """
    Create an enhanced pipeline blueprint with comprehensive routing and error handling.

    Args:
        pipeline_service: Service for pipeline operations
        staging_manager: Manager for staging operations
        jwt_manager: JWT manager for authentication and authorization

    Returns:
        Blueprint: Configured pipeline routes
    """
    pipeline_bp = Blueprint('pipeline', __name__)

    @pipeline_bp.route('/', methods=['GET'])
    @jwt_manager.permission_required('pipeline:list')
    def list_pipelines():
        """List pipelines with filtering and pagination"""
        try:
            # Parse and validate query parameters
            filters = request.args.to_dict()
            page = int(filters.pop('page', 1))
            per_page = int(filters.pop('per_page', 10))

            # Get pipelines with runtime status
            pipelines = pipeline_service.list_pipelines(
                filters=filters,
                page=page,
                per_page=per_page
            )

            # Enrich with runtime status
            for pipeline in pipelines['pipelines']:
                runtime_status = current_app.pipeline_manager.get_pipeline_status(
                    str(pipeline['id'])
                )
                if runtime_status:
                    pipeline['runtime_status'] = runtime_status

            # Validate and format response
            schema = PipelineListResponseSchema()
            response_data = schema.dump({
                'pipelines': pipelines['pipelines'],
                'total_count': pipelines['total_count'],
                'page': page,
                'per_page': per_page
            })

            return ResponseBuilder.success(response_data)

        except Exception as e:
            return handle_service_error(
                e,
                "Error retrieving pipelines",
                logger
            )

    @pipeline_bp.route('/', methods=['POST'])
    @jwt_manager.permission_required('pipeline:create')
    async def create_pipeline():
        """Create new pipeline with staging integration"""
        try:
            # Validate request data
            schema = PipelineRequestSchema()
            pipeline_data = schema.load(request.get_json())

            # Add user context
            pipeline_data['user_id'] = g.current_user.id

            # Stage initial configuration
            staging_ref = await staging_manager.stage_data(
                data=pipeline_data,
                component_type=ComponentType.PIPELINE_SERVICE,
                pipeline_id=None,  # Will be set after creation
                metadata={
                    'request_type': 'pipeline_creation',
                    'user_id': g.current_user.id
                }
            )

            # Create pipeline with staging reference
            pipeline = pipeline_service.create_pipeline(
                pipeline_data,
                staging_ref=staging_ref
            )

            # Update staging reference with pipeline ID
            await staging_manager.update_reference(
                staging_ref,
                {'pipeline_id': str(pipeline['id'])}
            )

            response_schema = PipelineResponseSchema()
            return ResponseBuilder.success(
                response_schema.dump(pipeline),
                status_code=201
            )

        except ValidationError as ve:
            return handle_validation_error(ve)
        except Exception as e:
            return handle_service_error(
                e,
                "Pipeline creation failed",
                logger
            )

    @pipeline_bp.route('/<pipeline_id>', methods=['GET'])
    @validate_pipeline_id
    @jwt_manager.permission_required('pipeline:read')
    async def get_pipeline(pipeline_id):
        """Get comprehensive pipeline details"""
        try:
            # Get base pipeline data
            pipeline = pipeline_service.get_pipeline(pipeline_id)

            # Enrich with runtime status
            runtime_status = current_app.pipeline_manager.get_pipeline_status(
                str(pipeline_id)
            )
            if runtime_status:
                pipeline['runtime_status'] = runtime_status

            # Get staged outputs if available
            staged_outputs = await staging_manager.get_pipeline_outputs(
                str(pipeline_id)
            )
            if staged_outputs:
                pipeline['staged_outputs'] = staged_outputs

            schema = PipelineResponseSchema()
            return ResponseBuilder.success(schema.dump(pipeline))

        except Exception as e:
            return handle_service_error(
                e,
                f"Error retrieving pipeline {pipeline_id}",
                logger
            )

    @pipeline_bp.route('/<pipeline_id>/start', methods=['POST'])
    @validate_pipeline_id
    @jwt_manager.permission_required('pipeline:execute')
    def start_pipeline(pipeline_id):
        """Start pipeline execution"""
        try:
            # Validate start configuration
            schema = PipelineRequestSchema(partial=True)
            config = schema.load(request.get_json() or {})

            # Create processing context
            context = ProcessingContext(
                pipeline_id=str(pipeline_id),
                stage=ProcessingStage.RECEPTION,
                status=ProcessingStatus.PENDING,
                metadata={
                    'start_config': config,
                    'user_id': g.current_user.id
                }
            )

            # Start pipeline with context
            result = pipeline_service.start_pipeline(
                pipeline_id,
                context=context
            )

            return ResponseBuilder.success({
                'status': 'started',
                'pipeline_id': str(pipeline_id),
                'context_id': str(context.request_id)
            })

        except ValidationError as ve:
            return handle_validation_error(ve)
        except Exception as e:
            return handle_service_error(
                e,
                f"Failed to start pipeline {pipeline_id}",
                logger
            )

    @pipeline_bp.route('/<pipeline_id>/status', methods=['GET'])
    @validate_pipeline_id
    @jwt_manager.permission_required('pipeline:read')
    async def get_pipeline_status(pipeline_id):
        """Get comprehensive pipeline status"""
        try:
            # Get persisted status
            db_status = pipeline_service.get_pipeline_status(pipeline_id)

            # Get runtime status
            runtime_status = current_app.pipeline_manager.get_pipeline_status(
                str(pipeline_id)
            )

            # Get staging status
            staging_status = await staging_manager.get_pipeline_status(
                str(pipeline_id)
            )

            # Combine all status information
            combined_status = {
                **db_status,
                'runtime_status': runtime_status or {},
                'staging_status': staging_status or {}
            }

            schema = PipelineStatusResponseSchema()
            return ResponseBuilder.success(schema.dump(combined_status))

        except Exception as e:
            return handle_service_error(
                e,
                f"Failed to get status for pipeline {pipeline_id}",
                logger
            )

    @pipeline_bp.route('/<pipeline_id>/logs', methods=['GET'])
    @validate_pipeline_id
    @jwt_manager.permission_required('pipeline:read')
    def get_pipeline_logs(pipeline_id):
        """Get filtered pipeline logs"""
        try:
            # Get logs with filters
            logs = pipeline_service.get_pipeline_logs(
                pipeline_id,
                start_time=request.args.get('start_time'),
                end_time=request.args.get('end_time'),
                level=request.args.get('level'),
                component=request.args.get('component')
            )

            schema = PipelineLogsResponseSchema()
            return ResponseBuilder.success(schema.dump({'logs': logs}))

        except Exception as e:
            return handle_service_error(
                e,
                f"Failed to retrieve logs for pipeline {pipeline_id}",
                logger
            )

    @pipeline_bp.route('/<pipeline_id>/metrics', methods=['GET'])
    @validate_pipeline_id
    @jwt_manager.permission_required('pipeline:read')
    async def get_pipeline_metrics(pipeline_id):
        """Get comprehensive pipeline metrics"""
        try:
            # Get metrics from multiple sources
            service_metrics = pipeline_service.get_pipeline_metrics(pipeline_id)
            runtime_metrics = current_app.pipeline_manager.get_pipeline_metrics(
                str(pipeline_id)
            )
            staging_metrics = await staging_manager.get_pipeline_metrics(
                str(pipeline_id)
            )

            # Combine metrics
            combined_metrics = {
                **service_metrics,
                'runtime_metrics': runtime_metrics or {},
                'staging_metrics': staging_metrics or {}
            }

            schema = PipelineMetricsResponseSchema()
            return ResponseBuilder.success(schema.dump(combined_metrics))

        except Exception as e:
            return handle_service_error(
                e,
                f"Failed to retrieve metrics for pipeline {pipeline_id}",
                logger
            )

    # Error handlers
    @pipeline_bp.errorhandler(404)
    def not_found_error(error):
        """Handle resource not found errors"""
        return ResponseBuilder.error(
            "Resource not found",
            status_code=404
        )

    @pipeline_bp.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors"""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return ResponseBuilder.error(
            "Internal server error",
            status_code=500
        )

    return pipeline_bp