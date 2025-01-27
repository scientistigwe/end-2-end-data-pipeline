# backend/core/managers/staging_manager.py

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from pathlib import Path

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType, ProcessingMessage, ComponentType, ModuleIdentifier,
    MessageMetadata, ProcessingStage, ProcessingStatus, StagingState
)
from db.repository.staging_repository import StagingRepository

logger = logging.getLogger(__name__)


class StagingManager:
    """
    Staging Manager:
    1. Direct interface for data sources and frontend
    2. Pub/sub for core component communications
    3. Manages staging area and stored resources
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            repository: StagingRepository,
            storage_path: Path
    ):
        self.message_broker = message_broker
        self.repository = repository
        self.storage_path = storage_path

        # Ensure storage exists
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Module identification for pub/sub
        self.module_identifier = ModuleIdentifier(
            component_name="staging_manager",
            component_type=ComponentType.STAGING_MANAGER,
            department="staging",
            role="manager"
        )

        # Active staging tracking
        self.active_processes: Dict[str, Dict[str, Any]] = {}

        # Setup message handlers
        self._setup_message_handlers()

    # -------------------------------------------------------------------------
    # DIRECT INTERFACE FOR DATA SOURCES AND FRONTEND
    # -------------------------------------------------------------------------

    async def store_data(
            self,
            data: Any,
            metadata: Dict[str, Any],
            source_type: str
    ) -> Dict[str, Any]:
        """Direct store interface for data sources"""
        try:
            # Generate storage path
            storage_ref = f"{datetime.now().timestamp()}_{source_type}"
            storage_path = self.storage_path / storage_ref

            # Store physical data
            if isinstance(data, bytes):
                await self._store_binary(storage_path, data)
            else:
                await self._store_text(storage_path, data)

            # Store in repository
            stored_resource = await self.repository.store_staged_resource(
                pipeline_id=metadata.get('pipeline_id'),
                data={
                    'storage_location': str(storage_path),
                    'resource_type': source_type,
                    'size_bytes': storage_path.stat().st_size,
                    **metadata
                }
            )

            return {
                'status': 'success',
                'staged_id': str(stored_resource.id),
                'reference': storage_ref
            }

        except Exception as e:
            logger.error(f"Direct store failed: {str(e)}")
            raise

    async def get_data(
            self,
            reference: str,
            requester_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Direct retrieval interface"""
        try:
            # Get resource info
            resource = await self.repository.get_by_id(reference)
            if not resource:
                return {'status': 'not_found'}

            # Check access if requester specified
            if requester_id and not await self._validate_access(reference, requester_id):
                return {'status': 'access_denied'}

            # Read data
            storage_path = Path(resource.storage_location)
            if not storage_path.exists():
                return {'status': 'data_missing'}

            data = await self._read_data(storage_path, resource.resource_type)

            return {
                'status': 'success',
                'data': data,
                'metadata': resource.metadata
            }

        except Exception as e:
            logger.error(f"Direct retrieval failed: {str(e)}")
            raise

    async def get_status(
            self,
            reference: str
    ) -> Dict[str, Any]:
        """Get staging status"""
        try:
            resource = await self.repository.get_by_id(reference)
            if not resource:
                return {'status': 'not_found'}

            return {
                'status': resource.status,
                'staged_at': resource.created_at.isoformat(),
                'resource_type': resource.resource_type,
                'metadata': resource.metadata
            }

        except Exception as e:
            logger.error(f"Status check failed: {str(e)}")
            raise

    # -------------------------------------------------------------------------
    # CORE COMPONENT PUB/SUB INTERFACE
    # -------------------------------------------------------------------------

    async def _setup_message_handlers(self):
        """Setup pub/sub message handlers"""
        handlers = {
            # Component Outputs
            MessageType.QUALITY_OUTPUT_STORE: self._handle_quality_output,
            MessageType.INSIGHT_OUTPUT_STORE: self._handle_insight_output,
            MessageType.DECISION_OUTPUT_STORE: self._handle_decision_output,
            MessageType.RECOMMENDATION_OUTPUT_STORE: self._handle_recommendation_output,

            # Access Control
            MessageType.STAGING_ACCESS_REQUEST: self._handle_access_request,

            # Process Control
            MessageType.STAGING_CLEANUP_REQUEST: self._handle_cleanup_request,
            MessageType.STAGING_STATUS_REQUEST: self._handle_status_request
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_quality_output(self, message: ProcessingMessage):
        """Handle quality analysis output storage"""
        try:
            # Store output
            result = await self.repository.store_staged_resource(
                pipeline_id=message.content['pipeline_id'],
                data={
                    'resource_type': 'quality_output',
                    'stage_key': 'quality_analysis',
                    'data': message.content['output'],
                    **message.content['metadata']
                }
            )

            # Notify storage complete
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_OUTPUT_STORED,
                    content={
                        'component': 'quality',
                        'reference': str(result.id),
                        'pipeline_id': message.content['pipeline_id']
                    },
                    source_identifier=self.module_identifier,
                    target_identifier=message.source_identifier
                )
            )

        except Exception as e:
            logger.error(f"Quality output storage failed: {str(e)}")
            await self._publish_error(message, str(e))

    async def _handle_insight_output(self, message: ProcessingMessage):
        """Handle insight analysis output storage"""
        try:
            # Store output
            result = await self.repository.store_staged_resource(
                pipeline_id=message.content['pipeline_id'],
                data={
                    'resource_type': 'insight_output',
                    'stage_key': 'insight_generation',
                    'data': message.content['output'],
                    **message.content['metadata']
                }
            )

            # Notify storage complete
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_OUTPUT_STORED,
                    content={
                        'component': 'insight',
                        'reference': str(result.id),
                        'pipeline_id': message.content['pipeline_id']
                    },
                    source_identifier=self.module_identifier,
                    target_identifier=message.source_identifier
                )
            )

        except Exception as e:
            logger.error(f"Insight output storage failed: {str(e)}")
            await self._publish_error(message, str(e))

    async def _handle_decision_output(self, message: ProcessingMessage):
        """Handle decision making output storage"""
        try:
            # Store output
            result = await self.repository.store_staged_resource(
                pipeline_id=message.content['pipeline_id'],
                data={
                    'resource_type': 'decision_output',
                    'stage_key': 'decision_making',
                    'data': message.content['output'],
                    **message.content['metadata']
                }
            )

            # Notify storage complete
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_OUTPUT_STORED,
                    content={
                        'component': 'decision',
                        'reference': str(result.id),
                        'pipeline_id': message.content['pipeline_id']
                    },
                    source_identifier=self.module_identifier,
                    target_identifier=message.source_identifier
                )
            )

        except Exception as e:
            logger.error(f"Decision output storage failed: {str(e)}")
            await self._publish_error(message, str(e))

    async def _handle_recommendation_output(self, message: ProcessingMessage):
        """Handle recommendation output storage"""
        try:
            # Store output
            result = await self.repository.store_staged_resource(
                pipeline_id=message.content['pipeline_id'],
                data={
                    'resource_type': 'recommendation_output',
                    'stage_key': 'recommendation_generation',
                    'data': message.content['output'],
                    **message.content['metadata']
                }
            )

            # Notify storage complete
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_OUTPUT_STORED,
                    content={
                        'component': 'recommendation',
                        'reference': str(result.id),
                        'pipeline_id': message.content['pipeline_id']
                    },
                    source_identifier=self.module_identifier,
                    target_identifier=message.source_identifier
                )
            )

        except Exception as e:
            logger.error(f"Recommendation output storage failed: {str(e)}")
            await self._publish_error(message, str(e))

    async def _handle_status_request(self, message: ProcessingMessage):
        """Handle status request from core components"""
        try:
            reference = message.content.get('reference')
            pipeline_id = message.content.get('pipeline_id')

            # Get resource/pipeline outputs
            if reference:
                status = await self.get_status(reference)
            elif pipeline_id:
                resources = await self.repository.get_pipeline_resources(
                    pipeline_id,
                    resource_type=message.content.get('resource_type')
                )
                status = {
                    'pipeline_id': pipeline_id,
                    'resources': [
                        {
                            'id': str(r.id),
                            'type': r.resource_type,
                            'status': r.status,
                            'created_at': r.created_at.isoformat()
                        }
                        for r in resources
                    ]
                }
            else:
                raise ValueError("Either reference or pipeline_id required")

            # Send status response
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_STATUS_RESPONSE,
                    content=status,
                    source_identifier=self.module_identifier,
                    target_identifier=message.source_identifier
                )
            )

        except Exception as e:
            logger.error(f"Status request failed: {str(e)}")
            await self._publish_error(message, str(e))

    async def _handle_access_request(self, message: ProcessingMessage):
        """Handle component data access requests"""
        try:
            reference = message.content['reference']
            requester = message.source_identifier.component_name

            # Validate access
            access_granted = await self._validate_access(reference, requester)

            event_type = MessageType.STAGING_ACCESS_GRANT if access_granted \
                else MessageType.STAGING_ACCESS_DENY

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=event_type,
                    content={
                        'reference': reference,
                        'granted': access_granted
                    },
                    source_identifier=self.module_identifier,
                    target_identifier=message.source_identifier
                )
            )

        except Exception as e:
            logger.error(f"Access request failed: {str(e)}")
            await self._publish_error(message, str(e))

    async def _handle_cleanup_request(self, message: ProcessingMessage):
        """Handle cleanup requests"""
        try:
            # Run cleanup
            expired_ids = await self.repository.cleanup_expired_resources()

            # Clean storage
            for resource_id in expired_ids:
                resource = await self.repository.get_by_id(resource_id)
                if resource and resource.storage_location:
                    storage_path = Path(resource.storage_location)
                    if storage_path.exists():
                        storage_path.unlink()

            # Notify cleanup complete
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_CLEANUP_COMPLETE,
                    content={
                        'cleaned_resources': len(expired_ids),
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    source_identifier=self.module_identifier,
                    target_identifier=message.source_identifier
                )
            )

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            await self._publish_error(message, str(e))

    # -------------------------------------------------------------------------
    # UTILITY METHODS
    # -------------------------------------------------------------------------

    async def _store_binary(self, path: Path, data: bytes) -> None:
        """Store binary data"""
        async with aiofiles.open(path, 'wb') as f:
            await f.write(data)

    async def _store_text(self, path: Path, data: str) -> None:
        """Store text data"""
        async with aiofiles.open(path, 'w') as f:
            await f.write(data)

    async def _read_data(self, path: Path, resource_type: str) -> Any:
        """Read stored data"""
        mode = 'rb' if resource_type in ['file', 'binary'] else 'r'
        async with aiofiles.open(path, mode) as f:
            return await f.read()

    async def _validate_access(
            self,
            reference: str,
            requester: str
    ) -> bool:
        """Validate access to resource"""
        try:
            resource = await self.repository.get_by_id(reference)
            if not resource:
                return False

            # Add your access control logic here
            # For now, basic component-type checking
            allowed_components = resource.metadata.get('allowed_components', [])
            return not allowed_components or requester in allowed_components

        except Exception as e:
            logger.error(f"Access validation failed: {str(e)}")
            return False

    async def _publish_error(
            self,
            original_message: ProcessingMessage,
            error: str
    ) -> None:
        """Publish error message"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.STAGING_ERROR,
                content={
                    'error': error,
                    'original_request': original_message.content
                },
                source_identifier=self.module_identifier,
                target_identifier=original_message.source_identifier
            )
        )