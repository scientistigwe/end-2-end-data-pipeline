# backend/core/messaging/event_types.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
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

    # Recommendation Operations
    RECOMMENDATION_START = "recommendation.start"  # Start recommendation generation
    RECOMMENDATION_CONTEXT = "recommendation.context"  # Context analysis complete
    RECOMMENDATION_CANDIDATES = "recommendation.candidates"  # Candidate generation complete
    RECOMMENDATION_FILTERED = "recommendation.filtered"  # Filtering complete
    RECOMMENDATION_RANKED = "recommendation.ranked"  # Ranking complete
    RECOMMENDATION_MERGED = "recommendation.merged"  # Results merged/aggregated
    RECOMMENDATION_COMPLETE = "recommendation.complete"  # Process completed
    RECOMMENDATION_ERROR = "recommendation.error"  # Error in process
    RECOMMENDATION_UPDATE = "recommendation.update"  # Status/progress update
    RECOMMENDATION_REQUEST = "recommendation.request"
    RECOMMENDATION_RANKING = "recommendation.ranking"
    RECOMMENDATION_FINAL = "recommendation.final"

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
    REPORT_START = "report.start"
    REPORT_SECTION_COMPLETE = "report.section.complete"
    REPORT_VISUALIZATION_COMPLETE = "report.visualization.complete"
    REPORT_VALIDATION_COMPLETE = "report.validation.complete"
    REPORT_STATUS_UPDATE = "report.status.update"
    REPORT_GENERATING = "report.generating"
    REPORT_READY_FOR_REVIEW = "report.ready_for_review"
    REPORT_REVIEWED = "report.reviewed"
    REPORT_COMPLETE = "report.complete"
    REPORT_ERROR = "report.error"
    REPORT_ARCHIVED = "report.archived"

    # Staging Operations
    STAGING_DATA_RECEIVED = "staging.data.received"  # Initial data receipt
    STAGING_DATA_STORED = "staging.data.stored"  # Data storage complete
    STAGING_DATA_VALIDATED = "staging.data.validated"  # Data validation complete
    STAGING_DATA_REJECTED = "staging.data.rejected"  # Data validation failed

    # Staging Access
    DATA_ACCESS_REQUEST = "staging.access.request"  # Component requesting data
    STAGING_ACCESS_GRANTED = "staging.access.granted"  # Access permission granted
    STAGING_ACCESS_DENIED = "staging.access.denied"  # Access permission denied

    # Staging Versioning
    STAGING_VERSION_CREATED = "staging.version.created"  # New version created
    STAGING_VERSION_UPDATED = "staging.version.updated"  # Version updated
    STAGING_VERSION_ARCHIVED = "staging.version.archived"  # Version archived

    # Staging Component Outputs
    COMPONENT_OUTPUT_READY = "staging.output.ready"  # Component output ready
    STAGING_OUTPUT_STORED = "staging.output.stored"  # Output storage complete
    STAGING_OUTPUT_ERROR = "staging.output.error"  # Output storage failed

    # Staging Maintenance
    STAGING_CLEANUP_START = "staging.cleanup.start"  # Cleanup process started
    STAGING_CLEANUP_COMPLETE = "staging.cleanup.complete"  # Cleanup process complete
    STAGING_SPACE_WARNING = "staging.space.warning"  # Storage space warning

    # Staging Recovery
    STAGING_RECOVERY_START = "staging.recovery.start"  # Recovery process started
    STAGING_RECOVERY_COMPLETE = "staging.recovery.complete"  # Recovery complete
    STAGING_RECOVERY_FAILED = "staging.recovery.failed"  # Recovery failed

    # Staging Status
    STAGING_STATUS_UPDATE = "staging.status.update"  # General status update
    STAGING_METRICS_UPDATE = "staging.metrics.update"  # Storage metrics update

    # Staging Pipeline Integration
    STAGING_PIPELINE_START = "staging.pipeline.start"  # Pipeline processing start
    STAGING_PIPELINE_UPDATE = "staging.pipeline.update"  # Pipeline status update
    STAGING_PIPELINE_COMPLETE = "staging.pipeline.complete"  # Pipeline complete

    # Staging Component Communication
    STAGING_COMPONENT_REQUEST = "staging.component.request"  # Component data request
    STAGING_COMPONENT_RESPONSE = "staging.component.response"  # Response to component


