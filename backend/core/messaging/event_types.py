# backend/core/messaging/event_types.py

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid
import re
from typing import Dict, Any, Optional, Set, List
from datetime import datetime
from pathlib import Path

class ProcessingStage(Enum):
    """Pipeline processing stages"""
    RECEPTION = "reception"
    QUALITY_CHECK = "quality_check"
    CONTEXT_ANALYSIS = "context_analysis"
    INSIGHT_GENERATION = "insight_generation"
    ADVANCED_ANALYTICS = "advanced_analytics"
    DECISION_MAKING = "decision_making"
    REPORT_GENERATION = "report_generation"
    RECOMMENDATION = "recommendation"
    USER_REVIEW = "user_review"
    COMPLETION = "completion"
    INITIAL_VALIDATION = "initial_validation"
    DATA_EXTRACTION = "data_extraction"
    DATA_VALIDATION = "data_validation"
    PROCESSING = "processing"
    COMPLETED = "completed"
    VALIDATION = "validation"


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
class BaseContext:
    """Base context for all processing types"""
    pipeline_id: str
    stage: ProcessingStage
    status: ProcessingStatus
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    completed_at: Optional[datetime] = None

    # Resource Management
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    allocated_resources: Dict[str, Any] = field(default_factory=dict)

    # Processing Configuration
    processing_mode: str = "batch"  # or "streaming"
    timeout_seconds: Optional[int] = None
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Added staging references
    staging_reference: Optional[str] = None  # Reference to staged data
    staging_location: Optional[str] = None  # Location in staging area
    input_refs: List[str] = field(default_factory=list)  # Input data references
    output_refs: List[str] = field(default_factory=list)  # Output data references

    # Monitoring
    metrics: Dict[str, Any] = field(default_factory=dict)
    health_status: Dict[str, str] = field(default_factory=dict)
    performance_stats: Dict[str, float] = field(default_factory=dict)

    # Error Handling
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    retry_count: Dict[str, int] = field(default_factory=dict)


@dataclass
class ModelContext:
    """Context for model operations"""
    model_id: str
    model_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    features: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    validation_history: List[Dict[str, Any]] = field(default_factory=list)
    training_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ManagerMetrics:
    """Track manager performance metrics"""
    messages_processed: int = 0
    errors_encountered: int = 0
    average_processing_time: float = 0.0
    last_activity: datetime = field(default_factory=datetime.now)
    active_processes: int = 0


