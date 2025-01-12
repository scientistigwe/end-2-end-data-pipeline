from typing import Tuple, Dict, Any, Optional, List
import logging
from dataclasses import dataclass
from confluent_kafka import Consumer, Producer, KafkaError
import pika
from enum import Enum, auto
import socket
import json

logger = logging.getLogger(__name__)

class StreamType(Enum):
    KAFKA = auto()
    RABBITMQ = auto()

@dataclass
class ValidationResult:
    is_valid: bool
    message: str
    details: Optional[Dict[str, Any]] = None

class StreamValidator:
    """Enhanced stream validation utilities with comprehensive checks"""

    DEFAULT_TIMEOUT = 5000  # 5 seconds
    
    @staticmethod
    def validate_stream_config(config: Dict[str, Any]) -> ValidationResult:
        """
        Validate stream configuration with detailed checks
        
        Args:
            config: Dictionary containing stream configuration
            
        Returns:
            ValidationResult object containing validation status and details
        """
        try:
            # Validate basic structure
            if not isinstance(config, dict):
                return ValidationResult(False, "Configuration must be a dictionary")

            # Validate stream type
            stream_type = config.get('stream_type', '').upper()
            try:
                stream_type_enum = StreamType[stream_type]
            except KeyError:
                return ValidationResult(
                    False,
                    f"Invalid stream type: {stream_type}. Must be one of: {', '.join(t.name for t in StreamType)}"
                )

            # Validate required fields based on stream type
            validation_result = StreamValidator._validate_required_fields(config, stream_type_enum)
            if not validation_result.is_valid:
                return validation_result

            # Validate field types and formats
            return StreamValidator._validate_field_types(config, stream_type_enum)

        except Exception as e:
            logger.exception("Configuration validation error")
            return ValidationResult(False, f"Configuration validation error: {str(e)}")

    @staticmethod
    def validate_kafka_connection(config: Dict[str, Any]) -> ValidationResult:
        """
        Validate Kafka connection with comprehensive checks using confluent-kafka
        
        Args:
            config: Kafka configuration dictionary
            
        Returns:
            ValidationResult object containing validation status and details
        """
        try:
            # Validate bootstrap servers format
            servers = config['bootstrap_servers']
            if isinstance(servers, str):
                servers = [s.strip() for s in servers.split(',')]

            # Check each server's connectivity
            unreachable_servers = []
            for server in servers:
                host, port = server.split(':')
                try:
                    with socket.create_connection((host, int(port)), timeout=5):
                        pass
                except (socket.timeout, socket.error):
                    unreachable_servers.append(server)

            if unreachable_servers:
                return ValidationResult(
                    False,
                    "Some Kafka servers are unreachable",
                    {'unreachable_servers': unreachable_servers}
                )

            # Configure Kafka client
            kafka_config = {
                'bootstrap.servers': ','.join(servers),
                'group.id': config.get('group_id', 'test_group'),
                'socket.timeout.ms': str(StreamValidator.DEFAULT_TIMEOUT),
                'session.timeout.ms': '6000',
                'auto.offset.reset': 'earliest'
            }

            # Test producer connection
            producer = Producer({
                'bootstrap.servers': ','.join(servers),
                'socket.timeout.ms': str(StreamValidator.DEFAULT_TIMEOUT)
            })
            producer.flush(timeout=5)

            # Test consumer connection
            consumer = Consumer(kafka_config)
            consumer.close()

            return ValidationResult(True, "Kafka connection successful")

        except Exception as e:
            logger.exception("Kafka connection validation error")
            return ValidationResult(
                False,
                f"Kafka connection error: {str(e)}",
                {'error_type': type(e).__name__}
            )

    @staticmethod
    def validate_rabbitmq_connection(config: Dict[str, Any]) -> ValidationResult:
        """
        Validate RabbitMQ connection with comprehensive checks
        
        Args:
            config: RabbitMQ configuration dictionary
            
        Returns:
            ValidationResult object containing validation status and details
        """
        try:
            # Validate host connectivity first
            host = config['host']
            port = config.get('port', 5672)
            
            try:
                with socket.create_connection((host, port), timeout=5):
                    pass
            except (socket.timeout, socket.error) as e:
                return ValidationResult(
                    False,
                    f"Cannot connect to RabbitMQ server at {host}:{port}",
                    {'error': str(e)}
                )

            # Test full connection with credentials
            credentials = pika.PlainCredentials(
                config.get('username', 'guest'),
                config.get('password', 'guest')
            )
            
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=host,
                    port=port,
                    virtual_host=config.get('virtual_host', '/'),
                    credentials=credentials,
                    connection_attempts=3,
                    retry_delay=2
                )
            )
            
            # Test channel creation
            channel = connection.channel()
            connection.close()

            return ValidationResult(True, "RabbitMQ connection successful")

        except Exception as e:
            logger.exception("RabbitMQ connection validation error")
            return ValidationResult(
                False,
                f"RabbitMQ connection error: {str(e)}",
                {'error_type': type(e).__name__}
            )

    @staticmethod
    def _validate_required_fields(config: Dict[str, Any], stream_type: StreamType) -> ValidationResult:
        """Validate required fields based on stream type"""
        required_fields = {
            StreamType.KAFKA: ['bootstrap_servers', 'group_id'],
            StreamType.RABBITMQ: ['host']
        }

        missing_fields = [
            field for field in required_fields[stream_type]
            if field not in config
        ]

        if missing_fields:
            return ValidationResult(
                False,
                f"Missing required fields: {', '.join(missing_fields)}",
                {'missing_fields': missing_fields}
            )

        return ValidationResult(True, "All required fields present")

    @staticmethod
    def _validate_field_types(config: Dict[str, Any], stream_type: StreamType) -> ValidationResult:
        """Validate field types and formats"""
        if stream_type == StreamType.KAFKA:
            # Validate bootstrap_servers format
            servers = config['bootstrap_servers']
            if isinstance(servers, str):
                servers = [s.strip() for s in servers.split(',')]
            
            for server in servers:
                try:
                    host, port = server.split(':')
                    if not (0 < int(port) <= 65535):
                        return ValidationResult(
                            False,
                            f"Invalid port number in server address: {server}"
                        )
                except ValueError:
                    return ValidationResult(
                        False,
                        f"Invalid server address format: {server}. Expected format: host:port"
                    )

        return ValidationResult(True, "Field types and formats are valid")

    def validate_all(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Perform all validations for the given configuration
        
        Args:
            config: Stream configuration dictionary
            
        Returns:
            ValidationResult object containing validation status and details
        """
        # First validate configuration
        config_validation = self.validate_stream_config(config)
        if not config_validation.is_valid:
            return config_validation

        # Then validate connection based on stream type
        stream_type = StreamType[config['stream_type'].upper()]
        if stream_type == StreamType.KAFKA:
            return self.validate_kafka_connection(config)
        elif stream_type == StreamType.RABBITMQ:
            return self.validate_rabbitmq_connection(config)

        return ValidationResult(False, f"Unsupported stream type: {stream_type}")