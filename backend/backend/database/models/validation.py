# models/validation.py
from sqlalchemy import (
    Column, 
    String, 
    DateTime, 
    Enum, 
    ForeignKey, 
    Float, 
    Text, 
    Integer, 
    Boolean
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class ValidationResult(BaseModel):
    """Model for data validation results."""
    __tablename__ = 'validation_results'

    # Basic information
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    status = Column(Enum('passed', 'failed', 'warning', name='validation_status'))
    
    # Relationships
    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'))
    quality_check_id = Column(UUID(as_uuid=True), ForeignKey('quality_checks.id'))

    # Results
    results = Column(JSONB)  # Detailed validation results
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    error_details = Column(JSONB)
    impact_score = Column(Float)
    
    # Timestamps
    validated_at = Column(DateTime)
    expires_at = Column(DateTime)

    # Relationships
    source = relationship('DataSource', back_populates='validation_results')
    quality_check = relationship('QualityCheck', back_populates='validation_results')
    decisions = relationship('Decision', back_populates='validation_result')

    def __repr__(self):
        return f"<ValidationResult(name='{self.name}', status='{self.status}')>"