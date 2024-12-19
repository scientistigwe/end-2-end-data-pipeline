# models/analysis.py
from sqlalchemy import Column, String, DateTime, JSON, Enum, ForeignKey, Float, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class QualityCheck(BaseModel):
    __tablename__ = 'quality_checks'

    dataset_id = Column(UUID(as_uuid=True), ForeignKey('datasets.id'), nullable=False)
    pipeline_run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id'))
    type = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    config = Column(JSONB)
    status = Column(Enum('pending', 'running', 'completed', 'failed', name='check_status'))
    results = Column(JSONB)
    score = Column(Float)
    impact = Column(Enum('low', 'medium', 'high', 'critical', name='impact_level'))
    
    dataset = relationship('Dataset', back_populates='quality_checks')
    pipeline_run = relationship('PipelineRun', back_populates='quality_checks')
    validation_results = relationship('ValidationResult', back_populates='quality_check')

class InsightAnalysis(BaseModel):
    __tablename__ = 'insight_analyses'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id'), nullable=False)
    type = Column(String(100), nullable=False)
    status = Column(Enum('pending', 'running', 'completed', 'failed', name='analysis_status'))
    config = Column(JSONB)
    results = Column(JSONB)
    metrics = Column(JSONB)
    
    patterns = relationship('Pattern', back_populates='analysis')
    correlations = relationship('Correlation', back_populates='analysis')
    anomalies = relationship('Anomaly', back_populates='analysis')

class Pattern(BaseModel):
    __tablename__ = 'patterns'

    analysis_id = Column(UUID(as_uuid=True), ForeignKey('insight_analyses.id'), nullable=False)
    type = Column(String(100))
    name = Column(String(255))
    description = Column(Text)
    confidence = Column(Float)
    support = Column(Float)
    data = Column(JSONB)
    
    analysis = relationship('InsightAnalysis', back_populates='patterns')

class Correlation(BaseModel):
    __tablename__ = 'correlations'

    analysis_id = Column(UUID(as_uuid=True), ForeignKey('insight_analyses.id'), nullable=False)
    field_a = Column(String(255))
    field_b = Column(String(255))
    coefficient = Column(Float)
    significance = Column(Float)
    type = Column(String(100))
    metadata = Column(JSONB)
    
    analysis = relationship('InsightAnalysis', back_populates='correlations')

class Anomaly(BaseModel):
    __tablename__ = 'anomalies'

    analysis_id = Column(UUID(as_uuid=True), ForeignKey('insight_analyses.id'), nullable=False)
    field = Column(String(255))
    type = Column(String(100))
    severity = Column(Float)
    timestamp = Column(DateTime)
    value = Column(Float)
    expected_range = Column(JSONB)  # {min: number, max: number}
    metadata = Column(JSONB)
    
    analysis = relationship('InsightAnalysis', back_populates='anomalies')