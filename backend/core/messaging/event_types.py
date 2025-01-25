# backend/core/messaging/event_types.py

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid
from typing import Dict, Any, Optional, Set, List
from datetime import datetime
from pathlib import Path

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
    state: ManagerState = field(default=ManagerState.INITIALIZING)
    metrics: ManagerMetrics = field(default_factory=ManagerMetrics)
    handlers: Dict[str, str] = field(default_factory=dict)


class QualityState(Enum):
    """States specific to quality processing"""
    INITIALIZING = "initializing"
    DETECTING = "detecting"
    ISSUE_DETECTED = "issue_detected"
    RESOLVING = "resolving"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class QualityCheckType(Enum):
    """Types of quality checks"""
    DATA_COMPLETENESS = "data_completeness"
    DATA_ACCURACY = "data_accuracy"
    DATA_CONSISTENCY = "data_consistency"
    DATA_TIMELINESS = "data_timeliness"
    DATA_VALIDITY = "data_validity"
    BUSINESS_RULES = "business_rules"
    REFERENCE_DATA = "reference_data"
    CUSTOM = "custom"


@dataclass
class QualityMetrics:
    """Metrics for quality processing"""
    total_records: int = 0
    processed_records: int = 0
    total_issues: int = 0
    issues_by_type: Dict[str, int] = field(default_factory=dict)
    issues_by_severity: Dict[str, int] = field(default_factory=dict)
    auto_resolvable: int = 0
    manual_required: int = 0
    resolution_rate: float = 0.0
    processing_time: float = 0.0
    completion_percentage: float = 0.0


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

    # Insight Generation
    INSIGHT_GENERATE_REQUEST = "insight.generate.request"
    INSIGHT_GENERATE_COMPLETE = "insight.generate.complete"

    # Insight Context Analysis
    INSIGHT_CONTEXT_ANALYZE_REQUEST = "insight.context.analyze.request"
    INSIGHT_CONTEXT_ANALYZE_COMPLETE = "insight.context.analyze.complete"

    # Insight Validation
    INSIGHT_VALIDATE_REQUEST = "insight.validate.request"
    INSIGHT_VALIDATE_COMPLETE = "insight.validate.complete"
    INSIGHT_VALIDATE_APPROVE = "insight.validate.approve"
    INSIGHT_VALIDATE_REJECT = "insight.validate.reject"

    # Insight Review
    INSIGHT_REVIEW_REQUEST = "insight.review.request"
    INSIGHT_REVIEW_COMPLETE = "insight.review.complete"

    # Insight Process Management
    INSIGHT_PROCESS_START_REQUEST = "insight.process.start.request"
    INSIGHT_PROCESS_STATE_UPDATE = "insight.process.state.update"
    INSIGHT_PROCESS_COMPLETE = "insight.process.complete"

    # Insight Advanced Analysis
    INSIGHT_CORRELATION_DETECT = "insight.correlation.detect"
    INSIGHT_TREND_ANALYZE = "insight.trend.analyze"
    INSIGHT_PREDICTIVE_REQUEST = "insight.predictive.request"
    INSIGHT_PREDICTIVE_GENERATE_COMPLETE = "insight.predictive.generate.complete"

    # Insight Reporting
    INSIGHT_STATUS_REQUEST = "insight.status.request"
    INSIGHT_STATUS_RESPONSE = "insight.status.response"
    INSIGHT_REPORT_REQUEST = "insight.report.request"
    INSIGHT_REPORT_RESPONSE = "insight.report.response"

    # Insight Cleanup
    INSIGHT_CLEANUP_REQUEST = "insight.cleanup.request"
    INSIGHT_CLEANUP_COMPLETE = "insight.cleanup.complete"

    # Advanced Analytics
    ANALYTICS_PROCESS_REQUEST = "analytics.process.request"
    ANALYTICS_PROCESS_COMPLETE = "analytics.process.complete"

    # Analytics Model Management
    ANALYTICS_MODEL_SELECT_REQUEST = "analytics.model.select.request"
    ANALYTICS_MODEL_SELECT_COMPLETE = "analytics.model.select.complete"
    ANALYTICS_MODEL_TRAIN_REQUEST = "analytics.model.train.request"
    ANALYTICS_MODEL_TRAIN_COMPLETE = "analytics.model.train.complete"
    ANALYTICS_MODEL_EVALUATE_REQUEST = "analytics.model.evaluate.request"
    ANALYTICS_MODEL_EVALUATE_COMPLETE = "analytics.model.evaluate.complete"

    # Analytics Feature Engineering
    ANALYTICS_FEATURE_ENGINEER_REQUEST = "analytics.feature.engineer.request"
    ANALYTICS_FEATURE_ENGINEER_COMPLETE = "analytics.feature.engineer.complete"

    # Analytics Simulation and Scenario
    ANALYTICS_SIMULATION_RUN = "analytics.simulation.run"
    ANALYTICS_SCENARIO_GENERATE = "analytics.scenario.generate"

    # Analytics Performance and Bias
    ANALYTICS_PERFORMANCE_MONITOR = "analytics.performance.monitor"
    ANALYTICS_BIAS_DETECT = "analytics.bias.detect"

    # Analytics Reporting
    ANALYTICS_STATUS_REQUEST = "analytics.status.request"
    ANALYTICS_STATUS_RESPONSE = "analytics.status.response"
    ANALYTICS_REPORT_REQUEST = "analytics.report.request"
    ANALYTICS_REPORT_RESPONSE = "analytics.report.response"

    # Decision Support
    DECISION_GENERATE_REQUEST = "decision.generate.request"
    DECISION_GENERATE_COMPLETE = "decision.generate.complete"

    # Decision Context Analysis
    DECISION_CONTEXT_ANALYZE_REQUEST = "decision.context.analyze.request"
    DECISION_CONTEXT_ANALYZE_COMPLETE = "decision.context.analyze.complete"

    # Decision Options Management
    DECISION_OPTIONS_GENERATE_REQUEST = "decision.options.generate.request"
    DECISION_OPTIONS_GENERATE_COMPLETE = "decision.options.generate.complete"

    # Decision Validation
    DECISION_VALIDATE_REQUEST = "decision.validate.request"
    DECISION_VALIDATE_COMPLETE = "decision.validate.complete"
    DECISION_VALIDATE_APPROVE = "decision.validate.approve"
    DECISION_VALIDATE_REJECT = "decision.validate.reject"

    # Decision Impact Assessment
    DECISION_IMPACT_ASSESS_REQUEST = "decision.impact.assess.request"
    DECISION_IMPACT_ASSESS_COMPLETE = "decision.impact.assess.complete"

    # Decision Optimization
    DECISION_OPTIMIZE_REQUEST = "decision.optimize.request"
    DECISION_OPTIMIZE_COMPLETE = "decision.optimize.complete"

    # Decision Advanced Scenarios
    DECISION_SCENARIO_CREATE = "decision.scenario.create"
    DECISION_RISK_ASSESS = "decision.risk.assess"
    DECISION_IMPACT_SIMULATE = "decision.impact.simulate"
    DECISION_RECOMMENDATION_COMPARE = "decision.recommendation.compare"

    # Decision Constraint Validation
    DECISION_CONSTRAINT_VALIDATE = "decision.constraint.validate"

    # Decision Reporting
    DECISION_STATUS_REQUEST = "decision.status.request"
    DECISION_STATUS_RESPONSE = "decision.status.response"
    DECISION_REPORT_REQUEST = "decision.report.request"
    DECISION_REPORT_RESPONSE = "decision.report.response"

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

    # Pipeline Management
    PIPELINE_CREATE_REQUEST = "pipeline.create.request"
    PIPELINE_CREATE_COMPLETE = "pipeline.create.complete"
    PIPELINE_START_REQUEST = "pipeline.start.request"
    PIPELINE_START_COMPLETE = "pipeline.start.complete"

    # Pipeline Stage Management
    PIPELINE_STAGE_START_REQUEST = "pipeline.stage.start.request"
    PIPELINE_STAGE_START_COMPLETE = "pipeline.stage.start.complete"
    PIPELINE_STAGE_COMPLETE_NOTIFY = "pipeline.stage.complete.notify"

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

    # Pipeline Reporting
    PIPELINE_REPORT_REQUEST = "pipeline.report.request"
    PIPELINE_REPORT_RESPONSE = "pipeline.report.response"

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

    # Department Handlers
    QUALITY_HANDLER = "quality.handler"
    INSIGHT_HANDLER = "insight.handler"
    ANALYTICS_HANDLER = "analytics.handler"
    DECISION_HANDLER = "decision.handler"
    RECOMMENDATION_HANDLER = "recommendation.handler"
    REPORT_HANDLER = "report.handler"
    MONITORING_HANDLER = "monitoring.handler"

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
class AnalyticsState(Enum):
    """Detailed states for analytics processing"""
    INITIALIZING = "initializing"
    DATA_PREPARATION = "data_preparation"
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_SELECTION = "model_selection"
    MODEL_TRAINING = "model_training"
    MODEL_EVALUATION = "model_evaluation"
    MODEL_VALIDATION = "model_validation"
    PREDICTION_GENERATION = "prediction_generation"
    RESULT_ANALYSIS = "result_analysis"
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
    """Enhanced analytics context with comprehensive tracking"""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_context: Optional[ModelContext] = None
    analytics_state: AnalyticsState = field(default=AnalyticsState.INITIALIZING)
    metrics: AnalyticsMetrics = field(default_factory=AnalyticsMetrics)
    feature_config: Dict[str, Any] = field(default_factory=dict)
    model_config: Dict[str, Any] = field(default_factory=dict)
    evaluation_criteria: Dict[str, Any] = field(default_factory=dict)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    visualization_config: Dict[str, Any] = field(default_factory=dict)
    error_thresholds: Dict[str, float] = field(default_factory=dict)
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    model_type: str = field(default="default_model")
    features: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    training_config: Dict[str, Any] = field(default_factory=lambda: {"method": "default"})
    evaluation_metrics: List[str] = field(default_factory=list)
    model_constraints: Dict[str, Any] = field(default_factory=dict)
    performance_requirements: Dict[str, float] = field(default_factory=lambda: {"accuracy": 0.0})
    data_dependencies: List[str] = field(default_factory=list)


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


