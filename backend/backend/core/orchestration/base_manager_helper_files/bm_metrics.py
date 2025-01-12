# backend/core/base/base_manager_metrics.py

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class ChannelMetrics:
    """Track channel health and performance"""
    message_count: int = 0
    error_count: int = 0
    last_processed: Optional[datetime] = None
    backpressure_applied: bool = False
    processing_time: List[float] = field(default_factory=list)
    retry_count: int = 0
    queue_size: int = 0

    def update_processing_time(self, processing_time: float, max_entries: int = 100) -> None:
        """
        Update processing time with a rolling window.

        Args:
            processing_time (float): Time taken to process a message
            max_entries (int, optional): Maximum number of entries to keep. Defaults to 100.
        """
        self.processing_time.append(processing_time)
        if len(self.processing_time) > max_entries:
            self.processing_time = self.processing_time[-max_entries:]

    def get_average_processing_time(self) -> float:
        """
        Calculate average processing time.

        Returns:
            float: Average processing time, or 0 if no entries
        """
        return sum(self.processing_time) / len(self.processing_time) if self.processing_time else 0


@dataclass
class ControlPointMetrics:
    """Track control point metrics"""
    active_control_points: int = 0
    decisions_pending: int = 0
    decisions_completed: int = 0
    decisions_timeout: int = 0
    average_decision_time: float = 0.0
    last_decision_time: Optional[datetime] = None

    def update_decision_metrics(self, decision_duration: float) -> None:
        """
        Update decision-related metrics.

        Args:
            decision_duration (float): Time taken for decision
        """
        self.decisions_completed += 1
        self.decisions_pending = max(0, self.decisions_pending - 1)

        if self.decisions_completed == 1:
            self.average_decision_time = decision_duration
        else:
            self.average_decision_time = (
                    (self.average_decision_time * (self.decisions_completed - 1) + decision_duration)
                    / self.decisions_completed
            )

        self.last_decision_time = datetime.now()


@dataclass
class ManagerMetadata:
    """Enhanced manager metadata with control points"""
    component_name: str
    instance_id: str
    created_at: datetime = field(default_factory=datetime.now)
    state: Any = None  # Use ResourceState
    error_count: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    control_point_metrics: ControlPointMetrics = field(default_factory=ControlPointMetrics)
    active_decisions: Dict[str, Any] = field(default_factory=dict)

    def update_performance_metrics(self, **kwargs) -> None:
        """
        Update performance metrics with provided key-value pairs.

        Args:
            **kwargs: Key-value pairs of performance metrics
        """
        self.performance_metrics.update(kwargs)

    def reset_metrics(self) -> None:
        """
        Reset all metrics to their initial state.
        """
        self.error_count = 0
        self.control_point_metrics = ControlPointMetrics()
        self.performance_metrics.clear()
        self.active_decisions.clear()