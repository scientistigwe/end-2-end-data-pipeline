from __future__ import annotations

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import timedelta
from cryptography.fernet import Fernet


@dataclass
class ConnectionSettings:
    """Database connection settings"""
    MAX_POOL_SIZE: int = field(default=20)
    MIN_POOL_SIZE: int = field(default=5)
    MAX_OVERFLOW: int = field(default=10)
    POOL_TIMEOUT: int = field(default=30)
    POOL_RECYCLE: int = field(default=3600)
    CONNECT_TIMEOUT: int = field(default=10)
    MAX_CONCURRENT_QUERIES: int = field(default=50)
    ECHO_SQL: bool = field(default=False)


@dataclass
class QuerySettings:
    """Query execution settings"""
    QUERY_TIMEOUT: int = field(default=300)
    MAX_ROWS: int = field(default=1000000)
    CHUNK_SIZE: int = field(default=10000)
    FETCH_SIZE: int = field(default=1000)
    MAX_JOIN_TABLES: int = field(default=5)
    MAX_UNION_DEPTH: int = field(default=3)
    MAX_SUBQUERY_DEPTH: int = field(default=3)


@dataclass
class SecuritySettings:
    """Security configuration"""
    ENCRYPTION_KEY: str = field(default_factory=lambda:
    os.getenv('DB_ENCRYPTION_KEY', Fernet.generate_key().decode())
                                )
    SSL_REQUIRED: bool = field(default=True)
    VERIFY_SSL: bool = field(default=True)
    MAX_RETRIES: int = field(default=3)
    PROHIBITED_COMMANDS: List[str] = field(default_factory=lambda: [
        'DROP', 'DELETE', 'TRUNCATE', 'UPDATE', 'INSERT',
        'GRANT', 'REVOKE', 'ALTER', 'CREATE'
    ])


@dataclass
class MonitoringSettings:
    """Monitoring configuration"""
    ENABLE_METRICS: bool = field(default=True)
    METRIC_PREFIX: str = field(default="db_client")
    SLOW_QUERY_THRESHOLD: float = field(default=1.0)  # seconds
    LOG_QUERIES: bool = field(default=False)
    TRACK_QUERY_STATS: bool = field(default=True)
    ERROR_TRACKING_WINDOW: int = field(default=3600)  # 1 hour