class ManagerState(Enum):
    """Manager operational states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PROCESSING = "processing"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class ManagerContext(BaseContext):
    """Base context for manager operations"""
    component_name: str = None
    domain_type: str = None
    state: ManagerState = field(default_factory=lambda: ManagerState.INITIALIZING)
    metrics: ManagerMetrics = field(default_factory=ManagerMetrics)
    handlers: Dict[str, str] = field(default_factory=dict)


class AnalyticsState(Enum):
    """Analytics processing states"""
    INITIALIZING = "initializing"
    DATA_PREPARATION = "data_preparation"
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_SELECTION = "model_selection"
    MODEL_TRAINING = "model_training"
    MODEL_EVALUATION = "model_evaluation"
    VISUALIZATION = "visualization"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AnalyticsMetrics:
    """Comprehensive metrics for analytics processing"""
    data_quality_score: float = 0.0
    feature_importance: Dict[str, float] = field(default_factory=dict)
    model_performance: Dict[str, float] = field(default_factory=dict)
    prediction_confidence: Dict[str, float] = field(default_factory=dict)
    processing_time: Dict[str, float] = field(default_factory=dict)
    resource_utilization: Dict[str, float] = field(default_factory=dict)
    validation_scores: Dict[str, float] = field(default_factory=dict)
    error_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class AnalyticsContext(BaseContext):
    """Enhanced analytics processing context"""
    # Core tracking
    pipeline_id: str
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: AnalyticsState = field(default_factory=lambda: AnalyticsState.INITIALIZING)
    status: ProcessingStatus = field(default_factory=lambda: ProcessingStatus.PENDING)

    # Data Management
    data_schema: Dict[str, Any] = field(default_factory=dict)
    data_quality_metrics: Dict[str, float] = field(default_factory=dict)
    feature_metadata: Dict[str, Any] = field(default_factory=dict)

    # Model Management
    model_type: Optional[str] = None
    model_parameters: Dict[str, Any] = field(default_factory=dict)
    model_metrics: Dict[str, float] = field(default_factory=dict)
    model_artifacts: Dict[str, str] = field(default_factory=dict)

    # Training Configuration
    training_config: Dict[str, Any] = field(default_factory=dict)
    validation_config: Dict[str, Any] = field(default_factory=dict)
    hyperparameters: Dict[str, Any] = field(default_factory=dict)

    # Performance Tracking
    training_metrics: Dict[str, float] = field(default_factory=dict)
    validation_metrics: Dict[str, float] = field(default_factory=dict)
    inference_metrics: Dict[str, float] = field(default_factory=dict)

    # MLOps
    model_version: Optional[str] = None
    model_lineage: Dict[str, Any] = field(default_factory=dict)
    experiment_tracking: Dict[str, Any] = field(default_factory=dict)
    deployment_config: Dict[str, Any] = field(default_factory=dict)

    # Configuration
    data_config: Dict[str, Any] = field(default_factory=dict)
    model_config: Dict[str, Any] = field(default_factory=dict)
    feature_config: Dict[str, Any] = field(default_factory=dict)
    visualization_config: Dict[str, Any] = field(default_factory=dict)

    # Results tracking
    phase_results: Dict[str, Any] = field(default_factory=dict)
    model_metadata: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)

    # Error handling
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def update_state(self, new_state: AnalyticsState) -> None:
        """Update processing state"""
        self.state = new_state
        self.updated_at = datetime.now()

        if new_state == AnalyticsState.COMPLETED:
            self.completed_at = datetime.now()


from enum import Enum


class MessageType(Enum):
    """
    Comprehensive Message Type System for the Analyst PA

    Design Principles:
    - Strict domain.action.state structure
    - Consistent and logical messaging
    - Supports complex, adaptive data processing workflows
    - Provides clear semantic meaning for each message type
    """
    # Global System Communication
    GLOBAL_ERROR_NOTIFY = "global.error.notify"
    GLOBAL_STATUS_REQUEST = "global.status.request"
    GLOBAL_STATUS_RESPONSE = "global.status.response"
    GLOBAL_HEALTH_CHECK = "global.health.check"
    GLOBAL_SYSTEM_BROADCAST = "global.system.broadcast"

    # System Lifecycle Management
    SYSTEM_INITIALIZE_REQUEST = "system.initialize.request"
    SYSTEM_INITIALIZE_COMPLETE = "system.initialize.complete"
    SYSTEM_SHUTDOWN_REQUEST = "system.shutdown.request"
    SYSTEM_SHUTDOWN_COMPLETE = "system.shutdown.complete"
    SYSTEM_RESTART_REQUEST = "system.restart.request"
    SYSTEM_CONFIG_UPDATE_REQUEST = "system.config.update.request"
    SYSTEM_CONFIG_UPDATE_COMPLETE = "system.config.update.complete"

    # Control Point Communication
    CONTROL_POINT_CREATE_REQUEST = "control.point.create.request"
    CONTROL_POINT_CREATE_COMPLETE = "control.point.create.complete"
    CONTROL_POINT_UPDATE_REQUEST = "control.point.update.request"
    CONTROL_POINT_UPDATE_COMPLETE = "control.point.update.complete"
    CONTROL_POINT_DECISION_REQUEST = "control.point.decision.request"
    CONTROL_POINT_DECISION_SUBMIT = "control.point.decision.submit"

    # Data Lifecycle Management
    DATA_RECEIVE_REQUEST = "data.receive.request"
    DATA_RECEIVE_COMPLETE = "data.receive.complete"
    DATA_VALIDATE_REQUEST = "data.validate.request"
    DATA_VALIDATE_COMPLETE = "data.validate.complete"
    DATA_VALIDATE_REJECT = "data.validate.reject"
    DATA_TRANSFORM_REQUEST = "data.transform.request"
    DATA_TRANSFORM_COMPLETE = "data.transform.complete"
    DATA_STORE_REQUEST = "data.store.request"
    DATA_STORE_COMPLETE = "data.store.complete"
    DATA_ENRICH_REQUEST = "data.enrich.request"
    DATA_ENRICH_COMPLETE = "data.enrich.complete"
    DATA_PROFILE_REQUEST = "data.profile.request"
    DATA_PROFILE_COMPLETE = "data.profile.complete"
    DATA_LINEAGE_TRACK = "data.lineage.track"

    # Workflow Management
    WORKFLOW_CREATE_REQUEST = "workflow.create.request"
    WORKFLOW_CREATE_COMPLETE = "workflow.create.complete"
    WORKFLOW_START_REQUEST = "workflow.start.request"
    WORKFLOW_START_COMPLETE = "workflow.start.complete"
    WORKFLOW_PAUSE_REQUEST = "workflow.pause.request"
    WORKFLOW_PAUSE_COMPLETE = "workflow.pause.complete"
    WORKFLOW_RESUME_REQUEST = "workflow.resume.request"
    WORKFLOW_RESUME_COMPLETE = "workflow.resume.complete"
    WORKFLOW_TERMINATE_REQUEST = "workflow.terminate.request"
    WORKFLOW_TERMINATE_COMPLETE = "workflow.terminate.complete"
    WORKFLOW_DEPENDENCY_CHECK = "workflow.dependency.check"
    WORKFLOW_ROLLBACK_REQUEST = "workflow.rollback.request"
    WORKFLOW_ROLLBACK_COMPLETE = "workflow.rollback.complete"

    #............................................Quality Types..........................................................
    # Quality Analysis
    QUALITY_ANALYZE_REQUEST = "quality.analyze.request"
    QUALITY_ANALYZE_COMPLETE = "quality.analyze.complete"

    # Quality Issue Detection
    QUALITY_ISSUE_DETECT_REQUEST = "quality.issue.detect.request"
    QUALITY_ISSUE_DETECT_COMPLETE = "quality.issue.detect.complete"
    QUALITY_ISSUE_DETECTED = "quality.issue.detect.notify"

    # Quality Issue Resolution
    QUALITY_ISSUE_RESOLVE_REQUEST = "quality.issue.resolve.request"
    QUALITY_ISSUE_RESOLVE_SUGGEST = "quality.issue.resolve.suggest"
    QUALITY_ISSUE_RESOLVE_COMPLETE = "quality.issue.resolve.complete"

    # Quality Validation
    QUALITY_VALIDATE_REQUEST = "quality.validate.request"
    QUALITY_VALIDATE_COMPLETE = "quality.validate.complete"
    QUALITY_VALIDATE_APPROVE = "quality.validate.approve"
    QUALITY_VALIDATE_REJECT = "quality.validate.reject"

    # Quality Process Management
    QUALITY_PROCESS_START_REQUEST = "quality.process.start.request"
    QUALITY_PROCESS_STATE_UPDATE = "quality.process.state.update"
    QUALITY_PROCESS_COMPLETE = "quality.process.complete"

    # Quality Reporting
    QUALITY_STATUS_REQUEST = "quality.status.request"
    QUALITY_STATUS_RESPONSE = "quality.status.response"
    QUALITY_REPORT_REQUEST = "quality.report.request"
    QUALITY_REPORT_RESPONSE = "quality.report.response"

    # Quality Advanced Checks
    QUALITY_ANOMALY_DETECT = "quality.anomaly.detect"
    QUALITY_PATTERN_RECOGNIZE = "quality.pattern.recognize"

    # Quality Cleanup
    QUALITY_CLEANUP_REQUEST = "quality.cleanup.request"
    QUALITY_CLEANUP_COMPLETE = "quality.cleanup.complete"

    # Core Process Flow
    QUALITY_PROCESS_START = "quality.process.start"
    QUALITY_PROCESS_PROGRESS = "quality.process.progress"
    QUALITY_PROCESS_FAILED = "quality.process.failed"

    # Context Analysis
    QUALITY_CONTEXT_ANALYZE_REQUEST = "quality.context.analyze.request"
    QUALITY_CONTEXT_ANALYZE_PROGRESS = "quality.context.analyze.progress"
    QUALITY_CONTEXT_ANALYZE_COMPLETE = "quality.context.analyze.complete"

    # Detection Process
    QUALITY_DETECTION_START = "quality.detection.start"
    QUALITY_DETECTION_PROGRESS = "quality.detection.progress"
    QUALITY_DETECTION_COMPLETE = "quality.detection.complete"

    # Issue Management
    QUALITY_ISSUE_DETECT = "quality.issue.detect"
    QUALITY_ISSUE_ANALYZE = "quality.issue.analyze"
    QUALITY_ISSUE_VALIDATE = "quality.issue.validate"

    # Resolution Management
    QUALITY_RESOLUTION_REQUEST = "quality.resolution.request"
    QUALITY_RESOLUTION_APPLY = "quality.resolution.apply"
    QUALITY_RESOLUTION_VALIDATE = "quality.resolution.validate"
    QUALITY_RESOLUTION_COMPLETE = "quality.resolution.complete"

    # Validation Flow
    QUALITY_VALIDATE_PROGRESS = "quality.validate.progress"
    # Quality Reporting
    QUALITY_REPORT_GENERATE = "quality.report.generate"
    QUALITY_METRICS_UPDATE = "quality.metrics.update"
    # System Operations
    QUALITY_CONFIG_UPDATE = "quality.config.update"
    QUALITY_RESOURCE_REQUEST = "quality.resource.request"

    #......................................Insight Types.............................................................
    # Core Flow
    INSIGHT_GENERATE_REQUEST = "insight.generate.request"
    INSIGHT_GENERATE_PROGRESS = "insight.generate.progress"
    INSIGHT_GENERATE_COMPLETE = "insight.generate.complete"
    INSIGHT_GENERATE_FAILED = "insight.generate.failed"

    # Context Analysis
    INSIGHT_CONTEXT_ANALYZE_REQUEST = "insight.context.analyze.request"
    INSIGHT_CONTEXT_ANALYZE_PROGRESS = "insight.context.analyze.progress"
    INSIGHT_CONTEXT_ANALYZE_COMPLETE = "insight.context.analyze.complete"

    # Detection Process
    INSIGHT_DETECTION_START = "insight.detection.start"
    INSIGHT_DETECTION_PROGRESS = "insight.detection.progress"
    INSIGHT_DETECTION_COMPLETE = "insight.detection.complete"
    INSIGHT_DETECTION_FAILED = "insight.detection.failed"

    # Type-Specific Processing
    INSIGHT_PATTERN_PROCESS = "insight.pattern.process"
    INSIGHT_TREND_PROCESS = "insight.trend.process"
    INSIGHT_RELATIONSHIP_PROCESS = "insight.relationship.process"
    INSIGHT_ANOMALY_PROCESS = "insight.anomaly.process"
    INSIGHT_CUSTOM_PROCESS = "insight.custom.process"

    # Validation Flow
    INSIGHT_VALIDATE_REQUEST = "insight.validate.request"
    INSIGHT_VALIDATE_PROGRESS = "insight.validate.progress"
    INSIGHT_VALIDATE_COMPLETE = "insight.validate.complete"
    INSIGHT_VALIDATE_FAILED = "insight.validate.failed"

    # Resource Management
    INSIGHT_RESOURCE_REQUEST = "insight.resource.request"
    INSIGHT_RESOURCE_RELEASE = "insight.resource.release"
    INSIGHT_RESOURCE_UNAVAILABLE = "insight.resource.unavailable"

    # Pipeline Control
    INSIGHT_PIPELINE_PAUSE = "insight.pipeline.pause"
    INSIGHT_PIPELINE_RESUME = "insight.pipeline.resume"
    INSIGHT_PIPELINE_CANCEL = "insight.pipeline.cancel"
    INSIGHT_PIPELINE_ROLLBACK = "insight.pipeline.rollback"

    # System Operations
    INSIGHT_METRICS_UPDATE = "insight.metrics.update"
    INSIGHT_HEALTH_CHECK = "insight.health.check"
    INSIGHT_CONFIG_UPDATE = "insight.config.update"
    INSIGHT_BACKPRESSURE_NOTIFY = "insight.backpressure.notify"

    # Component Communication
    INSIGHT_COMPONENT_HEARTBEAT = "insight.component.heartbeat"
    INSIGHT_COMPONENT_COORDINATE = "insight.component.coordinate"
    INSIGHT_COMPONENT_SYNC = "insight.component.sync"

    # ....................................Advanced Analytics Types........................................
    # Core Process Flow
    ANALYTICS_PROCESS_START = "analytics.process.start"
    ANALYTICS_PROCESS_PROGRESS = "analytics.process.progress"
    ANALYTICS_PROCESS_COMPLETE = "analytics.process.complete"
    ANALYTICS_PROCESS_FAILED = "analytics.process.failed"
    ANALYTICS_PROCESS_REQUEST = "analytics.process.request"
    ANALYTICS_PROCESS_ERROR = "analytics.process.error"

    # Data Preparation
    ANALYTICS_DATA_PREPARE_REQUEST = "analytics.data.prepare.request"
    ANALYTICS_DATA_PREPARE_PROGRESS = "analytics.data.prepare.progress"
    ANALYTICS_DATA_PREPARE_COMPLETE = "analytics.data.prepare.complete"
    ANALYTICS_DATA_VALIDATE = "analytics.data.validate"
    ANALYTICS_DATA_VALIDATE_REQUEST = "analytics.data.validate.request"
    ANALYTICS_DATA_VALIDATE_COMPLETE = "analytics.data.validate.complete"

    # Feature Engineering
    ANALYTICS_FEATURE_SELECT_REQUEST = "analytics.feature.select.request"
    ANALYTICS_FEATURE_TRANSFORM_REQUEST = "analytics.feature.transform.request"
    ANALYTICS_FEATURE_VALIDATE = "analytics.feature.validate"
    ANALYTICS_FEATURE_ENGINEER_REQUEST = "analytics.feature.engineer.request"
    ANALYTICS_FEATURE_ENGINEER_COMPLETE = "analytics.feature.engineer.complete"
    ANALYTICS_FEATURE_SELECT_COMPLETE = "analytics.feature.select.complete"

    # Model Management
    ANALYTICS_MODEL_SELECT_REQUEST = "analytics.model.select.request"
    ANALYTICS_MODEL_TRAIN_REQUEST = "analytics.model.train.request"
    ANALYTICS_MODEL_EVALUATE_REQUEST = "analytics.model.evaluate.request"
    ANALYTICS_MODEL_TUNE_REQUEST = "analytics.model.tune.request"
    ANALYTICS_MODEL_DEPLOY = "analytics.model.deploy"
    ANALYTICS_MODEL_MONITOR = "analytics.model.monitor"
    ANALYTICS_MODEL_SELECT_COMPLETE = "analytics.model.select.complete"
    ANALYTICS_MODEL_TRAIN_COMPLETE = "analytics.model.train.complete"
    ANALYTICS_MODEL_EVALUATE_COMPLETE = "analytics.model.evaluate.complete"

    # Performance Analysis
    ANALYTICS_PERFORMANCE_EVALUATE = "analytics.performance.evaluate"
    ANALYTICS_BIAS_CHECK = "analytics.bias.check"
    ANALYTICS_STABILITY_TEST = "analytics.stability.test"
    ANALYTICS_DRIFT_DETECT = "analytics.drift.detect"

    # Resource Management
    ANALYTICS_RESOURCE_REQUEST = "analytics.resource.request"
    ANALYTICS_RESOURCE_ALLOCATE = "analytics.resource.allocate"
    ANALYTICS_RESOURCE_RELEASE = "analytics.resource.release"
    ANALYTICS_RESOURCE_EXCEEDED = "analytics.resource.exceeded"

    # Pipeline Control
    ANALYTICS_PIPELINE_PAUSE = "analytics.pipeline.pause"
    ANALYTICS_PIPELINE_RESUME = "analytics.pipeline.resume"
    ANALYTICS_PIPELINE_CANCEL = "analytics.pipeline.cancel"
    ANALYTICS_PIPELINE_ROLLBACK = "analytics.pipeline.rollback"

    # System Operations
    ANALYTICS_METRICS_UPDATE = "analytics.metrics.update"
    ANALYTICS_HEALTH_CHECK = "analytics.health.check"
    ANALYTICS_CONFIG_UPDATE = "analytics.config.update"
    ANALYTICS_BACKPRESSURE_NOTIFY = "analytics.backpressure.notify"

    # ML Operations
    ANALYTICS_MODEL_VERSION_CONTROL = "analytics.model.version"
    ANALYTICS_MODEL_REGISTRY_UPDATE = "analytics.model.registry"
    ANALYTICS_MODEL_ARTIFACT_STORE = "analytics.model.artifact"
    ANALYTICS_MODEL_LINEAGE_TRACK = "analytics.model.lineage"

    # Visualization
    ANALYTICS_VISUALIZATION_REQUEST = "analytics.visualization.request"
    ANALYTICS_VISUALIZATION_COMPLETE = "analytics.visualization.complete"

    # Status & Control
    ANALYTICS_STATUS_REQUEST = "analytics.status.request"
    ANALYTICS_STATUS_UPDATE = "analytics.status.update"
    ANALYTICS_CANCEL_REQUEST = "analytics.cancel.request"
    ANALYTICS_CLEANUP_REQUEST = "analytics.cleanup.request"

    #....................................Decision Types........................................
    # Core Process Flow
    DECISION_PROCESS_START = "decision.process.start"
    DECISION_PROCESS_PROGRESS = "decision.process.progress"
    DECISION_PROCESS_COMPLETE = "decision.process.complete"
    DECISION_PROCESS_FAILED = "decision.process.failed"

    # Context Analysis
    DECISION_CONTEXT_ANALYZE_REQUEST = "decision.context.analyze.request"
    DECISION_CONTEXT_ANALYZE_PROGRESS = "decision.context.analyze.progress"
    DECISION_CONTEXT_ANALYZE_COMPLETE = "decision.context.analyze.complete"
    DECISION_CONTEXT_ANALYZE_FAILED = "decision.context.analyze.failed"

    # Option Management
    DECISION_OPTIONS_GENERATE_REQUEST = "decision.options.generate.request"
    DECISION_OPTIONS_GENERATE_PROGRESS = "decision.options.generate.progress"
    DECISION_OPTIONS_GENERATE_COMPLETE = "decision.options.generate.complete"
    DECISION_OPTIONS_UPDATE = "decision.options.update"
    DECISION_OPTIONS_PRIORITIZE = "decision.options.prioritize"

    # Validation Flow
    DECISION_VALIDATE_REQUEST = "decision.validate.request"
    DECISION_VALIDATE_PROGRESS = "decision.validate.progress"
    DECISION_VALIDATE_COMPLETE = "decision.validate.complete"
    DECISION_VALIDATE_REJECT = "decision.validate.reject"
    DECISION_VALIDATE_RETRY = "decision.validate.retry"
    DECISION_VALIDATE_APPROVE = "decision.validate.approve"

    # Impact Assessment
    DECISION_IMPACT_ASSESS_REQUEST = "decision.impact.assess.request"
    DECISION_IMPACT_ASSESS_PROGRESS = "decision.impact.assess.progress"
    DECISION_IMPACT_ASSESS_COMPLETE = "decision.impact.assess.complete"
    DECISION_IMPACT_SIMULATE = "decision.impact.simulate"

    # Component Communication
    DECISION_COMPONENT_REQUEST = "decision.component.request"
    DECISION_COMPONENT_RESPONSE = "decision.component.response"
    DECISION_COMPONENT_TIMEOUT = "decision.component.timeout"
    DECISION_COMPONENT_ERROR = "decision.component.error"
    DECISION_COMPONENT_UPDATE = "decision.component.update"
    DECISION_COMPONENT_NOTIFY = "decision.component.notify"

    # Resource Management
    DECISION_RESOURCE_REQUEST = "decision.resource.request"
    DECISION_RESOURCE_ALLOCATE = "decision.resource.allocate"
    DECISION_RESOURCE_RELEASE = "decision.resource.release"
    DECISION_RESOURCE_EXCEEDED = "decision.resource.exceeded"

    # Pipeline Control
    DECISION_PIPELINE_PAUSE = "decision.pipeline.pause"
    DECISION_PIPELINE_RESUME = "decision.pipeline.resume"
    DECISION_PIPELINE_CANCEL = "decision.pipeline.cancel"
    DECISION_PIPELINE_ROLLBACK = "decision.pipeline.rollback"

    # System Operations
    DECISION_METRICS_UPDATE = "decision.metrics.update"
    DECISION_HEALTH_CHECK = "decision.health.check"
    DECISION_CONFIG_UPDATE = "decision.config.update"
    DECISION_BACKPRESSURE_NOTIFY = "decision.backpressure.notify"

    # Compliance and Audit
    DECISION_AUDIT_LOG = "decision.audit.log"
    DECISION_COMPLIANCE_CHECK = "decision.compliance.check"
    DECISION_POLICY_VALIDATE = "decision.policy.validate"

    # Status & Control
    DECISION_STATUS_REQUEST = "decision.status.request"
    DECISION_STATUS_UPDATE = "decision.status.update"
    DECISION_CANCEL_REQUEST = "decision.cancel.request"

    #..............................Recommendation Types.......................................................
    # Recommendation Engine
    RECOMMENDATION_GENERATE_REQUEST = "recommendation.generate.request"
    RECOMMENDATION_GENERATE_COMPLETE = "recommendation.generate.complete"

    # Recommendation Context Analysis
    RECOMMENDATION_CONTEXT_ANALYZE_REQUEST = "recommendation.context.analyze.request"
    RECOMMENDATION_CONTEXT_ANALYZE_COMPLETE = "recommendation.context.analyze.complete"

    # Recommendation Candidates Management
    RECOMMENDATION_CANDIDATES_GENERATE_REQUEST = "recommendation.candidates.generate.request"
    RECOMMENDATION_CANDIDATES_GENERATE_COMPLETE = "recommendation.candidates.generate.complete"

    # Recommendation Filtering
    RECOMMENDATION_FILTER_REQUEST = "recommendation.candidates.filter.request"
    RECOMMENDATION_FILTER_COMPLETE = "recommendation.candidates.filter.complete"

    # Recommendation Ranking
    RECOMMENDATION_RANK_REQUEST = "recommendation.candidates.rank.request"
    RECOMMENDATION_RANK_COMPLETE = "recommendation.candidates.rank.complete"

    # Recommendation Merging
    RECOMMENDATION_MERGE_REQUEST = "recommendation.candidates.merge.request"
    RECOMMENDATION_MERGE_COMPLETE = "recommendation.candidates.merge.complete"

    # Recommendation Validation
    RECOMMENDATION_VALIDATE_REQUEST = "recommendation.validate.request"
    RECOMMENDATION_VALIDATE_COMPLETE = "recommendation.validate.complete"
    RECOMMENDATION_VALIDATE_APPROVE = "recommendation.validate.approve"
    RECOMMENDATION_VALIDATE_REJECT = "recommendation.validate.reject"

    # Recommendation Advanced Features
    RECOMMENDATION_PERSONALIZE = "recommendation.personalize"
    RECOMMENDATION_DIVERSITY_ENSURE = "recommendation.diversity.ensure"
    RECOMMENDATION_FEEDBACK_INCORPORATE = "recommendation.feedback.incorporate"

    # Recommendation Reporting
    RECOMMENDATION_STATUS_REQUEST = "recommendation.status.request"
    RECOMMENDATION_STATUS_RESPONSE = "recommendation.status.response"
    RECOMMENDATION_REPORT_REQUEST = "recommendation.report.request"
    RECOMMENDATION_REPORT_RESPONSE = "recommendation.report.response"

    # Core Process Flow
    RECOMMENDATION_PROCESS_START = "recommendation.process.start"
    RECOMMENDATION_PROCESS_PROGRESS = "recommendation.process.progress"
    RECOMMENDATION_PROCESS_COMPLETE = "recommendation.process.complete"
    RECOMMENDATION_PROCESS_FAILED = "recommendation.process.failed"

    # Candidate Generation
    RECOMMENDATION_CANDIDATES_GENERATE = "recommendation.candidates.generate"
    RECOMMENDATION_CANDIDATES_PROGRESS = "recommendation.candidates.progress"
    RECOMMENDATION_CANDIDATES_COMPLETE = "recommendation.candidates.complete"

    # Engine-Specific Processing
    RECOMMENDATION_ENGINE_CONTENT = "recommendation.engine.content"
    RECOMMENDATION_ENGINE_COLLABORATIVE = "recommendation.engine.collaborative"
    RECOMMENDATION_ENGINE_CONTEXTUAL = "recommendation.engine.contextual"
    RECOMMENDATION_ENGINE_HYBRID = "recommendation.engine.hybrid"

    # Diversity and Personalization
    RECOMMENDATION_DIVERSITY_APPLY = "recommendation.diversity.apply"
    RECOMMENDATION_BUSINESS_RULES = "recommendation.rules.apply"

    # Validation and Feedback
    RECOMMENDATION_FEEDBACK_PROCESS = "recommendation.feedback.process"

    # System Operations
    RECOMMENDATION_METRICS_UPDATE = "recommendation.metrics.update"
    RECOMMENDATION_CONFIG_UPDATE = "recommendation.config.update"
    RECOMMENDATION_CLEANUP_REQUEST = "recommendation.cleanup.request"

    #......................................Pipeline Types.............................................................
    # Pipeline Management
    PIPELINE_CREATE_REQUEST = "pipeline.create.request"
    PIPELINE_CREATE_COMPLETE = "pipeline.create.complete"
    PIPELINE_START_REQUEST = "pipeline.start.request"
    PIPELINE_START_COMPLETE = "pipeline.start.complete"

    # Pipeline Stage Management
    PIPELINE_STAGE_START_REQUEST = "pipeline.stage.start.request"
    PIPELINE_STAGE_START_COMPLETE = "pipeline.stage.start.complete"
    PIPELINE_STAGE_COMPLETE_NOTIFY = "pipeline.stage.complete.notify"
    PIPELINE_STAGE_START_FAILED = 'pipeline.stage.start.failed'

    # Pipeline State Control
    PIPELINE_PAUSE_REQUEST = "pipeline.pause.request"
    PIPELINE_PAUSE_COMPLETE = "pipeline.pause.complete"
    PIPELINE_RESUME_REQUEST = "pipeline.resume.request"
    PIPELINE_RESUME_COMPLETE = "pipeline.resume.complete"
    PIPELINE_CANCEL_REQUEST = "pipeline.cancel.request"
    PIPELINE_CANCEL_COMPLETE = "pipeline.cancel.complete"

    # Pipeline Progress and Status
    PIPELINE_PROGRESS_UPDATE = "pipeline.progress.update"
    PIPELINE_STATUS_REQUEST = "pipeline.status.request"
    PIPELINE_STATUS_RESPONSE = "pipeline.status.response"
    PIPELINE_ERROR_NOTIFY = "pipeline.error.notify"
    PIPELINE_METRICS_UPDATE = "pipeline.metrics.update"

    # Pipeline Reporting
    PIPELINE_REPORT_REQUEST = "pipeline.report.request"
    PIPELINE_REPORT_RESPONSE = "pipeline.report.response"

    #..................................Reporting Types.........................................................
    # Reporting Management
    REPORT_GENERATE_REQUEST = "report.generate.request"
    REPORT_GENERATE_COMPLETE = "report.generate.complete"

    # Report Data Preparation
    REPORT_DATA_PREPARE_REQUEST = "report.data.prepare.request"
    REPORT_DATA_PREPARE_COMPLETE = "report.data.prepare.complete"

    # Report Section Management
    REPORT_SECTION_GENERATE_REQUEST = "report.section.generate.request"
    REPORT_SECTION_GENERATE_COMPLETE = "report.section.generate.complete"

    # Report Visualization
    REPORT_VISUALIZATION_GENERATE_REQUEST = "report.visualization.generate.request"
    REPORT_VISUALIZATION_GENERATE_COMPLETE = "report.visualization.generate.complete"

    # Report Validation
    REPORT_VALIDATE_REQUEST = "report.validate.request"
    REPORT_VALIDATE_COMPLETE = "report.validate.complete"
    REPORT_VALIDATE_APPROVE = "report.validate.approve"
    REPORT_VALIDATE_REJECT = "report.validate.reject"

    # Report Review
    REPORT_REVIEW_REQUEST = "report.review.request"
    REPORT_REVIEW_COMPLETE = "report.review.complete"

    # Report Status and Tracking
    REPORT_STATUS_REQUEST = "report.status.request"
    REPORT_STATUS_RESPONSE = "report.status.response"

    # Core Process Flow
    REPORT_PROCESS_START = "report.process.start"
    REPORT_PROCESS_PROGRESS = "report.process.progress"
    REPORT_PROCESS_COMPLETE = "report.process.complete"
    REPORT_PROCESS_FAILED = "report.process.failed"

    # Data Preparation
    REPORT_DATA_PREPARE_PROGRESS = "report.data.prepare.progress"

    # Visualization Generation
    REPORT_VISUALIZATION_REQUEST = "report.visualization.generate"
    REPORT_VISUALIZATION_COMPLETE = "report.visualization.complete"
    REPORT_CHART_GENERATE = "report.chart.generate"
    REPORT_GRAPH_GENERATE = "report.graph.generate"

    # Format and Layout
    REPORT_FORMAT_REQUEST = "report.format.request"
    REPORT_LAYOUT_APPLY = "report.layout.apply"
    REPORT_STYLE_UPDATE = "report.style.update"

    # Review and Validation
    REPORT_FEEDBACK_SUBMIT = "report.feedback.submit"

    # Export and Delivery
    REPORT_EXPORT_REQUEST = "report.export.request"
    REPORT_EXPORT_COMPLETE = "report.export.complete"
    REPORT_DELIVERY_REQUEST = "report.delivery.request"

    # System Operations
    REPORT_CONFIG_UPDATE = "report.config.update"
    REPORT_TEMPLATE_UPDATE = "report.template.update"
    REPORT_CLEANUP_REQUEST = "report.cleanup.request"

    #........................................Staging Types..........................................................
    # Staging Management
    STAGING_CREATE_REQUEST = "staging.create.request"
    STAGING_CREATE_COMPLETE = "staging.create.complete"

    # Staging Data Operations
    STAGING_STORE_REQUEST = "staging.store.request"
    STAGING_STORE_COMPLETE = "staging.store.complete"
    STAGING_RETRIEVE_REQUEST = "staging.retrieve.request"
    STAGING_RETRIEVE_COMPLETE = "staging.retrieve.complete"
    STAGING_DELETE_REQUEST = "staging.delete.request"
    STAGING_DELETE_COMPLETE = "staging.delete.complete"

    # Staging Access Control
    STAGING_ACCESS_REQUEST = "staging.access.request"
    STAGING_ACCESS_GRANT = "staging.access.grant"
    STAGING_ACCESS_DENY = "staging.access.deny"

    # Staging Versioning
    STAGING_VERSION_CREATE_REQUEST = "staging.version.create.request"
    STAGING_VERSION_CREATE_COMPLETE = "staging.version.create.complete"

    # Staging Status and Metrics
    STAGING_STATUS_REQUEST = "staging.status.request"
    STAGING_STATUS_RESPONSE = "staging.status.response"
    STAGING_METRICS_UPDATE = "staging.metrics.update"

    # Staging Cleanup
    STAGING_CLEANUP_REQUEST = "staging.cleanup.request"
    STAGING_CLEANUP_COMPLETE = "staging.cleanup.complete"

    # Component Communication
    COMPONENT_INITIALIZE_REQUEST = "component.initialize.request"
    COMPONENT_INITIALIZE_COMPLETE = "component.initialize.complete"
    COMPONENT_UPDATE_REQUEST = "component.update.request"
    COMPONENT_UPDATE_COMPLETE = "component.update.complete"
    COMPONENT_ERROR_NOTIFY = "component.error.notify"
    COMPONENT_SYNC_REQUEST = "component.sync.request"
    COMPONENT_SYNC_COMPLETE = "component.sync.complete"

    # Resource Management
    RESOURCE_ACCESS_REQUEST = "resource.access.request"
    RESOURCE_ACCESS_GRANT = "resource.access.grant"
    RESOURCE_ACCESS_DENY = "resource.access.deny"
    RESOURCE_RELEASE_REQUEST = "resource.release.request"
    RESOURCE_RELEASE_COMPLETE = "resource.release.complete"

    # Monitoring and Metrics
    METRICS_COLLECT_REQUEST = "metrics.collect.request"
    METRICS_COLLECT_COMPLETE = "metrics.collect.complete"
    METRICS_ALERT_NOTIFY = "metrics.alert.notify"

    # Configuration Management
    CONFIG_UPDATE_REQUEST = "config.update.request"
    CONFIG_UPDATE_COMPLETE = "config.update.complete"
    CONFIG_ACCESS_REQUEST = "config.access.request"
    CONFIG_ACCESS_COMPLETE = "config.access.complete"

    # Error Handling
    ERROR_REPORT_NOTIFY = "error.report.notify"
    ERROR_PROCESS_REQUEST = "error.process.request"
    ERROR_PROCESS_COMPLETE = "error.process.complete"
    ERROR_RECOVER_REQUEST = "error.recover.request"
    ERROR_RECOVER_COMPLETE = "error.recover.complete"
    ERROR_CRITICAL_DETECT = "error.critical.detect"
    ERROR_FALLBACK_TRIGGER = "error.fallback.trigger"
    ERROR_CIRCUIT_BREAK = "error.circuit.break"

    # Feedback System
    FEEDBACK_SUBMIT_REQUEST = "feedback.submit.request"
    FEEDBACK_SUBMIT_COMPLETE = "feedback.submit.complete"
    FEEDBACK_PROCESS_REQUEST = "feedback.process.request"
    FEEDBACK_PROCESS_COMPLETE = "feedback.process.complete"

    # Compliance and Governance
    COMPLIANCE_CHECK_REQUEST = "compliance.check.request"
    COMPLIANCE_VALIDATE_COMPLETE = "compliance.validate.complete"
    GOVERNANCE_AUDIT_TRIGGER = "governance.audit.trigger"
    GOVERNANCE_POLICY_UPDATE = "governance.policy.update"
    COMPLIANCE_VIOLATION_DETECT = "compliance.violation.detect"
    REGULATORY_REQUIREMENT_CHECK = "regulatory.requirement.check"

    # User Interaction and Collaboration
    USER_NOTIFICATION_CREATE = "user.notification.create"
    USER_FEEDBACK_SUBMIT = "user.feedback.submit"
    USER_INTERVENTION_REQUEST = "user.intervention.request"
    USER_COLLABORATION_INVITE = "user.collaboration.invite"
    USER_PREFERENCES_UPDATE = "user.preferences.update"
    USER_ACCESS_REQUEST = "user.access.request"
    USER_ROLE_CHANGE = "user.role.change"

    # Security and Access Control
    SECURITY_THREAT_DETECT = "security.threat.detect"
    SECURITY_ACCESS_ANOMALY_DETECT = "security.access.anomaly.detect"
    SECURITY_ENCRYPTION_ROTATE_REQUEST = "security.encryption.rotate.request"
    SECURITY_COMPLIANCE_LOG = "security.compliance.log"
    SECURITY_AUTHENTICATION_REQUEST = "security.auth.request"
    SECURITY_AUTHENTICATION_COMPLETE = "security.auth.complete"
    SECURITY_AUTHORIZATION_CHECK = "security.authorization.check"
    SECURITY_TOKEN_REFRESH_REQUEST = "security.token.refresh.request"
    SECURITY_TOKEN_REFRESH_COMPLETE = "security.token.refresh.complete"

    # Machine Learning and Adaptive Systems
    ML_MODEL_RETRAIN_REQUEST = "ml.model.retrain.request"
    ML_MODEL_RETRAIN_COMPLETE = "ml.model.retrain.complete"
    ML_PERFORMANCE_MONITOR = "ml.performance.monitor"
    ML_DRIFT_DETECT = "ml.drift.detect"
    ML_EXPLAINABILITY_REQUEST = "ml.explainability.request"
    ML_FAIRNESS_ASSESS = "ml.fairness.assess"

    # Integration and Interoperability
    INTEGRATION_DEPENDENCY_CHECK = "integration.dependency.check"
    INTEGRATION_WORKFLOW_SYNC_REQUEST = "integration.workflow.sync.request"
    INTEGRATION_WORKFLOW_SYNC_COMPLETE = "integration.workflow.sync.complete"
    INTEGRATION_PERFORMANCE_OPTIMIZE_REQUEST = "integration.performance.optimize.request"
    INTEGRATION_PERFORMANCE_OPTIMIZE_COMPLETE = "integration.performance.optimize.complete"
    INTEGRATION_DATA_EXCHANGE_REQUEST = "integration.data.exchange.request"
    INTEGRATION_DATA_EXCHANGE_COMPLETE = "integration.data.exchange.complete"
    INTEGRATION_SERVICE_DISCOVER = "integration.service.discover"

    # Advanced Communication Patterns
    COMMUNICATION_ASYNC_REQUEST = "communication.async.request"
    COMMUNICATION_SYNC_REQUEST = "communication.sync.request"
    COMMUNICATION_BROADCAST = "communication.broadcast"
    COMMUNICATION_MULTICHANNEL = "communication.multichannel"

    # Extensibility Marker
    CUSTOM_EXTENSION_POINT = "custom.extension.point"

    #..................................Monitoring Types...................................................
    # Core Monitoring Flow
    MONITORING_PROCESS_START = "monitoring.process.start"
    MONITORING_PROCESS_PROGRESS = "monitoring.process.progress"
    MONITORING_PROCESS_COMPLETE = "monitoring.process.complete"
    MONITORING_PROCESS_FAILED = "monitoring.process.failed"

    # Metric Collection
    MONITORING_METRICS_COLLECT = "monitoring.metrics.collect"
    MONITORING_METRICS_UPDATE = "monitoring.metrics.update"
    MONITORING_METRICS_AGGREGATE = "monitoring.metrics.aggregate"
    MONITORING_METRICS_EXPORT = "monitoring.metrics.export"

    # Performance Monitoring
    MONITORING_PERFORMANCE_CHECK = "monitoring.performance.check"
    MONITORING_PERFORMANCE_ALERT = "monitoring.performance.alert"
    MONITORING_PERFORMANCE_REPORT = "monitoring.performance.report"

    # Resource Management
    MONITORING_RESOURCE_CHECK = "monitoring.resource.check"
    MONITORING_RESOURCE_ALERT = "monitoring.resource.alert"
    MONITORING_RESOURCE_THRESHOLD = "monitoring.resource.threshold"

    # System Health
    MONITORING_HEALTH_CHECK = "monitoring.health.check"
    MONITORING_HEALTH_STATUS = "monitoring.health.status"
    MONITORING_HEALTH_ALERT = "monitoring.health.alert"

    # Alert Management
    MONITORING_ALERT_GENERATE = "monitoring.alert.generate"
    MONITORING_ALERT_PROCESS = "monitoring.alert.process"
    MONITORING_ALERT_RESOLVE = "monitoring.alert.resolve"
    MONITORING_ALERT_ESCALATE = "monitoring.alert.escalate"

    # Data Export
    MONITORING_EXPORT_PROMETHEUS = "monitoring.export.prometheus"
    MONITORING_EXPORT_INFLUXDB = "monitoring.export.influxdb"
    MONITORING_EXPORT_JSON = "monitoring.export.json"

    # System Operations
    MONITORING_CONFIG_UPDATE = "monitoring.config.update"
    MONITORING_CLEANUP_REQUEST = "monitoring.cleanup.request"
    MONITORING_BACKUP_REQUEST = "monitoring.backup.request"

    @property
    def domain(self) -> str:
        """Extract domain from message type"""
        return self.value.split('.')[0]

    @property
    def action(self) -> str:
        """Extract action from message type"""
        parts = self.value.split('.')
        return parts[1] if len(parts) > 1 else ""

    @property
    def state(self) -> str:
        """Extract state from message type"""
        parts = self.value.split('.')
        return parts[2] if len(parts) > 2 else ""


class ComponentType(Enum):
    """Enhanced system component types with detailed categorization"""

    # Core Component Base Types
    CORE = "core"
    HANDLER = "handler"
    MANAGER = "manager"
    MODULE = "module"
    PROCESSOR = "processor"
    SERVICE = "service"

    # Department Managers
    QUALITY_MANAGER = "quality.manager"
    INSIGHT_MANAGER = "insight.manager"
    ANALYTICS_MANAGER = "analytics.manager"
    DECISION_MANAGER = "decision.manager"
    RECOMMENDATION_MANAGER = "recommendation.manager"
    REPORT_MANAGER = "report.manager"
    MONITORING_MANAGER = "monitoring.manager"
    STAGING_MANAGER = "staging.manager"
    SETTINGS_MANAGER = "settings.manager"
    PIPELINE_MANAGER = "pipeline.manager"

    # Department Handlers
    QUALITY_HANDLER = "quality.handler"
    INSIGHT_HANDLER = "insight.handler"
    ANALYTICS_HANDLER = "analytics.handler"
    DECISION_HANDLER = "decision.handler"
    RECOMMENDATION_HANDLER = "recommendation.handler"
    REPORT_HANDLER = "report.handler"
    MONITORING_HANDLER = "monitoring.handler"
    PIPELINE_HANDLER = "pipeline.handler"


    # Department Processors
    QUALITY_PROCESSOR = "quality.processor"
    INSIGHT_PROCESSOR = "insight.processor"
    ANALYTICS_PROCESSOR = "analytics.processor"
    DECISION_PROCESSOR = "decision.processor"
    RECOMMENDATION_PROCESSOR = "recommendation.processor"
    REPORT_PROCESSOR = "report.processor"
    MONITORING_PROCESSOR = "monitoring.processor"

    # Department Services
    QUALITY_SERVICE = "quality.service"
    INSIGHT_SERVICE = "insight.service"
    ANALYTICS_SERVICE = "analytics.service"
    DECISION_SERVICE = "decision.service"
    RECOMMENDATION_SERVICE = "recommendation.service"
    REPORT_SERVICE = "report.service"
    MONITORING_SERVICE = "monitoring.service"
    PIPELINE_SERVICE = "pipeline.service"
    SETTINGS_SERVICE = "settings.service"

    # External Data Source Services
    FILE_SERVICE = "service.file"
    API_SERVICE = "service.api"
    DATABASE_SERVICE = "service.database"
    STREAM_SERVICE = "service.stream"
    CLOUD_SERVICE = "service.cloud"

    # Additional Specialized Services
    STAGING_SERVICE = "service.staging"
    AUTHENTICATION_SERVICE = "service.authentication"
    AUTHORIZATION_SERVICE = "service.authorization"
    SUBSCRIPTION_SERVICE = "service.subscription"
    PAYMENT_SERVICE = "service.payment"

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
    def is_processor(self) -> bool:
        """Check if component is a processor"""
        return self.role == "processor"

    @property
    def is_service(self) -> bool:
        """Check if component is a service"""
        return self.role == "service" or self.department == "service"


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
        """Create identifier for department sub_managers"""
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


@dataclass
class MessageMetadata:
    """Enhanced message metadata with routing information"""
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_component: str = field(default_factory=lambda: "unknown")
    target_component: str = field(default_factory=lambda: "unknown")
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
class ImplementationContext:
    """Context for decision implementation tracking"""
    implementation_id: str
    decision_id: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    status: Dict[str, str] = field(default_factory=dict)
    progress: Dict[str, float] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class DecisionState(Enum):
    """States for decision processing"""
    INITIALIZING = "initializing"
    CONTEXT_ANALYSIS = "context_analysis"
    OPTION_GENERATION = "option_generation"
    VALIDATION = "validation"
    IMPACT_ANALYSIS = "impact_analysis"
    AWAITING_COMPONENT_RESPONSE = "awaiting_component_response"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DecisionContext:
    """Enhanced decision processing context"""
    pipeline_id: str
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: DecisionState = field(default_factory=lambda: DecisionState.INITIALIZING)

    # Decision Configuration and Request Tracking
    decision_type: str = field(default_factory=lambda: "standard")
    priority: str = "medium"
    requires_validation: bool = True
    auto_apply_threshold: Optional[float] = None
    request_id: Optional[str] = None
    source_component: str = field(default_factory=lambda: "unknown")
    requires_approval: bool = True

    # Decision content and Option Management
    options: List[Dict[str, Any]] = field(default_factory=list)
    selected_option: Optional[Dict[str, Any]] = None
    component_responses: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    impact_assessment: Dict[str, Any] = field(default_factory=dict)
    available_options: List[Dict[str, Any]] = field(default_factory=list)
    option_constraints: Dict[str, Any] = field(default_factory=dict)
    pending_responses: Set[str] = field(default_factory=set)
    timeout_components: List[str] = field(default_factory=list)

    # Processing metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Impact Assessment
    impact_metrics: Dict[str, float] = field(default_factory=dict)
    risk_assessment: Dict[str, Any] = field(default_factory=dict)
    compliance_status: Dict[str, bool] = field(default_factory=dict)

    def update_state(self, new_state: DecisionState) -> None:
        self.state = new_state
        self.updated_at = datetime.now()
        if new_state == DecisionState.COMPLETED:
            self.completed_at = datetime.now()


@dataclass
class DecisionRequest:
    """Structure for decision requests"""
    request_id: str
    pipeline_id: str
    source_component: str
    options: List[Dict[str, Any]]
    priority: str = "medium"
    requires_approval: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DecisionValidation:
    """Structure for validation results"""
    decision_id: str
    validation_type: str
    passed: bool
    issues: List[str] = field(default_factory=list)
    component_validations: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionImpact:
    """Structure for impact assessment"""
    decision_id: str
    affected_components: Dict[str, Any]
    cascading_effects: List[Dict[str, Any]]
    requires_updates: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DecisionMetrics:
    """Metrics for decision process tracking"""
    options_generated: int = 0
    options_validated: int = 0
    impact_scores: Dict[str, float] = field(default_factory=dict)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    risk_scores: Dict[str, float] = field(default_factory=dict)
    stakeholder_ratings: Dict[str, float] = field(default_factory=dict)
    implementation_progress: float = 0.0
    processing_time: Dict[str, float] = field(default_factory=dict)


@dataclass
class QualityMetrics:
    """Comprehensive metrics for quality analysis"""
    total_issues: int = 0
    issues_by_type: Dict[str, int] = field(default_factory=dict)
    issues_by_severity: Dict[str, int] = field(default_factory=dict)
    auto_resolvable: int = 0
    manual_required: int = 0
    resolution_rate: float = 0.0
    validation_rate: float = 0.0
    processing_time: float = 0.0
    average_severity: float = 0.0
    detection_accuracy: float = 0.0


@dataclass
class QualityRules:
    """Configuration for quality rules"""
    enabled_rules: List[str] = field(default_factory=list)
    severity_thresholds: Dict[str, float] = field(default_factory=dict)
    validation_criteria: Dict[str, Any] = field(default_factory=dict)
    auto_resolution_rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    custom_rules: Dict[str, Any] = field(default_factory=dict)


class QualityCheckType(Enum):
    """Comprehensive types of quality checks"""
    BASIC_VALIDATION = "basic_validation"
    ADDRESS_LOCATION = "address_location"
    CODE_CLASSIFICATION = "code_classification"
    DATETIME_PROCESSING = "datetime_processing"
    DOMAIN_VALIDATION = "domain_validation"
    DUPLICATION_CHECK = "duplication_check"
    IDENTIFIER_CHECK = "identifier_check"
    NUMERIC_CURRENCY = "numeric_currency"
    TEXT_STANDARD = "text_standard"
    RELATIONSHIP_CHECK = "relationship_check"
    CONSISTENCY_CHECK = "consistency_check"
    COMPLETENESS_CHECK = "completeness_check"


class QualityState(Enum):
    """States for quality processing"""
    INITIALIZING = "initializing"
    CONTEXT_ANALYSIS = "context_analysis"
    DETECTION = "detection"
    ANALYSIS = "analysis"
    RESOLUTION = "resolution"
    VALIDATION = "validation"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class QualityIssueType(Enum):
    """Types of quality issues"""
    MISSING_VALUE = "missing_value"
    INVALID_FORMAT = "invalid_format"
    INCONSISTENT_VALUE = "inconsistent_value"
    DUPLICATE_ENTRY = "duplicate_entry"
    RELATIONSHIP_VIOLATION = "relationship_violation"
    DOMAIN_VIOLATION = "domain_violation"
    RANGE_VIOLATION = "range_violation"
    FORMAT_VIOLATION = "format_violation"


class ResolutionType(Enum):
    """Types of issue resolutions"""
    AUTO_FILL = "auto_fill"
    FORMAT_CORRECTION = "format_correction"
    VALUE_STANDARDIZATION = "value_standardization"
    DUPLICATE_REMOVAL = "duplicate_removal"
    MANUAL_CORRECTION = "manual_correction"
    RELATIONSHIP_FIX = "relationship_fix"
    DOMAIN_CORRECTION = "domain_correction"


@dataclass
class QualityContext:
    """Enhanced quality processing context"""
    pipeline_id: str
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: QualityState = field(default_factory=lambda: QualityState.INITIALIZING)

    # Data Context
    total_rows: int = 0
    total_columns: int = 0
    column_profiles: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    relationships: Dict[str, List[str]] = field(default_factory=dict)

    # Processing Configuration
    enabled_checks: List[QualityCheckType] = field(default_factory=list)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    resolution_config: Dict[str, Any] = field(default_factory=dict)

    # Results Tracking
    detected_issues: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    applied_resolutions: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)

    # Performance Tracking
    processing_metrics: Dict[str, float] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def update_state(self, new_state: QualityState) -> None:
        self.state = new_state
        self.updated_at = datetime.now()

        if new_state == QualityState.COMPLETED:
            self.completed_at = datetime.now()


@dataclass
class QualityIssue:
    """Structure for quality issues"""
    issue_id: str
    issue_type: QualityIssueType
    column_name: str
    description: str
    affected_rows: List[int]
    severity: str
    auto_resolvable: bool
    resolution_type: Optional[ResolutionType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolutionResult:
    """Structure for resolution results"""
    resolution_id: str
    issue_id: str
    resolution_type: ResolutionType
    success: bool
    affected_rows: List[int]
    changes_made: Dict[str, Any]
    validation_status: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InsightMetrics:
    """Metrics tracking for insight generation"""
    total_insights: int = 0
    valid_insights: int = 0
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    processing_time: float = 0.0
    validation_scores: Dict[str, float] = field(default_factory=dict)
    review_status: Dict[str, str] = field(default_factory=dict)


class InsightState(Enum):
    """Enhanced insight processing states"""
    INITIALIZING = "initializing"
    RESOURCE_ALLOCATION = "resource_allocation"
    CONTEXT_ANALYSIS = "context_analysis"
    DETECTION_PREPARATION = "detection_preparation"
    DETECTION_IN_PROGRESS = "detection_in_progress"
    VALIDATION_PENDING = "validation_pending"
    VALIDATION_IN_PROGRESS = "validation_in_progress"
    RESULTS_AGGREGATION = "results_aggregation"
    COMPLETION = "completion"
    ERROR = "error"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    ROLLING_BACK = "rolling_back"


@dataclass
class InsightContext:
    """Enhanced insight processing context"""
    pipeline_id: str
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: InsightState = field(default_factory=lambda: InsightState.INITIALIZING)

    # Configuration
    enabled_features: List[str] = field(default_factory=list)
    custom_processors: Dict[str, Any] = field(default_factory=dict)
    processing_mode: str = "batch"  # or "streaming"

    # Resource Management
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    allocated_resources: Dict[str, Any] = field(default_factory=dict)

    # Processing Tracking
    progress: Dict[str, float] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    backpressure_indicators: Dict[str, Any] = field(default_factory=dict)

    # Results Management
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    validation_history: List[Dict[str, Any]] = field(default_factory=list)

    # Error Handling
    errors: List[Dict[str, Any]] = field(default_factory=list)
    retry_count: Dict[str, int] = field(default_factory=dict)

    # Timestamps and Duration
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    # Operational Metadata
    component_health: Dict[str, str] = field(default_factory=dict)
    sync_status: Dict[str, bool] = field(default_factory=dict)

    def update_state(self, new_state: InsightState, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Update state with tracking"""
        self.state = new_state
        self.updated_at = datetime.now()

        if metadata:
            self.metrics[f"state_change_{new_state.value}"] = metadata

        if new_state == InsightState.COMPLETION:
            self.completed_at = datetime.now()
            self.duration_ms = int((self.completed_at - self.created_at).total_seconds() * 1000)


