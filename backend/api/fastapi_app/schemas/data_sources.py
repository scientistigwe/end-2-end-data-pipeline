# backend/api/fastapi_app/schemas/data_sources.py

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, model_validator, validator, AnyUrl, constr, ConfigDict
from enum import Enum
from typing import Literal, Union
import logging

logger = logging.getLogger(__name__)

class DataSourceType(str, Enum):
    """Enum for different types of data sources"""
    FILE = "file"
    DATABASE = "db"
    S3 = "s3"
    API = "api"
    STREAM = "stream"

# API Source Schemas
class AuthType(str, Enum):
    BASIC = "basic"
    OAUTH = "oauth"
    API_KEY = "api_key"
    BEARER = "bearer"


class StagingResponseSchema(BaseModel):
    """Base response schema maintained for compatibility"""
    model_config = ConfigDict(from_attributes=True)


class StagingRequestSchema(BaseModel):
    """Base request schema maintained for compatibility"""
    model_config = ConfigDict(
        from_attributes=True,  # This replaces orm_mode=True
    )


class DatabaseDialect(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    MSSQL = "mssql"
    SQLITE = "sqlite"


class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"


# API Source Schemas
class APISourceConfigSchema(BaseModel):
    """Schema for API source configuration"""
    base_url: AnyUrl
    auth_type: AuthType
    auth_config: Dict[str, Any]
    headers: Dict[str, str] = Field(default_factory=dict)
    rate_limit: Optional[int]
    timeout: int = 30
    retry_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_attempts": 3,
            "backoff_factor": 1.5,
            "max_delay": 60
        }
    )
    webhook_url: Optional[str]
    webhook_secret: Optional[str]

    @model_validator(mode='after')
    def validate_auth_config(self) -> 'APISourceConfigSchema':
        required_fields = {
            AuthType.BASIC: ['username', 'password'],
            AuthType.OAUTH: ['client_id', 'client_secret'],
            AuthType.API_KEY: ['key', 'header_name'],
            AuthType.BEARER: ['token']
        }

        if self.auth_type in required_fields:
            for field in required_fields[self.auth_type]:
                if field not in self.auth_config:
                    raise ValueError(f'{field} required for {self.auth_type} authentication')
        return self

    model_config = ConfigDict(from_attributes=True)


class APISourceRequestSchema(StagingRequestSchema):
    base_url: AnyUrl
    auth_type: AuthType
    auth_config: Dict[str, Any]
    headers: Dict[str, str] = Field(default_factory=dict)
    rate_limit: Optional[int]
    timeout: int = 30
    retry_config: Dict[str, Any] = Field(default_factory=dict)
    webhook_url: Optional[str]
    webhook_secret: Optional[str]
    config: APISourceConfigSchema
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list)
    enabled: bool = True

    @model_validator(mode='after')
    def validate_auth_config(self) -> 'APISourceRequestSchema':
        required_fields = {
            AuthType.BASIC: ['username', 'password'],
            AuthType.OAUTH: ['client_id', 'client_secret'],
            AuthType.API_KEY: ['key', 'header_name'],
            AuthType.BEARER: ['token']
        }

        if self.auth_type in required_fields:
            for field in required_fields[self.auth_type]:
                if field not in self.auth_config:
                    raise ValueError(f'{field} required for {self.auth_type} authentication')
        return self


class APISourceResponseSchema(StagingResponseSchema):
    connection_status: str = Field(..., pattern='^(connected|disconnected|error)$')
    response_time: int
    last_successful_request: Optional[datetime]
    error_rate: float = Field(..., ge=0, le=1)
    rate_limit_remaining: Optional[int]


class APIUploadRequestSchema(StagingRequestSchema):
    endpoint: str
    method: HTTPMethod
    headers: Dict[str, str] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    stream: bool = False


class APIUploadResponseSchema(StagingResponseSchema):
    response_code: int
    response_headers: Dict[str, str]
    data_size: int
    processing_time: float


class APIMetadataResponseSchema(StagingResponseSchema):
    endpoint_info: Dict[str, Any]
    rate_limits: Dict[str, Any]
    data_format: str
    schema: Dict[str, Any]
    preview_data: List[Dict[str, Any]]


# Database Source Schemas
class DatabaseSourceRequestSchema(StagingRequestSchema):
    dialect: DatabaseDialect
    host: str
    port: int
    database: str
    username: str
    password: str = Field(..., exclude=True)
    schema: Optional[str]
    ssl_config: Dict[str, Any] = Field(default_factory=dict)
    pool_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "pool_size": 5,
            "max_overflow": 10
        }
    )
    timeout_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "connect_timeout": 30,
            "query_timeout": 60
        }
    )

    @validator('port')
    def validate_port_ranges(cls, v, values):
        port_ranges = {
            DatabaseDialect.POSTGRESQL: 5432,
            DatabaseDialect.MYSQL: 3306,
            DatabaseDialect.ORACLE: 1521,
            DatabaseDialect.MSSQL: 1433
        }
        dialect = values.get('dialect')
        if dialect in port_ranges and v != port_ranges[dialect]:
            raise ValueError(f"Non-standard port for {dialect}")
        return v


