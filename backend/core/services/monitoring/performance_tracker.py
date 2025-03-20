import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import statistics
import numpy as np

from ..base.base_service import BaseService
from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    MonitoringContext,
    MetricType,
    MetricsAggregate,
    PerformanceMetrics,
    PerformanceBaseline
)

logger = logging.getLogger(__name__)

class PerformanceTracker(BaseService):
    """
    Service for tracking and analyzing system performance.
    Handles performance metrics analysis, baseline creation, and anomaly detection.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker)
        
        # Service identifier
        self.module_identifier = ModuleIdentifier(
            component_name="performance_tracker",
            component_type=ComponentType.MONITORING_SERVICE,
            department="monitoring",
            role="tracker"
        )

        # Performance tracking configuration
        self.baseline_window = timedelta(hours=24)  # Default baseline window
        self.anomaly_threshold = 2.0  # Standard deviations for anomaly detection
        self.min_samples = 100  # Minimum samples for baseline calculation
        
        # Performance data storage
        self.performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self.performance_baselines: Dict[str, Dict[str, Any]] = {}
        
        # Setup message handlers
        self._setup_message_handlers()

    async def _setup_message_handlers(self) -> None:
        """Setup handlers for performance tracking messages"""
        handlers = {
            MessageType.MONITORING_METRICS_UPDATE: self._handle_metrics_update,
            MessageType.MONITORING_PERFORMANCE_ANALYZE: self._handle_performance_analysis,
            MessageType.MONITORING_BASELINE_UPDATE: self._handle_baseline_update
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_metrics_update(self, message: ProcessingMessage) -> None:
        """Handle incoming metrics updates"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")

            metrics = message.content.get('metrics', {})
            if not metrics:
                return

            # Store metrics in history
            if pipeline_id not in self.performance_history:
                self.performance_history[pipeline_id] = []
            
            self.performance_history[pipeline_id].append({
                'timestamp': datetime.now(),
                'metrics': metrics
            })

            # Clean up old metrics
            self._cleanup_old_metrics(pipeline_id)

            # Analyze performance if we have enough data
            if len(self.performance_history[pipeline_id]) >= self.min_samples:
                await self._analyze_performance(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle metrics update: {str(e)}")
            await self._handle_error(message, str(e))

    def _cleanup_old_metrics(self, pipeline_id: str) -> None:
        """Remove metrics older than the baseline window"""
        if pipeline_id not in self.performance_history:
            return

        cutoff_time = datetime.now() - self.baseline_window
        self.performance_history[pipeline_id] = [
            entry for entry in self.performance_history[pipeline_id]
            if entry['timestamp'] > cutoff_time
        ]

    async def _analyze_performance(self, pipeline_id: str) -> None:
        """Analyze performance metrics and detect anomalies"""
        try:
            if pipeline_id not in self.performance_history:
                return

            history = self.performance_history[pipeline_id]
            if len(history) < self.min_samples:
                return

            # Extract metrics for analysis
            metrics_data = self._extract_metrics_data(history)
            
            # Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics(metrics_data)
            
            # Detect anomalies
            anomalies = self._detect_anomalies(metrics_data, performance_metrics)
            
            # Create performance metrics object
            performance_result = PerformanceMetrics(
                pipeline_id=pipeline_id,
                timestamp=datetime.now(),
                metrics=performance_metrics,
                anomalies=anomalies,
                baseline_comparison=self._compare_with_baseline(pipeline_id, performance_metrics)
            )

            # Publish performance analysis results
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PERFORMANCE_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'performance': performance_result
                    },
                    metadata=MessageMetadata(
                        correlation_id=str(uuid.uuid4()),
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to analyze performance: {str(e)}")
            await self._handle_error(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_FAILED,
                    content={'pipeline_id': pipeline_id}
                ),
                str(e)
            )

    def _extract_metrics_data(self, history: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """Extract numeric metrics from history for analysis"""
        metrics_data = {}
        
        for entry in history:
            metrics = entry['metrics']
            for category, values in metrics.items():
                if category not in metrics_data:
                    metrics_data[category] = {}
                
                for key, value in values.items():
                    if isinstance(value, (int, float)):
                        if key not in metrics_data[category]:
                            metrics_data[category][key] = []
                        metrics_data[category][key].append(value)
        
        return metrics_data

    def _calculate_performance_metrics(self, metrics_data: Dict[str, Dict[str, List[float]]]) -> Dict[str, Any]:
        """Calculate performance metrics from raw data"""
        performance_metrics = {}
        
        for category, metrics in metrics_data.items():
            performance_metrics[category] = {}
            
            for key, values in metrics.items():
                if len(values) > 0:
                    performance_metrics[category][key] = {
                        'mean': statistics.mean(values),
                        'median': statistics.median(values),
                        'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
                        'min': min(values),
                        'max': max(values),
                        'p95': np.percentile(values, 95),
                        'p99': np.percentile(values, 99)
                    }
        
        return performance_metrics

    def _detect_anomalies(self, metrics_data: Dict[str, Dict[str, List[float]]], 
                         performance_metrics: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Detect anomalies in performance metrics"""
        anomalies = {}
        
        for category, metrics in metrics_data.items():
            anomalies[category] = []
            
            for key, values in metrics.items():
                if len(values) > 0:
                    current_value = values[-1]
                    stats = performance_metrics[category][key]
                    
                    # Check if current value is outside normal range
                    if abs(current_value - stats['mean']) > (self.anomaly_threshold * stats['std_dev']):
                        anomalies[category].append({
                            'metric': key,
                            'value': current_value,
                            'threshold': stats['mean'] + (self.anomaly_threshold * stats['std_dev']),
                            'severity': 'high' if abs(current_value - stats['mean']) > (3 * stats['std_dev']) else 'medium'
                        })
        
        return anomalies

    def _compare_with_baseline(self, pipeline_id: str, 
                             performance_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current performance with baseline"""
        if pipeline_id not in self.performance_baselines:
            return {'status': 'no_baseline'}
        
        baseline = self.performance_baselines[pipeline_id]
        comparison = {'status': 'baseline_comparison', 'metrics': {}}
        
        for category, metrics in performance_metrics.items():
            comparison['metrics'][category] = {}
            
            for key, stats in metrics.items():
                if category in baseline and key in baseline[category]:
                    baseline_value = baseline[category][key]
                    current_value = stats['mean']
                    
                    comparison['metrics'][category][key] = {
                        'current': current_value,
                        'baseline': baseline_value,
                        'difference': current_value - baseline_value,
                        'percent_change': ((current_value - baseline_value) / baseline_value) * 100
                    }
        
        return comparison

    async def _handle_performance_analysis(self, message: ProcessingMessage) -> None:
        """Handle performance analysis request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")

            # Trigger performance analysis
            await self._analyze_performance(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle performance analysis request: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_baseline_update(self, message: ProcessingMessage) -> None:
        """Handle baseline update request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")

            if pipeline_id not in self.performance_history:
                raise ValueError("No performance history available")

            # Calculate new baseline
            history = self.performance_history[pipeline_id]
            metrics_data = self._extract_metrics_data(history)
            performance_metrics = self._calculate_performance_metrics(metrics_data)

            # Create baseline
            baseline = PerformanceBaseline(
                pipeline_id=pipeline_id,
                timestamp=datetime.now(),
                metrics=performance_metrics,
                window_size=self.baseline_window
            )

            # Store baseline
            self.performance_baselines[pipeline_id] = performance_metrics

            # Publish baseline update notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_BASELINE_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'baseline': baseline
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to update baseline: {str(e)}")
            await self._handle_error(message, str(e)) 