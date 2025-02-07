from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Text, Boolean,
    Integer, Index, UniqueConstraint, CheckConstraint, Float
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from ..core.base import BaseModel



class DataSource(BaseModel):
    """Base model for managing data sources and their configurations."""
    __tablename__ = 'data_sources'

    name = Column(String(255), nullable=False)
    type = Column(
        Enum('file', 'db', 'api', 's3', 'stream', name='source_type'),
        nullable=False
    )
    status = Column(
        Enum('active', 'inactive', 'error', name='source_status'),
        default='active'
    )

    # Configuration and metadata
    config = Column(JSONB, nullable=False)
    meta_data = Column(JSONB)
    refresh_interval = Column(Integer)  # seconds
    last_sync = Column(DateTime)
    error = Column(Text)

    # Owner reference
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        index=True
    )

    # Security and access control
    access_level = Column(
        Enum('public', 'private', 'shared', name='access_level'),
        default='private'
    )
    encryption_enabled = Column(Boolean, default=False)
    encryption_config = Column(JSONB)

    # Performance monitoring
    performance_metrics = Column(JSONB)
    health_status = Column(JSONB)
    connection_retries = Column(Integer, default=0)

    # Relationships - Configuration
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

    # Relationships - Pipelines
    pipelines_as_source = relationship(
        'Pipeline',
        foreign_keys='[Pipeline.pipeline_source_id]',
        back_populates='pipeline_source'
    )
    pipelines_as_target = relationship(
        'Pipeline',
        foreign_keys='[Pipeline.pipeline_target_id]',
        back_populates='pipeline_target'
    )

    # Staged output relationships
    insight_outputs = relationship(
        'StagedInsightOutput',
        back_populates='source',
        foreign_keys='[StagedInsightOutput.insight_source_id]',
        cascade='all, delete-orphan'
    )
    analytics_outputs = relationship(
        'StagedAnalyticsOutput',
        back_populates='source',
        foreign_keys='[StagedAnalyticsOutput.analytics_source_id]',
        cascade='all, delete-orphan'
    )
    quality_outputs = relationship(
        'StagedQualityOutput',
        back_populates='source',
        foreign_keys='[StagedQualityOutput.quality_source_id]',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_data_sources_name_owner', 'name', 'owner_id', unique=True),
        Index('ix_data_sources_type_status', 'type', 'status'),
        CheckConstraint(
            'refresh_interval > 0',
            name='ck_refresh_interval_positive'
        ),
        CheckConstraint(
            'connection_retries >= 0',
            name='ck_connection_retries_valid'
        )
    )

    __mapper_args__ = {
        'polymorphic_identity': 'base_source',
        'polymorphic_on': type,
        'with_polymorphic': '*'
    }

    def update_health_status(self, metrics: Dict[str, Any]) -> None:
        """Update source health status with new metrics."""
        self.health_status = {
            'last_check': datetime.utcnow().isoformat(),
            'status': 'healthy' if not self.error else 'error',
            'metrics': metrics,
            'error': str(self.error) if self.error else None
        }

    def increment_retry_count(self) -> None:
        """Increment connection retry count."""
        self.connection_retries += 1
        if self.connection_retries >= 5:
            self.status = 'error'
            self.error = 'Maximum retry attempts exceeded'


class APISourceConfig(BaseModel):
    """Configuration for API data sources."""
    __tablename__ = 'api_source_configs'

    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='CASCADE'),
        primary_key=True
    )
    auth_type = Column(String(50))
    auth_config = Column(JSONB)
    rate_limit = Column(Integer)
    timeout = Column(Integer)
    headers = Column(JSONB)
    retry_config = Column(JSONB)
    webhook_url = Column(String(255))
    webhook_secret = Column(String(255))

    # Advanced configuration
    pagination_config = Column(JSONB)
    response_mapping = Column(JSONB)
    error_mapping = Column(JSONB)
    transformation_rules = Column(JSONB)

    source = relationship('DataSource', back_populates='api_config')

    __table_args__ = (
        CheckConstraint(
            'rate_limit > 0',
            name='ck_rate_limit_positive'
        ),
        CheckConstraint(
            'timeout > 0',
            name='ck_timeout_positive'
        )
    )


