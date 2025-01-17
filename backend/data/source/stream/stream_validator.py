# backend/source_handlers/stream/stream_validator.py

import logging
import socket
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto

import pika
from confluent_kafka import Consumer, Producer

logger = logging.getLogger(__name__)


class StreamType(Enum):
    """Enumeration of supported stream types"""
    KAFKA = auto()
    RABBITMQ = auto()


@dataclass
class StreamValidationConfig:
    """Configuration for stream source validation"""

    # Stream type configurations
    supported_stream_types: set[StreamType] = field(default_factory=lambda: {
        StreamType.KAFKA, StreamType.RABBITMQ
    })

    # Connection settings
    connection_timeout: int = 5  # seconds
    default_ports: Dict[StreamType, int] = field(default_factory=lambda: {
        StreamType.KAFKA: 9092,
        StreamType.RABBITMQ: 5672
    })

    # Validation constraints
    min_host_length: int = 1
    max_host_length: int = 255

    # Security and sensitive information
    blocked_patterns: list[str] = field(default_factory=lambda: [
        r'password', r'secret', r'key', r'token', r'credential'
    ])

    # Required fields per stream type
    required_fields: Dict[StreamType, list[str]] = field(default_factory=lambda: {
        StreamType.KAFKA: ['bootstrap_servers', 'group_id'],
        StreamType.RABBITMQ: ['host']
    })


class StreamSourceValidator:
    """Enhanced stream source validator with integrated config"""

    def __init__(self, config: Optional[StreamValidationConfig] = None):
        self.config = config or StreamValidationConfig()

    async def validate_source(
            self,
            source_data: Dict[str, Any],
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of stream source configuration

        Args:
            source_data: Stream source configuration
            metadata: Additional metadata for validation

        Returns:
            Validation result with issues and warnings
        """
        try:
            issues = []
            warnings = []

            # Validate stream type
            stream_type_validation = await self._validate_stream_type(
                source_data.get('stream_type', '')
            )
            issues.extend(stream_type_validation.get('issues', []))
            warnings.extend(stream_type_validation.get('warnings', []))

            # If stream type is invalid, return early
            if issues:
                return self._build_result(
                    passed=False,
                    issues=issues,
                    warnings=warnings
                )

            # Parse stream type
            stream_type = StreamType[source_data['stream_type'].upper()]

            # Validate required fields
            required_fields_validation = await self._validate_required_fields(
                source_data, stream_type
            )
            issues.extend(required_fields_validation.get('issues', []))
            warnings.extend(required_fields_validation.get('warnings', []))

            # Validate connection details based on stream type
            if stream_type == StreamType.KAFKA:
                connection_validation = await self._validate_kafka_connection(source_data)
            elif stream_type == StreamType.RABBITMQ:
                connection_validation = await self._validate_rabbitmq_connection(source_data)
            else:
                connection_validation = {
                    'issues': ["Unsupported stream type"],
                    'warnings': []
                }

            issues.extend(connection_validation.get('issues', []))
            warnings.extend(connection_validation.get('warnings', []))

            return self._build_result(
                passed=len(issues) == 0,
                issues=issues,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Stream source validation error: {str(e)}")
            return self._build_result(
                passed=False,
                issues=[str(e)],
                warnings=[]
            )

    async def _validate_stream_type(self, stream_type: str) -> Dict[str, Any]:
        """Validate stream type"""
        issues = []
        warnings = []

        # Check for empty stream type
        if not stream_type:
            issues.append("Stream type is required")
            return {'issues': issues, 'warnings': warnings}

        # Normalize stream type
        stream_type = stream_type.upper()

        try:
            parsed_stream_type = StreamType[stream_type]

            # Check if stream type is supported
            if parsed_stream_type not in self.config.supported_stream_types:
                issues.append(f"Unsupported stream type: {stream_type}")
                issues.append(f"Supported types: {', '.join(t.name for t in self.config.supported_stream_types)}")

        except KeyError:
            issues.append(f"Invalid stream type: {stream_type}")

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_required_fields(
            self,
            source_data: Dict[str, Any],
            stream_type: StreamType
    ) -> Dict[str, Any]:
        """Validate required fields for specific stream type"""
        issues = []
        warnings = []

        # Get required fields for this stream type
        required_fields = self.config.required_fields.get(stream_type, [])

        # Check for missing required fields
        missing_fields = [
            field for field in required_fields
            if field not in source_data or not source_data[field]
        ]

        if missing_fields:
            issues.append(f"Missing required fields: {', '.join(missing_fields)}")

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_kafka_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate Kafka connection details"""
        issues = []
        warnings = []

        try:
            # Validate bootstrap servers
            servers = config['bootstrap_servers']
            if isinstance(servers, str):
                servers = [s.strip() for s in servers.split(',')]

            # Check each server's connectivity
            for server in servers:
                try:
                    host, port = server.split(':')

                    # Validate port
                    port = int(port)
                    if not (0 < port <= 65535):
                        issues.append(f"Invalid port in server {server}")

                    # Check connectivity
                    with socket.create_connection((host, port), timeout=self.config.connection_timeout):
                        pass

                except ValueError:
                    issues.append(f"Invalid server format: {server}")
                except (socket.timeout, socket.error):
                    warnings.append(f"Unreachable server: {server}")

        except KeyError:
            issues.append("Bootstrap servers not specified")
        except Exception as e:
            issues.append(f"Kafka connection validation error: {str(e)}")

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_rabbitmq_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate RabbitMQ connection details"""
        issues = []
        warnings = []

        try:
            # Validate host
            host = config.get('host')
            if not host:
                issues.append("Host is required")
                return {'issues': issues, 'warnings': warnings}

            # Get port (use default if not specified)
            port = config.get('port', self.config.default_ports[StreamType.RABBITMQ])

            # Validate host connectivity
            try:
                with socket.create_connection((host, port), timeout=self.config.connection_timeout):
                    pass
            except (socket.timeout, socket.error):
                issues.append(f"Cannot connect to RabbitMQ server at {host}:{port}")

            # Optionally validate credentials
            username = config.get('username', 'guest')
            password = config.get('password', 'guest')

            # Check for sensitive information in credentials
            for cred_type, cred_value in [('username', username), ('password', password)]:
                if any(re.search(pattern, str(cred_value), re.IGNORECASE)
                       for pattern in self.config.blocked_patterns):
                    warnings.append(f"Potential sensitive information in {cred_type}")

        except Exception as e:
            issues.append(f"RabbitMQ connection validation error: {str(e)}")

        return {
            'issues': issues,
            'warnings': warnings
        }

    def _build_result(
            self,
            passed: bool,
            issues: list[str],
            warnings: list[str]
    ) -> Dict[str, Any]:
        """Build structured validation result"""
        return {
            'passed': passed,
            'issues': issues,
            'warnings': warnings,
            'validation_time': datetime.utcnow().isoformat()
        }