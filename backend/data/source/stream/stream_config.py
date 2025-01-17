from typing import Dict, Any
from cryptography.fernet import Fernet
import os

class Config:
    """Configuration for stream operations"""

    # Stream Types
    STREAM_TYPES = {
        'kafka': {
            'required_fields': ['bootstrap_servers', 'topics'],
            'optional_fields': ['group_id', 'client_id', 'auto_offset_reset']
        },
        'kinesis': {
            'required_fields': ['stream_name', 'region'],
            'optional_fields': ['shard_iterator_type', 'sequence_number']
        },
        'pubsub': {
            'required_fields': ['project_id', 'subscription_name'],
            'optional_fields': ['topic_name', 'credentials_path']
        }
    }

    # Default Settings
    DEFAULT_BATCH_SIZE = 100
    MAX_BATCH_SIZE = 1000
    CONNECTION_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_BACKOFF = 1.0

    # Consumer Settings
    CONSUMER_TIMEOUT_MS = 1000
    AUTO_COMMIT_INTERVAL_MS = 5000
    MAX_POLL_RECORDS = 500
    MAX_POLL_INTERVAL_MS = 300000

    # Security
    ENCRYPTION_KEY = os.getenv('STREAM_ENCRYPTION_KEY', Fernet.generate_key())
    cipher_suite = Fernet(ENCRYPTION_KEY)

    @classmethod
    def get_fetcher_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get configuration for stream fetcher"""
        stream_type = config.get('stream_type')
        if stream_type not in cls.STREAM_TYPES:
            raise ValueError(f"Unsupported stream type: {stream_type}")

        fetcher_config = {
            'stream_type': stream_type,
            'batch_size': config.get('batch_size', cls.DEFAULT_BATCH_SIZE),
            'timeout': config.get('timeout', cls.CONNECTION_TIMEOUT),
            'max_retries': config.get('max_retries', cls.MAX_RETRIES),
            'retry_backoff': config.get('retry_backoff', cls.RETRY_BACKOFF)
        }

        # Add type-specific configurations
        if stream_type == 'kafka':
            fetcher_config.update({
                'bootstrap_servers': config['bootstrap_servers'],
                'topics': config['topics'],
                'consumer_timeout_ms': cls.CONSUMER_TIMEOUT_MS,
                'auto_commit_interval_ms': cls.AUTO_COMMIT_INTERVAL_MS,
                'max_poll_records': cls.MAX_POLL_RECORDS
            })
        elif stream_type == 'kinesis':
            fetcher_config.update({
                'stream_name': config['stream_name'],
                'region': config['region']
            })
        elif stream_type == 'pubsub':
            fetcher_config.update({
                'project_id': config['project_id'],
                'subscription_name': config['subscription_name']
            })

        # Handle credentials
        if 'credentials' in config:
            fetcher_config['credentials'] = cls.encrypt_credentials(config['credentials'])

        return fetcher_config

    @classmethod
    def encrypt_credentials(cls, credentials: Dict[str, str]) -> Dict[str, bytes]:
        """Encrypt sensitive credentials"""
        return {
            key: cls.cipher_suite.encrypt(str(value).encode())
            for key, value in credentials.items()
        }

    @classmethod
    def decrypt_credentials(cls, encrypted_creds: Dict[str, bytes]) -> Dict[str, str]:
        """Decrypt credentials"""
        return {
            key: cls.cipher_suite.decrypt(value).decode()
            for key, value in encrypted_creds.items()
        }

    @classmethod
    def get_consumer_config(cls, stream_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get consumer-specific configuration"""
        if stream_type == 'kafka':
            return {
                'group.id': config.get('group_id', f'group_{os.getpid()}'),
                'auto.offset.reset': config.get('auto_offset_reset', 'latest'),
                'enable.auto.commit': config.get('enable_auto_commit', True),
                'max.poll.records': config.get('max_poll_records', cls.MAX_POLL_RECORDS),
                'max.poll.interval.ms': cls.MAX_POLL_INTERVAL_MS
            }
        elif stream_type == 'kinesis':
            return {
                'shard_iterator_type': config.get('shard_iterator_type', 'TRIM_HORIZON'),
                'sequence_number': config.get('sequence_number')
            }
        elif stream_type == 'pubsub':
            return {
                'ack_deadline_seconds': config.get('ack_deadline_seconds', 10),
                'max_outstanding_messages': config.get('max_outstanding_messages', 1000)
            }
        return {}