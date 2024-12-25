# backend\backend\database\models\analysis.py
from sqlalchemy import (
    Column, 
    String, 
    DateTime, 
    Enum, 
    ForeignKey, 
    Float, 
    Text, 
    Integer,
    Index,
    CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel
from datetime import datetime

class InsightAnalysis(BaseModel):
    """Model for storing and managing data analysis insights."""
    __tablename__ = 'insight_analysis'

    # Basic information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    analysis_type = Column(String(100), nullable=False)
    source_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('data_sources.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Analysis data
    results = Column(JSONB)
    insight_meta = Column(JSONB)
    status = Column(
        Enum('pending', 'running', 'completed', 'failed', name='analysis_status'),
        nullable=False,
        default='pending'
    )
    
    # Execution tracking
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    execution_time = Column(Float)  # in seconds
    
    # Relationships
    source = relationship('DataSource', back_populates='insights')
    patterns = relationship(
        'Pattern',
        back_populates='analysis',
        cascade='all, delete-orphan'
    )
    correlations = relationship(
        'Correlation',
        back_populates='analysis',
        cascade='all, delete-orphan'
    )
    anomalies = relationship(
        'Anomaly',
        back_populates='analysis',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_insight_analysis_status', 'status'),
        Index('ix_insight_analysis_type', 'analysis_type'),
        CheckConstraint('execution_time >= 0', name='ck_positive_execution_time'),
        CheckConstraint(
            'completed_at IS NULL OR completed_at >= started_at',
            name='ck_valid_completion_time'
        ),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<InsightAnalysis(name='{self.name}', type='{self.analysis_type}')>"


class Pattern(BaseModel):
    """Model for storing identified patterns in data analysis."""
    __tablename__ = 'patterns'

    analysis_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('insight_analysis.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    pattern_type = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    pattern_data = Column(JSONB)
    pattern_meta = Column(JSONB)
    
    # Additional fields
    frequency = Column(Integer)  # Number of occurrences
    impact_score = Column(Float)  # Measure of pattern significance
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    # Relationships
    analysis = relationship('InsightAnalysis', back_populates='patterns')

    __table_args__ = (
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='ck_valid_confidence'),
        CheckConstraint('impact_score >= 0', name='ck_positive_impact_score'),
        CheckConstraint(
            'end_date IS NULL OR end_date >= start_date',
            name='ck_valid_pattern_dates'
        )
    )

    def __repr__(self):
        return f"<Pattern(type='{self.pattern_type}', confidence={self.confidence})>"


class Correlation(BaseModel):
    """Model for storing correlations between data elements."""
    __tablename__ = 'correlations'

    analysis_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('insight_analysis.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    variable_x = Column(String(255), nullable=False)
    variable_y = Column(String(255), nullable=False)
    correlation_type = Column(String(100), nullable=False)
    strength = Column(Float, nullable=False)
    significance = Column(Float, nullable=False)
    correlation_data = Column(JSONB)
    correlation_meta = Column(JSONB)
    
    # Additional fields
    direction = Column(
        Enum('positive', 'negative', 'none', name='correlation_direction'),
        nullable=False
    )
    sample_size = Column(Integer)
    time_period = Column(String(50))  # e.g., 'daily', 'weekly', 'monthly'
    
    # Relationships
    analysis = relationship('InsightAnalysis', back_populates='correlations')

    __table_args__ = (
        CheckConstraint('strength >= -1 AND strength <= 1', name='ck_valid_correlation_strength'),
        CheckConstraint('significance >= 0 AND significance <= 1', name='ck_valid_significance'),
        CheckConstraint('sample_size > 0', name='ck_positive_sample_size'),
        Index('ix_correlations_vars', 'variable_x', 'variable_y'),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<Correlation(vars='{self.variable_x}->{self.variable_y}', strength={self.strength})>"


class Anomaly(BaseModel):
    """Model for storing detected anomalies in data."""
    __tablename__ = 'anomalies'

    analysis_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('insight_analysis.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    anomaly_type = Column(String(100), nullable=False)
    severity = Column(
        Enum('low', 'medium', 'high', 'critical', name='anomaly_severity'),
        nullable=False
    )
    confidence = Column(Float, nullable=False)
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    anomaly_data = Column(JSONB)
    anomaly_meta = Column(JSONB)
    
    # Additional fields
    resolution_status = Column(
        Enum('open', 'investigating', 'resolved', 'false_positive', name='resolution_status'),
        default='open'
    )
    resolved_at = Column(DateTime)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    resolution_notes = Column(Text)
    affected_metrics = Column(JSONB)
    
    # Relationships
    analysis = relationship('InsightAnalysis', back_populates='anomalies')
    resolver = relationship('User', foreign_keys=[resolved_by])

    __table_args__ = (
        CheckConstraint('confidence >= 0 AND confidence <= 1', name='ck_valid_anomaly_confidence'),
        CheckConstraint(
            'resolved_at IS NULL OR resolved_at >= detected_at',
            name='ck_valid_resolution_time'
        ),
        Index('ix_anomalies_severity', 'severity'),
        Index('ix_anomalies_resolution', 'resolution_status'),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<Anomaly(type='{self.anomaly_type}', severity='{self.severity}')>"