class DatabaseSourceConfig(BaseModel):
    """Configuration for database data sources."""
    __tablename__ = 'database_source_configs'

    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='CASCADE'),
        primary_key=True
    )
    dialect = Column(String(50))
    schema = Column(String(100))
    ssl_config = Column(JSONB)

    # Connection pooling
    pool_size = Column(Integer)
    max_overflow = Column(Integer)
    pool_timeout = Column(Integer)
    pool_recycle = Column(Integer)

    # Query configuration
    connection_timeout = Column(Integer)
    query_timeout = Column(Integer)
    execution_options = Column(JSONB)

    # Advanced features
    replication_config = Column(JSONB)
    migration_config = Column(JSONB)
    backup_config = Column(JSONB)

    source = relationship('DataSource', back_populates='db_config')

    __table_args__ = (
        CheckConstraint(
            'pool_size > 0',
            name='ck_pool_size_positive'
        ),
        CheckConstraint(
            'max_overflow >= 0',
            name='ck_max_overflow_valid'
        ),
        CheckConstraint(
            'pool_timeout > 0',
            name='ck_pool_timeout_positive'
        ),
        CheckConstraint(
            'connection_timeout > 0',
            name='ck_connection_timeout_positive'
        )
    )


class S3SourceConfig(BaseModel):
    """Configuration for S3 data sources."""
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
    versioning_enabled = Column(Boolean, default=False)

    # Transfer configuration
    transfer_config = Column(JSONB)
    multipart_threshold = Column(Integer)
    max_concurrency = Column(Integer)
    multipart_chunksize = Column(Integer)

    # Advanced features
    lifecycle_rules = Column(JSONB)
    replication_config = Column(JSONB)
    notification_config = Column(JSONB)

    source = relationship('DataSource', back_populates='s3_config')

    __table_args__ = (
        CheckConstraint(
            'multipart_threshold > 0',
            name='ck_multipart_threshold_positive'
        ),
        CheckConstraint(
            'max_concurrency > 0',
            name='ck_max_concurrency_positive'
        ),
        CheckConstraint(
            'multipart_chunksize > 0',
            name='ck_multipart_chunksize_positive'
        )
    )


class StreamSourceConfig(BaseModel):
    """Configuration for streaming data sources."""
    __tablename__ = 'stream_source_configs'

    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey('data_sources.id', ondelete='CASCADE'),
        primary_key=True
    )
    stream_type = Column(String(50))
    partitions = Column(Integer)
    batch_size = Column(Integer)

    # Processing configuration
    processing_config = Column(JSONB)
    error_handling = Column(JSONB)
    checkpoint_config = Column(JSONB)

    # Performance configuration
    scaling_config = Column(JSONB)
    throughput_config = Column(JSONB)
    latency_targets = Column(JSONB)

    # Advanced features
    schema_registry_config = Column(JSONB)
    compression_config = Column(JSONB)
    monitoring_config = Column(JSONB)

    source = relationship('DataSource', back_populates='stream_config')

    __table_args__ = (
        CheckConstraint(
            'partitions > 0',
            name='ck_partitions_positive'
        ),
        CheckConstraint(
            'batch_size > 0',
            name='ck_batch_size_positive'
        )
    )


class FileSourceInfo(BaseModel):
    """Information for file-based data sources."""
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
    hash = Column(String(64))
    encoding = Column(String(50))
    delimiter = Column(String(10))
    compression = Column(String(50))

    # File structure information
    schema = Column(JSONB)
    column_mappings = Column(JSONB)
    validation_rules = Column(JSONB)
    transformation_rules = Column(JSONB)

    source = relationship('DataSource', back_populates='file_info')

    __table_args__ = (
        CheckConstraint(
            'size >= 0',
            name='ck_size_non_negative'
        ),
    )


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
    connection_id = Column(String(255))
    connected_at = Column(DateTime)
    disconnected_at = Column(DateTime)
    error = Column(Text)

    # Connection metrics
    metrics = Column(JSONB)
    latency = Column(Float)
    throughput = Column(Float)
    error_rate = Column(Float)

    source = relationship('DataSource')

    __table_args__ = (
        Index('ix_source_connections_status', 'status'),
        CheckConstraint(
            'latency >= 0',
            name='ck_latency_non_negative'
        ),
        CheckConstraint(
            'throughput >= 0',
            name='ck_throughput_non_negative'
        ),
        CheckConstraint(
            'error_rate >= 0 AND error_rate <= 1',
            name='ck_error_rate_range'
        )
    )


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

    # Sync metrics
    records_processed = Column(Integer)
    bytes_processed = Column(Integer)
    error = Column(Text)
    sync_meta = Column(JSONB)

    # Performance metrics
    duration = Column(Float)
    average_speed = Column(Float)
    resource_usage = Column(JSONB)

    source = relationship('DataSource')

    __table_args__ = (
        Index('ix_source_sync_history_source_time', 'source_id', 'start_time'),
        CheckConstraint(
            'records_processed >= 0',
            name='ck_records_processed_non_negative'
        ),
        CheckConstraint(
            'bytes_processed >= 0',
            name='ck_bytes_processed_non_negative'
        ),
        CheckConstraint(
            'duration >= 0',
            name='ck_duration_non_negative'
        ),
        CheckConstraint(
            'average_speed >= 0',
            name='ck_average_speed_non_negative'
        )
    )


