import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any, List

from core.services.monitoring.performance_tracker import PerformanceTracker
from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    MetricType,
    PerformanceMetrics,
    PerformanceBaseline
)

@pytest.fixture
def mock_message_broker():
    broker = Mock(spec=MessageBroker)
    broker.subscribe = AsyncMock()
    broker.publish = AsyncMock()
    return broker

@pytest.fixture
def performance_tracker(mock_message_broker):
    return PerformanceTracker(mock_message_broker)

@pytest.fixture
def sample_metrics():
    return {
        'system': {
            'cpu_percent': 50.0,
            'memory_percent': 75.0,
            'disk_usage': 60.0
        },
        'performance': {
            'response_time': 0.5,
            'throughput': 1000
        }
    }

@pytest.mark.asyncio
async def test_initialization(performance_tracker, mock_message_broker):
    """Test PerformanceTracker initialization"""
    assert performance_tracker.baseline_window == timedelta(hours=24)
    assert performance_tracker.anomaly_threshold == 2.0
    assert performance_tracker.min_samples == 100
    assert performance_tracker.performance_history == {}
    assert performance_tracker.performance_baselines == {}
    
    # Verify message broker subscriptions
    mock_message_broker.subscribe.assert_called()

@pytest.mark.asyncio
async def test_handle_metrics_update(performance_tracker, mock_message_broker, sample_metrics):
    """Test handling of metrics update"""
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_METRICS_UPDATE,
        content={
            'pipeline_id': 'test_pipeline',
            'metrics': sample_metrics
        }
    )
    
    await performance_tracker._handle_metrics_update(message)
    
    # Verify metrics were stored
    assert 'test_pipeline' in performance_tracker.performance_history
    assert len(performance_tracker.performance_history['test_pipeline']) == 1
    
    # Verify stored metrics
    stored_metrics = performance_tracker.performance_history['test_pipeline'][0]
    assert 'timestamp' in stored_metrics
    assert stored_metrics['metrics'] == sample_metrics

@pytest.mark.asyncio
async def test_cleanup_old_metrics(performance_tracker):
    """Test cleanup of old metrics"""
    pipeline_id = 'test_pipeline'
    
    # Add old metrics
    old_time = datetime.now() - timedelta(hours=25)
    performance_tracker.performance_history[pipeline_id] = [
        {'timestamp': old_time, 'metrics': {'system': {'cpu_percent': 50.0}}},
        {'timestamp': datetime.now(), 'metrics': {'system': {'cpu_percent': 60.0}}}
    ]
    
    # Clean up old metrics
    performance_tracker._cleanup_old_metrics(pipeline_id)
    
    # Verify only recent metrics remain
    assert len(performance_tracker.performance_history[pipeline_id]) == 1
    assert performance_tracker.performance_history[pipeline_id][0]['timestamp'] > old_time

@pytest.mark.asyncio
async def test_extract_metrics_data(performance_tracker):
    """Test extraction of metrics data"""
    history = [
        {
            'timestamp': datetime.now(),
            'metrics': {
                'system': {'cpu_percent': 50.0, 'memory_percent': 75.0},
                'performance': {'response_time': 0.5}
            }
        },
        {
            'timestamp': datetime.now(),
            'metrics': {
                'system': {'cpu_percent': 60.0, 'memory_percent': 85.0},
                'performance': {'response_time': 0.6}
            }
        }
    ]
    
    metrics_data = performance_tracker._extract_metrics_data(history)
    
    # Verify extracted data structure
    assert 'system' in metrics_data
    assert 'performance' in metrics_data
    assert len(metrics_data['system']['cpu_percent']) == 2
    assert len(metrics_data['system']['memory_percent']) == 2
    assert len(metrics_data['performance']['response_time']) == 2

