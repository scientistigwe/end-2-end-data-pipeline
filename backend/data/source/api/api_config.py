# api_config.py

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

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
class ProcessingConfig:
    """Processing configuration"""
    TIMEOUT: int = 600  # 10 minutes default timeout
    MAX_RETRIES: int = 3
    PARALLEL_REQUESTS: int = 10
    ERROR_THRESHOLD: float = 0.1  # 10% error rate threshold
    BACKOFF_FACTOR: float = 1.5
    MAX_BACKOFF: int = 3600  # 1 hour max backoff

@dataclass
class Config:
    """API configuration with credential management"""
    
    # API Credentials and Authentication
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    auth_token: Optional[str] = None
    auth_type: str = "none"  # none, basic, bearer, oauth2
    
    # API Endpoint Configuration
    base_url: Optional[str] = None
    endpoints: Dict[str, str] = field(default_factory=dict)
    version: Optional[str] = None
    
    # Component configurations
    REQUEST: RequestConfig = field(default_factory=RequestConfig)
    PROCESSING: ProcessingConfig = field(default_factory=ProcessingConfig)
    RETRY: RetryConfig = field(default_factory=RetryConfig)
    
    # Connection settings
    connection_timeout: int = 10
    keep_alive: bool = True
    
    # Rate Limiting
    rate_limit_calls: int = 100
    rate_limit_period: int = 60  # seconds
    
    def __post_init__(self):
        """Initialize encryption for sensitive data"""
        self._encryption_key = os.getenv('API_ENCRYPTION_KEY', Fernet.generate_key())
        self._cipher_suite = Fernet(self._encryption_key)
        self._secure_credentials()

    def _secure_credentials(self):
        """Encrypt sensitive credentials"""
        if self.api_key:
            self.api_key = self._encrypt_value(self.api_key)
        if self.api_secret:
            self.api_secret = self._encrypt_value(self.api_secret)
        if self.auth_token:
            self.auth_token = self._encrypt_value(self.auth_token)

    def _encrypt_value(self, value: str) -> bytes:
        """Encrypt sensitive value"""
        return self._cipher_suite.encrypt(value.encode())

    def _decrypt_value(self, encrypted_value: bytes) -> str:
        """Decrypt sensitive value"""
        return self._cipher_suite.decrypt(encrypted_value).decode()

    def get_credentials(self) -> Dict[str, str]:
        """Get decrypted credentials"""
        credentials = {}
        if self.api_key:
            credentials['api_key'] = self._decrypt_value(self.api_key)
        if self.api_secret:
            credentials['api_secret'] = self._decrypt_value(self.api_secret)
        if self.auth_token:
            credentials['auth_token'] = self._decrypt_value(self.auth_token)
        return credentials

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Config':
        """Create configuration from dictionary"""
        # Extract nested configurations
        request_config = RequestConfig(
            **config_dict.get('REQUEST', {})
        )
        processing_config = ProcessingConfig(
            **config_dict.get('PROCESSING', {})
        )
        retry_config = RetryConfig(  # Add this
            **config_dict.get('RETRY', {})
        )
        
        # Create main config
        return cls(
            **{k: v for k, v in config_dict.items()
            if k not in ['REQUEST', 'PROCESSING', 'RETRY']},  # Update this
            REQUEST=request_config,
            PROCESSING=processing_config,
            RETRY=retry_config  # Add this
        )

def get_config(
    api_credentials: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None
) -> Config:
    """
    Get API configuration with credentials
    
    Args:
        api_credentials: Dictionary containing API credentials:
            {
                'api_key': 'your-api-key',
                'api_secret': 'your-api-secret',
                'auth_token': 'your-auth-token',
                'auth_type': 'bearer',
                'base_url': 'https://api.example.com',
                'version': 'v1'
            }
        config_path: Optional path to config file
        
    Returns:
        Config object with loaded configuration
    """
    try:
        # Start with default config
        config_dict = {
            'auth_type': 'none',
            'REQUEST': {},
            'PROCESSING': {}
        }
        
        # Load from file if provided
        if config_path:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    config_dict.update(file_config)
        
        # Update with provided credentials
        if api_credentials:
            config_dict.update(api_credentials)
        
        # Create config instance
        config = Config.from_dict(config_dict)
        
        # Validate configuration
        _validate_config(config)
        
        return config
        
    except Exception as e:
        logger.error(f"Error loading API configuration: {str(e)}")
        raise