class ComponentType(Enum):
    """Enhanced system component types"""
    # Core Components
    HANDLER = "handler"
    MANAGER = "manager"
    MODULE = "module"

    # Department Managers (subclass of MANAGER)
    QUALITY_MANAGER = "quality.manager"
    INSIGHT_MANAGER = "insight.manager"
    ANALYTICS_MANAGER = "analytics.manager"
    DECISION_MANAGER = "decision.manager"
    RECOMMENDATION_MANAGER = "recommendation.manager"
    REPORT_MANAGER = "report.manager"
    MONITORING_MANAGER = "monitoring.manager"

    # Department Handlers (subclass of HANDLER)
    QUALITY_HANDLER = "quality.handler"
    INSIGHT_HANDLER = "insight.handler"
    ANALYTICS_HANDLER = "analytics.handler"
    DECISION_HANDLER = "decision.handler"
    RECOMMENDATION_HANDLER = "recommendation.handler"
    REPORT_HANDLER = "report.handler"

    # Service Components
    FILE_SERVICE = "service.file"
    API_SERVICE = "service.api"
    DB_SERVICE = "service.database"
    STREAM_SERVICE = "service.stream"
    CLOUD_SERVICE = "service.cloud"

    @property
    def department(self) -> str:
        """Get department name"""
        return self.value.split('.')[0]

    @property
    def role(self) -> str:
        """Get role within department"""
        return self.value.split('.')[1]

    @property
    def is_manager(self) -> bool:
        """Check if component is a manager"""
        return self.role == "manager"

    @property
    def is_handler(self) -> bool:
        """Check if component is a handler"""
        return self.role == "handler"

    @property
    def is_service(self) -> bool:
        """Check if component is a service"""
        return self.department == "service"


@dataclass
class ModuleIdentifier:
    """Component identifier for precise message routing"""
    component_name: str
    component_type: ComponentType
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Added fields for organizational structure
    department: Optional[str] = None
    role: Optional[str] = None

    @classmethod
    def create_service_identifier(cls, service_type: ComponentType, name: str) -> 'ModuleIdentifier':
        """Create identifier for service desk components"""
        return cls(
            component_name=name,
            component_type=service_type,
            department="service",
            role=service_type.role
        )

    @classmethod
    def create_manager_identifier(cls, manager_type: ComponentType, name: str) -> 'ModuleIdentifier':
        """Create identifier for department managers"""
        return cls(
            component_name=name,
            component_type=manager_type,
            department=manager_type.department,
            role="manager"
        )

    @classmethod
    def create_handler_identifier(cls, handler_type: ComponentType, name: str) -> 'ModuleIdentifier':
        """Create identifier for department handlers"""
        return cls(
            component_name=name,
            component_type=handler_type,
            department=handler_type.department,
            role="handler"
        )

    def get_routing_key(self) -> str:
        """Get standardized message routing key"""
        return f"{self.department}.{self.role}.{self.component_name}.{self.instance_id}"

    def get_subscription_pattern(self) -> str:
        """Get subscription pattern for component"""
        return f"{self.department}.{self.role}.{self.component_name}.*"

    def matches_pattern(self, pattern: str) -> bool:
        """Check if identifier matches routing pattern"""
        if pattern == "#":  # Wildcard pattern
            return True

        pattern_parts = pattern.split(".")
        key_parts = self.get_routing_key().split(".")

        if len(pattern_parts) != len(key_parts):
            return False

        return all(
            p == "*" or p == k
            for p, k in zip(pattern_parts, key_parts)
        )


class ReportSectionType(Enum):
    """Types of report sections that can be generated"""
    OVERVIEW = "overview"
    QUALITY_METRICS = "quality_metrics"
    ISSUES = "issues"
    RECOMMENDATIONS = "recommendations"
    INSIGHTS = "insights"
    ANALYTICS_RESULTS = "analytics_results"
    VISUALIZATIONS = "visualizations"
    SUMMARY = "summary"
    CUSTOM = "custom"
    REPORT = "report"
    MODEL = "model"
    DATA = "data"
    METRICS = "metrics"


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
    RECOMMENDATION = "recommendation"
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
    ARCHIVED = "archived"



