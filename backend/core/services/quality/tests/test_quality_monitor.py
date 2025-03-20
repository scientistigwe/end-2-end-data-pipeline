import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from core.services.quality.quality_monitor import QualityMonitor
from core.messaging.message_broker import MessageBroker
from core.messaging.message_types import MessageType
from core.messaging.processing_message import ProcessingMessage

@pytest.fixture
def message_broker():
    broker = Mock(spec=MessageBroker)
    broker.request = AsyncMock()
    broker.publish = AsyncMock()
    return broker

@pytest.fixture
def quality_monitor(message_broker):
    monitor = QualityMonitor(message_broker)
    return monitor

@pytest.fixture
def sample_data():
    """Create sample data for testing"""
    data = {
        'numeric': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'categorical': ['A', 'B', 'A', 'C', 'B', 'A', 'B', 'C', 'A', 'B'],
        'text': ['text1', 'text2', 'text3', 'text4', 'text5', 'text6', 'text7', 'text8', 'text9', 'text10'],
        'date': pd.date_range(start='2023-01-01', periods=10, freq='D')
    }
    return pd.DataFrame(data)

@pytest.fixture
def sample_metrics():
    """Create sample metrics for testing"""
    return {
        "total_issues": 10,
        "resolved_issues": 8,
        "quality_score": 0.8,
        "completeness": 0.95,
        "consistency": 0.9,
        "accuracy": 0.85,
        "timeliness": 0.9
    }

@pytest.mark.asyncio
async def test_initialize_service(quality_monitor):
    """Test service initialization"""
    await quality_monitor._initialize_service()
    
    # Verify message handlers are registered
    assert MessageType.QUALITY_MONITOR_START in quality_monitor._message_handlers
    assert MessageType.QUALITY_MONITOR_STOP in quality_monitor._message_handlers
    assert MessageType.QUALITY_MONITOR_STATUS in quality_monitor._message_handlers
    assert MessageType.QUALITY_MONITOR_ALERT in quality_monitor._message_handlers

@pytest.mark.asyncio
async def test_handle_monitor_start(quality_monitor, sample_data, sample_metrics):
    """Test handling monitor start message"""
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_MONITOR_START,
        content={
            "pipeline_id": "test_pipeline",
            "data_id": "test_data",
            "data": sample_data.to_dict(),
            "metrics": sample_metrics,
            "check_interval": 60,
            "thresholds": {
                "quality_score": 0.8,
                "completeness": 0.9,
                "consistency": 0.9,
                "accuracy": 0.8,
                "timeliness": 0.9
            }
        }
    )
    
    # Handle message
    response = await quality_monitor._handle_monitor_start(message)
    
    # Verify response
    assert response.success
    assert "monitor_id" in response.content
    assert response.content["pipeline_id"] == "test_pipeline"
    
    # Verify monitor was created
    monitor_id = response.content["monitor_id"]
    assert monitor_id in quality_monitor.active_monitors
    assert quality_monitor.active_monitors[monitor_id]["pipeline_id"] == "test_pipeline"

@pytest.mark.asyncio
async def test_handle_monitor_stop(quality_monitor):
    """Test handling monitor stop message"""
    # Create test monitor
    monitor_id = "test_monitor"
    quality_monitor.active_monitors[monitor_id] = {
        "pipeline_id": "test_pipeline",
        "start_time": datetime.now(),
        "status": "running"
    }
    
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_MONITOR_STOP,
        content={
            "monitor_id": monitor_id
        }
    )
    
    # Handle message
    response = await quality_monitor._handle_monitor_stop(message)
    
    # Verify response
    assert response.success
    assert monitor_id not in quality_monitor.active_monitors

@pytest.mark.asyncio
async def test_perform_quality_check(quality_monitor, sample_data, sample_metrics):
    """Test performing quality check"""
    # Create test monitor context
    context = {
        "data": sample_data,
        "metrics": sample_metrics,
        "thresholds": {
            "quality_score": 0.8,
            "completeness": 0.9,
            "consistency": 0.9,
            "accuracy": 0.8,
            "timeliness": 0.9
        }
    }
    
    # Perform check
    result = await quality_monitor._perform_quality_check(context)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "check_results" in result.content
    assert "alerts" in result.content

@pytest.mark.asyncio
async def test_check_thresholds(quality_monitor, sample_metrics):
    """Test checking thresholds"""
    # Create test thresholds
    thresholds = {
        "quality_score": 0.8,
        "completeness": 0.9,
        "consistency": 0.9,
        "accuracy": 0.8,
        "timeliness": 0.9
    }
    
    # Check thresholds
    alerts = await quality_monitor._check_thresholds(sample_metrics, thresholds)
    
    # Verify alerts
    assert isinstance(alerts, list)
    assert all(isinstance(alert, dict) for alert in alerts)
    assert all("metric" in alert and "value" in alert and "threshold" in alert for alert in alerts)

