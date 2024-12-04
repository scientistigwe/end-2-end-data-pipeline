# api_config.py
from typing import Dict, Any
from cryptography.fernet import Fernet
import os


class Config:
    """Configuration and validation for API connections."""

    ALLOWED_METHODS = ['GET', 'POST', 'PUT', 'DELETE']
    REQUEST_TIMEOUT = 30  # Default timeout in seconds
    MAX_RETRIES = 3
    BATCH_SIZE = 1000  # For paginated responses

    # Security settings
    ENCRYPTION_KEY = os.getenv('API_ENCRYPTION_KEY', Fernet.generate_key())
    cipher_suite = Fernet(ENCRYPTION_KEY)

    def __init__(self, **kwargs):
        """Initialize Config with optional overrides."""
        for key, value in kwargs.items():
            if hasattr(Config, key):
                setattr(Config, key, value)

    @classmethod
    def encrypt_credentials(cls, credentials: Dict[str, str]) -> Dict[str, bytes]:
        """Encrypt sensitive API credentials."""
        return {
            key: cls.cipher_suite.encrypt(value.encode())
            for key, value in credentials.items()
        }

    @classmethod
    def decrypt_credentials(cls, encrypted_creds: Dict[str, bytes]) -> Dict[str, str]:
        """Decrypt API credentials."""
        return {
            key: cls.cipher_suite.decrypt(value).decode()
            for key, value in encrypted_creds.items()
        }
