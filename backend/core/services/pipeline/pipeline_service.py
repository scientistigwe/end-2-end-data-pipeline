# backend/core/services/pipeline_service.py

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata,
    ProcessingStage,
    ProcessingStatus
)
from ...staging.staging_manager import StagingManager

logger = logging.getLogger(__name__)

def initialize_services(app):
    services = {
        'pipeline_service': PipelineService(
            staging_manager=staging_manager,
            message_broker=message_broker,
            initialize_async=True
        )
    }
    return services


class PipelineService:
    """
    Service layer for pipeline orchestration.
    Acts as message handler for pipeline-related requests from CPM.
    Coordinates pipeline lifecycle and routing between components.
    """
    def __init__(self, staging_manager, message_broker, initialize_async=False):
        self.staging_manager = staging_manager
        self.message_broker = message_broker

        self.module_identifier = ModuleIdentifier(
            component_name="pipeline_service",
            component_type=ComponentType.PIPELINE_SERVICE,
            department="pipeline",
            role="service"
        )

        self.logger = logger

        if initialize_async:
            asyncio.run(self._initialize_async())

    async def _initialize_async(self):
        await self._initialize_message_handlers()

    async def _initialize_message_handlers(self) -> None:
        handlers = {
            MessageType.PIPELINE_CREATE_REQUEST: self._handle_create_request,
            MessageType.PIPELINE_START_REQUEST: self._handle_start_request,
            MessageType.PIPELINE_STOP_REQUEST: self._handle_stop_request,
            MessageType.PIPELINE_PAUSE_REQUEST: self._handle_pause_request,
            MessageType.PIPELINE_RESUME_REQUEST: self._handle_resume_request,
            MessageType.PIPELINE_STATUS_REQUEST: self._handle_status_request,
            MessageType.PIPELINE_ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=f"pipeline.{message_type.value}.#",
                callback=handler
            )

    def _setup_message_handlers(self) -> None:
        """Setup handlers for pipeline-related messages"""
        handlers = {
            # Pipeline Lifecycle
            MessageType.PIPELINE_CREATE_REQUEST: self._handle_create_request,
            MessageType.PIPELINE_START_REQUEST: self._handle_start_request,
            MessageType.PIPELINE_STOP_REQUEST: self._handle_stop_request,
            MessageType.PIPELINE_PAUSE_REQUEST: self._handle_pause_request,
            MessageType.PIPELINE_RESUME_REQUEST: self._handle_resume_request,

            # Status and Monitoring
            MessageType.PIPELINE_STATUS_REQUEST: self._handle_status_request,
            MessageType.PIPELINE_PROGRESS_UPDATE: self._handle_progress_update,

            # Stage Control
            MessageType.STAGE_COMPLETE: self._handle_stage_complete,
            MessageType.STAGE_ERROR: self._handle_stage_error,
            MessageType.STAGE_READY: self._handle_stage_ready,

            # Error Handling
            MessageType.PIPELINE_ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                component=self.module_identifier.component_name,
                pattern=f"pipeline.{message_type.value}.#",
                callback=handler
            )

    async def _handle_create_request(self, message: ProcessingMessage) -> None:
        """Handle pipeline creation request"""
        try:
            config = message.content.get('config', {})
            user_id = message.content.get('user_id')

            # Validate config
            if not self._validate_pipeline_config(config):
                raise ValueError("Invalid pipeline configuration")

            # Store in staging
            staged_id = await self.staging_manager.store_incoming_data(
                pipeline_id=None,  # New pipeline
                data=config,
                source_type='pipeline_config',
                metadata={
                    'user_id': user_id,
                    'type': 'pipeline_creation',
                    'stage_sequence': config.get('stage_sequence', []),
                    'created_at': datetime.utcnow().isoformat()
                }
            )

            # Forward to CPM for pipeline creation
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_CREATE,
                    content={
                        'staged_id': staged_id,
                        'config': config,
                        'user_id': user_id
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="control_point_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle create request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_start_request(self, message: ProcessingMessage) -> None:
        """Handle pipeline start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            config = message.content.get('config', {})
            staged_id = message.content.get('staged_id')  # Optional staged data to process

            # Create initial pipeline state
            pipeline_staged_id = await self.staging_manager.store_incoming_data(
                pipeline_id=pipeline_id,
                data={
                    'config': config,
                    'status': 'starting',
                    'current_stage': ProcessingStage.RECEPTION.value,
                    'progress': 0,
                    'stages_completed': [],
                    'input_staged_id': staged_id
                },
                source_type='pipeline_state',
                metadata={
                    'type': 'pipeline_execution',
                    'started_at': datetime.utcnow().isoformat()
                }
            )

            # Forward to CPM to start execution
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'staged_id': pipeline_staged_id,
                        'input_staged_id': staged_id,
                        'config': config
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="control_point_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle start request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_stage_complete(self, message: ProcessingMessage) -> None:
        """Handle stage completion and transition"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            stage = message.content.get('stage')
            results = message.content.get('results', {})

            # Get pipeline state
            pipeline_state = await self.staging_manager.retrieve_data(
                pipeline_id,
                'PIPELINE'
            )
            if not pipeline_state:
                raise ValueError(f"Pipeline {pipeline_id} state not found")

            # Update completed stages
            completed_stages = pipeline_state.get('stages_completed', [])
            completed_stages.append(stage)

            # Get next stage
            stage_sequence = pipeline_state.get('config', {}).get('stage_sequence', [])
            next_stage = self._get_next_stage(stage, stage_sequence)

            # Update pipeline state
            await self.staging_manager.store_component_output(
                pipeline_id=pipeline_id,
                component_type='PIPELINE',
                output={
                    **pipeline_state,
                    'stages_completed': completed_stages,
                    'current_stage': next_stage if next_stage else None,
                    'status': 'completed' if not next_stage else 'running',
                    'stage_results': {
                        **pipeline_state.get('stage_results', {}),
                        stage: results
                    }
                },
                metadata={
                    'updated_at': datetime.utcnow().isoformat(),
                    'last_completed_stage': stage
                }
            )

            # If pipeline completed
            if not next_stage:
                await self._handle_pipeline_complete(pipeline_id)
            else:
                # Notify CPM about next stage
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.STAGE_READY,
                        content={
                            'pipeline_id': pipeline_id,
                            'stage': next_stage,
                            'previous_results': results
                        },
                        metadata=MessageMetadata(
                            source_component=self.module_identifier.component_name,
                            target_component="control_point_manager",
                            correlation_id=message.metadata.correlation_id
                        )
                    )
                )

        except Exception as e:
            self.logger.error(f"Failed to handle stage completion: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_pipeline_complete(self, pipeline_id: str) -> None:
        """Handle pipeline completion"""
        try:
            # Get final state
            pipeline_state = await self.staging_manager.retrieve_data(
                pipeline_id,
                'PIPELINE'
            )

            # Create completion summary
            completion_data = {
                'status': 'completed',
                'completed_at': datetime.utcnow().isoformat(),
                'execution_time': self._calculate_execution_time(
                    pipeline_state.get('metadata', {}).get('started_at')
                ),
                'stages_completed': pipeline_state.get('stages_completed', []),
                'final_results': pipeline_state.get('stage_results', {})
            }

            # Store completion state
            await self.staging_manager.store_component_output(
                pipeline_id=pipeline_id,
                component_type='PIPELINE',
                output={
                    **pipeline_state,
                    **completion_data
                },
                metadata={
                    'type': 'pipeline_completion',
                    'completed_at': datetime.utcnow().isoformat()
                }
            )

            # Notify about completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'completion_data': completion_data
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="control_point_manager"
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle pipeline completion: {str(e)}")
            await self._handle_error(
                ProcessingMessage(
                    content={'pipeline_id': pipeline_id, 'error': str(e)}
                )
            )

    async def _handle_stage_error(self, message: ProcessingMessage) -> None:
        """Handle stage errors"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            stage = message.content.get('stage')
            error = message.content.get('error')

            # Update pipeline state
            await self.staging_manager.store_component_output(
                pipeline_id=pipeline_id,
                component_type='PIPELINE',
                output={
                    'status': 'failed',
                    'error': {
                        'stage': stage,
                        'message': error,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                },
                metadata={
                    'type': 'pipeline_error',
                    'failed_at': datetime.utcnow().isoformat()
                }
            )

            # Notify about failure
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage': stage,
                        'error': error
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="control_point_manager"
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle stage error: {str(e)}")

    def _validate_pipeline_config(self, config: Dict[str, Any]) -> bool:
        """Validate pipeline configuration"""
        required_fields = ['name', 'stage_sequence']

        # Check required fields
        if not all(field in config for field in required_fields):
            return False

        # Validate stage sequence
        stages = config.get('stage_sequence', [])
        if not stages or not isinstance(stages, list):
            return False

        # All stages should be valid ProcessingStage values
        return all(stage in [s.value for s in ProcessingStage] for stage in stages)

    def _get_next_stage(self, current_stage: str, stage_sequence: list) -> Optional[str]:
        """Get next stage in sequence"""
        try:
            current_idx = stage_sequence.index(current_stage)
            if current_idx < len(stage_sequence) - 1:
                return stage_sequence[current_idx + 1]
            return None
        except ValueError:
            return None

    def _calculate_execution_time(self, start_time: Optional[str]) -> Optional[float]:
        """Calculate execution time in seconds"""
        if not start_time:
            return None

        try:
            start = datetime.fromisoformat(start_time)
            return (datetime.utcnow() - start).total_seconds()
        except ValueError:
            return None

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        try:
            await self.message_broker.unsubscribe_all(
                self.module_identifier.component_name
            )
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")