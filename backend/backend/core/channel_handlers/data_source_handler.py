# backend/core/channel_handlers/source_handler.py

from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import logging
from enum import Enum
import pandas as pd

from backend.core.channel_handlers.base_channel_handler import BaseChannelHandler
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType, ProcessingMessage, ProcessingStatus,
    ProcessingStage, ModuleIdentifier, ComponentType
)

# Source Managers
from backend.data_pipeline.source.file.file_manager import FileManager
from backend.data_pipeline.source.api.api_manager import APIManager
from backend.data_pipeline.source.database.db_manager import DBManager
from backend.data_pipeline.source.cloud.s3_manager import S3Manager
from backend.data_pipeline.source.stream.stream_manager import StreamManager

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Types of data sources supported by the system."""
    FILE = "file"
    API = "api"
    DATABASE = "database"
    STREAM = "stream"
    S3 = "s3"


class SourceOperation(Enum):
    """Operations that can be performed on data sources."""
    CONNECT = "connect"
    READ = "read"
    VALIDATE = "validate"
    EXTRACT = "extract"
    DISCONNECT = "disconnect"


@dataclass
class SourceContext:
    """Enhanced context for tracking source operations with control points"""
    pipeline_id: str
    source_type: SourceType
    operation: SourceOperation
    metadata: Dict[str, Any]
    stage: ProcessingStage
    control_points: List[str] = field(default_factory=list)
    decisions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: ProcessingStatus = field(default=ProcessingStatus.PENDING)
    error: Optional[str] = field(default=None)
    validation_results: Optional[Dict[str, Any]] = field(default=None)
    processing_history: List[Dict[str, Any]] = field(default_factory=list)


class DataSourceChannelHandler(BaseChannelHandler):
    """Enhanced handler for data source operations with control points"""

    def __init__(self, message_broker: MessageBroker, control_point_manager: Any):
        super().__init__(message_broker, "source_handler")
        self.control_point_manager = control_point_manager
        self.source_managers = self._initialize_source_managers(message_broker)
        self.active_sources: Dict[str, SourceContext] = {}
        self._register_handlers()

    def _initialize_source_managers(self, message_broker: MessageBroker) -> Dict[SourceType, Any]:
        """Initialize all source managers"""
        managers = {
            SourceType.FILE: FileManager(message_broker),
            SourceType.API: APIManager(message_broker),
            SourceType.DATABASE: DBManager(message_broker),
            SourceType.STREAM: StreamManager(message_broker),
            SourceType.S3: S3Manager(message_broker)
        }

        for source_type, manager in managers.items():
            logger.info(f"Initialized {source_type.value} source manager")
        return managers

    def _register_handlers(self) -> None:
        """Register all message handlers including control point handlers"""
        # Source operation handlers
        operation_handlers = {
            MessageType.SOURCE_CONNECT: self._handle_source_connect,
            MessageType.SOURCE_READ: self._handle_source_read,
            MessageType.SOURCE_VALIDATE: self._handle_source_validate,
            MessageType.SOURCE_EXTRACT: self._handle_source_extract,
            MessageType.SOURCE_DISCONNECT: self._handle_source_disconnect
        }

        # Control point handlers
        control_handlers = {
            MessageType.CONTROL_POINT_REACHED: self._handle_control_point,
            MessageType.CONTROL_POINT_DECISION: self._handle_control_decision,
            MessageType.USER_DECISION_SUBMITTED: self._handle_user_decision,
            MessageType.USER_DECISION_TIMEOUT: self._handle_decision_timeout
        }

        # Register all handlers
        for message_type, handler in {**operation_handlers, **control_handlers}.items():
            self.register_callback(message_type, handler)
            logger.debug(f"Registered handler for {message_type.value}")

    async def handle_source_request(self, pipeline_id: str, source_type: str,
                                    request_data: Dict[str, Any]) -> None:
        """Enhanced entry point for handling source requests with control points"""
        try:
            source_type_enum = SourceType(source_type)
            source_manager = self.source_managers.get(source_type_enum)

            if not source_manager:
                raise ValueError(f"No manager found for source type: {source_type}")

            # Create enhanced context
            context = SourceContext(
                pipeline_id=pipeline_id,
                source_type=source_type_enum,
                operation=SourceOperation.CONNECT,
                metadata=request_data.get('metadata', {}),
                stage=ProcessingStage.INITIAL_VALIDATION,
                status=ProcessingStatus.PENDING
            )

            self.active_sources[pipeline_id] = context

            # Create initial control point
            control_point_id = await self.control_point_manager.create_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.INITIAL_VALIDATION,
                data={
                    'source_type': source_type,
                    'metadata': request_data.get('metadata', {}),
                    'config': request_data.get('config', {})
                },
                options=['proceed', 'validate', 'reject']
            )

            context.control_points.append(control_point_id)
            logger.info(f"Created source context and control point for pipeline {pipeline_id}")

        except Exception as e:
            logger.error(f"Failed to handle source request: {str(e)}", exc_info=True)
            self._handle_source_error(pipeline_id, str(e))

    async def route_to_source_manager(self, pipeline_id: str, operation: SourceOperation,
                                      data: Dict[str, Any]) -> None:
        """Route operation to appropriate source manager"""
        try:
            context = self.active_sources.get(pipeline_id)
            if not context:
                raise ValueError(f"No active source context for pipeline: {pipeline_id}")

            source_manager = self.source_managers.get(context.source_type)
            if not source_manager:
                raise ValueError(f"No manager found for source type: {context.source_type}")

            # Update context
            context.operation = operation
            context.status = ProcessingStatus.ACTIVE

            # Route operation
            operation_map = {
                SourceOperation.CONNECT: source_manager.connect,
                SourceOperation.READ: source_manager.read_data,
                SourceOperation.VALIDATE: source_manager.validate_source,
                SourceOperation.EXTRACT: source_manager.extract_data,
                SourceOperation.DISCONNECT: source_manager.disconnect
            }

            operation_func = operation_map.get(operation)
            if not operation_func:
                raise ValueError(f"Unsupported operation: {operation}")

            # Add to processing history
            context.processing_history.append({
                'timestamp': datetime.now().isoformat(),
                'operation': operation.value,
                'data': data
            })

            await operation_func(pipeline_id, data)
            logger.info(f"Routed {operation.value} operation for pipeline {pipeline_id}")

        except Exception as e:
            logger.error(f"Operation routing error: {str(e)}", exc_info=True)
            self._handle_source_error(pipeline_id, str(e))

    async def _handle_control_point(self, message: ProcessingMessage) -> None:
        """Handle control point reached notification"""
        pipeline_id = message.content['pipeline_id']
        control_point_id = message.content['control_point_id']

        context = self.active_sources.get(pipeline_id)
        if not context:
            logger.error(f"No context found for pipeline {pipeline_id}")
            return

        try:
            # Update context
            context.control_points.append(control_point_id)
            context.status = ProcessingStatus.AWAITING_DECISION

            # Track in processing history
            context.processing_history.append({
                'timestamp': datetime.now().isoformat(),
                'stage': message.content['stage'],
                'control_point_id': control_point_id,
                'type': 'control_point_reached'
            })

            # Forward to UI
            self.send_response(
                target_id="ui_handler",
                message_type=MessageType.CONTROL_POINT_REACHED,
                content=message.content
            )

        except Exception as e:
            logger.error(f"Error handling control point: {str(e)}")
            self._handle_source_error(pipeline_id, str(e))

    async def _handle_control_decision(self, message: ProcessingMessage) -> None:
        """Handle user decision for a control point"""
        pipeline_id = message.content['pipeline_id']
        control_point_id = message.content['control_point_id']
        decision = message.content['decision']

        context = self.active_sources.get(pipeline_id)
        if not context:
            logger.error(f"No context found for pipeline {pipeline_id}")
            return

        try:
            # Record decision
            context.decisions[control_point_id] = {
                'decision': decision,
                'timestamp': datetime.now().isoformat(),
                'details': message.content.get('details', {})
            }

            # Handle decision based on current stage
            if context.stage == ProcessingStage.INITIAL_VALIDATION:
                await self._handle_validation_decision(context, decision, message.content)
            elif context.stage == ProcessingStage.DATA_EXTRACTION:
                await self._handle_extraction_decision(context, decision, message.content)

            # Update processing history
            context.processing_history.append({
                'timestamp': datetime.now().isoformat(),
                'stage': context.stage.value,
                'decision': decision,
                'type': 'decision_made'
            })

        except Exception as e:
            logger.error(f"Error handling control decision: {str(e)}")
            self._handle_source_error(pipeline_id, str(e))

    async def _handle_validation_decision(self, context: SourceContext,
                                          decision: str, content: Dict[str, Any]) -> None:
        """Handle decision for validation stage"""
        if decision == 'proceed':
            # Move to extraction stage
            context.stage = ProcessingStage.DATA_EXTRACTION
            context.status = ProcessingStatus.ACTIVE

            await self.route_to_source_manager(
                context.pipeline_id,
                SourceOperation.EXTRACT,
                content.get('extraction_params', {})
            )

        elif decision == 'validate':
            # Perform additional validation
            context.status = ProcessingStatus.ACTIVE
            await self.route_to_source_manager(
                context.pipeline_id,
                SourceOperation.VALIDATE,
                content.get('validation_params', {})
            )

        elif decision == 'reject':
            context.status = ProcessingStatus.FAILED
            await self._handle_rejection(context, content.get('reason'))

    async def _handle_extraction_decision(self, context: SourceContext,
                                          decision: str, content: Dict[str, Any]) -> None:
        """Handle decision for data extraction stage"""
        if decision == 'proceed':
            context.status = ProcessingStatus.COMPLETED
            await self._finalize_extraction(context)

        elif decision == 'modify':
            # Apply modifications and re-extract
            context.status = ProcessingStatus.ACTIVE
            await self.route_to_source_manager(
                context.pipeline_id,
                SourceOperation.EXTRACT,
                {
                    'modifications': content.get('modifications', {}),
                    **content.get('extraction_params', {})
                }
            )

        elif decision == 'reject':
            context.status = ProcessingStatus.FAILED
            await self._handle_rejection(context, content.get('reason'))

    async def _finalize_extraction(self, context: SourceContext) -> None:
        """Finalize successful data extraction"""
        try:
            # Notify pipeline manager of completion
            self.send_response(
                target_id=f"pipeline_manager_{context.pipeline_id}",
                message_type=MessageType.SOURCE_SUCCESS,
                content={
                    'pipeline_id': context.pipeline_id,
                    'stage': context.stage.value,
                    'source_type': context.source_type.value,
                    'processing_history': context.processing_history,
                    'metadata': context.metadata
                }
            )

            # Cleanup
            await self._cleanup_source(context.pipeline_id)

        except Exception as e:
            logger.error(f"Error finalizing extraction: {str(e)}")
            self._handle_source_error(context.pipeline_id, str(e))

    async def _handle_rejection(self, context: SourceContext, reason: Optional[str]) -> None:
        """Handle source operation rejection"""
        try:
            # Notify pipeline manager
            self.send_response(
                target_id=f"pipeline_manager_{context.pipeline_id}",
                message_type=MessageType.SOURCE_ERROR,
                content={
                    'pipeline_id': context.pipeline_id,
                    'stage': context.stage.value,
                    'error': f"Operation rejected: {reason or 'No reason provided'}",
                    'metadata': context.metadata
                }
            )

            # Cleanup
            await self._cleanup_source(context.pipeline_id)

        except Exception as e:
            logger.error(f"Error handling rejection: {str(e)}")
            self._handle_source_error(context.pipeline_id, str(e))

    def get_source_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of source operation"""
        context = self.active_sources.get(pipeline_id)
        if not context:
            return None

        return {
            'pipeline_id': pipeline_id,
            'source_type': context.source_type.value,
            'stage': context.stage.value,
            'status': context.status.value,
            'current_operation': context.operation.value,
            'control_points': context.control_points,
            'decisions': context.decisions,
            'error': context.error,
            'created_at': context.created_at.isoformat(),
            'processing_history': context.processing_history
        }

    async def _cleanup_source(self, pipeline_id: str) -> None:
        """Enhanced cleanup with control point handling"""
        context = self.active_sources.get(pipeline_id)
        if context:
            try:
                # Cleanup source manager resources
                source_manager = self.source_managers.get(context.source_type)
                if source_manager:
                    await source_manager.cleanup(pipeline_id)

                # Cleanup control points
                for control_point_id in context.control_points:
                    await self.control_point_manager.cleanup_control_point(control_point_id)

                # Remove context
                del self.active_sources[pipeline_id]
                logger.info(f"Cleaned up resources for pipeline {pipeline_id}")

            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}", exc_info=True)

    async def _handle_decision_timeout(self, message: ProcessingMessage) -> None:
        """Handle user decision timeout"""
        pipeline_id = message.content['pipeline_id']
        control_point_id = message.content['control_point_id']

        context = self.active_sources.get(pipeline_id)
        if context:
            try:
                # Record timeout in history
                context.processing_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'type': 'decision_timeout',
                    'control_point_id': control_point_id,
                    'stage': context.stage.value
                })

                # Update status
                context.status = ProcessingStatus.FAILED
                context.error = f"Decision timeout for control point {control_point_id}"

                # Notify pipeline manager
                self.send_response(
                    target_id=f"pipeline_manager_{pipeline_id}",
                    message_type=MessageType.SOURCE_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': 'Decision timeout',
                        'control_point_id': control_point_id,
                        'stage': context.stage.value
                    }
                )

                # Cleanup
                await self._cleanup_source(pipeline_id)

            except Exception as e:
                logger.error(f"Error handling decision timeout: {str(e)}")
                self._handle_source_error(pipeline_id, str(e))

    async def _handle_user_decision(self, message: ProcessingMessage) -> None:
        """Handle user decision submission"""
        pipeline_id = message.content['pipeline_id']
        decision = message.content['decision']
        details = message.content.get('details', {})

        context = self.active_sources.get(pipeline_id)
        if not context:
            logger.error(f"No context found for pipeline {pipeline_id}")
            return

        try:
            # Record decision in history
            context.processing_history.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'user_decision',
                'decision': decision,
                'details': details,
                'stage': context.stage.value
            })

            # Forward to control point handler
            await self._handle_control_decision(message)

        except Exception as e:
            logger.error(f"Error handling user decision: {str(e)}")
            self._handle_source_error(pipeline_id, str(e))

    def _handle_source_error(self, pipeline_id: str, error_message: str) -> None:
        """Enhanced error handling"""
        context = self.active_sources.get(pipeline_id)
        if context:
            try:
                # Update context
                context.status = ProcessingStatus.FAILED
                context.error = error_message

                # Record error in history
                context.processing_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'type': 'error',
                    'error': error_message,
                    'stage': context.stage.value
                })

                # Notify pipeline manager
                self.send_response(
                    target_id=f"pipeline_manager_{pipeline_id}",
                    message_type=MessageType.SOURCE_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'operation': context.operation.value,
                        'stage': context.stage.value,
                        'error': error_message,
                        'metadata': context.metadata,
                        'processing_history': context.processing_history
                    }
                )

                # Cleanup
                self._cleanup_source(pipeline_id)

            except Exception as e:
                logger.error(f"Error in error handler: {str(e)}", exc_info=True)

    def __del__(self):
        """Cleanup handler resources"""
        try:
            for pipeline_id in list(self.active_sources.keys()):
                self._cleanup_source(pipeline_id)
        except Exception as e:
            logger.error(f"Error during deletion cleanup: {str(e)}")
        finally:
            super().__del__()