class RecommendationState(Enum):
    """States for recommendation processing"""
    INITIALIZING = "initializing"
    CANDIDATE_GENERATION = "candidate_generation"
    FILTERING = "filtering"
    RANKING = "ranking"
    PERSONALIZATION = "personalization"
    DIVERSITY_CHECK = "diversity_check"
    VALIDATION = "validation"
    COMPLETION = "completion"
    FAILED = "failed"


class RecommendationType(Enum):
    """Types of recommendation engines"""
    CONTENT_BASED = "content_based"
    COLLABORATIVE = "collaborative"
    CONTEXTUAL = "contextual"
    HYBRID = "hybrid"
    PERSONALIZED = "personalized"


@dataclass
class RecommendationContext:
    """Enhanced recommendation processing context"""
    pipeline_id: str
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: RecommendationState = field(default_factory=lambda: RecommendationState.INITIALIZING)

    # Engine Configuration
    enabled_engines: List[RecommendationType] = field(default_factory=list)
    engine_weights: Dict[str, float] = field(default_factory=dict)
    engine_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Processing Configuration
    filtering_rules: Dict[str, Any] = field(default_factory=dict)
    ranking_criteria: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    diversity_settings: Dict[str, Any] = field(default_factory=dict)
    personalization_config: Dict[str, Any] = field(default_factory=dict)

    # Limits and Thresholds
    min_confidence: float = 0.5
    max_recommendations: int = 10
    similarity_threshold: float = 0.8

    # Results Tracking
    candidates: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    filtered_candidates: List[Dict[str, Any]] = field(default_factory=list)
    ranked_recommendations: List[Dict[str, Any]] = field(default_factory=list)

    # Performance Tracking
    processing_metrics: Dict[str, float] = field(default_factory=dict)
    engine_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def update_state(self, new_state: RecommendationState) -> None:
        """Update recommendation state with timestamp"""
        self.state = new_state
        self.updated_at = datetime.now()

        if new_state == RecommendationState.COMPLETION:
            self.completed_at = datetime.now()


