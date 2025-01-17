# s3_service.py

from __future__ import annotations

import logging
import asyncio
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
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.monitoring.process import ProcessMonitor
from backend.core.utils.process_manager import ProcessManager
from backend.core.monitoring.collectors import MetricsCollector

from .s3_manager import S3Manager
from .s3_config import Config

logger = logging.getLogger(__name__)


@dataclass
class S3ProcessContext:
    """Context for S3 operations"""
    request_id: str
    pipeline_id: str
    stage: ProcessingStage
    status: ProcessingStatus
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    control_points: List[str] = field(default_factory=list)

class S3Service:
    """S3 service for data sourcing through CPM"""

    def __init__(
            self,
            message_broker: Optional[MessageBroker] = None,
            control_point_manager: Optional[ControlPointManager] = None,
            config: Optional[Config] = None,
            metrics_collector: Optional[MetricsCollector] = None
    ):
        """Initialize S3Service with required components"""
        # Core components
        self.message_broker = message_broker or MessageBroker()
        self.control_point_manager = control_point_manager or ControlPointManager(
            message_broker=self.message_broker
        )
        self.config = config or Config()
        self.metrics_collector = metrics_collector or MetricsCollector()

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="s3_service",
            source_id=str(uuid4())
        )

        # Operation tracking
        self.active_processes: Dict[str, S3ProcessContext] = {}

        # Register handlers with CPM
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register handlers with Control Point Manager"""
        handlers = {
            's3.request.start': self._handle_request_start,
            's3.request.complete': self._handle_request_complete,
            's3.request.error': self._handle_request_error
        }

        # Register with CPM
        self.control_point_manager.register_handler(
            source_type='s3',
            handlers=handlers
        )

    async def source_data(
            self,
            request_data: Dict[str, Any],
            user_id: str
    ) -> Dict[str, Any]:
        """Source data from S3 through CPM"""
        try:
            # Create process context
            context = S3ProcessContext(
                request_id=str(uuid4()),
                pipeline_id=str(uuid4()),
                stage=ProcessingStage.INITIAL_VALIDATION,
                status=ProcessingStatus.PENDING,
                metadata={
                    'user_id': user_id,
                    'source_type': 's3',
                    **request_data.get('metadata', {})
                }
            )

            self.active_processes[context.request_id] = context

            # Create validation control point
            validation_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.INITIAL_VALIDATION,
                data={
                    'request_data': request_data,
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
                        'request_data': request_data,
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
            logger.error(f"S3 request error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    def _setup_message_handlers(self) -> None:
        """Set up message handlers"""
        handlers = {
            's3.request.start': self._handle_request_start,
            's3.request.complete': self._handle_request_complete,
            's3.request.error': self._handle_request_error,
            's3.control.decision': self._handle_control_decision
        }

        for pattern, handler in handlers.items():
            self.message_broker.subscribe(
                component=ModuleIdentifier(
                    component_name='s3_service',
                    component_type=ComponentType.SERVICE,
                    method_name=handler.__name__
                ),
                pattern=pattern,
                callback=handler
            )

    async def _process_stages(
            self,
            context: S3ProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process request through stages with control points"""
        stages = [
            (ProcessingStage.INITIAL_VALIDATION, self._validate_request),
            (ProcessingStage.CONNECTION_CHECK, self._check_connection),
            (ProcessingStage.DATA_EXTRACTION, self._fetch_data)
        ]

        stage_results = {}

        for stage, processor in stages:
            context.stage = stage
            await self._update_status(context, f"Starting {stage.value}")

            # Process stage
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
            context: S3ProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate S3 request"""
        return await self.s3_manager.validate_request(request_data)

    async def _check_connection(
            self,
            context: S3ProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check S3 connection"""
        return await self.s3_manager.check_connection(request_data)

    async def _fetch_data(
            self,
            context: S3ProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch data from S3"""
        return await self.s3_manager.fetch_data(request_data)

    async def _create_control_point(
            self,
            context: S3ProcessContext,
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
            context: S3ProcessContext,
            message: str
    ) -> None:
        """Update processing status"""
        try:
            status_message = ProcessingMessage(
                source_identifier=ModuleIdentifier(
                    component_name='s3_service',
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

    async def get_status(
            self,
            request_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Get current status of S3 request"""
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

    async def _handle_cancellation(self, context: S3ProcessContext) -> None:
        """Handle operation cancellation"""
        try:
            context.status = ProcessingStatus.CANCELLED
            await self._update_status(context, "Operation cancelled")
            await self._cleanup_process(context.request_id)
        except Exception as e:
            logger.error(f"Cancellation handling error: {str(e)}", exc_info=True)

    async def _handle_error(
            self,
            context: S3ProcessContext,
            error: str
    ) -> None:
        """Handle operation error"""
        try:
            context.status = ProcessingStatus.FAILED
            context.error = error
            await self._update_status(context, f"Error: {error}")

            # Record error metrics
            await self.process_monitor.record_metric(
                'operation_error',
                1,
                error=error,
                request_id=context.request_id,
                stage=context.stage.value if context.stage else None
            )

        except Exception as e:
            logger.error(f"Error handling error: {str(e)}", exc_info=True)

    async def _handle_request_start(self, message: ProcessingMessage) -> None:
        """
        Handle the start of an S3 request
        
        Args:
            message: Processing message containing request details
        """
        try:
            logger.info(f"Handling S3 request start: {message.content}")
            
            request_id = message.content.get('request_id')
            if not request_id:
                logger.error("No request_id provided in request start message")
                return

            # Update process context if exists
            context = self.active_processes.get(request_id)
            if context:
                context.status = ProcessingStatus.RUNNING
                await self._update_status(
                    context, 
                    "Request processing started"
                )
            else:
                logger.warning(f"No active process found for request_id: {request_id}")

        except Exception as e:
            logger.error(f"Error in _handle_request_start: {str(e)}", exc_info=True)

    async def _handle_request_complete(self, message: ProcessingMessage) -> None:
        """
        Handle the completion of an S3 request
        
        Args:
            message: Processing message containing request completion details
        """
        try:
            logger.info(f"Handling S3 request complete: {message.content}")
            
            request_id = message.content.get('request_id')
            if not request_id:
                logger.error("No request_id provided in request complete message")
                return

            context = self.active_processes.get(request_id)
            if context:
                context.status = ProcessingStatus.COMPLETED
                await self._update_status(
                    context, 
                    "Request processing completed successfully"
                )
                await self._cleanup_process(request_id)
            else:
                logger.warning(f"No active process found for request_id: {request_id}")

        except Exception as e:
            logger.error(f"Error in _handle_request_complete: {str(e)}", exc_info=True)

    async def _handle_request_error(self, message: ProcessingMessage) -> None:
        """
        Handle errors in S3 request processing
        
        Args:
            message: Processing message containing error details
        """
        try:
            logger.error(f"Handling S3 request error: {message.content}")
            
            request_id = message.content.get('request_id')
            error = message.content.get('error', 'Unknown error')
            
            if not request_id:
                logger.error("No request_id provided in request error message")
                return

            context = self.active_processes.get(request_id)
            if context:
                await self._handle_error(context, error)
            else:
                logger.warning(f"No active process found for request_id: {request_id}")

        except Exception as e:
            logger.error(f"Error in _handle_request_error: {str(e)}", exc_info=True)

    async def _handle_control_decision(self, message: ProcessingMessage) -> None:
        """
        Handle control point decision messages
        
        Args:
            message: Processing message containing control decision details
        """
        try:
            logger.info(f"Handling control decision: {message.content}")
            
            control_point_id = message.content.get('control_point_id')
            decision = message.content.get('decision')
            
            if not control_point_id or not decision:
                logger.error("Incomplete control decision message")
                return

            # Delegate to control point manager to process the decision
            await self.control_point_manager.process_decision(
                control_point_id, 
                decision,
                message.content.get('modifications', {})
            )

        except Exception as e:
            logger.error(f"Error in _handle_control_decision: {str(e)}", exc_info=True)

    async def _apply_modifications(
            self, 
            request_data: Dict[str, Any], 
            modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply modifications to the request data
        
        Args:
            request_data: Original request data
            modifications: Modifications to apply
        
        Returns:
            Updated request data
        """
        try:
            # Deep copy to avoid modifying the original
            updated_data = request_data.copy()
            
            # Apply modifications
            for key, value in modifications.items():
                # Support nested key modifications
                keys = key.split('.')
                current = updated_data
                for k in keys[:-1]:
                    current = current.setdefault(k, {})
                current[keys[-1]] = value
            
            return updated_data

        except Exception as e:
            logger.error(f"Error applying modifications: {str(e)}", exc_info=True)
            return request_data
    
    async def _handle_rejection(
            self,
            context: S3ProcessContext,
            details: Dict[str, Any]
    ) -> None:
        """Handle stage rejection"""
        try:
            context.status = ProcessingStatus.REJECTED
            await self._update_status(
                context,
                f"Stage {context.stage.value} rejected: {details.get('reason', 'No reason provided')}"
            )
        except Exception as e:
            logger.error(f"Rejection handling error: {str(e)}", exc_info=True)

    def list_sources(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List S3 sources for a specific user
        
        Args:
            user_id: User's unique identifier
        
        Returns:
            List of S3 sources
        """
        try:
            sources = [
                {
                    'id': process.request_id,
                    'pipeline_id': process.pipeline_id,
                    'created_at': process.created_at.isoformat(),
                    'status': process.status.value,
                    'stage': process.stage.value,
                    'error': process.error,
                    'connection_details': process.metadata.get('connection_details')
                }
                for process in self.active_processes.values()
                if process.metadata.get('user_id') == user_id
            ]
            
            return sources
        except Exception as e:
            logger.error(f"Error listing S3 sources: {str(e)}", exc_info=True)
            return []
        
    async def _cleanup_process(self, request_id: str) -> None:
        """Clean up process resources"""
        try:
            context = self.active_processes.get(request_id)
            if not context:
                return

            # Clean up control points
            for control_point_id in context.control_points:
                try:
                    await self.control_point_manager.cleanup_control_point(
                        control_point_id
                    )
                except Exception as e:
                    logger.error(f"Control point cleanup error: {str(e)}")

            # Remove from active processes
            del self.active_processes[request_id]

        except Exception as e:
            logger.error(f"Process cleanup error: {str(e)}", exc_info=True)

    async def cleanup(self) -> None:
        """Clean up service resources"""
        try:
            # Clean up all active processes
            for request_id in list(self.active_processes.keys()):
                await self._cleanup_process(request_id)

            # Clean up manager
            await self.s3_manager.cleanup()

        except Exception as e:
            logger.error(f"Service cleanup error: {str(e)}", exc_info=True)