class Config:
    """Enhanced configuration for database operations"""

    # Database types and drivers
    SUPPORTED_DATABASES = {
        'postgresql': {
            'sync_driver': 'postgresql',
            'async_driver': 'postgresql+asyncpg',
            'default_port': 5432
        },
        'mysql': {
            'sync_driver': 'mysql+pymysql',
            'async_driver': 'mysql+aiomysql',
            'default_port': 3306
        },
        'mssql': {
            'sync_driver': 'mssql+pyodbc',
            'async_driver': None,  # No async support
            'default_port': 1433
        }
    }

    def __init__(
            self,
            connection_settings: Optional[ConnectionSettings] = None,
            query_settings: Optional[QuerySettings] = None,
            security_settings: Optional[SecuritySettings] = None,
            monitoring_settings: Optional[MonitoringSettings] = None
    ):
        """Initialize configuration with optional overrides"""
        self.CONNECTION = connection_settings or ConnectionSettings()
        self.QUERY = query_settings or QuerySettings()
        self.SECURITY = security_settings or SecuritySettings()
        self.MONITORING = monitoring_settings or MonitoringSettings()

        # Initialize encryption
        self._setup_encryption()

        # Validate configuration
        self._validate_configuration()

    def _setup_encryption(self):
        """Set up encryption for sensitive data"""
        try:
            self.cipher_suite = Fernet(self.SECURITY.ENCRYPTION_KEY.encode())
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {str(e)}")

    def _validate_configuration(self):
        """Validate configuration settings"""
        self._validate_pool_settings()
        self._validate_query_settings()
        self._validate_security()

    def _validate_pool_settings(self):
        """Validate connection pool settings"""
        if self.CONNECTION.MAX_POOL_SIZE < self.CONNECTION.MIN_POOL_SIZE:
            raise ValueError("MAX_POOL_SIZE must be greater than MIN_POOL_SIZE")

        if self.CONNECTION.POOL_TIMEOUT <= 0:
            raise ValueError("POOL_TIMEOUT must be positive")

        if self.CONNECTION.MAX_CONCURRENT_QUERIES > self.CONNECTION.MAX_POOL_SIZE:
            raise ValueError("MAX_CONCURRENT_QUERIES cannot exceed MAX_POOL_SIZE")

    def _validate_query_settings(self):
        """Validate query settings"""
        if self.QUERY.QUERY_TIMEOUT <= 0:
            raise ValueError("QUERY_TIMEOUT must be positive")

        if self.QUERY.CHUNK_SIZE <= 0:
            raise ValueError("CHUNK_SIZE must be positive")

        if self.QUERY.MAX_ROWS <= 0:
            raise ValueError("MAX_ROWS must be positive")

    def _validate_security(self):
        """Validate security settings"""
        if not self.SECURITY.ENCRYPTION_KEY:
            raise ValueError("ENCRYPTION_KEY is required")

    def build_connection_string(
            self,
            connection_data: Dict[str, Any],
            async_mode: bool = True
    ) -> str:
        """Build database connection string"""
        db_type = connection_data.get('type', 'postgresql').lower()
        if db_type not in self.SUPPORTED_DATABASES:
            raise ValueError(f"Unsupported database type: {db_type}")

        db_info = self.SUPPORTED_DATABASES[db_type]
        driver = db_info['async_driver' if async_mode else 'sync_driver']

        if async_mode and not driver:
            raise ValueError(f"Async mode not supported for {db_type}")

        # Decrypt credentials
        creds = self.decrypt_credentials(connection_data['credentials'])

        # Build connection args
        conn_args = {
            'host': connection_data.get('host', 'localhost'),
            'port': connection_data.get('port', db_info['default_port']),
            'database': connection_data['database'],
            'user': creds['username'],
            'password': creds['password']
        }

        # Add SSL if required
        if self.SECURITY.SSL_REQUIRED:
            conn_args['sslmode'] = 'require' if self.SECURITY.VERIFY_SSL else 'prefer'

        # Build string
        conn_str = f"{driver}://"
        conn_str += f"{conn_args['user']}:{conn_args['password']}"
        conn_str += f"@{conn_args['host']}:{conn_args['port']}"
        conn_str += f"/{conn_args['database']}"

        # Add query parameters
        query_params = []
        if 'sslmode' in conn_args:
            query_params.append(f"sslmode={conn_args['sslmode']}")
        if self.CONNECTION.ECHO_SQL:
            query_params.append("echo=true")

        if query_params:
            conn_str += "?" + "&".join(query_params)

        return conn_str

    def encrypt_credentials(self, credentials: Dict[str, str]) -> Dict[str, bytes]:
        """Encrypt database credentials"""
        try:
            return {
                key: self.cipher_suite.encrypt(str(value).encode())
                for key, value in credentials.items()
            }
        except Exception as e:
            raise ValueError(f"Credential encryption failed: {str(e)}")

    def decrypt_credentials(self, encrypted_creds: Dict[str, bytes]) -> Dict[str, str]:
        """Decrypt database credentials"""
        try:
            return {
                key: self.cipher_suite.decrypt(value).decode()
                for key, value in encrypted_creds.items()
            }
        except Exception as e:
            raise ValueError(f"Credential decryption failed: {str(e)}")

    def get_pool_config(self) -> Dict[str, Any]:
        """Get connection pool configuration"""
        return {
            'pool_size': self.CONNECTION.MAX_POOL_SIZE,
            'max_overflow': self.CONNECTION.MAX_OVERFLOW,
            'pool_timeout': self.CONNECTION.POOL_TIMEOUT,
            'pool_recycle': self.CONNECTION.POOL_RECYCLE
        }

    def get_executor_config(self) -> Dict[str, Any]:
        """Get query executor configuration"""
        return {
            'timeout': self.QUERY.QUERY_TIMEOUT,
            'max_rows': self.QUERY.MAX_ROWS,
            'chunk_size': self.QUERY.CHUNK_SIZE,
            'fetch_size': self.QUERY.FETCH_SIZE
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> Config:
        """Create configuration from dictionary"""
        connection_settings = ConnectionSettings(
            **config_dict.get('CONNECTION', {})
        )
        query_settings = QuerySettings(
            **config_dict.get('QUERY', {})
        )
        security_settings = SecuritySettings(
            **config_dict.get('SECURITY', {})
        )
        monitoring_settings = MonitoringSettings(
            **config_dict.get('MONITORING', {})
        )

        return cls(
            connection_settings=connection_settings,
            query_settings=query_settings,
            security_settings=security_settings,
            monitoring_settings=monitoring_settings
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'CONNECTION': {
                field.name: getattr(self.CONNECTION, field.name)
                for field in self.CONNECTION.__dataclass_fields__
            },
            'QUERY': {
                field.name: getattr(self.QUERY, field.name)
                for field in self.QUERY.__dataclass_fields__
            },
            'SECURITY': {
                field.name: getattr(self.SECURITY, field.name)
                for field in self.SECURITY.__dataclass_fields__
                if field.name != 'ENCRYPTION_KEY'
            },
            'MONITORING': {
                field.name: getattr(self.MONITORING, field.name)
                for field in self.MONITORING.__dataclass_fields__
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