class DatabaseSourceResponseSchema(StagingResponseSchema):
    connection_status: str = Field(..., pattern='^(connected|disconnected|error)$')
    available_tables: List[str]
    connection_pool_status: Dict[str, Any]
    query_performance_metrics: Dict[str, Any]
    last_successful_connection: Optional[datetime]


class DBUploadRequestSchema(StagingRequestSchema):
    query: str
    params: Dict[str, Any] = Field(default_factory=dict)
    chunk_size: Optional[int]
    transaction: bool = False


class DBUploadResponseSchema(StagingResponseSchema):
    rows_affected: int
    execution_time: float
    transaction_id: str


class DBMetadataResponseSchema(StagingResponseSchema):
    table_schema: Dict[str, Any]
    column_types: Dict[str, str]
    row_count: int
    indices: List[Dict[str, Any]]
    preview_data: List[Dict[str, Any]]


# File Source Schemas
class FileUploadRequestSchema(StagingRequestSchema):
    filename: str
    content_type: str
    chunk_number: int
    total_chunks: int
    chunk_size: int
    total_size: int
    identifier: str


class FileUploadResponseSchema(StagingResponseSchema):
    status: str = Field(..., pattern='^(success|error|in_progress)$')
    staged_id: str
    control_point_id: str
    tracking_url: str
    upload_status: Optional[str] = Field(None, pattern='^(in_progress|completed|failed)$')
    error: Optional[str]
    message: Optional[str]


class FileSourceRequestSchema(StagingRequestSchema):
    original_filename: str
    file_type: str = Field(..., pattern='^(csv|json|xlsx|parquet|xml)$')
    mime_type: str
    encoding: str = 'utf-8'
    delimiter: Optional[str]
    compression: Optional[str] = Field(None, pattern='^(gzip|zip|bzip2)$')
    chunk_size: int = 1000
    checksum: Optional[str]
    max_file_size: Optional[int]
    allowed_extensions: List[str] = Field(default_factory=list)


class FileSourceResponseSchema(StagingResponseSchema):
    storage_location: str
    file_size: int
    row_count: Optional[int]
    column_count: Optional[int]
    detected_encoding: str
    preview_data: List[Dict[str, Any]]
    processing_metrics: Dict[str, Any]


class FileMetadataResponseSchema(StagingResponseSchema):
    metadata: Dict[str, Any]
    file_size: int
    mime_type: str
    created_at: datetime
    modified_at: datetime
    checksum: str
    encoding: str
    line_count: int
    headers: List[str]
    sheet_names: List[str]
    preview_data: List[Dict[str, Any]]
    processing_status: str = Field(..., pattern='^(pending|processing|completed|failed)$')


# S3 Source Schemas
class S3SourceConfigSchema(BaseModel):
    """Schema for S3 source configuration"""
    bucket: constr(min_length=3, max_length=63)
    region: str
    prefix: Optional[str]
    access_key: str = Field(..., exclude=True)
    secret_key: str = Field(..., exclude=True)
    session_token: Optional[str] = Field(None, exclude=True)
    encryption_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "algorithm": "AES256",
            "kms_key_id": None
        }
    )
    storage_class: str = Field(..., pattern='^(STANDARD|STANDARD_IA|ONEZONE_IA|GLACIER|DEEP_ARCHIVE)$')
    transfer_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "multipart_threshold": 8388608,  # 8MB
            "max_concurrency": 10,
            "multipart_chunksize": 8388608,
            "use_threads": True
        }
    )
    versioning_enabled: bool = False
    lifecycle_rules: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_s3_config(self) -> 'S3SourceConfigSchema':
        # Validate bucket name according to AWS rules
        if not self.bucket.islower() or not self.bucket.isalnum():
            raise ValueError("Bucket name must be lowercase alphanumeric")

        # Validate region format
        if not self.region.startswith('us-') and not self.region.startswith('eu-'):
            raise ValueError("Invalid AWS region format")

        # Validate encryption config
        if self.encryption_config.get('algorithm') not in ['AES256', 'aws:kms']:
            raise ValueError("Invalid encryption algorithm")

        return self

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "bucket": "my-data-bucket",
                "region": "us-east-1",
                "prefix": "data/",
                "access_key": "AKIAXXXXXXXXXXXXXXXX",
                "secret_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "storage_class": "STANDARD"
            }
        }
    )

