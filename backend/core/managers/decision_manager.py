# backend/core/managers/decision_manager.py

import logging
import asyncio
from datetime import timedelta
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    DecisionContext,
    DecisionState,
    MessageMetadata,
    ModuleIdentifier,
    ComponentType,
    ManagerState
)
from .base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class DecisionManager(BaseManager):
    """
    Decision Manager coordinates decision workflow through message-based communication.
    Responsible for orchestrating the decision process while maintaining workflow state.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.module_identifier = ModuleIdentifier(
            component_name="decision_manager",
            component_type=ComponentType.DECISION_MANAGER,
            department="decision",
            role="manager"
        )

        # State management
        self.active_processes: Dict[str, DecisionContext] = {}
        self.state = ManagerState.INITIALIZING

        # Initialize manager
        self._initialize_manager()

    def _initialize_manager(self) -> None:
        """Initialize manager components"""
        self._setup_message_handlers()
        self._start_monitoring_tasks()
        self.state = ManagerState.ACTIVE

    def _setup_message_handlers(self) -> None:
        """Setup subscriptions for all incoming messages"""
        handlers = {
            # Service Layer Responses
            MessageType.DECISION_SERVICE_COMPLETE: self._handle_service_complete,
            MessageType.DECISION_SERVICE_ERROR: self._handle_service_error,
            MessageType.DECISION_SERVICE_STATUS: self._handle_service_status,

            # Decision Flow Responses
            MessageType.DECISION_OPTIONS_READY: self._handle_options_ready,
            MessageType.DECISION_VALIDATION_COMPLETE: self._handle_validation_complete,
            MessageType.DECISION_IMPACT_ASSESSED: self._handle_impact_assessed,
            MessageType.DECISION_FEEDBACK_RECEIVED: self._handle_feedback_received,

            # Control Point Messages
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.CONTROL_POINT_UPDATED: self._handle_control_point_updated,

            # Resource Messages
            MessageType.RESOURCE_ALLOCATED: self._handle_resource_allocated,
            MessageType.RESOURCE_RELEASED: self._handle_resource_released,

            # System Messages
            MessageType.DECISION_HEALTH_CHECK: self._handle_health_check,
            MessageType.DECISION_CONFIG_UPDATE: self._handle_config_update
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def request_decision(
            self,
            pipeline_id: str,
            options: Dict[str, Any],
            config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Initiate a new decision request through the service layer
        Returns correlation ID for tracking
        """
        correlation_id = str(uuid.uuid4())

        try:
            # Create decision context
            context = DecisionContext(
                pipeline_id=pipeline_id,
                correlation_id=correlation_id,
                options=options,
                state=DecisionState.INITIALIZING,
                config=config or {},
                created_at=datetime.now()
            )

            self.active_processes[pipeline_id] = context

            # Request through service layer
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_SERVICE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'options': options,
                        'config': context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="decision_service",
                        domain_type="decision",
                        processing_stage=ProcessingStage.DECISION_MAKING
                    ),
                    source_identifier=self.module_identifier
                )
            )

            logger.info(f"Decision request initiated for pipeline: {pipeline_id}")
            return correlation_id

        except Exception as e:
            logger.error(f"Failed to initiate decision request: {str(e)}")
            raise

    async def _handle_service_complete(self, message: ProcessingMessage) -> None:
        """Handle completion message from service layer"""
        pipeline_id = message.content["pipeline_id"]
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context
            context.state = DecisionState.COMPLETED
            context.completed_at = datetime.now()
            context.results = message.content.get("results", {})

            # Notify completion
            await self._notify_completion(pipeline_id, context.results)

            # Cleanup
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Service completion handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_options_ready(self, message: ProcessingMessage) -> None:
        """Handle options ready notification"""
        pipeline_id = message.content["pipeline_id"]
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context with options
            context.available_options = message.content.get("options", [])
            context.state = DecisionState.OPTION_GENERATION

            # Request validation if needed
            if context.requires_validation:
                await self._request_validation(pipeline_id)
            else:
                await self._request_impact_analysis(pipeline_id)

        except Exception as e:
            logger.error(f"Options handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_validation_complete(self, message: ProcessingMessage) -> None:
        """Handle validation completion"""
        pipeline_id = message.content["pipeline_id"]
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            validation_results = message.content.get("validation_results", {})
            is_valid = validation_results.get("is_valid", False)

            if is_valid:
                await self._request_impact_analysis(pipeline_id)
            else:
                await self._handle_validation_failure(
                    pipeline_id,
                    validation_results.get("issues", [])
                )

        except Exception as e:
            logger.error(f"Validation handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_impact_assessed(self, message: ProcessingMessage) -> None:
        """Handle impact assessment completion"""
        pipeline_id = message.content["pipeline_id"]
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            context.impacts = message.content.get("impacts", {})
            context.state = DecisionState.IMPACT_ANALYSIS

            if context.requires_approval:
                await self._request_approval(pipeline_id)
            else:
                await self._finalize_decision(pipeline_id)

        except Exception as e:
            logger.error(f"Impact assessment handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _request_validation(self, pipeline_id: str) -> None:
        """Request validation through service layer"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.DECISION_SERVICE_VALIDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'options': context.available_options,
                    'constraints': context.config.get("constraints", {})
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="decision_service"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _request_impact_analysis(self, pipeline_id: str) -> None:
        """Request impact analysis through service layer"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.DECISION_SERVICE_ANALYZE_IMPACT,
                content={
                    'pipeline_id': pipeline_id,
                    'options': context.available_options,
                    'config': context.config
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="decision_service"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_error(self, pipeline_id: str, error: str) -> None:
        """Handle errors in decision process"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            context.state = DecisionState.FAILED
            context.error = error

            # Notify error
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'stage': context.state.value
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="control_point_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def _notify_completion(self, pipeline_id: str, results: Dict[str, Any]) -> None:
        """Notify decision completion"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.DECISION_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'results': results,
                    'completion_time': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _cleanup_process(self, pipeline_id: str) -> None:
        """Clean up process resources"""
        if pipeline_id in self.active_processes:
            del self.active_processes[pipeline_id]

    async def cleanup(self) -> None:
        """Clean up manager resources"""
        self.state = ManagerState.SHUTDOWN

        try:
            # Clean up all active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self._cleanup_process(pipeline_id)

            # Unsubscribe from all messages
            await self.message_broker.unsubscribe_all(self.module_identifier)

        except Exception as e:
            logger.error(f"Manager cleanup failed: {str(e)}")
            raise

    async def _handle_service_error(self, message: ProcessingMessage) -> None:
        """
        Handle error message from service layer

        Args:
            message (ProcessingMessage): Error message from service
        """
        pipeline_id = message.content.get("pipeline_id")
        error = message.content.get("error", "Unknown service error")

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update context
            context.state = DecisionState.FAILED
            context.error = error

            # Publish error
            await self._handle_error(pipeline_id, error)

        except Exception as e:
            logger.error(f"Service error handling failed: {str(e)}")


    async def _handle_service_status(self, message: ProcessingMessage) -> None:
        """
        Handle status update from service layer

        Args:
            message (ProcessingMessage): Status update message
        """
        pipeline_id = message.content.get("pipeline_id")
        status = message.content.get("status")
        progress = message.content.get("progress", 0.0)

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update context
            context.status = status
            context.progress = progress

            # Publish status update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_STATUS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': status,
                        'progress': progress,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="control_point_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Service status handling failed: {str(e)}")


    async def _handle_feedback_received(self, message: ProcessingMessage) -> None:
        """
        Handle feedback for the decision process

        Args:
            message (ProcessingMessage): Feedback message
        """
        pipeline_id = message.content.get("pipeline_id")
        feedback = message.content.get("feedback", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update context with feedback
            context.feedback = feedback
            context.state = DecisionState.FEEDBACK_RECEIVED

            # Process feedback
            await self._process_feedback(pipeline_id, feedback)

        except Exception as e:
            logger.error(f"Feedback handling failed: {str(e)}")
            await self._handle_error(pipeline_id, f"Feedback processing error: {str(e)}")


    async def _process_feedback(self, pipeline_id: str, feedback: Dict[str, Any]) -> None:
        """
        Process and potentially adjust decision based on feedback

        Args:
            pipeline_id (str): Unique identifier for the processing pipeline
            feedback (Dict[str, Any]): Feedback details
        """
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Determine if feedback requires decision modification
            if feedback.get('requires_adjustment', False):
                await self._request_decision_adjustment(pipeline_id, feedback)
            else:
                await self._finalize_decision(pipeline_id)

        except Exception as e:
            logger.error(f"Feedback processing failed: {str(e)}")
            await self._handle_error(pipeline_id, f"Feedback processing error: {str(e)}")


    async def _request_decision_adjustment(self, pipeline_id: str, feedback: Dict[str, Any]) -> None:
        """
        Request decision adjustment based on feedback

        Args:
            pipeline_id (str): Unique identifier for the processing pipeline
            feedback (Dict[str, Any]): Feedback details
        """
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.DECISION_SERVICE_ADJUST,
                content={
                    'pipeline_id': pipeline_id,
                    'feedback': feedback,
                    'current_options': context.available_options
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="decision_service"
                ),
                source_identifier=self.module_identifier
            )
        )


    async def _finalize_decision(self, pipeline_id: str) -> None:
        """
        Finalize the decision process

        Args:
            pipeline_id (str): Unique identifier for the processing pipeline
        """
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Select best option
            selected_option = self._select_best_option(context)

            # Publish final decision
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_FINALIZED,
                    content={
                        'pipeline_id': pipeline_id,
                        'selected_option': selected_option,
                        'impacts': context.impacts,
                        'feedback': context.feedback
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="control_point_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            context.state = DecisionState.COMPLETED
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Decision finalization failed: {str(e)}")
            await self._handle_error(pipeline_id, f"Finalization error: {str(e)}")


    def _select_best_option(self, context: DecisionContext) -> Dict[str, Any]:
        """
        Select the best option based on impact analysis and constraints

        Args:
            context (DecisionContext): Current decision context

        Returns:
            Dict[str, Any]: Selected best option
        """
        if not context.available_options:
            raise ValueError("No options available for selection")

        # Simple selection strategy - can be made more complex
        if context.impacts:
            # Sort options by impact score if available
            ranked_options = sorted(
                context.available_options,
                key=lambda opt: context.impacts.get(opt.get('id', ''), 0),
                reverse=True
            )
            return ranked_options[0]

        # Fallback to first option if no impact analysis
        return context.available_options[0]


    async def _handle_control_point_created(self, message: ProcessingMessage) -> None:
        """
        Handle new control point creation

        Args:
            message (ProcessingMessage): Control point creation message
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            config = message.content.get('config', {})

            # Check if decision is needed
            if config.get('requires_decision', False):
                # Initiate decision process
                await self.request_decision(
                    pipeline_id=pipeline_id,
                    options=config.get('options', {}),
                    config=config
                )

        except Exception as e:
            logger.error(f"Control point creation handling failed: {str(e)}")


    async def _handle_control_point_updated(self, message: ProcessingMessage) -> None:
        """
        Handle control point updates

        Args:
            message (ProcessingMessage): Control point update message
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            update_type = message.content.get('update_type')

            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Handle specific update types
            if update_type == 'constraints_update':
                context.config['constraints'] = message.content.get('constraints', {})
                await self._request_validation(pipeline_id)

            elif update_type == 'options_update':
                context.available_options = message.content.get('options', [])
                await self._request_validation(pipeline_id)

        except Exception as e:
            logger.error(f"Control point update handling failed: {str(e)}")


    def _start_monitoring_tasks(self) -> None:
        """
        Start background monitoring tasks
        """
        import asyncio

        # Monitor process timeouts
        asyncio.create_task(self._monitor_process_timeouts())


    async def _monitor_process_timeouts(self) -> None:
        """
        Monitor and handle long-running decision processes
        """
        while self.state == ManagerState.ACTIVE:
            try:
                current_time = datetime.now()
                timeout_threshold = datetime.now() - timedelta(hours=1)

                for pipeline_id, context in list(self.active_processes.items()):
                    if context.created_at < timeout_threshold:
                        await self._handle_error(
                            pipeline_id,
                            "Decision process exceeded maximum time limit"
                        )

                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Process timeout monitoring failed: {str(e)}")