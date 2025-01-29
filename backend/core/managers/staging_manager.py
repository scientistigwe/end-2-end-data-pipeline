import logging
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
import aiofiles

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    StagingContext,
    StagingState,
    ManagerState
)
from .base.base_manager import BaseManager
from db.repository.staging_repository import StagingRepository

logger = logging.getLogger(__name__)


class StagingManager(BaseManager):
    """
    Staging Manager:
    Manages staging area and stored resources with advanced resource management
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            repository: StagingRepository,
            storage_path: Path,
            component_name: str = "staging_manager",
            domain_type: str = "staging"
    ):
        super().__init__(
            message_broker=message_broker,
            component_name=component_name,
            domain_type=domain_type
        )

        # Dependencies
        self.repository = repository
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Active processes and contexts
        self.active_processes: Dict[str, StagingContext] = {}
        self.process_timeouts: Dict[str, datetime] = {}

        # Resource limits
        self.staging_limits = {
            "max_file_size_mb": 1024,  # 1GB
            "max_storage_usage_gb": 10,  # 10GB
            "max_retention_hours": 24,
            "cleanup_interval_minutes": 30
        }

        # Initialize state
        self.state = ManagerState.INITIALIZING
        self._initialize_manager()

    def _initialize_manager(self) -> None:
        """Initialize staging manager components"""
        self._setup_domain_handlers()
        self._start_background_tasks()
        self.state = ManagerState.ACTIVE

    async def _setup_domain_handlers(self) -> None:
        """Setup staging-specific message handlers"""
        handlers = {
            # Service Layer Messages
            MessageType.STAGING_SERVICE_START: self._handle_service_start,
            MessageType.STAGING_SERVICE_STATUS: self._handle_service_status,
            MessageType.STAGING_SERVICE_COMPLETE: self._handle_service_complete,
            MessageType.STAGING_SERVICE_ERROR: self._handle_service_error,
            MessageType.STAGING_SERVICE_DECISION: self._handle_service_decision,

            # Handler Messages
            MessageType.STAGING_HANDLER_START: self._handle_handler_start,
            MessageType.STAGING_HANDLER_STORE: self._handle_handler_store,
            MessageType.STAGING_HANDLER_DELETE: self._handle_handler_delete,
            MessageType.STAGING_HANDLER_RETRIEVE: self._handle_handler_retrieve,
            MessageType.STAGING_HANDLER_DECISION: self._handle_handler_decision,
            MessageType.STAGING_HANDLER_UPDATE: self._handle_handler_update,
            MessageType.STAGING_HANDLER_COMPLETE: self._handle_handler_complete,
            MessageType.STAGING_HANDLER_STATUS: self._handle_handler_status,
            MessageType.STAGING_HANDLER_ERROR: self._handle_handler_error,

            # Data Operations
            MessageType.STAGING_STORE_REQUEST: self._handle_store_request,
            MessageType.STAGING_RETRIEVE_REQUEST: self._handle_retrieve_request,
            MessageType.STAGING_DELETE_REQUEST: self._handle_delete_request,

            # Access Control
            MessageType.STAGING_ACCESS_REQUEST: self._handle_access_request,
            MessageType.STAGING_ACCESS_GRANT: self._handle_access_grant,
            MessageType.STAGING_ACCESS_DENY: self._handle_access_deny,

            # Status and Metrics
            MessageType.STAGING_STATUS_REQUEST: self._handle_status_request,
            MessageType.STAGING_STATUS_RESPONSE: self._handle_status_response,
            MessageType.STAGING_METRICS_UPDATE: self._handle_metrics_update,

            # Cleanup Operations
            MessageType.STAGING_CLEANUP_REQUEST: self._handle_cleanup_request,
            MessageType.STAGING_CLEANUP_COMPLETE: self._handle_cleanup_complete
        }

        for message_type, handler in handlers.items():
            await self.register_message_handler(message_type, handler)

    def _start_background_tasks(self) -> None:
        """Start background monitoring tasks"""
        asyncio.create_task(self._monitor_storage_usage())
        asyncio.create_task(self._monitor_expired_resources())
        asyncio.create_task(self._monitor_process_timeouts())

    async def store_data(
            self,
            data: Any,
            metadata: Dict[str, Any],
            source_type: str
    ) -> Dict[str, Any]:
        """Store data in staging area"""
        try:
            # Validate storage limits
            await self._validate_storage_limits(data)

            # Generate storage reference
            storage_ref = f"{datetime.now().timestamp()}_{source_type}"
            storage_path = self.storage_path / storage_ref

            # Store data
            await self._store_data_by_type(storage_path, data, source_type)

            # Create repository record
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
            logger.error(f"Data storage failed: {str(e)}")
            raise

    async def _store_data_by_type(self, path: Path, data: Any, source_type: str) -> None:
        """Store data based on type"""
        try:
            if isinstance(data, bytes):
                await self._store_binary(path, data)
            elif isinstance(data, str):
                await self._store_text(path, data)
            else:
                raise ValueError(f"Unsupported data type for {source_type}")

        except Exception as e:
            logger.error(f"Data storage failed: {str(e)}")
            raise

    async def _validate_storage_limits(self, data: Any) -> None:
        """Validate storage limits before storing data"""
        try:
            # Check file size
            data_size_mb = len(data) / (1024 * 1024)
            if data_size_mb > self.staging_limits['max_file_size_mb']:
                raise ValueError(f"File size exceeds limit of {self.staging_limits['max_file_size_mb']}MB")

            # Check total storage usage
            current_usage_gb = await self._get_current_storage_usage_gb()
            if current_usage_gb > self.staging_limits['max_storage_usage_gb']:
                raise ValueError(f"Storage usage exceeds limit of {self.staging_limits['max_storage_usage_gb']}GB")

        except Exception as e:
            logger.error(f"Storage limit validation failed: {str(e)}")
            raise

    async def _get_current_storage_usage_gb(self) -> float:
        """Get current storage usage in GB"""
        try:
            total_size = 0
            for file_path in self.storage_path.glob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size / (1024 * 1024 * 1024)  # Convert to GB

        except Exception as e:
            logger.error(f"Storage usage calculation failed: {str(e)}")
            return 0.0

    async def _store_binary(self, path: Path, data: bytes) -> None:
        """Store binary data"""
        async with aiofiles.open(path, 'wb') as f:
            await f.write(data)

    async def _store_text(self, path: Path, data: str) -> None:
        """Store text data"""
        async with aiofiles.open(path, 'w') as f:
            await f.write(data)

    async def retrieve_data(
            self,
            reference: str,
            requester_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve data from staging area"""
        try:
            # Validate access
            if not await self._validate_access(reference, requester_id):
                return {'status': 'access_denied'}

            # Get resource details
            resource = await self.repository.get_by_id(reference)
            if not resource:
                return {'status': 'not_found'}

            # Check file existence
            storage_path = Path(resource.storage_location)
            if not storage_path.exists():
                return {'status': 'data_missing'}

            # Read data
            data = await self._read_data(storage_path, resource.resource_type)
            return {
                'status': 'success',
                'data': data,
                'metadata': resource.metadata
            }

        except Exception as e:
            logger.error(f"Data retrieval failed: {str(e)}")
            raise

    async def _read_data(self, path: Path, resource_type: str) -> Any:
        """Read stored data based on type"""
        mode = 'rb' if resource_type in ['file', 'binary'] else 'r'
        async with aiofiles.open(path, mode) as f:
            return await f.read()

    async def _validate_access(self, reference: str, requester: str) -> bool:
        """Validate access permissions"""
        try:
            resource = await self.repository.get_by_id(reference)
            if not resource:
                return False

            allowed_components = resource.metadata.get('allowed_components', [])
            return not allowed_components or requester in allowed_components

        except Exception as e:
            logger.error(f"Access validation failed: {str(e)}")
            return False

    async def _monitor_storage_usage(self) -> None:
        """Monitor storage usage and trigger cleanup if needed"""
        while self.state == ManagerState.ACTIVE:
            try:
                usage_gb = await self._get_current_storage_usage_gb()
                if usage_gb > self.staging_limits['max_storage_usage_gb'] * 0.9:  # 90% threshold
                    await self._trigger_cleanup()

                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                logger.error(f"Storage monitoring failed: {str(e)}")
                await asyncio.sleep(60)

    async def _monitor_expired_resources(self) -> None:
        """Monitor and cleanup expired resources"""
        while self.state == ManagerState.ACTIVE:
            try:
                cleanup_interval = self.staging_limits['cleanup_interval_minutes']
                await asyncio.sleep(cleanup_interval * 60)
                await self._cleanup_expired_resources()

            except Exception as e:
                logger.error(f"Expired resource monitoring failed: {str(e)}")
                await asyncio.sleep(300)

    async def _cleanup_expired_resources(self) -> None:
        """Clean up expired resources"""
        try:
            retention_hours = self.staging_limits['max_retention_hours']
            expiry_time = datetime.now() - timedelta(hours=retention_hours)

            # Get expired resources
            expired_ids = await self.repository.get_expired_resources(expiry_time)

            # Clean up each expired resource
            for resource_id in expired_ids:
                await self._delete_resource(resource_id)

        except Exception as e:
            logger.error(f"Resource cleanup failed: {str(e)}")

    async def _delete_resource(self, resource_id: str) -> None:
        """Delete a resource and its file"""
        try:
            resource = await self.repository.get_by_id(resource_id)
            if resource and resource.storage_location:
                file_path = Path(resource.storage_location)
                if file_path.exists():
                    file_path.unlink()

            await self.repository.delete_resource(resource_id)

        except Exception as e:
            logger.error(f"Resource deletion failed: {str(e)}")

    async def _trigger_cleanup(self) -> None:
        """Trigger cleanup process"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_CLEANUP_REQUEST,
                    content={
                        'reason': 'storage_limit_exceeded',
                        'current_usage_gb': await self._get_current_storage_usage_gb(),
                        'limit_gb': self.staging_limits['max_storage_usage_gb']
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="staging_service",
                        domain_type="staging"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Cleanup trigger failed: {str(e)}")

    async def _monitor_process_timeouts(self) -> None:
        """Monitor and handle timed-out staging processes"""
        while self.state == ManagerState.ACTIVE:
            try:
                current_time = datetime.now()
                timeout_ids = [
                    process_id for process_id, timeout_time in self.process_timeouts.items()
                    if current_time > timeout_time
                ]

                for process_id in timeout_ids:
                    # Handle timed-out process
                    await self._handle_process_timeout(process_id)

                # Sleep for a reasonable interval before next check
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Process timeout monitoring failed: {str(e)}")
                await asyncio.sleep(60)

    async def _handle_process_timeout(self, process_id: str) -> None:
        """Handle a timed-out staging process"""
        try:
            # Remove from timeouts dictionary
            if process_id in self.process_timeouts:
                del self.process_timeouts[process_id]

            # Remove from active processes
            if process_id in self.active_processes:
                context = self.active_processes.pop(process_id)

                # Publish a timeout message
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.STAGING_SERVICE_ERROR,
                        content={
                            'process_id': process_id,
                            'error_type': 'timeout',
                            'error_message': 'Staging process exceeded maximum time limit'
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component="staging_service",
                            domain_type="staging"
                        )
                    )
                )

                # Optional: Clean up any associated resources
                if context.storage_reference:
                    await self._delete_resource(context.storage_reference)

        except Exception as e:
            logger.error(f"Process timeout handling failed for {process_id}: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup staging manager resources"""
        try:
            self.state = ManagerState.SHUTDOWN

            # Clean up all active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self._cleanup_process(pipeline_id)

            # Clear storage directory
            if self.storage_path.exists():
                for file in self.storage_path.iterdir():
                    try:
                        file.unlink()
                    except Exception as e:
                        logger.error(f"Failed to delete file {file}: {str(e)}")

            # Clear data structures
            self.active_processes.clear()
            self.process_timeouts.clear()

            # Cleanup base manager resources
            await super().cleanup()

        except Exception as e:
            logger.error(f"Staging manager cleanup failed: {str(e)}")
            raise