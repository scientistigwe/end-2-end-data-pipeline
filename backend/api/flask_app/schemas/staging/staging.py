# backend/api/flask_app/schemas/staging.py

from marshmallow import Schema, fields, validates_schema, ValidationError, post_load
from marshmallow.validate import OneOf
from marshmallow_enum import EnumField
from typing import Dict, Any, Optional, List

from core.messaging.event_types import (
    ComponentType,
    ReportSectionType,
    ProcessingStatus
)


class BaseOutputSchema(Schema):
    """
    Comprehensive base schema for staged outputs with core capabilities.
    """
    # Core Identification Fields
    id = fields.String(required=True)
    pipeline_id = fields.String(required=True)
    reference_id = fields.String(required=False, allow_none=True)

    # Enumeration Fields with Strong Typing
    component_type = EnumField(ComponentType, by_value=True, required=True)
    output_type = EnumField(ReportSectionType, by_value=True, required=True)
    status = EnumField(ProcessingStatus, by_value=True, default=ProcessingStatus.PENDING)

    # Storage Metadata
    storage_path = fields.String(required=False, allow_none=True)
    data_size = fields.Integer(default=0)
    is_temporary = fields.Boolean(default=True)

    # Flexible Metadata Handling
    metadata = fields.Dict(keys=fields.String(), values=fields.Raw(), default={})
    metrics = fields.Dict(keys=fields.String(), values=fields.Raw(), default={})

    # Timestamp Fields
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    expires_at = fields.DateTime(allow_none=True)


class StagedOutputRequestSchema(BaseOutputSchema):
    """
    Schema for creating or updating staged outputs with request-specific fields.
    """
    # Additional fields specific to request context
    config = fields.Dict(required=False)
    input_data = fields.Dict(required=False)
    user_id = fields.String(required=False)

    @validates_schema
    def validate_request_fields(self, data: Dict[str, Any], **kwargs) -> None:
        """
        Validate request-specific fields and constraints.
        """
        if not data.get('pipeline_id'):
            raise ValidationError('Pipeline ID is required for output request')


class StagedOutputResponseSchema(BaseOutputSchema):
    """
    Schema for returning staged output details with response-specific fields.
    """
    progress = fields.Float(validate=lambda n: 0 <= n <= 100)
    error_details = fields.Dict(required=False, allow_none=True)
    result = fields.Dict(required=False, allow_none=True)
    processed_records = fields.Integer(required=False)

    @validates_schema
    def validate_response_fields(self, data: Dict[str, Any], **kwargs) -> None:
        """
        Validate response-specific fields and constraints.
        """
        if data.get('status') == ProcessingStatus.FAILED and not data.get('error_details'):
            raise ValidationError('Failed status requires error details')


class QualityOutputSchema(StagedOutputResponseSchema):
    """Schema for quality-specific outputs"""
    quality_score = fields.Float()
    issues_count = fields.Integer()
    critical_issues_count = fields.Integer()
    warnings_count = fields.Integer()
    resolved_issues_count = fields.Integer()
    recommendations_count = fields.Integer()

    completeness_score = fields.Float(allow_none=True)
    consistency_score = fields.Float(allow_none=True)
    accuracy_score = fields.Float(allow_none=True)

    validation_results = fields.Dict()
    profile_data = fields.Dict()
    issue_summary = fields.Dict()
    recommendations = fields.List(fields.Dict())


class InsightOutputSchema(StagedOutputResponseSchema):
    """Schema for insight-specific outputs"""
    insight_count = fields.Integer()
    goal_alignment_score = fields.Float()
    business_impact_score = fields.Float()
    confidence_score = fields.Float()

    insights = fields.List(fields.Dict())
    goals_analysis = fields.Dict()
    metrics_analysis = fields.Dict()
    patterns_discovered = fields.List(fields.Dict())
    correlations = fields.Dict()
    recommendations = fields.List(fields.Dict())


class DecisionOutputSchema(StagedOutputResponseSchema):
    """Schema for decision-specific outputs"""
    decision_options = fields.List(fields.Dict())
    selected_option = fields.Dict(allow_none=True)
    decision_criteria = fields.Dict()
    impact_analysis = fields.Dict()
    confidence_score = fields.Float(allow_none=True)


class RecommendationOutputSchema(StagedOutputResponseSchema):
    """Schema for recommendation-specific outputs"""
    recommendation_candidates = fields.List(fields.Dict())
    top_recommendations = fields.List(fields.Dict())
    ranking_criteria = fields.Dict()
    diversity_score = fields.Float(allow_none=True)
    personalization_score = fields.Float(allow_none=True)


class AnalyticsOutputSchema(StagedOutputResponseSchema):
    """Schema for analytics-specific outputs"""
    # Model and Training Metadata
    model_type = fields.String(required=True)
    model_name = fields.String(required=False, allow_none=True)
    training_duration = fields.Float()
    iteration_count = fields.Integer()

    # Performance Metrics
    performance_metrics = fields.Dict(keys=fields.String(), values=fields.Raw())
    feature_importance = fields.Dict(keys=fields.String(), values=fields.Float())
    model_parameters = fields.Dict()

    # Prediction and Evaluation Results
    predictions = fields.List(fields.Dict())
    evaluation_results = fields.Dict()
    model_artifacts = fields.Dict()

    # Additional Analytical Insights
    data_distribution = fields.Dict()
    outliers = fields.List(fields.Dict())
    correlation_matrix = fields.Dict()

    # Model Performance Indicators
    accuracy = fields.Float(allow_none=True)
    precision = fields.Float(allow_none=True)
    recall = fields.Float(allow_none=True)
    f1_score = fields.Float(allow_none=True)


