# backend/core/orchestration/conductor.py

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    ModuleIdentifier,
    ProcessingMessage,
    MessageType,
    ProcessingStatus,
    ComponentType
)

from backend.core.registry.component_registry import ComponentRegistry

logger = logging.getLogger(__name__)


class RouteType(Enum):
    """Types of routing paths"""
    SEQUENTIAL = "sequential"  # Standard pipeline flow
    PARALLEL = "parallel"  # Concurrent processing paths
    CONDITIONAL = "conditional"  # Decision-based routing


@dataclass
class Route:
    """Represents a processing route"""
    source_node: str
    target_nodes: List[str]
    route_type: RouteType
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0


@dataclass
class RouteExecution:
    """Tracks route execution"""
    route_id: str
    pipeline_id: str
    current_nodes: Set[str]
    completed_nodes: Set[str]
    route_type: RouteType
    start_time: datetime = field(default_factory=datetime.now)
    status: str = "active"


@dataclass
class ConductorMetrics:
    """Tracks routing metrics"""
    total_routes: int = 0
    active_routes: int = 0
    completed_routes: int = 0
    failed_routes: int = 0
    avg_execution_time: float = 0.0


class DataConductor:
    """
    Enhanced routing logic manager that determines message paths
    through the pipeline
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.registry = ComponentRegistry()

        # Initialize component ID
        self.component_id = ModuleIdentifier(
            "Conductor",
            ComponentType.MODULE,
            "route_management",
            self.registry.get_component_uuid("Conductor")
        )

        # Core routing data
        self.routes: Dict[str, Route] = {}
        self.active_executions: Dict[str, RouteExecution] = {}
        self.metrics = ConductorMetrics()

        # Standard pipeline flow
        self._initialize_standard_routes()

    def _initialize_standard_routes(self) -> None:
        """Initialize standard pipeline routes"""
        standard_flow = [
            ("source", ["quality"]),
            ("quality", ["insight"]),
            ("insight", ["decision"]),
            ("decision", ["final"])
        ]

        for source, targets in standard_flow:
            self.register_route(
                source_node=source,
                target_nodes=targets,
                route_type=RouteType.SEQUENTIAL
            )

    def register_route(self, source_node: str, target_nodes: List[str],
                       route_type: RouteType, conditions: Dict[str, Any] = None) -> str:
        """Register a new route"""
        route_id = f"{source_node}_{'_'.join(target_nodes)}"

        self.routes[route_id] = Route(
            source_node=source_node,
            target_nodes=target_nodes,
            route_type=route_type,
            conditions=conditions or {}
        )

        return route_id

    def get_initial_route(self, pipeline_id: str,
                          context: Dict[str, Any]) -> List[str]:
        """Get initial pipeline route"""
        # Start with source processing
        return ["source"]

    def get_next_nodes(self, pipeline_id: str, current_node: str,
                       context: Dict[str, Any]) -> List[str]:
        """Get next nodes in the route"""
        try:
            # Find applicable routes
            next_nodes = set()
            for route in self.routes.values():
                if route.source_node == current_node:
                    if self._evaluate_conditions(route, context):
                        next_nodes.update(route.target_nodes)

            return list(next_nodes)

        except Exception as e:
            logger.error(f"Error getting next nodes: {str(e)}")
            return []

    def start_route_execution(self, pipeline_id: str, route_type: RouteType,
                              initial_nodes: List[str]) -> str:
        """Start new route execution"""
        execution_id = f"route_{pipeline_id}_{datetime.now().timestamp()}"

        execution = RouteExecution(
            route_id=execution_id,
            pipeline_id=pipeline_id,
            current_nodes=set(initial_nodes),
            completed_nodes=set(),
            route_type=route_type
        )

        self.active_executions[execution_id] = execution
        self.metrics.active_routes += 1

        return execution_id

    def update_route_execution(self, execution_id: str, completed_node: str,
                               context: Dict[str, Any]) -> List[str]:
        """Update route execution state"""
        execution = self.active_executions.get(execution_id)
        if not execution:
            raise ValueError(f"No active execution found: {execution_id}")

        # Update execution state
        execution.completed_nodes.add(completed_node)
        execution.current_nodes.remove(completed_node)

        # Get next nodes
        next_nodes = self.get_next_nodes(
            execution.pipeline_id,
            completed_node,
            context
        )

        # Update current nodes
        execution.current_nodes.update(next_nodes)

        return next_nodes

    def handle_conditional_routing(self, execution_id: str,
                                   condition_result: Dict[str, Any]) -> List[str]:
        """Handle conditional routing decision"""
        execution = self.active_executions.get(execution_id)
        if not execution or execution.route_type != RouteType.CONDITIONAL:
            raise ValueError("Invalid execution for conditional routing")

        # Find matching route based on condition
        next_nodes = []
        for route in self.routes.values():
            if route.conditions and self._evaluate_conditions(route, condition_result):
                next_nodes.extend(route.target_nodes)

        return next_nodes

    def _evaluate_conditions(self, route: Route, context: Dict[str, Any]) -> bool:
        """Evaluate route conditions"""
        if not route.conditions:
            return True

        try:
            for key, value in route.conditions.items():
                if context.get(key) != value:
                    return False
            return True

        except Exception as e:
            logger.error(f"Error evaluating conditions: {str(e)}")
            return False

    def complete_route_execution(self, execution_id: str, status: str = "completed") -> None:
        """Complete route execution"""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return

        execution.status = status

        # Update metrics
        self.metrics.active_routes -= 1
        if status == "completed":
            self.metrics.completed_routes += 1
        else:
            self.metrics.failed_routes += 1

        # Calculate execution time
        execution_time = (datetime.now() - execution.start_time).total_seconds()
        self._update_metrics(execution_time)

        # Cleanup
        del self.active_executions[execution_id]

    def _update_metrics(self, execution_time: float) -> None:
        """Update routing metrics"""
        total_routes = self.metrics.completed_routes + self.metrics.failed_routes
        if total_routes > 0:
            current_avg = self.metrics.avg_execution_time
            self.metrics.avg_execution_time = (
                    (current_avg * (total_routes - 1) + execution_time) / total_routes
            )

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get route execution status"""
        execution = self.active_executions.get(execution_id)
        if not execution:
            return None

        return {
            'execution_id': execution_id,
            'pipeline_id': execution.pipeline_id,
            'route_type': execution.route_type.value,
            'current_nodes': list(execution.current_nodes),
            'completed_nodes': list(execution.completed_nodes),
            'status': execution.status,
            'start_time': execution.start_time.isoformat()
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get routing metrics"""
        return {
            'total_routes': self.metrics.total_routes,
            'active_routes': self.metrics.active_routes,
            'completed_routes': self.metrics.completed_routes,
            'failed_routes': self.metrics.failed_routes,
            'avg_execution_time': self.metrics.avg_execution_time
        }
