# backend/core/managers/insight_manager.py

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
    MessageMetadata,
    InsightContext,
    InsightState,
    ModuleIdentifier,
    ComponentType
)

logger = logging.getLogger(__name__)


class InsightManager:
    """
    Insight Manager: Coordinates high-level insight workflow via message-driven communication
    Only communicates through message broker
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.active_contexts: Dict[str, InsightContext] = {}

        # Manager identification
        self.module_identifier = ModuleIdentifier(
            component_name="insight_manager",
            component_type=ComponentType.INSIGHT_MANAGER,
            department="insight",
            role="manager"
        )

        # Setup subscriptions
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup message subscriptions"""
        handlers = {
            # CPM Messages
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.CONTROL_POINT_UPDATE: self._handle_control_point_update,
            MessageType.CONTROL_POINT_DECISION: self._handle_control_point_decision,

            # Service Messages
            MessageType.INSIGHT_SERVICE_STATUS: self._handle_service_status,
            MessageType.INSIGHT_SERVICE_COMPLETE: self._handle_service_complete,
            MessageType.INSIGHT_SERVICE_ERROR: self._handle_service_error,

            # Staging Messages
            MessageType.STAGING_COMPLETE: self._handle_staging_complete,
            MessageType.STAGING_ERROR: self._handle_staging_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_control_point_created(self, message: ProcessingMessage) -> None:
        """Handle new control point for insight generation"""
        try:
            pipeline_id = message.content['pipeline_id']
            control_point_id = message.content['control_point_id']
            config = message.content.get('config', {})

            # Create insight context
            context = InsightContext(
                pipeline_id=pipeline_id,
                control_point_id=control_point_id,
                state=InsightState.INITIALIZING,
                config=config
            )
            self.active_contexts[pipeline_id] = context

            # Request service start
            await self._publish_service_start(pipeline_id, config)

        except Exception as e:
            logger.error(f"Control point handling failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_control_point_update(self, message: ProcessingMessage) -> None:
        """Handle control point updates"""
        try:
            pipeline_id = message.content['pipeline_id']
            update_type = message.content.get('update_type')
            update_data = message.content.get('update_data', {})

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Forward update to service
            await self._publish_service_update(pipeline_id, update_type, update_data)

        except Exception as e:
            logger.error(f"Update handling failed: {str(e)}")

    async def _handle_control_point_decision(self, message: ProcessingMessage) -> None:
        """Handle decisions about insight process"""
        try:
            pipeline_id = message.content['pipeline_id']
            decision = message.content['decision']

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Forward decision to service
            await self._publish_service_decision(pipeline_id, decision)

        except Exception as e:
            logger.error(f"Decision handling failed: {str(e)}")

    async def _handle_service_status(self, message: ProcessingMessage) -> None:
        """Handle status updates from service"""
        pipeline_id = message.content['pipeline_id']
        status = message.content['status']

        context = self.active_contexts.get(pipeline_id)
        if context:
            # Update context state
            context.status = status

            # Notify CPM of status
            await self._publish_status_update(pipeline_id, status)

    async def _handle_service_complete(self, message: ProcessingMessage) -> None:
        """Handle service completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            results = message.content.get('results', {})

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Notify CPM of completion
            await self._publish_completion(pipeline_id, results)

            # Cleanup
            del self.active_contexts[pipeline_id]

        except Exception as e:
            logger.error(f"Completion handling failed: {str(e)}")

    async def _handle_service_error(self, message: ProcessingMessage) -> None:
        """Handle service errors"""
        pipeline_id = message.content['pipeline_id']
        error = message.content['error']

        await self._publish_error(pipeline_id, error)

        # Cleanup
        if pipeline_id in self.active_contexts:
            del self.active_contexts[pipeline_id]

    async def _publish_service_start(self, pipeline_id: str, config: Dict[str, Any]) -> None:
        """Publish service start request"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.INSIGHT_SERVICE_START,
                content={
                    'pipeline_id': pipeline_id,
                    'config': config
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="insight_service"
                )
            )
        )

    async def _publish_service_update(
            self,
            pipeline_id: str,
            update_type: str,
            update_data: Dict[str, Any]
    ) -> None:
        """Publish service update"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.INSIGHT_SERVICE_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'update_type': update_type,
                    'update_data': update_data
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="insight_service"
                )
            )
        )

    async def _publish_service_decision(
            self,
            pipeline_id: str,
            decision: Dict[str, Any]
    ) -> None:
        """Publish service decision"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.INSIGHT_SERVICE_DECISION,
                content={
                    'pipeline_id': pipeline_id,
                    'decision': decision
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="insight_service"
                )
            )
        )

    async def _publish_status_update(self, pipeline_id: str, status: Dict[str, Any]) -> None:
        """Publish status update to CPM"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_STAGE_STATUS,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.INSIGHT_GENERATION,
                    'status': status
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager"
                )
            )
        )

    async def _publish_completion(self, pipeline_id: str, results: Dict[str, Any]) -> None:
        """Publish completion to CPM"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_STAGE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.INSIGHT_GENERATION,
                    'results': results
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager"
                )
            )
        )

    async def _publish_error(self, pipeline_id: str, error: str) -> None:
        """Publish error to CPM"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.INSIGHT_GENERATION,
                    'error': error
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager"
                )
            )
        )

    async def cleanup(self) -> None:
        """Cleanup manager resources"""
        try:
            # Notify cleanup for active contexts
            for pipeline_id in list(self.active_contexts.keys()):
                await self._publish_error(
                    pipeline_id,
                    "Manager cleanup initiated"
                )
                del self.active_contexts[pipeline_id]

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise

    async def _handle_staging_complete(self, message: ProcessingMessage) -> None:
        """
        Handle successful staging of data for insight generation

        Args:
            message (ProcessingMessage): Staging completion message
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            staged_data = message.content.get('data', {})

            context = self.active_contexts.get(pipeline_id)
            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update context with staged data
            context.staged_data = staged_data
            context.state = InsightState.DATA_PREPARED

            # Initiate insight generation
            await self._publish_service_start(pipeline_id, {
                **context.config,
                'staged_data': staged_data
            })

            logger.info(f"Staging completed for pipeline {pipeline_id}")

        except Exception as e:
            logger.error(f"Staging completion handling failed: {str(e)}")
            await self._publish_error(pipeline_id, f"Staging error: {str(e)}")


    async def _handle_staging_error(self, message: ProcessingMessage) -> None:
        """
        Handle errors during data staging

        Args:
            message (ProcessingMessage): Staging error message
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            error = message.content.get('error', 'Unknown staging error')

            # Publish error to control point manager
            await self._publish_error(pipeline_id, error)

            # Remove context
            if pipeline_id in self.active_contexts:
                del self.active_contexts[pipeline_id]

            logger.error(f"Staging error for pipeline {pipeline_id}: {error}")

        except Exception as e:
            logger.critical(f"Error handling staging error: {str(e)}")


    def _generate_correlation_id(self) -> str:
        """
        Generate a unique correlation ID for tracking

        Returns:
            str: Unique correlation identifier
        """
        return str(uuid.uuid4())


    async def initiate_insight_generation(
            self,
            pipeline_id: Optional[str] = None,
            config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Initiate a new insight generation process

        Args:
            pipeline_id (Optional[str]): Existing pipeline ID or None to generate new
            config (Optional[Dict[str, Any]]): Configuration for insight generation

        Returns:
            str: Pipeline ID for the insight generation process
        """
        try:
            # Generate pipeline ID if not provided
            current_pipeline_id = pipeline_id or self._generate_correlation_id()
            current_config = config or {}

            # Create insight context
            context = InsightContext(
                pipeline_id=current_pipeline_id,
                state=InsightState.INITIALIZING,
                config=current_config,
                created_at=datetime.now()
            )
            self.active_contexts[current_pipeline_id] = context

            # Publish service start
            await self._publish_service_start(current_pipeline_id, current_config)

            logger.info(f"Insight generation initiated for pipeline {current_pipeline_id}")
            return current_pipeline_id

        except Exception as e:
            logger.error(f"Insight generation initiation failed: {str(e)}")
            raise


    async def _monitor_insight_processes(self) -> None:
        """
        Monitor long-running insight generation processes
        """
        try:
            while True:
                current_time = datetime.now()
                timeout_threshold = current_time - timedelta(hours=2)  # 2-hour timeout

                # Check for and handle timed-out processes
                for pipeline_id, context in list(self.active_contexts.items()):
                    if context.created_at < timeout_threshold:
                        await self._publish_error(
                            pipeline_id,
                            "Insight generation exceeded maximum time limit"
                        )
                        # Remove timed-out context
                        del self.active_contexts[pipeline_id]

                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes

        except Exception as e:
            logger.error(f"Insight process monitoring failed: {str(e)}")


    async def cancel_insight_generation(self, pipeline_id: str) -> None:
        """
        Cancel an ongoing insight generation process

        Args:
            pipeline_id (str): Pipeline ID to cancel
        """
        try:
            context = self.active_contexts.get(pipeline_id)
            if not context:
                logger.warning(f"No active context found for pipeline {pipeline_id}")
                return

            # Publish cancellation request
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_SERVICE_CANCEL,
                    content={
                        'pipeline_id': pipeline_id
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="insight_service"
                    )
                )
            )

            # Remove context
            del self.active_contexts[pipeline_id]

            logger.info(f"Insight generation cancelled for pipeline {pipeline_id}")

        except Exception as e:
            logger.error(f"Insight generation cancellation failed: {str(e)}")
            await self._publish_error(pipeline_id, f"Cancellation error: {str(e)}")


    def _validate_insight_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate insight generation configuration

        Args:
            config (Dict[str, Any]): Configuration to validate

        Returns:
            bool: Whether the configuration is valid
        """
        # Implement basic configuration validation
        required_keys = ['data_source', 'analysis_type']

        for key in required_keys:
            if key not in config:
                logger.warning(f"Missing required configuration key: {key}")
                return False

        # Additional validation can be added here
        return True


    async def _start_background_tasks(self) -> None:
        """
        Start background monitoring tasks
        """
        # Start process monitoring
        asyncio.create_task(self._monitor_insight_processes())