@dataclass
class DecisionState(Enum):
    """Comprehensive states for decision processing"""
    INITIALIZING = "initializing"
    CONTEXT_ANALYSIS = "context_analysis"
    OPTION_GENERATION = "option_generation"
    IMPACT_ANALYSIS = "impact_analysis"
    CONSTRAINT_VALIDATION = "constraint_validation"
    AWAITING_APPROVAL = "awaiting_approval"
    IMPLEMENTATION = "implementation"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    ANALYZING = "analyzing"
    VALIDATING = "validating"
    AWAITING_INPUT = "awaiting_input"
    PROCESSING = "processing"


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
class DecisionContext(BaseContext):
    """Enhanced decision context with comprehensive tracking"""

    # Core tracking
    decision_state: DecisionState = field(default=DecisionState.INITIALIZING)
    metrics: DecisionMetrics = field(default_factory=DecisionMetrics)
    implementation_context: Optional[ImplementationContext] = None
    stakeholders: List[str] = field(default_factory=list)
    approval_chain: List[str] = field(default_factory=list)
    impact_criteria: Dict[str, Any] = field(default_factory=dict)
    risk_thresholds: Dict[str, float] = field(default_factory=dict)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    control_point_id: Optional[str] = None
    staged_id: Optional[str] = None

    # Decision configuration
    source_component: str = field(default="default_decision_maker")
    decision_type: str = field(default="standard_decision")
    options: List[Dict[str, Any]] = field(default_factory=list)
    impacts: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    required_validations: List[str] = field(default_factory=list)

    # Processing state
    state: DecisionState = field(default_factory=lambda: DecisionState.INITIALIZING)  # Changed this line
    requires_confirmation: bool = True
    timeout_minutes: Optional[int] = None

    # Tracking
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    feedback: List[Dict[str, Any]] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def update_state(self, new_state: DecisionState) -> None:
        """Update process state with timestamp"""
        self.state = new_state
        self.updated_at = datetime.now()

        if new_state == DecisionState.COMPLETED:
            self.completed_at = datetime.now()


