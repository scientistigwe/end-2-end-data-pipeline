# api_service.py

from __future__ import annotations

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass, field

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    ComponentType,
    MessageType,
    ProcessingMessage,
    ModuleIdentifier,
    ProcessingStage,
    ProcessingStatus
)
from backend.core.orchestration.data_conductor import DataConductor
from backend.core.orchestration.staging_manager import StagingManager
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.monitoring.process import ProcessMonitor
from backend.core.monitoring.collectors import MetricsCollector
from backend.core.utils.process_manager import ProcessManager, ProcessContext

from .api_validator import APIValidator
from .api_config import Config
from .api_fetcher import APIFetcher

logger = logging.getLogger(__name__)


@dataclass
class APIProcessContext:
    """Context for API operations"""
    request_id: str
    pipeline_id: str
    stage: ProcessingStage
    status: ProcessingStatus
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    control_points: List[str] = field(default_factory=list)


class APIService:
    """API service for data sourcing through CPM"""

    def __init__(
            self,
            message_broker: Optional[MessageBroker] = None,
            control_point_manager: Optional[ControlPointManager] = None,
            validator: Optional[APIValidator] = None,
            config: Optional[Config] = None,
            metrics_collector: Optional[MetricsCollector] = None
    ):
        # Core components
        self.message_broker = message_broker or MessageBroker()
        self.control_point_manager = control_point_manager or ControlPointManager(
            message_broker=self.message_broker
        )
        self.config = config or Config()
        self.metrics_collector = metrics_collector or MetricsCollector()

        # Initialize validator
        self.validator = validator or APIValidator(
            config=self.config,
            metrics_collector=self.metrics_collector
        )

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="api_service",
            source_id=str(uuid4())
        )

        # Operation tracking
        self.active_operations: Dict[str, APIProcessContext] = {}

        # Register handlers with CPM
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register handlers with Control Point Manager"""
        handlers = {
            'api.request.start': self._handle_request_start,
            'api.request.complete': self._handle_request_complete,
            'api.request.error': self._handle_request_error,
            'api.validation.complete': self._handle_validation_complete
        }

        # Register with CPM
        self.control_point_manager.register_handler(
            source_type='api',
            handlers=handlers
        )

    async def source_data(
            self,
            endpoint: str,
            method: str = 'GET',
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, Any]] = None,
            data: Optional[Dict[str, Any]] = None,
            user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Source data from API through CPM"""
        # Create process context
        context = APIProcessContext(
            request_id=str(uuid4()),
            pipeline_id=str(uuid4()),
            stage=ProcessingStage.INITIAL_VALIDATION,
            status=ProcessingStatus.PENDING,
            metadata={
                'user_id': user_id,
                'source_type': 'api',
                'endpoint': endpoint,
                'method': method
            }
        )
        self.active_operations[context.request_id] = context

        try:
            # Create validation control point
            validation_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.INITIAL_VALIDATION,
                data={
                    'endpoint': endpoint,
                    'method': method,
                    'params': params,
                    'headers': headers,
                    'metadata': context.metadata
                },
                options=['proceed', 'reject']
            )

            # Wait for validation decision
            decision = await self.control_point_manager.wait_for_decision(
                validation_point.id,
                timeout=self.config.VALIDATION_TIMEOUT
            )

            if decision.decision == 'proceed':
                # Create processing control point
                process_point = await self.control_point_manager.create_control_point(
                    pipeline_id=context.pipeline_id,
                    stage=ProcessingStage.PROCESSING,
                    data={
                        'request_id': context.request_id,
                        'endpoint': endpoint,
                        'method': method,
                        'params': params,
                        'headers': headers,
                        'data': data,
                        'metadata': context.metadata
                    },
                    options=['process']
                )

                return {
                    'status': 'processing',
                    'request_id': context.request_id,
                    'pipeline_id': context.pipeline_id
                }

            else:
                context.status = ProcessingStatus.REJECTED
                context.error = decision.details.get('reason', 'Request rejected')
                return {
                    'status': 'rejected',
                    'reason': context.error
                }

        except Exception as e:
            logger.error(f"API request error: {str(e)}", exc_info=True)

            context.status = ProcessingStatus.FAILED
            context.error = str(e)

            return {
                'status': 'error',
                'error': str(e)
            }

    async def update_credentials(
            self,
            credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update API credentials
        
        Args:
            credentials: New API credentials
            
        Returns:
            Status of the update operation
        """
        try:
            # Validate credentials
            validation_result = await self.validator.validate_auth_config(credentials)
            if not validation_result.passed:
                raise ValueError(
                    f"Credential validation failed: {validation_result.message}"
                )

            # Update config with new credentials
            self.config.update(**credentials)

            return {
                'status': 'success',
                'message': 'Credentials updated successfully'
            }

        except Exception as e:
            logger.error(f"Credential update error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    def list_sources(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List API sources for a specific user
        
        Args:
            user_id: User's unique identifier
        
        Returns:
            List of API sources
        """
        try:
            sources = [
                {
                    'id': operation.request_id,
                    'pipeline_id': operation.pipeline_id,
                    'created_at': operation.created_at.isoformat(),
                    'status': operation.status.value,
                    'stage': operation.stage.value,
                    'error': operation.error,
                    'endpoint': operation.metadata.get('endpoint')
                }
                for operation in self.active_operations.values()
                if operation.metadata.get('user_id') == user_id
            ]
            
            return sources
        except Exception as e:
            logger.error(f"Error listing API sources: {str(e)}", exc_info=True)
            return []
        
    async def list_active_operations(self) -> List[Dict[str, Any]]:
        """List all active API operations"""
        return [
            {
                'request_id': operation.request_id,
                'pipeline_id': operation.pipeline_id,
                'status': operation.status.value,
                'stage': operation.stage.value,
                'created_at': operation.created_at.isoformat(),
                'error': operation.error
            }
            for operation in self.active_operations.values()
        ]

    async def cancel_operation(self, request_id: str) -> Dict[str, Any]:
        """Cancel an active API operation"""
        try:
            context = self.active_operations.get(request_id)
            if not context:
                return {
                    'status': 'error',
                    'message': f'Operation {request_id} not found'
                }

            # Update status
            context.status = ProcessingStatus.CANCELLED

            # Remove from active operations
            del self.active_operations[request_id]

            return {
                'status': 'success',
                'message': f'Operation {request_id} cancelled'
            }

        except Exception as e:
            logger.error(f"Operation cancellation error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    async def cleanup(self) -> None:
        """Clean up service resources"""
        try:
            # Clear all active operations
            self.active_operations.clear()
            
            logger.info("APIService resources cleaned up")

        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}", exc_info=True)