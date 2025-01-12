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
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.monitoring.process import ProcessMonitor
from backend.core.utils.rate_limiter import AsyncRateLimiter
from backend.core.utils.process_manager import ProcessManager
from backend.core.monitoring.collectors import MetricsCollector
from .api_manager import APIManager
from .api_config import Config

logger = logging.getLogger(__name__)


@dataclass
class APIProcessContext:
    """Context for API processing"""
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
    """Enhanced API service with comprehensive control point integration"""

    def __init__(
            self,
            message_broker: MessageBroker,
            control_point_manager: Optional[ControlPointManager] = None,
            config: Optional[Config] = None,
            metrics_collector: Optional[MetricsCollector] = None,
    ):
        """Initialize APIService with required components"""
        self.message_broker = message_broker
        self.control_point_manager = control_point_manager or ControlPointManager(message_broker)
        self.config = config or Config()
        self.metrics_collector = metrics_collector

        # Initialize managers and handlers
        self.api_manager = APIManager(
            message_broker=self.message_broker,
            control_point_manager=self.control_point_manager,
            config=self.config
        )
        self.process_handler = ProcessManager(config=self.config.RETRY)

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="api_service",
            source_id=str(uuid4())
        )

        # Rate limiting
        self.rate_limiter = AsyncRateLimiter(
            max_calls=self.config.RATE_LIMIT.MAX_CALLS,
            period=self.config.RATE_LIMIT.TIME_PERIOD
        )

        # Process tracking
        self.active_processes: Dict[str, APIProcessContext] = {}

        # Initialize handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Set up message handlers"""
        handlers = {
            'api.request.start': self._handle_request_start,
            'api.request.complete': self._handle_request_complete,
            'api.request.error': self._handle_request_error,
            'api.control.decision': self._handle_control_decision
        }

        for pattern, handler in handlers.items():
            self.message_broker.subscribe(
                component=ModuleIdentifier(
                    component_name='api_service',
                    component_type=ComponentType.SERVICE,
                    method_name=handler.__name__
                ),
                pattern=pattern,
                callback=handler
            )

    async def process_api_request(
            self,
            request_data: Dict[str, Any],
            user_id: str
    ) -> Dict[str, Any]:
        """
        Process API request with comprehensive handling

        Args:
            request_data: Request configuration
            user_id: User identifier

        Returns:
            Dictionary containing processing results
        """
        async with self.rate_limiter:
            try:
                # Create process context
                context = APIProcessContext(
                    request_id=str(uuid4()),
                    pipeline_id=str(uuid4()),
                    stage=ProcessingStage.INITIAL_VALIDATION,
                    status=ProcessingStatus.PENDING,
                    metadata={
                        'user_id': user_id,
                        'request_type': request_data.get('type', 'unknown'),
                        'created_at': datetime.now().isoformat(),
                        **request_data.get('metadata', {})
                    }
                )

                self.active_processes[context.request_id] = context

                # Process through stages
                try:
                    result = await self._process_request_stages(context, request_data)
                    return {
                        'status': 'success',
                        'request_id': context.request_id,
                        'pipeline_id': context.pipeline_id,
                        'data': result
                    }

                except asyncio.CancelledError:
                    await self._handle_cancellation(context)
                    raise
                except Exception as e:
                    await self._handle_error(context, str(e))
                    raise

            except Exception as e:
                logger.error(f"API request processing error: {str(e)}", exc_info=True)
                return {
                    'status': 'error',
                    'error': str(e)
                }

    async def _process_request_stages(
            self,
            context: APIProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process request through various stages with control points"""
        stages = [
            (ProcessingStage.INITIAL_VALIDATION, self._validate_request),
            (ProcessingStage.CONNECTION_CHECK, self._check_connection),
            (ProcessingStage.DATA_EXTRACTION, self._execute_request),
            (ProcessingStage.DATA_VALIDATION, self._validate_response),
            (ProcessingStage.PROCESSING, self._process_response)
        ]

        stage_results = {}

        for stage, processor in stages:
            context.stage = stage
            await self._update_status(context, f"Starting {stage.value}")

            # Execute stage processor
            result = await processor(context, request_data)

            # Create control point
            decision = await self._create_control_point(
                context=context,
                stage=stage,
                data=result,
                options=['proceed', 'modify', 'reject']
            )

            if decision['decision'] == 'reject':
                await self._handle_rejection(context, decision.get('details', {}))
                raise ValueError(f"Processing rejected at stage {stage.value}")

            elif decision['decision'] == 'modify':
                request_data = await self._apply_modifications(
                    request_data,
                    decision.get('modifications', {})
                )

            stage_results[stage.value] = result

            # Update processing history
            context.processing_history.append({
                'stage': stage.value,
                'timestamp': datetime.now().isoformat(),
                'status': 'completed',
                'details': {
                    k: v for k, v in result.items()
                    if k not in ['data']  # Exclude large data from history
                }
            })

        return stage_results

    async def _validate_request(
            self,
            context: APIProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Initial request validation"""
        return await self.api_manager.validate_request(request_data)

    async def _check_connection(
            self,
            context: APIProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check API connection"""
        return await self.api_manager.check_connection(request_data)

    async def _execute_request(
            self,
            context: APIProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute API request"""
        return await self.api_manager.execute_request(request_data)

    async def _validate_response(
            self,
            context: APIProcessContext,
            response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate API response"""
        return await self.api_manager.validate_response(response_data)

    async def _process_response(
            self,
            context: APIProcessContext,
            response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process API response"""
        return await self.api_manager.process_response(response_data)

    async def _create_control_point(
            self,
            context: APIProcessContext,
            stage: ProcessingStage,
            data: Dict[str, Any],
            options: List[str]
    ) -> Dict[str, Any]:
        """Create control point and wait for decision"""
        try:
            control_point_id = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=stage,
                data={
                    'request_id': context.request_id,
                    'stage_data': data,
                    'metadata': context.metadata
                },
                options=options
            )

            context.control_points.append(control_point_id)
            context.status = ProcessingStatus.AWAITING_DECISION

            await self._update_status(
                context,
                f"Awaiting decision at {stage.value}"
            )

            return await self.control_point_manager.wait_for_decision(
                control_point_id,
                timeout=self.config.REQUEST.REQUEST_TIMEOUT
            )

        except Exception as e:
            logger.error(f"Control point creation error: {str(e)}", exc_info=True)
            raise

    async def _update_status(
            self,
            context: APIProcessContext,
            message: str
    ) -> None:
        """Update processing status"""
        try:
            status_message = ProcessingMessage(
                source_identifier=ModuleIdentifier(
                    component_name='api_service',
                    component_type=ComponentType.SERVICE,
                    method_name='update_status'
                ),
                target_identifier=ModuleIdentifier("pipeline_manager"),
                message_type=MessageType.STATUS_UPDATE,
                content={
                    'pipeline_id': context.pipeline_id,
                    'request_id': context.request_id,
                    'status': context.status.value,
                    'stage': context.stage.value,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                }
            )

            await self.message_broker.publish(status_message)

            # Record metrics
            await self.process_monitor.record_status_update(
                status=context.status.value,
                stage=context.stage.value,
                request_id=context.request_id
            )

        except Exception as e:
            logger.error(f"Status update error: {str(e)}", exc_info=True)

    async def get_request_status(
            self,
            request_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Get current status of API request"""
        try:
            context = self.active_processes.get(request_id)
            if not context:
                return {'status': 'not_found'}

            # Verify user authorization
            if context.metadata['user_id'] != user_id:
                return {'status': 'unauthorized'}

            return {
                'status': context.status.value,
                'stage': context.stage.value,
                'request_id': context.request_id,
                'pipeline_id': context.pipeline_id,
                'created_at': context.created_at.isoformat(),
                'processing_history': context.processing_history,
                'error': context.error
            }

        except Exception as e:
            logger.error(f"Status retrieval error: {str(e)}", exc_info=True)
            return {'status': 'error', 'error': str(e)}

    async def cleanup(self) -> None:
        """Clean up service resources"""
        try:
            # Clean up all active processes
            for request_id in list(self.active_processes.keys()):
                context = self.active_processes[request_id]
                await self._cleanup_process(context)

            # Clean up managers
            await self.api_manager.cleanup()

        except Exception as e:
            logger.error(f"Service cleanup error: {str(e)}", exc_info=True)

    async def _cleanup_process(self, context: APIProcessContext) -> None:
        """Clean up process resources"""
        try:
            # Clean up control points
            for control_point_id in context.control_points:
                try:
                    await self.control_point_manager.cleanup_control_point(
                        control_point_id
                    )
                except Exception as e:
                    logger.error(f"Control point cleanup error: {str(e)}")

            # Remove from active processes
            if context.request_id in self.active_processes:
                del self.active_processes[context.request_id]

        except Exception as e:
            logger.error(f"Process cleanup error: {str(e)}", exc_info=True)