@dataclass
class MessageMetadata:
    """Enhanced message metadata with routing information"""
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

    # Added routing fields
    chain_id: Optional[str] = None  # Identifies processing chain
    department: Optional[str] = None  # Department handling the message
    workflow_step: Optional[int] = None  # Step in the workflow
    is_broadcast: bool = False  # Indicates if message is for all components


@dataclass
class BaseContext:
    """Enhanced base context with staging information"""
    pipeline_id: str
    stage: ProcessingStage
    status: ProcessingStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Added staging references
    staging_reference: Optional[str] = None  # Reference to staged data
    staging_location: Optional[str] = None  # Location in staging area
    input_refs: List[str] = field(default_factory=list)  # Input data references
    output_refs: List[str] = field(default_factory=list)  # Output data references


@dataclass
class ProcessingMessage:
    """Core message structure with precise routing"""
    message_type: MessageType
    content: Dict[str, Any]
    metadata: MessageMetadata = field(default_factory=MessageMetadata)
    context: Optional[BaseContext] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Add source and target identifiers
    source_identifier: Optional[ModuleIdentifier] = None
    target_identifier: Optional[ModuleIdentifier] = None

    def create_response(
        self,
        message_type: MessageType,
        content: Dict[str, Any]
    ) -> 'ProcessingMessage':
        """Create a response message with proper routing"""
        return ProcessingMessage(
            message_type=message_type,
            content=content,
            source_identifier=self.target_identifier,
            target_identifier=self.source_identifier,
            metadata=MessageMetadata(
                correlation_id=self.metadata.correlation_id,
                source_component=self.metadata.target_component,
                target_component=self.metadata.source_component,
                domain_type=self.metadata.domain_type,
                processing_stage=self.metadata.processing_stage,
                chain_id=self.metadata.chain_id
            ),
            context=self.context
        )

    def create_forward(
        self,
        target_identifier: ModuleIdentifier,
        message_type: Optional[MessageType] = None
    ) -> 'ProcessingMessage':
        """Forward message to another component"""
        return ProcessingMessage(
            message_type=message_type or self.message_type,
            content=self.content,
            source_identifier=self.target_identifier,
            target_identifier=target_identifier,
            metadata=MessageMetadata(
                correlation_id=self.metadata.correlation_id,
                source_component=self.target_identifier.component_name if self.target_identifier else "unknown",
                target_component=target_identifier.component_name,
                domain_type=self.metadata.domain_type,
                processing_stage=self.metadata.processing_stage,
                chain_id=self.metadata.chain_id
            ),
            context=self.context
        )

    def create_broadcast(
            self,
            message_type: MessageType,
            content: Dict[str, Any]
    ) -> 'ProcessingMessage':
        """Create a broadcast message to all departments"""
        metadata = MessageMetadata(
            correlation_id=self.metadata.correlation_id,
            source_component=self.metadata.source_component,
            target_component="broadcast",
            is_broadcast=True,
            chain_id=self.metadata.chain_id
        )
        return ProcessingMessage(
            message_type=message_type,
            content=content,
            metadata=metadata,
            context=self.context
        )


@dataclass
class QualityContext(BaseContext):
    """Quality analysis context"""
    source_type: str = field(default="data_quality")
    column_types: Dict[str, str] = field(default_factory=dict)
    detected_issues: List[Dict[str, Any]] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=lambda: {"overall": 0.0})
    suggested_actions: List[str] = field(default_factory=list)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    resolution_status: Dict[str, str] = field(default_factory=lambda: {"status": "pending"})
    requires_decision: bool = False