@dataclass
class RecommendationCandidate:
    """Structure for recommendation candidates"""
    candidate_id: str
    source_engine: RecommendationType
    confidence_score: float
    features: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    ranking_scores: Dict[str, float] = field(default_factory=dict)
    diversity_score: Optional[float] = None


@dataclass
class RankedRecommendation:
    """Structure for ranked recommendations"""
    recommendation_id: str
    candidate: RecommendationCandidate
    final_score: float
    rank: int
    confidence: float
    ranking_factors: Dict[str, float]
    diversity_contribution: float = 0.0
    personalization_score: float = 0.0
    validation_status: Optional[str] = None


@dataclass
class RecommendationMetrics:
    """Metrics for recommendation process"""
    pipeline_id: str
    total_candidates: int = 0
    filtered_count: int = 0
    engine_metrics: Dict[str, Dict[str, float]] = field(default_factory=dict)
    ranking_metrics: Dict[str, float] = field(default_factory=dict)
    diversity_score: float = 0.0
    relevance_score: float = 0.0
    average_confidence: float = 0.0
    processing_time: Dict[str, float] = field(default_factory=dict)
    validation_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class RecommendationState(Enum):
    """States specific to recommendation processing"""
    INITIALIZING = "initializing"
    ENGINE_SELECTION = "engine_selection"
    GENERATING = "generating"
    FILTERING = "filtering"
    RANKING = "ranking"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RecommendationItem:
    """Structure for individual recommendations"""
    source_engine: str
    score: float
    confidence: float
    rationale: str
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    validated: bool = False
    ranking_features: Dict[str, float] = field(default_factory=dict)
    feedback: Optional[Dict[str, Any]] = None


