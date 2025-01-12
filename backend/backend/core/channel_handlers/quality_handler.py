import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID

from backend.core.channel_handlers.base_channel_handler import BaseChannelHandler
from backend.core.channel_handlers.core_process_handler import CoreProcessHandler
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ProcessingStage,
    ModuleIdentifier,
    ComponentType
)
from backend.data_pipeline.quality_analysis.data_quality_processor import (
    DataQualityProcessor,
    QualityPhase
)

logger = logging.getLogger(__name__)


class QualityChannelHandler(BaseChannelHandler):
    """
    Handles communication and routing for quality-related messages

    Responsibilities:
    - Route quality-related messages
    - Coordinate with data quality processor
    - Interface with quality manager
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            process_handler: Optional[CoreProcessHandler] = None,
            quality_processor: Optional[DataQualityProcessor] = None
    ):
        """
        Initialize quality channel handler

        Args:
            message_broker: Message broker for communication
            process_handler: Optional process handler
            quality_processor: Optional data quality processor
        """
        super().__init__(message_broker, "quality_handler")

        # Initialize dependencies
        self.process_handler = process_handler or CoreProcessHandler(message_broker)
        self.quality_processor = quality_processor or DataQualityProcessor(message_broker)

        # Register message handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register message handlers for quality processing"""
        self.register_callback(
            MessageType.QUALITY_START,
            self._handle_quality_start
        )
        self.register_callback(
            MessageType.QUALITY_COMPLETE,
            self._handle_quality_complete
        )
        self.register_callback(
            MessageType.QUALITY_UPDATE,
            self._handle_quality_update
        )
        self.register_callback(
            MessageType.QUALITY_ERROR,
            self._handle_quality_error
        )

    def _handle_quality_start(self, message: ProcessingMessage) -> None:
        """
        Handle quality check start request

        Args:
            message: Processing message for quality check start
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            data = message.content.get('data', {})
            context = message.content.get('context', {})

            # Create a response message to quality manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="quality_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_quality_start"
                ),
                message_type=MessageType.QUALITY_STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'status': 'started',
                    'phase': QualityPhase.DETECTION.value
                }
            )

            # Execute process via process handler
            self.process_handler.execute_process(
                self._run_quality_check,
                pipeline_id=pipeline_id,
                stage=ProcessingStage.QUALITY_CHECK,
                message_type=MessageType.QUALITY_START,
                data=data,
                context=context
            )

            # Publish response to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to start quality check: {e}")
            self._handle_quality_error(
                ProcessingMessage(
                    source_identifier=self.module_id,
                    target_identifier=ModuleIdentifier(
                        component_name="quality_manager",
                        component_type=ComponentType.MANAGER
                    ),
                    message_type=MessageType.QUALITY_ERROR,
                    content={
                        'error': str(e),
                        'pipeline_id': message.content.get('pipeline_id')
                    }
                )
            )

    async def _run_quality_check(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core quality check execution logic

        Args:
            data: Data to be quality checked
            context: Processing context

        Returns:
            Quality check results
        """
        try:
            # Run detection phase
            detection_results = await self.quality_processor.run_detection_phase(
                context.get('check_id'),
                data,
                context
            )

            # Run analysis phase
            analysis_results = await self.quality_processor.run_analysis_phase(
                context.get('check_id'),
                detection_results
            )

            # Run resolution phase
            resolution_results = await self.quality_processor.run_resolution_phase(
                context.get('check_id'),
                analysis_results
            )

            # Prepare final results
            return {
                'detection_results': detection_results,
                'analysis_results': analysis_results,
                'resolution_results': resolution_results,
                'pipeline_id': context.get('pipeline_id')
            }

        except Exception as e:
            logger.error(f"Quality check failed: {e}")
            raise

    def _handle_quality_complete(self, message: ProcessingMessage) -> None:
        """
        Handle quality check completion

        Args:
            message: Processing message about quality check completion
        """
        try:
            # Create completion response for manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="quality_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_quality_complete"
                ),
                message_type=MessageType.QUALITY_COMPLETE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'results': message.content.get('results', {}),
                    'status': 'completed'
                }
            )

            # Publish completion to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling quality completion: {e}")

    def _handle_quality_update(self, message: ProcessingMessage) -> None:
        """
        Handle quality process updates

        Args:
            message: Processing message with quality update
        """
        try:
            # Forward update to quality manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="quality_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_quality_update"
                ),
                message_type=MessageType.QUALITY_STATUS_UPDATE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'status': message.content.get('status'),
                    'progress': message.content.get('progress')
                }
            )

            # Publish update to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling quality update: {e}")

    def _handle_quality_error(self, message: ProcessingMessage) -> None:
        """
        Handle quality process errors

        Args:
            message: Processing message with error details
        """
        try:
            # Forward error to quality manager
            error_response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="quality_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_quality_error"
                ),
                message_type=MessageType.QUALITY_ERROR,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'error': message.content.get('error')
                }
            )

            # Publish error to manager
            self.message_broker.publish(error_response)

        except Exception as e:
            logger.error(f"Error handling quality error: {e}")

    def get_process_status(self, check_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current process status

        Args:
            check_id: Unique check identifier

        Returns:
            Process status dictionary or None
        """
        return self.process_handler.get_process_status(check_id)