# backend/core/managers/routing_manager.py

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.base.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage, ProcessingStatus

# Channel Handler
from backend.core.channel_handlers.routing_handler import RoutingChannelHandler

logger = logging.getLogger(__name__)


class RouteType(Enum):
    """Types of routing flows"""
    SEQUENTIAL = "sequential"  # Default flow through pipeline phases
    PARALLEL = "parallel"  # Parallel processing paths
    CONDITIONAL = "conditional"  # Decision-based routing


@dataclass
class RouteState:
    """Tracks routing state for a pipeline"""
    pipeline_id: str
    current_nodes: Set[str]  # Currently active nodes
    completed_nodes: Set[str]  # Completed processing nodes
    route_type: RouteType
    status: ProcessingStatus
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None


class RoutingManager(BaseManager):
    """
    Orchestrates message routing and flow control across pipeline components
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "RoutingManager")

        # Initialize routing handler
        self.routing_handler = RoutingChannelHandler(message_broker)

        # Track active routes
        self.active_routes: Dict[str, RouteState] = {}

    def initialize_routing(self, message: ProcessingMessage) -> None:
        """Initialize routing for a new pipeline"""
        try:
            pipeline_id = message.content['pipeline_id']
            route_type = RouteType(message.content.get('route_type', 'sequential'))

            # Create route state
            route_state = RouteState(
                pipeline_id=pipeline_id,
                current_nodes=set(),
                completed_nodes=set(),
                route_type=route_type,
                status=ProcessingStatus.PENDING
            )

            self.active_routes[pipeline_id] = route_state

            # Start routing
            self.routing_handler.initialize_route(
                pipeline_id,
                route_type,
                message.content.get('config', {})
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize routing: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def route_message(self, message: ProcessingMessage) -> None:
        """Route message to next component"""
        try:
            pipeline_id = message.content['pipeline_id']
            current_node = message.content.get('current_node')

            route_state = self.active_routes.get(pipeline_id)
            if not route_state:
                raise ValueError(f"No active route for pipeline: {pipeline_id}")

            # Update route state
            if current_node:
                route_state.completed_nodes.add(current_node)
                route_state.current_nodes.remove(current_node)

            # Get next nodes
            next_nodes = self.routing_handler.get_next_nodes(
                pipeline_id,
                current_node,
                message.content
            )

            for node in next_nodes:
                route_state.current_nodes.add(node)
                self.routing_handler.route_to_node(
                    pipeline_id,
                    node,
                    message.content
                )

            # Check if pipeline complete
            if not route_state.current_nodes:
                self._finalize_routing(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to route message: {str(e)}")
            self.handle_error(e, {
                "pipeline_id": pipeline_id,
                "current_node": current_node
            })
            raise

    def handle_node_complete(self, message: ProcessingMessage) -> None:
        """Handle node completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            node = message.content['node']

            route_state = self.active_routes.get(pipeline_id)
            if not route_state:
                return

            # Update state
            route_state.completed_nodes.add(node)
            route_state.current_nodes.remove(node)

            # Route to next nodes if any
            self.route_message(message)

        except Exception as e:
            self.logger.error(f"Failed to handle node completion: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def handle_routing_condition(self, message: ProcessingMessage) -> None:
        """Handle conditional routing decisions"""
        try:
            pipeline_id = message.content['pipeline_id']
            condition_result = message.content['condition_result']

            route_state = self.active_routes.get(pipeline_id)
            if not route_state or route_state.route_type != RouteType.CONDITIONAL:
                return

            # Get conditional route
            next_nodes = self.routing_handler.get_conditional_route(
                pipeline_id,
                condition_result
            )

            # Update and route
            route_state.current_nodes.update(next_nodes)
            for node in next_nodes:
                self.routing_handler.route_to_node(
                    pipeline_id,
                    node,
                    message.content
                )

        except Exception as e:
            self.logger.error(f"Failed to handle routing condition: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def get_routing_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current routing status"""
        route_state = self.active_routes.get(pipeline_id)
        if not route_state:
            return None

        return {
            'pipeline_id': pipeline_id,
            'route_type': route_state.route_type.value,
            'current_nodes': list(route_state.current_nodes),
            'completed_nodes': list(route_state.completed_nodes),
            'status': route_state.status.value,
            'start_time': route_state.start_time.isoformat(),
            'end_time': route_state.end_time.isoformat() if route_state.end_time else None
        }

    def _finalize_routing(self, pipeline_id: str) -> None:
        """Complete routing process"""
        route_state = self.active_routes.get(pipeline_id)
        if not route_state:
            return

        try:
            route_state.status = ProcessingStatus.COMPLETED
            route_state.end_time = datetime.now()

            # Notify completion
            self.routing_handler.notify_routing_complete(
                pipeline_id,
                self.get_routing_status(pipeline_id)
            )

            # Cleanup
            self._cleanup_routing(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to finalize routing: {str(e)}")
            self.handle_error(e, {"pipeline_id": pipeline_id})
            raise

    def _cleanup_routing(self, pipeline_id: str) -> None:
        """Clean up routing resources"""
        if pipeline_id in self.active_routes:
            del self.active_routes[pipeline_id]

    def __del__(self):
        """Cleanup manager resources"""
        self.active_routes.clear()
        super().__del__()