@dataclass
class EngineConfig:
    """Configuration for recommendation engines"""
    engine_id: str
    weight: float = 1.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    thresholds: Dict[str, float] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class ReportSection:
    """Structure for report sections"""
    section_type: str
    title: str
    content: Dict[str, Any]
    section_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"
    dependencies: List[str] = field(default_factory=list)
    visualizations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ReportMetrics:
    """Metrics for report generation"""
    total_sections: int = 0
    completed_sections: int = 0
    visualization_count: int = 0
    processing_time: Dict[str, float] = field(default_factory=dict)
    data_points: Dict[str, int] = field(default_factory=dict)
    section_sizes: Dict[str, int] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class ReportConfig:
    """Configuration for report generation"""
    template_id: str
    sections: List[str]
    formatting: Dict[str, Any] = field(default_factory=dict)
    visualization_config: Dict[str, Any] = field(default_factory=dict)
    output_formats: List[str] = field(default_factory=list)
    custom_settings: Dict[str, Any] = field(default_factory=dict)


class ReportState(Enum):
    """States for report processing"""
    INITIALIZING = "initializing"
    DATA_PREPARATION = "data_preparation"
    SECTION_GENERATION = "section_generation"
    VISUALIZATION_CREATION = "visualization_creation"
    FORMATTING = "formatting"
    REVIEW = "review"
    EXPORT = "export"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportType(Enum):
    """Types of reports"""
    QUALITY_REPORT = "quality_report"
    INSIGHT_REPORT = "insight_report"
    ANALYTICS_REPORT = "analytics_report"
    SUMMARY_REPORT = "summary_report"
    CUSTOM_REPORT = "custom_report"


