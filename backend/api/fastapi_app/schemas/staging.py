# backend/api/fastapi_app/schemas/staging.py

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, validator, model_validator, constr, confloat, ConfigDict
from enum import Enum
from .base import BaseStagingSchema, ProcessingStatus, ComponentType

class ReportStatus(str, Enum):
    """Enum for report generation status"""
    QUEUED = "queued"
    GENERATING = "generating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"

class ReportGenerationStatus(BaseStagingSchema):
    """Schema for report generation status tracking"""
    status: ReportStatus
    progress: float = Field(0.0, ge=0.0, le=100.0)
    current_section: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    generation_metrics: Dict[str, Any] = Field(default_factory=dict)
    error_details: Optional[Dict[str, Any]] = None
    staging_details: Optional[Dict[str, Any]] = None

    @model_validator(mode='after')
    def validate_progress(self) -> 'ReportGenerationStatus':
        """Validates progress against status"""
        if self.status == ReportStatus.COMPLETED and self.progress != 100.0:
            self.progress = 100.0
        if self.status == ReportStatus.FAILED and not self.error_details:
            raise ValueError("Error details required for failed status")
        return self

class ReportTemplateRequest(BaseModel):
    """Schema for report template creation"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    type: str = Field(..., pattern='^(standard|custom|automated)$')
    sections: List[Dict[str, Any]]
    parameters: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ReportTemplateResponse(BaseModel):
    """Schema for report template responses"""
    template_id: UUID
    name: str
    type: str
    version: int
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    parameters: Dict[str, Any]
    usage_count: int = 0

class ReportSectionsResponse(BaseModel):
    """Schema for report sections response"""
    sections: List[Dict[str, Any]]
    metrics: Optional[Dict[str, Any]] = None
    section_order: List[str]
    dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    validation_results: Optional[Dict[str, Any]] = None

class StagedOutputRequest(BaseStagingSchema):
    """Request schema for staged output operations"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    output_type: str
    format: str
    expires_at: Optional[datetime] = None
    retention_policy: Optional[Dict[str, Any]] = None
    processing_config: Dict[str, Any] = Field(default_factory=dict)

class StagedOutputResponse(BaseStagingSchema):
    """Response schema for staged output operations"""
    name: str
    description: Optional[str]
    output_type: str
    format: str
    size: int = 0
    processing_status: ProcessingStatus
    processing_metrics: Dict[str, Any] = Field(default_factory=dict)
    validation_results: Optional[Dict[str, Any]] = None
    access_url: Optional[str] = None
    expires_at: Optional[datetime] = None

class StagedOutputSchemas:
    """Registry for component-specific output schemas"""
    _schemas = {}

    @classmethod
    def register_schema(cls, component_type: str, schema_type: str, schema_class: type):
        """Register a schema for a specific component and type"""
        if component_type not in cls._schemas:
            cls._schemas[component_type] = {}
        cls._schemas[component_type][schema_type] = schema_class

    @classmethod
    def get_schema(cls, component_type: str, schema_type: str) -> type:
        """Get the registered schema for a component and type"""
        return cls._schemas.get(component_type, {}).get(
            schema_type,
            StagedOutputResponse if schema_type == 'response' else StagedOutputRequest
        )

class ArchiveRequest(BaseModel):
    """Request schema for archiving staged outputs"""
    ttl_days: Optional[int] = Field(None, ge=1)
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CleanupRequest(BaseModel):
    """Request schema for cleanup operations"""
    older_than_days: Optional[int] = Field(None, ge=1)
    status_filter: Optional[List[ProcessingStatus]] = None
    component_filter: Optional[List[ComponentType]] = None
    metadata_filter: Optional[Dict[str, Any]] = None

class MetricsResponse(BaseModel):
    """Response schema for metrics endpoints"""
    storage_metrics: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    component_metrics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    collection_time: datetime = Field(default_factory=datetime.utcnow)


