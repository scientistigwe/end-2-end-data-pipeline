Message Broker Architecture Refactoring Guide
Core Principles
The message broker architecture establishes a system where all components communicate exclusively through messages, eliminating direct dependencies. This approach creates a more maintainable, scalable, and resilient system. Each component operates independently, knowing only about the messages it sends and receives.
Component Types and Their Roles
Managers
Managers orchestrate high-level workflows and maintain minimal state for active processes. They:

Subscribe to workflow-related messages
Maintain process contexts
Coordinate between different components through messages
Handle error recovery and cleanup

Handlers
Handlers process specific tasks within their domain. They:

Subscribe to task-specific messages
Execute business logic
Coordinate with processors
Report progress and results through messages

Processors
Processors perform actual data processing. They:

Subscribe to processing requests
Execute computations
Report results through messages
Handle processing-specific errors

Refactoring Process
Step 1: Context Definition
First, define the component's context class in event_types.py:
pythonCopy@dataclass
class ComponentContext:
    """State tracking for component operations"""
    request_id: str
    correlation_id: str
    state: ComponentState
    metadata: Dict[str, Any]
    metrics: ComponentMetrics
    created_at: datetime
    updated_at: datetime
Step 2: Message Types
Define all message types related to the component:
pythonCopyclass MessageType(Enum):
    # Requests
    COMPONENT_START_REQUEST = "component.start.request"
    COMPONENT_PROCESS_REQUEST = "component.process.request"
    
    # Status Updates
    COMPONENT_STATUS_UPDATE = "component.status.update"
    COMPONENT_COMPLETE = "component.complete"
    
    # Error Handling
    COMPONENT_ERROR = "component.error"
    COMPONENT_RETRY_REQUEST = "component.retry.request"
Step 3: Component Structure
Implement the basic component structure:
pythonCopyclass ComponentName:
    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.active_processes = {}  # Track active processes
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        handlers = {
            MessageType.COMPONENT_START_REQUEST: self._handle_start_request,
            MessageType.COMPONENT_PROCESS_REQUEST: self._handle_process_request
        }
        
        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.component_name,
                f"{message_type.value}.#",
                handler
            )
Message Communication Pattern
Publishing Messages
When publishing messages:

Include correlation ID for tracking
Specify clear source and target components
Include relevant context in message content

pythonCopyasync def _publish_message(self, message_type: MessageType, content: Dict[str, Any], target: str) -> None:
    await self.message_broker.publish(ProcessingMessage(
        message_type=message_type,
        content=content,
        metadata=MessageMetadata(
            correlation_id=self.context.correlation_id,
            source_component=self.component_name,
            target_component=target
        )
    ))
Subscribing to Messages
When subscribing to messages:

Use specific patterns to receive only relevant messages
Validate message content before processing
Handle errors appropriately

pythonCopyasync def _handle_message(self, message: ProcessingMessage) -> None:
    try:
        if not self._validate_message(message):
            logger.error(f"Invalid message received: {message}")
            return
            
        await self._process_message(message)
        
    except Exception as e:
        await self._handle_error(message, e)
Error Handling Pattern
Implement comprehensive error handling:

Detect and classify errors
Attempt recovery when appropriate
Propagate unrecoverable errors
Maintain system state consistency

pythonCopyasync def _handle_error(self, message: ProcessingMessage, error: Exception) -> None:
    error_context = {
        'correlation_id': message.metadata.correlation_id,
        'error_type': type(error).__name__,
        'error_message': str(error)
    }
    
    await self._publish_message(
        MessageType.COMPONENT_ERROR,
        error_context,
        "error_handler"
    )
State Management Pattern
Maintain minimal but sufficient state:

Track only essential process information
Update state through well-defined transitions
Ensure state consistency across components
Clean up state appropriately

pythonCopyasync def _update_state(self, new_state: ComponentState) -> None:
    self.context.state = new_state
    self.context.updated_at = datetime.now()
    
    await self._publish_message(
        MessageType.COMPONENT_STATUS_UPDATE,
        {'new_state': new_state.value},
        "state_tracker"
    )
Implementation Checklist
For each component:

Define component-specific context and message types
Implement message handlers for all relevant message types
Remove direct component calls
Add proper error handling
Implement state management
Add cleanup procedures

Best Practices

Message Naming:

Use consistent naming patterns
Include component domain in message types
Make message purposes clear


Error Handling:

Implement retry mechanisms
Log errors comprehensively
Maintain system stability


State Management:

Keep state minimal
Update state atomically
Clean up state properly


Testing:

Test message flows
Verify error handling
Ensure state consistency



This guide provides a framework for systematically refactoring components to use message broker architecture. Following these patterns ensures consistent implementation across the system while maintaining component independence and system reliability.