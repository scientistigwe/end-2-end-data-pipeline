import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from core.managers.quality_manager import QualityManager
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
def quality_manager(message_broker):
    manager = QualityManager(message_broker)
    return manager

@pytest.mark.asyncio
async def test_initialize_manager(quality_manager):
    """Test manager initialization"""
    await quality_manager._initialize_manager()
    
    # Verify message handlers are registered
    assert MessageType.QUALITY_PROCESS_START in quality_manager._message_handlers
    assert MessageType.QUALITY_PROCESS_COMPLETE in quality_manager._message_handlers
    assert MessageType.QUALITY_PROCESS_FAILED in quality_manager._message_handlers
    assert MessageType.QUALITY_STATUS_REQUEST in quality_manager._message_handlers
    assert MessageType.QUALITY_STATUS_RESPONSE in quality_manager._message_handlers

@pytest.mark.asyncio
async def test_handle_process_start(quality_manager):
    """Test handling process start message"""
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_PROCESS_START,
        content={
            "pipeline_id": "test_pipeline",
            "config": {"test": "config"},
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_manager._handle_process_start(message)
    
    # Verify response
    assert response.success
    assert "process_id" in response.content
    assert response.content["pipeline_id"] == "test_pipeline"
    
    # Verify process was created
    process_id = response.content["process_id"]
    assert process_id in quality_manager.active_processes
    assert quality_manager.active_processes[process_id]["pipeline_id"] == "test_pipeline"

@pytest.mark.asyncio
async def test_handle_process_complete(quality_manager):
    """Test handling process complete message"""
    # Create test process
    process_id = "test_process"
    quality_manager.active_processes[process_id] = {
        "pipeline_id": "test_pipeline",
        "start_time": datetime.now(),
        "status": "running"
    }
    
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_PROCESS_COMPLETE,
        content={
            "process_id": process_id,
            "pipeline_id": "test_pipeline",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_manager._handle_process_complete(message)
    
    # Verify response
    assert response.success
    assert response.content["process_id"] == process_id
    
    # Verify process was completed
    assert process_id not in quality_manager.active_processes
    assert process_id in quality_manager.completed_processes

@pytest.mark.asyncio
async def test_handle_process_failed(quality_manager):
    """Test handling process failed message"""
    # Create test process
    process_id = "test_process"
    quality_manager.active_processes[process_id] = {
        "pipeline_id": "test_pipeline",
        "start_time": datetime.now(),
        "status": "running"
    }
    
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_PROCESS_FAILED,
        content={
            "process_id": process_id,
            "pipeline_id": "test_pipeline",
            "error": "Test error",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_manager._handle_process_failed(message)
    
    # Verify response
    assert response.success
    assert response.content["process_id"] == process_id
    assert response.content["error"] == "Test error"
    
    # Verify process was marked as failed
    assert process_id not in quality_manager.active_processes
    assert process_id in quality_manager.failed_processes

@pytest.mark.asyncio
async def test_handle_status_request(quality_manager):
    """Test handling status request message"""
    # Create test process
    process_id = "test_process"
    quality_manager.active_processes[process_id] = {
        "pipeline_id": "test_pipeline",
        "start_time": datetime.now(),
        "status": "running"
    }
    
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_STATUS_REQUEST,
        content={
            "process_id": process_id,
            "pipeline_id": "test_pipeline",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_manager._handle_status_request(message)
    
    # Verify response
    assert response.success
    assert response.content["process_id"] == process_id
    assert response.content["status"] == "running"
    assert "start_time" in response.content
    assert "duration" in response.content

@pytest.mark.asyncio
async def test_handle_status_response(quality_manager):
    """Test handling status response message"""
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_STATUS_RESPONSE,
        content={
            "process_id": "test_process",
            "pipeline_id": "test_pipeline",
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "duration": 10.5
        }
    )
    
    # Handle message
    response = await quality_manager._handle_status_response(message)
    
    # Verify response
    assert response.success
    assert response.content["process_id"] == "test_process"
    assert response.content["status"] == "running"

@pytest.mark.asyncio
async def test_monitor_active_processes(quality_manager):
    """Test monitoring active processes"""
    # Create test process
    process_id = "test_process"
    quality_manager.active_processes[process_id] = {
        "pipeline_id": "test_pipeline",
        "start_time": datetime.now(),
        "status": "running"
    }
    
    # Start monitoring task
    monitor_task = asyncio.create_task(quality_manager._monitor_active_processes())
    
    # Wait for monitoring cycle
    await asyncio.sleep(0.1)
    
    # Cancel monitoring task
    monitor_task.cancel()
    
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    
    # Verify monitoring metrics were updated
    assert "active_processes" in quality_manager.monitoring_metrics
    assert quality_manager.monitoring_metrics["active_processes"] == 1

@pytest.mark.asyncio
async def test_monitor_process_timeouts(quality_manager):
    """Test monitoring process timeouts"""
    # Create test process with old start time
    process_id = "test_process"
    quality_manager.active_processes[process_id] = {
        "pipeline_id": "test_pipeline",
        "start_time": datetime.now().timestamp() - 3600,  # 1 hour old
        "status": "running"
    }
    
    # Start monitoring task
    monitor_task = asyncio.create_task(quality_manager._monitor_process_timeouts())
    
    # Wait for monitoring cycle
    await asyncio.sleep(0.1)
    
    # Cancel monitoring task
    monitor_task.cancel()
    
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    
    # Verify process was marked as failed due to timeout
    assert process_id not in quality_manager.active_processes
    assert process_id in quality_manager.failed_processes
    assert "timeout" in quality_manager.failed_processes[process_id]["error"]

@pytest.mark.asyncio
async def test_update_quality_metrics(quality_manager):
    """Test updating quality metrics"""
    # Create test metrics
    test_metrics = {
        "total_issues": 10,
        "resolved_issues": 8,
        "quality_score": 0.8
    }
    
    # Update metrics
    await quality_manager._update_quality_metrics(test_metrics)
    
    # Verify metrics were updated
    assert quality_manager.quality_metrics["total_issues"] == 10
    assert quality_manager.quality_metrics["resolved_issues"] == 8
    assert quality_manager.quality_metrics["quality_score"] == 0.8
    assert "last_update" in quality_manager.quality_metrics

@pytest.mark.asyncio
async def test_cleanup_resources(quality_manager):
    """Test resource cleanup"""
    # Create test processes
    process_id = "test_process"
    quality_manager.active_processes[process_id] = {
        "pipeline_id": "test_pipeline",
        "start_time": datetime.now(),
        "status": "running"
    }
    
    # Cleanup resources
    await quality_manager._cleanup_resources()
    
    # Verify resources were cleaned up
    assert not quality_manager.active_processes
    assert not quality_manager.completed_processes
    assert not quality_manager.failed_processes
    assert not quality_manager.quality_metrics
    assert not quality_manager.monitoring_metrics

@pytest.mark.asyncio
async def test_error_handling(quality_manager):
    """Test error handling"""
    # Create test message with invalid content
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_PROCESS_START,
        content={}  # Missing required fields
    )
    
    # Handle message
    response = await quality_manager._handle_process_start(message)
    
    # Verify error response
    assert not response.success
    assert "error" in response.content
    assert "Missing required fields" in response.content["error"]

@pytest.mark.asyncio
async def test_concurrent_process_handling(quality_manager):
    """Test handling concurrent processes"""
    # Create multiple test processes
    process_ids = [f"test_process_{i}" for i in range(5)]
    for process_id in process_ids:
        quality_manager.active_processes[process_id] = {
            "pipeline_id": f"test_pipeline_{i}",
            "start_time": datetime.now(),
            "status": "running"
        }
    
    # Verify concurrent process limit
    assert len(quality_manager.active_processes) <= quality_manager.config["max_concurrent_processes"]
    
    # Cleanup
    await quality_manager._cleanup_resources() 