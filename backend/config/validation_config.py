"""
Validation Configuration Module

This module provides comprehensive validation configurations for different data sources
including files, APIs, databases, streams, and S3 storage. It implements detailed
validation rules and security checks for each data source type.

Features:
    - File format and content validation
    - API endpoint and request validation
    - Database connection and query validation
    - Stream processing validation
    - S3 bucket and object validation
    - Security pattern checking
    - MIME type verification

Usage:
    from config.validation_config import ValidationConfigs

    configs = ValidationConfigs()
    file_config = configs.get_config('file')
    if file_config.matches_blocked_pattern(content):
        raise SecurityError("Blocked content detected")
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Pattern, Union
from enum import Enum, auto
import re
import logging
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)


class StreamType(Enum):
    """Enumeration of supported stream types with documentation."""
    KAFKA = auto()
    RABBITMQ = auto()

    def __str__(self) -> str:
        """String representation of stream type."""
        return self.name.lower()


@dataclass
class BaseValidationConfig:
    """
    Base configuration class with common validation settings.

    This class provides common validation functionality and security checks
    that are inherited by specific validation configurations.

    Attributes:
        blocked_patterns (List[str]): Patterns to block for security
        REQUEST_TIMEOUT (int): Default timeout for requests in seconds
    """
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r'password', r'secret', r'key', r'token', r'credential',
        r'auth', r'access', r'private', r'sensitive'
    ])
    REQUEST_TIMEOUT: int = 30

    def __post_init__(self):
        """
        Initialize compiled regex patterns for performance optimization.
        Compiles all blocked patterns into regex objects for faster matching.
        """
        self._compiled_patterns: List[Pattern] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.blocked_patterns
        ]

    def matches_blocked_pattern(self, text: Union[str, bytes]) -> bool:
        """
        Check if text matches any blocked pattern.

        Args:
            text (Union[str, bytes]): Text to check against blocked patterns

        Returns:
            bool: True if text matches any blocked pattern
        """
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')
        return any(pattern.search(text) for pattern in self._compiled_patterns)


@dataclass
class FileValidationConfig(BaseValidationConfig):
    """
    Configuration for file source validation.

    Provides comprehensive validation rules for file-based data sources
    including size limits, format verification, and content checking.

    Attributes:
        max_file_size_mb (int): Maximum file size in megabytes
        min_file_size_bytes (int): Minimum file size in bytes
        allowed_formats (List[str]): List of allowed file formats
        mime_types (Dict[str, List[str]]): Mapping of formats to MIME types
        file_signatures (Dict[str, List[bytes]]): File format signatures
        scan_encoding (bool): Whether to scan file encoding
    """
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
    scan_encoding: bool = True

    def validate_file_size(self, size_bytes: int) -> bool:
        """
        Validate file size against configured limits.

        Args:
            size_bytes (int): File size in bytes

        Returns:
            bool: True if file size is within limits
        """
        return (
                self.min_file_size_bytes <= size_bytes <=
                self.max_file_size_mb * 1024 * 1024
        )

    def validate_file_format(self, filename: str, content: bytes) -> bool:
        """
        Validate file format using extension and content signatures.

        Args:
            filename (str): Name of the file
            content (bytes): First few bytes of file content

        Returns:
            bool: True if file format is valid
        """
        ext = Path(filename).suffix.lower().lstrip('.')
        if ext not in self.allowed_formats:
            return False

        signatures = self.file_signatures.get(ext, [])
        return not signatures or any(
            content.startswith(sig) for sig in signatures
        )


@dataclass
class APIValidationConfig(BaseValidationConfig):
    """
    Configuration for API source validation.

    Provides validation rules for API endpoints including allowed methods,
    authentication types, and security requirements.
    """
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


@dataclass
class DatabaseValidationConfig(BaseValidationConfig):
    """
    Configuration for database source validation.

    Provides validation rules for database connections including supported
    databases, naming conventions, and security requirements.

    Attributes:
        supported_sources (Dict): Mapping of database types to their configurations
        min_database_length (int): Minimum length for database names
        max_database_length (int): Maximum length for database names
        allowed_database_chars (str): Regex pattern for valid database name characters
    """
    supported_sources: Dict[str, Dict[str, Optional[int]]] = field(
        default_factory=lambda: {
            'postgresql': {'default_port': 5432},
            'mysql': {'default_port': 3306},
            'mssql': {'default_port': 1433},
            'oracle': {'default_port': 1521},
            'sqlite': {'default_port': None}
        }
    )
    min_database_length: int = 1
    max_database_length: int = 128
    min_host_length: int = 1
    max_host_length: int = 255
    allowed_database_chars: str = r'^[a-zA-Z0-9_\-\.]+$'
    allowed_host_chars: str = r'^[a-zA-Z0-9\-\.]+$'
    allowed_username_chars: str = r'^[a-zA-Z0-9_\-\.]+$'

    def __post_init__(self):
        """Initialize regex patterns for database name validation."""
        super().__post_init__()
        self._db_name_pattern = re.compile(self.allowed_database_chars)
        self._host_pattern = re.compile(self.allowed_host_chars)
        self._username_pattern = re.compile(self.allowed_username_chars)

    def validate_database_name(self, name: str) -> bool:
        """
        Validate database name against configured rules.

        Args:
            name (str): Database name to validate

        Returns:
            bool: True if name is valid
        """
        return (
                self.min_database_length <= len(name) <= self.max_database_length
                and bool(self._db_name_pattern.match(name))
        )

    def validate_host(self, host: str) -> bool:
        """
        Validate database host against configured rules.

        Args:
            host (str): Host name to validate

        Returns:
            bool: True if host is valid
        """
        return (
                self.min_host_length <= len(host) <= self.max_host_length
                and bool(self._host_pattern.match(host))
        )


@dataclass
class StreamValidationConfig(BaseValidationConfig):
    """
    Configuration for stream source validation.

    Provides validation rules for stream-based data sources including
    supported stream types, connection parameters, and runtime validation.

    Attributes:
        supported_stream_types (Set[StreamType]): Set of supported stream types
        connection_timeout (int): Connection timeout in seconds
        default_ports (Dict): Default ports for different stream types
    """
    supported_stream_types: Set[StreamType] = field(
        default_factory=lambda: {StreamType.KAFKA, StreamType.RABBITMQ}
    )
    connection_timeout: int = 5
    default_ports: Dict[StreamType, int] = field(
        default_factory=lambda: {
            StreamType.KAFKA: 9092,
            StreamType.RABBITMQ: 5672
        }
    )
    min_host_length: int = 1
    max_host_length: int = 255
    required_fields: Dict[StreamType, List[str]] = field(
        default_factory=lambda: {
            StreamType.KAFKA: ['bootstrap_servers', 'group_id'],
            StreamType.RABBITMQ: ['host', 'virtual_host']
        }
    )

    def validate_stream_config(self, stream_type: StreamType, config: Dict[str, Any]) -> bool:
        """
        Validate stream configuration parameters.

        Args:
            stream_type (StreamType): Type of stream to validate
            config (Dict[str, Any]): Configuration parameters

        Returns:
            bool: True if configuration is valid
        """
        if stream_type not in self.supported_stream_types:
            return False

        required = self.required_fields.get(stream_type, [])
        return all(field in config for field in required)


@dataclass
class S3ValidationConfig(BaseValidationConfig):
    """
    Configuration for S3 source validation.

    Provides validation rules for S3 storage including bucket naming,
    object keys, and access patterns.

    Attributes:
        max_bucket_name_length (int): Maximum length for bucket names
        min_bucket_name_length (int): Minimum length for bucket names
        allowed_bucket_chars (str): Regex pattern for valid bucket name characters
    """
    max_bucket_name_length: int = 63
    min_bucket_name_length: int = 3
    max_key_length: int = 1024
    max_file_size_mb: int = 5 * 1024  # 5 GB
    min_file_size_bytes: int = 1
    allowed_bucket_chars: str = r'^[a-z0-9.-]+$'
    allowed_key_chars: str = r'^[a-zA-Z0-9_\-./]+$'
    allowed_regions: Set[str] = field(
        default_factory=lambda: {
            'us-east-1', 'us-west-2', 'eu-west-1',
            'ap-southeast-1', 'ap-northeast-1'
        }
    )
    allowed_operations: Set[str] = field(
        default_factory=lambda: {
            'get', 'put', 'delete', 'list', 'head'
        }
    )

    def __post_init__(self):
        """Initialize regex patterns for S3 validation."""
        super().__post_init__()
        self._bucket_pattern = re.compile(self.allowed_bucket_chars)
        self._key_pattern = re.compile(self.allowed_key_chars)

    def validate_bucket_name(self, name: str) -> bool:
        """
        Validate S3 bucket name against AWS naming rules.

        Args:
            name (str): Bucket name to validate

        Returns:
            bool: True if bucket name is valid
        """
        return (
                self.min_bucket_name_length <= len(name) <= self.max_bucket_name_length
                and bool(self._bucket_pattern.match(name))
        )

    def validate_key(self, key: str) -> bool:
        """
        Validate S3 object key against configured rules.

        Args:
            key (str): Object key to validate

        Returns:
            bool: True if key is valid
        """
        return len(key) <= self.max_key_length and bool(self._key_pattern.match(key))


@dataclass
class ValidationConfigs:
    """
    Container for all validation configurations.

    Provides centralized access to all validation configurations and
    utilities for working with them.

    Attributes:
        file (FileValidationConfig): File validation configuration
        api (APIValidationConfig): API validation configuration
        database (DatabaseValidationConfig): Database validation configuration
        stream (StreamValidationConfig): Stream validation configuration
        s3 (S3ValidationConfig): S3 validation configuration
    """
    file: FileValidationConfig = field(default_factory=FileValidationConfig)
    api: APIValidationConfig = field(default_factory=APIValidationConfig)
    database: DatabaseValidationConfig = field(default_factory=DatabaseValidationConfig)
    stream: StreamValidationConfig = field(default_factory=StreamValidationConfig)
    s3: S3ValidationConfig = field(default_factory=S3ValidationConfig)

    def get_config(self, source_type: str) -> Optional[BaseValidationConfig]:
        """
        Get validation config for specific source type.

        Args:
            source_type (str): Type of source to get configuration for

        Returns:
            Optional[BaseValidationConfig]: Configuration for source type or None
        """
        config_map = {
            'file': self.file,
            'api': self.api,
            'database': self.database,
            'stream': self.stream,
            's3': self.s3
        }
        return config_map.get(source_type.lower())


# Create global instance
validation_configs = ValidationConfigs()