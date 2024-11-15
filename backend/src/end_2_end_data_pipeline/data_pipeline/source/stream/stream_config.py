# stream_config.py
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class ValidationConfig:
    """Configuration for stream data validation"""
    source_health_threshold: float = 0.9
    schema_validation: bool = True
    data_quality_checks: Dict[str, Any] = None

@dataclass
class StreamConfig:
    """Configuration class for stream processing"""
    bootstrap_servers: str
    group_id: str
    topic: str
    validation_config: Optional[Dict[str, Any]] = None
    auth_config: Optional[Dict[str, str]] = None
    consumer_config: Optional[Dict[str, Any]] = None
    poll_timeout: float = 1.0
    max_poll_records: int = 500

    def get_consumer_config(self) -> Dict[str, Any]:
        """
        Get Kafka consumer configuration.

        Returns:
            Dict[str, Any]: Configuration dictionary for Kafka consumer
        """
        config = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'enable.auto.commit': False,
            'max.poll.records': self.max_poll_records,
            'auto.offset.reset': 'earliest'
        }

        # Include authentication configuration if provided
        if self.auth_config:
            config.update(self.auth_config)

        # Include additional consumer configuration if provided
        if self.consumer_config:
            config.update(self.consumer_config)

        return config