@dataclass
class QualityContext(BaseContext):
    """Enhanced quality context for message-based processing"""
    # Core tracking
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    control_point_id: Optional[str] = None
    staged_id: Optional[str] = None
    source_type: str = field(default="data_quality")
    column_types: Dict[str, str] = field(default_factory=dict)
    detected_issues: List[Dict[str, Any]] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=lambda: {"overall": 0.0})
    suggested_actions: List[str] = field(default_factory=list)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    resolution_status: Dict[str, str] = field(default_factory=lambda: {"status": "pending"})
    requires_decision: bool = False

    # Process state
    state: QualityState = field(default=QualityState.INITIALIZING)
    config: Dict[str, Any] = field(default_factory=dict)

    # Results tracking
    issues: List[Dict[str, Any]] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    metrics: QualityMetrics = field(default_factory=QualityMetrics)

    # Error handling
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def update_state(self, new_state: QualityState) -> None:
        """Update process state with timestamp"""
        self.state = new_state
        self.updated_at = datetime.now()

        if new_state == QualityState.COMPLETED:
            self.completed_at = datetime.now()

    def add_warning(self, warning: str) -> None:
        """Add warning message"""
        self.warnings.append(warning)
        self.updated_at = datetime.now()

    def add_issues(self, issues: List[Dict[str, Any]]) -> None:
        """Add detected quality issues"""
        self.issues.extend(issues)
        self.updated_at = datetime.now()

    def update_metrics(self, metrics: QualityMetrics) -> None:
        """Update quality metrics"""
        self.metrics = metrics
        self.updated_at = datetime.now()


