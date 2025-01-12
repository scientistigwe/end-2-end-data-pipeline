from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Float, Text, Integer, Boolean, CheckConstraint,
    Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .base import BaseModel

class ValidationRule(BaseModel):
    """Model for validation rules and criteria."""
    __tablename__ = 'validation_rules'

    name = Column(String(255), nullable=False)
    description = Column(Text)
    rule_type = Column(
        Enum('data_quality', 'business_logic', 'compliance', 'custom', name='rule_type'),
        nullable=False
    )
    status = Column(
        Enum('active', 'inactive', 'deprecated', name='rule_status'),
        default='active'
    )
    criteria = Column(JSONB, nullable=False)  # Rule validation criteria
    parameters = Column(JSONB)  # Rule parameters
    severity = Column(
        Enum('low', 'medium', 'high', 'critical', name='severity_level'),
        default='medium'
    )
    category = Column(String(100))
    tags = Column(JSONB)
    version = Column(String(50))
    active_from = Column(DateTime)
    active_until = Column(DateTime)

    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    last_modified_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))

    quality_checks = relationship('QualityCheck', back_populates='rule', cascade='all, delete-orphan')

    __table_args__ = (
        Index('ix_validation_rules_type_status', 'rule_type', 'status'),
        CheckConstraint(
            'active_until IS NULL OR active_until > active_from',
            name='ck_rule_active_period'
        )
    )


class QualityCheck(BaseModel):
    """Model for quality check configurations."""
    __tablename__ = 'quality_checks'

    name = Column(String(255), nullable=False)
    description = Column(Text)
    check_type = Column(String(100), nullable=False)

    rule_id = Column(
        UUID(as_uuid=True),
        ForeignKey('validation_rules.id', ondelete='CASCADE'),
        nullable=False
    )
    configuration = Column(JSONB)
    schedule = Column(JSONB)
    is_active = Column(Boolean, default=True)

    error_threshold = Column(Float)
    warning_threshold = Column(Float)
    timeout_seconds = Column(Integer, default=3600)

    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    priority = Column(
        Enum('low', 'medium', 'high', name='check_priority'),
        default='medium'
    )
    tags = Column(JSONB)

    rule = relationship('ValidationRule', back_populates='quality_checks')

    validation_results = relationship(
        'ValidationResult',
        back_populates='quality_check',
        cascade='all, delete-orphan'
    )

    pipeline_run = relationship(
        'PipelineRun',
        back_populates='quality_checks'
    )

    pipeline_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey('pipeline_runs.id', ondelete='CASCADE'),
        index=True
    )

    datasets = relationship(
        'Dataset',
        secondary='dataset_quality_checks',
        back_populates='quality_checks'
    )

    quality_profile_checks = relationship(
        'QualityProfileChecks',
        back_populates='quality_check'
    )

    profiles = relationship(
        'QualityProfile',
        secondary='quality_profile_checks',
        back_populates='quality_checks'
    )

    __table_args__ = (
        Index('ix_quality_checks_rule', 'rule_id'),
        CheckConstraint(
            'error_threshold >= 0 AND error_threshold <= 1',
            name='ck_error_threshold'
        ),
        CheckConstraint(
            'warning_threshold >= 0 AND warning_threshold <= 1',
            name='ck_warning_threshold'
        ),
        CheckConstraint('timeout_seconds > 0', name='ck_timeout')
    )