class DatabaseDataSource(DataSource):
    """Database-specific data source implementation."""

    __mapper_args__ = {
        'polymorphic_identity': 'db'
    }

    def initialize_connection(self) -> None:
        """Initialize database connection using configuration."""
        if not self.db_config:
            raise ValueError("Database configuration is required")

        # Reset connection metrics
        self.connection_retries = 0
        self.error = None

        # Update health metrics
        self.update_health_status({
            'connection_pool_size': self.db_config.pool_size,
            'max_overflow': self.db_config.max_overflow,
            'dialect': self.db_config.dialect
        })

    def validate_schema(self) -> bool:
        """Validate database schema configuration."""
        if not self.db_config or not self.db_config.schema:
            return False
        return True


class APIDataSource(DataSource):
    """API-specific data source implementation."""

    __mapper_args__ = {
        'polymorphic_identity': 'api'
    }

    def configure_auth(self) -> None:
        """Configure API authentication."""
        if not self.api_config:
            raise ValueError("API configuration is required")

        # Reset connection state
        self.connection_retries = 0
        self.error = None

        # Update health metrics
        self.update_health_status({
            'auth_type': self.api_config.auth_type,
            'rate_limit': self.api_config.rate_limit,
            'timeout': self.api_config.timeout
        })

    def validate_endpoints(self) -> bool:
        """Validate API endpoint configuration."""
        if not self.api_config or not self.api_config.webhook_url:
            return False
        return True


class S3DataSource(DataSource):
    """S3-specific data source implementation."""

    __mapper_args__ = {
        'polymorphic_identity': 's3'
    }

    def configure_bucket(self) -> None:
        """Configure S3 bucket settings."""
        if not self.s3_config:
            raise ValueError("S3 configuration is required")

        # Reset connection state
        self.connection_retries = 0
        self.error = None

        # Update health metrics
        self.update_health_status({
            'bucket': self.s3_config.bucket,
            'region': self.s3_config.region,
            'storage_class': self.s3_config.storage_class
        })

    def validate_bucket_access(self) -> bool:
        """Validate S3 bucket access permissions."""
        if not self.s3_config or not self.s3_config.bucket:
            return False
        return True


class StreamDataSource(DataSource):
    """Stream-specific data source implementation."""

    __mapper_args__ = {
        'polymorphic_identity': 'stream'
    }

    def configure_stream(self) -> None:
        """Configure stream processing settings."""
        if not self.stream_config:
            raise ValueError("Stream configuration is required")

        # Reset connection state
        self.connection_retries = 0
        self.error = None

        # Update health metrics
        self.update_health_status({
            'stream_type': self.stream_config.stream_type,
            'partitions': self.stream_config.partitions,
            'batch_size': self.stream_config.batch_size
        })

    def validate_stream_config(self) -> bool:
        """Validate stream configuration."""
        if not self.stream_config or not self.stream_config.stream_type:
            return False
        return True


class FileDataSource(DataSource):
    """File-specific data source implementation."""

    __mapper_args__ = {
        'polymorphic_identity': 'file'
    }

    def process_file(self) -> None:
        """Process file data source."""
        if not self.file_info:
            raise ValueError("File information is required")

        # Reset processing state
        self.connection_retries = 0
        self.error = None

        # Update health metrics
        self.update_health_status({
            'file_type': self.file_info.file_type,
            'size': self.file_info.size,
            'encoding': self.file_info.encoding
        })

    def validate_file_metadata(self) -> bool:
        """Validate file metadata."""
        if not self.file_info or not self.file_info.original_filename:
            return False
        return True