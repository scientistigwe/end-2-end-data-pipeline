# s3_config.py
from typing import Dict, Any
from cryptography.fernet import Fernet
import os


class Config:
    """Configuration for S3 operations"""

    # S3 Settings
    SUPPORTED_FORMATS = ['csv', 'json', 'parquet', 'xlsx']
    MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
    CHUNK_SIZE = 8 * 1024 * 1024  # 8MB for multipart
    MULTIPART_THRESHOLD = 100 * 1024 * 1024  # 100MB
    MAX_POOL_CONNECTIONS = 100

    # AWS Specific
    DEFAULT_REGION = 'us-east-1'
    AWS_ENDPOINTS = {
        'us-east-1': 's3.amazonaws.com',
        'us-west-2': 's3.us-west-2.amazonaws.com'
    }

    # Security
    ENCRYPTION_KEY = os.getenv('S3_ENCRYPTION_KEY', Fernet.generate_key())
    cipher_suite = Fernet(ENCRYPTION_KEY)

    @classmethod
    def encrypt_credentials(cls, credentials: Dict[str, str]) -> Dict[str, bytes]:
        """Encrypt AWS credentials"""
        return {
            key: cls.cipher_suite.encrypt(str(value).encode())
            for key, value in credentials.items()
        }

    @classmethod
    def decrypt_credentials(cls, encrypted_creds: Dict[str, bytes]) -> Dict[str, str]:
        """Decrypt AWS credentials"""
        return {
            key: cls.cipher_suite.decrypt(value).decode()
            for key, value in encrypted_creds.items()
        }


