# backend/core/services/base/base_service.py

import logging
from typing import Dict, Any
from datetime import datetime

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ModuleIdentifier,
    MessageMetadata,
    ProcessingStage,
    BaseContext
)

logger = logging.getLogger(__name__)


class BaseService:
    """Base class for all services providing common functionality."""

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self._is_initialized = False
        self._active_requests: Dict[str, BaseContext] = {}
        self._last_health_check = None
        self._status = {"is_healthy": True, "status": "operational", "errors": []}
        self.module_identifier: ModuleIdentifier = None  # Will be set by child classes

    async def initialize(self) -> None:
        """Initialize service and subscribe to required messages."""
        try:
            if not self.module_identifier:
                raise ValueError("module_identifier must be set by child class")

            # Subscribe to health checks
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=[
                    MessageType.GLOBAL_HEALTH_CHECK.value,
                    f"{self.department}.{MessageType.GLOBAL_HEALTH_CHECK.value}"
                ],
                callback=self.handle_health_check
            )

            self._is_initialized = True
            logger.info(f"{self.department} service initialized successfully")

        except Exception as e:
            logger.error(f"Service initialization failed: {str(e)}")
            raise

    async def handle_health_check(self, message: ProcessingMessage) -> None:
        """Handle health check request."""
        try:
            health_status = await self.get_health_status()

            # Create health check response
            response = ProcessingMessage(
                message_type=MessageType.GLOBAL_STATUS_RESPONSE,
                content={
                    'status': health_status['status'],
                    'is_healthy': health_status['is_healthy'],
                    'department': self.department,
                    'active_requests': len(self._active_requests),
                    'last_health_check': self._last_health_check.isoformat() if self._last_health_check else None,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=message.metadata.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component=message.metadata.source_component,
                    domain_type=self.department,
                    processing_stage=ProcessingStage.PROCESSING
                ),
                source_identifier=self.module_identifier,
                target_identifier=message.source_identifier
            )

            # Send response
            await self.message_broker.publish(response)
            self._last_health_check = datetime.now()

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            await self._handle_health_check_error(message, str(e))

    async def get_health_status(self) -> Dict[str, Any]:
        """Get current service health status."""
        return {
            'is_healthy': self._status['is_healthy'],
            'status': self._status['status'],
            'errors': self._status['errors'],
            'active_requests': len(self._active_requests),
            'uptime': (datetime.now() - self._last_health_check).total_seconds() if self._last_health_check else 0,
            'component_type': self.module_identifier.component_type.value if self.module_identifier else None,
            'department': self.department
        }

    async def _handle_health_check_error(self, message: ProcessingMessage, error: str) -> None:
        """Handle health check error."""
        try:
            error_response = ProcessingMessage(
                message_type=MessageType.GLOBAL_ERROR_NOTIFY,
                content={
                    'status': 'error',
                    'is_healthy': False,
                    'department': self.department,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=message.metadata.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component=message.metadata.source_component,
                    domain_type=self.department,
                    processing_stage=ProcessingStage.PROCESSING
                ),
                source_identifier=self.module_identifier,
                target_identifier=message.source_identifier
            )
            await self.message_broker.publish(error_response)

        except Exception as e:
            logger.error(f"Error handling health check error: {str(e)}")

    @property
    def department(self) -> str:
        """Get service department name."""
        return self.module_identifier.department if self.module_identifier else None

    async def cleanup(self) -> None:
        """Cleanup service resources."""
        try:
            self._is_initialized = False
            self._active_requests.clear()
            self._status['is_healthy'] = False
            self._status['status'] = 'shutdown'

            # Unsubscribe from all handlers
            if self.module_identifier:
                await self.message_broker.unsubscribe(self.module_identifier)

            logger.info(f"{self.department} service cleaned up successfully")

        except Exception as e:
            logger.error(f"Service cleanup failed: {str(e)}")
            raise