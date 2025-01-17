# backend/db/types/dataset.py
from sqlalchemy import (
    Column, String, DateTime, JSON, Enum, ForeignKey, Float, Text, 
    Integer, Boolean, CheckConstraint, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from .base import BaseModel
from .associations import dataset_tags, dataset_quality_checks
from datetime import datetime

class Dataset(BaseModel):
    """Model for managing datasets and their metadata."""
    __tablename__ = 'datasets'

    # Basic information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(100))
    format = Column(
        Enum('csv', 'json', 'parquet', 'avro', 'orc', name='dataset_format'),
        nullable=False
    )

    # Size information
    size = Column(Integer)  # in bytes
    row_count = Column(Integer)
    column_count = Column(Integer)
    compressed_size = Column(Integer)
    compression_ratio = Column(Float)

    # Schema and metadata
    schema = Column(JSONB)
    stats = Column(JSONB)
    data_profile = Column(JSONB)
    quality_score = Column(Float)
    dataset_meta = Column(JSONB)

    # Location and source
    location = Column(String(255))
    source_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('data_sources.id', name='fk_dataset_source'),
        index=True
    )
    status = Column(
        Enum('active', 'archived', 'deleted', name='dataset_status'),
        default='active',
        nullable=False
    )

    # Access control
    owner_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id', name='fk_dataset_owner'),
        nullable=False,
        index=True
    )
    is_public = Column(Boolean, default=False)
    access_level = Column(
        Enum('read', 'write', 'admin', name='dataset_access_level'),
        default='read'
    )
    
    # Time tracking
    last_modified_at = Column(DateTime)
    last_accessed_at = Column(DateTime)
    expiry_date = Column(DateTime)
    retention_period = Column(Integer)

    # Performance metrics
    avg_query_time = Column(Float)
    peak_memory_usage = Column(Float)
    cache_hit_ratio = Column(Float)
    
    # Relationships
    source = relationship('DataSource', back_populates='datasets')
    quality_checks = relationship(
        'QualityCheck',
        secondary=dataset_quality_checks,
        back_populates='datasets',
        cascade='all, delete'
    )
    pipelines = relationship(
        'Pipeline',
        back_populates='dataset',
        cascade='all, delete-orphan'
    )
    tags = relationship(
        'Tag',
        secondary=dataset_tags,
        back_populates='datasets'
    )

    # Rest of your existing methods and constraints remain the same
    __table_args__ = (
        Index('ix_datasets_name_owner', 'name', 'owner_id', unique=True),
        Index('ix_datasets_type_format', 'type', 'format'),
        Index('ix_datasets_status', 'status'),
        CheckConstraint('size >= 0', name='ck_dataset_size_positive'),
        CheckConstraint('row_count >= 0', name='ck_dataset_row_count_positive'),
        CheckConstraint('column_count >= 0', name='ck_dataset_column_count_positive'),
        CheckConstraint('quality_score >= 0 AND quality_score <= 1', name='ck_dataset_quality_score_range'),
        CheckConstraint('retention_period > 0', name='ck_dataset_retention_period_positive'),
        CheckConstraint(
            'last_modified_at IS NULL OR last_modified_at <= CURRENT_TIMESTAMP',
            name='ck_dataset_last_modified_valid'
        ),
        CheckConstraint(
            'expiry_date IS NULL OR expiry_date > created_at',
            name='ck_dataset_expiry_valid'
        ),
        {'extend_existing': True}
    )