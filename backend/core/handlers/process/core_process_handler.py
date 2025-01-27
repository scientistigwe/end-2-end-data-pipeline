# import asyncio
# import logging
# import uuid
# from typing import Dict, Any, Optional, List, Callable, Coroutine
# from datetime import datetime, timedelta
# from functools import wraps
#
# from backend.core.channel_handlers.base_channel_handler import (
#     BaseChannelHandler,
#     HandlerStatus,
#     MessageContext
# )
# from backend.core.messaging.broker import MessageBroker
# from backend.core.messaging.types import (
#     ProcessingMessage,
#     MessageType,
#     ProcessingStatus,
#     ProcessingStage,
#     ComponentType,
#     ModuleIdentifier
# )
# from backend.core.orchestration.pipeline_manager_helper import (
#     PipelineState,
#     PipelineStateManager
# )
#
# logger = logging.getLogger(__name__)
#
#
# class CoreProcessHandler(BaseChannelHandler):
#     """
#     Centralized process handler for managing complex asynchronous operations
#
#     Responsibilities:
#     - Coordinate process execution across the pipeline
#     - Provide comprehensive process tracking
#     - Integrate with message broker and pipeline manager
#     - Support advanced_analytics process management
#     """
#
#     def __init__(
#             self,
#             message_broker: MessageBroker,
#             state_manager: Optional[PipelineStateManager] = None,
#             max_concurrent_processes: int = 10,
#             default_timeout: float = 600.0,  # 10 minutes
#             default_max_retries: int = 3,
#             handler_name: str = "core_process_handler"
#     ):
#         """
#         Initialize the core process handler
#
#         Args:
#             message_broker: Message broker for system communication
#             state_manager: Optional pipeline state manager
#             max_concurrent_processes: Maximum number of concurrent processes
#             default_timeout: Default timeout for processes in seconds
#             default_max_retries: Default maximum retry attempts
#             handler_name: Name of the handler
#         """
#         # Initialize base handler
#         super().__init__(message_broker, handler_name)
#
#         # Process management configuration
#         self.max_concurrent_processes = max_concurrent_processes
#         self.default_timeout = default_timeout
#         self.default_max_retries = default_max_retries
#
#         # State management
#         self.state_manager = state_manager or PipelineStateManager()
#
#         # Process tracking
#         self.active_processes: Dict[str, Dict[str, Any]] = {}
#         self.process_semaphore = asyncio.Semaphore(max_concurrent_processes)
#
#         # Cleanup task reference
#         self._cleanup_task = None
#
#         # Defer async initialization
#         self._is_initialized = False
#
#     async def initialize(self):
#         """
#         Async initialization method to be called when an event loop is available
#         """
#         if not self._is_initialized:
#             try:
#                 # Setup specific message handlers
#                 await self._setup_process_handlers()
#
#                 # Start background management tasks
#                 await self.start()
#
#                 self._is_initialized = True
#             except Exception as e:
#                 logger.error(f"Async initialization error: {e}")
#                 raise
#
#     def get_process_decorator(
#             message_broker: Optional[MessageBroker] = None,
#             max_concurrent_processes: int = 10,
#             default_timeout: float = 600.0,
#             default_max_retries: int = 3
#     ):
#         """
#         Create a process decorator with predefined configuration
#
#         Args:
#             message_broker: Optional message broker instance
#             max_concurrent_processes: Maximum number of concurrent processes
#             default_timeout: Default timeout for processes
#             default_max_retries: Default maximum retry attempts
#
#         Returns:
#             Process decorator factory
#         """
#         # Use global message broker if not provided
#         if message_broker is None:
#             from backend.core.messaging.broker import MessageBroker
#             message_broker = MessageBroker()
#
#         # Create global process handler
#         global_process_handler = CoreProcessHandler(
#             message_broker,
#             max_concurrent_processes=max_concurrent_processes,
#             default_timeout=default_timeout,
#             default_max_retries=default_max_retries
#         )
#
#         # Defer initialization
#         async def init_process_handler():
#             await global_process_handler.initialize()
#
#         # Attempt to run initialization if event loop is available
#         try:
#             loop = asyncio.get_event_loop()
#             if loop.is_running():
#                 loop.create_task(init_process_handler())
#         except Exception:
#             logger.warning("Could not initialize process handler during import")
#
#     async def _setup_process_handlers(self) -> None:
#         """
#         Set up specific message handlers for process management
#         """
#         # Register callbacks for different process-related message types
#         await self.register_callback(MessageType.PIPELINE_START, self._handle_pipeline_start)
#         await self.register_callback(MessageType.PIPELINE_PAUSE, self._handle_pipeline_pause)
#         await self.register_callback(MessageType.PIPELINE_RESUME, self._handle_pipeline_resume)
#         await self.register_callback(MessageType.PIPELINE_CANCEL, self._handle_pipeline_cancel)
#
#         # Setup error handling for process-related messages
#         await self._setup_error_handling()
#
#     async def execute_process(
#             self,
#             process_func: Callable[..., Coroutine],
#             pipeline_id: Optional[str] = None,
#             stage: Optional[ProcessingStage] = None,
#             message_type: Optional[MessageType] = None,
#             **kwargs
#     ) -> Any:
#         """
#         Execute an asynchronous process with comprehensive management
#
#         Args:
#             process_func: Async function to execute
#             pipeline_id: Optional pipeline identifier
#             stage: Optional processing stage
#             message_type: Associated message type
#             **kwargs: Additional process configuration and arguments
#
#         Returns:
#             Result of the process execution
#         """
#         # Generate unique process ID
#         process_id = kwargs.get('process_id') or str(uuid.uuid4())
#
#         # Prepare pipeline state if not exists
#         if pipeline_id:
#             pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
#             if not pipeline_state:
#                 # Create new pipeline state if not exists
#                 pipeline_state = PipelineState(
#                     pipeline_id=pipeline_id,
#                     current_stage=stage or ProcessingStage.VALIDATION,
#                     status=ProcessingStatus.PENDING,
#                     metadata=kwargs.get('metadata', {})
#                 )
#                 self.state_manager.add_pipeline(pipeline_state)
#
#         # Prepare process context
#         process_context = {
#             'id': process_id,
#             'pipeline_id': pipeline_id,
#             'stage': stage,
#             'start_time': datetime.now(),
#             'status': ProcessingStatus.PENDING,
#             'metadata': kwargs.get('metadata', {}),
#             'max_retries': kwargs.get('max_retries', self.default_max_retries),
#             'timeout': kwargs.get('timeout', self.default_timeout)
#         }
#
#         # Store process context
#         self.active_processes[process_id] = process_context
#
#         async with self.process_semaphore:
#             try:
#                 # Update status to running
#                 process_context['status'] = ProcessingStatus.ACTIVE
#
#                 # Update pipeline state if exists
#                 if pipeline_id:
#                     pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
#                     if pipeline_state:
#                         pipeline_state.status = ProcessingStatus.RUNNING
#                         pipeline_state.current_progress = 0.1  # Initial progress
#
#                 # Publish process start event
#                 if message_type or pipeline_id:
#                     await self._publish_process_start(
#                         process_id,
#                         pipeline_id,
#                         stage,
#                         message_type or MessageType.PIPELINE_START
#                     )
#
#                 # Execute with retry and timeout
#                 result = await self._execute_with_retry(
#                     process_func,
#                     process_id,
#                     process_context,
#                     **kwargs
#                 )
#
#                 # Update status to completed
#                 process_context['status'] = ProcessingStatus.COMPLETED
#                 process_context['end_time'] = datetime.now()
#
#                 # Update pipeline state if exists
#                 if pipeline_id:
#                     pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
#                     if pipeline_state:
#                         pipeline_state.status = ProcessingStatus.COMPLETED
#                         pipeline_state.current_progress = 1.0
#                         pipeline_state.record_stage_completion(stage.value if stage else 'unknown')
#
#                 # Publish completion event
#                 if message_type or pipeline_id:
#                     await self._publish_process_complete(
#                         process_id,
#                         pipeline_id,
#                         stage,
#                         message_type or MessageType.PIPELINE_START,
#                         result
#                     )
#
#                 return result
#
#             except Exception as e:
#                 # Handle process failure
#                 process_context['status'] = ProcessingStatus.FAILED
#                 process_context['error'] = str(e)
#                 process_context['end_time'] = datetime.now()
#
#                 # Update pipeline state if exists
#                 if pipeline_id:
#                     pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
#                     if pipeline_state:
#                         pipeline_state.status = ProcessingStatus.FAILED
#                         pipeline_state.add_error(str(e))
#
#                 # Publish error event
#                 if message_type or pipeline_id:
#                     error_message = ProcessingMessage(
#                         source_identifier=self.module_id,
#                         target_identifier=ModuleIdentifier(
#                             component_name="pipeline_manager",
#                             component_type=ComponentType.MANAGER,
#                             method_name="process_error"
#                         ),
#                         message_type=MessageType.PIPELINE_ERROR,
#                         content={
#                             'process_id': process_id,
#                             'pipeline_id': pipeline_id,
#                             'stage': stage.value if stage else None,
#                             'error': str(e)
#                         }
#                     )
#                     await self._publish_process_error(error_message, str(e))
#
#                 raise
#             finally:
#                 # Cleanup process after completion or failure
#                 if process_context['status'] in [
#                     ProcessingStatus.COMPLETED,
#                     ProcessingStatus.FAILED
#                 ]:
#                     await self._cleanup_process(process_id)
#
#     async def _publish_process_start(
#             self,
#             process_id: str,
#             pipeline_id: Optional[str],
#             stage: Optional[ProcessingStage],
#             message_type: MessageType
#     ):
#         """
#         Publish process start event
#
#         Args:
#             process_id: Unique process identifier
#             pipeline_id: Associated pipeline ID
#             stage: Processing stage
#             message_type: Type of process message
#         """
#         start_message = ProcessingMessage(
#             source_identifier=ModuleIdentifier(
#                 component_name="core_process_handler",
#                 component_type=ComponentType.HANDLER,  # Use HANDLER component type
#                 method_name="process_start"
#             ),
#             target_identifier=ModuleIdentifier(
#                 component_name="pipeline_manager",
#                 component_type=ComponentType.MANAGER,  # Use MANAGER component type
#                 method_name="process_tracking"
#             ),
#             message_type=message_type,
#             content={
#                 'process_id': process_id,
#                 'pipeline_id': pipeline_id,
#                 'stage': stage.value if stage else None,
#                 'status': ProcessingStatus.ACTIVE.value
#             }
#         )
#         await self.message_broker.publish(start_message)
#
#     async def _publish_process_complete(
#             self,
#             process_id: str,
#             pipeline_id: Optional[str],
#             stage: Optional[ProcessingStage],
#             message_type: MessageType,
#             result: Any
#     ):
#         """
#         Publish process completion event
#
#         Args:
#             process_id: Unique process identifier
#             pipeline_id: Associated pipeline ID
#             stage: Processing stage
#             message_type: Type of process message
#             result: Process execution result
#         """
#         complete_message = ProcessingMessage(
#             source_identifier=self.module_id,
#             target_identifier=ModuleIdentifier(
#                 component_name="pipeline_manager",
#                 component_type=ComponentType.MANAGER,
#                 method_name="process_tracking"
#             ),
#             message_type=message_type,
#             content={
#                 'process_id': process_id,
#                 'pipeline_id': pipeline_id,
#                 'stage': stage.value if stage else None,
#                 'status': ProcessingStatus.COMPLETED.value,
#                 'result': result
#             }
#         )
#         await self.message_broker.publish(complete_message)
#
#     async def _execute_with_retry(
#             self,
#             process_func: Callable[..., Coroutine],
#             process_id: str,
#             context: Dict[str, Any],
#             **kwargs
#     ) -> Any:
#         """
#         Execute process with retry and timeout logic
#
#         Args:
#             process_func: Async function to execute
#             process_id: Unique process identifier
#             context: Process context dictionary
#             **kwargs: Additional process arguments
#
#         Returns:
#             Result of process execution
#         """
#         last_exception = None
#
#         for attempt in range(context['max_retries'] + 1):
#             try:
#                 # Update retry context
#                 context['current_attempt'] = attempt + 1
#
#                 # Apply exponential backoff
#                 if attempt > 0:
#                     await asyncio.sleep(2 ** attempt)
#
#                 # Execute with timeout
#                 result = await asyncio.wait_for(
#                     process_func(**{k: v for k, v in kwargs.items() if k != 'metadata'}),
#                     timeout=context['timeout']
#                 )
#                 return result
#
#             except asyncio.TimeoutError as e:
#                 logger.warning(f"Process {process_id} timed out on attempt {attempt + 1}")
#                 last_exception = e
#                 context['last_error'] = f"Timeout after {context['timeout']}s"
#
#             except Exception as e:
#                 logger.error(f"Process {process_id} failed on attempt {attempt + 1}: {str(e)}")
#                 last_exception = e
#                 context['last_error'] = str(e)
#
#         # Raise final exception if all retries fail
#         raise last_exception or RuntimeError(
#             f"Process {process_id} failed after {context['max_retries']} attempts"
#         )
#
#     async def _cleanup_process(self, process_id: str):
#         """
#         Cleanup process resources
#
#         Args:
#             process_id: Unique process identifier to cleanup
#         """
#         try:
#             # Remove process from active processes after delay
#             await asyncio.sleep(60)  # Keep record for 1 minute
#             if process_id in self.active_processes:
#                 del self.active_processes[process_id]
#             if process_id in self._active_contexts:
#                 del self._active_contexts[process_id]
#         except Exception as e:
#             logger.error(f"Error cleaning up process {process_id}: {str(e)}")
#
#     def get_process_status(self, process_id: str) -> Optional[Dict[str, Any]]:
#         """
#         Retrieve detailed status for a specific process
#
#         Args:
#             process_id: Unique process identifier
#
#         Returns:
#             Detailed process status or None if not found
#         """
#         process = self.active_processes.get(process_id)
#         if not process:
#             return None
#
#         return {
#             'process_id': process_id,
#             'pipeline_id': process.get('pipeline_id'),
#             'stage': process.get('stage'),
#             'status': process.get('status', ProcessingStatus.PENDING).value,
#             'start_time': process.get('start_time'),
#             'end_time': process.get('end_time'),
#             'current_attempt': process.get('current_attempt', 0),
#             'max_retries': process.get('max_retries', self.default_max_retries),
#             'timeout': process.get('timeout', self.default_timeout),
#             'metadata': process.get('metadata', {}),
#             'last_error': process.get('last_error')
#         }
#
#     def list_active_processes(
#             self,
#             status: Optional[ProcessingStatus] = None,
#             pipeline_id: Optional[str] = None,
#             stage: Optional[ProcessingStage] = None
#     ) -> List[Dict[str, Any]]:
#         """
#         List active processes with optional filtering
#
#         Args:
#             status: Optional status to filter processes
#             pipeline_id: Optional pipeline ID to filter
#             stage: Optional processing stage to filter
#
#         Returns:
#             List of active process statuses
#         """
#         filtered_processes = []
#
#         for pid, process in self.active_processes.items():
#             # Apply status filter if provided
#             if status and process.get('status') != status:
#                 continue
#
#             # Apply pipeline ID filter if provided
#             if pipeline_id and process.get('pipeline_id') != pipeline_id:
#                 continue
#
#             # Apply stage filter if provided
#             if stage and process.get('stage') != stage:
#                 continue
#
#             process_status = self.get_process_status(pid)
#             if process_status:
#                 filtered_processes.append(process_status)
#
#         return filtered_processes
#
#     async def _handle_pipeline_start(self, message: ProcessingMessage):
#         """
#         Handle pipeline start request
#
#         Args:
#             message: Pipeline start message
#         """
#         try:
#             pipeline_id = message.content.get('pipeline_id')
#             stage = message.content.get('stage')
#
#             # Validate and start pipeline process
#             process_id = str(uuid.uuid4())
#
#             # Ensure pipeline state exists
#             if pipeline_id:
#                 pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
#                 if not pipeline_state:
#                     pipeline_state = PipelineState(
#                         pipeline_id=pipeline_id,
#                         current_stage=ProcessingStage(stage) if stage else ProcessingStage.INITIAL_VALIDATION,
#                         status=ProcessingStatus.RUNNING
#                     )
#                     self.state_manager.add_pipeline(pipeline_state)
#
#             # Respond with pipeline start confirmation
#             response = message.create_response(
#                 message_type=MessageType.PIPELINE_START,
#                 content={
#                     'process_id': process_id,
#                     'pipeline_id': pipeline_id,
#                     'status': ProcessingStatus.ACTIVE.value
#                 }
#             )
#
#             # Send response via message broker
#             await self.message_broker.publish(response)
#
#         except Exception as e:
#             # Publish error response
#             error_message = message.create_response(
#                 message_type=MessageType.PIPELINE_ERROR,
#                 content={
#                     'error': str(e),
#                     'status': ProcessingStatus.FAILED.value
#                 }
#             )
#             await self.message_broker.publish(error_message)
#
#     async def _handle_pipeline_pause(self, message: ProcessingMessage):
#         """
#         Handle pipeline pause request
#
#         Args:
#             message: Pipeline pause message
#         """
#         try:
#             pipeline_id = message.content.get('pipeline_id')
#
#             # Find and pause active processes for pipeline
#             paused_processes = [
#                 pid for pid, process in self.active_processes.items()
#                 if process.get('pipeline_id') == pipeline_id
#             ]
#
#             # Update process statuses
#             for pid in paused_processes:
#                 self.active_processes[pid]['status'] = ProcessingStatus.PAUSED
#
#             # Update pipeline state
#             if pipeline_id:
#                 pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
#                 if pipeline_state:
#                     pipeline_state.status = ProcessingStatus.PAUSED
#
#             # Respond with pause confirmation
#             response = message.create_response(
#                 message_type=MessageType.PIPELINE_PAUSE,
#                 content={
#                     'paused_processes': paused_processes,
#                     'status': ProcessingStatus.PAUSED.value
#                 }
#             )
#
#             # Send response via message broker
#             await self.message_broker.publish(response)
#         except Exception as e:
#             # Publish error response
#             error_message = message.create_response(
#                 message_type=MessageType.PIPELINE_ERROR,
#                 content={
#                     'error': str(e),
#                     'status': ProcessingStatus.FAILED.value
#                 }
#             )
#             await self.message_broker.publish(error_message)
#
#     async def _handle_pipeline_resume(self, message: ProcessingMessage):
#         """
#         Handle pipeline resume request
#
#         Args:
#             message: Pipeline resume message
#         """
#         try:
#             pipeline_id = message.content.get('pipeline_id')
#
#             # Find and resume paused processes for pipeline
#             resumed_processes = [
#                 pid for pid, process in self.active_processes.items()
#                 if (process.get('pipeline_id') == pipeline_id and
#                     process.get('status') == ProcessingStatus.PAUSED)
#             ]
#
#             # Update process statuses
#             for pid in resumed_processes:
#                 self.active_processes[pid]['status'] = ProcessingStatus.ACTIVE
#
#             # Update pipeline state
#             if pipeline_id:
#                 pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
#                 if pipeline_state:
#                     pipeline_state.status = ProcessingStatus.RUNNING
#
#             # Respond with resume confirmation
#             response = message.create_response(
#                 message_type=MessageType.PIPELINE_RESUME,
#                 content={
#                     'resumed_processes': resumed_processes,
#                     'status': ProcessingStatus.ACTIVE.value
#                 }
#             )
#
#             # Send response via message broker
#             await self.message_broker.publish(response)
#
#         except Exception as e:
#             # Publish error response
#             error_message = message.create_response(
#                 message_type=MessageType.PIPELINE_ERROR,
#                 content={
#                     'error': str(e),
#                     'status': ProcessingStatus.FAILED.value
#                 }
#             )
#             await self.message_broker.publish(error_message)
#
#     async def _handle_pipeline_cancel(self, message: ProcessingMessage):
#         """
#         Handle pipeline cancel request
#
#         Args:
#             message: Pipeline cancel message
#         """
#         try:
#             pipeline_id = message.content.get('pipeline_id')
#
#             # Find and cancel active processes for pipeline
#             cancelled_processes = [
#                 pid for pid, process in self.active_processes.items()
#                 if (process.get('pipeline_id') == pipeline_id and
#                     process.get('status') in [
#                         ProcessingStatus.PENDING,
#                         ProcessingStatus.ACTIVE,
#                         ProcessingStatus.PAUSED
#                     ])
#             ]
#
#             # Update process statuses
#             for pid in cancelled_processes:
#                 self.active_processes[pid]['status'] = ProcessingStatus.CANCELLED
#                 # Asynchronously cleanup
#                 asyncio.create_task(self._cleanup_process(pid))
#
#             # Update pipeline state
#             if pipeline_id:
#                 pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
#                 if pipeline_state:
#                     pipeline_state.status = ProcessingStatus.CANCELLED
#
#             # Respond with cancel confirmation
#             response = message.create_response(
#                 message_type=MessageType.PIPELINE_CANCEL,
#                 content={
#                     'cancelled_processes': cancelled_processes,
#                     'status': ProcessingStatus.CANCELLED.value
#                 }
#             )
#
#             # Send response via message broker
#             await self.message_broker.publish(response)
#
#         except Exception as e:
#             # Publish error response
#             error_message = message.create_response(
#                 message_type=MessageType.PIPELINE_ERROR,
#                 content={
#                     'error': str(e),
#                     'status': ProcessingStatus.FAILED.value
#                 }
#             )
#             await self.message_broker.publish(error_message)
#
#     async def start(self):
#         """
#         Start background management tasks
#         """
#         # Start periodic cleanup task
#         self._cleanup_task = asyncio.create_task(self._periodic_process_cleanup())
#
#     async def stop(self):
#         """
#         Gracefully stop all background tasks
#         """
#         if self._cleanup_task:
#             self._cleanup_task.cancel()
#             try:
#                 await self._cleanup_task
#             except asyncio.CancelledError:
#                 pass
#
#     async def _periodic_process_cleanup(self):
#         """
#         Background task for cleaning up expired or stuck processes
#         """
#         while True:
#             try:
#                 await asyncio.sleep(300)  # Check every 5 minutes
#                 current_time = datetime.now()
#
#                 # Identify processes to remove
#                 expired_processes = [
#                     pid for pid, process in list(self.active_processes.items())
#                     if (
#                         # Remove completed/failed processes after 1 hour
#                             (process.get('status') in [
#                                 ProcessingStatus.COMPLETED,
#                                 ProcessingStatus.FAILED,
#                                 ProcessingStatus.CANCELLED
#                             ] and current_time - process.get('end_time', current_time) > timedelta(hours=1)) or
#                             # Remove stuck running processes
#                             (process.get('status') == ProcessingStatus.ACTIVE and
#                              current_time - process.get('start_time', current_time) >
#                              timedelta(minutes=process.get('timeout', self.default_timeout)))
#                     )
#                 ]
#
#                 # Remove expired processes
#                 for pid in expired_processes:
#                     await self._cleanup_process(pid)
#
#             except asyncio.CancelledError:
#                 break
#             except Exception as e:
#                 logger.error(f"Process cleanup loop error: {str(e)}")
#
#
# def get_process_decorator(
#         message_broker: Optional[MessageBroker] = None,
#         max_concurrent_processes: int = 10,
#         default_timeout: float = 600.0,
#         default_max_retries: int = 3
# ):
#     """
#     Create a process decorator with predefined configuration
#
#     Args:
#         message_broker: Optional message broker instance
#         max_concurrent_processes: Maximum number of concurrent processes
#         default_timeout: Default timeout for processes
#         default_max_retries: Default maximum retry attempts
#
#     Returns:
#         Process decorator factory
#     """
#     # Use global message broker if not provided
#     if message_broker is None:
#         from backend.core.messaging.broker import MessageBroker
#         message_broker = MessageBroker()
#
#     # Create global process handler
#     global_process_handler = CoreProcessHandler(
#         message_broker,
#         max_concurrent_processes=max_concurrent_processes,
#         default_timeout=default_timeout,
#         default_max_retries=default_max_retries
#     )
#
#     def process_decorator(
#             message_type: Optional[MessageType] = None,
#             pipeline_id: Optional[str] = None,
#             stage: Optional[ProcessingStage] = None
#     ):
#         """
#         Decorator for process management
#
#         Args:
#             message_type: Associated message type
#             pipeline_id: Pipeline identifier
#             stage: Processing stage
#         """
#
#         def decorator(func):
#             @wraps(func)
#             async def wrapper(*args, **kwargs):
#                 # Prepare process context
#                 process_kwargs = {
#                     'metadata': kwargs.get('metadata', {}),
#                     'timeout': kwargs.get('timeout', global_process_handler.default_timeout),
#                     'max_retries': kwargs.get('max_retries', global_process_handler.default_max_retries)
#                 }
#
#                 # Use provided or generate pipeline ID
#                 current_pipeline_id = pipeline_id or process_kwargs['metadata'].get('pipeline_id')
#
#                 # Execute process
#                 return await global_process_handler.execute_process(
#                     func,
#                     pipeline_id=current_pipeline_id,
#                     stage=stage,
#                     message_type=message_type,
#                     **process_kwargs
#                 )
#
#             return wrapper
#
#         return decorator
#
#     return process_decorator
#
#
# # Global process decorator
# process = get_process_decorator()