class QualityCheckRequest(BaseStagingSchema):
    """Request schema for quality checks"""
    pipeline_id: UUID
    rules: List[Dict[str, Any]]
    thresholds: Dict[str, float]
    sampling_config: Optional[Dict[str, Any]] = None
    validation_level: str = Field(..., pattern='^(basic|advanced|comprehensive)$')
    notification_settings: Optional[Dict[str, Any]] = None

class QualityCheckResponse(BaseStagingSchema):
    """Response schema for quality check results"""
    check_id: UUID
    status: ProcessingStatus
    quality_score: float = Field(..., ge=0.0, le=1.0)
    issues_found: List[Dict[str, Any]]
    metrics: Dict[str, float]
    recommendations: List[Dict[str, Any]]
    execution_time: float

class QualityStagingRequest(BaseStagingSchema):
    """Request schema for quality staging operations"""
    source_id: UUID
    target_id: UUID
    validation_rules: List[Dict[str, Any]]
    quality_gates: Dict[str, Any]
    error_thresholds: Dict[str, float]

class QualityStagingResponse(BaseStagingSchema):
    """Response schema for quality staging results"""
    staging_id: UUID
    validation_results: Dict[str, Any]
    quality_metrics: Dict[str, float]
    gate_results: List[Dict[str, Any]]
    error_summary: Dict[str, int]

class QualityIssuesResponse(BaseStagingSchema):
    """Response schema for quality issues"""
    issues: List[Dict[str, Any]]
    severity_counts: Dict[str, int]
    impact_analysis: Dict[str, Any]
    remediation_cost: Dict[str, float]

class QualityRemediationResponse(BaseStagingSchema):
    """Response schema for quality remediation plans"""
    remediation_id: UUID
    plan: List[Dict[str, Any]]
    estimated_effort: Dict[str, Any]
    priority_order: List[str]
    dependencies: Dict[str, List[str]]

class ValidationRulesRequest(BaseStagingSchema):
    """Request schema for validation rules"""
    rules: List[Dict[str, Any]]
    scope: str = Field(..., pattern='^(column|table|database)$')
    severity_levels: Dict[str, str]
    custom_validators: Optional[Dict[str, Any]] = None

# staging/analytics.py
class AnalyticsStagingRequest(BaseStagingSchema):
    """Request schema for analytics staging"""
    model_type: str
    features: List[str]
    target_column: str
    split_ratio: float = Field(0.2, ge=0.0, le=1.0)
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    preprocessing_steps: List[Dict[str, Any]]

class AnalyticsStagingResponse(BaseStagingSchema):
    """Response schema for analytics staging results"""
    model_id: UUID
    metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    model_artifacts: Dict[str, Any]
    validation_results: Dict[str, Any]

# staging/reports.py
class ReportStagingRequest(BaseStagingSchema):
    """Request schema for report staging"""
    report_type: str
    timeframe: Dict[str, Any]
    metrics: List[str]
    grouping: Optional[List[str]] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    format: str = Field(..., pattern='^(pdf|excel|html)$')

class ReportStagingResponse(BaseStagingSchema):
    """Response schema for report staging results"""
    report_id: UUID
    generated_at: datetime
    sections: List[Dict[str, Any]]
    data_summary: Dict[str, Any]
    visualizations: List[Dict[str, Any]]

# data_source/models.py
class FileUploadRequest(BaseModel):
    """Request schema for file uploads"""
    filename: str
    content_type: str
    size: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    chunk_size: Optional[int] = None

class FileUploadResponse(BaseModel):
    """Response schema for file uploads"""
    file_id: UUID
    upload_url: str
    expires_at: datetime
    chunk_urls: Optional[List[str]] = None

class FileSourceResponse(BaseModel):
    """Response schema for file sources"""
    source_id: UUID
    filename: str
    size: int
    content_type: str
    metadata: Dict[str, Any]
    status: str
    created_at: datetime

class DatabaseSourceConfig(BaseModel):
    """Configuration schema for database sources"""
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: Optional[str] = None
    schema: Optional[str] = None
    max_connections: int = 5