@dataclass
class InsightContext(BaseContext):
    """Insight generation context"""
    analysis_type: str = field(default="general_analysis")
    target_metrics: List[str] = field(default_factory=list)
    confidence_threshold: float = 0.5
    business_rules: Dict[str, Any] = field(default_factory=dict)
    validation_criteria: List[str] = field(default_factory=list)
    data_segments: List[str] = field(default_factory=list)
    insight_categories: List[str] = field(default_factory=list)
    priority_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyticsContext(BaseContext):
    """Advanced analytics context"""
    model_type: str = field(default="default_model")
    features: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    training_config: Dict[str, Any] = field(default_factory=lambda: {"method": "default"})
    evaluation_metrics: List[str] = field(default_factory=list)
    model_constraints: Dict[str, Any] = field(default_factory=dict)
    performance_requirements: Dict[str, float] = field(default_factory=lambda: {"accuracy": 0.0})
    data_dependencies: List[str] = field(default_factory=list)


@dataclass
class DecisionContext(BaseContext):
    """Decision processing context"""
    source_component: str = field(default="default_decision_maker")
    decision_type: str = field(default="standard_decision")
    options: List[Dict[str, Any]] = field(default_factory=list)
    impacts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    required_validations: List[str] = field(default_factory=list)
    timeout_minutes: Optional[int] = None
    requires_confirmation: bool = True

@dataclass
class RecommendationContext(BaseContext):
    """Recommendation processing context"""
    # Core properties
    source_component: str = field(default="recommendation_system")
    request_type: str = field(default="general_recommendation")
    target_type: str = field(default="default_target")

    # Engine configuration
    enabled_engines: List[str] = field(default_factory=list)
    engine_weights: Dict[str, float] = field(default_factory=dict)

    # Processing rules
    candidate_limits: Dict[str, int] = field(default_factory=lambda: {"max_candidates": 10})
    filtering_rules: Dict[str, Any] = field(default_factory=dict)
    ranking_criteria: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    diversity_settings: Dict[str, Any] = field(default_factory=lambda: {"enabled": False})

    # Contextual information
    user_context: Dict[str, Any] = field(default_factory=dict)
    temporal_context: Dict[str, Any] = field(default_factory=dict)
    business_context: Dict[str, Any] = field(default_factory=dict)

    # Performance settings
    min_confidence: float = 0.5
    max_recommendations: int = 10
    timeout_seconds: Optional[int] = None

@dataclass
class PipelineContext(BaseContext):
    """Pipeline management context"""
    current_stage: str = field(default="initial")
    stage_sequence: List[str] = field(default_factory=list)
    stage_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    stage_configs: Dict[str, Any] = field(default_factory=dict)
    component_states: Dict[str, str] = field(default_factory=dict)
    progress: Dict[str, float] = field(default_factory=lambda: {"overall": 0.0})
    error_handling_rules: Dict[str, Any] = field(default_factory=lambda: {"default_action": "log"})


@dataclass
class ReportContext(BaseContext):
    """Enhanced Report generation context"""
    # Basic report information
    report_type: str = field(default="default_report")
    report_id: uuid.UUID = field(default_factory=uuid.uuid4)

    # Content configuration
    templates: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    sections: List[ReportSectionType] = field(default_factory=lambda: [
        ReportSectionType.OVERVIEW,
        ReportSectionType.SUMMARY
    ])

    # Formatting and presentation
    formatting_rules: Dict[str, Any] = field(default_factory=lambda: {
        "theme": "default",
        "font": "Arial",
        "font_size": 12
    })
    output_formats: List[str] = field(default_factory=lambda: ["pdf", "html"])

    # Component integration
    components_included: List[str] = field(default_factory=list)
    aggregation_rules: Dict[str, Any] = field(default_factory=dict)

    # Data references
    quality_data_ref: Optional[str] = None
    insight_data_ref: Optional[str] = None
    analytics_data_ref: Optional[str] = None

    # Visualization and formatting
    visualization_config: Dict[str, Any] = field(default_factory=lambda: {
        "color_scheme": "default",
        "chart_type": "auto"
    })
    style_config: Dict[str, Any] = field(default_factory=lambda: {
        "layout": "standard",
        "theme": "light"
    })

    # Distribution and access
    distribution_rules: Optional[Dict[str, Any]] = None
    access_control: Dict[str, Any] = field(default_factory=lambda: {
        "default_access": "restricted"
    })

    # User customization
    user_preferences: Dict[str, Any] = field(default_factory=dict)

    # Processing metadata
    section_status: Dict[str, str] = field(default_factory=lambda: {
        "overall_status": "not_started"
    })
    report_metadata: Dict[str, Any] = field(default_factory=lambda: {
        "version": "1.0",
        "generated_at": datetime.now().isoformat()
    })


