# backend/core/channel_handlers/routing_handler.py

import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.channel_handlers.base_handler import BaseHandler
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage

# Import the conductor module
from backend.core.orchestration.route_manager import DataConductor

logger = logging.getLogger(__name__)


class RouteType(Enum):
    """Types of routing paths"""
    SEQUENTIAL = "sequential"  # Standard pipeline flow
    PARALLEL = "parallel"  # Concurrent processing paths
    CONDITIONAL = "conditional"  # Decision-based routing


@dataclass
class RouteContext:
    """Context for routing operations"""
    pipeline_id: str
    route_type: RouteType
    current_nodes: Set[str]
    completed_nodes: Set[str]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "active"


class RoutingHandler(BaseHandler):
    """
    Handles communication between orchestrator and conductor
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "routing_handler")

        # Initialize conductor
        self.conductor = DataConductor(message_broker)

        # Track active routes
        self.active_routes: Dict[str, RouteContext] = {}

        # Register handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register message handlers"""
        self.register_callback(
            MessageType.ROUTE_REQUEST,
            self._handle_route_request
        )
        self.register_callback(
            MessageType.NODE_COMPLETE,
            self._handle_node_complete
        )
        self.register_callback(
            MessageType.ROUTE_CHANGE,
            self._handle_route_change
        )
        self.register_callback(
            MessageType.ROUTING_ERROR,
            self._handle_routing_error
        )

    def initiate_routing(self, pipeline_id: str, route_type: str,
                         context: Dict[str, Any]) -> None:
        """Entry point for routing operations"""
        try:
            route_context = RouteContext(
                pipeline_id=pipeline_id,
                route_type=RouteType(route_type),
                current_nodes=set(),
                completed_nodes=set(),
                metadata=context
            )

            self.active_routes[pipeline_id] = route_context

            # Get initial route from conductor
            initial_route = self.conductor.get_initial_route(
                pipeline_id,
                route_type,
                context
            )

            # Set current nodes
            route_context.current_nodes.update(initial_route)

            # Notify orchestrator of initial route
            self._notify_route_update(pipeline_id, initial_route)

        except Exception as e:
            self.logger.error(f"Failed to initiate routing: {str(e)}")
            self._handle_process_error(pipeline_id, str(e))

    def get_next_nodes(self, pipeline_id: str, current_node: str,
                       context: Dict[str, Any]) -> List[str]:
        """Get next nodes in route"""
        try:
            route_context = self.active_routes.get(pipeline_id)
            if not route_context:
                raise ValueError(f"No active route for pipeline: {pipeline_id}")

            # Get next nodes from conductor
            next_nodes = self.conductor.get_next_nodes(
                pipeline_id,
                current_node,
                route_context.route_type,
                context
            )

            return next_nodes

        except Exception as e:
            self.logger.error(f"Failed to get next nodes: {str(e)}")
            self._handle_process_error(pipeline_id, str(e))
            return []

    def _handle_route_request(self, message: ProcessingMessage) -> None:
        """Handle routing request"""
        pipeline_id = message.content['pipeline_id']
        route_type = message.content.get('route_type', 'sequential')
        context = message.content.get('context', {})

        self.initiate_routing(pipeline_id, route_type, context)

    def _handle_node_complete(self, message: ProcessingMessage) -> None:
        """Handle node completion"""
        pipeline_id = message.content['pipeline_id']
        completed_node = message.content['node']

        route_context = self.active_routes.get(pipeline_id)
        if not route_context:
            return

        try:
            # Update route state
            route_context.completed_nodes.add(completed_node)
            route_context.current_nodes.remove(completed_node)

            # Get next nodes
            next_nodes = self.get_next_nodes(
                pipeline_id,
                completed_node,
                message.content.get('context', {})
            )

            if next_nodes:
                # Update current nodes
                route_context.current_nodes.update(next_nodes)
                self._notify_route_update(pipeline_id, next_nodes)
            elif not route_context.current_nodes:
                # No more nodes - route complete
                self._handle_route_complete(pipeline_id)

        except Exception as e:
            self._handle_process_error(pipeline_id, str(e))

    def _handle_route_change(self, message: ProcessingMessage) -> None:
        """Handle dynamic route changes"""
        pipeline_id = message.content['pipeline_id']
        new_route = message.content.get('new_route', [])
        reason = message.content.get('reason', '')

        route_context = self.active_routes.get(pipeline_id)
        if not route_context:
            return

        try:
            # Update route state
            route_context.current_nodes = set(new_route)

            # Notify orchestrator
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.ROUTE_CHANGED,
                content={
                    'pipeline_id': pipeline_id,
                    'new_route': new_route,
                    'reason': reason
                }
            )

        except Exception as e:
            self._handle_process_error(pipeline_id, str(e))

    def _handle_route_complete(self, pipeline_id: str) -> None:
        """Handle route completion"""
        route_context = self.active_routes.get(pipeline_id)
        if not route_context:
            return

        try:
            # Notify orchestrator
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.ROUTE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'completed_nodes': list(route_context.completed_nodes),
                    'metadata': route_context.metadata
                }
            )

            # Cleanup
            self._cleanup_route(pipeline_id)

        except Exception as e:
            self._handle_process_error(pipeline_id, str(e))

    def _handle_process_error(self, pipeline_id: str, error: str) -> None:
        """Handle routing errors"""
        route_context = self.active_routes.get(pipeline_id)
        if route_context:
            # Notify orchestrator
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.ROUTING_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'error': error,
                    'current_nodes': list(route_context.current_nodes),
                    'completed_nodes': list(route_context.completed_nodes)
                }
            )

            # Cleanup
            self._cleanup_route(pipeline_id)

    def _notify_route_update(self, pipeline_id: str, new_nodes: List[str]) -> None:
        """Notify orchestrator of route update"""
        self.send_response(
            target_id=f"pipeline_manager_{pipeline_id}",
            message_type=MessageType.ROUTE_UPDATE,
            content={
                'pipeline_id': pipeline_id,
                'next_nodes': new_nodes
            }
        )

    def get_route_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current routing status"""
        route_context = self.active_routes.get(pipeline_id)
        if not route_context:
            return None

        return {
            'pipeline_id': pipeline_id,
            'route_type': route_context.route_type.value,
            'current_nodes': list(route_context.current_nodes),
            'completed_nodes': list(route_context.completed_nodes),
            'status': route_context.status,
            'created_at': route_context.created_at.isoformat()
        }

    def _cleanup_route(self, pipeline_id: str) -> None:
        """Clean up routing resources"""
        if pipeline_id in self.active_routes:
            del self.active_routes[pipeline_id]

    def __del__(self):
        """Cleanup handler resources"""
        self.active_routes.clear()
        super().__del__()
