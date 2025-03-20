import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from core.messaging.message_broker import MessageBroker
from core.messaging.message_types import MessageType
from core.messaging.processing_message import ProcessingMessage
from core.managers.insight_manager import InsightManager

@pytest.fixture
async def message_broker():
    broker = MessageBroker()
    await broker.initialize()
    return broker

@pytest.fixture
async def insight_manager(message_broker):
    manager = InsightManager(message_broker)
    await manager.initialize()
    return manager

@pytest.fixture
def sample_time_series_data():
    """Create a sample time series dataset with known patterns and anomalies"""
    dates = pd.date_range(start='2023-01-01', periods=1000, freq='H')
    
    # Create base trend
    trend = np.linspace(0, 100, 1000)
    
    # Add seasonality
    seasonal = np.sin(np.linspace(0, 20*np.pi, 1000)) * 20
    
    # Add random noise
    noise = np.random.normal(0, 5, 1000)
    
    # Add some anomalies
    anomalies = np.zeros(1000)
    anomaly_indices = [100, 300, 500, 700, 900]
    anomalies[anomaly_indices] = np.random.normal(50, 10, len(anomaly_indices))
    
    # Combine all components
    data = pd.DataFrame({
        'value': trend + seasonal + noise + anomalies,
        'trend': trend,
        'seasonal': seasonal,
        'noise': noise,
        'anomalies': anomalies
    }, index=dates)
    
    return data

@pytest.mark.asyncio
async def test_end_to_end_insight_generation(insight_manager, sample_time_series_data):
    """Test complete end-to-end insight generation process"""
    # Create insight request
    message = ProcessingMessage(
        message_type=MessageType.INSIGHT_REQUEST,
        content={
            "insight_id": "test_insight_1",
            "data": sample_time_series_data.to_dict(),
            "insight_types": ["pattern", "trend", "anomaly", "correlation", "seasonality"]
        }
    )

    # Handle request
    response = await insight_manager._handle_insight_request(message)
    assert response.message_type == MessageType.INSIGHT_START
    assert response.content["status"] == "started"

    # Wait for completion
    insight_id = response.content["insight_id"]
    while insight_manager.active_insights[insight_id]["status"] == "pending":
        await asyncio.sleep(0.1)

    # Verify results
    assert insight_manager.active_insights[insight_id]["status"] == "completed"
    insights = insight_manager.active_insights[insight_id]["insights"]
    
    # Check all insight types were generated
    assert "patterns" in insights
    assert "trends" in insights
    assert "anomalies" in insights
    assert "correlations" in insights
    assert "seasonality" in insights

@pytest.mark.asyncio
async def test_insight_generation_with_resource_management(insight_manager, sample_time_series_data):
    """Test insight generation with resource management"""
    # Create multiple concurrent requests
    requests = []
    for i in range(3):
        message = ProcessingMessage(
            message_type=MessageType.INSIGHT_REQUEST,
            content={
                "insight_id": f"test_insight_{i}",
                "data": sample_time_series_data.to_dict(),
                "insight_types": ["pattern", "trend", "anomaly"]
            }
        )
        requests.append(insight_manager._handle_insight_request(message))

    # Process all requests concurrently
    responses = await asyncio.gather(*requests)
    
    # Verify all requests were handled
    assert len(responses) == 3
    for response in responses:
        assert response.message_type == MessageType.INSIGHT_START
        assert response.content["status"] == "started"

    # Wait for all insights to complete
    insight_ids = [response.content["insight_id"] for response in responses]
    while any(insight_manager.active_insights[insight_id]["status"] == "pending" 
              for insight_id in insight_ids):
        await asyncio.sleep(0.1)

    # Verify resource cleanup
    for insight_id in insight_ids:
        assert insight_manager.active_insights[insight_id]["status"] == "completed"
        assert insight_id in insight_manager.insight_metrics

@pytest.mark.asyncio
async def test_insight_generation_with_error_handling(insight_manager):
    """Test insight generation with error handling"""
    # Create request with invalid data
    message = ProcessingMessage(
        message_type=MessageType.INSIGHT_REQUEST,
        content={
            "insight_id": "test_insight_error",
            "data": {"invalid": "data"},
            "insight_types": ["pattern", "trend", "anomaly"]
        }
    )

    # Handle request
    response = await insight_manager._handle_insight_request(message)
    assert response.message_type == MessageType.INSIGHT_FAILED
    assert "error" in response.content

    # Verify error state
    insight_id = response.content["insight_id"]
    assert insight_id not in insight_manager.active_insights
    assert insight_id not in insight_manager.insight_metrics

@pytest.mark.asyncio
async def test_insight_generation_with_backpressure(insight_manager, sample_time_series_data):
    """Test insight generation with backpressure handling"""
    # Create many concurrent requests to trigger backpressure
    requests = []
    for i in range(10):  # More than max_concurrent_insights
        message = ProcessingMessage(
            message_type=MessageType.INSIGHT_REQUEST,
            content={
                "insight_id": f"test_insight_{i}",
                "data": sample_time_series_data.to_dict(),
                "insight_types": ["pattern", "trend", "anomaly"]
            }
        )
        requests.append(insight_manager._handle_insight_request(message))

    # Process requests
    responses = await asyncio.gather(*requests)
    
    # Verify backpressure handling
    assert any(response.message_type == MessageType.INSIGHT_FAILED 
              for response in responses)
    assert len(insight_manager.active_insights) <= insight_manager.config["max_concurrent_insights"]