@pytest.mark.asyncio
async def test_process_alerts(quality_monitor):
    """Test processing alerts"""
    # Create test alerts
    alerts = [
        {
            "metric": "quality_score",
            "value": 0.75,
            "threshold": 0.8,
            "severity": "warning"
        },
        {
            "metric": "completeness",
            "value": 0.85,
            "threshold": 0.9,
            "severity": "critical"
        }
    ]
    
    # Process alerts
    result = await quality_monitor._process_alerts(alerts)
    
    # Verify result
    assert result is not None
    assert "processed_alerts" in result
    assert "notifications" in result
    assert len(result["processed_alerts"]) == 2
    assert len(result["notifications"]) > 0

@pytest.mark.asyncio
async def test_send_status_update(quality_monitor):
    """Test sending status update"""
    # Create test status
    status = {
        "monitor_id": "test_monitor",
        "pipeline_id": "test_pipeline",
        "status": "running",
        "last_check": datetime.now().isoformat(),
        "metrics": {"test": "metrics"}
    }
    
    # Send update
    result = await quality_monitor._send_status_update(status)
    
    # Verify result
    assert result is not None
    assert result.success
    assert quality_monitor.message_broker.publish.called

@pytest.mark.asyncio
async def test_update_monitor_metrics(quality_monitor):
    """Test updating monitor metrics"""
    # Create test metrics
    test_metrics = {
        "total_checks": 100,
        "failed_checks": 5,
        "total_alerts": 10,
        "average_duration": 1.5
    }
    
    # Update metrics
    await quality_monitor._update_monitor_metrics(test_metrics)
    
    # Verify metrics were updated
    assert quality_monitor.monitor_metrics["total_checks"] == 100
    assert quality_monitor.monitor_metrics["failed_checks"] == 5
    assert quality_monitor.monitor_metrics["total_alerts"] == 10
    assert quality_monitor.monitor_metrics["average_duration"] == 1.5
    assert "last_update" in quality_monitor.monitor_metrics

@pytest.mark.asyncio
async def test_cleanup_resources(quality_monitor):
    """Test resource cleanup"""
    # Create test monitor
    monitor_id = "test_monitor"
    quality_monitor.active_monitors[monitor_id] = {
        "pipeline_id": "test_pipeline",
        "start_time": datetime.now(),
        "status": "running"
    }
    
    # Cleanup resources
    await quality_monitor._cleanup_resources()
    
    # Verify resources were cleaned up
    assert not quality_monitor.active_monitors
    assert not quality_monitor.monitor_metrics

@pytest.mark.asyncio
async def test_error_handling(quality_monitor):
    """Test error handling"""
    # Create test message with invalid data
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_MONITOR_START,
        content={
            "pipeline_id": "test_pipeline",
            "data_id": "test_data",
            "data": None,  # Invalid data
            "metrics": None,  # Invalid metrics
            "check_interval": 60,
            "thresholds": {}
        }
    )
    
    # Handle message
    response = await quality_monitor._handle_monitor_start(message)
    
    # Verify error response
    assert not response.success
    assert "error" in response.content
    assert "Invalid data format" in response.content["error"]

@pytest.mark.asyncio
async def test_large_data_handling(quality_monitor):
    """Test handling large datasets"""
    # Create large dataset
    large_data = pd.DataFrame({
        'numeric': np.random.randn(10000),
        'categorical': np.random.choice(['A', 'B', 'C'], 10000)
    })
    
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_MONITOR_START,
        content={
            "pipeline_id": "test_pipeline",
            "data_id": "test_data",
            "data": large_data.to_dict(),
            "metrics": {"test": "metrics"},
            "check_interval": 60,
            "thresholds": {}
        }
    )
    
    # Handle message
    response = await quality_monitor._handle_monitor_start(message)
    
    # Verify response
    assert response.success
    assert "monitor_id" in response.content
    
    # Verify batch processing
    monitor_id = response.content["monitor_id"]
    assert quality_monitor.active_monitors[monitor_id]["batch_size"] <= quality_monitor.config["max_rows_per_batch"]

@pytest.mark.asyncio
async def test_concurrent_monitoring(quality_monitor):
    """Test handling multiple concurrent monitors"""
    # Create multiple test monitors
    monitor_ids = []
    for i in range(3):
        message = ProcessingMessage(
            message_type=MessageType.QUALITY_MONITOR_START,
            content={
                "pipeline_id": f"test_pipeline_{i}",
                "data_id": f"test_data_{i}",
                "data": {"test": "data"},
                "metrics": {"test": "metrics"},
                "check_interval": 60,
                "thresholds": {}
            }
        )
        response = await quality_monitor._handle_monitor_start(message)
        monitor_ids.append(response.content["monitor_id"])
    
    # Verify all monitors were created
    assert len(quality_monitor.active_monitors) == 3
    assert all(monitor_id in quality_monitor.active_monitors for monitor_id in monitor_ids)
    
    # Stop all monitors
    for monitor_id in monitor_ids:
        message = ProcessingMessage(
            message_type=MessageType.QUALITY_MONITOR_STOP,
            content={"monitor_id": monitor_id}
        )
        await quality_monitor._handle_monitor_stop(message)
    
    # Verify all monitors were stopped
    assert not quality_monitor.active_monitors 