class PipelineOutputSchema(StagedOutputResponseSchema):
    """Schema for pipeline-specific outputs"""
    # Pipeline Execution Metadata
    pipeline_type = fields.String(required=True)
    execution_mode = fields.String()

    # Stage-level Details
    stages_completed = fields.List(fields.String())
    current_stage = fields.String()
    stage_durations = fields.Dict(keys=fields.String(), values=fields.Float())

    # Performance Tracking
    total_processing_time = fields.Float()
    memory_usage = fields.Dict()
    cpu_usage = fields.Dict()

    # Error and Retry Tracking
    error_count = fields.Integer(default=0)
    retry_count = fields.Integer(default=0)
    critical_errors = fields.List(fields.Dict())

    # Configuration and Metadata
    configuration = fields.Dict()
    input_parameters = fields.Dict()

    # Execution Environment
    environment_details = fields.Dict()
    resource_constraints = fields.Dict()


class SettingsOutputSchema(StagedOutputResponseSchema):
    """Schema for settings-specific outputs"""
    # User and System Preferences
    user_id = fields.String(required=False)
    settings_version = fields.String()
    previous_version = fields.String(allow_none=True)

    # Preference Categories
    user_preferences = fields.Dict()
    system_settings = fields.Dict()
    appearance_settings = fields.Dict()

    # Security and Privacy
    privacy_settings = fields.Dict()
    security_configuration = fields.Dict()
    access_control = fields.Dict()

    # Notification and Communication
    notification_preferences = fields.Dict()
    communication_settings = fields.Dict()

    # Audit and Change Tracking
    change_history = fields.List(fields.Dict())
    last_modified_by = fields.String(allow_none=True)
    last_modified_at = fields.DateTime(allow_none=True)


class MonitoringOutputSchema(StagedOutputResponseSchema):
    """Schema for monitoring-specific outputs"""
    # System Health Metrics
    system_status = fields.String()
    overall_health_score = fields.Float()

    # Resource Monitoring
    cpu_usage = fields.Dict()
    memory_usage = fields.Dict()
    disk_usage = fields.Dict()
    network_metrics = fields.Dict()

    # Performance Indicators
    response_times = fields.Dict(keys=fields.String(), values=fields.Float())
    error_rates = fields.Dict(keys=fields.String(), values=fields.Float())
    throughput = fields.Dict()

    # Alert and Anomaly Tracking
    active_alerts = fields.List(fields.Dict())
    recent_anomalies = fields.List(fields.Dict())
    critical_thresholds = fields.Dict()

    # Comprehensive Logs
    system_logs = fields.List(fields.Dict())
    error_logs = fields.List(fields.Dict())


class ReportOutputSchema(StagedOutputResponseSchema):
    """Schema for report-specific outputs"""
    # Report Metadata
    report_type = fields.String(required=True)
    report_version = fields.String()
    report_format = fields.List(fields.String())

    # Structural Elements
    sections = fields.List(fields.Dict())
    visualizations = fields.List(fields.Dict())
    summary = fields.Dict()

    # Rendering and Interactivity
    interactivity_config = fields.Dict()
    rendering_metadata = fields.Dict()

    # Distribution and Access
    distribution_info = fields.Dict()
    access_control = fields.Dict()

    # Compliance and Validation
    validation_status = fields.String()
    compliance_checks = fields.List(fields.Dict())


# Update the StagedOutputSchemas class
class StagedOutputSchemas:
    """
    Facade class to provide convenient access to different schema types.
    """
    BASE = BaseOutputSchema
    REQUEST = StagedOutputRequestSchema
    RESPONSE = StagedOutputResponseSchema

    # Component-specific schemas
    QUALITY = QualityOutputSchema
    INSIGHT = InsightOutputSchema
    DECISION = DecisionOutputSchema
    RECOMMENDATION = RecommendationOutputSchema
    ANALYTICS = AnalyticsOutputSchema
    PIPELINE = PipelineOutputSchema
    SETTINGS = SettingsOutputSchema
    MONITORING = MonitoringOutputSchema
    REPORT = ReportOutputSchema

    @classmethod
    def get_schema(
            cls,
            component_type: ComponentType,
            schema_type: str = 'response'
    ) -> Schema:
        """
        Enhanced schema retrieval with more component types.
        """
        schema_mapping = {
            'base': cls.BASE,
            'request': cls.REQUEST,
            'response': cls.RESPONSE
        }

        component_mapping = {
            ComponentType.QUALITY_MANAGER: cls.QUALITY,
            ComponentType.INSIGHT_MANAGER: cls.INSIGHT,
            ComponentType.DECISION_MANAGER: cls.DECISION,
            ComponentType.RECOMMENDATION_MANAGER: cls.RECOMMENDATION,
            ComponentType.ANALYTICS_MANAGER: cls.ANALYTICS,
            ComponentType.PIPELINE_SERVICE: cls.PIPELINE,
            ComponentType.SETTINGS_SERVICE: cls.SETTINGS,
            ComponentType.MONITORING_MANAGER: cls.MONITORING,
            ComponentType.REPORT_MANAGER: cls.REPORT
        }

        base_schema = schema_mapping.get(schema_type, cls.RESPONSE)

        # If a component-specific schema exists and we want a response, use it
        if schema_type == 'response' and component_type in component_mapping:
            return component_mapping[component_type]

        return base_schema
