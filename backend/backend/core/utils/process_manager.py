import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List, Union, Callable, Awaitable
from datetime import datetime, timedelta
from functools import wraps

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ProcessingStatus,
    ModuleIdentifier,
    ComponentType,
    ProcessingMessage
)
import functools
import logging
from typing import Callable, Awaitable, Any

from backend.core.messaging.types import ProcessingStatus

logger = logging.getLogger(__name__)



class ProcessContext:
    """
    Comprehensive context for tracking process execution

    Attributes:
        process_id: Unique identifier for the process
        pipeline_id: Associated pipeline identifier
        handler_type: Type of handler managing the process
        start_time: When the process began
        end_time: When the process completed
        status: Current status of the process
        metadata: Additional contextual information
        error: Any error encountered during process execution
    """

    def __init__(
            self,
            process_id: str,
            pipeline_id: Optional[str] = None,
            handler_type: Optional[str] = None
    ):
        self.process_id = process_id
        self.pipeline_id = pipeline_id
        self.handler_type = handler_type
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.status = ProcessingStatus.PENDING
        self.metadata: Dict[str, Any] = {}
        self.error: Optional[str] = None
        self.retries = 0
        self.max_retries = 3
        self.timeout = 600.0  # 10 minutes default

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert process context to dictionary representation

        Returns:
            Dictionary with process details
        """
        return {
            'process_id': self.process_id,
            'pipeline_id': self.pipeline_id,
            'handler_type': self.handler_type,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status.value,
            'metadata': self.metadata,
            'error': self.error,
            'retries': self.retries,
            'max_retries': self.max_retries,
            'timeout': self.timeout
        }

class ProcessManager:
    """
    Advanced process management system

    Key Responsibilities:
    - Track and manage process lifecycle
    - Provide comprehensive process monitoring
    - Support flexible process handling
    - Integrate with messaging system
    """

    _instance = None

    def __new__(cls, message_broker: Optional[MessageBroker] = None):
        """
        Singleton implementation for ProcessManager

        Args:
            message_broker: Optional message broker instance
        """
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, message_broker: Optional[MessageBroker] = None):
        """
        Initialize process manager

        Args:
            message_broker: Optional message broker instance
        """
        # Prevent re-initialization
        if not hasattr(self, '_initialized'):
            # Use provided message broker or import default
            if message_broker is None:
                from backend.core.messaging.broker import MessageBroker

            # Core process tracking
            self.message_broker = MessageBroker
            self.active_processes: Dict[str, ProcessContext] = {}
            self.process_lock = asyncio.Lock()

            # Background cleanup task
            self._cleanup_task = None

            # Module identifier for messaging
            self.module_id = ModuleIdentifier(
                component_name="process_manager",
                component_type=ComponentType.MANAGER,
                method_name="process_tracking"
            )

            # Initialization flag
            self._initialized = True

    async def start(self) -> None:
        """
        Start process manager background tasks
        """
        try:
            # Register with message broker
            await self.message_broker.register_component(
                component=self.module_id,
                default_callback=self._handle_process_messages
            )

            # Subscribe to process-related messages
            await self.message_broker.subscribe(
                component=self.module_id,
                pattern="process.#",
                callback=self._handle_process_messages
            )

            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._periodic_process_cleanup())

            logger.info("Process Manager started successfully")

        except Exception as e:
            logger.error(f"Failed to start Process Manager: {e}")
            raise

    async def stop(self) -> None:
        """
        Gracefully stop process manager
        """
        try:
            # Cancel cleanup task
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # Cleanup all active processes
            await self.cleanup_all_processes()

            logger.info("Process Manager stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping Process Manager: {e}")

    async def create_process(
            self,
            pipeline_id: Optional[str] = None,
            handler_type: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessContext:
        """
        Create a new process context

        Args:
            pipeline_id: Optional associated pipeline ID
            handler_type: Optional handler type
            metadata: Optional additional metadata

        Returns:
            Created ProcessContext instance
        """
        async with self.process_lock:
            # Generate unique process ID
            process_id = str(uuid.uuid4())

            # Create process context
            process = ProcessContext(
                process_id=process_id,
                pipeline_id=pipeline_id,
                handler_type=handler_type
            )

            # Set metadata if provided
            if metadata:
                process.metadata = metadata

            # Store process
            self.active_processes[process_id] = process

            return process

    async def update_process_status(
            self,
            process_id: str,
            status: ProcessingStatus,
            error: Optional[str] = None
    ) -> Optional[ProcessContext]:
        """
        Update status of an existing process

        Args:
            process_id: Unique process identifier
            status: New processing status
            error: Optional error message

        Returns:
            Updated ProcessContext or None if not found
        """
        async with self.process_lock:
            process = self.active_processes.get(process_id)
            if not process:
                logger.warning(f"Process {process_id} not found for status update")
                return None

            # Update status
            process.status = status

            # Set error if provided
            if error:
                process.error = error
                process.status = ProcessingStatus.FAILED

            # Update end time for final states
            if status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]:
                process.end_time = datetime.now()

            return process

    async def _handle_process_messages(self, message: 'ProcessingMessage') -> None:
        """
        Handle incoming process-related messages

        Args:
            message: Incoming processing message
        """
        try:
            # Route based on message type
            if message.message_type == MessageType.PIPELINE_START:
                await self._handle_pipeline_start(message)
            elif message.message_type == MessageType.PIPELINE_PAUSE:
                await self._handle_pipeline_pause(message)
            elif message.message_type == MessageType.PIPELINE_RESUME:
                await self._handle_pipeline_resume(message)
            elif message.message_type == MessageType.PIPELINE_CANCEL:
                await self._handle_pipeline_cancel(message)

        except Exception as e:
            logger.error(f"Error handling process message: {e}")

    async def _handle_pipeline_start(self, message: 'ProcessingMessage') -> None:
        """
        Handle pipeline start request

        Args:
            message: Pipeline start message
        """
        try:
            pipeline_id = message.content.get('pipeline_id')

            # Create process context
            process = await self.create_process(
                pipeline_id=pipeline_id,
                handler_type='pipeline',
                metadata=message.content.get('metadata', {})
            )

            # Update status to active
            await self.update_process_status(
                process.process_id,
                ProcessingStatus.ACTIVE
            )

            # Publish start confirmation
            start_response = message.create_response(
                message_type=MessageType.PIPELINE_START,
                content={
                    'process_id': process.process_id,
                    'status': ProcessingStatus.ACTIVE.value
                }
            )
            await self.message_broker.publish(start_response)

        except Exception as e:
            logger.error(f"Pipeline start handling failed: {e}")

    async def _handle_pipeline_pause(self, message: 'ProcessingMessage') -> None:
        """
        Handle pipeline pause request

        Args:
            message: Pipeline pause message
        """
        try:
            pipeline_id = message.content.get('pipeline_id')

            # Find and pause processes for the pipeline
            paused_processes = []
            async with self.process_lock:
                for process in self.active_processes.values():
                    if (process.pipeline_id == pipeline_id and
                            process.status == ProcessingStatus.ACTIVE):
                        await self.update_process_status(
                            process.process_id,
                            ProcessingStatus.PAUSED
                        )
                        paused_processes.append(process.process_id)

            # Publish pause confirmation
            pause_response = message.create_response(
                message_type=MessageType.PIPELINE_PAUSE,
                content={
                    'paused_processes': paused_processes,
                    'status': ProcessingStatus.PAUSED.value
                }
            )
            await self.message_broker.publish(pause_response)

        except Exception as e:
            logger.error(f"Pipeline pause handling failed: {e}")

    async def _handle_pipeline_resume(self, message: 'ProcessingMessage') -> None:
        """
        Handle pipeline resume request

        Args:
            message: Pipeline resume message
        """
        try:
            pipeline_id = message.content.get('pipeline_id')

            # Find and resume paused processes
            resumed_processes = []
            async with self.process_lock:
                for process in self.active_processes.values():
                    if (process.pipeline_id == pipeline_id and
                            process.status == ProcessingStatus.PAUSED):
                        await self.update_process_status(
                            process.process_id,
                            ProcessingStatus.ACTIVE
                        )
                        resumed_processes.append(process.process_id)

            # Publish resume confirmation
            resume_response = message.create_response(
                message_type=MessageType.PIPELINE_RESUME,
                content={
                    'resumed_processes': resumed_processes,
                    'status': ProcessingStatus.ACTIVE.value
                }
            )
            await self.message_broker.publish(resume_response)

        except Exception as e:
            logger.error(f"Pipeline resume handling failed: {e}")

    async def _handle_pipeline_cancel(self, message: 'ProcessingMessage') -> None:
        """
        Handle pipeline cancel request

        Args:
            message: Pipeline cancel message
        """
        try:
            pipeline_id = message.content.get('pipeline_id')

            # Find and cancel active processes
            cancelled_processes = []
            async with self.process_lock:
                for process in list(self.active_processes.values()):
                    if (process.pipeline_id == pipeline_id and
                            process.status in [
                                ProcessingStatus.PENDING,
                                ProcessingStatus.ACTIVE,
                                ProcessingStatus.PAUSED
                            ]):
                        await self.update_process_status(
                            process.process_id,
                            ProcessingStatus.CANCELLED
                        )
                        cancelled_processes.append(process.process_id)

            # Publish cancel confirmation
            cancel_response = message.create_response(
                message_type=MessageType.PIPELINE_CANCEL,
                content={
                    'cancelled_processes': cancelled_processes,
                    'status': ProcessingStatus.CANCELLED.value
                }
            )
            await self.message_broker.publish(cancel_response)

        except Exception as e:
            logger.error(f"Pipeline cancel handling failed: {e}")

    async def _periodic_process_cleanup(self) -> None:
        """
        Periodic cleanup of expired or stuck processes
        """
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                current_time = datetime.now()

                async with self.process_lock:
                    # Identify processes to remove
                    expired_processes = [
                        pid for pid, process in list(self.active_processes.items())
                        if (
                            # Remove completed/failed processes after 1 hour
                                (process.status in [
                                    ProcessingStatus.COMPLETED,
                                    ProcessingStatus.FAILED,
                                    ProcessingStatus.CANCELLED
                                ] and current_time - process.end_time > timedelta(hours=1)) or
                                # Remove stuck processes
                                (process.status in [
                                    ProcessingStatus.PENDING,
                                    ProcessingStatus.ACTIVE
                                ] and current_time - process.start_time > timedelta(minutes=process.timeout))
                        )
                    ]

                    # Remove expired processes
                    for pid in expired_processes:
                        del self.active_processes[pid]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Process cleanup error: {e}")

    async def cleanup_all_processes(self) -> None:
        """
        Cleanup all active processes
        """
        async with self.process_lock:
            for process in list(self.active_processes.values()):
                # Mark as cancelled if still active
                if process.status not in [
                    ProcessingStatus.COMPLETED,
                    ProcessingStatus.FAILED,
                    ProcessingStatus.CANCELLED
                ]:
                    await self.update_process_status(
                        process.process_id,
                        ProcessingStatus.CANCELLED,
                        error="Process manager shutdown"
                    )

            # Clear active processes
            self.active_processes.clear()

    async def execute_with_tracking(
            self,
            func: Callable[..., Awaitable[Any]],
            pipeline_id: Optional[str] = None,
            handler_type: Optional[str] = None,
            **kwargs
    ) -> Any:
        """
        Execute a function with comprehensive process tracking

        Args:
            func: Async function to execute
            pipeline_id: Optional associated pipeline ID
            handler_type: Optional handler type
            **kwargs: Additional arguments to pass to the function

        Returns:
            Result of the function execution
        """
        # Create process context
        process = await self.create_process(
            pipeline_id=pipeline_id,
            handler_type=handler_type,
            metadata=kwargs.get('metadata', {})
        )

        try:
            # Update status to active
            await self.update_process_status(
                process.process_id,
                ProcessingStatus.ACTIVE
            )

            # Execute function
            result = await func(**kwargs)

            # Update status to completed
            await self.update_process_status(
                process.process_id,
                ProcessingStatus.COMPLETED
            )

            return result

        except Exception as e:
            # Update status to failed
            await self.update_process_status(
                process.process_id,
                ProcessingStatus.FAILED,
                error=str(e)
            )

            # Re-raise the exception
            raise

    def create_process_decorator(self):
        """
        Create a process tracking decorator

        Returns:
            Decorator for tracking process execution
        """
        def decorator(
                pipeline_id: Optional[str] = None,
                handler_type: Optional[str] = None
        ):
            def wrapper(func):
                @wraps(func)
                async def tracked_func(*args, **kwargs):
                    return await self.execute_with_tracking(
                        func,
                        pipeline_id=pipeline_id,
                        handler_type=handler_type,
                        **kwargs
                    )

                return tracked_func

            return wrapper

        return decorator

    def get_process_status(self, process_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific process

        Args:
            process_id: Unique process identifier

        Returns:
            Process status dictionary or None
        """
        process = self.active_processes.get(process_id)
        return process.to_dict() if process else None

    def list_active_processes(
            self,
            status: Optional[ProcessingStatus] = None,
            pipeline_id: Optional[str] = None,
            handler_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List active processes with optional filtering

        Args:
            status: Optional status to filter
            pipeline_id: Optional pipeline ID to filter
            handler_type: Optional handler type to filter

        Returns:
            List of process status dictionaries
        """
        filtered_processes = []

        for process in self.active_processes.values():
            # Apply status filter
            if status is not None and process.status != status:
                continue

            # Apply pipeline ID filter
            if pipeline_id is not None and process.pipeline_id != pipeline_id:
                continue

            # Apply handler type filter
            if handler_type is not None and process.handler_type != handler_type:
                continue

            # Add matching process
            filtered_processes.append(process.to_dict())

        return filtered_processes


async def with_process_handling(
    func: Callable[..., Awaitable[Any]]
) -> Callable[..., Awaitable[Any]]:
    """
    Standalone decorator for adding process tracking to async methods

    Args:
        func: The async method to be decorated

    Returns:
        Wrapped method with process tracking
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        from backend.core.utils.process_manager import process_manager

        # Create process context
        process = await process_manager.create_process(
            handler_type=func.__name__
        )

        try:
            # Update status to active
            await process_manager.update_process_status(
                process.process_id,
                ProcessingStatus.ACTIVE
            )

            # Execute the original method
            result = await func(*args, **kwargs)

            # Update status to completed
            await process_manager.update_process_status(
                process.process_id,
                ProcessingStatus.COMPLETED
            )

            return result

        except Exception as e:
            # Update status to failed
            await process_manager.update_process_status(
                process.process_id,
                ProcessingStatus.FAILED,
                error=str(e)
            )

            # Log the error
            logger.error(f"Process {process.process_id} failed: {str(e)}")

            # Re-raise the exception
            raise

    return wrapper

# Global process manager instance
process_manager = ProcessManager()

# Utility functions for easy access
async def initialize_process_manager(message_broker=None) -> ProcessManager:
    """
    Async initialization of global process manager

    Args:
        message_broker: Optional message broker instance

    Returns:
        Initialized ProcessManager instance
    """
    try:
        # Get or create process manager instance
        manager = ProcessManager(message_broker)

        # Start the process manager
        await manager.start()

        return manager

    except Exception as e:
        logger.error(f"Process manager initialization failed: {e}")
        raise


async def shutdown_process_manager():
    """
    Gracefully shutdown the global process manager
    """
    try:
        # Stop the process manager
        await process_manager.stop()
    except Exception as e:
        logger.error(f"Process manager shutdown failed: {e}")


# Convenience functions for existing API compatibility
async def get_active_processes(*args, **kwargs):
    """
    Get list of active processes

    Maintains compatibility with existing API
    """
    return process_manager.list_active_processes(*args, **kwargs)


async def get_process_status(process_id):
    """
    Get status of a specific process

    Maintains compatibility with existing API
    """
    return process_manager.get_process_status(process_id)


def list_active_processes(
        status: Optional[ProcessingStatus] = None,
        pipeline_id: Optional[str] = None,
        handler_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List active processes with optional filtering

    Args:
        status: Optional status to filter
        pipeline_id: Optional pipeline ID to filter
        handler_type: Optional handler type to filter

    Returns:
        List of process status dictionaries
    """
    return process_manager.list_active_processes(
        status=status,
        pipeline_id=pipeline_id,
        handler_type=handler_type
    )