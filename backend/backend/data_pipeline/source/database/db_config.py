from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import os
from cryptography.fernet import Fernet
from backend.backend.data_pipeline.exceptions import DatabaseConfigError, DataPipelineError
from .db_types import DatabaseType


@dataclass
class DatabaseConfig:
    """Database configuration with encryption support"""

    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_enabled: bool = False
    ssl_ca_cert: Optional[Path] = None
    connection_timeout: int = 30
    _fernet: Optional[Fernet] = None

    def __init__(self, encryption_key: str = None, **kwargs):
        """Initialize the database config and optionally set up encryption"""
        self._fernet = None
        if encryption_key:
            self._fernet = Fernet(encryption_key.encode())
        self.db_type = kwargs.get('db_type')
        self.host = kwargs.get('host')
        self.port = kwargs.get('port')
        self.database = kwargs.get('database')
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        self.ssl_enabled = kwargs.get('ssl_enabled', False)
        self.ssl_ca_cert = kwargs.get('ssl_ca_cert', None)
        self.connection_timeout = kwargs.get('connection_timeout', 30)

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'DatabaseConfig':
        """Create instance from configuration dictionary"""
        try:
            db_type = DatabaseType.from_string(config['db_type'])
            return cls(
                db_type=db_type,
                host=config['host'],
                port=int(config['port']),
                database=config['database'],
                username=config.get('username') or config.get('user'),  # Allow 'user' as an alias
                password=config['password'],
                ssl_enabled=config.get('ssl_enabled', False),
                ssl_ca_cert=Path(config['ssl_ca_cert']) if config.get('ssl_ca_cert') else None,
                connection_timeout=int(config.get('connection_timeout', 30))
            )
        except (KeyError, ValueError) as e:
            raise DatabaseConfigError(f"Invalid configuration: {str(e)}")

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'DatabaseConfig':
        """Create instance from YAML file"""
        try:
            with open(yaml_path) as f:
                config = yaml.safe_load(f)
            return cls.from_dict(config)
        except Exception as e:
            raise DatabaseConfigError(f"Failed to load config from {yaml_path}: {str(e)}")

    def _setup_encryption(self) -> None:
        """Set up encryption using environment key"""
        try:
            key = os.environ.get('DB_ENCRYPTION_KEY')
            if not key:
                key = Fernet.generate_key()
                os.environ['DB_ENCRYPTION_KEY'] = key.decode()
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise DatabaseConfigError(f"Encryption setup failed: {str(e)}")

    def _encrypt_value(self, value: str) -> str:
        """Encrypt a string value"""
        if not value:
            return value
        if not self._fernet:
            raise DatabaseConfigError("Encryption key is not set up.")
        try:
            return self._fernet.encrypt(value.encode()).decode()
        except Exception as e:
            raise DatabaseConfigError(f"Encryption failed: {str(e)}")

    def _decrypt_value(self, value: str) -> str:
        """Decrypt an encrypted string value"""
        if not value or not self._fernet:
            return value  # Return the original value if decryption isn't possible
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except Exception as e:
            raise DataPipelineError(f"Failed to decrypt value: {e}")

    def get_connection_params(self) -> Dict[str, Any]:
        """Get decrypted connection parameters"""
        params = {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.username,
            'password': self._decrypt_value(self.password),
            'connect_timeout': self.connection_timeout
        }

        if self.ssl_enabled and self.ssl_ca_cert:
            params['ssl'] = {'ca': str(self.ssl_ca_cert)}

        return params