class ReportFormat(Enum):
    """Output formats for reports"""
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"
    JSON = "json"


@dataclass
class ReportContext:
    """Enhanced report processing context"""
    # Report Configuration
    pipeline_id: str
    report_type: ReportType
    report_format: ReportFormat
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: ReportState = field(default_factory=lambda: ReportState.INITIALIZING)
    template_name: Optional[str] = None
    style_config: Dict[str, Any] = field(default_factory=dict)

    # Content Management
    sections: List[Dict[str, Any]] = field(default_factory=list)
    visualizations: Dict[str, Any] = field(default_factory=dict)
    data_sources: Dict[str, Any] = field(default_factory=dict)

    # Processing State
    current_section: Optional[str] = None
    completed_sections: List[str] = field(default_factory=list)
    section_status: Dict[str, str] = field(default_factory=dict)

    # Content Validation
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)

    # Export Configuration
    export_config: Dict[str, Any] = field(default_factory=dict)
    delivery_options: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def update_state(self, new_state: ReportState) -> None:
        """Update report state with timestamp"""
        self.state = new_state
        self.updated_at = datetime.now()

        if new_state == ReportState.COMPLETED:
            self.completed_at = datetime.now()


@dataclass
class ReportSection:
    """Structure for report sections"""
    section_id: str
    title: str
    content: Dict[str, Any]
    order: int
    section_type: str
    visualizations: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Visualization:
    """Structure for report visualizations"""
    visualization_id: str
    visualization_type: str
    data: Dict[str, Any]
    config: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportTemplate:
    """Structure for report templates"""
    template_id: str
    template_type: ReportType
    sections: List[Dict[str, Any]]
    style_config: Dict[str, Any]
    validation_rules: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

