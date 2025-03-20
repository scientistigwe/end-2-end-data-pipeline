import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any, List

from core.services.monitoring.health_checker import HealthChecker, HealthCheckType
from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    HealthStatus,
    ComponentStatus,
    HealthCheckResult
)

@pytest.fixture
def mock_message_broker():
    broker = Mock(spec=MessageBroker)
    broker.subscribe = AsyncMock()
    broker.publish = AsyncMock()
    broker.is_connected = Mock(return_value=True)
    return broker

@pytest.fixture
def health_checker(mock_message_broker):
    return HealthChecker(mock_message_broker)

@pytest.fixture
def sample_component_status():
    return {
        'component_id': 'test_component',
        'status': 'healthy',
        'timestamp': datetime.now(),
        'details': {'metric1': 100, 'metric2': 200}
    }

@pytest.mark.asyncio
async def test_initialization(health_checker, mock_message_broker):
    """Test HealthChecker initialization"""
    assert health_checker.check_interval == 60
    assert health_checker.timeout == 10
    assert health_checker.retry_count == 3
    assert health_checker.retry_delay == 5
    assert health_checker.component_status == {}
    assert health_checker.health_history == []
    assert health_checker.active_checks == {}
    
    # Verify message broker subscriptions
    mock_message_broker.subscribe.assert_called()

@pytest.mark.asyncio
async def test_handle_health_check_start(health_checker, mock_message_broker):
    """Test handling of health check start request"""
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_HEALTH_START,
        content={'pipeline_id': 'test_pipeline'}
    )
    
    await health_checker._handle_health_check_start(message)
    
    # Verify health check task was created
    assert 'test_pipeline' in health_checker.active_checks
    
    # Verify start notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_HEALTH_START

@pytest.mark.asyncio
async def test_handle_health_check_stop(health_checker, mock_message_broker):
    """Test handling of health check stop request"""
    # Set up active health check
    pipeline_id = 'test_pipeline'
    health_checker.active_checks[pipeline_id] = asyncio.create_task(
        asyncio.sleep(1)
    )
    
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_HEALTH_STOP,
        content={'pipeline_id': pipeline_id}
    )
    
    await health_checker._handle_health_check_stop(message)
    
    # Verify health check task was cancelled and removed
    assert pipeline_id not in health_checker.active_checks
    
    # Verify stop notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_HEALTH_STOP

@pytest.mark.asyncio
async def test_handle_health_check_request(health_checker, mock_message_broker):
    """Test handling of immediate health check request"""
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_HEALTH_CHECK,
        content={'pipeline_id': 'test_pipeline'}
    )
    
    await health_checker._handle_health_check_request(message)
    
    # Verify health check result was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_HEALTH_RESULT
    assert 'result' in published_message.content

@pytest.mark.asyncio
async def test_handle_component_status(health_checker, mock_message_broker, sample_component_status):
    """Test handling of component status updates"""
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_COMPONENT_STATUS,
        content=sample_component_status
    )
    
    await health_checker._handle_component_status(message)
    
    # Verify component status was updated
    assert sample_component_status['component_id'] in health_checker.component_status
    status = health_checker.component_status[sample_component_status['component_id']]
    assert status.status == sample_component_status['status']
    assert status.details == sample_component_status['details']
    
    # Verify status update notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_COMPONENT_STATUS

@pytest.mark.asyncio
async def test_check_system_resources(health_checker):
    """Test system resource checking"""
    with patch('psutil.cpu_percent') as mock_cpu_percent, \
         patch('psutil.cpu_count') as mock_cpu_count, \
         patch('psutil.virtual_memory') as mock_virtual_memory, \
         patch('psutil.disk_usage') as mock_disk_usage:
        
        # Set up mock values
        mock_cpu_percent.return_value = 50.0
        mock_cpu_count.return_value = 4
        mock_virtual_memory.return_value = Mock(percent=60.0, available=8000000000)
        mock_disk_usage.return_value = Mock(percent=70.0, free=1000000000000)
        
        # Check system resources
        result = await health_checker._check_system_resources()
        
        # Verify results
        assert result['cpu']['usage'] == 50.0
        assert result['cpu']['count'] == 4
        assert result['memory']['usage'] == 60.0
        assert result['disk']['usage'] == 70.0

