# backend/config/validation_config.py

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set
from enum import Enum, auto


class StreamType(Enum):
    """Enumeration of supported stream types"""
    KAFKA = auto()
    RABBITMQ = auto()


@dataclass
class FileValidationConfig:
    """Configuration for file source validation"""
    max_file_size_mb: int = 100
    min_file_size_bytes: int = 1
    allowed_formats: List[str] = field(default_factory=lambda: [
        'csv', 'xlsx', 'xls', 'json', 'parquet', 'txt'
    ])
    mime_types: Dict[str, List[str]] = field(default_factory=lambda: {
        'csv': ['text/csv', 'text/plain'],
        'xlsx': [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel'
        ],
        'xls': ['application/vnd.ms-excel'],
        'json': ['application/json', 'text/plain'],
        'parquet': ['application/octet-stream'],
        'txt': ['text/plain']
    })
    file_signatures: Dict[str, List[bytes]] = field(default_factory=lambda: {
        'xlsx': [b'PK\x03\x04'],
        'xls': [b'\xD0\xCF\x11\xE0'],
        'csv': [b',', b';'],
        'json': [b'{', b'['],
        'parquet': [b'PAR1'],
        'txt': []
    })
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r'password', r'secret', r'key', r'token', r'credential'
    ])
    scan_encoding: bool = True


@dataclass
class APIValidationConfig:
    """Configuration for API source validation"""
    allowed_schemes: Set[str] = field(default_factory=lambda: {'http', 'https'})
    allowed_methods: Set[str] = field(default_factory=lambda: {
        'GET', 'POST', 'PUT', 'DELETE', 'PATCH'
    })
    connection_timeout: int = 5
    max_redirects: int = 3
    require_ssl: bool = True
    required_headers: Dict[str, Set[str]] = field(default_factory=lambda: {
        'GET': {'Accept'},
        'POST': {'Content-Type', 'Accept'},
        'PUT': {'Content-Type', 'Accept'},
        'DELETE': {'Accept'},
        'PATCH': {'Content-Type', 'Accept'}
    })
    supported_auth_types: Set[str] = field(default_factory=lambda: {
        'none', 'basic', 'bearer', 'oauth2', 'api_key'
    })
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r'password', r'secret', r'key', r'token', r'credential'
    ])
    REQUEST_TIMEOUT: int = 30


@dataclass
class DatabaseValidationConfig:
    """Configuration for database source validation"""
    supported_sources: Dict[str, Dict[str, Optional[int]]] = field(default_factory=lambda: {
        'postgresql': {'default_port': 5432},
        'mysql': {'default_port': 3306},
        'mssql': {'default_port': 1433},
        'oracle': {'default_port': 1521},
        'sqlite': {'default_port': None}
    })
    min_database_length: int = 1
    max_database_length: int = 128
    min_host_length: int = 1
    max_host_length: int = 255
    allowed_database_chars: str = r'^[a-zA-Z0-9_\-\.]+$'
    allowed_host_chars: str = r'^[a-zA-Z0-9.-]+$'
    allowed_username_chars: str = r'^[a-zA-Z0-9_\-\.]+$'
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r'password', r'secret', r'key', r'token', r'credential'
    ])
    REQUEST_TIMEOUT: int = 30


@dataclass
class StreamValidationConfig:
    """Configuration for stream source validation"""
    supported_stream_types: Set[StreamType] = field(default_factory=lambda: {
        StreamType.KAFKA, StreamType.RABBITMQ
    })
    connection_timeout: int = 5
    default_ports: Dict[StreamType, int] = field(default_factory=lambda: {
        StreamType.KAFKA: 9092,
        StreamType.RABBITMQ: 5672
    })
    min_host_length: int = 1
    max_host_length: int = 255
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r'password', r'secret', r'key', r'token', r'credential'
    ])
    required_fields: Dict[StreamType, List[str]] = field(default_factory=lambda: {
        StreamType.KAFKA: ['bootstrap_servers', 'group_id'],
        StreamType.RABBITMQ: ['host']
    })
    REQUEST_TIMEOUT: int = 30


@dataclass
class S3ValidationConfig:
    """Configuration for S3 source validation"""
    max_bucket_name_length: int = 63
    min_bucket_name_length: int = 3
    max_key_length: int = 1024
    max_file_size_mb: int = 5 * 1024  # 5 GB
    min_file_size_bytes: int = 1
    allowed_bucket_chars: str = r'^[a-z0-9.-]+$'
    allowed_key_chars: str = r'^[a-zA-Z0-9_\-./]+$'
    allowed_regions: Set[str] = field(default_factory=lambda: {
        'us-east-1', 'us-west-2', 'eu-west-1',
        'ap-southeast-1', 'ap-northeast-1'
    })
    allowed_operations: Set[str] = field(default_factory=lambda: {
        'get', 'put', 'delete', 'list', 'head'
    })
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r'password', r'secret', r'key', r'token', r'credential'
    ])
    REQUEST_TIMEOUT: int = 30


@dataclass
class ValidationConfigs:
    """Container for all validation configurations"""
    file: FileValidationConfig = field(default_factory=FileValidationConfig)
    api: APIValidationConfig = field(default_factory=APIValidationConfig)
    database: DatabaseValidationConfig = field(default_factory=DatabaseValidationConfig)
    stream: StreamValidationConfig = field(default_factory=StreamValidationConfig)
    s3: S3ValidationConfig = field(default_factory=S3ValidationConfig)

    def get_config(self, source_type: str) -> Any:
        """Get validation config for specific source type"""
        config_map = {
            'file': self.file,
            'api': self.api,
            'database': self.database,
            'stream': self.stream,
            's3': self.s3
        }
        return config_map.get(source_type)