@pytest.mark.asyncio
async def test_insight_generation_with_timeout(insight_manager, sample_time_series_data):
    """Test insight generation with timeout handling"""
    # Create request with very small timeout
    insight_manager.config["timeout_seconds"] = 0.1
    
    message = ProcessingMessage(
        message_type=MessageType.INSIGHT_REQUEST,
        content={
            "insight_id": "test_insight_timeout",
            "data": sample_time_series_data.to_dict(),
            "insight_types": ["pattern", "trend", "anomaly"]
        }
    )

    # Handle request
    response = await insight_manager._handle_insight_request(message)
    assert response.message_type == MessageType.INSIGHT_START

    # Wait for timeout
    await asyncio.sleep(0.2)

    # Verify timeout handling
    insight_id = response.content["insight_id"]
    assert insight_id not in insight_manager.active_insights
    assert insight_id not in insight_manager.insight_metrics

@pytest.mark.asyncio
async def test_insight_generation_with_metrics(insight_manager, sample_time_series_data):
    """Test insight generation with metrics collection"""
    message = ProcessingMessage(
        message_type=MessageType.INSIGHT_REQUEST,
        content={
            "insight_id": "test_insight_metrics",
            "data": sample_time_series_data.to_dict(),
            "insight_types": ["pattern", "trend", "anomaly"]
        }
    )

    # Handle request
    response = await insight_manager._handle_insight_request(message)
    insight_id = response.content["insight_id"]

    # Wait for completion
    while insight_manager.active_insights[insight_id]["status"] == "pending":
        await asyncio.sleep(0.1)

    # Verify metrics
    assert insight_id in insight_manager.insight_metrics
    metrics = insight_manager.insight_metrics[insight_id]
    
    assert "duration" in metrics
    assert "status" in metrics
    assert "insight_types" in metrics
    assert metrics["status"] == "completed"
    assert metrics["duration"] > 0

@pytest.mark.asyncio
async def test_insight_generation_with_large_data(insight_manager):
    """Test insight generation with large dataset"""
    # Create a large dataset
    dates = pd.date_range(start='2023-01-01', periods=10000, freq='H')
    large_data = pd.DataFrame({
        "value": np.random.randn(10000).cumsum(),
        "seasonal": np.sin(np.linspace(0, 200*np.pi, 10000)) * 100,
        "noise": np.random.randn(10000) * 0.1
    }, index=dates)
    large_data['total'] = large_data['value'] + large_data['seasonal'] + large_data['noise']

    message = ProcessingMessage(
        message_type=MessageType.INSIGHT_REQUEST,
        content={
            "insight_id": "test_insight_large",
            "data": large_data.to_dict(),
            "insight_types": ["pattern", "trend", "anomaly"]
        }
    )

    # Handle request
    response = await insight_manager._handle_insight_request(message)
    insight_id = response.content["insight_id"]

    # Wait for completion
    while insight_manager.active_insights[insight_id]["status"] == "pending":
        await asyncio.sleep(0.1)

    # Verify results
    assert insight_manager.active_insights[insight_id]["status"] == "completed"
    insights = insight_manager.active_insights[insight_id]["insights"]
    
    # Check memory usage in metrics
    metrics = insight_manager.insight_metrics[insight_id]
    assert metrics["duration"] > 0
    assert metrics["status"] == "completed"

@pytest.mark.asyncio
async def test_insight_generation_with_custom_config(insight_manager, sample_time_series_data):
    """Test insight generation with custom configuration"""
    # Update configuration
    insight_manager.config.update({
        "pattern_detection": {
            "min_pattern_length": 5,
            "max_pattern_length": 15,
            "similarity_threshold": 0.9
        },
        "trend_analysis": {
            "window_size": 50,
            "min_trend_length": 10,
            "significance_level": 0.01
        },
        "anomaly_detection": {
            "contamination": 0.05,
            "random_state": 42
        }
    })

    message = ProcessingMessage(
        message_type=MessageType.INSIGHT_REQUEST,
        content={
            "insight_id": "test_insight_config",
            "data": sample_time_series_data.to_dict(),
            "insight_types": ["pattern", "trend", "anomaly"]
        }
    )

    # Handle request
    response = await insight_manager._handle_insight_request(message)
    insight_id = response.content["insight_id"]

    # Wait for completion
    while insight_manager.active_insights[insight_id]["status"] == "pending":
        await asyncio.sleep(0.1)

    # Verify results with custom config
    insights = insight_manager.active_insights[insight_id]["insights"]
    
    # Check pattern detection results
    patterns = insights["patterns"]
    for pattern in patterns.values():
        assert pattern["size"] >= 5
        assert pattern["size"] <= 15

    # Check trend analysis results
    trends = insights["trends"]
    for trend in trends.values():
        assert trend["magnitude"] > 0
        assert "stationarity" in trend

    # Check anomaly detection results
    anomalies = insights["anomalies"]
    assert len(anomalies) <= int(len(sample_time_series_data) * 0.05)  # contamination check 