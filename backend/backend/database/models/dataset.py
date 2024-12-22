# models/dataset.py
from sqlalchemy import (
    Column, 
    String, 
    DateTime, 
    JSON, 
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

class Dataset(BaseModel):
    """Model for managing datasets."""
    __tablename__ = 'datasets'

    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(100))
    format = Column(String(50))  # csv, json, parquet, etc.
    size = Column(Integer)  # in bytes
    row_count = Column(Integer)
    column_count = Column(Integer)
    schema = Column(JSONB)  # column definitions
    stats = Column(JSONB)  # basic statistics
    location = Column(String(255))  # file path or URL
    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'))
    status = Column(Enum('active', 'archived', 'deleted', name='dataset_status'))

    # Relationships
    source = relationship('DataSource', back_populates='datasets')
    quality_checks = relationship('QualityCheck', back_populates='dataset')

    def __repr__(self):
        return f"<Dataset(name='{self.name}', type='{self.type}')>"