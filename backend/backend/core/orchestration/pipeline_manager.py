# backend/core/orchestration/pipeline_manager.py

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from queue import Queue
from threading import Thread

from backend.core.orchestration.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    ModuleIdentifier,
    ComponentType,
    ProcessingMessage,
    ProcessingStatus,
    MessageType
)

from .pipeline_manager_helper import (
    PipelineChannelType,
    PipelineState,
    MessageHandler,
    PipelineStateManager,
    DatabaseHelper,
    PipelineOperations,
    QualityHandler,
    SourceHandler
)

logger = logging.getLogger(__name__)


class PipelineManager(BaseManager):
    """Pipeline manager for handling pipeline operations"""

    def __init__(self, message_broker: MessageBroker, db_session=None):
        """Initialize pipeline manager"""
        super().__init__(message_broker=message_broker, component_name="PipelineManager")

        # Initialize components
        self.db_session = db_session
        self.state_manager = PipelineStateManager()
        self.message_queue = Queue()
        self._handlers = MessageHandler.get_default_handlers()

        # Start processing
        self._initialize_pipeline_components()
        self._start_message_processor()

    def _initialize_pipeline_components(self) -> None:
        """Initialize pipeline components with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._register_pipeline_handlers()
                self._initialize_messaging()
                logger.info("Pipeline components initialized successfully")
                break
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed to initialize pipeline components: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                import time
                time.sleep(1)

    def _register_pipeline_handlers(self) -> None:
        """Register message type handlers"""
        try:
            self._handlers.update({
                MessageType.PIPELINE_START: self._handle_pipeline_start,
                MessageType.PIPELINE_PAUSE: self._handle_pipeline_pause,
                MessageType.PIPELINE_RESUME: self._handle_pipeline_resume,
                MessageType.PIPELINE_CANCEL: self._handle_pipeline_cancel,
                MessageType.QUALITY_COMPLETE: self._handle_quality_message,
                MessageType.SOURCE_SUCCESS: self._handle_source_message
            })
            logger.info("Pipeline handlers registered successfully")
        except Exception as e:
            logger.error(f"Error registering handlers: {str(e)}")
            raise

    def _initialize_messaging(self) -> None:
        """Initialize pipeline-specific message handling"""
        try:
            # First call parent's initialization
            super()._initialize_messaging()

            logger.info("Starting pipeline messaging initialization...")
            logger.info(f"Message Broker Configuration: {self.message_broker}")

            component_id = ModuleIdentifier(
                component_name="pipeline",
                component_type=ComponentType.MANAGER,
                method_name="handle_pipeline_message"
            )

            base_patterns = [
                f"{component_id.get_tag()}.{MessageType.PIPELINE_START.value}",
                f"{component_id.get_tag()}.{MessageType.PIPELINE_PAUSE.value}",
                f"{component_id.get_tag()}.{MessageType.PIPELINE_RESUME.value}",
                f"{component_id.get_tag()}.{MessageType.PIPELINE_CANCEL.value}",
                f"{component_id.get_tag()}.{MessageType.QUALITY_COMPLETE.value}",
                f"{component_id.get_tag()}.{MessageType.SOURCE_SUCCESS.value}"
            ]

            success_count = 0
            for pattern in base_patterns:
                try:
                    logger.info(f"Attempting to subscribe to pattern: {pattern}")
                    logger.info(f"Component ID tag: {component_id.get_tag()}")
                    logger.info(f"Full subscription pattern: {pattern}")
                    logger.info(f"Current subscriptions: {self.message_broker.subscriptions}")

                    start_time = time.time()
                    self.message_broker.subscribe(
                        component=component_id,
                        pattern=pattern,
                        callback=self._handle_pipeline_message,
                        timeout=5.0
                    )
                    success_count += 1
                    logger.info(f"Successfully subscribed to {pattern} in {time.time() - start_time:.2f} seconds")
                except Exception as e:
                    logger.error(f"CRITICAL: Failed to subscribe to pattern {pattern}: {str(e)}")
                    continue

            if success_count == 0:
                raise RuntimeError("Failed to subscribe to any patterns")

            logger.info(f"Successfully subscribed to {success_count} patterns")

        except Exception as e:
            logger.error(f"CRITICAL: Pipeline messaging initialization failed: {str(e)}")
            raise

    def _start_message_processor(self) -> None:
        """Start asynchronous message processing"""

        def process_messages():
            while True:
                try:
                    message = self.message_queue.get()
                    MessageHandler.handle_pipeline_message(message, self._handlers)
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                finally:
                    self.message_queue.task_done()

        Thread(target=process_messages, daemon=True).start()
        logger.info("Message processor started")

    def _handle_pipeline_message(self, message: ProcessingMessage) -> None:
        """Queue message for processing"""
        self.message_queue.put(message)

    def _handle_pipeline_start(self, message: ProcessingMessage) -> None:
        """Handle pipeline start message"""
        pipeline_id = message.metadata.get('pipeline_id')
        try:
            PipelineOperations.start_pipeline(self.db_session, pipeline_id, self.state_manager)
        except Exception as e:
            logger.error(f"Error handling pipeline start: {str(e)}")
            raise

    def _handle_pipeline_pause(self, message: ProcessingMessage) -> None:
        """Handle pipeline pause message"""
        pipeline_id = message.metadata.get('pipeline_id')
        try:
            PipelineOperations.pause_pipeline(self.db_session, pipeline_id, self.state_manager)
        except Exception as e:
            logger.error(f"Error handling pipeline pause: {str(e)}")
            raise

    def _handle_pipeline_resume(self, message: ProcessingMessage) -> None:
        """Handle pipeline resume message"""
        pipeline_id = message.metadata.get('pipeline_id')
        try:
            PipelineOperations.resume_pipeline(self.db_session, pipeline_id, self.state_manager)
        except Exception as e:
            logger.error(f"Error handling pipeline resume: {str(e)}")
            raise

    def _handle_pipeline_cancel(self, message: ProcessingMessage) -> None:
        """Handle pipeline cancel message"""
        pipeline_id = message.metadata.get('pipeline_id')
        try:
            PipelineOperations.cancel_pipeline(self.db_session, pipeline_id, self.state_manager)
        except Exception as e:
            logger.error(f"Error handling pipeline cancel: {str(e)}")
            raise

    def _handle_quality_message(self, message: ProcessingMessage) -> None:
        """Handle quality check messages"""
        try:
            QualityHandler.handle_quality_message(self.db_session, message, self.state_manager)
        except Exception as e:
            logger.error(f"Error handling quality message: {str(e)}")
            raise

    def _handle_source_message(self, message: ProcessingMessage) -> None:
        """Handle source messages"""
        try:
            SourceHandler.handle_source_message(self.db_session, message, self.state_manager)
        except Exception as e:
            logger.error(f"Error handling source message: {str(e)}")
            raise

    def cleanup(self) -> None:
        """Cleanup pipeline manager resources"""
        try:
            logger.info("Starting pipeline manager cleanup...")
            # Cleanup active pipelines
            for pipeline_id in list(self.state_manager.active_pipelines.keys()):
                try:
                    self._cleanup_pipeline(pipeline_id)
                except Exception as e:
                    logger.error(f"Error cleaning up pipeline {pipeline_id}: {str(e)}")

            # Clear message queue
            while not self.message_queue.empty():
                try:
                    self.message_queue.get_nowait()
                except Exception:
                    pass

            # Call parent cleanup
            super().cleanup()
            logger.info("Pipeline manager cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def _cleanup_pipeline(self, pipeline_id: str) -> None:
        """Cleanup single pipeline"""
        try:
            # Cancel if running
            state = self.state_manager.get_pipeline_state(pipeline_id)
            if state and state.status in [ProcessingStatus.RUNNING, ProcessingStatus.PENDING]:
                PipelineOperations.cancel_pipeline(self.db_session, pipeline_id, self.state_manager)

            # Remove from active pipelines
            self.state_manager.remove_pipeline(pipeline_id)
            logger.info(f"Pipeline {pipeline_id} cleaned up")

        except Exception as e:
            logger.error(f"Error cleaning up pipeline {pipeline_id}: {str(e)}")
            raise

    def __del__(self):
        """Safe deletion"""
        try:
            self.cleanup()
        except Exception as e:
            logger.error(f"Error during deletion: {str(e)}")