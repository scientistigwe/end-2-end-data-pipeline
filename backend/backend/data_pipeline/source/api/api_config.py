from __future__ import annotations

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import timedelta
from cryptography.fernet import Fernet


@dataclass
class RequestConfig:
    """Request-specific configuration"""
    ALLOWED_METHODS: List[str] = field(default_factory=lambda: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
    REQUEST_TIMEOUT: int = 30
    MAX_REDIRECTS: int = 5
    MAX_CONTENT_LENGTH: int = 10 * 1024 * 1024  # 10MB
    VERIFY_SSL: bool = True
    DEFAULT_HEADERS: Dict[str, str] = field(default_factory=lambda: {
        'User-Agent': 'APIClient/1.0',
        'Accept': 'application/json'
    })


@dataclass
class AuthConfig:
    """Authentication configuration"""
    VALID_AUTH_TYPES: List[str] = field(default_factory=lambda: [
        'none', 'basic', 'bearer', 'oauth2', 'api_key'
    ])
    TOKEN_EXPIRY_MARGIN: int = 300  # seconds before actual expiry
    ENCRYPTION_KEY: str = field(default_factory=lambda: os.getenv('API_ENCRYPTION_KEY', Fernet.generate_key().decode()))
    AUTO_REFRESH_TOKEN: bool = True
    SECURE_HEADERS: List[str] = field(default_factory=lambda: [
        'Authorization', 'X-API-Key', 'Bearer'
    ])


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    MAX_CALLS: int = 100
    TIME_PERIOD: float = 1.0  # seconds
    RATE_LIMIT_HEADERS: Dict[str, str] = field(default_factory=lambda: {
        'limit': 'X-RateLimit-Limit',
        'remaining': 'X-RateLimit-Remaining',
        'reset': 'X-RateLimit-Reset'
    })
    BACKOFF_FACTOR: float = 1.5
    MAX_BACKOFF: int = 3600  # 1 hour in seconds


@dataclass
class CacheConfig:
    """Caching configuration"""
    ENABLE_CACHE: bool = True
    CACHE_TTL: int = 3600  # 1 hour in seconds
    MAX_CACHE_SIZE: int = 1000
    CACHE_EXEMPT_ENDPOINTS: List[str] = field(default_factory=list)
    CACHE_METHODS: List[str] = field(default_factory=lambda: ['GET'])


@dataclass
class RetryConfig:
    """Retry configuration"""
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    MAX_DELAY: int = 30
    RETRY_CODES: List[int] = field(default_factory=lambda: [
        408, 429, 500, 502, 503, 504
    ])
    RETRY_METHODS: List[str] = field(default_factory=lambda: [
        'GET', 'HEAD', 'PUT', 'DELETE', 'OPTIONS', 'TRACE'
    ])


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""
    ENABLE_METRICS: bool = True
    METRIC_PREFIX: str = "api_client"
    TRACK_RESPONSE_TIME: bool = True
    SLOW_REQUEST_THRESHOLD: float = 2.0  # seconds
    HEALTH_CHECK_INTERVAL: int = 300  # 5 minutes
    ERROR_TRACKING_WINDOW: int = 3600  # 1 hour


@dataclass
class Config:
    """Comprehensive API configuration"""

    # Basic settings
    ENVIRONMENT: str = field(default="development")
    DEBUG: bool = field(default=False)
    LOG_LEVEL: str = field(default="INFO")

    # Component configurations
    REQUEST: RequestConfig = field(default_factory=RequestConfig)
    AUTH: AuthConfig = field(default_factory=AuthConfig)
    RATE_LIMIT: RateLimitConfig = field(default_factory=RateLimitConfig)
    CACHE: CacheConfig = field(default_factory=CacheConfig)
    RETRY: RetryConfig = field(default_factory=RetryConfig)
    MONITORING: MonitoringConfig = field(default_factory=MonitoringConfig)

    # Connection settings
    HEALTH_CHECK_ENDPOINT: Optional[str] = None
    CONNECTION_TIMEOUT: int = 10
    POOL_SIZE: int = 100
    KEEP_ALIVE: bool = True

    # Batch processing
    BATCH_SIZE: int = 1000
    MAX_CONCURRENT_REQUESTS: int = 10
    PAGINATION_STYLE: str = "offset"  # or "cursor"

    def __post_init__(self):
        """Post initialization setup and validation"""
        self._setup_encryption()
        self._validate_configuration()

    def _setup_encryption(self):
        """Set up encryption for sensitive data"""
        try:
            self.cipher_suite = Fernet(self.AUTH.ENCRYPTION_KEY.encode())
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {str(e)}")

    def _validate_configuration(self):
        """Validate configuration settings"""
        self._validate_timeouts()
        self._validate_batch_settings()
        self._validate_rate_limits()

    def _validate_timeouts(self):
        """Validate timeout settings"""
        if self.REQUEST.REQUEST_TIMEOUT <= 0:
            raise ValueError("Request timeout must be positive")
        if self.CONNECTION_TIMEOUT <= 0:
            raise ValueError("Connection timeout must be positive")

    def _validate_batch_settings(self):
        """Validate batch processing settings"""
        if self.BATCH_SIZE <= 0:
            raise ValueError("Batch size must be positive")
        if self.MAX_CONCURRENT_REQUESTS <= 0:
            raise ValueError("Max concurrent requests must be positive")

    def _validate_rate_limits(self):
        """Validate rate limit settings"""
        if self.RATE_LIMIT.MAX_CALLS <= 0:
            raise ValueError("Rate limit max calls must be positive")
        if self.RATE_LIMIT.TIME_PERIOD <= 0:
            raise ValueError("Rate limit time period must be positive")

    def encrypt_value(self, value: str) -> bytes:
        """Encrypt sensitive value"""
        return self.cipher_suite.encrypt(value.encode())

    def decrypt_value(self, encrypted_value: bytes) -> str:
        """Decrypt sensitive value"""
        return self.cipher_suite.decrypt(encrypted_value).decode()

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> Config:
        """Create configuration from dictionary"""
        # Handle nested configurations
        request_config = RequestConfig(
            **config_dict.get('REQUEST', {})
        )
        auth_config = AuthConfig(
            **config_dict.get('AUTH', {})
        )
        rate_limit_config = RateLimitConfig(
            **config_dict.get('RATE_LIMIT', {})
        )
        cache_config = CacheConfig(
            **config_dict.get('CACHE', {})
        )
        retry_config = RetryConfig(
            **config_dict.get('RETRY', {})
        )
        monitoring_config = MonitoringConfig(
            **config_dict.get('MONITORING', {})
        )

        # Create main config
        return cls(
            **{
                k: v for k, v in config_dict.items()
                if k not in ['REQUEST', 'AUTH', 'RATE_LIMIT', 'CACHE', 'RETRY', 'MONITORING']
            },
            REQUEST=request_config,
            AUTH=auth_config,
            RATE_LIMIT=rate_limit_config,
            CACHE=cache_config,
            RETRY=retry_config,
            MONITORING=monitoring_config
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'ENVIRONMENT': self.ENVIRONMENT,
            'DEBUG': self.DEBUG,
            'LOG_LEVEL': self.LOG_LEVEL,
            'REQUEST': self.REQUEST.__dict__,
            'AUTH': {
                k: v for k, v in self.AUTH.__dict__.items()
                if k != 'ENCRYPTION_KEY'  # Exclude sensitive data
            },
            'RATE_LIMIT': self.RATE_LIMIT.__dict__,
            'CACHE': self.CACHE.__dict__,
            'RETRY': self.RETRY.__dict__,
            'MONITORING': self.MONITORING.__dict__,
            'HEALTH_CHECK_ENDPOINT': self.HEALTH_CHECK_ENDPOINT,
            'CONNECTION_TIMEOUT': self.CONNECTION_TIMEOUT,
            'POOL_SIZE': self.POOL_SIZE,
            'KEEP_ALIVE': self.KEEP_ALIVE,
            'BATCH_SIZE': self.BATCH_SIZE,
            'MAX_CONCURRENT_REQUESTS': self.MAX_CONCURRENT_REQUESTS,
            'PAGINATION_STYLE': self.PAGINATION_STYLE
        }

    def update(self, **kwargs):
        """Update configuration settings"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                if isinstance(value, dict):
                    # Update nested config
                    current_config = getattr(self, key)
                    for k, v in value.items():
                        if hasattr(current_config, k):
                            setattr(current_config, k, v)
                else:
                    setattr(self, key, value)

        # Revalidate after updates
        self._validate_configuration()