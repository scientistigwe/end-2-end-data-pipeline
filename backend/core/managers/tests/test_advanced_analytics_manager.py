import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from core.messaging.message_types import MessageType
from core.messaging.processing_message import ProcessingMessage
from core.managers.advanced_analytics_manager import AdvancedAnalyticsManager

@pytest.fixture
def message_broker():
    broker = Mock()
    broker.request = AsyncMock()
    broker.publish = AsyncMock()
    return broker

@pytest.fixture
def advanced_analytics_manager(message_broker):
    manager = AdvancedAnalyticsManager(message_broker)
    return manager

@pytest.fixture
def sample_data():
    # Create sample data for testing
    np.random.seed(42)
    data = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 100),
        'feature2': np.random.normal(0, 1, 100),
        'target': np.random.normal(0, 1, 100)
    })
    return data

@pytest.mark.asyncio
async def test_initialize_manager(advanced_analytics_manager):
    """Test manager initialization"""
    assert advanced_analytics_manager.message_broker is not None
    assert advanced_analytics_manager.active_processes == {}
    assert advanced_analytics_manager.completed_processes == {}
    assert advanced_analytics_manager.failed_processes == {}
    assert advanced_analytics_manager.analytics_metrics == {}

@pytest.mark.asyncio
async def test_handle_process_start(advanced_analytics_manager):
    """Test handling of process start message"""
    # Create process start request
    request = ProcessingMessage(
        message_type=MessageType.ANALYTICS_PROCESS_START,
        content={
            "pipeline_id": "pipeline_123",
            "config": {
                "max_retries": 3,
                "timeout_seconds": 300,
                "batch_size": 1000
            },
            "timestamp": datetime.now().isoformat()
        }
    )

    # Handle request
    response = await advanced_analytics_manager._handle_process_start(request)

    # Verify response
    assert response.success
    assert "process_id" in response.content
    assert response.content["process_id"] in advanced_analytics_manager.active_processes

@pytest.mark.asyncio
async def test_handle_process_complete(advanced_analytics_manager):
    """Test handling of process complete message"""
    # Add process to active processes
    process_id = "process_123"
    advanced_analytics_manager.active_processes[process_id] = {
        "pipeline_id": "pipeline_123",
        "start_time": datetime.now(),
        "config": {}
    }

    # Create process complete request
    request = ProcessingMessage(
        message_type=MessageType.ANALYTICS_PROCESS_COMPLETE,
        content={
            "process_id": process_id,
            "timestamp": datetime.now().isoformat()
        }
    )

    # Handle request
    response = await advanced_analytics_manager._handle_process_complete(request)

    # Verify response
    assert response.success
    assert process_id not in advanced_analytics_manager.active_processes
    assert process_id in advanced_analytics_manager.completed_processes

@pytest.mark.asyncio
async def test_handle_process_failed(advanced_analytics_manager):
    """Test handling of process failed message"""
    # Add process to active processes
    process_id = "process_123"
    advanced_analytics_manager.active_processes[process_id] = {
        "pipeline_id": "pipeline_123",
        "start_time": datetime.now(),
        "config": {}
    }

    # Create process failed request
    request = ProcessingMessage(
        message_type=MessageType.ANALYTICS_PROCESS_FAILED,
        content={
            "process_id": process_id,
            "error": "Test error",
            "timestamp": datetime.now().isoformat()
        }
    )

    # Handle request
    response = await advanced_analytics_manager._handle_process_failed(request)

    # Verify response
    assert response.success
    assert process_id not in advanced_analytics_manager.active_processes
    assert process_id in advanced_analytics_manager.failed_processes
    assert advanced_analytics_manager.failed_processes[process_id]["error"] == "Test error"

@pytest.mark.asyncio
async def test_handle_status_request(advanced_analytics_manager):
    """Test handling of status request message"""
    # Add processes to manager
    process_id = "process_123"
    advanced_analytics_manager.active_processes[process_id] = {
        "pipeline_id": "pipeline_123",
        "start_time": datetime.now(),
        "config": {}
    }
    advanced_analytics_manager.completed_processes["process_456"] = {
        "pipeline_id": "pipeline_123",
        "start_time": datetime.now(),
        "end_time": datetime.now(),
        "config": {}
    }

    # Create status request
    request = ProcessingMessage(
        message_type=MessageType.ANALYTICS_STATUS_REQUEST,
        content={
            "pipeline_id": "pipeline_123",
            "timestamp": datetime.now().isoformat()
        }
    )

    # Handle request
    response = await advanced_analytics_manager._handle_status_request(request)

    # Verify response
    assert response.success
    assert "status" in response.content
    assert response.content["status"]["active_processes"] == 1
    assert response.content["status"]["completed_processes"] == 1
    assert response.content["status"]["failed_processes"] == 0