class S3SourceConfig(BaseModel):
    """Configuration schema for S3 sources"""
    bucket: str
    region: str
    access_key: str
    secret_key: str
    prefix: Optional[str] = None
    endpoint_url: Optional[str] = None

class APISourceConfig(BaseModel):
    """Configuration schema for API sources"""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = Field(default_factory=dict)
    auth_type: Optional[str] = None
    auth_config: Dict[str, Any] = Field(default_factory=dict)

class StreamSourceConfig(BaseModel):
    """Configuration schema for stream sources"""
    stream_type: str
    connection_string: str
    consumer_group: Optional[str] = None
    topics: List[str]
    schema_registry_url: Optional[str] = None

class DataSourceRequest(BaseModel):
    """Request schema for data sources"""
    name: str
    type: str
    config: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    refresh_interval: Optional[int] = None

class DataSourceResponse(BaseModel):
    """Response schema for data sources"""
    source_id: UUID
    name: str
    type: str
    status: str
    config: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

class PipelineStage(str, Enum):
    """Pipeline processing stages"""
    RECEPTION = "reception"
    QUALITY_CHECK = "quality_check"
    INSIGHT_GENERATION = "insight_generation"
    ADVANCED_ANALYTICS = "advanced_analytics"
    DECISION_MAKING = "decision_making"
    RECOMMENDATION = "recommendation"
    REPORT_GENERATION = "report_generation"

class ProcessingStage(str, Enum):
    INGESTION = "ingestion"
    PROCESSING = "processing"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    COMPLETION = "completion"


class PipelineStatus(str, Enum):
    """Pipeline status states"""
    PENDING = "pending"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    IN_PROGRESS = "in_progress"

