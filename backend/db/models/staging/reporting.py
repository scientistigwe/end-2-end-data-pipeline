from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Float, Text,
    Integer, Index, CheckConstraint, Boolean
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseStagedOutput, ComponentType

class StagedReportOutput(BaseStagedOutput):
    """Model for managing comprehensive report generation and delivery."""
    __tablename__ = 'staged_report_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )

    # Add source_id column
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='SET NULL'),
        nullable=True
    )

    # Report identification
    report_type = Column(String(100), nullable=False)
    version = Column(String(50))
    report_format = Column(String(50))  # pdf, excel, html, etc.
    template_id = Column(UUID(as_uuid=True))

    # Content organization
    sections = Column(JSONB)
    table_of_contents = Column(JSONB)
    executive_summary = Column(Text)
    main_findings = Column(JSONB)
    recommendations = Column(JSONB)
    appendices = Column(JSONB)

    # Visual elements
    visualizations = Column(JSONB)
    charts_config = Column(JSONB)
    styling_config = Column(JSONB)
    branding_elements = Column(JSONB)

    # Generation settings
    auto_generation = Column(Boolean, default=False)
    schedule_config = Column(JSONB)
    retention_policy = Column(JSONB)
    access_control = Column(JSONB)

    # Distribution
    distribution_list = Column(JSONB)
    delivery_status = Column(String(50))
    notification_sent = Column(Boolean, default=False)
    access_log = Column(JSONB)

    # Source relationship
    report_source = relationship(
        "DataSource",
        back_populates="report_outputs",
        foreign_keys=[source_id],
        primaryjoin="DataSource.id == StagedReportOutput.source_id"
    )

    __mapper_args__ = {
        "polymorphic_identity": ComponentType.REPORT,
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    __table_args__ = (
        Index('ix_report_outputs_type', 'report_type'),
        Index('ix_report_outputs_delivery', 'delivery_status'),
        CheckConstraint(
            'version ~ \'^[0-9]+\.[0-9]+\.[0-9]+$\'',
            name='ck_version_format'
        ),
        {'extend_existing': True}
    )


class StagedMetricsOutput(BaseStagedOutput):
    """Model for managing metric reporting and KPI tracking."""
    __tablename__ = 'staged_metrics_outputs'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )

    # Add source_id column
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='SET NULL'),
        nullable=True
    )

    # Metric categorization
    category = Column(String(100), nullable=False)
    subcategory = Column(String(100))
    dimension = Column(String(100))
    time_period = Column(String(50))

    # Core metrics
    key_metrics = Column(JSONB)
    calculated_kpis = Column(JSONB)
    historical_trends = Column(JSONB)
    forecasted_values = Column(JSONB)

    # Performance tracking
    target_values = Column(JSONB)
    actual_values = Column(JSONB)
    variance_analysis = Column(JSONB)
    threshold_breaches = Column(JSONB)

    # Analysis components
    trend_analysis = Column(JSONB)
    seasonality_patterns = Column(JSONB)
    correlation_insights = Column(JSONB)
    anomaly_detection = Column(JSONB)

    # Visualization preferences
    chart_preferences = Column(JSONB)
    dashboard_layout = Column(JSONB)
    alert_configuration = Column(JSONB)
    notification_rules = Column(JSONB)

    # Source relationship
    metrics_source = relationship(
        "DataSource",
        back_populates="metrics_outputs",
        foreign_keys=[source_id],
        primaryjoin="DataSource.id == StagedMetricsOutput.source_id"
    )

    __mapper_args__ = {
        "polymorphic_identity": ComponentType.METRICS,
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    __table_args__ = (
        Index('ix_metrics_outputs_category', 'category'),
        Index('ix_metrics_outputs_period', 'time_period'),
        {'extend_existing': True}
    )


class StagedComplianceReport(BaseStagedOutput):
    """Model for managing compliance and regulatory reporting."""
    __tablename__ = 'staged_compliance_reports'

    base_id = Column(
        UUID(as_uuid=True),
        ForeignKey('staged_outputs.id'),
        primary_key=True
    )

    # Add source_id column
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='SET NULL'),
        nullable=True
    )

    # Compliance context
    regulation_type = Column(String(100), nullable=False)
    compliance_framework = Column(String(100))
    reporting_period = Column(String(50))
    jurisdiction = Column(String(100))

    # Assessment details
    compliance_status = Column(String(50))
    control_assessments = Column(JSONB)
    risk_assessments = Column(JSONB)
    gap_analysis = Column(JSONB)

    # Documentation
    evidence_collected = Column(JSONB)
    control_documentation = Column(JSONB)
    audit_trail = Column(JSONB)
    review_notes = Column(JSONB)

    # Findings and actions
    findings = Column(JSONB)
    violations = Column(JSONB)
    remediation_plans = Column(JSONB)
    action_items = Column(JSONB)

    # Review process
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    review_status = Column(String(50))
    reviewed_at = Column(DateTime)
    approval_chain = Column(JSONB)

    # Additional tracking
    submission_deadline = Column(DateTime)
    submission_status = Column(String(50))
    regulatory_responses = Column(JSONB)
    follow_up_actions = Column(JSONB)

    # Source relationship
    compliance_source = relationship(
        "DataSource",
        back_populates="compliance_outputs",
        foreign_keys=[source_id],
        primaryjoin="DataSource.id == StagedComplianceReport.source_id"
    )

    __mapper_args__ = {
        "polymorphic_identity": ComponentType.COMPLIANCE,
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    __table_args__ = (
        Index('ix_compliance_reports_type', 'regulation_type'),
        Index('ix_compliance_reports_status', 'compliance_status'),
        CheckConstraint(
            'reviewed_at IS NULL OR reviewed_at <= submission_deadline',
            name='ck_review_deadline_valid'
        ),
        {'extend_existing': True}
    )

    @property
    def is_overdue(self) -> bool:
        """Check if report is overdue for submission."""
        if not self.submission_deadline:
            return False
        return (
                datetime.utcnow() > self.submission_deadline and
                self.submission_status != 'submitted'
        )

    def validate_compliance(self) -> bool:
        """Validate compliance status based on assessments."""
        if not self.control_assessments:
            return False

        # Implementation would check control assessments against requirements
        # and update compliance_status accordingly
        return True