class S3SourceRequestSchema(StagingRequestSchema):
    bucket: constr(min_length=3, max_length=63)
    region: str
    prefix: Optional[str]
    access_key: str = Field(..., exclude=True)
    secret_key: str = Field(..., exclude=True)
    session_token: Optional[str] = Field(None, exclude=True)
    encryption_config: Dict[str, Any] = Field(default_factory=dict)
    storage_class: str = Field(..., pattern='^(STANDARD|STANDARD_IA|ONEZONE_IA|GLACIER|DEEP_ARCHIVE)$')
    config: S3SourceConfigSchema
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list)
    enabled: bool = True
    transfer_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "multipart_threshold": 8388608,
            "max_concurrency": 10,
            "multipart_chunksize": 8388608,
            "use_threads": True
        }
    )
    versioning_enabled: bool = False
    lifecycle_rules: List[Dict[str, Any]] = Field(default_factory=list)


class S3SourceResponseSchema(StagingResponseSchema):
    connection_status: str = Field(..., pattern='^(connected|disconnected|error)$')
    total_objects: int
    total_size: int
    bucket_metrics: Dict[str, Any]
    last_sync: Optional[datetime]
    versioning_status: str = Field(..., pattern='^(Enabled|Suspended|Disabled)$')
    replication_status: Dict[str, Any]
    transfer_stats: Dict[str, Any]


class S3UploadRequestSchema(StagingRequestSchema):
    bucket: str
    key: str
    content_type: str
    chunk_number: int
    total_chunks: int
    part_size: int
    total_size: int
    upload_id: Optional[str]


class S3UploadResponseSchema(StagingResponseSchema):
    upload_id: str
    parts_uploaded: int
    bytes_transferred: int
    etag: str
    upload_status: str = Field(..., pattern='^(initiated|in_progress|completed|failed)$')
    presigned_url: str


class S3MetadataResponseSchema(StagingResponseSchema):
    bucket_info: Dict[str, Any]
    object_info: Dict[str, Any]
    storage_class: str
    encryption: Dict[str, Any]
    tags: Dict[str, str]
    version_id: str
    preview_data: List[Dict[str, Any]]


# Stream Source Schemas
class StreamSourceConfigSchema(BaseModel):
    """Schema for stream source configuration"""
    stream_type: str = Field(..., pattern='^(kafka|kinesis|rabbitmq|pubsub)$')
    connection_config: Dict[str, Any]
    batch_size: int = 100
    processing_timeout: int = 30
    error_handling: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_retries": 3,
            "dead_letter_queue": None,
            "retry_delay": 5
        }
    )
    concurrency: int = 1
    rate_limiting: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_records_per_second": 1000,
            "max_bytes_per_second": None
        }
    )
    checkpoint_interval: int = 60

    @model_validator(mode='after')
    def validate_connection_config(self) -> 'StreamSourceConfigSchema':
        required_fields = {
            'kafka': ['bootstrap_servers', 'topic'],
            'kinesis': ['stream_name', 'region'],
            'rabbitmq': ['host', 'queue'],
            'pubsub': ['project_id', 'subscription_name']
        }

        if self.stream_type in required_fields:
            for field in required_fields[self.stream_type]:
                if field not in self.connection_config:
                    raise ValueError(f'{field} required for {self.stream_type} configuration')
        return self

    model_config = ConfigDict(from_attributes=True)

class StreamSourceRequestSchema(StagingRequestSchema):
    config: StreamSourceConfigSchema
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list)
    enabled: bool = True
    stream_type: str = Field(..., pattern='^(kafka|kinesis|rabbitmq|pubsub)$')
    connection_config: Dict[str, Any]
    batch_size: int = 100
    processing_timeout: int = 30
    error_handling: Dict[str, Any] = Field(default_factory=dict)
    concurrency: int = 1
    rate_limiting: Dict[str, Any] = Field(default_factory=dict)
    checkpoint_interval: int = 60


class StreamSourceResponseSchema(StagingResponseSchema):
    stream_status: str = Field(..., pattern='^(active|paused|error)$')
    current_throughput: float
    lag: int
    processing_metrics: Dict[str, Any]
    error_count: int
    last_checkpoint: Optional[datetime]


class StreamUploadRequestSchema(StagingRequestSchema):
    stream_name: str
    partition_key: str
    sequence_number: Optional[str]
    data: Dict[str, Any]
    encoding: str = 'utf-8'


class StreamUploadResponseSchema(StagingResponseSchema):
    sequence_number: str
    shard_id: str
    timestamp: datetime
    partition_key: str
    bytes_processed: int
    upload_status: str = Field(..., pattern='^(pending|processing|delivered|failed)$')


class StreamMetadataResponseSchema(StagingResponseSchema):
    stream_info: Dict[str, Any]
    shard_info: Dict[str, Any]
    throughput: Dict[str, Any]
    retention_period: int
    encryption_type: str
    preview_data: List[Dict[str, Any]]

