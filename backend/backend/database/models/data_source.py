from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Text, Boolean, Integer, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from .base import BaseModel

class DataSource(BaseModel):
    """Model for managing data sources and their configurations."""
    __tablename__ = 'data_sources'

    # Basic information
    name = Column(String(255), nullable=False)
    type = Column(
        Enum('file', 'database', 'api', 's3', 'stream', name='source_type'),
        nullable=False
    )
    status = Column(
        Enum('active', 'inactive', 'error', name='source_status'),
        default='active'
    )
    config = Column(JSONB, nullable=False)
    meta_data = Column(JSONB)
    last_sync = Column(DateTime)
    error = Column(Text)
    refresh_interval = Column(Integer)  # in seconds
    
    # Foreign Keys
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        index=True
    )
    
    # Relationships
    owner = relationship('User', back_populates='data_sources', foreign_keys=[owner_id])
    validation_results = relationship(
        'ValidationResult',
        back_populates='source',
        cascade='all, delete-orphan'
    )
    datasets = relationship(
        'Dataset',
        back_populates='source',
        cascade='all, delete-orphan'
    )
    insights = relationship(
        'InsightAnalysis',
        back_populates='source',
        cascade='all, delete-orphan'
    )
    pipelines_as_source = relationship(
        'Pipeline',
        foreign_keys='Pipeline.source_id',
        back_populates='source'
    )
    pipelines_as_target = relationship(
        'Pipeline',
        foreign_keys='Pipeline.target_id',
        back_populates='target'
    )
    tags = relationship(
        'Tag',
        secondary='datasource_tags',
        back_populates='data_sources'
    )

    # Config relationships with cascade
    api_config = relationship(
        'APISourceConfig',
        back_populates='source',
        uselist=False,
        cascade='all, delete-orphan'
    )
    db_config = relationship(
        'DatabaseSourceConfig',
        back_populates='source',
        uselist=False,
        cascade='all, delete-orphan'
    )
    s3_config = relationship(
        'S3SourceConfig',
        back_populates='source',
        uselist=False,
        cascade='all, delete-orphan'
    )
    stream_config = relationship(
        'StreamSourceConfig',
        back_populates='source',
        uselist=False,
        cascade='all, delete-orphan'
    )
    file_info = relationship(
        'FileSourceInfo',
        back_populates='source',
        uselist=False,
        cascade='all, delete-orphan'
    )

    # Indexes and Constraints
    __table_args__ = (
        Index('ix_data_sources_name_owner', 'name', 'owner_id', unique=True),
        Index('ix_data_sources_type_status', 'type', 'status'),
        {'extend_existing': True}
    )

    # Polymorphic Identity
    __mapper_args__ = {
        'polymorphic_identity': 'base',
        'polymorphic_on': type
    }

    @validates('config')
    def validate_config(self, key, config):
        """Validate config based on source type."""
        required_fields = {
            'file': ['file_path', 'file_type'],
            'database': ['connection_string', 'dialect'],
            'api': ['base_url', 'auth_type'],
            's3': ['bucket', 'region'],
            'stream': ['stream_type', 'endpoint']
        }
        
        if self.type in required_fields:
            missing = [
                field for field in required_fields[self.type] 
                if field not in config
            ]
            if missing:
                raise ValueError(f"Missing required config fields: {missing}")
        return config

    def __repr__(self):
        """String representation of DataSource."""
        return f"<DataSource(name='{self.name}', type='{self.type}', status='{self.status}')>"


class APISourceConfig(BaseModel):
    """Configuration model for API data sources."""
    __tablename__ = 'api_source_configs'

    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='CASCADE'),
        primary_key=True
    )
    auth_type = Column(String(50))  # basic, oauth, api_key
    auth_config = Column(JSONB)
    rate_limit = Column(Integer)
    timeout = Column(Integer)
    headers = Column(JSONB)
    retry_config = Column(JSONB)
    webhook_url = Column(String(255))
    webhook_secret = Column(String(255))
    
    source = relationship('DataSource', back_populates='api_config')

    def __repr__(self):
        return f"<APISourceConfig(source_id='{self.source_id}', auth_type='{self.auth_type}')>"