@dataclass
class InsightState(Enum):
    """States specific to insight processing"""
    INITIALIZING = "initializing"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    VALIDATING = "validating"
    REVIEWING = "reviewing"
    COMPLETING = "completing"
    FAILED = "failed"
    COMPLETED = "completed"
    AWAITING_REVIEW = "awaiting_review"


@dataclass
class InsightMetrics:
    """Metrics tracking for insight generation"""
    total_insights: int = 0
    valid_insights: int = 0
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    processing_time: float = 0.0
    validation_scores: Dict[str, float] = field(default_factory=dict)
    review_status: Dict[str, str] = field(default_factory=dict)

@dataclass
class InsightContext(BaseContext):
    """Enhanced context for insight processing"""
    # Core tracking
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    control_point_id: Optional[str] = None
    staged_id: Optional[str] = None
    data_segments: List[str] = field(default_factory=list)
    priority_rules: Dict[str, Any] = field(default_factory=dict)

    # Insight configuration
    analysis_type: str = field(default="general_analysis")
    target_metrics: List[str] = field(default_factory=list)
    insight_categories: List[str] = field(default_factory=list)
    confidence_threshold: float = 0.5
    validation_criteria: List[str] = field(default_factory=list)
    business_rules: Dict[str, Any] = field(default_factory=dict)

    # Processing state
    state: InsightState = field(default=InsightState.INITIALIZING)
    metrics: InsightMetrics = field(default_factory=InsightMetrics)
    requires_review: bool = False

    # Results tracking
    insights_generated: int = 0
    insights_validated: int = 0
    insights: Dict[str, Any] = field(default_factory=dict)

    # Error handling
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def update_state(self, new_state: InsightState) -> None:
        """Update process state with timestamp"""
        self.state = new_state
        self.updated_at = datetime.now()

        if new_state == InsightState.COMPLETED:
            self.completed_at = datetime.now()

    def add_insight(self, category: str, insight: Dict[str, Any]) -> None:
        """Add generated insight"""
        if category not in self.insights:
            self.insights[category] = []
        self.insights[category].append(insight)
        self.insights_generated += 1
        self.updated_at = datetime.now()

    def update_metrics(self, metrics_update: Dict[str, Any]) -> None:
        """Update insight metrics"""
        self.metrics = InsightMetrics(**{
            **self.metrics.__dict__,
            **metrics_update
        })
        self.updated_at = datetime.now()


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
class RecommendationContext(BaseContext):
    """Enhanced recommendation context for message-based processing"""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    control_point_id: Optional[str] = None
    staged_id: Optional[str] = None

    # Core properties
    source_component: str = field(default="recommendation_system")
    request_type: str = field(default="general_recommendation")
    target_type: str = field(default="default_target")

    # Processing state
    candidate_limits: Dict[str, int] = field(default_factory=lambda: {"max_candidates": 10})
    state: RecommendationState = field(default_factory=lambda: RecommendationState.INITIALIZING)  # Changed this line
    engine_results: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    aggregated_results: List[Dict[str, Any]] = field(default_factory=list)

    # Configuration
    enabled_engines: List[str] = field(default_factory=list)
    engine_weights: Dict[str, float] = field(default_factory=dict)
    filtering_rules: Dict[str, Any] = field(default_factory=dict)
    ranking_criteria: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    diversity_settings: Dict[str, Any] = field(default_factory=lambda: {"enabled": False})

    # Performance tracking
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    min_confidence: float = 0.5
    max_recommendations: int = 10
    timeout_seconds: Optional[int] = None

    # Contextual information
    user_context: Dict[str, Any] = field(default_factory=dict)
    temporal_context: Dict[str, Any] = field(default_factory=dict)
    business_context: Dict[str, Any] = field(default_factory=dict)

    def update_state(self, new_state: RecommendationState) -> None:
        """Update process state with timestamp"""
        self.state = new_state
        self.updated_at = datetime.now()

        if new_state == RecommendationState.COMPLETED:
            self.completed_at = datetime.now()

    def add_engine_results(self, engine: str, results: List[Dict[str, Any]]) -> None:
        """Add results from a recommendation engine"""
        self.engine_results[engine] = results
        self.updated_at = datetime.now()