@pytest.mark.asyncio
async def test_check_component_status(health_checker, sample_component_status):
    """Test component status checking"""
    # Add test component status
    health_checker.component_status[sample_component_status['component_id']] = ComponentStatus(
        **sample_component_status
    )
    
    # Check component status
    result = await health_checker._check_component_status()
    
    # Verify results
    assert sample_component_status['component_id'] in result
    component_result = result[sample_component_status['component_id']]
    assert component_result['status'] == sample_component_status['status']
    assert component_result['details'] == sample_component_status['details']

@pytest.mark.asyncio
async def test_check_service_availability(health_checker):
    """Test service availability checking"""
    with patch.object(health_checker, '_check_database_connectivity') as mock_db_check, \
         patch.object(health_checker, '_check_api_availability') as mock_api_check:
        
        # Set up mock values
        mock_db_check.return_value = True
        mock_api_check.return_value = True
        
        # Check service availability
        result = await health_checker._check_service_availability()
        
        # Verify results
        assert result['services']['message_broker'] is True
        assert result['services']['database'] is True
        assert result['services']['api'] is True
        assert result['status'] == 'healthy'

@pytest.mark.asyncio
async def test_check_network_connectivity(health_checker):
    """Test network connectivity checking"""
    with patch('aiohttp.ClientSession') as mock_session:
        # Set up mock session
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value = mock_response
        mock_session.return_value.get.return_value = mock_context
        
        # Check network connectivity
        result = await health_checker._check_network_connectivity()
        
        # Verify results
        assert result['endpoints']['api'] is True
        assert result['endpoints']['database'] is True
        assert result['status'] == 'healthy'

@pytest.mark.asyncio
async def test_determine_overall_status(health_checker):
    """Test overall status determination"""
    # Test healthy status
    healthy_statuses = [
        {'status': 'healthy'},
        {'status': 'healthy'},
        {'status': 'healthy'}
    ]
    assert health_checker._determine_overall_status(healthy_statuses) == HealthStatus.HEALTHY
    
    # Test degraded status
    degraded_statuses = [
        {'status': 'healthy'},
        {'status': 'degraded'},
        {'status': 'healthy'}
    ]
    assert health_checker._determine_overall_status(degraded_statuses) == HealthStatus.DEGRADED
    
    # Test error status
    error_statuses = [
        {'status': 'healthy'},
        {'status': 'error'},
        {'status': 'healthy'}
    ]
    assert health_checker._determine_overall_status(error_statuses) == HealthStatus.ERROR

@pytest.mark.asyncio
async def test_cleanup_old_results(health_checker):
    """Test cleanup of old health check results"""
    # Add old and recent results
    old_time = datetime.now() - timedelta(hours=25)
    recent_time = datetime.now()
    
    health_checker.health_history = [
        HealthCheckResult(
            pipeline_id='test_pipeline',
            timestamp=old_time,
            status=HealthStatus.HEALTHY,
            details={}
        ),
        HealthCheckResult(
            pipeline_id='test_pipeline',
            timestamp=recent_time,
            status=HealthStatus.HEALTHY,
            details={}
        )
    ]
    
    # Clean up old results
    health_checker._cleanup_old_results()
    
    # Verify only recent results remain
    assert len(health_checker.health_history) == 1
    assert health_checker.health_history[0].timestamp == recent_time

@pytest.mark.asyncio
async def test_perform_health_checks(health_checker, mock_message_broker):
    """Test health check loop"""
    pipeline_id = 'test_pipeline'
    
    # Set up health check task
    check_task = asyncio.create_task(
        health_checker._perform_health_checks(pipeline_id)
    )
    
    # Let it run for a short time
    await asyncio.sleep(0.1)
    
    # Cancel the task
    check_task.cancel()
    
    try:
        await check_task
    except asyncio.CancelledError:
        pass
    
    # Verify health check results were published
    mock_message_broker.publish.assert_called()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_HEALTH_RESULT 