class DatabaseSourceConfig(BaseModel):
    """Configuration model for database data sources."""
    __tablename__ = 'database_source_configs'

    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='CASCADE'),
        primary_key=True
    )
    dialect = Column(String(50))  # postgresql, mysql, etc.
    schema = Column(String(100))
    ssl_config = Column(JSONB)
    pool_size = Column(Integer)
    max_overflow = Column(Integer)
    connection_timeout = Column(Integer)
    query_timeout = Column(Integer)
    
    source = relationship('DataSource', back_populates='db_config')

    def __repr__(self):
        return f"<DatabaseSourceConfig(source_id='{self.source_id}', dialect='{self.dialect}')>"


class S3SourceConfig(BaseModel):
    """Configuration model for S3 data sources."""
    __tablename__ = 's3_source_configs'

    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='CASCADE'),
        primary_key=True
    )
    bucket = Column(String(255))
    region = Column(String(50))
    prefix = Column(String(255))
    encryption_config = Column(JSONB)
    storage_class = Column(String(50))
    versioning_enabled = Column(Boolean)
    transfer_config = Column(JSONB)
    
    source = relationship('DataSource', back_populates='s3_config')

    def __repr__(self):
        return f"<S3SourceConfig(source_id='{self.source_id}', bucket='{self.bucket}')>"


class StreamSourceConfig(BaseModel):
    """Configuration model for streaming data sources."""
    __tablename__ = 'stream_source_configs'

    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='CASCADE'),
        primary_key=True
    )
    stream_type = Column(String(50))  # kafka, kinesis, etc.
    partitions = Column(Integer)
    batch_size = Column(Integer)
    processing_config = Column(JSONB)
    error_handling = Column(JSONB)
    checkpoint_config = Column(JSONB)
    scaling_config = Column(JSONB)
    
    source = relationship('DataSource', back_populates='stream_config')

    def __repr__(self):
        return f"<StreamSourceConfig(source_id='{self.source_id}', type='{self.stream_type}')>"


class FileSourceInfo(BaseModel):
    """Information model for file-based data sources."""
    __tablename__ = 'file_source_info'

    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='CASCADE'),
        primary_key=True
    )
    original_filename = Column(String(255))
    file_type = Column(String(50))
    mime_type = Column(String(100))
    size = Column(Integer)
    hash = Column(String(64))  # For integrity checking
    encoding = Column(String(50))
    delimiter = Column(String(10))  # For CSV files
    compression = Column(String(50))  # gzip, zip, etc.
    
    source = relationship('DataSource', back_populates='file_info')

    def __repr__(self):
        return f"<FileSourceInfo(source_id='{self.source_id}', filename='{self.original_filename}')>"


class SourceConnection(BaseModel):
    """Model for tracking data source connections."""
    __tablename__ = 'source_connections'

    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='CASCADE'),
        nullable=False
    )
    status = Column(
        Enum('connected', 'disconnected', 'error', name='connection_status'),
        default='disconnected'
    )
    connection_id = Column(String(255))  # External connection identifier
    connected_at = Column(DateTime)
    disconnected_at = Column(DateTime)
    error = Column(Text)
    metrics = Column(JSONB)  # Connection-specific metrics
    
    source = relationship('DataSource')

    def __repr__(self):
        return f"<SourceConnection(source_id='{self.source_id}', status='{self.status}')>"


class SourceSyncHistory(BaseModel):
    """Model for tracking data source synchronization history."""
    __tablename__ = 'source_sync_history'

    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='CASCADE'),
        nullable=False
    )
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(
        Enum('success', 'partial', 'failed', name='sync_status'),
        nullable=False
    )
    records_processed = Column(Integer)
    bytes_processed = Column(Integer)
    error = Column(Text)
    sync_meta = Column(JSONB)
    
    source = relationship('DataSource')

    def __repr__(self):
        return f"<SourceSyncHistory(source_id='{self.source_id}', status='{self.status}')>"