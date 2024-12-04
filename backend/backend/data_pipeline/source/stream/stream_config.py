# stream_config.py
from typing import Dict, Any
from cryptography.fernet import Fernet
import os

class Config:
    """Configuration for stream operations"""
    
    # Supported Stream Types
    STREAM_TYPES = {
        'kafka': {
            'required_fields': ['bootstrap_servers', 'topics', 'group_id'],
            'optional_fields': ['auto_offset_reset', 'enable_auto_commit']
        },
        'rabbitmq': {
            'required_fields': ['host', 'queue', 'exchange'],
            'optional_fields': ['port', 'virtual_host', 'routing_key']
        }
    }
    
    # Default Settings
    DEFAULT_BATCH_SIZE = 1000
    CONSUMER_TIMEOUT_MS = 5000
    MAX_POLL_RECORDS = 500
    HEARTBEAT_INTERVAL_MS = 3000
    
    # Encryption for credentials
    ENCRYPTION_KEY = os.getenv('STREAM_ENCRYPTION_KEY', Fernet.generate_key())
    cipher_suite = Fernet(ENCRYPTION_KEY)
    
    @classmethod
    def encrypt_credentials(cls, credentials: Dict[str, str]) -> Dict[str, bytes]:
        """Encrypt stream credentials"""
        return {
            key: cls.cipher_suite.encrypt(str(value).encode())
            for key, value in credentials.items()
        }
    
    @classmethod
    def decrypt_credentials(cls, encrypted_creds: Dict[str, bytes]) -> Dict[str, str]:
        """Decrypt stream credentials"""
        return {
            key: cls.cipher_suite.decrypt(value).decode()
            for key, value in encrypted_creds.items()
        }

