# backend/core/managers/base/base_manager.py

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Coroutine, List, Set
from datetime import datetime
import uuid
from pathlib import Path
import psutil

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    ManagerContext,
    ManagerState,
    ManagerMetrics,
    ProcessingStage,
    ProcessingStatus
)
from .manager_types import ChannelManager


class BaseManager:
    """Base manager implementation with comprehensive message handling"""

    def __init__(
            self,
            message_broker: MessageBroker,
            component_name: str,
            domain_type: str
    ):
        # Core components
        self.message_broker = message_broker
        self.logger = logging.getLogger(f"{component_name}_manager")

        # State tracking
        self._shutting_down = False
        self.storage_path: Optional[Path] = None

        # Context initialization
        self._context: Optional[ManagerContext] = None
        self._initialize_context(component_name, domain_type)

        # Thread-safe task management
        self._async_lock = asyncio.Lock()
        self._background_tasks: Set[asyncio.Task] = set()
        self._message_handlers: Dict[MessageType, Callable] = {}

        # Channel management
        self.channel_manager = ChannelManager(logger=self.logger)

        # Process tracking
        self.active_processes: Dict[str, Any] = {}
        self.process_timeouts: Dict[str, datetime] = {}

        # Resource management
        self.resource_limits = {
            'max_cpu_percent': 80,
            'max_memory_percent': 85,
            'max_storage_gb': 10
        }

    def _initialize_context(self, component_name: str, domain_type: str) -> None:
        """Initialize manager context safely"""
        try:
            self._context = ManagerContext(
                pipeline_id=str(uuid.uuid4()),
                component_name=component_name,
                domain_type=domain_type,
                stage=ProcessingStage.INITIAL_VALIDATION,
                status=ProcessingStatus.PENDING,
                state=ManagerState.INITIALIZING,
                metrics=ManagerMetrics()
            )
        except Exception as e:
            self.logger.error(f"Context initialization failed: {e}")
            raise

    @property
    def context(self) -> ManagerContext:
        """Safe context access with validation"""
        if self._context is None:
            raise AttributeError(f"{self.__class__.__name__} context not initialized")
        return self._context

    def _start_background_task(self, coro, task_name: str) -> None:
        """Start and track a background task safely"""
        if self._shutting_down:
            return

        task = asyncio.create_task(coro, name=task_name)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def start(self) -> None:
        """Initialize and start the manager"""
        try:
            self.logger.info(f"Starting {self.context.component_name} manager")

            # Setup handlers
            await self._setup_base_handlers()
            await self._setup_domain_handlers()

            # Start monitoring
            self._start_monitoring()

            # Mark as active
            self.context.state = ManagerState.ACTIVE

        except Exception as e:
            self.logger.error(f"Manager start failed: {str(e)}")
            raise

    def _start_monitoring(self) -> None:
        """Start essential monitoring tasks"""
        self._start_background_task(
            self._monitor_process_timeouts(),
            "process_timeout_monitor"
        )
        self._start_background_task(
            self._monitor_resource_usage(),
            "resource_usage_monitor"
        )
        self._start_background_task(
            self._monitor_system_health(),
            "system_health_monitor"
        )

    async def _setup_base_handlers(self) -> None:
        """Setup common message handlers"""
        base_handlers = {
            MessageType.MONITORING_HEALTH_CHECK: self._handle_health_check,
            MessageType.ERROR_REPORT_NOTIFY: self._handle_error_report,
            MessageType.MONITORING_CLEANUP_REQUEST: self.cleanup
        }

        for message_type, handler in base_handlers.items():
            await self.register_message_handler(message_type, handler)

    async def _setup_domain_handlers(self) -> None:
        """Setup domain-specific handlers - to be implemented by subclasses"""
        raise NotImplementedError

    async def _monitor_process_timeouts(self) -> None:
        """Monitor for process timeouts"""
        while not self._shutting_down:
            try:
                current_time = datetime.now()
                for process_id, timeout_time in list(self.process_timeouts.items()):
                    if current_time > timeout_time:
                        await self._handle_process_timeout(process_id)
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Process timeout monitoring failed: {str(e)}")
                if not self._shutting_down:
                    await asyncio.sleep(60)

    async def _monitor_resource_usage(self) -> None:
        """Monitor system resource usage"""
        while not self._shutting_down:
            try:
                metrics = await self._collect_resource_metrics()
                await self._check_resource_limits(metrics)
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Resource monitoring failed: {str(e)}")
                if not self._shutting_down:
                    await asyncio.sleep(30)

    async def _monitor_system_health(self) -> None:
        """Monitor overall system health"""
        while not self._shutting_down:
            try:
                status = await self._check_system_health()
                if not status['healthy']:
                    await self._handle_health_issues(status)
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health monitoring failed: {str(e)}")
                if not self._shutting_down:
                    await asyncio.sleep(60)

    async def _collect_resource_metrics(self) -> Dict[str, float]:
        """Collect current resource metrics"""
        try:
            process = psutil.Process()
            return {
                'cpu_percent': process.cpu_percent(),
                'memory_percent': process.memory_percent(),
                'num_threads': process.num_threads(),
                'open_files': len(process.open_files())
            }
        except Exception as e:
            self.logger.error(f"Resource metrics collection failed: {str(e)}")
            return {}

    async def _check_resource_limits(self, metrics: Dict[str, float]) -> None:
        """Check if resource usage exceeds limits"""
        if metrics.get('cpu_percent', 0) > self.resource_limits['max_cpu_percent']:
            await self._handle_resource_violation('cpu', metrics['cpu_percent'])

        if metrics.get('memory_percent', 0) > self.resource_limits['max_memory_percent']:
            await self._handle_resource_violation('memory', metrics['memory_percent'])

    async def _handle_resource_violation(self, resource: str, value: float) -> None:
        """Handle resource limit violations"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RESOURCE_ALERT,
                    content={
                        'resource': resource,
                        'value': value,
                        'limit': self.resource_limits[f'max_{resource}_percent'],
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.context.component_name,
                        target_component='monitoring_service',
                        domain_type=self.context.domain_type
                    )
                )
            )
        except Exception as e:
            self.logger.error(f"Resource violation handling failed: {str(e)}")

    async def register_message_handler(
            self,
            message_type: MessageType,
            handler: Callable[[ProcessingMessage], Coroutine]
    ) -> None:
        """Register a message handler thread-safely"""
        async with self._async_lock:
            self._message_handlers[message_type] = handler
            await self.message_broker.subscribe(
                module_identifier=self.context.component_name,
                message_patterns=[message_type.value],
                callback=self._handle_message
            )

    async def _handle_message(self, message: ProcessingMessage) -> None:
        """Handle messages with proper error handling"""
        if self._shutting_down:
            return

        try:
            handler = self._message_handlers.get(message.message_type)
            if not handler:
                raise ValueError(f"No handler for message type: {message.message_type}")

            self.context.state = ManagerState.PROCESSING
            await handler(message)

        except Exception as e:
            self.logger.error(f"Message handling failed: {str(e)}")
            await self._handle_error(message, str(e))
        finally:
            if not self._shutting_down:
                self.context.state = ManagerState.ACTIVE

    async def cleanup(self) -> None:
        """Perform thorough cleanup"""
        try:
            self._shutting_down = True
            self.logger.info(f"Starting cleanup for {self.context.component_name}")

            # Cancel background tasks
            if self._background_tasks:
                for task in self._background_tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
                self._background_tasks.clear()

            # Cleanup processes and resources
            await self._cleanup_active_processes()
            await self._cleanup_resources()
            await self._cleanup_messaging()

            # Allow specific cleanup
            await self._manager_specific_cleanup()

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise
        finally:
            self.logger.info("Cleanup completed")

    async def _cleanup_active_processes(self) -> None:
        """Clean up active processes"""
        try:
            for process_id in list(self.active_processes.keys()):
                await self._cleanup_process(process_id)
            self.active_processes.clear()
            self.process_timeouts.clear()
        except Exception as e:
            self.logger.error(f"Process cleanup failed: {str(e)}")

    async def _cleanup_resources(self) -> None:
        """Clean up file system resources"""
        try:
            if self.storage_path and self.storage_path.exists():
                for file in self.storage_path.glob('*'):
                    try:
                        file.unlink()
                    except Exception as e:
                        self.logger.error(f"Failed to delete {file}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Resource cleanup failed: {str(e)}")

    async def _cleanup_messaging(self) -> None:
        """Clean up messaging system"""
        try:
            self.channel_manager.cleanup_channels()
            self._message_handlers.clear()
        except Exception as e:
            self.logger.error(f"Messaging cleanup failed: {str(e)}")

    async def _cleanup_process(self, process_id: str) -> None:
        """Clean up a specific process"""
        try:
            process = self.active_processes.pop(process_id, None)
            if process:
                self.process_timeouts.pop(process_id, None)
                if hasattr(process, 'cleanup'):
                    await process.cleanup()
        except Exception as e:
            self.logger.error(f"Process cleanup failed for {process_id}: {str(e)}")

    async def _manager_specific_cleanup(self) -> None:
        """Hook for manager-specific cleanup"""
        pass

    async def _handle_health_check(self, message: ProcessingMessage) -> None:
        """Handle health check requests"""
        try:
            status = await self._check_system_health()
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.HEALTH_CHECK_RESPONSE,
                    content=status,
                    metadata=MessageMetadata(
                        source_component=self.context.component_name,
                        target_component=message.metadata.source_component,
                        domain_type=self.context.domain_type
                    )
                )
            )
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _check_system_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        try:
            metrics = await self._collect_resource_metrics()
            return {
                'healthy': all(
                    metrics.get(k, 0) <= v
                    for k, v in self.resource_limits.items()
                ),
                'metrics': metrics,
                'state': self.context.state.value,
                'active_processes': len(self.active_processes),
                'background_tasks': len(self._background_tasks),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {'healthy': False, 'error': str(e)}

    async def _handle_process_timeout(self, process_id: str) -> None:
        """Handle process timeout"""
        try:
            await self._cleanup_process(process_id)
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PROCESS_TIMEOUT,
                    content={
                        'process_id': process_id,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.context.component_name,
                        target_component='monitoring_service',
                        domain_type=self.context.domain_type
                    )
                )
            )
        except Exception as e:
            self.logger.error(f"Timeout handling failed: {str(e)}")

    # Continuation of BaseManager class

    async def _handle_error(self, message: ProcessingMessage, error: str) -> None:
        """Handle processing errors"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ERROR_REPORT,
                    content={
                        'error': error,
                        'message_type': message.message_type.value,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.context.component_name,
                        target_component='error_handler',
                        domain_type=self.context.domain_type,
                        error=True
                    )
                )
            )
        except Exception as e:
            self.logger.error(f"Error reporting failed: {str(e)}")
            if not self._shutting_down:
                await self._emergency_shutdown(str(e))

    async def _emergency_shutdown(self, error: str) -> None:
        """Perform emergency shutdown on critical error"""
        try:
            self.logger.critical(f"Emergency shutdown triggered: {error}")
            self._shutting_down = True

            # Cancel all tasks
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.SYSTEM_SHUTDOWN_REQUEST,
                    content={
                        'component': self.context.component_name,
                        'error': error,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.context.component_name,
                        target_component='system',
                        domain_type=self.context.domain_type,
                        error=True
                    )
                )
            )
        except Exception as e:
            self.logger.critical(f"Emergency shutdown failed: {str(e)}")

    async def _handle_health_issues(self, health_status: Dict[str, Any]) -> None:
        """Handle system health issues"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.HEALTH_ALERT,
                    content={
                        'status': health_status,
                        'component': self.context.component_name,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.context.component_name,
                        target_component='monitoring_service',
                        domain_type=self.context.domain_type
                    )
                )
            )
        except Exception as e:
            self.logger.error(f"Health alert failed: {str(e)}")

    async def _handle_error_report(self, message: ProcessingMessage) -> None:
        """Handle error report messages"""
        try:
            error_info = message.content.get('error', '')
            self.logger.error(f"Error report received: {error_info}")
            self.context.metrics.errors_encountered += 1

            # Update error tracking
            if hasattr(self.context, 'error_history'):
                self.context.error_history.append({
                    'error': error_info,
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            self.logger.error(f"Error report handling failed: {str(e)}")

    async def _update_metrics(self, metrics_update: Dict[str, Any]) -> None:
        """Update component metrics"""
        try:
            # Update standard metrics
            if hasattr(self.context.metrics, 'messages_processed'):
                self.context.metrics.messages_processed += metrics_update.get('messages_processed', 0)

            if hasattr(self.context.metrics, 'errors_encountered'):
                self.context.metrics.errors_encountered += metrics_update.get('errors_encountered', 0)

            # Update any additional metrics
            for key, value in metrics_update.items():
                if hasattr(self.context.metrics, key):
                    setattr(self.context.metrics, key, value)

            self.context.metrics.last_activity = datetime.now()

        except Exception as e:
            self.logger.error(f"Metrics update failed: {str(e)}")

    def _get_process_info(self, process_id: str) -> Optional[Dict[str, Any]]:
        """Get process information safely"""
        try:
            process = self.active_processes.get(process_id)
            if not process:
                return None

            return {
                'id': process_id,
                'state': getattr(process, 'state', None),
                'start_time': getattr(process, 'start_time', None),
                'updated_at': getattr(process, 'updated_at', None)
            }
        except Exception as e:
            self.logger.error(f"Process info retrieval failed: {str(e)}")
            return None

    async def _validate_process_state(
            self,
            process_id: str,
            expected_states: List[Any]
    ) -> bool:
        """Validate process state"""
        try:
            process = self.active_processes.get(process_id)
            if not process:
                return False

            current_state = getattr(process, 'state', None)
            return current_state in expected_states

        except Exception as e:
            self.logger.error(f"Process state validation failed: {str(e)}")
            return False

    async def _update_process_state(
            self,
            process_id: str,
            new_state: Any,
            metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update process state safely"""
        try:
            process = self.active_processes.get(process_id)
            if not process:
                return False

            # Update state
            process.state = new_state
            process.updated_at = datetime.now()

            # Update metadata
            if metadata:
                process.metadata.update(metadata)

            return True

        except Exception as e:
            self.logger.error(f"Process state update failed: {str(e)}")
            return False

    async def _handle_timeout_error(self, error_details: Dict[str, Any]) -> None:
        """Handle timeout errors"""
        try:
            process_id = error_details.get('process_id')
            if process_id:
                await self._cleanup_process(process_id)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.TIMEOUT_ERROR,
                    content={
                        'error_details': error_details,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.context.component_name,
                        target_component='error_handler',
                        domain_type=self.context.domain_type,
                        error=True
                    )
                )
            )
        except Exception as e:
            self.logger.error(f"Timeout error handling failed: {str(e)}")

    async def _publish_metrics(self, metrics: Dict[str, Any]) -> None:
        """Publish metrics update"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.METRICS_UPDATE,
                    content={
                        'metrics': metrics,
                        'component': self.context.component_name,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.context.component_name,
                        target_component='monitoring_service',
                        domain_type=self.context.domain_type
                    )
                )
            )
        except Exception as e:
            self.logger.error(f"Metrics publishing failed: {str(e)}")