@pytest.mark.asyncio
async def test_calculate_performance_metrics(performance_tracker):
    """Test calculation of performance metrics"""
    metrics_data = {
        'system': {
            'cpu_percent': [50.0, 60.0, 55.0],
            'memory_percent': [75.0, 85.0, 80.0]
        },
        'performance': {
            'response_time': [0.5, 0.6, 0.55]
        }
    }
    
    performance_metrics = performance_tracker._calculate_performance_metrics(metrics_data)
    
    # Verify calculated metrics
    assert 'system' in performance_metrics
    assert 'performance' in performance_metrics
    
    # Check CPU metrics
    cpu_metrics = performance_metrics['system']['cpu_percent']
    assert cpu_metrics['mean'] == 55.0
    assert cpu_metrics['median'] == 55.0
    assert cpu_metrics['min'] == 50.0
    assert cpu_metrics['max'] == 60.0

@pytest.mark.asyncio
async def test_detect_anomalies(performance_tracker):
    """Test anomaly detection"""
    metrics_data = {
        'system': {
            'cpu_percent': [50.0, 60.0, 55.0, 90.0],  # 90.0 is an anomaly
            'memory_percent': [75.0, 85.0, 80.0, 95.0]  # 95.0 is an anomaly
        }
    }
    
    performance_metrics = performance_tracker._calculate_performance_metrics(metrics_data)
    anomalies = performance_tracker._detect_anomalies(metrics_data, performance_metrics)
    
    # Verify anomalies were detected
    assert 'system' in anomalies
    assert len(anomalies['system']) > 0
    
    # Check anomaly details
    for anomaly in anomalies['system']:
        assert 'metric' in anomaly
        assert 'value' in anomaly
        assert 'threshold' in anomaly
        assert 'severity' in anomaly

@pytest.mark.asyncio
async def test_compare_with_baseline(performance_tracker):
    """Test baseline comparison"""
    pipeline_id = 'test_pipeline'
    
    # Set up baseline
    baseline_metrics = {
        'system': {
            'cpu_percent': {'mean': 50.0},
            'memory_percent': {'mean': 75.0}
        }
    }
    performance_tracker.performance_baselines[pipeline_id] = baseline_metrics
    
    # Current performance metrics
    current_metrics = {
        'system': {
            'cpu_percent': {'mean': 60.0},
            'memory_percent': {'mean': 80.0}
        }
    }
    
    comparison = performance_tracker._compare_with_baseline(pipeline_id, current_metrics)
    
    # Verify comparison results
    assert comparison['status'] == 'baseline_comparison'
    assert 'system' in comparison['metrics']
    
    # Check CPU comparison
    cpu_comparison = comparison['metrics']['system']['cpu_percent']
    assert cpu_comparison['current'] == 60.0
    assert cpu_comparison['baseline'] == 50.0
    assert cpu_comparison['difference'] == 10.0
    assert cpu_comparison['percent_change'] == 20.0

@pytest.mark.asyncio
async def test_handle_performance_analysis(performance_tracker, mock_message_broker):
    """Test handling of performance analysis request"""
    # Set up test data
    pipeline_id = 'test_pipeline'
    performance_tracker.performance_history[pipeline_id] = [
        {'timestamp': datetime.now(), 'metrics': {'system': {'cpu_percent': 50.0}}}
    ] * 150  # More than min_samples
    
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_PERFORMANCE_ANALYZE,
        content={'pipeline_id': pipeline_id}
    )
    
    await performance_tracker._handle_performance_analysis(message)
    
    # Verify performance update was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_PERFORMANCE_UPDATE

@pytest.mark.asyncio
async def test_handle_baseline_update(performance_tracker, mock_message_broker):
    """Test handling of baseline update request"""
    # Set up test data
    pipeline_id = 'test_pipeline'
    performance_tracker.performance_history[pipeline_id] = [
        {'timestamp': datetime.now(), 'metrics': {'system': {'cpu_percent': 50.0}}}
    ] * 150  # More than min_samples
    
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_BASELINE_UPDATE,
        content={'pipeline_id': pipeline_id}
    )
    
    await performance_tracker._handle_baseline_update(message)
    
    # Verify baseline was updated
    assert pipeline_id in performance_tracker.performance_baselines
    
    # Verify baseline update notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_BASELINE_UPDATE 