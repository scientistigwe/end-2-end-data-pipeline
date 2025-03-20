import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import asyncio
from typing import Dict, Any

from core.services.monitoring.metrics_collector import MetricsCollector
from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    MonitoringContext,
    MetricType,
    MetricsAggregate
)

@pytest.fixture
def mock_message_broker():
    broker = Mock(spec=MessageBroker)
    broker.subscribe = AsyncMock()
    broker.publish = AsyncMock()
    return broker

@pytest.fixture
def metrics_collector(mock_message_broker):
    return MetricsCollector(mock_message_broker)

@pytest.fixture
def sample_collection_config():
    return {
        'pipeline_id': 'test_pipeline',
        'config': {
            'metric_types': [MetricType.SYSTEM, MetricType.PERFORMANCE],
            'collection_interval': 30,
            'buffer_size': 100
        }
    }

@pytest.mark.asyncio
async def test_initialization(metrics_collector, mock_message_broker):
    """Test MetricsCollector initialization"""
    assert metrics_collector.collection_interval == 60
    assert metrics_collector.buffer_size == 1000
    assert metrics_collector.active_collections == {}
    assert metrics_collector.metric_buffers == {}
    
    # Verify message broker subscriptions
    mock_message_broker.subscribe.assert_called()

@pytest.mark.asyncio
async def test_handle_collection_request(metrics_collector, mock_message_broker, sample_collection_config):
    """Test handling of collection request"""
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_METRICS_COLLECT,
        content=sample_collection_config
    )
    
    await metrics_collector._handle_collection_request(message)
    
    # Verify collection task was created
    assert 'test_pipeline' in metrics_collector.active_collections
    
    # Verify start notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_METRICS_COLLECT
    assert published_message.content['status'] == 'started'

@pytest.mark.asyncio
async def test_handle_collection_request_duplicate(metrics_collector, mock_message_broker, sample_collection_config):
    """Test handling of duplicate collection request"""
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_METRICS_COLLECT,
        content=sample_collection_config
    )
    
    # Start first collection
    await metrics_collector._handle_collection_request(message)
    
    # Try to start second collection for same pipeline
    await metrics_collector._handle_collection_request(message)
    
    # Verify only one collection task exists
    assert len(metrics_collector.active_collections) == 1

@pytest.mark.asyncio
async def test_handle_collection_request_invalid(metrics_collector, mock_message_broker):
    """Test handling of invalid collection request"""
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_METRICS_COLLECT,
        content={}  # Missing pipeline_id
    )
    
    await metrics_collector._handle_collection_request(message)
    
    # Verify error was handled
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_PROCESS_FAILED

@pytest.mark.asyncio
async def test_gather_metrics(metrics_collector):
    """Test metrics gathering"""
    context = MonitoringContext(
        pipeline_id='test_pipeline',
        metric_types=[MetricType.SYSTEM, MetricType.PERFORMANCE],
        collection_interval=30
    )
    
    with patch('psutil.cpu_percent') as mock_cpu_percent, \
         patch('psutil.virtual_memory') as mock_memory, \
         patch('psutil.disk_usage') as mock_disk, \
         patch('psutil.net_io_counters') as mock_network:
        
        # Setup mock values
        mock_cpu_percent.return_value = 50.0
        mock_memory.return_value.percent = 75.0
        mock_disk.return_value.percent = 60.0
        mock_network.return_value.bytes_sent = 1000
        mock_network.return_value.bytes_recv = 2000
        
        metrics = await metrics_collector._gather_metrics(context)
        
        # Verify metrics structure
        assert 'timestamp' in metrics
        assert 'pipeline_id' in metrics
        assert 'metrics' in metrics
        
        # Verify system metrics
        system_metrics = metrics['metrics']['system']
        assert system_metrics['cpu_percent'] == 50.0
        assert system_metrics['memory_percent'] == 75.0
        assert system_metrics['disk_usage'] == 60.0
        assert 'network_io' in system_metrics

@pytest.mark.asyncio
async def test_aggregate_metrics(metrics_collector):
    """Test metrics aggregation"""
    metrics_list = [
        {
            'metrics': {
                'system': {
                    'cpu_percent': 50.0,
                    'memory_percent': 75.0
                }
            }
        },
        {
            'metrics': {
                'system': {
                    'cpu_percent': 60.0,
                    'memory_percent': 85.0
                }
            }
        }
    ]
    
    aggregated = metrics_collector._aggregate_metrics(metrics_list)
    
    # Verify averages
    assert aggregated['system']['cpu_percent'] == 55.0
    assert aggregated['system']['memory_percent'] == 80.0

@pytest.mark.asyncio
async def test_handle_config_update(metrics_collector, mock_message_broker):
    """Test configuration update handling"""
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_CONFIG_UPDATE,
        content={
            'pipeline_id': 'test_pipeline',
            'config': {
                'collection_interval': 120,
                'buffer_size': 2000
            }
        }
    )
    
    await metrics_collector._handle_config_update(message)
    
    # Verify configuration was updated
    assert metrics_collector.collection_interval == 120
    assert metrics_collector.buffer_size == 2000
    
    # Verify update notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_CONFIG_UPDATE
    assert published_message.content['status'] == 'updated'

@pytest.mark.asyncio
async def test_handle_collection_stop(metrics_collector, mock_message_broker):
    """Test collection stop handling"""
    # Setup active collection
    context = MonitoringContext(
        pipeline_id='test_pipeline',
        metric_types=[MetricType.SYSTEM],
        collection_interval=30
    )
    collection_task = asyncio.create_task(asyncio.sleep(1))
    metrics_collector.active_collections['test_pipeline'] = collection_task
    
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_PROCESS_COMPLETE,
        content={'pipeline_id': 'test_pipeline'}
    )
    
    await metrics_collector._handle_collection_stop(message)
    
    # Verify collection was stopped
    assert 'test_pipeline' not in metrics_collector.active_collections
    
    # Verify stop notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_PROCESS_COMPLETE
    assert published_message.content['status'] == 'stopped'

@pytest.mark.asyncio
async def test_collect_metrics_loop(metrics_collector, mock_message_broker):
    """Test metrics collection loop"""
    context = MonitoringContext(
        pipeline_id='test_pipeline',
        metric_types=[MetricType.SYSTEM],
        collection_interval=0.1  # Short interval for testing
    )
    
    # Start collection
    collection_task = asyncio.create_task(metrics_collector._collect_metrics(context))
    
    # Wait for a few iterations
    await asyncio.sleep(0.5)
    
    # Cancel collection
    collection_task.cancel()
    
    try:
        await collection_task
    except asyncio.CancelledError:
        pass
    
    # Verify metrics were collected
    assert 'test_pipeline' in metrics_collector.metric_buffers
    assert len(metrics_collector.metric_buffers['test_pipeline']) > 0 