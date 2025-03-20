import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any, List

from core.services.monitoring.resource_monitor import ResourceMonitor
from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    ResourceMetrics,
    ResourceThreshold,
    ResourceAlert
)

@pytest.fixture
def mock_message_broker():
    broker = Mock(spec=MessageBroker)
    broker.subscribe = AsyncMock()
    broker.publish = AsyncMock()
    return broker

@pytest.fixture
def resource_monitor(mock_message_broker):
    return ResourceMonitor(mock_message_broker)

@pytest.fixture
def sample_metrics():
    return {
        'cpu': {
            'percent': 75.0,
            'count': 4,
            'freq': {'current': 2.5, 'min': 1.0, 'max': 3.0},
            'times': {'user': 100.0, 'system': 50.0, 'idle': 200.0}
        },
        'memory': {
            'total': 16000000000,  # 16GB
            'available': 8000000000,  # 8GB
            'percent': 85.0,
            'used': 12000000000,  # 12GB
            'free': 4000000000  # 4GB
        },
        'disk': {
            'total': 1000000000000,  # 1TB
            'used': 850000000000,  # 850GB
            'free': 150000000000,  # 150GB
            'percent': 85.0
        },
        'network': {
            'bytes_sent': 1000000,
            'bytes_recv': 2000000,
            'packets_sent': 1000,
            'packets_recv': 2000
        }
    }

@pytest.mark.asyncio
async def test_initialization(resource_monitor, mock_message_broker):
    """Test ResourceMonitor initialization"""
    assert resource_monitor.monitoring_interval == 60
    assert resource_monitor.history_window == timedelta(hours=24)
    assert resource_monitor.alert_cooldown == timedelta(minutes=5)
    assert resource_monitor.resource_history == {}
    assert resource_monitor.last_alerts == {}
    assert resource_monitor.active_monitoring == {}
    
    # Verify thresholds
    assert 'cpu' in resource_monitor.thresholds
    assert 'memory' in resource_monitor.thresholds
    assert 'disk' in resource_monitor.thresholds
    assert 'network' in resource_monitor.thresholds
    
    # Verify message broker subscriptions
    mock_message_broker.subscribe.assert_called()

@pytest.mark.asyncio
async def test_handle_monitoring_start(resource_monitor, mock_message_broker):
    """Test handling of monitoring start request"""
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_RESOURCE_START,
        content={'pipeline_id': 'test_pipeline'}
    )
    
    await resource_monitor._handle_monitoring_start(message)
    
    # Verify monitoring task was created
    assert 'test_pipeline' in resource_monitor.active_monitoring
    
    # Verify history was initialized
    assert 'test_pipeline' in resource_monitor.resource_history
    assert resource_monitor.resource_history['test_pipeline'] == []
    
    # Verify start notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_RESOURCE_START

@pytest.mark.asyncio
async def test_handle_monitoring_stop(resource_monitor, mock_message_broker):
    """Test handling of monitoring stop request"""
    # Set up active monitoring
    pipeline_id = 'test_pipeline'
    resource_monitor.active_monitoring[pipeline_id] = asyncio.create_task(
        asyncio.sleep(1)
    )
    
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_RESOURCE_STOP,
        content={'pipeline_id': pipeline_id}
    )
    
    await resource_monitor._handle_monitoring_stop(message)
    
    # Verify monitoring task was cancelled and removed
    assert pipeline_id not in resource_monitor.active_monitoring
    
    # Verify stop notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_RESOURCE_STOP

@pytest.mark.asyncio
async def test_handle_threshold_update(resource_monitor, mock_message_broker):
    """Test handling of threshold updates"""
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_THRESHOLD_UPDATE,
        content={
            'pipeline_id': 'test_pipeline',
            'thresholds': {
                'cpu': {'warning': 85.0, 'critical': 95.0},
                'memory': {'warning': 90.0, 'critical': 98.0}
            }
        }
    )
    
    await resource_monitor._handle_threshold_update(message)
    
    # Verify thresholds were updated
    assert resource_monitor.thresholds['cpu']['warning'] == 85.0
    assert resource_monitor.thresholds['cpu']['critical'] == 95.0
    assert resource_monitor.thresholds['memory']['warning'] == 90.0
    assert resource_monitor.thresholds['memory']['critical'] == 98.0
    
    # Verify threshold update notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_THRESHOLD_UPDATE