@pytest.mark.asyncio
async def test_handle_analysis_request(advanced_analytics_manager, sample_data):
    """Test handling of analysis request message"""
    # Create analysis request
    request = ProcessingMessage(
        message_type=MessageType.ANALYTICS_ANALYSIS_REQUEST,
        content={
            "pipeline_id": "pipeline_123",
            "data_id": "data_456",
            "analysis_type": "comprehensive",
            "data": sample_data.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    )

    # Handle request
    response = await advanced_analytics_manager._handle_analysis_request(request)

    # Verify response
    assert response.success
    assert "analysis_id" in response.content
    assert response.content["analysis_id"] in advanced_analytics_manager.active_analyses

@pytest.mark.asyncio
async def test_perform_comprehensive_analysis(advanced_analytics_manager, sample_data):
    """Test performing comprehensive analysis"""
    # Create analysis request
    request = ProcessingMessage(
        message_type=MessageType.ANALYTICS_ANALYSIS_REQUEST,
        content={
            "pipeline_id": "pipeline_123",
            "data_id": "data_456",
            "analysis_type": "comprehensive",
            "data": sample_data.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    )

    # Handle request
    response = await advanced_analytics_manager._handle_analysis_request(request)
    analysis_id = response.content["analysis_id"]

    # Perform analysis
    result = await advanced_analytics_manager._perform_comprehensive_analysis(
        analysis_id,
        sample_data
    )

    # Verify result
    assert result is not None
    assert "statistical_analysis" in result
    assert "predictive_analysis" in result
    assert "clustering_analysis" in result

@pytest.mark.asyncio
async def test_perform_statistical_analysis(advanced_analytics_manager, sample_data):
    """Test performing statistical analysis"""
    # Create analysis request
    request = ProcessingMessage(
        message_type=MessageType.ANALYTICS_ANALYSIS_REQUEST,
        content={
            "pipeline_id": "pipeline_123",
            "data_id": "data_456",
            "analysis_type": "statistical",
            "data": sample_data.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    )

    # Handle request
    response = await advanced_analytics_manager._handle_analysis_request(request)
    analysis_id = response.content["analysis_id"]

    # Perform analysis
    result = await advanced_analytics_manager._perform_statistical_analysis(
        analysis_id,
        sample_data
    )

    # Verify result
    assert result is not None
    assert "basic_stats" in result
    assert "correlation_matrix" in result
    assert "distribution_stats" in result

@pytest.mark.asyncio
async def test_perform_predictive_analysis(advanced_analytics_manager, sample_data):
    """Test performing predictive analysis"""
    # Create analysis request
    request = ProcessingMessage(
        message_type=MessageType.ANALYTICS_ANALYSIS_REQUEST,
        content={
            "pipeline_id": "pipeline_123",
            "data_id": "data_456",
            "analysis_type": "predictive",
            "data": sample_data.to_dict(),
            "target_column": "target",
            "timestamp": datetime.now().isoformat()
        }
    )

    # Handle request
    response = await advanced_analytics_manager._handle_analysis_request(request)
    analysis_id = response.content["analysis_id"]

    # Perform analysis
    result = await advanced_analytics_manager._perform_predictive_analysis(
        analysis_id,
        sample_data,
        "target"
    )

    # Verify result
    assert result is not None
    assert "feature_importance" in result
    assert "model_performance" in result
    assert "predictions" in result

@pytest.mark.asyncio
async def test_perform_clustering_analysis(advanced_analytics_manager, sample_data):
    """Test performing clustering analysis"""
    # Create analysis request
    request = ProcessingMessage(
        message_type=MessageType.ANALYTICS_ANALYSIS_REQUEST,
        content={
            "pipeline_id": "pipeline_123",
            "data_id": "data_456",
            "analysis_type": "clustering",
            "data": sample_data.to_dict(),
            "n_clusters": 5,
            "timestamp": datetime.now().isoformat()
        }
    )

    # Handle request
    response = await advanced_analytics_manager._handle_analysis_request(request)
    analysis_id = response.content["analysis_id"]

    # Perform analysis
    result = await advanced_analytics_manager._perform_clustering_analysis(
        analysis_id,
        sample_data,
        5
    )

    # Verify result
    assert result is not None
    assert "cluster_labels" in result
    assert "cluster_centers" in result
    assert "cluster_metrics" in result

@pytest.mark.asyncio
async def test_monitor_active_analyses(advanced_analytics_manager, sample_data):
    """Test monitoring of active analyses"""
    # Add analysis to active analyses
    analysis_id = "analysis_123"
    advanced_analytics_manager.active_analyses[analysis_id] = {
        "pipeline_id": "pipeline_123",
        "data_id": "data_456",
        "start_time": datetime.now(),
        "data": sample_data,
        "analysis_type": "comprehensive"
    }

    # Monitor analyses
    await advanced_analytics_manager._monitor_active_analyses()

    # Verify metrics update
    assert analysis_id in advanced_analytics_manager.analytics_metrics
    assert "duration" in advanced_analytics_manager.analytics_metrics[analysis_id]
    assert "status" in advanced_analytics_manager.analytics_metrics[analysis_id]

@pytest.mark.asyncio
async def test_monitor_analysis_timeouts(advanced_analytics_manager, sample_data):
    """Test monitoring of analysis timeouts"""
    # Add analysis to active analyses with old start time
    analysis_id = "analysis_123"
    advanced_analytics_manager.active_analyses[analysis_id] = {
        "pipeline_id": "pipeline_123",
        "data_id": "data_456",
        "start_time": datetime.now().replace(hour=0, minute=0, second=0),
        "data": sample_data,
        "analysis_type": "comprehensive"
    }

    # Monitor timeouts
    await advanced_analytics_manager._monitor_analysis_timeouts()

    # Verify analysis marked as failed
    assert analysis_id not in advanced_analytics_manager.active_analyses
    assert analysis_id in advanced_analytics_manager.failed_analyses
    assert "timeout" in advanced_analytics_manager.failed_analyses[analysis_id]["error"]

@pytest.mark.asyncio
async def test_update_analytics_metrics(advanced_analytics_manager):
    """Test updating analytics metrics"""
    # Add analysis to active analyses
    analysis_id = "analysis_123"
    advanced_analytics_manager.active_analyses[analysis_id] = {
        "pipeline_id": "pipeline_123",
        "data_id": "data_456",
        "start_time": datetime.now(),
        "analysis_type": "comprehensive"
    }

    # Update metrics
    await advanced_analytics_manager._update_analytics_metrics(analysis_id)

    # Verify metrics update
    assert analysis_id in advanced_analytics_manager.analytics_metrics
    assert "duration" in advanced_analytics_manager.analytics_metrics[analysis_id]
    assert "status" in advanced_analytics_manager.analytics_metrics[analysis_id]

@pytest.mark.asyncio
async def test_cleanup_resources(advanced_analytics_manager):
    """Test cleanup of resources"""
    # Add processes and analyses
    process_id = "process_123"
    analysis_id = "analysis_123"
    advanced_analytics_manager.active_processes[process_id] = {}
    advanced_analytics_manager.active_analyses[analysis_id] = {}
    advanced_analytics_manager.analytics_metrics[analysis_id] = {}

    # Cleanup resources
    await advanced_analytics_manager._cleanup_resources()

    # Verify cleanup
    assert not advanced_analytics_manager.active_processes
    assert not advanced_analytics_manager.active_analyses
    assert not advanced_analytics_manager.analytics_metrics

@pytest.mark.asyncio
async def test_error_handling(advanced_analytics_manager):
    """Test error handling"""
    # Create invalid request
    request = ProcessingMessage(
        message_type=MessageType.ANALYTICS_ANALYSIS_REQUEST,
        content={
            "pipeline_id": "pipeline_123",
            "data_id": "data_456",
            "analysis_type": "invalid_type",
            "timestamp": datetime.now().isoformat()
        }
    )

    # Handle request
    response = await advanced_analytics_manager._handle_analysis_request(request)

    # Verify error response
    assert not response.success
    assert "error" in response.content
    assert "Invalid analysis type" in response.content["error"]

@pytest.mark.asyncio
async def test_large_data_handling(advanced_analytics_manager):
    """Test handling of large datasets"""
    # Create large dataset
    large_data = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 10000),
        'feature2': np.random.normal(0, 1, 10000),
        'target': np.random.normal(0, 1, 10000)
    })

    # Create analysis request
    request = ProcessingMessage(
        message_type=MessageType.ANALYTICS_ANALYSIS_REQUEST,
        content={
            "pipeline_id": "pipeline_123",
            "data_id": "data_456",
            "analysis_type": "comprehensive",
            "data": large_data.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    )

    # Handle request
    response = await advanced_analytics_manager._handle_analysis_request(request)
    analysis_id = response.content["analysis_id"]

    # Verify batch processing
    assert analysis_id in advanced_analytics_manager.active_analyses
    assert advanced_analytics_manager.active_analyses[analysis_id]["batch_size"] == 1000

@pytest.mark.asyncio
async def test_concurrent_analysis_handling(advanced_analytics_manager, sample_data):
    """Test handling of concurrent analyses"""
    # Create multiple analysis requests
    requests = []
    for i in range(6):  # Exceed max_concurrent_analyses
        request = ProcessingMessage(
            message_type=MessageType.ANALYTICS_ANALYSIS_REQUEST,
            content={
                "pipeline_id": f"pipeline_{i}",
                "data_id": f"data_{i}",
                "analysis_type": "comprehensive",
                "data": sample_data.to_dict(),
                "timestamp": datetime.now().isoformat()
            }
        )
        requests.append(request)

    # Handle requests
    responses = []
    for request in requests:
        response = await advanced_analytics_manager._handle_analysis_request(request)
        responses.append(response)

    # Verify concurrent analysis limit
    active_analyses = len(advanced_analytics_manager.active_analyses)
    assert active_analyses <= 5  # max_concurrent_analyses 