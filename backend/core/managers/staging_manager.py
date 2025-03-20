import logging
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
import aiofiles
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    StagingContext,
    StagingState,
    ManagerState,
    ComponentType
)
from .base.base_manager import BaseManager
from db.repository.staging import StagingRepository
from db.models.staging.processing import (
    StagedAnalyticsOutput,
    StagedInsightOutput,
    StagedDecisionOutput,
    StagedMonitoringOutput,
    StagedQualityOutput,
    StagedRecommendationOutput
)

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
        super().__init__(message_broker, component_name, domain_type)

        # Dependencies
        self.repository = repository
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Resource limits and configuration
        self.staging_limits = {
            "max_file_size_mb": 1024,
            "max_storage_usage_gb": 10,
            "max_retention_hours": 24,
            "cleanup_interval_minutes": 30,
            "max_concurrent_operations": 10,
            "backpressure_threshold": 0.8  # 80% of max storage
        }

        # Resource tracking
        self.active_operations = 0
        self.storage_metrics = StagingMetrics()
        self.resource_locks = {}
        self.access_control = {}

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
            MessageType.STAGING_ACCESS_GRANTED: self._handle_access_grant,
            MessageType.STAGING_ACCESS_DENIED: self._handle_access_deny,

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

    async def start(self) -> None:
        """Initialize and start staging manager"""
        try:
            await super().start()  # Call base start first

            # Start staging-specific monitoring
            self._start_background_task(
                self._monitor_storage_usage(),
                "storage_usage_monitor"
            )
            self._start_background_task(
                self._monitor_expired_resources(),
                "expired_resources_monitor"
            )
            self._start_background_task(
                self._monitor_active_operations(),
                "active_operations_monitor"
            )

            # Initialize metrics
            await self._initialize_metrics()

        except Exception as e:
            self.logger.error(f"Staging manager start failed: {str(e)}")
            raise

    async def _initialize_metrics(self) -> None:
        """Initialize staging metrics"""
        try:
            # Get current storage usage
            usage_gb = await self._get_current_storage_usage_gb()
            self.storage_metrics.current_storage_usage = usage_gb
            self.storage_metrics.max_storage_usage = max(
                usage_gb,
                self.storage_metrics.max_storage_usage
            )

            # Get active operations count
            self.storage_metrics.active_stages = len(self.active_processes)

            # Publish initial metrics
            await self._publish_metrics_update()

        except Exception as e:
            self.logger.error(f"Failed to initialize metrics: {str(e)}")

    async def _monitor_active_operations(self) -> None:
        """Monitor active operations and enforce limits"""
        while not self._shutting_down:
            try:
                if self.active_operations >= self.staging_limits['max_concurrent_operations']:
                    await self._handle_backpressure()
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Active operations monitoring failed: {str(e)}")
                if not self._shutting_down:
                    await asyncio.sleep(5)

    async def _handle_backpressure(self) -> None:
        """Handle backpressure when system is overloaded"""
        try:
            # Publish backpressure notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_METRICS_UPDATE,
                    content={
                        'type': 'backpressure',
                        'active_operations': self.active_operations,
                        'max_operations': self.staging_limits['max_concurrent_operations'],
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component='system_monitor',
                        domain_type='staging'
                    )
                )
            )

            # Wait for operations to complete
            await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"Backpressure handling failed: {str(e)}")

    async def _handle_store_request(self, message: ProcessingMessage) -> None:
        """Handle store request with improved resource management"""
        try:
            # Check resource limits
            if not await self._check_resource_limits():
                await self._send_error_response(
                    message,
                    "Resource limits exceeded",
                    MessageType.STAGING_HANDLER_ERROR
                )
                return

            # Extract request details
            pipeline_id = message.content.get('pipeline_id')
            data = message.content.get('data')
            metadata = message.content.get('metadata', {})

            # Create staging context
            context = StagingContext(
                pipeline_id=pipeline_id,
                state=StagingState.STORING,
                metadata=metadata
            )

            # Store data
            try:
                self.active_operations += 1
                await self._store_data(context, data)
                context.state = StagingState.STORED
                context.completion_time = datetime.now()

                # Update metrics
                self.storage_metrics.storage_operations += 1
                self.storage_metrics.total_stored_bytes += len(data)

                # Send success response
                await self._send_success_response(
                    message,
                    {
                        'pipeline_id': pipeline_id,
                        'status': 'stored',
                        'location': context.storage_path,
                        'size_bytes': len(data)
                    },
                    MessageType.STAGING_STORE_COMPLETE
                )

            finally:
                self.active_operations -= 1
                await self._publish_metrics_update()

        except Exception as e:
            self.logger.error(f"Store request handling failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.STAGING_HANDLER_ERROR
            )

    async def _check_resource_limits(self) -> bool:
        """Check if resource limits are exceeded"""
        try:
            # Check storage usage
            usage_gb = await self._get_current_storage_usage_gb()
            if usage_gb > self.staging_limits['max_storage_usage_gb']:
                return False

            # Check concurrent operations
            if self.active_operations >= self.staging_limits['max_concurrent_operations']:
                return False

            return True

        except Exception as e:
            self.logger.error(f"Resource limit check failed: {str(e)}")
            return False

    async def _store_data(self, context: StagingContext, data: bytes) -> None:
        """Store data with improved error handling"""
        try:
            # Generate storage path
            storage_path = self.storage_path / f"{context.pipeline_id}_{uuid.uuid4()}"
            context.storage_path = str(storage_path)

            # Store data
            async with aiofiles.open(storage_path, 'wb') as f:
                await f.write(data)

            # Update context
            context.size_bytes = len(data)
            context.state = StagingState.STORED

            # Update repository
            await self.repository.create_resource(
                context.pipeline_id,
                str(storage_path),
                context.metadata
            )

        except Exception as e:
            self.logger.error(f"Data storage failed: {str(e)}")
            raise

    async def _send_success_response(
        self,
        original_message: ProcessingMessage,
        content: Dict[str, Any],
        message_type: MessageType
    ) -> None:
        """Send success response with proper routing"""
        response = original_message.create_response(
            message_type=message_type,
            content=content
        )
        await self.message_broker.publish(response)

    async def _send_error_response(
        self,
        original_message: ProcessingMessage,
        error_message: str,
        message_type: MessageType
    ) -> None:
        """Send error response with proper routing"""
        response = original_message.create_response(
            message_type=message_type,
            content={
                'error': error_message,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(response)

    async def _publish_metrics_update(self) -> None:
        """Publish current metrics"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_METRICS_UPDATE,
                    content={
                        'metrics': {
                            'active_stages': self.storage_metrics.active_stages,
                            'total_stored_bytes': self.storage_metrics.total_stored_bytes,
                            'current_storage_usage': self.storage_metrics.current_storage_usage,
                            'storage_operations': self.storage_metrics.storage_operations,
                            'retrieval_operations': self.storage_metrics.retrieval_operations,
                            'error_count': self.storage_metrics.error_count,
                            'active_operations': self.active_operations
                        },
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component='system_monitor',
                        domain_type='staging'
                    )
                )
            )
        except Exception as e:
            self.logger.error(f"Metrics update failed: {str(e)}")

    async def _manager_specific_cleanup(self) -> None:
        """Staging-specific cleanup"""
        try:
            # Cleanup expired resources
            await self._cleanup_expired_resources()

            # Cleanup repository
            if self.repository:
                await self.repository.cleanup_pending()

            # Release all resource locks
            self.resource_locks.clear()

            # Clear access control
            self.access_control.clear()

        except Exception as e:
            self.logger.error(f"Staging specific cleanup failed: {str(e)}")

    async def _monitor_storage_usage(self) -> None:
        """Monitor storage usage and trigger cleanup if needed"""
        while not self._shutting_down:
            try:
                usage_gb = await self._get_current_storage_usage_gb()
                if usage_gb > self.staging_limits['max_storage_usage_gb'] * 0.9:
                    await self._trigger_cleanup()
                await asyncio.sleep(300)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Storage monitoring failed: {str(e)}")
                if not self._shutting_down:
                    await asyncio.sleep(60)

    async def _monitor_expired_resources(self) -> None:
        """Monitor and cleanup expired resources"""
        while not self._shutting_down:
            try:
                cleanup_interval = self.staging_limits['cleanup_interval_minutes']
                await asyncio.sleep(cleanup_interval * 60)
                await self._cleanup_expired_resources()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Expired resource monitoring failed: {str(e)}")
                if not self._shutting_down:
                    await asyncio.sleep(60)

    async def _handle_service_error(self, message: ProcessingMessage) -> None:
        """
        Handle service error messages and perform appropriate error handling actions.

        Args:
            message (ProcessingMessage): The error message containing error details
                and metadata.
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            error_type = message.content.get('error_type', 'unknown')
            error_message = message.content.get('error_message', 'Unknown error occurred')

            # Update process context if it exists
            if pipeline_id in self.active_processes:
                context = self.active_processes[pipeline_id]
                context.status = ProcessingStatus.ERROR
                context.error = {
                    'type': error_type,
                    'message': error_message,
                    'timestamp': datetime.now().isoformat()
                }

                # Publish error status
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.STAGING_STATUS_RESPONSE,
                        content={
                            'pipeline_id': pipeline_id,
                            'status': 'error',
                            'error': context.error
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component='pipeline_manager',
                            domain_type='staging'
                        )
                    )
                )

                # Clean up resources if needed
                await self._cleanup_error_resources(pipeline_id)

            self.logger.error(
                f"Service error in pipeline {pipeline_id}: {error_type} - {error_message}"
            )

        except Exception as e:
            self.logger.error(f"Error handling service error: {str(e)}")
            raise

    async def _handle_metrics_update(self, message: ProcessingMessage) -> None:
        """
        Handle metrics update messages and process performance metrics.

        Args:
            message (ProcessingMessage): The message containing metrics data
                and metadata.
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            metric_type = message.content.get('metric_type')
            timestamp = message.content.get('timestamp', datetime.now().isoformat())
            metric_data = message.content.get('data', {})

            # Process metrics based on type
            if metric_type == 'storage_usage':
                await self._process_storage_metrics(metric_data)
            elif metric_type == 'performance':
                await self._process_performance_metrics(metric_data)
            elif metric_type == 'status_update':
                await self._process_status_metrics(metric_data)

            # Update repository with metrics if needed
            if pipeline_id:
                await self.repository.update_resource_metadata(
                    pipeline_id,
                    {
                        'last_metric_update': timestamp,
                        f'metrics_{metric_type}': metric_data
                    }
                )

            # Forward metrics to monitoring service
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_METRICS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'component': self.component_name,
                        'metric_type': metric_type,
                        'timestamp': timestamp,
                        'data': metric_data
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component='monitoring_service',
                        domain_type='staging'
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Error handling metrics update: {str(e)}")
            raise

    async def _cleanup_error_resources(self, pipeline_id: str) -> None:
        """
        Clean up resources after an error occurs.

        Args:
            pipeline_id (str): The ID of the pipeline that encountered an error.
        """
        try:
            context = self.active_processes.get(pipeline_id)
            if context and context.storage_reference:
                await self._delete_resource(context.storage_reference)

            # Remove from active processes
            self.active_processes.pop(pipeline_id, None)

        except Exception as e:
            self.logger.error(f"Error cleaning up resources for {pipeline_id}: {str(e)}")

    async def _process_storage_metrics(self, metric_data: Dict[str, Any]) -> None:
        """
        Process storage-related metrics.

        Args:
            metric_data (Dict[str, Any]): Dictionary containing storage metrics.
        """
        try:
            current_usage = metric_data.get('current_usage_gb', 0)
            if current_usage > self.staging_limits['max_storage_usage_gb'] * 0.8:
                await self._trigger_cleanup()

        except Exception as e:
            self.logger.error(f"Error processing storage metrics: {str(e)}")

    async def _process_performance_metrics(self, metric_data: Dict[str, Any]) -> None:
        """
        Process performance-related metrics.

        Args:
            metric_data (Dict[str, Any]): Dictionary containing performance metrics.
        """
        try:
            processing_time = metric_data.get('processing_time_ms')
            if processing_time and processing_time > 5000:  # 5 seconds threshold
                self.logger.warning(
                    f"High processing time detected: {processing_time}ms"
                )

        except Exception as e:
            self.logger.error(f"Error processing performance metrics: {str(e)}")

    async def _process_status_metrics(self, metric_data: Dict[str, Any]) -> None:
        """
        Process status-related metrics.

        Args:
            metric_data (Dict[str, Any]): Dictionary containing status metrics.
        """
        try:
            status = metric_data.get('status')
            if status == 'error':
                self.logger.error(
                    f"Error status detected: {metric_data.get('error_message', 'Unknown error')}"
                )

        except Exception as e:
            self.logger.error(f"Error processing status metrics: {str(e)}")

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

            # Determine appropriate output type
            type_mapping = {
                'file': 'ANALYTICS',
                'csv': 'ANALYTICS',
                'excel': 'ANALYTICS',
                'database': 'DECISION',
                'api': 'INSIGHT',
            }
            output_type = type_mapping.get(source_type, 'ANALYTICS')

            # Force a stage_key if not present
            if 'stage_key' not in metadata or metadata['stage_key'] is None:
                metadata['stage_key'] = f"{source_type}_{datetime.now().timestamp()}_{uuid.uuid4().hex}"

            # Log for debugging
            logger.info(f"In store_data - stage_key: {metadata.get('stage_key')}")

            # Ensure component_type is set correctly
            if 'component_type' in metadata:
                # Map to database enum values
                component_mapping = {
                    'analytics.service': 'ANALYTICS',
                    'analytics': 'ANALYTICS',
                    'ANALYTICS_SERVICE': 'ANALYTICS',
                    # ... other mappings
                }

                if isinstance(metadata['component_type'], str):
                    metadata['component_type'] = component_mapping.get(metadata['component_type'], 'ANALYTICS')
            else:
                metadata['component_type'] = output_type

            # Create a new metadata dictionary that guarantees the stage_key is present
            fixed_metadata = {
                'stage_key': metadata['stage_key'],  # Ensure this is copied
                **metadata
            }

            logger.info(f"Before repository call - stage_key: {fixed_metadata.get('stage_key')}")

            # Create staged output with the fixed metadata
            stored_resource = await self.repository.create_staged_output(
                fixed_metadata,  # Use the fixed metadata
                output_type=output_type,
                pipeline_id=metadata.get('pipeline_id'),
                user_id=metadata.get('user_id')
            )

            return {
                'status': 'success',
                'staged_id': str(stored_resource.id),
                'reference': metadata.get('stage_key')
            }

        except Exception as e:
            logger.error(f"Data storage failed: {str(e)}", exc_info=True)
            # Log the state of metadata for debugging
            logger.error(f"Failed metadata: {metadata}")
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

    async def _handle_service_start(self, message: ProcessingMessage) -> None:
        """Handle service start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            staging_context = StagingContext(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.RECEPTION,
                status=ProcessingStatus.PENDING
            )
            self.active_processes[pipeline_id] = staging_context
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_SERVICE_STATUS,
                    content={'pipeline_id': pipeline_id, 'status': 'started'},
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component=message.metadata.source_component,
                        domain_type="staging"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Service start handling failed: {str(e)}")
            raise

    async def _handle_service_status(self, message: ProcessingMessage) -> None:
        """Handle service status request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_processes.get(pipeline_id)
            if context:
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.STAGING_STATUS_RESPONSE,
                        content={
                            'pipeline_id': pipeline_id,
                            'stage': context.stage.value,
                            'status': context.status.value
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component=message.metadata.source_component,
                            domain_type="staging"
                        )
                    )
                )
        except Exception as e:
            logger.error(f"Status handling failed: {str(e)}")
            raise

    async def _handle_service_complete(self, message: ProcessingMessage) -> None:
        """Handle service completion"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if pipeline_id in self.active_processes:
                context = self.active_processes[pipeline_id]
                context.status = ProcessingStatus.COMPLETED
                await self._cleanup_process(pipeline_id)
        except Exception as e:
            logger.error(f"Service completion handling failed: {str(e)}")
            raise

    async def _handle_service_decision(self, message: ProcessingMessage) -> None:
        """Handle service decision request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            decision = message.content.get('decision')
            if pipeline_id in self.active_processes:
                context = self.active_processes[pipeline_id]
                await self._process_decision(context, decision)
        except Exception as e:
            logger.error(f"Decision handling failed: {str(e)}")
            raise

    async def _handle_handler_start(self, message: ProcessingMessage) -> None:
        """Handle handler start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            self.active_processes[pipeline_id] = StagingContext(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.RECEPTION,
                status=ProcessingStatus.PENDING
            )
        except Exception as e:
            logger.error(f"Handler start failed: {str(e)}")
            raise

    async def _handle_handler_store(self, message: ProcessingMessage) -> None:
        """Handle store request from handler"""
        try:
            await self.store_data(
                data=message.content.get('data'),
                metadata=message.content.get('metadata', {}),
                source_type=message.content.get('source_type')
            )
        except Exception as e:
            logger.error(f"Handler store failed: {str(e)}")
            raise

    async def _handle_handler_delete(self, message: ProcessingMessage) -> None:
        """Handle delete request from handler"""
        try:
            resource_id = message.content.get('resource_id')
            await self._delete_resource(resource_id)
        except Exception as e:
            logger.error(f"Handler delete failed: {str(e)}")
            raise

    async def _handle_handler_retrieve(self, message: ProcessingMessage) -> None:
        """Handle retrieve request with access control and error handling"""
        try:
            # Extract request details
            pipeline_id = message.content.get('pipeline_id')
            reference = message.content.get('reference')
            requester_id = message.content.get('requester_id')

            # Validate access
            if not await self._validate_access(reference, requester_id):
                await self._send_error_response(
                    message,
                    "Access denied",
                    MessageType.STAGING_ACCESS_DENIED
                )
                return

            # Check resource limits
            if not await self._check_resource_limits():
                await self._send_error_response(
                    message,
                    "Resource limits exceeded",
                    MessageType.STAGING_HANDLER_ERROR
                )
                return

            # Create staging context
            context = StagingContext(
                pipeline_id=pipeline_id,
                state=StagingState.RETRIEVING,
                metadata=message.content.get('metadata', {})
            )

            # Retrieve data
            try:
                self.active_operations += 1
                data = await self._read_data(Path(reference), context.metadata.get('type', 'binary'))
                context.state = StagingState.STORED

                # Update metrics
                self.storage_metrics.retrieval_operations += 1
                self.storage_metrics.total_retrieved_bytes += len(data)

                # Send success response
                await self._send_success_response(
                    message,
                    {
                        'pipeline_id': pipeline_id,
                        'reference': reference,
                        'data': data,
                        'size_bytes': len(data),
                        'type': context.metadata.get('type', 'binary')
                    },
                    MessageType.STAGING_RETRIEVE_COMPLETE
                )

            finally:
                self.active_operations -= 1
                await self._publish_metrics_update()

        except Exception as e:
            self.logger.error(f"Retrieve request handling failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.STAGING_HANDLER_ERROR
            )

    async def _handle_handler_decision(self, message: ProcessingMessage) -> None:
        """Handle decision from handler"""
        await self._handle_service_decision(message)

    async def _handle_handler_update(self, message: ProcessingMessage) -> None:
        """Handle update from handler"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            updates = message.content.get('updates', {})
            if pipeline_id in self.active_processes:
                context = self.active_processes[pipeline_id]
                for key, value in updates.items():
                    setattr(context, key, value)
        except Exception as e:
            logger.error(f"Handler update failed: {str(e)}")
            raise

    async def _handle_handler_complete(self, message: ProcessingMessage) -> None:
        """Handle handler completion"""
        await self._handle_service_complete(message)

    async def _handle_handler_status(self, message: ProcessingMessage) -> None:
        """Handle handler status request"""
        await self._handle_service_status(message)

    async def _handle_handler_error(self, message: ProcessingMessage) -> None:
        """Handle handler error"""
        await self._handle_service_error(message)

    async def _handle_status_request(self, message: ProcessingMessage) -> None:
        """Handle status requests with comprehensive metrics"""
        try:
            # Get current metrics
            current_usage = await self._get_current_storage_usage_gb()
            active_ops = self.active_operations
            metrics = {
                'storage_usage': current_usage,
                'active_operations': active_ops,
                'total_stored_bytes': self.storage_metrics.total_stored_bytes,
                'total_retrieved_bytes': self.storage_metrics.total_retrieved_bytes,
                'storage_operations': self.storage_metrics.storage_operations,
                'retrieval_operations': self.storage_metrics.retrieval_operations,
                'error_count': self.storage_metrics.error_count,
                'cleanup_count': self.storage_metrics.cleanup_count,
                'timestamp': datetime.now().isoformat()
            }

            # Send status response
            await self._send_success_response(
                message,
                metrics,
                MessageType.STAGING_STATUS_RESPONSE
            )

        except Exception as e:
            self.logger.error(f"Status request handling failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.STAGING_HANDLER_ERROR
            )

    async def _handle_cleanup_request(self, message: ProcessingMessage) -> None:
        """Handle cleanup requests with proper resource management"""
        try:
            # Extract request details
            pipeline_id = message.content.get('pipeline_id')
            force = message.content.get('force', False)

            # Trigger cleanup
            try:
                await self._cleanup_expired_resources()
                
                if force:
                    # Additional cleanup for force mode
                    await self._cleanup_error_resources(pipeline_id)

                # Update metrics
                self.storage_metrics.cleanup_count += 1

                # Send success response
                await self._send_success_response(
                    message,
                    {
                        'pipeline_id': pipeline_id,
                        'status': 'cleaned',
                        'force': force
                    },
                    MessageType.STAGING_CLEANUP_COMPLETE
                )

            except Exception as e:
                self.logger.error(f"Cleanup operation failed: {str(e)}")
                await self._send_error_response(
                    message,
                    str(e),
                    MessageType.STAGING_HANDLER_ERROR
                )

        except Exception as e:
            self.logger.error(f"Cleanup request handling failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.STAGING_HANDLER_ERROR
            )

    async def _handle_cleanup_complete(self, message: ProcessingMessage) -> None:
        """Handle cleanup completion"""
        pass  # Optional: implement if needed

    async def _handle_store_request(self, message: ProcessingMessage) -> None:
        """Handle data store request"""
        await self._handle_handler_store(message)

    async def _handle_retrieve_request(self, message: ProcessingMessage) -> None:
        """Handle data retrieve request"""
        await self._handle_handler_retrieve(message)

    async def _handle_delete_request(self, message: ProcessingMessage) -> None:
        """Handle data delete request"""
        await self._handle_handler_delete(message)

    async def _handle_access_request(self, message: ProcessingMessage) -> None:
        """Handle access control requests"""
        try:
            # Extract request details
            pipeline_id = message.content.get('pipeline_id')
            reference = message.content.get('reference')
            requester_id = message.content.get('requester_id')
            access_type = message.content.get('access_type', 'read')

            # Validate access
            if await self._validate_access(reference, requester_id):
                # Grant access
                await self._handle_access_grant(message)
            else:
                # Deny access
                await self._handle_access_deny(message)

        except Exception as e:
            self.logger.error(f"Access request handling failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.STAGING_HANDLER_ERROR
            )

    async def _handle_status_response(self, message: ProcessingMessage) -> None:
        """Handle status response"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            status = message.content.get('status')
            stage = message.content.get('stage')

            # Update process context if exists
            if pipeline_id in self.active_processes:
                context = self.active_processes[pipeline_id]
                context.status = ProcessingStatus(status) if status else context.status
                context.stage = ProcessingStage(stage) if stage else context.stage

                # Update metrics
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.STAGING_METRICS_UPDATE,
                        content={
                            'pipeline_id': pipeline_id,
                            'metric_type': 'status_update',
                            'timestamp': datetime.now().isoformat(),
                            'data': {
                                'status': status,
                                'stage': stage,
                                'component': message.metadata.source_component
                            }
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component='monitoring_service',
                            domain_type='staging'
                        )
                    )
                )

                # Forward status update to interested components
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.STAGING_STATUS_REQUEST,
                        content={
                            'pipeline_id': pipeline_id,
                            'status': status,
                            'stage': stage
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component='pipeline_manager',
                            domain_type='staging'
                        )
                    )
                )

        except Exception as e:
            logger.error(f"Status response handling failed: {str(e)}")
            raise

    async def _handle_access_grant(self, message: ProcessingMessage) -> None:
        """Handle access grant response"""
        try:
            reference = message.content.get('reference')
            requester = message.metadata.source_component

            # Update resource access metadata
            resource = await self.repository.get_by_id(reference)
            if resource:
                # Add requester to allowed components if not already present
                allowed_components = resource.metadata.get('allowed_components', [])
                if requester not in allowed_components:
                    allowed_components.append(requester)

                # Update metadata
                await self.repository.update_resource_metadata(
                    reference,
                    {
                        'allowed_components': allowed_components,
                        'last_access_grant': datetime.now().isoformat(),
                        'last_access_component': requester
                    }
                )

            # Notify requester of access grant
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_ACCESS_GRANTED,
                    content={
                        'reference': reference,
                        'status': 'granted',
                        'access_level': 'read_write'  # or based on your access control logic
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component=requester,
                        domain_type='staging'
                    )
                )
            )

        except Exception as e:
            logger.error(f"Access grant handling failed: {str(e)}")
            raise

    async def _handle_access_deny(self, message: ProcessingMessage) -> None:
        """Handle access denial response"""
        try:
            reference = message.content.get('reference')
            requester = message.metadata.source_component
            reason = message.content.get('reason', 'Access denied by policy')

            # Log access denial
            resource = await self.repository.get_by_id(reference)
            if resource:
                # Update metadata with denial info
                await self.repository.update_resource_metadata(
                    reference,
                    {
                        'last_access_denial': datetime.now().isoformat(),
                        'last_denied_component': requester,
                        'denial_reason': reason
                    }
                )

            # Notify requester of access denial
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.STAGING_ACCESS_DENIED,
                    content={
                        'reference': reference,
                        'status': 'denied',
                        'reason': reason,
                        'retry_allowed': True  # or based on your policy
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component=requester,
                        domain_type='staging'
                    )
                )
            )

            # Optional: Notify monitoring service of access denial
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_SECURITY_EVENT,
                    content={
                        'event_type': 'access_denial',
                        'component': requester,
                        'resource': reference,
                        'reason': reason,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component='monitoring_service',
                        domain_type='staging'
                    )
                )
            )

        except Exception as e:
            logger.error(f"Access denial handling failed: {str(e)}")
            raise

    async def get_staged_files(self, filter_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get staged files with filtering

        Args:
            filter_params: Filtering parameters (user_id, source_type, etc.)

        Returns:
            List of staged files matching filter criteria
        """
        try:
            # Use repository to get staged files
            staged_files = await self.repository.get_all_resources(
                query_params=filter_params,
                sort=[("created_at", -1)]  # Most recent first
            )

            return [
                {
                    'id': str(file.id),
                    'filename': file.metadata.get('original_filename', ''),
                    'status': file.status,
                    'created_at': file.created_at,
                    'metadata': file.metadata,
                    'size': file.metadata.get('size', 0),
                    'mime_type': file.metadata.get('mime_type', ''),
                    'processing_status': file.processing_status
                }
                for file in staged_files
            ]
        except Exception as e:
            logger.error(f"Error getting staged files: {str(e)}")
            return []


    async def list_files(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List all files for a specific user

        Args:
            user_id: ID of the user

        Returns:
            List of files belonging to the user
        """
        try:
            return await self.get_staged_files({
                'user_id': user_id,
                'resource_type': 'file'
            })
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            return []