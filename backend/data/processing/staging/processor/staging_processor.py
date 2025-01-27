# backend/core/processors/staging_processor.py

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata,
    ProcessingStage,
    ProcessingStatus,
    ReportSectionType
)
from core.modules.staging_module import StagingDataModule
from db.repository.staging_repository import StagingRepository
from db.models.staging.base_staging_model import BaseStagedOutput
from db.models.staging.staging_control_model import StagingControlPoint
from db.models.staging.staging_history_model import StagingProcessingHistory

logger = logging.getLogger(__name__)


class StagingProcessor:
    """
    Staging Processor: Coordinates direct resource interactions

    Responsibilities:
    - Direct interaction with staging modules
    - Coordinate with database repositories
    - Handle resource-level operations
    - Manage data processing workflows
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_module: StagingDataModule,
            staging_repository: StagingRepository
    ):
        # Core dependencies
        self.message_broker = message_broker
        self.staging_module = staging_module
        self.staging_repository = staging_repository

        # Processor identification
        self.module_identifier = ModuleIdentifier(
            component_name="staging_processor",
            component_type=ComponentType.STAGING_PROCESSOR,
            department="staging",
            role="processor"
        )

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Configure message handlers for staging processor"""
        handlers = {
            # Processing Requests
            MessageType.STAGING_PROCESSOR_START: self._handle_processor_start,
            MessageType.STAGING_PROCESSOR_STORE: self._handle_store_request,
            MessageType.STAGING_PROCESSOR_RETRIEVE: self._handle_retrieve_request,
            MessageType.STAGING_PROCESSOR_DELETE: self._handle_delete_request,
            MessageType.STAGING_PROCESSOR_UPDATE: self._handle_update_request,
            MessageType.STAGING_PROCESSOR_DECISION: self._handle_decision_request,

            # Resource Management
            MessageType.STAGING_RESOURCE_VALIDATE: self._handle_resource_validation,
            MessageType.STAGING_RESOURCE_CLEANUP: self._handle_resource_cleanup,

            # Error Handling
            MessageType.STAGING_ERROR: self._handle_error
        }

        # Subscribe to all processor message types
        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=f"staging.{message_type.value}.*",
                callback=handler
            )

    async def _handle_processor_start(self, message: ProcessingMessage) -> None:
        """
        Initialize staging processing workflow
        Direct interaction with staging module and repository
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            config = message.content.get('config', {})
            component_type = message.content.get('component_type', ComponentType.STAGING_SERVICE)

            # Prepare staging resource
            staged_output = await self._prepare_staged_output(
                pipeline_id=pipeline_id,
                component_type=component_type,
                config=config
            )

            # Notify handler of processing start
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_HANDLER_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage_id': str(staged_output.id),
                        'status': ProcessingStatus.INITIALIZING.value
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_store_request(self, message: ProcessingMessage) -> None:
        """
        Handle data storage requests
        Direct interaction with staging module and repository
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            stage_id = message.content.get('stage_id', str(uuid.uuid4()))
            data = message.content.get('data')
            metadata = message.content.get('metadata', {})
            component_type = message.content.get('component_type', ComponentType.STAGING_SERVICE)

            # Store data in staging module
            storage_path = await self.staging_module.store_data(
                stage_id=stage_id,
                data=data,
                metadata=metadata
            )

            # Update staged output in repository
            staged_output = await self.staging_repository.update_staged_output(
                stage_id=stage_id,
                data={
                    'storage_path': str(storage_path),
                    'data_size': len(str(data)),
                    'base_stage_metadata': metadata,
                    'status': ProcessingStatus.STORED,
                    'component_type': component_type,
                    'output_type': ReportSectionType.DATA
                }
            )

            # Create processing history entry
            await self.staging_repository.create_processing_history(
                stage_id=stage_id,
                event_type='store',
                status=ProcessingStatus.STORED,
                details={
                    'storage_path': str(storage_path),
                    'size': len(str(data))
                }
            )

            # Notify handler of successful storage
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_HANDLER_COMPLETE,
                    content={
                        'stage_id': stage_id,
                        'storage_path': str(storage_path),
                        'status': ProcessingStatus.STORED.value
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_retrieve_request(self, message: ProcessingMessage) -> None:
        """
        Handle data retrieval requests
        Direct interaction with staging module and repository
        """
        try:
            stage_id = message.content.get('stage_id')

            # Validate access (can be expanded with more complex logic)
            if not await self._validate_access(stage_id):
                raise PermissionError("Access denied")

            # Retrieve data from staging module
            data = await self.staging_module.retrieve_data(stage_id)

            # Fetch staged output metadata
            staged_output = await self.staging_repository.get_staged_output(stage_id)

            # Create processing history entry
            await self.staging_repository.create_processing_history(
                stage_id=stage_id,
                event_type='retrieve',
                status=ProcessingStatus.RETRIEVED,
                details={'retrieval_time': datetime.utcnow()}
            )

            # Notify handler of successful retrieval
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_HANDLER_COMPLETE,
                    content={
                        'stage_id': stage_id,
                        'data': data,
                        'metadata': staged_output.base_stage_metadata,
                        'status': ProcessingStatus.RETRIEVED.value
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_delete_request(self, message: ProcessingMessage) -> None:
        """
        Handle deletion requests
        Direct interaction with staging module and repository
        """
        try:
            stage_id = message.content.get('stage_id')

            # Delete from staging module
            await self.staging_module.delete_data(stage_id)

            # Update staged output status
            await self.staging_repository.update_staged_output(
                stage_id=stage_id,
                data={
                    'status': ProcessingStatus.DELETED,
                    'is_temporary': True
                }
            )

            # Create processing history entry
            await self.staging_repository.create_processing_history(
                stage_id=stage_id,
                event_type='delete',
                status=ProcessingStatus.DELETED,
                details={'deletion_time': datetime.utcnow()}
            )

            # Notify handler of deletion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_HANDLER_COMPLETE,
                    content={
                        'stage_id': stage_id,
                        'status': ProcessingStatus.DELETED.value
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _prepare_staged_output(
            self,
            pipeline_id: str,
            component_type: ComponentType,
            config: Dict[str, Any]
    ) -> BaseStagedOutput:
        """
        Prepare staged output with initial configuration
        """
        # Create initial staged output entry
        staged_output = await self.staging_repository.create_staged_output(
            pipeline_id=pipeline_id,
            data={
                'component_type': component_type,
                'base_stage_metadata': config,
                'status': ProcessingStatus.INITIALIZING,
                'expires_at': datetime.utcnow() + timedelta(hours=24)
            }
        )

        # Create initial processing history
        await self.staging_repository.create_processing_history(
            stage_id=str(staged_output.id),
            event_type='initialization',
            status=ProcessingStatus.INITIALIZING,
            details=config
        )

        return staged_output

    # Remaining methods (error handling, validation, etc.) remain similar to previous implementation

    async def cleanup(self) -> None:
        """
        Gracefully clean up processor resources
        """
        try:
            await self.message_broker.unsubscribe_all(
                self.module_identifier.component_name
            )
        except Exception as e:
            logger.error(f"Staging processor cleanup failed: {str(e)}")