# Add to event_types.py

@dataclass
class PipelineState(Enum):
    """States specific to pipeline processing"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineContext:
    """Enhanced pipeline context for orchestration"""
    pipeline_id: str
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None

    # Progress tracking
    component_states: Dict[str, str] = field(default_factory=dict)
    progress: Dict[str, float] = field(default_factory=lambda: {"overall": 0.0})

    # Stage management
    current_stage: ProcessingStage = field(default=ProcessingStage.INITIAL_VALIDATION)
    stage_configs: Dict[str, Any] = field(default_factory=dict)
    stages_completed: List[str] = field(default_factory=list)
    failed_stage: Optional[str] = None

    # State management
    state: PipelineState = field(default=PipelineState.INITIALIZING)
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


@dataclass
class StageMetadata:
    """Metadata for pipeline stages"""
    stage_type: str
    stage_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config: Dict[str, Any] = field(default_factory=dict)
    timeout_minutes: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    current_stage: str = field(default="initial")
    stage_sequence: List[str] = field(default_factory=list)
    stage_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    stage_configs: Dict[str, Any] = field(default_factory=dict)
    component_states: Dict[str, str] = field(default_factory=dict)
    progress: Dict[str, float] = field(default_factory=lambda: {"overall": 0.0})
    error_handling_rules: Dict[str, Any] = field(default_factory=lambda: {"default_action": "log"})


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
class ReportState(Enum):
    """States specific to report generation"""
    INITIALIZING = "initializing"
    GATHERING_DATA = "gathering_data"
    GENERATING = "generating"
    FORMATTING = "formatting"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportContext(BaseContext):
    """Enhanced report context for message-based processing"""
    # Core tracking
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    control_point_id: Optional[str] = None
    staged_id: Optional[str] = None

    # Report configuration
    report_type: str = field(default="default_report")
    report_id: uuid.UUID = field(default_factory=uuid.uuid4)
    format: str = field(default="html")
    template_name: Optional[str] = None
    templates: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    sections: List[ReportSectionType] = field(default_factory=lambda: [
        ReportSectionType.OVERVIEW,
        ReportSectionType.SUMMARY
    ])

    # Processing state
    state: ReportState = field(default_factory=lambda: ReportState.INITIALIZING)  # Changed this line
    section_status: Dict[str, str] = field(default_factory=lambda: {
        "overall_status": "not_started"
    })
    report_metadata: Dict[str, Any] = field(default_factory=lambda: {
        "version": "1.0",
        "generated_at": datetime.now().isoformat()
    })

    # Content tracking
    collected_data: Dict[str, Any] = field(default_factory=dict)
    generated_sections: Dict[str, Any] = field(default_factory=dict)

    # Error handling
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def update_state(self, new_state: ReportState) -> None:
        """Update process state with timestamp"""
        self.state = new_state
        self.updated_at = datetime.now()

        if new_state == ReportState.COMPLETED:
            self.completed_at = datetime.now()

    def add_section_data(self, section: str, data: Any) -> None:
        """Add data for a report section"""
        self.collected_data[section] = data
        self.section_status[section] = "data_ready"
        self.updated_at = datetime.now()

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


@dataclass
class MonitoringContext(BaseContext):
    """
    Comprehensive monitoring context for tracking system health and performance

    Provides detailed configuration and tracking for monitoring workflows
    """
    # Core monitoring configuration
    source_component: str = field(default="system_monitor")
    monitoring_type: str = field(default="comprehensive")

    # Metrics Collection Configuration
    metrics_types: List[str] = field(default_factory=list)
    collectors: List[str] = field(default_factory=lambda: ["system", "application", "network"])

    # Monitoring Thresholds and Alerts
    thresholds: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "cpu_usage": {"warning": 80, "critical": 95},
        "memory_usage": {"warning": 85, "critical": 95},
        "disk_space": {"warning": 80, "critical": 90}
    })

    # Performance and Resource Tracking
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    resource_limits: Dict[str, Any] = field(default_factory=lambda: {
        "max_cpu_cores": None,
        "max_memory_gb": None,
        "max_disk_gb": None
    })

    # Alert and Anomaly Configuration
    alert_rules: Dict[str, Any] = field(default_factory=lambda: {
        "severity_levels": ["info", "warning", "critical"],
        "notification_channels": []
    })

    # Monitoring Scope and Focus
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
    """Context for staged data"""
    stage_id: str
    pipeline_id: str
    state: StagingState = field(default=StagingState.INITIALIZING)
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