class ValidationResult(BaseModel):
    """Model for validation results."""
    __tablename__ = 'validation_results'

    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    status = Column(
        Enum('passed', 'failed', 'warning', 'error', name='validation_status'),
        nullable=False
    )

    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'))
    quality_check_id = Column(
        UUID(as_uuid=True),
        ForeignKey('quality_checks.id'),
        nullable=False
    )
    executed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    results = Column(JSONB)
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    error_details = Column(JSONB)
    row_count = Column(Integer)
    processed_count = Column(Integer)
    failed_count = Column(Integer, default=0)
    success_rate = Column(Float)
    impact_score = Column(Float)

    execution_time = Column(Float)  # seconds
    memory_usage = Column(Float)  # MB

    validated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    environment = Column(String(50))
    version = Column(String(50))
    validation_meta = Column(JSONB)

    source = relationship('DataSource', back_populates='validation_results')
    quality_check = relationship('QualityCheck', back_populates='validation_results')
    decision = relationship('Decision', back_populates='validation_result', uselist=False)

    remediation_actions = relationship(
        'RemediationAction',
        back_populates='validation_result',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_validation_results_status', 'status'),
        CheckConstraint('error_count >= 0', name='ck_error_count'),
        CheckConstraint('warning_count >= 0', name='ck_warning_count'),
        CheckConstraint(
            'success_rate >= 0 AND success_rate <= 1',
            name='ck_success_rate'
        ),
        CheckConstraint('execution_time >= 0', name='ck_execution_time'),
        CheckConstraint('memory_usage >= 0', name='ck_memory_usage')
    )


class QualityProfile(BaseModel):
    """Model for defining quality profiles and standards."""
    __tablename__ = 'quality_profiles'

    name = Column(String(255), nullable=False)
    description = Column(Text)
    rules = Column(JSONB, nullable=False)
    quality_profile_metadata = Column(JSONB)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    quality_checks = relationship(
        'QualityCheck',
        secondary='quality_profile_checks',
        back_populates='profiles'
    )

    quality_profile_checks = relationship(
        'QualityProfileChecks',
        back_populates='quality_profile'
    )

    __table_args__ = (
        UniqueConstraint('name', name='uq_quality_profile_name'),
        Index('ix_quality_profiles_active', 'is_active'),
        {'extend_existing': True}
    )


class RemediationAction(BaseModel):
    """Model for remediation actions."""
    __tablename__ = 'remediation_actions'

    validation_result_id = Column(
        UUID(as_uuid=True),
        ForeignKey('validation_results.id', ondelete='CASCADE'),
        nullable=False
    )
    type = Column(String(100), nullable=False)
    status = Column(
        Enum('pending', 'in_progress', 'completed', 'failed', name='remediation_status'),
        default='pending'
    )

    description = Column(Text)
    action_taken = Column(Text)
    priority = Column(
        Enum('low', 'medium', 'high', 'critical', name='action_priority'),
        default='medium'
    )

    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    result = Column(JSONB)

    validation_result = relationship('ValidationResult', back_populates='remediation_actions')

    __table_args__ = (
        Index('ix_remediation_actions_status', 'status'),
        CheckConstraint(
            'completed_at IS NULL OR completed_at >= started_at',
            name='ck_completion_time'
        )
    )


class QualityRule:
    def __init__(self, id: str, description: str, threshold: float):
        self.id = id
        self.description = description
        self.threshold = threshold

    def evaluate(self, score: float) -> bool:
        """
        Evaluate whether the score meets the quality threshold.
        """
        return score >= self.threshold

    def __repr__(self):
        return f"QualityRule(id='{self.id}', description='{self.description}', threshold={self.threshold})"

class QualityMetric:
    def __init__(self, id: str, description: str, calculation_func: callable):
        self.id = id
        self.description = description
        self.calculation_func = calculation_func

    def calculate(self, data) -> float:
        """
        Calculate the metric score based on the provided data.
        """
        return self.calculation_func(data)

    def __repr__(self):
        return f"QualityMetric(id='{self.id}', description='{self.description}')"


class QualityProfileChecks(BaseModel):
    __tablename__ = 'quality_profile_checks'
    id = Column(Integer, primary_key=True)
    quality_profile_id = Column(Integer, ForeignKey('quality_profiles.id'), nullable=False)
    quality_check_id = Column(Integer, ForeignKey('quality_checks.id'), nullable=False)

    quality_profile = relationship('QualityProfile', back_populates='quality_profile_checks')
    quality_check = relationship('QualityCheck', back_populates='quality_profile_checks')