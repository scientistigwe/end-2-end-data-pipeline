from __future__ import annotations

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import timedelta
from cryptography.fernet import Fernet


@dataclass
class S3Settings:
    """S3-specific settings"""
    SUPPORTED_FORMATS: List[str] = field(default_factory=lambda: [
        'csv', 'json', 'parquet', 'xlsx', 'xls'
    ])
    MAX_FILE_SIZE: int = field(default=5 * 1024 * 1024 * 1024)  # 5GB
    CHUNK_SIZE: int = field(default=8 * 1024 * 1024)  # 8MB
    MULTIPART_THRESHOLD: int = field(default=100 * 1024 * 1024)  # 100MB
    MAX_POOL_CONNECTIONS: int = field(default=100)
    DOWNLOAD_FOLDER: str = field(default="downloads")
    MAX_KEYS_PER_REQUEST: int = field(default=1000)
    VALIDATE_CONTENT_TYPE: bool = field(default=True)


@dataclass
class AWSSettings:
    """AWS-specific settings"""
    DEFAULT_REGION: str = field(default="us-east-1")
    AWS_ENDPOINTS: Dict[str, str] = field(default_factory=lambda: {
        'us-east-1': 's3.amazonaws.com',
        'us-west-2': 's3.us-west-2.amazonaws.com',
        'eu-west-1': 's3.eu-west-1.amazonaws.com'
    })
    DEFAULT_ACL: str = field(default="private")
    SIGNATURE_VERSION: str = field(default="s3v4")
    ADDRESSING_STYLE: str = field(default="virtual")


@dataclass
class SecuritySettings:
    """Security configuration"""
    ENCRYPTION_KEY: str = field(default_factory=lambda:
    os.getenv('S3_ENCRYPTION_KEY', Fernet.generate_key().decode())
                                )
    SERVER_SIDE_ENCRYPTION: str = field(default="AES256")
    ENABLE_SSL: bool = field(default=True)
    VERIFY_SSL: bool = field(default=True)
    MAX_RETRIES_ON_ERROR: int = field(default=3)


@dataclass
class PerformanceSettings:
    """Performance optimization settings"""
    MAX_CONCURRENT_REQUESTS: int = field(default=10)
    CONNECTION_TIMEOUT: int = field(default=60)
    READ_TIMEOUT: int = field(default=60)
    MAX_ATTEMPTS: int = field(default=3)
    RETRY_MODE: str = field(default="adaptive")
    USE_ACCELERATE_ENDPOINT: bool = field(default=False)


@dataclass
class MonitoringSettings:
    """Monitoring configuration"""
    ENABLE_METRICS: bool = field(default=True)
    METRIC_PREFIX: str = field(default="s3_client")
    TRACK_PERFORMANCE: bool = field(default=True)
    SLOW_OPERATION_THRESHOLD: float = field(default=5.0)  # seconds
    LOG_LEVEL: str = field(default="INFO")

@dataclass
class RetrySettings:
    """Retry configuration"""
    MAX_RETRIES: int = field(default=3)
    RETRY_DELAY: float = field(default=1.0)
    MAX_DELAY: int = field(default=30)
    RETRY_CODES: List[int] = field(default_factory=lambda: [
        408, 429, 500, 502, 503, 504
    ])
    RETRY_METHODS: List[str] = field(default_factory=lambda: [
        'GET', 'HEAD', 'PUT', 'DELETE', 'OPTIONS', 'TRACE'
    ])
    BACKOFF_FACTOR: float = field(default=1.5)
    MAX_BACKOFF: int = field(default=3600)  # 1 hour max backoff

