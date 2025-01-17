import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID
import uuid

from backend.core.orchestration.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ProcessingStage,
    ComponentType,
    ModuleIdentifier
)
from backend.core.channel_handlers.staging_handler import StagingHandler
from backend.db.repository.staging_repository import StagingRepository
from backend.core.orchestration.pipeline_manager_helper import PipelineStateManager

logger = logging.getLogger(__name__)


class StagingManager(BaseManager):
    """
    Manages staging area for pipeline resources

    Responsibilities:
    - Resource lifecycle management
    - Control point integration
    - State tracking
    - Cleanup and maintenance
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            repository: Optional[StagingRepository] = None,
            staging_handler: Optional[StagingHandler] = None,
            state_manager: Optional[PipelineStateManager] = None,
            control_point_manager: Optional[Any] = None,
            component_name: str = "StagingManager"
    ):
        """Initialize staging manager with comprehensive components"""
        # Initialize base manager
        super().__init__(
            message_broker=message_broker,
            component_name=component_name
        )

        # Dependency injection
        self.repository = repository
        self.staging_handler = staging_handler or StagingHandler(
            message_broker,
            control_point_manager=control_point_manager
        )
        self.state_manager = state_manager or PipelineStateManager()
        self.control_point_manager = control_point_manager

        # Flag to track setup status
        self._setup_complete = False
        self._setup_task = None

    async def initialize(self) -> None:
        """Initialize the staging manager and set up handlers"""
        if not self._setup_complete:
            await self._setup_event_handlers()
            self._setup_complete = True

    async def _setup_event_handlers(self) -> None:
        """Setup message handlers for staging-related events"""
        try:
            # Subscribe to staging handler message patterns
            await self.message_broker.subscribe(
                component=self.module_id,
                pattern="staging_handler.*",
                callback=self._handle_handler_messages
            )
            logger.info("StagingManager event handlers setup complete")
            self._setup_complete = True

        except Exception as e:
            logger.error(f"Failed to setup event handlers: {str(e)}")
            await self._handle_error(None, e)
            raise

    async def start(self) -> None:
        """Start the staging manager"""
        if not self._setup_complete:
            await self.initialize()

    async def stop(self) -> None:
        """Stop the staging manager and cleanup resources"""
        try:
            self._setup_complete = False
            # Additional cleanup if needed
            logger.info("StagingManager stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping StagingManager: {str(e)}")

    async def _handle_handler_messages(self, message: ProcessingMessage) -> None:
        """Central routing for messages from staging handler"""
        try:
            if message.message_type == MessageType.STAGE_STATUS_UPDATE:
                await self.handle_staging_status_update(message)
            elif message.message_type == MessageType.STAGE_COMPLETE:
                await self.handle_staging_complete(message)
            elif message.message_type == MessageType.STAGE_ERROR:
                await self.handle_staging_error(message)
            elif message.message_type == MessageType.CONTROL_POINT_DECISION:
                await self.handle_control_point_decision(message)
            elif message.message_type == MessageType.RESOURCE_MODIFIED:
                await self.handle_resource_modification(message)

        except Exception as e:
            logger.error(f"Error routing handler message: {str(e)}")
            await self._handle_error(
                message.content.get('pipeline_id'),
                e
            )

    async def stage_resource(
            self,
            pipeline_id: str,
            data: Any,
            resource_type: str,
            requires_approval: bool = True,
            metadata: Optional[Dict[str, Any]] = None,
            validation_rules: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """Stage a resource for processing"""
        try:
            # Generate resource ID
            resource_id = UUID(uuid.uuid4())

            # Create initial record in repository
            if self.repository:
                stage_key = f"{resource_type}_{datetime.utcnow().timestamp()}"
                resource = await self.repository.create_staged_resource({
                    'pipeline_id': pipeline_id,
                    'resource_id': resource_id,
                    'stage_key': stage_key,
                    'resource_type': resource_type,
                    'requires_approval': requires_approval,
                    'metadata': metadata or {},
                    'status': 'pending'
                })

            # Create staging request message
            staging_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="staging_handler",
                    component_type=ComponentType.HANDLER
                ),
                message_type=MessageType.STAGE_STORE,
                content={
                    'pipeline_id': pipeline_id,
                    'resource_id': resource_id,
                    'resource_data': {
                        'data': data,
                        'type': resource_type,
                        'metadata': metadata or {}
                    },
                    'requires_approval': requires_approval,
                    'validation_rules': validation_rules
                }
            )

            # Send staging request
            await self.message_broker.publish(staging_message)

            return resource_id

        except Exception as e:
            logger.error(f"Failed to stage resource: {str(e)}")
            await self._handle_error(pipeline_id, e)
            raise

    async def handle_staging_status_update(self, message: ProcessingMessage) -> None:
        """Handle status updates from staging handler"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            resource_id = message.content.get('resource_id')
            status = message.content.get('status')
            progress = message.content.get('progress', 0)

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus(status)
                pipeline_state.current_progress = progress

            # Update repository if available
            if self.repository:
                await self.repository.update_resource_status(
                    UUID(resource_id),
                    status=status,
                    metadata_updates={'progress': progress}
                )

            # Record event
            if self.repository:
                await self.repository.record_event(
                    UUID(resource_id),
                    {
                        'event_type': 'status_update',
                        'details': {
                            'status': status,
                            'progress': progress
                        },
                        'pipeline_id': pipeline_id
                    }
                )

        except Exception as e:
            logger.error(f"Error handling staging status update: {str(e)}")
            await self._handle_error(pipeline_id, e)


    async def handle_staging_complete(self, message: ProcessingMessage) -> None:
        """Handle staging completion"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            resource_id = message.content.get('resource_id')
            results = message.content.get('results', {})

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus.COMPLETED
                pipeline_state.current_stage = ProcessingStage.PROCESSING
                pipeline_state.current_progress = 100.0

            # Update repository if available
            if self.repository:
                await self.repository.update_resource_status(
                    UUID(resource_id),
                    status='completed',
                    metadata_updates={'results': results}
                )

            # Notify pipeline manager about stage completion
            completion_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="pipeline_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.STAGE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'resource_id': resource_id,
                    'stage': ProcessingStage.STAGING.value,
                    'results': results
                }
            )
            await self.message_broker.publish(completion_message)

        except Exception as e:
            logger.error(f"Error handling staging completion: {str(e)}")
            await self._handle_error(pipeline_id, e)


    async def handle_staging_error(self, message: ProcessingMessage) -> None:
        """Handle staging errors"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            resource_id = message.content.get('resource_id')
            error = message.content.get('error')

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus.FAILED
                pipeline_state.add_error(error)

            # Update repository if available
            if self.repository:
                await self.repository.update_resource_status(
                    UUID(resource_id),
                    status='error',
                    metadata_updates={'error': error}
                )

                # Record error event
                await self.repository.record_event(
                    UUID(resource_id),
                    {
                        'event_type': 'error',
                        'details': {'error': error},
                        'pipeline_id': pipeline_id
                    }
                )

            # Notify pipeline manager about stage failure
            error_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="pipeline_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.STAGE_FAILED,
                content={
                    'pipeline_id': pipeline_id,
                    'resource_id': resource_id,
                    'stage': ProcessingStage.STAGING.value,
                    'error': error
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Error handling staging error: {str(e)}")


    async def handle_control_point_decision(self, message: ProcessingMessage) -> None:
        """Handle control point decision"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            resource_id = message.content.get('resource_id')
            decision = message.content.get('decision')
            decision_maker = message.content.get('decision_maker')

            # Record decision in repository
            if self.repository:
                await self.repository.record_decision(
                    UUID(resource_id),
                    {
                        'decision_type': decision,
                        'decision_maker': decision_maker,
                        'metadata': message.content.get('metadata', {}),
                        'reason': message.content.get('reason')
                    }
                )

            # Forward decision to handler
            decision_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="staging_handler",
                    component_type=ComponentType.HANDLER
                ),
                message_type=MessageType.CONTROL_POINT_DECISION,
                content=message.content
            )
            await self.message_broker.publish(decision_message)

        except Exception as e:
            logger.error(f"Error handling control point decision: {str(e)}")
            await self._handle_error(pipeline_id, e)


    async def handle_resource_modification(self, message: ProcessingMessage) -> None:
        """Handle resource modification"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            resource_id = message.content.get('resource_id')
            modifications = message.content.get('modifications', {})

            # Record modification in repository
            if self.repository:
                await self.repository.create_modification(
                    UUID(resource_id),
                    {
                        'modification_type': 'user_requested',
                        'changes': modifications,
                        'metadata': message.content.get('metadata', {})
                    }
                )

            # Create new control point for verification if needed
            if self.control_point_manager:
                resource = await self.repository.get_resource(UUID(resource_id))
                if resource and resource.requires_approval:
                    await self.control_point_manager.create_control_point(
                        pipeline_id=pipeline_id,
                        stage=ProcessingStage.STAGING,
                        data={
                            'resource_id': resource_id,
                            'modifications': modifications,
                            'metadata': resource.metadata
                        },
                        options=['approve', 'reject', 'modify']
                    )

        except Exception as e:
            logger.error(f"Error handling resource modification: {str(e)}")
            await self._handle_error(pipeline_id, e)


    async def _handle_error(
            self,
            pipeline_id: Optional[str],
            error: Exception
    ) -> None:
        """Comprehensive error handling"""
        try:
            # Log error
            logger.error(f"Staging manager error: {str(error)}")

            # Update pipeline state
            if pipeline_id:
                pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
                if pipeline_state:
                    pipeline_state.status = ProcessingStatus.FAILED
                    pipeline_state.add_error(str(error))

            # Publish error message
            error_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="pipeline_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.STAGING.value,
                    'error': str(error)
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Critical error in staging manager error handling: {str(e)}")


    async def cleanup_expired_resources(self) -> None:
        """Clean up expired resources"""
        try:
            if self.repository:
                expired_ids = await self.repository.cleanup_expired_resources()
                for resource_id in expired_ids:
                    await self.staging_handler.cleanup_pipeline_resources(str(resource_id))

        except Exception as e:
            logger.error(f"Error cleaning up expired resources: {str(e)}")


    async def get_resource_status(self, resource_id: UUID) -> Optional[Dict[str, Any]]:
        """Get comprehensive resource status"""
        try:
            if self.repository:
                resource = await self.repository.get_resource(resource_id)
                if resource:
                    # Get related data
                    decisions = await self.repository.get_resource_decisions(resource_id)
                    modifications = await self.repository.get_resource_modifications(resource_id)
                    events = await self.repository.get_resource_events(resource_id)

                    return {
                        'resource_id': str(resource_id),
                        'status': resource.status,
                        'type': resource.resource_type,
                        'metadata': resource.metadata,
                        'requires_approval': resource.requires_approval,
                        'creation_time': resource.created_at.isoformat(),
                        'last_update': resource.updated_at.isoformat(),
                        'expiry_time': resource.expires_at.isoformat() if resource.expires_at else None,
                        'decisions': [d.to_dict() for d in decisions],
                        'modifications': [m.to_dict() for m in modifications],
                        'events': [e.to_dict() for e in events]
                    }
            return None

        except Exception as e:
            logger.error(f"Error retrieving resource status: {str(e)}")
            return None


    async def get_pipeline_resources(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """Get all resources for a pipeline"""
        try:
            if self.repository:
                resources = await self.repository.get_pipeline_resources(UUID(pipeline_id))
                return [
                    {
                        'resource_id': str(r.resource_id),
                        'type': r.resource_type,
                        'status': r.status,
                        'metadata': r.metadata,
                        'created_at': r.created_at.isoformat()
                    }
                    for r in resources
                ]
            return []

        except Exception as e:
            logger.error(f"Error retrieving pipeline resources: {str(e)}")
            return []

    @classmethod
    async def create(
            cls,
            message_broker: Optional[MessageBroker] = None,
            repository: Optional[StagingRepository] = None,
            control_point_manager: Optional[Any] = None
    ) -> 'StagingManager':
        """Factory method to create and initialize StagingManager"""
        # Import global message broker if not provided
        if message_broker is None:
            from backend.core.messaging.broker import message_broker

        manager = cls(
            message_broker=message_broker,
            repository=repository,
            control_point_manager=control_point_manager
        )

        # Initialize the manager
        await manager.initialize()
        return manager
