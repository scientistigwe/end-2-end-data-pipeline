# backend/api/fastapi_app/schemas/staging.py

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, validator, root_validator, constr, confloat
from enum import Enum

# staging/quality.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator
from .staging import BaseStagingSchema, ProcessingStatus, ComponentType

class QualityCheckRequest(BaseStagingSchema):
    """Request schema for quality checks"""
    pipeline_id: UUID
    rules: List[Dict[str, Any]]
    thresholds: Dict[str, float]
    sampling_config: Optional[Dict[str, Any]] = None
    validation_level: str = Field(..., regex='^(basic|advanced|comprehensive)$')
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
    scope: str = Field(..., regex='^(column|table|database)$')
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
    format: str = Field(..., regex='^(pdf|excel|html)$')

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

# pipeline/models.py
class PipelineRequest(BaseStagingSchema):
    """Request schema for pipeline operations"""
    name: str
    description: Optional[str] = None
    source_id: UUID
    target_id: UUID
    steps: List[Dict[str, Any]]
    schedule: Optional[Dict[str, Any]] = None

class PipelineResponse(BaseStagingSchema):
    """Response schema for pipeline details"""
    pipeline_id: UUID
    name: str
    status: str
    metrics: Dict[str, Any]
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

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
class ProcessingStage(str, Enum):
    INGESTION = "ingestion"
    PROCESSING = "processing"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    COMPLETION = "completion"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ComponentType(str, Enum):
    ANALYTICS = "analytics"
    DECISION = "decision"
    INSIGHT = "insight"
    MONITORING = "monitoring"
    QUALITY = "quality"
    PIPELINE = "pipeline"


class DecisionMessageType(str, Enum):
    START = "start"
    PROGRESS = "progress"
    COMPLETE = "complete"
    FAILED = "failed"
    CONTEXT_ANALYZE = "context_analyze"
    OPTIONS_GENERATE = "options_generate"
    VALIDATE = "validate"


class BaseStagingSchema(BaseModel):
    """Base schema for all staging operations"""
    id: UUID
    pipeline_id: UUID
    component_type: ComponentType
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        orm_mode = True


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
    priority: str = Field(..., regex='^(LOW|MEDIUM|HIGH)$')
    rationale: Optional[str]


class DecisionStagingRequestSchema(BaseStagingSchema):
    decision_type: DecisionMessageType
    options: List[Dict[str, Any]]
    criteria: Dict[str, Any]
    constraints: Dict[str, Any] = Field(default_factory=dict)
    deadline: Optional[datetime]


class DecisionStagingResponseSchema(BaseStagingSchema):
    recommendation: Dict[str, Any]
    alternatives: List[Dict[str, Any]]
    impact_analysis: Dict[str, Any]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    rationale: Dict[str, Any]


# Insight Schemas
class InsightStagingRequestSchema(BaseStagingSchema):
    analysis_config: Dict[str, Any]
    target_metrics: List[str]
    time_window: Dict[str, Any]
    insight_types: List[str] = Field(..., regex='^(trend|anomaly|correlation|pattern)$')


class InsightStagingResponseSchema(BaseStagingSchema):
    insights: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    supporting_metrics: Dict[str, Any]
    impact_analysis: Dict[str, Any]


# Monitoring Schemas
class MonitoringStagingRequestSchema(BaseStagingSchema):
    metrics: List[str]
    aggregation: str = Field(..., regex='^(sum|avg|min|max)$')
    time_window: Dict[str, Any]
    filters: Dict[str, Any] = Field(default_factory=dict)


class MonitoringStagingResponseSchema(BaseStagingSchema):
    results: List[Dict[str, Any]]
    aggregates: Dict[str, Any]


class AlertStagingRequestSchema(BaseStagingSchema):
    alert_type: str
    severity: str = Field(..., regex='^(info|warning|critical)$')
    conditions: Dict[str, Any]
    notification_config: Dict[str, Any] = Field(default_factory=dict)


class AlertStagingResponseSchema(BaseStagingSchema):
    alert_status: str = Field(..., regex='^(active|acknowledged|resolved)$')
    triggered_at: datetime
    acknowledged_by: Optional[str]
    resolved_by: Optional[str]


# Pipeline Schemas
class PipelineRequestSchema(BaseStagingSchema):
    source_configs: Dict[str, Any]
    destination_configs: Dict[str, Any]
    pipeline_type: str
    execution_mode: str = Field(..., regex='^(sequential|parallel|distributed)$')
    max_retries: int = Field(3, ge=0, le=10)
    retry_strategy: str = Field(..., regex='^(exponential|linear|fixed)$')


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
class RecommendationStagingRequestSchema(BaseStagingSchema):
    type: str
    context: Dict[str, Any]
    constraints: Dict[str, Any] = Field(default_factory=dict)
    priority: str = Field(..., regex='^(low|medium|high|critical)$')
    target_metrics: List[str]


class RecommendationStagingResponseSchema(BaseStagingSchema):
    recommendations: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    impact_analysis: Dict[str, Any]
    priority_ranking: Dict[str, Any]


# Report Schemas
class ReportStagingRequestSchema(BaseStagingSchema):
    report_type: str
    format: str = Field(..., regex='^(pdf|excel|csv|json)$')
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
    category: str = Field(..., regex='^(user|system|security|notifications|appearance|integrations)$')
    settings: Dict[str, Any]
    overrides: Dict[str, Any] = Field(default_factory=dict)
    scope: str = Field(..., regex='^(global|user|pipeline)$')


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
    severity: str = Field(..., regex='^(critical|major|minor)$')
    message: Optional[str]


class ValidationRequestSchema(BaseStagingSchema):
    target_type: str
    rules: List[ValidationRuleSchema]
    validation_context: Dict[str, Any] = Field(default_factory=dict)
    threshold: float = Field(..., ge=0.0, le=1.0)


class ValidationResponseSchema(BaseStagingSchema):
    validation_id: UUID
    passed: bool
    results: List[Dict[str, Any]]
    validation_time: datetime
    metrics: Dict[str, Any]

    @root_validator
    def validate_results(cls, values):
        if not values.get('passed') and not values.get('results'):
            raise ValueError('Failed validation requires detailed results')
        return values