@dataclass
class ReportMessage(ProcessingMessage):
    """Specialized message type for report-related communication"""
    report_context: Optional[ReportContext] = None
    section_id: Optional[str] = None
    visualization_id: Optional[str] = None
    processing_phase: Optional[str] = None

    def create_section_complete_message(self, section_id: str, section_data: Dict[str, Any]) -> 'ReportMessage':
        """Create message for section completion"""
        return ReportMessage(
            message_type=MessageType.REPORT_SECTION_COMPLETE,
            content={
                'section_id': section_id,
                'section_data': section_data,
                'timestamp': datetime.now().isoformat()
            },
            metadata=self.metadata,
            report_context=self.report_context,
            section_id=section_id
        )

    def create_visualization_complete_message(self, viz_id: str, viz_data: Dict[str, Any]) -> 'ReportMessage':
        """Create message for visualization completion"""
        return ReportMessage(
            message_type=MessageType.REPORT_VISUALIZATION_COMPLETE,
            content={
                'visualization_id': viz_id,
                'visualization_data': viz_data,
                'timestamp': datetime.now().isoformat()
            },
            metadata=self.metadata,
            report_context=self.report_context,
            visualization_id=viz_id
        )

    def create_status_update_message(self, status: str, progress: float) -> 'ReportMessage':
        """Create message for status update"""
        return ReportMessage(
            message_type=MessageType.REPORT_STATUS_UPDATE,
            content={
                'status': status,
                'progress': progress,
                'timestamp': datetime.now().isoformat()
            },
            metadata=self.metadata,
            report_context=self.report_context,
            processing_phase=status
        )


# Add this to your backend/core/messaging/event_types.py

@dataclass
class ProcessingContext:
    """
    Comprehensive context for processing operations
    Tracks detailed information about a processing lifecycle
    """
    pipeline_id: str
    stage: ProcessingStage
    status: ProcessingStatus
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timing and tracking
    started_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Processing details
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_context_id: Optional[str] = None

    # Error and performance tracking
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

    # Execution tracking
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    control_points: List[str] = field(default_factory=list)

    def add_performance_metric(self, metric_name: str, value: Any) -> None:
        """
        Add a performance metric to the context

        Args:
            metric_name (str): Name of the performance metric
            value (Any): Value of the metric
        """
        self.performance_metrics[metric_name] = value

    def add_warning(self, warning: str) -> None:
        """
        Add a warning to the context

        Args:
            warning (str): Warning message to add
        """
        self.warnings.append(warning)

    def update_status(self, new_status: ProcessingStatus) -> None:
        """
        Update the processing status and timestamp

        Args:
            new_status (ProcessingStatus): New status to set
        """
        self.status = new_status
        self.updated_at = datetime.now()

        if new_status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]:
            self.completed_at = datetime.now()

    def record_step(self, step_details: Dict[str, Any]) -> None:
        """
        Record a step in the processing history

        Args:
            step_details (Dict[str, Any]): Details of the processing step
        """
        step_details['timestamp'] = datetime.now().isoformat()
        self.processing_history.append(step_details)

    def add_control_point(self, control_point_id: str) -> None:
        """
        Add a control point to the context

        Args:
            control_point_id (str): Identifier of the control point
        """
        self.control_points.append(control_point_id)

    @property
    def duration(self) -> Optional[timedelta]:
        """
        Calculate total processing duration

        Returns:
            Optional[timedelta]: Duration of processing if completed
        """
        if self.completed_at:
            return self.completed_at - self.started_at
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to a dictionary representation

        Returns:
            Dict[str, Any]: Dictionary representation of the context
        """
        return {
            'pipeline_id': self.pipeline_id,
            'stage': self.stage.value,
            'status': self.status.value,
            'metadata': self.metadata,
            'started_at': self.started_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'request_id': self.request_id,
            'parent_context_id': self.parent_context_id,
            'error': self.error,
            'warnings': self.warnings,
            'performance_metrics': self.performance_metrics,
            'processing_history': self.processing_history,
            'control_points': self.control_points
        }
