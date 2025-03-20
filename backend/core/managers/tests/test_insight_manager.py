import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from core.messaging.message_broker import MessageBroker
from core.messaging.message_types import MessageType
from core.messaging.processing_message import ProcessingMessage
from core.managers.insight_manager import InsightManager

@pytest.fixture
def message_broker():
    broker = MagicMock(spec=MessageBroker)
    broker.request = AsyncMock()
    broker.publish = AsyncMock()
    return broker

@pytest.fixture
def insight_manager(message_broker):
    manager = InsightManager(message_broker)
    return manager

@pytest.fixture
def sample_data():
    # Create sample time series data
    dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
    data = pd.DataFrame({
        'value': np.random.randn(100).cumsum(),
        'seasonal': np.sin(np.linspace(0, 4*np.pi, 100)) * 10,
        'noise': np.random.randn(100) * 0.1
    }, index=dates)
    data['total'] = data['value'] + data['seasonal'] + data['noise']
    return data

@pytest.mark.asyncio
async def test_initialize_manager(insight_manager):
    """Test manager initialization"""
    await insight_manager._initialize_manager()
    assert len(insight_manager.message_handlers) > 0
    assert MessageType.INSIGHT_REQUEST in insight_manager.message_handlers

@pytest.mark.asyncio
async def test_handle_insight_request(insight_manager, sample_data):
    """Test handling of insight request message"""
    message = ProcessingMessage(
        message_type=MessageType.INSIGHT_REQUEST,
        content={
            "insight_id": "test_insight_1",
            "data": sample_data.to_dict(),
            "insight_types": ["pattern", "trend", "anomaly"]
        }
    )

    response = await insight_manager._handle_insight_request(message)
    assert response.message_type == MessageType.INSIGHT_START
    assert response.content["insight_id"] == "test_insight_1"
    assert response.content["status"] == "started"

@pytest.mark.asyncio
async def test_detect_patterns(insight_manager, sample_data):
    """Test pattern detection"""
    result = await insight_manager._detect_patterns(sample_data)
    
    assert "patterns" in result
    assert "pattern_count" in result
    assert "timestamp" in result
    assert isinstance(result["patterns"], dict)
    assert isinstance(result["pattern_count"], int)

@pytest.mark.asyncio
async def test_analyze_trends(insight_manager, sample_data):
    """Test trend analysis"""
    result = await insight_manager._analyze_trends(sample_data)
    
    assert "trends" in result
    assert "trend_count" in result
    assert "timestamp" in result
    assert isinstance(result["trends"], dict)
    assert isinstance(result["trend_count"], int)

    # Check trend properties
    for column, trend in result["trends"].items():
        assert "direction" in trend
        assert "magnitude" in trend
        assert "stationarity" in trend
        assert "seasonality" in trend
        assert "residuals" in trend

@pytest.mark.asyncio
async def test_detect_anomalies(insight_manager, sample_data):
    """Test anomaly detection"""
    result = await insight_manager._detect_anomalies(sample_data)
    
    assert "anomalies" in result
    assert "anomaly_count" in result
    assert "timestamp" in result
    assert isinstance(result["anomalies"], dict)
    assert isinstance(result["anomaly_count"], int)

    # Check anomaly properties
    for anomaly_id, anomaly in result["anomalies"].items():
        assert "index" in anomaly
        assert "values" in anomaly
        assert "score" in anomaly

@pytest.mark.asyncio
async def test_start_insight_generation(insight_manager, sample_data):
    """Test starting insight generation process"""
    insight_id = "test_insight_1"
    insight_manager.active_insights[insight_id] = {
        "insight_id": insight_id,
        "data": sample_data,
        "insight_types": ["pattern", "trend", "anomaly"],
        "start_time": datetime.now(),
        "status": "pending"
    }

    await insight_manager._start_insight_generation(insight_id)
    
    assert insight_manager.active_insights[insight_id]["status"] == "completed"
    assert "insights" in insight_manager.active_insights[insight_id]