class MonitoringState(Enum):
    """States for monitoring processing"""
    INITIALIZING = "initializing"
    COLLECTING = "collecting"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    EXPORTING = "exporting"
    ALERTING = "alerting"
    COMPLETED = "completed"
    FAILED = "failed"


class AlertSeverity(Enum):
    """Severity levels for monitoring alerts"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class MetricType(Enum):
    """Types of metrics collected"""
    SYSTEM = "system"
    PERFORMANCE = "performance"
    RESOURCE = "resource"
    BUSINESS = "business"
    CUSTOM = "custom"


@dataclass
class MetricsAggregate:
    """Structure for aggregated metrics"""
    metric_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    source: str
    aggregation_type: str
    dimensions: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MonitoringAlert:
    """Structure for monitoring alerts"""
    alert_id: str
    severity: AlertSeverity
    source: str
    message: str
    timestamp: datetime
    metric_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    resolution: Optional[Dict[str, Any]] = None
    escalation_level: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MonitoringState(Enum):
    """Detailed states for monitoring operations"""
    INITIALIZING = "initializing"
    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    ALERTING = "alerting"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class MonitoringMetrics:
    """Comprehensive metrics for system monitoring"""
    system_metrics: Dict[str, float] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    resource_metrics: Dict[str, float] = field(default_factory=dict)
    error_rates: Dict[str, float] = field(default_factory=dict)
    alert_counts: Dict[str, int] = field(default_factory=dict)
    response_times: Dict[str, float] = field(default_factory=dict)
    component_health: Dict[str, str] = field(default_factory=dict)
    collection_timestamps: Dict[str, str] = field(default_factory=dict)


@dataclass
class AlertContext:
    """Context for system alerts"""
    alert_id: str
    source: str
    severity: str
    message: str
    component: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    acknowledgment: Optional[Dict[str, Any]] = None
    resolution: Optional[Dict[str, Any]] = None


@dataclass
class MonitoringContext:
    """Enhanced monitoring context"""
    pipeline_id: str
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: MonitoringState = field(default_factory=lambda: MonitoringState.INITIALIZING)

    # Collection Configuration
    metric_types: List[MetricType] = field(default_factory=list)
    collectors_enabled: List[str] = field(default_factory=list)
    collection_interval: int = 60

    # Metrics Storage
    collected_metrics: Dict[str, Any] = field(default_factory=dict)
    aggregated_metrics: Dict[str, Any] = field(default_factory=dict)
    historical_metrics: List[Dict[str, Any]] = field(default_factory=list)

    # Alert Management
    active_alerts: List[Dict[str, Any]] = field(default_factory=list)
    alert_history: List[Dict[str, Any]] = field(default_factory=list)

    # Export Configuration
    export_targets: List[str] = field(default_factory=list)
    export_format: str = "json"

    # Timestamps and Duration
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def update_state(self, new_state: MonitoringState) -> None:
        """Update monitoring state with timestamp"""
        self.state = new_state
        self.updated_at = datetime.now()

        if new_state == MonitoringState.COMPLETED:
            self.completed_at = datetime.now()

    monitor_state: MonitoringState = field(default_factory=lambda: MonitoringState.INITIALIZING)
    metrics: MonitoringMetrics = field(default_factory=MonitoringMetrics)

    # Monitoring configuration
    monitored_components: List[str] = field(default_factory=list)
    source_component: str = field(default_factory=lambda: "system_monitor")
    monitoring_type: str = field(default_factory=lambda: "comprehensive")

    # Alert and Anomaly Configuration
    alert_thresholds: Dict[str, float] = field(default_factory=dict)
    alert_rules: Dict[str, Any] = field(default_factory=lambda: {
        "severity_levels": ["info", "warning", "critical"],
        "notification_channels": []
    })

    # Resource tracking
    resource_quotas: Dict[str, float] = field(default_factory=dict)
    resource_usage: Dict[str, float] = field(default_factory=dict)

    # Performance and Resource Tracking
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    resource_limits: Dict[str, Any] = field(default_factory=lambda: {
        "max_cpu_cores": None,
        "max_memory_gb": None,
        "max_disk_gb": None
    })
    performance_baselines: Dict[str, float] = field(default_factory=dict)
    performance_trends: Dict[str, List[float]] = field(default_factory=dict)

    # Health checking
    health_check_results: Dict[str, bool] = field(default_factory=dict)
    last_health_check: Optional[datetime] = None

    # Metrics Collection Configuration
    metrics_types: List[str] = field(default_factory=list)
    collectors: List[str] = field(default_factory=lambda: ["system", "application", "network"])

    # Monitoring Thresholds and Alerts
    thresholds: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "cpu_usage": {"warning": 80, "critical": 95},
        "memory_usage": {"warning": 85, "critical": 95},
        "disk_space": {"warning": 80, "critical": 90}
    })
    target_systems: List[str] = field(default_factory=list)
    excluded_systems: List[str] = field(default_factory=list)

    # Temporal Configuration
    sampling_interval: Optional[int] = 60  # Seconds
    retention_period: Optional[int] = 86400  # 24 hours in seconds

    # Advanced Monitoring Features
    anomaly_detection_enabled: bool = True
    predictive_analysis_enabled: bool = False

    # Compliance and Audit Requirements
    compliance_requirements: Dict[str, Any] = field(default_factory=dict)
    audit_logging_enabled: bool = True

    # Diagnostic and Recovery Options
    auto_recovery_enabled: bool = False
    recovery_actions: List[str] = field(default_factory=list)

    # Reporting Configuration
    reporting_config: Dict[str, Any] = field(default_factory=lambda: {
        "format": ["json", "prometheus"],
        "frequency": "hourly",
        "export_targets": []
    })

    def update_metrics(self, new_metrics: Dict[str, Any]) -> None:
        """Update monitoring metrics"""
        for category, values in new_metrics.items():
            if hasattr(self.metrics, category):
                current = getattr(self.metrics, category)
                if isinstance(current, dict):
                    current.update(values)
                else:
                    setattr(self.metrics, category, values)
        self.updated_at = datetime.now()

    def add_alert(self, alert: AlertContext) -> None:
        """Add new alert to active alerts"""
        self.active_alerts.append(alert)
        self.updated_at = datetime.now()

    def resolve_alert(self, alert_id: str, resolution: Dict[str, Any]) -> None:
        """Resolve an active alert"""
        for alert in self.active_alerts:
            if alert.alert_id == alert_id:
                alert.status = "resolved"
                alert.resolution = resolution
                self.alert_history.append(alert)
                self.active_alerts.remove(alert)
                break
        self.updated_at = datetime.now()

    def update_health_check(self, results: Dict[str, bool]) -> None:
        """Update health check results"""
        self.health_check_results.update(results)
        self.last_health_check = datetime.now()
        self.updated_at = datetime.now()


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


@dataclass
class StagingMetrics:
    """Metrics for staging operations"""
    active_stages: int = 0
    total_stored_bytes: int = 0
    total_retrieved_bytes: int = 0
    storage_operations: int = 0
    retrieval_operations: int = 0
    error_count: int = 0
    cleanup_count: int = 0
    current_storage_usage: float = 0.0
    max_storage_usage: float = 0.0
    average_storage_time: float = 0.0


@dataclass
class PipelineMetrics:
    """Metrics for pipeline processing"""
    total_stages: int = 0
    completed_stages: int = 0
    failed_stages: int = 0
    total_decisions: int = 0
    average_stage_duration: float = 0.0
    processing_time: float = 0.0
    completion_percentage: float = 0.0


@dataclass
class StagingState(Enum):
    """States for staging operations"""
    INITIALIZING = "initializing"
    STORING = "storing"
    STORED = "stored"
    RETRIEVING = "retrieving"
    CLEANING = "cleaning"
    ERROR = "error"
    DELETED = "deleted"

@dataclass
class StagingContext:
    """Context for pipeline stage execution"""
    pipeline_id: str
    stage_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stage_type: ProcessingStage = field(default_factory=lambda: ProcessingStage.INITIAL_VALIDATION)
    start_time: datetime = field(default_factory=datetime.now)
    completion_time: Optional[datetime] = None
    status: ProcessingStatus = field(default_factory=lambda: ProcessingStatus.PENDING)
    retries: int = 0
    max_retries: int = 3
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    dependencies_met: bool = False
    state: StagingState = field(default_factory=lambda: StagingState.INITIALIZING)
    storage_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_control: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    size_bytes: int = 0
    error: Optional[str] = None

    def grant_access(self, component_id: str) -> None:
        self.access_control.add(component_id)
        self.updated_at = datetime.now()

    def has_access(self, component_id: str) -> bool:
        return component_id in self.access_control


@dataclass
class PipelineState(Enum):
    """Detailed states for pipeline execution"""
    INITIALIZING = "initializing"
    STAGE_TRANSITION = "stage_transition"
    STAGE_PROCESSING = "stage_processing"
    STAGE_VALIDATING = "stage_validating"
    AWAITING_DECISION = "awaiting_decision"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RUNNING = "running"


@dataclass
class PipelineContext(BaseContext):
    """Enhanced context for pipeline execution tracking"""
    pipeline_state: PipelineState = field(default_factory=lambda: PipelineState.INITIALIZING)

    # Stage management
    current_stage: Optional[StagingContext] = None
    stage_configs: Dict[str, Any] = field(default_factory=dict)
    stages_completed: List[str] = field(default_factory=list)
    failed_stage: Optional[str] = None
    completed_stages: List[StagingContext] = field(default_factory=list)
    stage_sequence: List[ProcessingStage] = field(default_factory=list)
    stage_dependencies: Dict[str, List[str]] = field(default_factory=dict)

    # Progress tracking
    component_states: Dict[str, str] = field(default_factory=dict)
    progress: Dict[str, float] = field(default_factory=lambda: {"overall": 0.0})
    stage_timeouts: Dict[str, datetime] = field(default_factory=dict)
    retry_counts: Dict[str, int] = field(default_factory=dict)

    # Error handling
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    recovery_attempts: Dict[str, int] = field(default_factory=dict)

    # Resource tracking
    resource_allocation: Dict[str, Any] = field(default_factory=dict)
    resource_usage: Dict[str, float] = field(default_factory=dict)

    pipeline_id: str
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None

    # State management
    state: PipelineState = field(default_factory=lambda: PipelineState.INITIALIZING)
    error: Optional[str] = None

    # Decision handling
    pending_decision: Optional[Dict[str, Any]] = None
    pause_reason: Optional[str] = None

    # Metrics tracking
    metrics: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def update_stage(self, new_stage: ProcessingStage) -> None:
        """Update current stage with timestamp"""
        self.current_stage = new_stage
        self.updated_at = datetime.now()

    def complete_stage(self, stage: str) -> None:
        """Record stage completion"""
        if stage not in self.stages_completed:
            self.stages_completed.append(stage)
            self.updated_at = datetime.now()

    def update_metrics(self, metrics_update: Dict[str, Any]) -> None:
        """Update pipeline metrics"""
        self.metrics.update(metrics_update)
        self.updated_at = datetime.now()

    def add_completed_stage(self, stage: str) -> None:
        """Record completed stage"""
        if stage not in self.stages_completed:
            self.stages_completed.append(stage)
            self.updated_at = datetime.now()

    def update_progress(self, stage: str, progress: float) -> None:
        """Update stage progress"""
        self.progress[stage] = progress
        self.progress["overall"] = sum(self.progress.values()) / len(self.stage_configs)
        self.updated_at = datetime.now()

    def add_error(self, stage: str, error: str, details: Dict[str, Any]) -> None:
        """Record pipeline error"""
        self.error_history.append({
            'stage': stage,
            'error': error,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        self.updated_at = datetime.now()

    def can_proceed_to_stage(self, stage: ProcessingStage) -> bool:
        """Check if pipeline can proceed to given stage"""
        if not self.stage_dependencies:
            return True

        dependencies = self.stage_dependencies.get(stage.value, [])
        completed_stages = {s.stage_type.value for s in self.completed_stages}
        return all(dep in completed_stages for dep in dependencies)


class EventTypeRegistry:
    """Central registry for managing domain event types"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventTypeRegistry, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """Initialize the registry"""
        self._registry = {}
        self._patterns = {}
        self._validators = {}
        self._metadata = {}

    def register_domain(self, domain: str, event_types: List[MessageType],
                        pattern_validator: Optional[callable] = None,
                        metadata: Optional[Dict[str, Any]] = None):
        """Register a domain's event types"""
        self._registry[domain] = event_types
        if pattern_validator:
            self._validators[domain] = pattern_validator
        if metadata:
            self._metadata[domain] = metadata

    def get_domain_events(self, domain: str) -> Optional[List[MessageType]]:
        """Get event types for a domain"""
        return self._registry.get(domain)

    def validate_event(self, domain: str, event_type: str) -> bool:
        """Validate event type against domain patterns"""
        validator = self._validators.get(domain)
        if validator:
            return validator(event_type)
        return True