@pytest.mark.asyncio
async def test_collect_resource_metrics(resource_monitor):
    """Test resource metrics collection"""
    with patch('psutil.cpu_percent') as mock_cpu_percent, \
         patch('psutil.cpu_count') as mock_cpu_count, \
         patch('psutil.cpu_freq') as mock_cpu_freq, \
         patch('psutil.cpu_times') as mock_cpu_times, \
         patch('psutil.virtual_memory') as mock_virtual_memory, \
         patch('psutil.disk_usage') as mock_disk_usage, \
         patch('psutil.net_io_counters') as mock_net_io:
        
        # Set up mock values
        mock_cpu_percent.return_value = 75.0
        mock_cpu_count.return_value = 4
        mock_cpu_freq.return_value = Mock(current=2.5, min=1.0, max=3.0)
        mock_cpu_times.return_value = Mock(user=100.0, system=50.0, idle=200.0)
        mock_virtual_memory.return_value = Mock(
            total=16000000000,
            available=8000000000,
            percent=85.0,
            used=12000000000,
            free=4000000000
        )
        mock_disk_usage.return_value = Mock(
            total=1000000000000,
            used=850000000000,
            free=150000000000,
            percent=85.0
        )
        mock_net_io.return_value = Mock(
            bytes_sent=1000000,
            bytes_recv=2000000,
            packets_sent=1000,
            packets_recv=2000
        )
        
        # Collect metrics
        metrics = await resource_monitor._collect_resource_metrics()
        
        # Verify collected metrics
        assert metrics['cpu']['percent'] == 75.0
        assert metrics['cpu']['count'] == 4
        assert metrics['memory']['percent'] == 85.0
        assert metrics['disk']['percent'] == 85.0
        assert metrics['network']['bytes_sent'] == 1000000

@pytest.mark.asyncio
async def test_cleanup_old_metrics(resource_monitor):
    """Test cleanup of old metrics"""
    pipeline_id = 'test_pipeline'
    
    # Add old and recent metrics
    old_time = datetime.now() - timedelta(hours=25)
    recent_time = datetime.now()
    
    resource_monitor.resource_history[pipeline_id] = [
        {'timestamp': old_time, 'metrics': {'cpu': {'percent': 50.0}}},
        {'timestamp': recent_time, 'metrics': {'cpu': {'percent': 60.0}}}
    ]
    
    # Clean up old metrics
    resource_monitor._cleanup_old_metrics(pipeline_id)
    
    # Verify only recent metrics remain
    assert len(resource_monitor.resource_history[pipeline_id]) == 1
    assert resource_monitor.resource_history[pipeline_id][0]['timestamp'] == recent_time

@pytest.mark.asyncio
async def test_check_thresholds(resource_monitor, mock_message_broker, sample_metrics):
    """Test threshold checking and alert generation"""
    pipeline_id = 'test_pipeline'
    
    # Check thresholds
    await resource_monitor._check_thresholds(pipeline_id, sample_metrics)
    
    # Verify alerts were published
    mock_message_broker.publish.assert_called()
    
    # Verify alert content
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_RESOURCE_ALERT
    assert 'alert' in published_message.content
    alert = published_message.content['alert']
    assert alert.resource in ['cpu', 'memory', 'disk']
    assert alert.level in ['warning', 'critical']
    assert isinstance(alert.value, float)
    assert isinstance(alert.threshold, float)

@pytest.mark.asyncio
async def test_create_alert(resource_monitor):
    """Test alert creation"""
    alert = resource_monitor._create_alert('cpu', 'warning', 85.0)
    
    assert alert.resource == 'cpu'
    assert alert.level == 'warning'
    assert alert.value == 85.0
    assert alert.threshold == resource_monitor.thresholds['cpu']['warning']
    assert isinstance(alert.timestamp, datetime)

@pytest.mark.asyncio
async def test_publish_alerts(resource_monitor, mock_message_broker):
    """Test alert publishing with cooldown"""
    pipeline_id = 'test_pipeline'
    alerts = [
        resource_monitor._create_alert('cpu', 'warning', 85.0),
        resource_monitor._create_alert('memory', 'critical', 95.0)
    ]
    
    # Publish alerts
    await resource_monitor._publish_alerts(pipeline_id, alerts)
    
    # Verify alerts were published
    assert mock_message_broker.publish.call_count == 2
    
    # Try to publish same alerts again immediately
    await resource_monitor._publish_alerts(pipeline_id, alerts)
    
    # Verify no new alerts were published due to cooldown
    assert mock_message_broker.publish.call_count == 2

@pytest.mark.asyncio
async def test_monitor_resources(resource_monitor, mock_message_broker, sample_metrics):
    """Test resource monitoring loop"""
    pipeline_id = 'test_pipeline'
    
    # Set up monitoring task
    monitoring_task = asyncio.create_task(
        resource_monitor._monitor_resources(pipeline_id)
    )
    
    # Let it run for a short time
    await asyncio.sleep(0.1)
    
    # Cancel the task
    monitoring_task.cancel()
    
    try:
        await monitoring_task
    except asyncio.CancelledError:
        pass
    
    # Verify metrics were collected and stored
    assert pipeline_id in resource_monitor.resource_history
    assert len(resource_monitor.resource_history[pipeline_id]) > 0 