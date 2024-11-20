# core/orchestration/conductor.py

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from backend.core.messaging.broker import MessageBroker
from backend.core.config.config_manager import ConfigurationManager
from backend.core.messaging.types import (
    ModuleIdentifier,
    ProcessingMessage,
    MessageType,
    ProcessingStatus
)

@dataclass
class ProcessingFlow:
    """Represents a single processing flow configuration"""
    source_module: ModuleIdentifier
    target_module: ModuleIdentifier
    conditions: Dict[str, Any]
    priority: int


class DataConductor:
    """Manages data flow routing and processing paths"""

    def __init__(self, message_broker: MessageBroker, config_manager: ConfigurationManager = None):
        self.config_manager = config_manager or ConfigurationManager()
        # Use configuration for dynamic settings
        max_flows = self.config_manager.get('max_processing_flows', 10)
        flow_retention_period = self.config_manager.get('flow_retention_hours', 24)
        self.message_broker = message_broker
        self.processing_flows: Dict[str, List[ProcessingFlow]] = {}
        self.active_flows: Dict[str, Dict[str, Any]] = {}
        self.metrics = {
            'total_flows': 0,
            'successful_flows': 0,
            'failed_flows': 0
        }

    def register_flow(
            self,
            source_module: ModuleIdentifier,
            target_module: ModuleIdentifier,
            conditions: Optional[Dict[str, Any]] = None,
            priority: int = 0
    ) -> None:
        """Register a processing flow path"""
        source_tag = source_module.get_tag()

        if source_tag not in self.processing_flows:
            self.processing_flows[source_tag] = []

        flow = ProcessingFlow(
            source_module=source_module,
            target_module=target_module,
            conditions=conditions or {},
            priority=priority
        )

        self.processing_flows[source_tag].append(flow)

    def get_next_module(self, message: ProcessingMessage) -> Optional[ModuleIdentifier]:
        """Determine the next processing module based on message context"""
        if not message.source_identifier:
            return None

        source_tag = message.source_identifier.get_tag()
        if source_tag not in self.processing_flows:
            return None

        eligible_flows = sorted(
            self.processing_flows[source_tag],
            key=lambda x: x.priority,
            reverse=True
        )

        for flow in eligible_flows:
            if self._check_conditions(flow.conditions, message.content):
                return flow.target_module

        return None

    def _check_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if message context matches flow conditions"""
        for key, value in conditions.items():
            if key not in context:
                return False
            if callable(value):
                if not value(context[key]):
                    return False
            elif context[key] != value:
                return False
        return True

    def handle_flow_completion(self, message: ProcessingMessage) -> None:
        """Handle flow completion and update metrics"""
        flow_id = message.message_id
        if flow_id in self.active_flows:
            if message.status == ProcessingStatus.COMPLETED:
                self.metrics['successful_flows'] += 1
            else:
                self.metrics['failed_flows'] += 1
            del self.active_flows[flow_id]