class Config:
    """Enhanced configuration for S3 operations"""

    def __init__(
            self,
            s3_settings: Optional[S3Settings] = None,
            aws_settings: Optional[AWSSettings] = None,
            security_settings: Optional[SecuritySettings] = None,
            performance_settings: Optional[PerformanceSettings] = None,
            monitoring_settings: Optional[MonitoringSettings] = None,
            retry_settings: Optional[RetrySettings] = None
    ):
        """Initialize configuration with optional overrides"""
        self.S3 = s3_settings or S3Settings()
        self.AWS = aws_settings or AWSSettings()
        self.SECURITY = security_settings or SecuritySettings()
        self.PERFORMANCE = performance_settings or PerformanceSettings()
        self.MONITORING = monitoring_settings or MonitoringSettings()
        self.RETRY = retry_settings or RetrySettings()

        # Initialize encryption
        self._setup_encryption()

        # Validate configuration
        self._validate_configuration()

        # Create required directories
        self._setup_directories()

    def _setup_encryption(self):
        """Set up encryption for sensitive data"""
        try:
            self.cipher_suite = Fernet(self.SECURITY.ENCRYPTION_KEY.encode())
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {str(e)}")

    def _validate_configuration(self):
        """Validate configuration settings"""
        self._validate_sizes()
        self._validate_timeouts()
        self._validate_security()

    def _validate_sizes(self):
        """Validate size-related settings"""
        if self.S3.MAX_FILE_SIZE <= 0:
            raise ValueError("MAX_FILE_SIZE must be positive")
        if self.S3.CHUNK_SIZE <= 0:
            raise ValueError("CHUNK_SIZE must be positive")
        if self.S3.MULTIPART_THRESHOLD <= self.S3.CHUNK_SIZE:
            raise ValueError("MULTIPART_THRESHOLD must be greater than CHUNK_SIZE")

    def _validate_timeouts(self):
        """Validate timeout settings"""
        if self.PERFORMANCE.CONNECTION_TIMEOUT <= 0:
            raise ValueError("CONNECTION_TIMEOUT must be positive")
        if self.PERFORMANCE.READ_TIMEOUT <= 0:
            raise ValueError("READ_TIMEOUT must be positive")

    def _validate_security(self):
        """Validate security settings"""
        if not self.SECURITY.ENCRYPTION_KEY:
            raise ValueError("ENCRYPTION_KEY is required")

    def _setup_directories(self):
        """Create required directories"""
        os.makedirs(self.S3.DOWNLOAD_FOLDER, exist_ok=True)

    def encrypt_credentials(self, credentials: Dict[str, str]) -> Dict[str, bytes]:
        """
        Encrypt AWS credentials

        Args:
            credentials: Dictionary of credentials to encrypt

        Returns:
            Dictionary of encrypted credentials
        """
        try:
            return {
                key: self.cipher_suite.encrypt(str(value).encode())
                for key, value in credentials.items()
            }
        except Exception as e:
            raise ValueError(f"Credential encryption failed: {str(e)}")

    def decrypt_credentials(self, encrypted_creds: Dict[str, bytes]) -> Dict[str, str]:
        """
        Decrypt AWS credentials

        Args:
            encrypted_creds: Dictionary of encrypted credentials

        Returns:
            Dictionary of decrypted credentials
        """
        try:
            return {
                key: self.cipher_suite.decrypt(value).decode()
                for key, value in encrypted_creds.items()
            }
        except Exception as e:
            raise ValueError(f"Credential decryption failed: {str(e)}")

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> Config:
        """Create configuration from dictionary"""
        s3_settings = S3Settings(**config_dict.get('S3', {}))
        aws_settings = AWSSettings(**config_dict.get('AWS', {}))
        security_settings = SecuritySettings(**config_dict.get('SECURITY', {}))
        performance_settings = PerformanceSettings(**config_dict.get('PERFORMANCE', {}))
        monitoring_settings = MonitoringSettings(**config_dict.get('MONITORING', {}))
        retry_settings = RetrySettings(**config_dict.get('RETRY', {}))  # Add this

        return cls(
            s3_settings=s3_settings,
            aws_settings=aws_settings,
            security_settings=security_settings,
            performance_settings=performance_settings,
            monitoring_settings=monitoring_settings,
            retry_settings=retry_settings  # Add this
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'S3': {
                field.name: getattr(self.S3, field.name)
                for field in self.S3.__dataclass_fields__
            },
            'AWS': {
                field.name: getattr(self.AWS, field.name)
                for field in self.AWS.__dataclass_fields__
            },
            'SECURITY': {
                field.name: getattr(self.SECURITY, field.name)
                for field in self.SECURITY.__dataclass_fields__
                if field.name != 'ENCRYPTION_KEY'  # Exclude sensitive data
            },
            'PERFORMANCE': {
                field.name: getattr(self.PERFORMANCE, field.name)
                for field in self.PERFORMANCE.__dataclass_fields__
            },
            'MONITORING': {
                field.name: getattr(self.MONITORING, field.name)
                for field in self.MONITORING.__dataclass_fields__
            },
            'RETRY': {  # Add this
                field.name: getattr(self.RETRY, field.name)
                for field in self.RETRY.__dataclass_fields__
            }
        }
    
    def update(self, **kwargs):
        """Update configuration settings"""
        for section, values in kwargs.items():
            if hasattr(self, section):
                config_section = getattr(self, section)
                for key, value in values.items():
                    if hasattr(config_section, key):
                        setattr(config_section, key, value)

        # Revalidate after updates
        self._validate_configuration()

    def get_boto3_config(self) -> Dict[str, Any]:
        """Get boto3 client configuration"""
        return {
            'region_name': self.AWS.DEFAULT_REGION,
            'use_ssl': self.SECURITY.ENABLE_SSL,
            'verify': self.SECURITY.VERIFY_SSL,
            'endpoint_url': self.AWS.AWS_ENDPOINTS.get(
                self.AWS.DEFAULT_REGION
            ),
            'config': {
                'max_pool_connections': self.S3.MAX_POOL_CONNECTIONS,
                'connect_timeout': self.PERFORMANCE.CONNECTION_TIMEOUT,
                'read_timeout': self.PERFORMANCE.READ_TIMEOUT,
                'retries': {
                    'max_attempts': self.PERFORMANCE.MAX_ATTEMPTS,
                    'mode': self.PERFORMANCE.RETRY_MODE
                },
                'signature_version': self.AWS.SIGNATURE_VERSION,
                's3': {
                    'addressing_style': self.AWS.ADDRESSING_STYLE,
                    'use_accelerate_endpoint': self.PERFORMANCE.USE_ACCELERATE_ENDPOINT
                }
            }
        }