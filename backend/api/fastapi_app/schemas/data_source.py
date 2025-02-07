# backend/api/fastapi_app/schemas/data_source.py

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator, root_validator, AnyUrl, constr
from enum import Enum


class StagingRequestSchema(BaseModel):
    """Base request schema maintained for compatibility"""

    class Config:
        orm_mode = True


class StagingResponseSchema(BaseModel):
    """Base response schema maintained for compatibility"""

    class Config:
        orm_mode = True


class AuthType(str, Enum):
    BASIC = "basic"
    OAUTH = "oauth"
    API_KEY = "api_key"
    BEARER = "bearer"


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

    @root_validator
    def validate_auth_config(cls, values):
        required_fields = {
            AuthType.BASIC: ['username', 'password'],
            AuthType.OAUTH: ['client_id', 'client_secret'],
            AuthType.API_KEY: ['key', 'header_name'],
            AuthType.BEARER: ['token']
        }
        auth_type = values.get('auth_type')
        auth_config = values.get('auth_config', {})

        if auth_type in required_fields:
            for field in required_fields[auth_type]:
                if field not in auth_config:
                    raise ValueError(f'{field} required for {auth_type} authentication')
        return values


class APISourceResponseSchema(StagingResponseSchema):
    connection_status: str = Field(..., regex='^(connected|disconnected|error)$')
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
    connection_status: str = Field(..., regex='^(connected|disconnected|error)$')
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
    status: str = Field(..., regex='^(success|error|in_progress)$')
    staged_id: str
    control_point_id: str
    tracking_url: str
    upload_status: Optional[str] = Field(None, regex='^(in_progress|completed|failed)$')
    error: Optional[str]
    message: Optional[str]


class FileSourceRequestSchema(StagingRequestSchema):
    original_filename: str
    file_type: str = Field(..., regex='^(csv|json|xlsx|parquet|xml)$')
    mime_type: str
    encoding: str = 'utf-8'
    delimiter: Optional[str]
    compression: Optional[str] = Field(None, regex='^(gzip|zip|bzip2)$')
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
    processing_status: str = Field(..., regex='^(pending|processing|completed|failed)$')


# S3 Source Schemas
class S3SourceRequestSchema(StagingRequestSchema):
    bucket: constr(min_length=3, max_length=63)
    region: str
    prefix: Optional[str]
    access_key: str = Field(..., exclude=True)
    secret_key: str = Field(..., exclude=True)
    session_token: Optional[str] = Field(None, exclude=True)
    encryption_config: Dict[str, Any] = Field(default_factory=dict)
    storage_class: str = Field(..., regex='^(STANDARD|STANDARD_IA|ONEZONE_IA|GLACIER|DEEP_ARCHIVE)$')
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
    connection_status: str = Field(..., regex='^(connected|disconnected|error)$')
    total_objects: int
    total_size: int
    bucket_metrics: Dict[str, Any]
    last_sync: Optional[datetime]
    versioning_status: str = Field(..., regex='^(Enabled|Suspended|Disabled)$')
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
    upload_status: str = Field(..., regex='^(initiated|in_progress|completed|failed)$')
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
class StreamSourceRequestSchema(StagingRequestSchema):
    stream_type: str = Field(..., regex='^(kafka|kinesis|rabbitmq|pubsub)$')
    connection_config: Dict[str, Any]
    batch_size: int = 100
    processing_timeout: int = 30
    error_handling: Dict[str, Any] = Field(default_factory=dict)
    concurrency: int = 1
    rate_limiting: Dict[str, Any] = Field(default_factory=dict)
    checkpoint_interval: int = 60

    @root_validator
    def validate_connection_config(cls, values):
        required_fields = {
            'kafka': ['bootstrap_servers', 'topic'],
            'kinesis': ['stream_name', 'region'],
            'rabbitmq': ['host', 'queue'],
            'pubsub': ['project_id', 'subscription_name']
        }

        stream_type = values.get('stream_type')
        config = values.get('connection_config', {})

        if stream_type in required_fields:
            for field in required_fields[stream_type]:
                if field not in config:
                    raise ValueError(f'{field} required for {stream_type} configuration')
        return values


class StreamSourceResponseSchema(StagingResponseSchema):
    stream_status: str = Field(..., regex='^(active|paused|error)$')
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
    upload_status: str = Field(..., regex='^(pending|processing|delivered|failed)$')


class StreamMetadataResponseSchema(StagingResponseSchema):
    stream_info: Dict[str, Any]
    shard_info: Dict[str, Any]
    throughput: Dict[str, Any]
    retention_period: int
    encryption_type: str
    preview_data: List[Dict[str, Any]]