class PipelineRequest(BaseModel):
    """Schema for pipeline creation/update requests"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    source_id: UUID
    config: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    enabled: bool = True
    scheduling: Optional[Dict[str, Any]] = None
    target_id: UUID
    steps: List[Dict[str, Any]]
    schedule: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "name": "Daily Data Processing",
                "description": "Process daily data from source",
                "source_id": "123e4567-e89b-12d3-a456-426614174000",
                "config": {
                    "batch_size": 1000,
                    "timeout": 3600,
                    "retries": 3
                },
                "tags": ["daily", "processing"],
                "enabled": True,
                "scheduling": {
                    "frequency": "daily",
                    "time": "00:00"
                }
            }
        }
    )

class PipelineResponse(BaseModel):
    """Schema for pipeline responses"""
    pipeline_id: UUID
    name: str
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    description: Optional[str]
    source_id: UUID
    config: Dict[str, Any]
    tags: List[str]
    enabled: bool
    status: PipelineStatus
    current_stage: Optional[PipelineStage]
    progress: float = Field(0.0, ge=0.0, le=100.0)
    created_at: datetime
    updated_at: datetime
    error_count: int = 0
    metrics: Dict[str, Any] = Field(default_factory=dict)
    owner_id: UUID
    scheduling: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Daily Data Processing",
                "description": "Process daily data from source",
                "source_id": "123e4567-e89b-12d3-a456-426614174001",
                "status": "running",
                "current_stage": "quality_check",
                "progress": 45.5,
                "created_at": "2024-02-09T12:00:00Z",
                "updated_at": "2024-02-09T12:30:00Z"
            }
        }
    )

class PipelineStatusResponse(BaseStagingSchema):
    """Response schema for pipeline status"""
    status: str
    current_step: Optional[str] = None
    progress: float = 0.0
    started_at: Optional[datetime] = None
    errors: List[Dict[str, Any]] = Field(default_factory=list)

class PipelineLogsResponse(BaseStagingSchema):
    """Response schema for pipeline logs"""
    logs: List[Dict[str, Any]]
    total_count: int
    filter_stats: Dict[str, int]
    timeframe: Dict[str, datetime]

class PipelineMetricsResponse(BaseStagingSchema):
    """Response schema for pipeline metrics"""
    execution_time: float
    records_processed: int
    error_rate: float
    resource_usage: Dict[str, float]
    performance_metrics: Dict[str, Any]

class PipelineListResponse(BaseStagingSchema):
    """Response schema for pipeline listing"""
    pipelines: List[PipelineResponse]
    total_count: int
    page: int
    page_size: int


class DecisionMessageType(str, Enum):
    START = "start"
    PROGRESS = "progress"
    COMPLETE = "complete"
    FAILED = "failed"
    CONTEXT_ANALYZE = "context_analyze"
    OPTIONS_GENERATE = "options_generate"
    VALIDATE = "validate"

# Analytics Schemas
class AnalyticsStagingRequestSchema(BaseStagingSchema):
    model_type: str
    features: List[str]
    parameters: Dict[str, Any]
    training_config: Dict[str, Any] = Field(default_factory=dict)
    validation_split: float = Field(0.2, ge=0.0, le=1.0)


class AnalyticsStagingResponseSchema(BaseStagingSchema):
    model_artifacts: Dict[str, Any]
    performance_metrics: Dict[str, float]
    feature_importance: Dict[str, float]
    predictions: List[Dict[str, Any]]


# Decision Schemas
class DecisionItemSchema(BaseStagingSchema):
    decision_type: DecisionMessageType
    description: str
    context: Dict[str, Any]
    options: List[Dict[str, Any]]
    deadline: Optional[datetime]
    assigned_to: Optional[str]
    priority: str = Field(..., pattern='^(LOW|MEDIUM|HIGH)$')
    rationale: Optional[str]


class DecisionStagingRequest(BaseStagingSchema):
    decision_type: DecisionMessageType
    options: List[Dict[str, Any]]
    criteria: Dict[str, Any]
    constraints: Dict[str, Any] = Field(default_factory=dict)
    deadline: Optional[datetime]


class DecisionStagingResponse(BaseStagingSchema):
    recommendation: Dict[str, Any]
    alternatives: List[Dict[str, Any]]
    impact_analysis: Dict[str, Any]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    rationale: Dict[str, Any]


class DecisionListResponse(BaseStagingSchema):
    """Schema for listing decisions with pagination"""
    decisions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of decision objects"
    )
    total_count: int = Field(
        default=0,
        description="Total number of decisions",
        ge=0
    )
    page: int = Field(
        default=1,
        description="Current page number",
        ge=1
    )
    page_size: int = Field(
        default=10,
        description="Number of items per page",
        ge=1,
        le=100
    )

class DecisionHistoryResponse(BaseStagingSchema):
    """Schema for decision history responses"""
    history: List[Dict[str, Any]] = Field(
        ...,
        description="List of historical decision records"
    )
    summary_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary metrics for the decision history"
    )
    time_range: Dict[str, datetime] = Field(
        default_factory=dict,
        description="Time range of the history records"
    )
    aggregated_stats: Dict[str, Any] = Field(
        default_factory=dict,
        description="Aggregated statistics of decisions"
    )

class DecisionImpactResponse(BaseStagingSchema):
    """Schema for decision impact analysis"""
    impact_metrics: Dict[str, float] = Field(
        ...,
        description="Quantitative metrics of decision impact"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score of the impact analysis"
    )
    historical_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Historical context and comparisons"
    )
    affected_components: List[str] = Field(
        default_factory=list,
        description="Components affected by the decision"
    )
    risk_assessment: Dict[str, Any] = Field(
        default_factory=dict,
        description="Risk assessment details"
    )

    @model_validator(mode='after')
    def validate_impact_metrics(self) -> 'DecisionImpactResponse':
        """Validate that impact metrics contain required fields"""
        required_metrics = {'efficiency', 'cost', 'quality'}
        if not all(metric in self.impact_metrics for metric in required_metrics):
            raise ValueError(f"Impact metrics must contain all required metrics: {required_metrics}")
        return self

class DecisionFeedbackRequest(BaseStagingSchema):
    """Schema for decision feedback requests"""
    feedback_type: str = Field(
        ...,
        pattern='^(positive|negative|neutral)$',
        description="Type of feedback"
    )
    comments: Optional[str] = Field(
        None,
        max_length=1000,
        description="Detailed feedback comments"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Quantitative feedback metrics"
    )
    suggestions: Optional[List[str]] = Field(
        None,
        description="Suggestions for improvement"
    )

# Insight Schemas
class InsightStagingRequestSchema(BaseStagingSchema):
    analysis_config: Dict[str, Any]
    target_metrics: List[str]
    time_window: Dict[str, Any]
    insight_types: List[str] = Field(..., pattern='^(trend|anomaly|correlation|pattern)$')


class InsightStagingResponseSchema(BaseStagingSchema):
    insights: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    supporting_metrics: Dict[str, Any]
    impact_analysis: Dict[str, Any]


# Monitoring Schemas
class MonitoringStagingRequestSchema(BaseStagingSchema):
    metrics: List[str]
    aggregation: str = Field(..., pattern='^(sum|avg|min|max)$')
    time_window: Dict[str, Any]
    filters: Dict[str, Any] = Field(default_factory=dict)


class MonitoringStagingResponseSchema(BaseStagingSchema):
    results: List[Dict[str, Any]]
    aggregates: Dict[str, Any]


class AlertStagingRequestSchema(BaseStagingSchema):
    alert_type: str
    severity: str = Field(..., pattern='^(info|warning|critical)$')
    conditions: Dict[str, Any]
    notification_config: Dict[str, Any] = Field(default_factory=dict)


class AlertStagingResponseSchema(BaseStagingSchema):
    alert_status: str = Field(..., pattern='^(active|acknowledged|resolved)$')
    triggered_at: datetime
    acknowledged_by: Optional[str]
    resolved_by: Optional[str]


# Pipeline Schemas
class PipelineRequestSchema(BaseStagingSchema):
    source_configs: Dict[str, Any]
    destination_configs: Dict[str, Any]
    pipeline_type: str
    execution_mode: str = Field(..., pattern='^(sequential|parallel|distributed)$')
    max_retries: int = Field(3, ge=0, le=10)
    retry_strategy: str = Field(..., pattern='^(exponential|linear|fixed)$')


class PipelineResponseSchema(BaseStagingSchema):
    status: ProcessingStatus
    current_stage: Optional[ProcessingStage]
    execution_time: Optional[float]
    records_processed: int = 0
    error_count: int = 0
    last_error: Optional[Dict[str, Any]]
    runtime_status: Optional[Dict[str, Any]]
    configuration: Dict[str, Any]


# Quality Schemas
class QualityCheckRequestSchema(BaseStagingSchema):
    validation_rules: Dict[str, Dict[str, Any]]
    quality_thresholds: Dict[str, float]
    sampling_config: Optional[Dict[str, Any]]
    advanced_options: Dict[str, bool] = Field(
        default_factory=lambda: {
            "anomaly_detection": False,
            "pattern_matching": False,
            "correlation_analysis": False
        }
    )


class QualityCheckResponseSchema(BaseStagingSchema):
    quality_score: float = Field(..., ge=0.0, le=1.0)
    issues_found: Dict[str, int]
    validation_results: Dict[str, Any]
    remediation_suggestions: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]


# Recommendation Schemas
class RecommendationStagingRequest(BaseStagingSchema):
    type: str
    context: Dict[str, Any]
    constraints: Dict[str, Any] = Field(default_factory=dict)
    priority: str = Field(..., pattern='^(low|medium|high|critical)$')
    target_metrics: List[str]


class RecommendationStagingResponse(BaseStagingSchema):
    recommendations: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    impact_analysis: Dict[str, Any]
    priority_ranking: Dict[str, Any]


class RecommendationApplyRequest(BaseStagingSchema):
    """Schema for applying recommendations"""
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context for recommendation application"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for applying the recommendation"
    )
    priority: str = Field(
        ...,
        pattern='^(high|medium|low)$',
        description="Priority level for application"
    )
    schedule: Optional[Dict[str, Any]] = Field(
        None,
        description="Schedule for recommendation application"
    )


class RecommendationDismissRequest(BaseStagingSchema):
    """Schema for dismissing recommendations"""
    reason: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Reason for dismissing the recommendation"
    )
    feedback: Optional[str] = Field(
        None,
        max_length=1000,
        description="Additional feedback for improvement"
    )
    alternative_action: Optional[str] = Field(
        None,
        description="Alternative action taken instead"
    )
    dismissal_category: str = Field(
        ...,
        pattern='^(irrelevant|incorrect|already_implemented|other)$',
        description="Category of dismissal"
    )


class RecommendationListResponse(BaseStagingSchema):
    """Schema for listing recommendations"""
    recommendations: List[Dict[str, Any]] = Field(
        ...,
        description="List of recommendation objects"
    )
    total_count: int = Field(
        default=0,
        ge=0,
        description="Total number of recommendations"
    )
    filter_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of applied filters"
    )
    priority_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Distribution of recommendations by priority"
    )


class RecommendationImpactResponse(BaseStagingSchema):
    """Schema for recommendation impact analysis"""
    metrics: Dict[str, float] = Field(
        ...,
        description="Impact metrics for the recommendation"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the impact assessment"
    )
    potential_risks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Potential risks associated with implementation"
    )
    estimated_effort: Dict[str, Any] = Field(
        default_factory=dict,
        description="Estimated effort for implementation"
    )
    cost_benefit_analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cost-benefit analysis details"
    )

    @model_validator(mode='after')
    def validate_metrics(self) -> 'RecommendationImpactResponse':
        """Validate that required impact metrics are present"""
        required_metrics = {'roi', 'time_savings', 'resource_impact'}
        if not all(metric in self.metrics for metric in required_metrics):
            raise ValueError(f"Impact metrics must contain all required metrics: {required_metrics}")
        return self


# Report Schemas
class ReportStagingRequestSchema(BaseStagingSchema):
    report_type: str
    format: str = Field(..., pattern='^(pdf|excel|csv|json)$')
    sections: List[Dict[str, Any]]
    parameters: Dict[str, Any] = Field(default_factory=dict)
    template_id: Optional[UUID]


class ReportStagingResponseSchema(BaseStagingSchema):
    output_path: str
    sections: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    visualizations: List[Dict[str, Any]]


# Settings Schemas
class SettingsStagingRequestSchema(BaseStagingSchema):
    category: str = Field(..., pattern='^(user|system|security|notifications|appearance|integrations)$')
    settings: Dict[str, Any]
    overrides: Dict[str, Any] = Field(default_factory=dict)
    scope: str = Field(..., pattern='^(global|user|pipeline)$')


class SettingsStagingResponseSchema(BaseStagingSchema):
    applied_settings: Dict[str, Any]
    effective_settings: Dict[str, Any]
    override_history: List[Dict[str, Any]]


# Validation Schemas
class ValidationRuleSchema(BaseModel):
    rule_type: str
    field: str
    condition: str
    value: Any
    severity: str = Field(..., pattern='^(critical|major|minor)$')
    message: Optional[str]


class ValidationRequestSchema(BaseStagingSchema):
    target_type: str
    rules: List[ValidationRuleSchema]
    validation_context: Dict[str, Any] = Field(default_factory=dict)
    threshold: float = Field(..., ge=0.0, le=1.0)


class ValidationResponseSchema(BaseStagingSchema):
    """Schema for validation response data.

    Attributes:
        validation_id: Unique identifier for the validation
        passed: Boolean indicating if validation passed
        results: List of validation results with detailed information
        validation_time: Timestamp of validation
        metrics: Dictionary containing validation metrics
    """
    validation_id: UUID
    passed: bool
    results: List[Dict[str, Any]]
    validation_time: datetime
    metrics: Dict[str, Any]

    @model_validator(mode='after')
    def validate_results(self) -> 'ValidationResponseSchema':
        """Validate that failed validations include detailed results.

        Returns:
            Self: The validated model instance

        Raises:
            ValueError: If validation failed but no results provided
        """
        if not self.passed and not self.results:
            raise ValueError(
                'Failed validation must include detailed results. '
                'Please provide information about failure reasons.'
            )
        return self