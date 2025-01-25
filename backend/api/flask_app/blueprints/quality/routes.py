# flask_app/blueprints/quality/routes.py

from flask import Blueprint, request, g, current_app
from marshmallow import ValidationError
from uuid import UUID
import logging
from datetime import datetime
from typing import Dict, Any

from ...schemas.staging.quality import (
    QualityCheckRequestSchema,
    QualityCheckResponseSchema,
    QualityStagingRequestSchema,
    QualityStagingResponseSchema
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


def validate_uuid(identifier_type: str = 'id'):
    """Decorator to validate UUID format for different identifier types."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                for key, value in kwargs.items():
                    if key.endswith(identifier_type):
                        kwargs[key] = UUID(value)
                return func(*args, **kwargs)
            except ValueError:
                return ResponseBuilder.error(
                    f"Invalid {identifier_type} format",
                    status_code=400
                )

        return wrapper

    return decorator


def create_quality_blueprint(quality_service, staging_manager):
    """
    Create quality blueprint with comprehensive functionality.

    Args:
        quality_service: Service for quality analysis operations
        staging_manager: Manager for staging operations

    Returns:
        Blueprint: Configured quality routes
    """
    quality_bp = Blueprint('quality', __name__)

    @quality_bp.route('/analyze', methods=['POST'])
    async def start_quality_analysis():
        """Initiate quality analysis with comprehensive validation."""
        try:
            schema = QualityCheckRequestSchema()
            data = schema.load(request.get_json())
            data.update({
                'user_id': g.current_user.id,
                'request_time': datetime.utcnow().isoformat()
            })

            # Stage quality analysis request
            staging_ref = await staging_manager.stage_data(
                data=data,
                component_type=ComponentType.QUALITY_MANAGER,
                pipeline_id=data.get('pipeline_id'),
                metadata={
                    'analysis_type': 'quality_check',
                    'validation_count': len(data['validation_rules']),
                    'columns_validated': list(data['column_rules'].keys()),
                    'sampling_enabled': bool(data.get('sampling_config')),
                    'advanced_options': data.get('advanced_options', {})
                }
            )

            # Initialize analysis
            analysis = await quality_service.start_analysis(data, staging_ref)

            # Track analysis configuration
            await quality_service.track_analysis_start({
                'analysis_id': str(analysis.id),
                'staging_ref': staging_ref,
                'config_summary': {
                    'rules_count': len(data['validation_rules']),
                    'columns_count': len(data['column_rules']),
                    'thresholds': len(data.get('quality_thresholds', {}))
                }
            })

            return ResponseBuilder.success({
                'analysis_id': str(analysis.id),
                'status': analysis.status.value,
                'staging_reference': staging_ref,
                'estimated_duration': analysis.estimated_duration
            })

        except ValidationError as ve:
            return handle_validation_error(ve)
        except Exception as e:
            return handle_service_error(
                e,
                "Failed to start quality analysis",
                logger
            )

    @quality_bp.route('/<analysis_id>/status', methods=['GET'])
    @validate_uuid('analysis_id')
    async def get_analysis_status(analysis_id):
        """Get detailed quality analysis status with progress tracking."""
        try:
            analysis_status = await quality_service.get_analysis_status(analysis_id)

            # Retrieve and enrich staging status
            staging_status = None
            if analysis_status.staging_reference:
                staging_status = await staging_manager.get_status(
                    analysis_status.staging_reference
                )
                execution_metrics = await staging_manager.get_execution_metrics(
                    analysis_status.staging_reference
                )
                staging_status['execution_metrics'] = execution_metrics

            response_data = QualityCheckResponseSchema().dump({
                **analysis_status,
                'staging_status': staging_status,
                'progress': {
                    'current_stage': analysis_status.current_stage,
                    'completed_rules': analysis_status.completed_rules,
                    'total_rules': analysis_status.total_rules,
                    'estimated_completion': analysis_status.estimated_completion,
                    'performance_metrics': analysis_status.performance_metrics
                }
            })

            return ResponseBuilder.success({'status': response_data})

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to get analysis status",
                logger
            )

    @quality_bp.route('/<analysis_id>/results', methods=['GET'])
    @validate_uuid('analysis_id')
    async def get_analysis_results(analysis_id):
        """Get comprehensive quality analysis results."""
        try:
            results = await quality_service.get_analysis_results(analysis_id)

            if not results:
                return handle_not_found_error(
                    Exception("Results not found"),
                    f"No results found for analysis {analysis_id}",
                    logger
                )

            # Retrieve column profiles if available
            column_profiles = None
            if results.staging_reference:
                column_profiles = await staging_manager.get_column_profiles(
                    results.staging_reference
                )

            response_data = QualityCheckResponseSchema().dump({
                **results,
                'data_profile': column_profiles,
                'execution_summary': {
                    'start_time': results.start_time,
                    'end_time': results.end_time,
                    'duration': results.duration,
                    'rules_evaluated': results.rules_evaluated
                }
            })

            return ResponseBuilder.success({'results': response_data})

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to get analysis results",
                logger
            )

    @quality_bp.route('/<analysis_id>/issues', methods=['GET'])
    @validate_uuid('analysis_id')
    async def get_quality_issues(analysis_id):
        """Get detailed quality issues with full context."""
        try:
            issues = await quality_service.get_quality_issues(analysis_id)

            # Enrich with historical context
            if issues.staging_reference:
                historical_context = await staging_manager.get_historical_issues(
                    issues.staging_reference
                )
                for issue in issues.issues_found:
                    issue['historical_context'] = historical_context.get(
                        issue['issue_id'],
                        {}
                    )

            return ResponseBuilder.success({
                'issues': issues.issues_found,
                'summary': issues.issue_summary,
                'remediation_suggestions': issues.remediation_suggestions
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to get quality issues",
                logger
            )

    @quality_bp.route('/<analysis_id>/remediation', methods=['GET'])
    @validate_uuid('analysis_id')
    async def get_remediation_plan(analysis_id):
        """Get detailed remediation plan with impact analysis."""
        try:
            remediation_plan = await quality_service.get_remediation_plan(analysis_id)

            if not remediation_plan:
                return handle_not_found_error(
                    Exception("Remediation plan not found"),
                    f"No remediation plan found for analysis {analysis_id}",
                    logger
                )

            return ResponseBuilder.success({
                'remediation_plan': {
                    'suggestions': remediation_plan.suggestions,
                    'priorities': remediation_plan.priorities,
                    'effort_estimates': remediation_plan.effort_estimates,
                    'impact_analysis': remediation_plan.impact_analysis
                }
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to get remediation plan",
                logger
            )

    @quality_bp.route('/config/rules', methods=['POST'])
    async def update_validation_rules():
        """Update quality validation rules with tracking."""
        try:
            new_rules = request.get_json()
            pipeline_id = new_rules.get('pipeline_id')

            # Stage updated rules
            staging_ref = await staging_manager.stage_data(
                data=new_rules,
                component_type=ComponentType.QUALITY_MANAGER,
                pipeline_id=pipeline_id,
                metadata={
                    'operation': 'rule_update',
                    'update_time': datetime.utcnow().isoformat(),
                    'updated_by': g.current_user.id
                }
            )

            # Apply rule updates
            update_result = await quality_service.update_validation_rules(
                new_rules,
                staging_ref
            )

            return ResponseBuilder.success({
                'status': 'updated',
                'rule_count': len(new_rules.get('rules', [])),
                'staging_reference': staging_ref,
                'effective_time': datetime.utcnow().isoformat()
            })

        except Exception as e:
            return handle_service_error(
                e,
                "Failed to update validation rules",
                logger
            )

    @quality_bp.errorhandler(404)
    def not_found_error(error):
        """Handle resource not found errors."""
        return ResponseBuilder.error(
            "Resource not found",
            status_code=404
        )

    @quality_bp.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return ResponseBuilder.error(
            "Internal server error",
            status_code=500
        )

    return quality_bp