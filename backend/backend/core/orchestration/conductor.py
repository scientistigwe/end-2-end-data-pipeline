# core/orchestration/conductor.py

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging
from backend.core.messaging.broker import MessageBroker
from backend.core.config.config_manager import ConfigurationManager
from backend.core.messaging.types import (
    ModuleIdentifier,
    ProcessingMessage,
    MessageType,
    ProcessingStatus
)
from backend.core.registry.component_registry import ComponentRegistry

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class ProcessingFlow:
    """Represents a single processing flow configuration"""
    source_module: ModuleIdentifier
    target_module: ModuleIdentifier
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    execution_count: int = 0


@dataclass
class FlowMetrics:
    """Tracks metrics for flow execution"""
    total_flows: int = 0
    successful_flows: int = 0
    failed_flows: int = 0
    avg_processing_time: float = 0.0
    active_flows: int = 0


class DataConductor:
    """
    Manages data flow routing and processing paths with enhanced subscription handling
    and consistent messaging patterns.
    """

    def __init__(self, message_broker: MessageBroker, config_manager: Optional[ConfigurationManager] = None):
        self.config_manager = config_manager or ConfigurationManager()
        self.message_broker = message_broker
        self.registry = ComponentRegistry()

        # Initialize module identifiers with instance UUID
        self.module_id = ModuleIdentifier(
            "DataConductor",
            "manage_flow",
            self.registry.get_component_uuid("DataConductor")
        )
        self.flow_completed_module = ModuleIdentifier("DataConductor", "flow_completed")
        self.flow_status_module = ModuleIdentifier("DataConductor", "flow_status")

        # Core data structures
        self.processing_flows: Dict[str, List[ProcessingFlow]] = {}
        self.active_flows: Dict[str, Dict[str, Any]] = {}
        self.metrics = FlowMetrics()

        # Load configuration
        self._load_configuration()

        # Initialize subscriptions
        self._initialize_subscriptions()

    def _load_configuration(self) -> None:
        """Load and set up configuration parameters"""
        self.max_flows = self.config_manager.get('max_processing_flows', 10)
        self.flow_retention_hours = self.config_manager.get('flow_retention_hours', 24)
        self.retry_attempts = self.config_manager.get('retry_attempts', 3)

        logger.info(f"Initialized with max_flows: {self.max_flows}, "
                    f"retention_hours: {self.flow_retention_hours}")

    def _initialize_subscriptions(self) -> None:
        """Initialize all required message broker subscriptions"""
        try:
            # Register modules
            for module in [self.module_id, self.flow_completed_module, self.flow_status_module]:
                self.message_broker.register_module(module)
                logger.info(f"Registered module: {module.get_tag()}")

            # Set up subscriptions
            subscriptions = [
                (self.module_id.get_tag(), self._handle_flow_message),
                (self.flow_completed_module.get_tag(), self._handle_flow_completion),
                (self.flow_status_module.get_tag(), self._handle_flow_status)
            ]

            for tag, handler in subscriptions:
                self.message_broker.subscribe_to_module(tag, handler)
                logger.info(f"Subscribed to {tag} with handler {handler.__name__}")

        except Exception as e:
            logger.error(f"Error initializing subscriptions: {str(e)}")
            raise

    def register_flow(
            self,
            source_module: ModuleIdentifier,
            target_module: ModuleIdentifier,
            conditions: Optional[Dict[str, Any]] = None,
            priority: int = 0
    ) -> None:
        """Register a processing flow path with validation"""
        try:
            source_tag = source_module.get_tag()

            # Validate modules are registered
            if not self.message_broker.is_module_registered(source_module.get_tag()):
                raise ValueError(f"Source module {source_tag} is not registered")

            if not self.message_broker.is_module_registered(target_module.get_tag()):
                raise ValueError(f"Target module {target_module.get_tag()} is not registered")

            # Initialize flow list if needed
            if source_tag not in self.processing_flows:
                self.processing_flows[source_tag] = []

            # Create and register flow
            flow = ProcessingFlow(
                source_module=source_module,
                target_module=target_module,
                conditions=conditions or {},
                priority=priority
            )

            self.processing_flows[source_tag].append(flow)
            logger.info(f"Registered flow from {source_tag} to {target_module.get_tag()}")

        except Exception as e:
            logger.error(f"Error registering flow: {str(e)}")
            raise

    def _handle_flow_message(self, message: ProcessingMessage) -> None:
        """Handle incoming flow control messages"""
        try:
            if not message.content.get('action'):
                logger.warning("Received message without action specification")
                return

            actions = {
                'get_next_module': self._process_next_module_request,
                'register_flow': self._process_flow_registration,
                'update_flow': self._process_flow_update
            }

            action = message.content['action']
            if action in actions:
                actions[action](message)
            else:
                logger.warning(f"Unknown action received: {action}")

        except Exception as e:
            logger.error(f"Error handling flow message: {str(e)}")
            self._publish_error_message(message, str(e))

    def _handle_flow_completion(self, message: ProcessingMessage) -> None:
        """Handle flow completion messages with metrics updates"""
        try:
            flow_id = message.message_id
            if flow_id not in self.active_flows:
                logger.warning(f"Received completion for unknown flow: {flow_id}")
                return

            # Update metrics
            if message.content.get('status') == ProcessingStatus.COMPLETED:
                self.metrics.successful_flows += 1
            else:
                self.metrics.failed_flows += 1

            # Calculate processing time
            flow_data = self.active_flows[flow_id]
            processing_time = (datetime.now() - flow_data['start_time']).total_seconds()

            # Update average processing time
            self._update_processing_time_metrics(processing_time)

            # Cleanup
            del self.active_flows[flow_id]
            self.metrics.active_flows -= 1

            logger.info(f"Flow {flow_id} completed with status: {message.content.get('status')}")

        except Exception as e:
            logger.error(f"Error handling flow completion: {str(e)}")

    def _handle_flow_status(self, message: ProcessingMessage) -> None:
        """Handle flow status update messages"""
        try:
            flow_id = message.content.get('flow_id')
            if not flow_id:
                logger.warning("Received status update without flow_id")
                return

            if flow_id in self.active_flows:
                self.active_flows[flow_id].update({
                    'status': message.content.get('status'),
                    'last_updated': datetime.now()
                })

                logger.info(f"Updated status for flow {flow_id}: {message.content.get('status')}")
            else:
                logger.warning(f"Status update for unknown flow: {flow_id}")

        except Exception as e:
            logger.error(f"Error handling flow status: {str(e)}")

    def _update_processing_time_metrics(self, processing_time: float) -> None:
        """Update average processing time metrics"""
        total_flows = self.metrics.successful_flows + self.metrics.failed_flows
        if total_flows > 0:
            current_avg = self.metrics.avg_processing_time
            self.metrics.avg_processing_time = (
                    (current_avg * (total_flows - 1) + processing_time) / total_flows
            )

    def _publish_error_message(self, original_message: ProcessingMessage, error_details: str) -> None:
        """Publish error message to message broker"""
        error_message = ProcessingMessage(
            source_identifier=self.module_id,
            message_type=MessageType.ERROR,
            content={
                'original_message_id': original_message.message_id,
                'error_details': error_details,
                'timestamp': datetime.now().isoformat()
            }
        )
        self.message_broker.publish(error_message)

    def get_metrics(self) -> Dict[str, Any]:
        """Return current metrics"""
        return {
            'total_flows': self.metrics.total_flows,
            'successful_flows': self.metrics.successful_flows,
            'failed_flows': self.metrics.failed_flows,
            'active_flows': self.metrics.active_flows,
            'avg_processing_time': self.metrics.avg_processing_time
        }

    def get_initial_route(self) -> ModuleIdentifier:
        """Return the initial module for new data processing"""
        try:
            return ModuleIdentifier(
                "DataQualityReport",
                "generate_report",
                self.registry.get_component_uuid("DataQualityReport")
            )
        except Exception as e:
            logger.error(f"Error getting initial route: {str(e)}")
            # Return a default route or raise the error based on your needs
            raise
