# stream_validator.py
from typing import Tuple, Dict, Any
import logging
from kafka import KafkaConsumer
import pika
from .stream_config import Config

logger = logging.getLogger(__name__)

class StreamValidator:
    """Stream validation utilities"""

    @staticmethod
    def validate_stream_config(config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate stream configuration"""
        try:
            stream_type = config.get('stream_type')
            if stream_type not in Config.STREAM_TYPES:
                return False, f"Unsupported stream type: {stream_type}"

            # Check required fields
            required_fields = Config.STREAM_TYPES[stream_type]['required_fields']
            missing_fields = [field for field in required_fields
                            if field not in config]

            if missing_fields:
                return False, f"Missing required fields: {', '.join(missing_fields)}"

            return True, "Stream configuration is valid"

        except Exception as e:
            return False, f"Configuration validation error: {str(e)}"

    @staticmethod
    def validate_kafka_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate Kafka connection"""
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=config['bootstrap_servers'],
                group_id=config['group_id'],
                consumer_timeout_ms=Config.CONSUMER_TIMEOUT_MS
            )
            consumer.close()
            return True, "Kafka connection successful"
        except Exception as e:
            return False, f"Kafka connection error: {str(e)}"

    @staticmethod
    def validate_rabbitmq_connection(config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate RabbitMQ connection"""
        try:
            credentials = pika.PlainCredentials(
                config.get('username', 'guest'),
                config.get('password', 'guest')
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=config['host'],
                    port=config.get('port', 5672),
                    virtual_host=config.get('virtual_host', '/'),
                    credentials=credentials
                )
            )
            connection.close()
            return True, "RabbitMQ connection successful"
        except Exception as e:
            return False, f"RabbitMQ connection error: {str(e)}"
