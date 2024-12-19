# models/data_source.py
from sqlalchemy import Column, String, DateTime, JSON, Enum, ForeignKey, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from .base import BaseModel

class DataSource(BaseModel):
    __tablename__ = 'data_sources'

    name = Column(String(255), nullable=False)
    type = Column(Enum('file', 'database', 'api', 's3', 'stream', name='source_type'), nullable=False)
    status = Column(Enum('active', 'inactive', 'error', name='source_status'))
    config = Column(JSONB, nullable=False)
    metadata = Column(JSONB)
    last_sync = Column(DateTime)
    error = Column(Text)
    refresh_interval = Column(Integer)  # in seconds
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    owner = relationship('User', back_populates='data_sources')
    
    # Relationships
    validation_results = relationship('ValidationResult', back_populates='source')
    datasets = relationship('Dataset', back_populates='source')
    api_config = relationship('APISourceConfig', back_populates='source', uselist=False)
    db_config = relationship('DatabaseSourceConfig', back_populates='source', uselist=False)
    s3_config = relationship('S3SourceConfig', back_populates='source', uselist=False)
    stream_config = relationship('StreamSourceConfig', back_populates='source', uselist=False)
    file_info = relationship('FileSourceInfo', back_populates='source', uselist=False)

    __mapper_args__ = {
        'polymorphic_identity': 'base',
        'polymorphic_on': type
    }

    @validates('config')
    def validate_config(self, key, config):
        required_fields = {
            'file': ['file_path', 'file_type'],
            'database': ['connection_string', 'dialect'],
            'api': ['base_url', 'auth_type'],
            's3': ['bucket', 'region'],
            'stream': ['stream_type', 'endpoint']
        }
        
        if self.type in required_fields:
            missing = [field for field in required_fields[self.type] 
                      if field not in config]
            if missing:
                raise ValueError(f"Missing required config fields: {missing}")
        return config

# Source-specific configuration models
class APISourceConfig(BaseModel):
    __tablename__ = 'api_source_configs'

    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'), primary_key=True)
    auth_type = Column(String(50))  # basic, oauth, api_key
    auth_config = Column(JSONB)
    rate_limit = Column(Integer)
    timeout = Column(Integer)
    headers = Column(JSONB)
    retry_config = Column(JSONB)
    webhook_url = Column(String(255))
    webhook_secret = Column(String(255))
    
    source = relationship('DataSource', back_populates='api_config')

class DatabaseSourceConfig(BaseModel):
    __tablename__ = 'database_source_configs'

    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'), primary_key=True)
    dialect = Column(String(50))  # postgresql, mysql, etc.
    schema = Column(String(100))
    ssl_config = Column(JSONB)
    pool_size = Column(Integer)
    max_overflow = Column(Integer)
    connection_timeout = Column(Integer)
    query_timeout = Column(Integer)
    
    source = relationship('DataSource', back_populates='db_config')

class S3SourceConfig(BaseModel):
    __tablename__ = 's3_source_configs'

    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'), primary_key=True)
    bucket = Column(String(255))
    region = Column(String(50))
    prefix = Column(String(255))
    encryption_config = Column(JSONB)
    storage_class = Column(String(50))
    versioning_enabled = Column(Boolean)
    transfer_config = Column(JSONB)
    
    source = relationship('DataSource', back_populates='s3_config')

class StreamSourceConfig(BaseModel):
    __tablename__ = 'stream_source_configs'

    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'), primary_key=True)
    stream_type = Column(String(50))  # kafka, kinesis, etc.
    partitions = Column(Integer)
    batch_size = Column(Integer)
    processing_config = Column(JSONB)
    error_handling = Column(JSONB)
    checkpoint_config = Column(JSONB)
    scaling_config = Column(JSONB)
    
    source = relationship('DataSource', back_populates='stream_config')

class FileSourceInfo(BaseModel):
    __tablename__ = 'file_source_info'

    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'), primary_key=True)
    original_filename = Column(String(255))
    file_type = Column(String(50))
    mime_type = Column(String(100))
    size = Column(Integer)
    hash = Column(String(64))  # For integrity checking
    encoding = Column(String(50))
    delimiter = Column(String(10))  # For CSV files
    compression = Column(String(50))  # gzip, zip, etc.
    
    source = relationship('DataSource', back_populates='file_info')

# Add connection tracking
class SourceConnection(BaseModel):
    __tablename__ = 'source_connections'

    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'), nullable=False)
    status = Column(Enum('connected', 'disconnected', 'error', name='connection_status'))
    connection_id = Column(String(255))  # External connection identifier
    connected_at = Column(DateTime)
    disconnected_at = Column(DateTime)
    error = Column(Text)
    metrics = Column(JSONB)  # Connection-specific metrics
    
    source = relationship('DataSource')

# Add sync history
class SourceSyncHistory(BaseModel):
    __tablename__ = 'source_sync_history'

    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(Enum('success', 'partial', 'failed', name='sync_status'))
    records_processed = Column(Integer)
    bytes_processed = Column(Integer)
    error = Column(Text)
    metadata = Column(JSONB)
    
    source = relationship('DataSource')