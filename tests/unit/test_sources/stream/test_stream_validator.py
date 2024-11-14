import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_pipeline.source.stream.stream_validator import StreamDataValidator, StreamingDataValidationError

@pytest.fixture
def validator_config():
    return {
        'max_latency_seconds': 300,
        'batch_size_limits': {'min': 1, 'max': 10000},
        'timestamp_column': 'event_timestamp',
        'max_gap_seconds': 60,
        'source_health_threshold': 0.9,
        'partition_keys': ['partition_id', 'shard_id'],
        'max_retry_attempts': 3,
        'backpressure_threshold': 1000,
        'min_throughput': 100
    }

@pytest.fixture
def validator(validator_config):
    return StreamDataValidator(validator_config)

@pytest.fixture
def sample_data():
    now = datetime.now()
    return pd.DataFrame({
        'event_timestamp': [now - timedelta(seconds=x) for x in range(10)],
        'partition_id': ['p1'] * 10,
        'shard_id': ['s1'] * 10,
        'value': range(10)
    })

@pytest.fixture
def healthy_metrics():
    return {
        'connection_drops': 0,
        'retry_attempts': 0,
        'messages_per_second': 150,
        'pending_messages': 500,
        'fetch_success': True
    }

class TestStreamDataValidator:
    def test_initialization(self, validator_config):
        validator = StreamDataValidator(validator_config)
        assert validator.config == validator_config
        assert validator.validation_results == []
        assert validator.source_health_metrics['total_attempts'] == 0

    def test_validate_source_connectivity_success(self, validator):
        metrics = {'connection_drops': 0, 'retry_attempts': 1}
        validator._validate_source_connectivity(metrics)
        assert validator.validation_results[0]['passed']
        assert 'Source connection stable' in validator.validation_results[0]['message']

    def test_validate_source_connectivity_failure(self, validator):
        metrics = {'connection_drops': 2, 'retry_attempts': 5}
        validator._validate_source_connectivity(metrics)
        assert not validator.validation_results[0]['passed']
        assert 'Connection unstable' in validator.validation_results[0]['message']

    def test_validate_source_throughput_success(self, validator):
        metrics = {'messages_per_second': 150}
        validator._validate_source_throughput(metrics)
        assert validator.validation_results[0]['passed']
        assert 'Throughput acceptable' in validator.validation_results[0]['message']

    def test_validate_source_throughput_failure(self, validator):
        metrics = {'messages_per_second': 50}
        validator._validate_source_throughput(metrics)
        assert not validator.validation_results[0]['passed']
        assert 'Throughput below threshold' in validator.validation_results[0]['message']

    def test_validate_source_partitioning_success(self, validator, sample_data):
        validator._validate_source_partitioning(sample_data)
        assert validator.validation_results[0]['passed']
        assert 'Partitioning valid' in validator.validation_results[0]['message']

    def test_validate_source_partitioning_failure(self, validator):
        bad_data = pd.DataFrame({'wrong_column': range(10)})
        validator._validate_source_partitioning(bad_data)
        assert not validator.validation_results[0]['passed']
        assert 'Missing partition keys' in validator.validation_results[0]['message']

    def test_validate_source_backpressure_success(self, validator):
        metrics = {'pending_messages': 500}
        validator._validate_source_backpressure(metrics)
        assert validator.validation_results[0]['passed']
        assert 'Normal backpressure' in validator.validation_results[0]['message']

    def test_validate_source_backpressure_failure(self, validator):
        metrics = {'pending_messages': 1500}
        validator._validate_source_backpressure(metrics)
        assert not validator.validation_results[0]['passed']
        assert 'High backpressure' in validator.validation_results[0]['message']

    def test_validate_stream_freshness_success(self, validator, sample_data):
        validator._validate_stream_freshness(sample_data)
        assert validator.validation_results[0]['passed']
        assert 'Stream fresh' in validator.validation_results[0]['message']

    def test_validate_stream_freshness_failure(self, validator):
        old_data = pd.DataFrame({
            'event_timestamp': [datetime.now() - timedelta(seconds=600)],
            'value': [1]
        })
        validator._validate_stream_freshness(old_data)
        assert not validator.validation_results[0]['passed']
        assert 'Stream latency' in validator.validation_results[0]['message']

    def test_validate_stream_continuity_success(self, validator, sample_data):
        validator._validate_stream_continuity(sample_data)
        assert validator.validation_results[0]['passed']
        assert 'Stream continuous' in validator.validation_results[0]['message']

    def test_validate_stream_continuity_failure(self, validator):
        now = datetime.now()
        gap_data = pd.DataFrame({
            'event_timestamp': [now, now - timedelta(seconds=100)],
            'value': [1, 2]
        })
        validator._validate_stream_continuity(gap_data)
        assert not validator.validation_results[0]['passed']
        assert 'Stream gap detected' in validator.validation_results[0]['message']

    def test_validate_message_ordering_success(self, validator, sample_data):
        validator._validate_message_ordering(sample_data)
        assert validator.validation_results[0]['passed']
        assert 'Message ordering maintained' in validator.validation_results[0]['message']

    def test_validate_message_ordering_failure(self, validator):
        unordered_data = pd.DataFrame({
            'event_timestamp': [
                datetime.now(),
                datetime.now() - timedelta(seconds=10),
                datetime.now() - timedelta(seconds=5)
            ],
            'value': [1, 2, 3]
        })
        validator._validate_message_ordering(unordered_data)
        assert not validator.validation_results[0]['passed']
        assert 'Message ordering violated' in validator.validation_results[0]['message']

    def test_update_source_health_metrics(self, validator):
        metrics = {'fetch_success': True, 'retry_attempts': 1, 'connection_drops': 0}
        validator._update_source_health_metrics(metrics)
        assert validator.source_health_metrics['total_attempts'] == 1
        assert validator.source_health_metrics['successful_fetches'] == 1
        assert validator.source_health_metrics['failed_fetches'] == 0

    def test_calculate_source_quality(self, validator, sample_data, healthy_metrics):
        validator.validate_source(sample_data, healthy_metrics)
        quality_score = validator._calculate_source_quality()
        assert 0 <= quality_score <= 1.0
        assert quality_score >= validator.config['source_health_threshold']

    def test_generate_source_health_report(self, validator, sample_data, healthy_metrics):
        validator.validate_source(sample_data, healthy_metrics)
        report = validator._generate_source_health_report()
        assert 'timestamp' in report
        assert 'source_quality_score' in report
        assert 'health_metrics' in report
        assert 'validation_results' in report
        assert 'recommendations' in report

    def test_full_validation_success(self, validator, sample_data, healthy_metrics):
        result = validator.validate_source(sample_data, healthy_metrics)
        assert result is True

    def test_full_validation_failure(self, validator, sample_data):
        bad_metrics = {
            'connection_drops': 5,
            'retry_attempts': 10,
            'messages_per_second': 50,
            'pending_messages': 2000,
            'fetch_success': False
        }
        result = validator.validate_source(sample_data, bad_metrics)
        assert result is False

    def test_validation_error_handling(self, validator):
        with pytest.raises(StreamingDataValidationError):
            validator.validate_source(None, None)