# Database Configuration Schemas
class DatabaseSourceConfigSchema(BaseModel):
    """Schema for database source configuration"""
    dialect: DatabaseDialect
    host: str
    port: int
    database: str
    username: str
    password: str = Field(..., exclude=True)
    schema: Optional[str]
    ssl_enabled: bool = False
    ssl_config: Dict[str, Any] = Field(default_factory=dict)
    pool_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 1800,
            "pool_pre_ping": True
        }
    )
    timeout_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "connect_timeout": 30,
            "query_timeout": 60,
            "pool_timeout": 30
        }
    )

    @model_validator(mode='after')
    def validate_port_and_config(self) -> 'DatabaseSourceConfigSchema':
        # Validate standard ports
        standard_ports = {
            DatabaseDialect.POSTGRESQL: 5432,
            DatabaseDialect.MYSQL: 3306,
            DatabaseDialect.ORACLE: 1521,
            DatabaseDialect.MSSQL: 1433,
            DatabaseDialect.SQLITE: None
        }

        if self.dialect in standard_ports and standard_ports[self.dialect]:
            if self.port != standard_ports[self.dialect]:
                # Log warning instead of error for non-standard ports
                logger.warning(f"Non-standard port {self.port} used for {self.dialect}")

        # Validate SSL configuration
        if self.ssl_enabled and not self.ssl_config:
            raise ValueError("SSL configuration required when SSL is enabled")

        return self

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "dialect": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database": "mydb",
                "username": "user",
                "password": "password",
                "schema": "public",
                "ssl_enabled": False
            }
        }
    )

# Status schema for database connections
class DatabaseConnectionStatusSchema(BaseModel):
    """Schema for database connection status"""
    status: str = Field(..., pattern='^(connected|disconnected|error)$')
    message: Optional[str]
    last_connected: Optional[datetime]
    connection_error: Optional[str]
    latency_ms: Optional[float]
    active_connections: int = 0
    max_connections: int
    uptime_seconds: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class DataSourceRequestSchema(BaseModel):
    """Schema for data source creation/update requests"""
    type: DataSourceType
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list)
    enabled: bool = True
    config: Union[
        DatabaseSourceConfigSchema,
        S3SourceConfigSchema,
        APISourceConfigSchema,
        StreamSourceConfigSchema,
        FileSourceRequestSchema
    ]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "type": "database",
                "name": "Production PostgreSQL",
                "description": "Main production database",
                "tags": ["production", "core"],
                "enabled": True,
                "config": {
                    "dialect": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "database": "mydb",
                    "username": "user",
                    "password": "password",
                    "schema": "public"
                }
            }
        }
    )

    @model_validator(mode='after')
    def validate_config_type(self) -> 'DataSourceRequestSchema':
        """Validate that the config matches the source type"""
        config_type_map = {
            DataSourceType.DATABASE: DatabaseSourceConfigSchema,
            DataSourceType.S3: S3SourceConfigSchema,
            DataSourceType.API: APISourceConfigSchema,
            DataSourceType.STREAM: StreamSourceConfigSchema,
            DataSourceType.FILE: FileSourceRequestSchema
        }

        expected_type = config_type_map.get(self.type)
        if not isinstance(self.config, expected_type):
            raise ValueError(
                f"Config type mismatch. Expected {expected_type.__name__} "
                f"for source type {self.type}"
            )
        return self


class DataSourceResponseSchema(BaseModel):
    """Schema for data source responses"""
    id: UUID
    type: DataSourceType
    name: str
    description: Optional[str]
    tags: List[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    owner_id: UUID
    status: Literal["active", "inactive", "error"]
    connection_info: Union[
        DatabaseSourceResponseSchema,
        S3SourceResponseSchema,
        APISourceResponseSchema,
        StreamSourceResponseSchema,
        FileSourceResponseSchema
    ]
    error_message: Optional[str] = None
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "database",
                "name": "Production PostgreSQL",
                "description": "Main production database",
                "tags": ["production", "core"],
                "enabled": True,
                "created_at": "2024-02-09T12:00:00Z",
                "updated_at": "2024-02-09T12:00:00Z",
                "owner_id": "123e4567-e89b-12d3-a456-426614174001",
                "status": "active"
            }
        }
    )


@model_validator(mode='after')
def validate_connection_config(self) -> 'StreamSourceRequestSchema':
    required_fields = {
        'kafka': ['bootstrap_servers', 'topic'],
        'kinesis': ['stream_name', 'region'],
        'rabbitmq': ['host', 'queue'],
        'pubsub': ['project_id', 'subscription_name']
    }

    if self.stream_type in required_fields:
        for field in required_fields[self.stream_type]:
            if field not in self.connection_config:
                raise ValueError(f'{field} required for {self.stream_type} configuration')
    return self
