# backend/core/messaging/event_types.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class MessageType(Enum):
    """Enhanced message types with clear component separation"""

    # Data Reception & Validation
    DATA_RECEIVED = "data.received"
    DATA_VALIDATED = "data.validated"
    DATA_REJECTED = "data.rejected"
    DATA_TRANSFORMATION = "data.transformation"
    DATA_STORAGE = "data.storage"

    # Quality Analysis
    QUALITY_START = "quality.start"
    QUALITY_CONTEXT_ANALYZED = "quality.context.analyzed"
    QUALITY_ISSUES_DETECTED = "quality.issues.detected"
    QUALITY_RESOLUTION_SUGGESTED = "quality.resolution.suggested"
    QUALITY_RESOLUTION_APPLIED = "quality.resolution.applied"
    QUALITY_APPROVED = "quality.approved"
    QUALITY_REJECTED = "quality.rejected"
    QUALITY_UPDATE = "quality.update"

    # Insight Generation
    INSIGHT_START = "insight.start"
    INSIGHT_CONTEXT_ANALYZED = "insight.context.analyzed"
    INSIGHT_GENERATED = "insight.generated"
    INSIGHT_VERIFIED = "insight.verified"
    INSIGHT_APPROVED = "insight.approved"
    INSIGHT_REJECTED = "insight.rejected"
    INSIGHT_UPDATE = "insight.update"

    # Advanced Analytics
    ANALYTICS_START = "analytics.start"
    ANALYTICS_CONTEXT_ANALYZED = "analytics.context.analyzed"
    ANALYTICS_MODEL_SELECTED = "analytics.model.selected"
    ANALYTICS_PROCESSING = "analytics.processing"
    ANALYTICS_COMPLETE = "analytics.complete"
    ANALYTICS_ERROR = "analytics.error"
    ANALYTICS_UPDATE = "analytics.update"

    # Decision Operations
    DECISION_REQUEST = "decision.request"
    DECISION_OPTIONS = "decision.options"
    DECISION_SUBMIT = "decision.submit"
    DECISION_VALIDATE = "decision.validate"
    DECISION_IMPACT = "decision.impact"
    DECISION_UPDATE = "decision.update"
    DECISION_COMPLETE = "decision.complete"
    DECISION_ERROR = "decision.error"
    DECISION_TIMEOUT = "decision.timeout"

    # Pipeline Control
    PIPELINE_START = "pipeline.start"
    PIPELINE_STAGE_START = "pipeline.stage.start"
    PIPELINE_STAGE_COMPLETE = "pipeline.stage.complete"
    PIPELINE_PROGRESS = "pipeline.progress"
    PIPELINE_PAUSE = "pipeline.pause"
    PIPELINE_RESUME = "pipeline.resume"
    PIPELINE_COMPLETE = "pipeline.complete"
    PIPELINE_ERROR = "pipeline.error"

    # Component Communication
    COMPONENT_INIT = "component.init"
    COMPONENT_UPDATE = "component.update"
    COMPONENT_ERROR = "component.error"
    COMPONENT_SYNC = "component.sync"

    # Report Generation
    REPORT_REQUEST = "report.request"
    REPORT_GENERATING = "report.generating"
    REPORT_COMPLETE = "report.complete"
    REPORT_ERROR = "report.error"


class ProcessingStage(Enum):
    """Pipeline processing stages"""
    RECEPTION = "reception"
    VALIDATION = "validation"
    QUALITY_CHECK = "quality_check"
    CONTEXT_ANALYSIS = "context_analysis"
    INSIGHT_GENERATION = "insight_generation"
    ADVANCED_ANALYTICS = "advanced_analytics"
    DECISION_MAKING = "decision_making"
    REPORT_GENERATION = "report_generation"
    USER_REVIEW = "user_review"
    COMPLETION = "completion"


class ProcessingStatus(Enum):
    """Processing status states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_DECISION = "awaiting_decision"
    DECISION_TIMEOUT = "decision_timeout"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MessageMetadata:
    """Enhanced message metadata"""
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_component: str = field(default="unknown")
    target_component: str = field(default="unknown")
    priority: int = 1
    retry_count: int = 0
    domain_type: Optional[str] = None
    processing_stage: Optional[ProcessingStage] = None
    requires_response: bool = False
    timeout_seconds: Optional[int] = None


@dataclass
class BaseContext:
    """Base context for all processing contexts"""
    pipeline_id: str
    stage: ProcessingStage
    status: ProcessingStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class QualityContext(BaseContext):
    """Quality analysis context"""
    source_type: str
    column_types: Dict[str, str]
    detected_issues: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    suggested_actions: List[str]
    validation_rules: Dict[str, Any]
    resolution_status: Dict[str, str]
    requires_decision: bool = False


@dataclass
class InsightContext(BaseContext):
    """Insight generation context"""
    analysis_type: str
    target_metrics: List[str]
    confidence_threshold: float
    business_rules: Dict[str, Any]
    validation_criteria: List[str]
    data_segments: List[str]
    insight_categories: List[str]
    priority_rules: Dict[str, Any]


@dataclass
class AnalyticsContext(BaseContext):
    """Advanced analytics context"""
    model_type: str
    features: List[str]
    parameters: Dict[str, Any]
    training_config: Dict[str, Any]
    evaluation_metrics: List[str]
    model_constraints: Dict[str, Any]
    performance_requirements: Dict[str, float]
    data_dependencies: List[str]


@dataclass
class DecisionContext(BaseContext):
    """Decision processing context"""
    source_component: str
    decision_type: str
    options: List[Dict[str, Any]]
    impacts: Dict[str, Dict[str, Any]]
    constraints: Dict[str, Any]
    required_validations: List[str]
    timeout_minutes: Optional[int] = None
    requires_confirmation: bool = True


@dataclass
class ReportContext(BaseContext):
    """Report generation context"""
    report_type: str
    templates: List[str]
    data_sources: List[str]
    formatting_rules: Dict[str, Any]
    components_included: List[str]
    aggregation_rules: Dict[str, Any]
    output_formats: List[str]
    distribution_rules: Optional[Dict[str, Any]] = None


@dataclass
class PipelineContext(BaseContext):
    """Pipeline management context"""
    stage_sequence: List[str]
    current_stage: str
    stage_dependencies: Dict[str, List[str]]
    stage_configs: Dict[str, Any]
    component_states: Dict[str, str]
    progress: Dict[str, float]
    error_handling_rules: Dict[str, Any]


@dataclass
class ProcessingMessage:
    """Core message structure"""
    message_type: MessageType
    content: Dict[str, Any]
    metadata: MessageMetadata = field(default_factory=MessageMetadata)
    context: Optional[BaseContext] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def create_response(
            self,
            message_type: MessageType,
            content: Dict[str, Any]
    ) -> 'ProcessingMessage':
        """Create a response message"""
        return ProcessingMessage(
            message_type=message_type,
            content=content,
            metadata=MessageMetadata(
                correlation_id=self.metadata.correlation_id,
                source_component=self.metadata.target_component,
                target_component=self.metadata.source_component,
                domain_type=self.metadata.domain_type,
                processing_stage=self.metadata.processing_stage
            ),
            context=self.context
        )