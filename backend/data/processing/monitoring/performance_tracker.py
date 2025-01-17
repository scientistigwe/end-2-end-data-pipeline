from typing import Any, Dict
from datetime import datetime
import threading
from backend.core.messaging.types import (
    ProcessingMessage,
    MessageType,
    ProcessingStatus,
    ModuleIdentifier
)

class PerformanceTracker:
    """Tracks and manages pipeline performance metrics

    Manages both individual pipeline metrics and global system performance statistics
    using thread-safe operations.
    """

    def __init__(self):
        """Initialize performance tracking structures"""
        self.pipeline_metrics: Dict[str, Dict[str, Any]] = {}
        self.global_metrics = {
            'total_pipelines': 0,
            'successful_pipelines': 0,
            'average_processing_time': 0.0,
            'total_data_processed': 0
        }
        self._lock = threading.Lock()

    def track_pipeline_start(self, pipeline_id: str, message: ProcessingMessage):
        """Record pipeline initiation metrics

        Args:
            pipeline_id (str): Unique identifier for the pipeline
            message (ProcessingMessage): Initial processing message
        """
        start_time = datetime.now()
        data_size = len(str(message.content.get('data', '')))

        with self._lock:
            self.pipeline_metrics[pipeline_id] = {
                'start_time': start_time,
                'source_type': message.source_identifier.module_name,
                'initial_data_size': data_size,
                'status': 'in_progress'
            }

            self.global_metrics['total_pipelines'] += 1
            self.global_metrics['total_data_processed'] += data_size

    def finalize_pipeline_metrics(self, pipeline_id: str, status: str):
        """Update metrics upon pipeline completion

        Args:
            pipeline_id (str): Pipeline identifier
            status (str): Final pipeline status
        """
        with self._lock:
            if pipeline_id not in self.pipeline_metrics:
                return

            pipeline_data = self.pipeline_metrics[pipeline_id]
            end_time = datetime.now()
            duration = (end_time - pipeline_data['start_time']).total_seconds()

            pipeline_data.update({
                'end_time': end_time,
                'duration': duration,
                'status': status
            })

            if status == 'success':
                self.global_metrics['successful_pipelines'] += 1

            total_pipelines = self.global_metrics['total_pipelines']
            current_avg = self.global_metrics['average_processing_time']
            new_avg = (current_avg * (total_pipelines - 1) + duration) / total_pipelines
            self.global_metrics['average_processing_time'] = new_avg

    def get_performance_summary(self) -> Dict[str, Any]:
        """Generate comprehensive performance report

        Returns:
            Dict[str, Any]: Detailed performance metrics
        """
        with self._lock:
            return {
                'global_metrics': self.global_metrics,
                'active_pipelines': len(self.pipeline_metrics),
                'detailed_pipeline_metrics': self.pipeline_metrics
            }
