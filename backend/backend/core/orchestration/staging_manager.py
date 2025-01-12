# backend/core/staging/staging_manager.py

import logging
import asyncio
import pandas as pd  # Added for preview functionality
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType, ProcessingMessage, ProcessingStatus,
    ProcessingStage, ControlPoint, ModuleIdentifier
)

logger = logging.getLogger(__name__)


@dataclass
class StagedData:
    """Enhanced staged data tracking"""
    pipeline_id: str
    stage_id: str
    data: Any
    metadata: Dict[str, Any]
    status: ProcessingStatus
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    control_points: List[str] = field(default_factory=list)


class StagingManager:
    """Enhanced staging manager with control point integration"""

    def __init__(
            self,
            message_broker: MessageBroker,
            control_point_manager: Optional[Any] = None,
            component_name: str = "staging_manager"
    ):
        # Core components
        self.message_broker = message_broker
        self.control_point_manager = control_point_manager

        # Create module identifier
        self.module_id = ModuleIdentifier(
            component_name=component_name,
            component_type="manager",
            method_name="staging_handler",
            instance_id=str(datetime.now().timestamp())
        )

        # Staged data management
        self.staged_data: Dict[str, StagedData] = {}

        # Async setup tracking
        self._setup_complete = False
        self._setup_handlers_task = None

    def start_message_handlers(self) -> None:
        """
        Synchronous method to initiate async message handler setup

        This method can be safely called in synchronous contexts
        """
        # If already set up, do nothing
        if self._setup_complete:
            return

        # Create a new event loop if no running loop exists
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_setup_message_handlers())
        except Exception as e:
            logger.error(f"Error starting message handlers: {str(e)}")

    async def _async_setup_message_handlers(self) -> None:
        """
        Async method to set up message handlers
        """
        try:
            # Register the component
            await self.message_broker.register_component(
                component=self.module_id,
                default_callback=self._handle_generic_message
            )

            # Subscribe to relevant message patterns
            message_patterns = [
                "*.stage.*",  # Wildcard for staging related messages
                f"{self.module_id.get_tag()}.#"  # Exact component messages
            ]

            for pattern in message_patterns:
                await self.message_broker.subscribe(
                    component=self.module_id,
                    pattern=pattern,
                    callback=self._route_message
                )

            logger.info("Staging Manager message handlers setup complete")
            self._setup_complete = True

        except Exception as e:
            logger.error(f"Error setting up message handlers: {str(e)}")
            self._setup_complete = False

    async def _handle_decision_timeout(self, message: ProcessingMessage) -> None:
        """
        Handle decision timeout for a staged data point

        Args:
            message (ProcessingMessage): Timeout message
        """
        try:
            # Extract stage ID from message
            stage_id = message.content.get('stage_id')

            if not stage_id:
                logger.warning("Received decision timeout without stage ID")
                return

            # Find the staged data
            staged = self.staged_data.get(stage_id)

            if not staged:
                logger.warning(f"No staged data found for stage ID: {stage_id}")
                return

            # Update status to failed
            staged.status = ProcessingStatus.FAILED

            # Notify about the timeout
            error_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier("pipeline_manager"),
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': staged.pipeline_id,
                    'stage_id': stage_id,
                    'error': 'Staging decision timed out',
                    'timestamp': datetime.now().isoformat()
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Error handling staging decision timeout: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the Staging Manager

        Returns:
            Dict[str, Any]: Status information
        """
        return {
            'active_staged_data': len(self.staged_data),
            'message_handlers_setup': self._setup_complete
        }

    async def cleanup(self) -> None:
        """
        Comprehensive cleanup of staged data resources
        """
        try:
            # Clear all staged data
            self.staged_data.clear()

            logger.info("Staging Manager cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during Staging Manager cleanup: {str(e)}")

    async def _route_message(self, message: ProcessingMessage) -> None:
        """
        Route messages to appropriate handlers based on message type

        Args:
            message (ProcessingMessage): Incoming message to route
        """
        try:
            handler_map = {
                MessageType.STAGE_STORE: self._handle_stage_store,
                MessageType.STAGE_RETRIEVE: self._handle_stage_retrieve,
                MessageType.STAGE_UPDATE: self._handle_stage_update,
                MessageType.CONTROL_POINT_DECISION: self._handle_control_point_decision,
                MessageType.USER_DECISION_TIMEOUT: self._handle_decision_timeout
            }

            handler = handler_map.get(message.message_type)
            if handler:
                await handler(message)
            else:
                await self._handle_generic_message(message)

        except Exception as e:
            logger.error(f"Error routing message: {str(e)}")

    async def _handle_generic_message(self, message: ProcessingMessage) -> None:
        """
        Default handler for unrecognized messages

        Args:
            message (ProcessingMessage): Unhandled message
        """
        logger.warning(f"Received unhandled message type: {message.message_type}")

    async def stage_data(
            self,
            pipeline_id: str,
            key: str,
            data: Any,
            metadata: Optional[Dict[str, Any]] = None,
            requires_approval: bool = True
    ) -> Dict[str, Any]:
        """
        Stage data with optional control point integration

        Args:
            pipeline_id (str): Unique pipeline identifier
            key (str): Unique key for the staged data
            data (Any): Data to be staged
            metadata (Optional[Dict[str, Any]], optional): Additional metadata
            requires_approval (bool, optional): Whether data needs approval

        Returns:
            Dict[str, Any]: Staging result
        """
        try:
            stage_id = f"{pipeline_id}_{key}_{datetime.now().timestamp()}"

            # Create staged data entry
            staged = StagedData(
                pipeline_id=pipeline_id,
                stage_id=stage_id,
                data=data,
                metadata=metadata or {},
                status=ProcessingStatus.PENDING,
                expires_at=datetime.now() + timedelta(days=7)
            )

            # Store staged data
            self.staged_data[stage_id] = staged

            if requires_approval and self.control_point_manager:
                # Create control point for data staging
                control_point_id = await self.control_point_manager.create_control_point(
                    pipeline_id=pipeline_id,
                    stage=ProcessingStage.DATA_EXTRACTION,
                    data={
                        'stage_id': stage_id,
                        'metadata': metadata or {},
                        'preview': self._generate_preview(data)
                    },
                    options=['approve', 'reject', 'modify']
                )

                staged.control_points.append(control_point_id)
                staged.status = ProcessingStatus.AWAITING_DECISION
            else:
                staged.status = ProcessingStatus.COMPLETED

            # Notify about staged data
            await self._update_status(pipeline_id, stage_id, staged.status)

            return {
                'stage_id': stage_id,
                'status': staged.status.value,
                'requires_approval': requires_approval
            }

        except Exception as e:
            logger.error(f"Error staging data: {str(e)}")
            await self._handle_staging_error(pipeline_id, str(e))
            raise

    async def _handle_stage_store(self, message: ProcessingMessage) -> None:
        """Handle stage store request"""
        try:
            pipeline_id = message.content['pipeline_id']
            key = message.content.get('key', 'default')
            data = message.content['data']
            metadata = message.content.get('metadata', {})
            requires_approval = message.content.get('requires_approval', True)

            result = await self.stage_data(
                pipeline_id=pipeline_id,
                key=key,
                data=data,
                metadata=metadata,
                requires_approval=requires_approval
            )

            # Send response
            response_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=message.source_identifier,
                message_type=MessageType.STAGE_SUCCESS,
                content=result
            )
            await self.message_broker.publish(response_message)

        except Exception as e:
            await self._handle_staging_error(pipeline_id, str(e))

    def _generate_preview(self, data: Any) -> Dict[str, Any]:
        """Generate data preview with support for various data types"""
        try:
            if isinstance(data, (pd.DataFrame, pd.Series)):
                return {
                    'head': data.head(5).to_dict(),
                    'info': {
                        'shape': data.shape,
                        'columns': list(data.columns) if hasattr(data, 'columns') else None,
                        'dtypes': data.dtypes.to_dict() if hasattr(data, 'dtypes') else None
                    }
                }
            elif isinstance(data, dict):
                return {
                    'sample': dict(list(data.items())[:5]),
                    'total_keys': len(data)
                }
            elif isinstance(data, list):
                return {
                    'sample': data[:5],
                    'total_items': len(data)
                }
            else:
                return {
                    'type': str(type(data)),
                    'preview': str(data)[:100]
                }
        except Exception as e:
            logger.error(f"Error generating preview: {str(e)}")
            return {'error': 'Could not generate preview'}

    async def _update_status(
            self,
            pipeline_id: str,
            stage_id: str,
            status: ProcessingStatus
    ) -> None:
        """Update staging status via message broker"""
        message = ProcessingMessage(
            source_identifier=self.module_id,
            target_identifier=ModuleIdentifier("pipeline_manager"),
            message_type=MessageType.STATUS_UPDATE,
            content={
                'pipeline_id': pipeline_id,
                'stage_id': stage_id,
                'status': status.value,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    async def _handle_staging_error(
            self,
            pipeline_id: str,
            error_message: str
    ) -> None:
        """Handle and notify about staging errors"""
        error_message = ProcessingMessage(
            source_identifier=self.module_id,
            target_identifier=ModuleIdentifier("pipeline_manager"),
            message_type=MessageType.STAGE_ERROR,
            content={
                'pipeline_id': pipeline_id,
                'error': error_message,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(error_message)

    def cleanup_expired(self) -> None:
        """Clean up expired staged data"""
        current_time = datetime.now()
        expired_stages = [
            stage_id for stage_id, staged in self.staged_data.items()
            if staged.expires_at and staged.expires_at <= current_time
        ]

        for stage_id in expired_stages:
            self._cleanup_staged_data(stage_id)

    def _cleanup_staged_data(self, stage_id: str) -> None:
        """Clean up staged data"""
        if stage_id in self.staged_data:
            del self.staged_data[stage_id]

    async def _handle_control_point_decision(self, message: ProcessingMessage) -> None:
        """Handle control point decision"""
        pipeline_id = message.content['pipeline_id']
        stage_id = message.content['stage_id']
        decision = message.content['decision']

        staged = self.staged_data.get(stage_id)
        if not staged:
            logger.error(f"No staged data found for {stage_id}")
            return

        try:
            if decision == 'approve':
                staged.status = ProcessingStatus.COMPLETED

                # Notify pipeline manager
                self.send_response(
                    target_id=f"pipeline_manager_{pipeline_id}",
                    message_type=MessageType.STAGE_SUCCESS,
                    content={
                        'stage_id': stage_id,
                        'pipeline_id': pipeline_id,
                        'status': 'approved'
                    }
                )

            elif decision == 'reject':
                staged.status = ProcessingStatus.FAILED
                await self._handle_rejection(staged, message.content.get('reason'))

            elif decision == 'modify':
                modifications = message.content.get('modifications', {})
                await self._apply_modifications(staged, modifications)

            # Update status
            self._update_status(pipeline_id, stage_id, staged.status)

        except Exception as e:
            self._handle_staging_error(pipeline_id, str(e))

    async def _apply_modifications(self, staged: StagedData, modifications: Dict[str, Any]) -> None:
        """Apply modifications to staged data"""
        try:
            # Record modification in history
            staged.processing_history.append({
                'action': 'modify',
                'timestamp': datetime.now().isoformat(),
                'modifications': modifications
            })

            # Apply modifications
            modified_data = await self._modify_data(staged.data, modifications)

            # Update staged data
            staged.data = modified_data
            staged.status = ProcessingStatus.COMPLETED

            # Create new control point for verification
            control_point_id = await self.control_point_manager.create_control_point(
                pipeline_id=staged.pipeline_id,
                stage=ProcessingStage.DATA_EXTRACTION,
                data={
                    'stage_id': staged.stage_id,
                    'preview': self._generate_preview(modified_data),
                    'modifications_applied': modifications
                },
                options=['approve', 'reject', 'modify']
            )

            staged.control_points.append(control_point_id)

        except Exception as e:
            logger.error(f"Error applying modifications: {str(e)}")
            staged.status = ProcessingStatus.FAILED
            raise

