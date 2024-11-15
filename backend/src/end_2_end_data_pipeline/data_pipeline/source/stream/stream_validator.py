# data_pipeline/source/cloud/stream_data_validator.py
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from backend.src.end_2_end_data_pipeline.data_pipeline.exceptions import StreamingDataValidationError


class StreamDataValidator:
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the validator with source-specific configuration.

        config: {
            'max_latency_seconds': int,
            'required_schema': Dict[str, str],  # Core schema requirements
            'batch_size_limits': {'min': int, 'max': int},
            'timestamp_column': str,
            'max_gap_seconds': int,
            'source_health_threshold': float,  # Expected success rate (0.0-1.0)
            'partition_keys': List[str],  # Required partition keys
            'max_retry_attempts': int,     # Maximum retry attempts before failing
            'backpressure_threshold': int  # Maximum pending messages
        }
        """
        self.config = config or {}
        self.validation_results = []
        self.source_health_metrics = {
            'total_attempts': 0,
            'successful_fetches': 0,
            'failed_fetches': 0,
            'retry_counts': [],
            'connection_drops': 0
        }

    def validate_source(self, data: pd.DataFrame, source_metrics: Dict) -> tuple[bool, Dict]:
        """
        Validates the streaming source health and reliability.

        Args:
            data: DataFrame containing the streaming data
            source_metrics: Dictionary containing source metrics

        Returns:
            tuple: (is_valid, report) where:
                - is_valid: True if source meets quality threshold
                - report: Dict containing detailed health report

        Raises:
            StreamingDataValidationError: If validation process fails
        """
        try:
            self.validation_results = []

            # Core Source Validations
            self._validate_source_connectivity(source_metrics)
            self._validate_source_throughput(source_metrics)
            self._validate_source_partitioning(data)
            self._validate_source_backpressure(source_metrics)

            # Stream Health Validations
            self._validate_stream_freshness(data)
            self._validate_stream_continuity(data)
            self._validate_message_ordering(data)

            # Source Reliability Metrics
            self._update_source_health_metrics(source_metrics)
            self._validate_source_health()

            # Generate source health report
            report = self._generate_source_health_report()

            # Calculate if source meets quality threshold
            is_valid = self._calculate_source_quality() >= self.config.get('source_health_threshold', 0.9)

            # Add validation status to report
            report['validation_status'] = {
                'is_valid': is_valid,
                'threshold': self.config.get('source_health_threshold', 0.9),
                'timestamp': datetime.now().isoformat()
            }

            return is_valid, report

        except Exception as e:
            raise StreamingDataValidationError(f"Source validation failed: {str(e)}")

    def _validate_source_connectivity(self, metrics: Dict):
        """Validate source connection stability"""
        connection_drops = metrics.get('connection_drops', 0)
        retry_attempts = metrics.get('retry_attempts', 0)
        max_retries = self.config.get('max_retry_attempts', 3)

        is_stable = (connection_drops == 0) and (retry_attempts <= max_retries)

        self.validation_results.append({
            'check': 'source_connectivity',
            'passed': is_stable,
            'message': f"Connection unstable: drops={connection_drops}, retries={retry_attempts}" if not is_stable else 'Source connection stable'
        })

    def _validate_source_throughput(self, metrics: Dict):
        """Validate source is meeting expected throughput"""
        current_throughput = metrics.get('messages_per_second', 0)
        expected_throughput = self.config.get('min_throughput', 1)

        is_valid = current_throughput >= expected_throughput

        self.validation_results.append({
            'check': 'source_throughput',
            'passed': is_valid,
            'message': f"Throughput below threshold: {current_throughput} msg/s" if not is_valid else 'Throughput acceptable'
        })

    def _validate_source_partitioning(self, data: pd.DataFrame):
        """Validate stream partitioning is correct"""
        if 'partition_keys' in self.config:
            required_keys = set(self.config['partition_keys'])
            actual_keys = set(data.columns)

            missing_keys = required_keys - actual_keys
            is_valid = len(missing_keys) == 0

            self.validation_results.append({
                'check': 'source_partitioning',
                'passed': is_valid,
                'message': f"Missing partition keys: {missing_keys}" if not is_valid else 'Partitioning valid'
            })

    def _validate_source_backpressure(self, metrics: Dict):
        """Check if source is experiencing backpressure"""
        pending_messages = metrics.get('pending_messages', 0)
        threshold = self.config.get('backpressure_threshold', 1000)

        is_valid = pending_messages <= threshold

        self.validation_results.append({
            'check': 'source_backpressure',
            'passed': is_valid,
            'message': f"High backpressure: {pending_messages} pending messages" if not is_valid else 'Normal backpressure'
        })

    def _validate_stream_freshness(self, data: pd.DataFrame):
        """Validate data freshness/latency"""
        if 'timestamp_column' in self.config and 'max_latency_seconds' in self.config:
            ts_col = self.config['timestamp_column']
            if ts_col in data.columns:
                current_time = datetime.now()
                max_latency = timedelta(seconds=self.config['max_latency_seconds'])

                latest_timestamp = pd.to_datetime(data[ts_col]).max()
                latency = current_time - latest_timestamp

                is_fresh = latency <= max_latency
                self.validation_results.append({
                    'check': 'stream_freshness',
                    'passed': is_fresh,
                    'message': f"Stream latency: {latency.total_seconds()}s" if not is_fresh else 'Stream fresh'
                })

    def _validate_stream_continuity(self, data: pd.DataFrame):
        """Validate there are no significant gaps in the stream"""
        if 'timestamp_column' in self.config and 'max_gap_seconds' in self.config:
            ts_col = self.config['timestamp_column']
            if ts_col in data.columns:
                timestamps = pd.to_datetime(data[ts_col]).sort_values()
                gaps = timestamps.diff()[1:]
                max_gap = gaps.max()

                is_continuous = max_gap.total_seconds() <= self.config['max_gap_seconds']
                self.validation_results.append({
                    'check': 'stream_continuity',
                    'passed': is_continuous,
                    'message': f"Stream gap detected: {max_gap.total_seconds()}s" if not is_continuous else 'Stream continuous'
                })

    def _validate_message_ordering(self, data: pd.DataFrame):
        """Validate message sequence ordering"""
        if 'timestamp_column' in self.config:
            ts_col = self.config['timestamp_column']
            if ts_col in data.columns:
                is_ordered = data[ts_col].is_monotonic_increasing

                self.validation_results.append({
                    'check': 'message_ordering',
                    'passed': is_ordered,
                    'message': 'Message ordering violated' if not is_ordered else 'Message ordering maintained'
                })

    def _update_source_health_metrics(self, metrics: Dict):
        """Update source health tracking metrics"""
        self.source_health_metrics['total_attempts'] += 1
        if metrics.get('fetch_success', False):
            self.source_health_metrics['successful_fetches'] += 1
        else:
            self.source_health_metrics['failed_fetches'] += 1

        self.source_health_metrics['retry_counts'].append(metrics.get('retry_attempts', 0))
        self.source_health_metrics['connection_drops'] += metrics.get('connection_drops', 0)

    def _calculate_source_quality(self) -> float:
        """Calculate overall source quality score"""
        if not self.source_health_metrics['total_attempts']:
            return 0.0

        success_rate = (
                self.source_health_metrics['successful_fetches'] /
                self.source_health_metrics['total_attempts']
        )

        # Weight different factors
        weights = {
            'success_rate': 0.4,
            'connectivity': 0.3,
            'throughput': 0.3
        }

        # Calculate weighted score
        score = (
                success_rate * weights['success_rate'] +
                (1 - self.source_health_metrics['connection_drops'] / max(1, self.source_health_metrics[
                    'total_attempts'])) * weights['connectivity'] +
                (len([r for r in self.validation_results if r['check'] == 'source_throughput' and r['passed']]) / max(1,
                                                                                                                      len(self.validation_results))) *
                weights['throughput']
        )

        return score

    def _generate_source_health_report(self) -> Dict:
        """Generate comprehensive source health report"""
        return {
            'timestamp': datetime.now().isoformat(),
            'source_quality_score': self._calculate_source_quality(),
            'health_metrics': self.source_health_metrics,
            'validation_results': self.validation_results,
            'recommendations': self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []

        if self.source_health_metrics['connection_drops'] > 0:
            recommendations.append("Consider implementing connection pooling or circuit breaker")

        if any(r['check'] == 'source_throughput' and not r['passed'] for r in self.validation_results):
            recommendations.append("Evaluate source capacity and scaling requirements")

        if self.source_health_metrics['retry_counts'] and max(
                self.source_health_metrics['retry_counts']) > self.config.get('max_retry_attempts', 3):
            recommendations.append("Review retry strategy and timeout configurations")

        return recommendations

    def _validate_source_health(self):
        """
        Validate overall source health based on collected metrics and thresholds.
        This method analyzes various health indicators and adds validation results.
        """
        # Calculate success rate
        total_attempts = self.source_health_metrics['total_attempts']
        if total_attempts == 0:
            success_rate = 0.0
        else:
            success_rate = self.source_health_metrics['successful_fetches'] / total_attempts

        # Check success rate against threshold
        health_threshold = self.config.get('source_health_threshold', 0.9)
        is_healthy = success_rate >= health_threshold

        self.validation_results.append({
            'check': 'source_health',
            'passed': is_healthy,
            'message': f"Source health below threshold: {success_rate:.2%}" if not is_healthy else 'Source health acceptable'
        })

        # Check retry pattern
        retry_counts = self.source_health_metrics['retry_counts']
        if retry_counts:
            avg_retries = sum(retry_counts) / len(retry_counts)
            max_retries = max(retry_counts)
            max_retry_threshold = self.config.get('max_retry_attempts', 3)

            retry_health_ok = max_retries <= max_retry_threshold
            self.validation_results.append({
                'check': 'retry_health',
                'passed': retry_health_ok,
                'message': f"High retry rate detected: avg={avg_retries:.1f}, max={max_retries}" if not retry_health_ok else 'Retry pattern acceptable'
            })

        # Check connection stability
        connection_drops = self.source_health_metrics['connection_drops']
        connection_drop_rate = connection_drops / max(1, total_attempts)
        stability_threshold = 0.05  # 5% maximum acceptable drop rate

        is_stable = connection_drop_rate <= stability_threshold
        self.validation_results.append({
            'check': 'connection_stability',
            'passed': is_stable,
            'message': f"Unstable connection: {connection_drop_rate:.2%} drop rate" if not is_stable else 'Connection stability acceptable'
        })
