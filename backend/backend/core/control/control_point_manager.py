# backend/core/control/control_point_manager.py

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ProcessingStage,
    ControlPoint,
    ProcessingMessage,
    ModuleIdentifier
)

logger = logging.getLogger(__name__)


class ControlPointManager:
    """Manages control points and user decisions in the pipeline"""

    def __init__(
            self,
            message_broker: MessageBroker,
            component_name: str = "control_point_manager"
    ):
        """
        Initialize the Control Point Manager

        Args:
            message_broker (EnhancedMessageBroker): Message broker for communication
            component_name (str, optional): Name of the component
        """
        self.message_broker = message_broker
        self.active_control_points: Dict[str, ControlPoint] = {}
        self.pending_decisions: Dict[str, asyncio.Future] = {}

        # Create a unique module identifier
        self.module_id = ModuleIdentifier(
            component_name=component_name,
            component_type="manager",
            method_name="control_point_handler",
            instance_id=str(datetime.now().timestamp())
        )

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
                default_callback=self._handle_control_messages
            )

            # Subscribe to relevant message patterns
            message_patterns = [
                "*.control_point.*",  # Wildcard for control point related messages
                f"{self.module_id.get_tag()}.#"  # Exact component messages
            ]

            for pattern in message_patterns:
                await self.message_broker.subscribe(
                    component=self.module_id,
                    pattern=pattern,
                    callback=self._handle_control_messages
                )

            logger.info("Control Point Manager message handlers setup complete")
            self._setup_complete = True

        except Exception as e:
            logger.error(f"Error setting up message handlers: {str(e)}")
            self._setup_complete = False

    async def _handle_control_messages(self, message: ProcessingMessage) -> None:
        """
        Handle incoming control messages with comprehensive routing

        Args:
            message (ProcessingMessage): Incoming message to process
        """
        try:
            logger.info(f"Received control message: {message}")

            # Route based on message type
            if message.message_type == MessageType.CONTROL_POINT_REACHED:
                await self._handle_control_point_reached(message)
            elif message.message_type == MessageType.USER_DECISION_SUBMITTED:
                await self._handle_user_decision(message)
            elif message.message_type == MessageType.USER_DECISION_TIMEOUT:
                await self._handle_decision_timeout_message(message)

        except Exception as e:
            logger.error(f"Error processing control message: {str(e)}")

    async def _handle_decision_timeout_message(self, message: ProcessingMessage) -> None:
        """
        Handle decision timeout message

        Args:
            message (ProcessingMessage): Timeout message
        """
        try:
            # Extract control point ID from message
            control_point_id = message.content.get('control_point_id')

            if not control_point_id:
                logger.warning("Received decision timeout without control point ID")
                return

            # Find the control point
            control_point = self.active_control_points.get(control_point_id)

            if not control_point:
                logger.warning(f"No control point found for ID: {control_point_id}")
                return

            # Handle timeout
            await self._handle_decision_timeout(control_point_id)

        except Exception as e:
            logger.error(f"Error handling decision timeout: {str(e)}")

    async def _handle_decision_timeout(self, control_point_id: str) -> None:
        """
        Handle decision timeout for a specific control point

        Args:
            control_point_id (str): ID of the control point
        """
        try:
            # Retrieve the control point
            control_point = self.active_control_points.get(control_point_id)

            if not control_point:
                logger.warning(f"Cannot handle timeout for unknown control point: {control_point_id}")
                return

            # Create timeout notification message
            timeout_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier("pipeline_manager"),
                message_type=MessageType.USER_DECISION_TIMEOUT,
                content={
                    'control_point_id': control_point_id,
                    'pipeline_id': control_point.pipeline_id,
                    'stage': control_point.stage.value,
                    'timeout_reason': 'Decision not made within allocated time'
                }
            )

            # Publish timeout message
            await self.message_broker.publish(timeout_message)

            # Complete the future with a timeout exception if it's not already done
            pending_decision = self.pending_decisions.get(control_point_id)
            if pending_decision and not pending_decision.done():
                pending_decision.set_exception(asyncio.TimeoutError("Control point decision timed out"))

            # Remove the control point from active control points
            if control_point_id in self.active_control_points:
                del self.active_control_points[control_point_id]
            if control_point_id in self.pending_decisions:
                del self.pending_decisions[control_point_id]

        except Exception as e:
            logger.error(f"Error in decision timeout handler: {str(e)}")

    async def _handle_control_point_reached(self, message: ProcessingMessage) -> None:
        """Handle control point reached notification"""
        logger.info(f"Control point reached: {message.content}")

    async def _handle_user_decision(self, message: ProcessingMessage) -> None:
        """Handle submitted user decision"""
        logger.info(f"User decision received: {message.content}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the Control Point Manager

        Returns:
            Dict[str, Any]: Status information
        """
        return {
            'active_control_points': len(self.active_control_points),
            'pending_decisions': len(self.pending_decisions),
            'message_handlers_setup': self._setup_complete
        }

    async def cleanup(self) -> None:
        """
        Comprehensive cleanup of control point resources
        """
        try:
            # Cancel all pending decisions
            for future in self.pending_decisions.values():
                if not future.done():
                    future.cancel()

            # Clear active control points and pending decisions
            self.active_control_points.clear()
            self.pending_decisions.clear()

            logger.info("Control Point Manager cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during Control Point Manager cleanup: {str(e)}")

    async def create_control_point(
            self,
            pipeline_id: str,
            stage: ProcessingStage,
            data: Dict[str, Any],
            options: List[str],
            timeout_seconds: int = 3600
    ) -> str:
        """Create a new control point and notify users"""

        control_point = ControlPoint(
            pipeline_id=pipeline_id,
            stage=stage,
            data=data,
            options=options,
            timeout_seconds=timeout_seconds
        )

        # Store control point
        control_point_id = f"{pipeline_id}_{stage.value}_{datetime.now().timestamp()}"
        self.active_control_points[control_point_id] = control_point

        # Create future for decision
        self.pending_decisions[control_point_id] = asyncio.Future()

        # Notify users - now using async publish
        await self._notify_control_point(control_point_id, control_point)

        # Set up timeout
        self._setup_decision_timeout(control_point_id, timeout_seconds)

        return control_point_id

    async def _notify_control_point(self, control_point_id: str, control_point: ControlPoint) -> None:
        """Asynchronous notification of control point"""
        message = ProcessingMessage(
            source_identifier=self.module_id,
            target_identifier=ModuleIdentifier("ui_handler"),
            message_type=MessageType.CONTROL_POINT_REACHED,
            content={
                'control_point_id': control_point_id,
                'pipeline_id': control_point.pipeline_id,
                'stage': control_point.stage.value,
                'data': control_point.data,
                'options': control_point.options,
                'timeout_seconds': control_point.timeout_seconds
            }
        )
        await self.message_broker.publish(message)
