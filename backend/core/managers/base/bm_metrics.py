# backend/core/managers/base/bm_metrics.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

@dataclass
class ChannelMetrics:
    """Metrics for channel monitoring"""
    channel_name: str
    created_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    queue_size: int = 0
    error_count: int = 0
    last_message_at: datetime = field(default_factory=datetime.now)
    processing_times: Dict[str, float] = field(default_factory=dict)
    handler_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def update_handler_stats(self, handler_name: str, success: bool, duration: float) -> None:
        """Update handler statistics"""
        if handler_name not in self.handler_stats:
            self.handler_stats[handler_name] = {
                'success_count': 0,
                'error_count': 0,
                'total_duration': 0.0,
                'average_duration': 0.0,
                'last_execution': None
            }

        stats = self.handler_stats[handler_name]
        if success:
            stats['success_count'] += 1
        else:
            stats['error_count'] += 1

        stats['total_duration'] += duration
        total_executions = stats['success_count'] + stats['error_count']
        stats['average_duration'] = stats['total_duration'] / total_executions
        stats['last_execution'] = datetime.now()

    def add_processing_time(self, message_type: str, duration: float) -> None:
        """Add processing time for message type"""
        if message_type not in self.processing_times:
            self.processing_times[message_type] = duration
        else:
            # Calculate running average
            current = self.processing_times[message_type]
            message_count = self.message_count or 1
            self.processing_times[message_type] = (current * (message_count - 1) + duration) / message_count

    def increment_error(self) -> None:
        """Increment error count"""
        self.error_count += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        return {
            'channel_name': self.channel_name,
            'message_count': self.message_count,
            'error_count': self.error_count,
            'queue_size': self.queue_size,
            'uptime': (datetime.now() - self.created_at).total_seconds(),
            'last_message': self.last_message_at.isoformat(),
            'processing_times': self.processing_times,
            'handler_stats': self.handler_stats
        }

    def reset(self) -> None:
        """Reset metrics"""
        self.message_count = 0
        self.queue_size = 0
        self.error_count = 0
        self.last_message_at = datetime.now()
        self.processing_times.clear()
        self.handler_stats.clear()

@dataclass
class ManagerMetrics:
    """Aggregated metrics for manager"""
    total_messages: int = 0
    total_errors: int = 0
    channel_metrics: Dict[str, ChannelMetrics] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)

    def update_channel_metrics(self, channel_name: str, metrics: ChannelMetrics) -> None:
        """Update metrics for a specific channel"""
        self.channel_metrics[channel_name] = metrics
        self.total_messages += metrics.message_count
        self.total_errors += metrics.error_count
        self.last_update = datetime.now()

    def get_summary(self) -> Dict[str, Any]:
        """Get manager metrics summary"""
        return {
            'total_messages': self.total_messages,
            'total_errors': self.total_errors,
            'uptime': (datetime.now() - self.start_time).total_seconds(),
            'last_update': self.last_update.isoformat(),
            'channels': {
                name: metrics.get_summary()
                for name, metrics in self.channel_metrics.items()
            }
        }

    def reset(self) -> None:
        """Reset all metrics"""
        self.total_messages = 0
        self.total_errors = 0
        for metrics in self.channel_metrics.values():
            metrics.reset()
        self.last_update = datetime.now()