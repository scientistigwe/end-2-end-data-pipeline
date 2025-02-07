from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Text,
    Integer, Boolean, Index, CheckConstraint, Float
)
from enum import Enum as PyEnum
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, column_property, validates
from ..core.base import BaseModel


class ComponentType(str, PyEnum):
    """Enumeration of component types for staged outputs."""
    ANALYTICS = "analytics"
    DECISION = "decision"
    INSIGHT = "insight"
    MONITORING = "monitoring"
    QUALITY = "quality"
    RECOMMENDATION = "recommendation"
    REPORT = "report"
    CONTROL = "control"


class ProcessingStage(str, PyEnum):
    """Enumeration of processing stages for staged outputs."""
    INGESTION = "ingestion"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    PROCESSING = "processing"
    COMPLETION = "completion"


class ProcessingStatus(str, PyEnum):
    """Enumeration of processing statuses for staged outputs."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class BaseStagedOutput(BaseModel):
    """Base model for all staged outputs with comprehensive tracking and validation."""
    __tablename__ = 'staged_outputs'

    # Core fields
    stage_key = Column(String, nullable=False)
    pipeline_id = Column(
        UUID(as_uuid=True),
        ForeignKey('pipelines.id', ondelete='CASCADE'),
        nullable=False
    )
    base_source_id = Column(
        'source_id',  # Actual column name in database
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='SET NULL'),
        nullable=True
    )

    # Classification
    component_type = Column(Enum(ComponentType))
    stage = Column(Enum(ProcessingStage))
    status = Column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        nullable=False
    )

    # Storage and metadata
    storage_path = Column(String(255))
    data_size = Column(Integer, default=0)
    meta_data = Column(JSONB, default=dict)
    is_temporary = Column(Boolean, default=True)

    # Performance tracking
    processing_time = Column(Float)
    error_count = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    last_error = Column(Text)
    metrics = Column(JSONB, default=dict)

    # Timestamps
    expires_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    last_processed_at = Column(DateTime)

    # Relationships
    pipeline = relationship(
        "Pipeline",
        back_populates="staged_outputs",
        foreign_keys=[pipeline_id]
    )
    source = relationship(
        "DataSource",
        foreign_keys=[base_source_id]
    )
    processing_history = relationship(
        "StagingProcessingHistory",
        back_populates="staged_output",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_staged_outputs_pipeline_id', 'pipeline_id'),
        Index('ix_staged_outputs_source_id', 'source_id'),
        Index('ix_staged_outputs_status', 'status'),
        Index('ix_staged_outputs_component', 'component_type'),
        Index('ix_staged_outputs_stage', 'stage'),
        CheckConstraint(
            'data_size >= 0',
            name='ck_data_size_non_negative'
        ),
        CheckConstraint(
            'error_count >= 0',
            name='ck_error_count_non_negative'
        ),
        CheckConstraint(
            'retry_count >= 0',
            name='ck_retry_count_non_negative'
        ),
        CheckConstraint(
            'processing_time >= 0 OR processing_time IS NULL',
            name='ck_processing_time_valid'
        ),
        CheckConstraint(
            'completed_at IS NULL OR completed_at >= started_at',
            name='ck_completion_time_valid'
        ),
        {'extend_existing': True}
    )

    __mapper_args__ = {
        "polymorphic_identity": "base",
        "polymorphic_on": component_type
    }

    @validates('stage')
    def validate_stage(self, key: str, value: ProcessingStage) -> ProcessingStage:
        """Validate stage transitions."""
        if hasattr(self, 'stage'):
            current_stage = getattr(self, 'stage')
            valid_transitions = {
                ProcessingStage.INGESTION: [ProcessingStage.VALIDATION],
                ProcessingStage.VALIDATION: [ProcessingStage.TRANSFORMATION],
                ProcessingStage.TRANSFORMATION: [ProcessingStage.PROCESSING],
                ProcessingStage.PROCESSING: [ProcessingStage.COMPLETION]
            }
            if current_stage and value not in valid_transitions.get(current_stage, []):
                raise ValueError(f"Invalid stage transition from {current_stage} to {value}")
        return value

    def update_status(self, new_status: ProcessingStatus, error: Optional[str] = None) -> None:
        """Update processing status with proper tracking."""
        self.status = new_status
        self.last_processed_at = datetime.utcnow()

        if new_status == ProcessingStatus.FAILED:
            self.error_count += 1
            self.last_error = error
        elif new_status == ProcessingStatus.COMPLETED:
            self.completed_at = datetime.utcnow()
            if self.started_at:
                self.processing_time = (self.completed_at - self.started_at).total_seconds()

    def record_metrics(self, metrics: Dict[str, Any]) -> None:
        """Record processing metrics."""
        if not self.metrics:
            self.metrics = {}

        timestamp = datetime.utcnow().isoformat()
        self.metrics[timestamp] = {
            'status': self.status,
            'stage': self.stage,
            'data_size': self.data_size,
            'error_count': self.error_count,
            'processing_time': self.processing_time,
            **metrics
        }

    def can_process(self) -> bool:
        """Check if output can be processed."""
        return (
                self.status in (ProcessingStatus.PENDING, ProcessingStatus.PAUSED) and
                (not self.expires_at or datetime.utcnow() < self.expires_at) and
                self.retry_count < 3
        )


class StagingProcessingHistory(BaseModel):
    """Model for tracking detailed processing history of staged outputs."""
    __tablename__ = 'staging_processing_history'

    # Core references
    staged_output_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id', ondelete='CASCADE'),
        nullable=False
    )
    event_type = Column(String(100), nullable=False)

    # Event details
    details = Column(JSONB)
    history_status = Column(Enum(ProcessingStatus))
    history_created_at = column_property(Column(DateTime, default=datetime.utcnow))

    # Performance tracking
    duration = Column(Float)
    memory_usage = Column(Float)
    cpu_usage = Column(Float)
    error_details = Column(JSONB)

    # Context information
    component = Column(String(100))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    trace_id = Column(String(100))

    # Relationships
    staged_output = relationship(
        "BaseStagedOutput",
        back_populates="processing_history",
        foreign_keys=[staged_output_id]
    )

    __table_args__ = (
        Index('ix_staging_history_output', 'staged_output_id'),
        Index('ix_staging_history_type', 'event_type'),
        Index('ix_staging_history_status', 'history_status'),
        CheckConstraint(
            'duration >= 0 OR duration IS NULL',
            name='ck_history_duration_valid'
        ),
        CheckConstraint(
            'memory_usage >= 0 OR memory_usage IS NULL',
            name='ck_memory_usage_valid'
        ),
        CheckConstraint(
            'cpu_usage >= 0 OR cpu_usage IS NULL',
            name='ck_cpu_usage_valid'
        ),
        {'extend_existing': True}
    )


class StagingControlPoint(BaseStagedOutput):
    """Model for managing control points in the staging process."""
    __tablename__ = 'staging_control_points'

    # Primary key and inheritance
    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )

    # Control configuration
    control_type = Column(String(100), nullable=False)
    validation_rules = Column(JSONB)
    threshold_config = Column(JSONB)
    notification_config = Column(JSONB)

    # Control state
    control_status = Column(
        Enum('pending', 'active', 'passed', 'failed', name='control_status'),
        default='pending'
    )
    last_check = Column(DateTime)
    check_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    # Decision tracking
    decision = Column(JSONB)
    decision_made_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    decision_made_at = Column(DateTime)
    decision_rationale = Column(Text)

    # Relationships
    control_source = relationship(
        "DataSource",
        back_populates="control_points",
        foreign_keys=[BaseStagedOutput.base_source_id]
    )

    __mapper_args__ = {
        "polymorphic_identity": ComponentType.CONTROL,
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    __table_args__ = (
        Index('ix_control_points_type', 'control_type'),
        Index('ix_control_points_status', 'control_status'),
        CheckConstraint(
            'check_count >= 0',
            name='ck_check_count_non_negative'
        ),
        CheckConstraint(
            'failure_count >= 0',
            name='ck_failure_count_non_negative'
        ),
        CheckConstraint(
            'decision_made_at IS NULL OR decision_made_at >= created_at',
            name='ck_decision_time_valid'
        ),
        {'extend_existing': True}
    )

    def evaluate_control(self, context: Dict[str, Any]) -> bool:
        """Evaluate control point against provided context."""
        self.check_count += 1
        self.last_check = datetime.utcnow()

        try:
            # Implementation would validate context against rules
            passed = True  # Placeholder for actual validation logic

            if not passed:
                self.failure_count += 1
                self.control_status = 'failed'
            else:
                self.control_status = 'passed'

            return passed

        except Exception as e:
            self.failure_count += 1
            self.control_status = 'failed'
            self.error_details = {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'context': context
            }
            return False

    def record_decision(
            self,
            decision: Dict[str, Any],
            user_id: UUID,
            rationale: Optional[str] = None
    ) -> None:
        """Record control point decision."""
        self.decision = decision
        self.decision_made_by = user_id
        self.decision_made_at = datetime.utcnow()
        self.decision_rationale = rationale