@dataclass
class EventMetadata:
    """Event metadata with versioning support"""
    version: str
    domain: str
    deprecated: bool = False
    supported_versions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    deprecation_date: Optional[datetime] = None
    replacement_event: Optional[str] = None


class EventPatternValidator:
    """Validates event patterns across domains"""

    @staticmethod
    def validate_pattern(event_type: str) -> bool:
        """Validate event type follows domain pattern"""
        pattern = r'^[a-z]+\.[a-z]+\.(request|complete|progress|failed|notify)$'
        return bool(re.match(pattern, event_type))

    @staticmethod
    def create_domain_validator(domain: str, custom_pattern: Optional[str] = None):
        """Create domain-specific validator"""

        def validator(event_type: str) -> bool:
            pattern = custom_pattern or f'^{domain}\.[a-z]+\.(request|complete|progress|failed|notify)$'
            return bool(re.match(pattern, event_type))

        return validator


class EventTypeManager:
    """Manages event type lifecycle and evolution"""

    def __init__(self):
        self.registry = EventTypeRegistry()
        self.deprecated_events = {}
        self.event_metadata = {}

    def deprecate_event(self, event_type: MessageType, replacement: MessageType,
                        deprecation_date: Optional[datetime] = None):
        """Handle event deprecation"""
        metadata = self.event_metadata.get(event_type.value, EventMetadata(
            version="1.0",
            domain=event_type.domain
        ))
        metadata.deprecated = True
        metadata.replacement_event = replacement.value
        metadata.deprecation_date = deprecation_date

        self.deprecated_events[event_type.value] = replacement.value
        self.event_metadata[event_type.value] = metadata

    def register_event_type(self, domain: str, event_type: MessageType,
                            version: str = "1.0",
                            metadata: Optional[Dict[str, Any]] = None):
        """Register new event type"""
        event_metadata = EventMetadata(
            version=version,
            domain=domain,
            **(metadata or {})
        )
        self.event_metadata[event_type.value] = event_metadata


# Initialize global event management
event_manager = EventTypeManager()
event_registry = EventTypeRegistry()

# Register all domains and their events
for enum_value in MessageType:
    domain = enum_value.domain
    if domain not in event_registry._registry:
        event_registry.register_domain(
            domain,
            [msg for msg in MessageType if msg.domain == domain],
            EventPatternValidator.create_domain_validator(domain)
        )