@pytest.mark.asyncio
async def test_update_insight_metrics(insight_manager):
    """Test updating insight metrics"""
    insight_id = "test_insight_1"
    start_time = datetime.now()
    end_time = datetime.now()
    
    insight_manager.active_insights[insight_id] = {
        "start_time": start_time,
        "end_time": end_time,
        "status": "completed",
        "insight_types": ["pattern", "trend", "anomaly"]
    }

    await insight_manager._update_insight_metrics(insight_id)
    
    assert insight_id in insight_manager.insight_metrics
    assert "duration" in insight_manager.insight_metrics[insight_id]
    assert "status" in insight_manager.insight_metrics[insight_id]
    assert "insight_types" in insight_manager.insight_metrics[insight_id]

@pytest.mark.asyncio
async def test_cleanup_resources(insight_manager):
    """Test cleanup of manager resources"""
    # Add some test data
    insight_manager.active_insights["test_insight_1"] = {}
    insight_manager.insight_metrics["test_insight_1"] = {}

    await insight_manager._cleanup_resources()
    
    assert len(insight_manager.active_insights) == 0
    assert len(insight_manager.insight_metrics) == 0

@pytest.mark.asyncio
async def test_error_handling(insight_manager):
    """Test error handling in insight process"""
    message = ProcessingMessage(
        message_type=MessageType.INSIGHT_REQUEST,
        content={
            "insight_id": "test_insight_1",
            "data": {},  # Invalid data
            "insight_types": ["pattern", "trend", "anomaly"]
        }
    )

    response = await insight_manager._handle_insight_request(message)
    assert response.message_type == MessageType.INSIGHT_FAILED
    assert "error" in response.content

@pytest.mark.asyncio
async def test_large_data_handling(insight_manager):
    """Test handling of large datasets"""
    # Create a large dataset
    large_data = pd.DataFrame({
        "value": np.random.randn(10000).cumsum(),
        "seasonal": np.sin(np.linspace(0, 40*np.pi, 10000)) * 10,
        "noise": np.random.randn(10000) * 0.1
    })
    large_data['total'] = large_data['value'] + large_data['seasonal'] + large_data['noise']

    insight_id = "test_insight_1"
    insight_manager.active_insights[insight_id] = {
        "insight_id": insight_id,
        "data": large_data,
        "insight_types": ["pattern", "trend", "anomaly"],
        "start_time": datetime.now(),
        "status": "pending"
    }

    await insight_manager._start_insight_generation(insight_id)
    
    assert insight_manager.active_insights[insight_id]["status"] == "completed"
    assert "insights" in insight_manager.active_insights[insight_id]

@pytest.mark.asyncio
async def test_concurrent_insight_handling(insight_manager, sample_data):
    """Test handling of concurrent insight requests"""
    insight_ids = [f"test_insight_{i}" for i in range(3)]
    
    for insight_id in insight_ids:
        insight_manager.active_insights[insight_id] = {
            "insight_id": insight_id,
            "data": sample_data,
            "insight_types": ["pattern", "trend", "anomaly"],
            "start_time": datetime.now(),
            "status": "pending"
        }

    # Start all insights concurrently
    await asyncio.gather(*[
        insight_manager._start_insight_generation(insight_id)
        for insight_id in insight_ids
    ])

    # Verify all insights completed successfully
    for insight_id in insight_ids:
        assert insight_manager.active_insights[insight_id]["status"] == "completed"
        assert "insights" in insight_manager.active_insights[insight_id]

@pytest.mark.asyncio
async def test_validate_insight_request(insight_manager):
    """Test validation of insight request"""
    content = {
        "insight_id": "test_insight_1",
        "data": pd.DataFrame().to_dict(),
        "insight_types": ["pattern", "trend", "anomaly"]
    }
    
    assert insight_manager._validate_insight_request(content)

    invalid_content = {
        "insight_id": "test_insight_1",
        "data": {}  # Missing required fields
    }
    
    assert not insight_manager._validate_insight_request(invalid_content) 