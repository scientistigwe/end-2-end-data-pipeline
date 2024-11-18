# core/orchestration/conductor.py

from typing import Dict, List, Any, Optional
from backend.backend.core.messaging.broker import MessageBroker
from backend.backend.core.messaging.types import (
    ProcessingMessage,
    ModuleIdentifier,
    MessageType,
    ProcessingStatus,
)

class DataConductor:
    """Enhanced conductor for managing module interactions and data flow"""

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.module_graph: Dict[str, List[str]] = {}
        self.active_flows: Dict[str, Dict[str, Any]] = {}
        self.stage_handlers: Dict[str, callable] = {}

    def register_module_flow(self, source_module: ModuleIdentifier,
                             target_modules: List[ModuleIdentifier],
                             conditions: Optional[Dict[str, Any]] = None):
        """Register possible flow paths between modules"""
        source_tag = source_module.get_tag()
        if source_tag not in self.module_graph:
            self.module_graph[source_tag] = []

        for target in target_modules:
            self.module_graph[source_tag].append({
                'target': target.get_tag(),
                'conditions': conditions or {}
            })

    def handle_message(self, message: ProcessingMessage):
        """Process incoming messages and determine next steps"""
        source_tag = message.source_identifier.get_tag()

        # For recommendations requiring decisions
        if message.message_type == MessageType.RECOMMENDATION:
            self.active_flows[message.message_id] = {
                'source': source_tag,
                'status': ProcessingStatus.AWAITING_DECISION
            }
            return

        # For completed stages, determine next module
        if message.status == ProcessingStatus.COMPLETED:
            next_modules = self._get_next_modules(source_tag, message.content)
            for next_module in next_modules:
                self._route_to_module(message, next_module)

    def _get_next_modules(self, source_tag: str, context: Dict[str, Any]) -> List[str]:
        """Determine next modules based on flow rules and context"""
        next_modules = []
        if source_tag in self.module_graph:
            for flow in self.module_graph[source_tag]:
                if self._check_conditions(flow['conditions'], context):
                    next_modules.append(flow['target'])
        return next_modules

    def _check_conditions(self, conditions: Dict[str, Any],
                          context: Dict[str, Any]) -> bool:
        """Check if conditions are met for module transition"""
        for key, value in conditions.items():
            if key not in context or context[key] != value:
                return False
        return True

    def _route_to_module(self, source_message: ProcessingMessage,
                         target_module_tag: str):
        """Route data to the next module"""
        if target_module_tag in self.stage_handlers:
            self.stage_handlers[target_module_tag](source_message)


# Example usage
def example_setup():
    # Create message broker and conductor
    broker = MessageBroker()
    conductor = DataConductor(broker)

    # Register modules
    file_ingest = ModuleIdentifier("FileSystem", "ingest_csv")
    staging = ModuleIdentifier("StagingArea", "stage_data")
    eda = ModuleIdentifier("DataQuality", "generate_report")

    # Register flow
    conductor.register_module_flow(
        file_ingest,
        [staging],
        {'status': 'success'}
    )
    conductor.register_module_flow(
        staging,
        [eda],
        {'quality_check': 'passed'}
    )

    # Example message flow
    ingest_msg = ProcessingMessage(
        source_identifier=file_ingest,
        message_type=MessageType.STATUS_UPDATE,
        content={'file_path': 'data.csv', 'status': 'success'},
        status=ProcessingStatus.COMPLETED
    )

    # Handle the message
    conductor.handle_message(ingest_msg)