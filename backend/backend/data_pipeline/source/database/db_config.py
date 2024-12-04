# db_config.py
from typing import Dict, Any
from cryptography.fernet import Fernet
import os


class Config:
    """Configuration for database connections"""

    SUPPORTED_DATABASES = {
        'postgresql': 'postgresql',
        'mysql': 'mysql+pymysql',
        'mssql': 'mssql+pyodbc',
        'oracle': 'oracle+cx_oracle'
    }

    # Connection settings
    MAX_POOL_SIZE = 20
    POOL_TIMEOUT = 30
    MAX_OVERFLOW = 10
    POOL_RECYCLE = 3600

    # Query settings
    QUERY_TIMEOUT = 300  # seconds
    MAX_ROWS = 1000000  # Maximum rows per query
    CHUNK_SIZE = 10000  # Rows per chunk for large queries

    # Security
    ENCRYPTION_KEY = os.getenv('DB_ENCRYPTION_KEY', Fernet.generate_key())
    cipher_suite = Fernet(ENCRYPTION_KEY)

    @classmethod
    def encrypt_credentials(cls, credentials: Dict[str, str]) -> Dict[str, bytes]:
        """Encrypt database credentials"""
        return {
            key: cls.cipher_suite.encrypt(str(value).encode())
            for key, value in credentials.items()
        }

    @classmethod
    def decrypt_credentials(cls, encrypted_creds: Dict[str, bytes]) -> Dict[str, str]:
        """Decrypt database credentials"""
        return {
            key: cls.cipher_suite.decrypt(value).decode()
            for key, value in encrypted_creds.items()
        }

    @classmethod
    def build_connection_string(cls, config: Dict[str, Any]) -> str:
        """Build database connection string"""
        db_type = config.get('type', 'postgresql')
        if db_type not in cls.SUPPORTED_DATABASES:
            raise ValueError(f"Unsupported database type: {db_type}")

        driver = cls.SUPPORTED_DATABASES[db_type]
        creds = cls.decrypt_credentials(config['credentials'])

        return f"{driver}://{creds['username']}:{creds['password']}@{config['host']}:{config['port']}/{config['database']}"

