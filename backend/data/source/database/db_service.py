from __future__ import annotations

import logging
import asyncio
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from uuid import uuid4

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
from backend.core.orchestration.pipeline_manager import PipelineManager
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.monitoring.process import ProcessMonitor
from backend.core.monitoring.collectors import MetricsCollector
from backend.core.utils.process_manager import ProcessManager

from .db_validator import DatabaseSourceValidator
from .db_config import DatabaseSourceConfig
from .db_fetcher import DBFetcher

logger = logging.getLogger(__name__)


@dataclass
class DBProcessContext:
    """Context for db operations"""
    request_id: str
    pipeline_id: str
    stage: ProcessingStage
    status: ProcessingStatus
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    control_points: List[str] = field(default_factory=list)


class DBService:
    """Database service for data sourcing through CPM"""

    def __init__(
            self,
            message_broker: Optional[MessageBroker] = None,
            control_point_manager: Optional[ControlPointManager] = None,
            config: Optional[DatabaseSourceConfig] = None,
            metrics_collector: Optional[MetricsCollector] = None,
    ):
        # Core components
        self.message_broker = message_broker or MessageBroker()
        self.control_point_manager = control_point_manager or ControlPointManager(
            message_broker=self.message_broker
        )
        self.config = config or DatabaseSourceConfig()
        self.metrics_collector = metrics_collector or MetricsCollector()

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="database_service",
            source_id=str(uuid4())
        )

        # Operation tracking
        self.active_operations: Dict[str, DBProcessContext] = {}

        # Register handlers with CPM
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register handlers with Control Point Manager"""
        handlers = {
            'db.request.start': self._handle_request_start,
            'db.request.complete': self._handle_request_complete,
            'db.request.error': self._handle_request_error,
            'db.validation.complete': self._handle_validation_complete
        }

        # Register with CPM
        self.control_point_manager.register_handler(
            source_type='db',
            handlers=handlers
        )

    async def source_data(
            self,
            connection_config: Dict[str, Any],
            query: str,
            user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Source data from db through CPM"""
        # Create process context
        context = DBProcessContext(
            request_id=str(uuid4()),
            pipeline_id=str(uuid4()),
            stage=ProcessingStage.INITIAL_VALIDATION,
            status=ProcessingStatus.PENDING,
            metadata={
                'user_id': user_id,
                'source_type': 'db'
            }
        )
        self.active_operations[context.request_id] = context

        try:
            # Create validation control point
            validation_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.INITIAL_VALIDATION,
                data={
                    'connection_config': {
                        k: v for k, v in connection_config.items()
                        if k not in ['password']  # Exclude sensitive info
                    },
                    'query': query,
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
                        'connection_config': connection_config,
                        'query': query,
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
            logger.error(f"Database request error: {str(e)}", exc_info=True)

            context.status = ProcessingStatus.FAILED
            context.error = str(e)

            return {
                'status': 'error',
                'error': str(e)
            }

    async def list_active_operations(self) -> List[Dict[str, Any]]:
        """List all active db operations"""
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
        """Cancel an active db operation"""
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

            logger.info("DBService resources cleaned up")

        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}", exc_info=True)