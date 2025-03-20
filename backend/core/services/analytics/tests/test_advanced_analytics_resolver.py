import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from core.messaging.message_broker import MessageBroker
from core.messaging.message_types import MessageType
from core.messaging.processing_message import ProcessingMessage
from core.services.analytics.advanced_analytics_resolver import AdvancedAnalyticsResolver

@pytest.fixture
def message_broker():
    broker = MagicMock(spec=MessageBroker)
    broker.request = AsyncMock()
    broker.publish = AsyncMock()
    return broker

@pytest.fixture
def advanced_analytics_resolver(message_broker):
    resolver = AdvancedAnalyticsResolver(message_broker)
    return resolver

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "column1": [1, 2, np.nan, 4, 5],
        "column2": [10, 20, 30, 40, 50],
        "column3": [100, 200, 300, 400, 500]
    })

@pytest.mark.asyncio
async def test_initialize_service(advanced_analytics_resolver):
    """Test service initialization"""
    await advanced_analytics_resolver._initialize_service()
    assert len(advanced_analytics_resolver.message_handlers) > 0
    assert MessageType.ANALYTICS_RESOLUTION_REQUEST in advanced_analytics_resolver.message_handlers

@pytest.mark.asyncio
async def test_handle_resolution_request(advanced_analytics_resolver, sample_data):
    """Test handling of resolution request message"""
    message = ProcessingMessage(
        message_type=MessageType.ANALYTICS_RESOLUTION_REQUEST,
        content={
            "resolution_id": "test_resolution_1",
            "analysis_id": "test_analysis_1",
            "data": sample_data.to_dict(),
            "issues": [
                {
                    "type": "missing_values",
                    "affected_columns": ["column1"]
                }
            ]
        }
    )

    response = await advanced_analytics_resolver._handle_resolution_request(message)
    assert response.message_type == MessageType.ANALYTICS_RESOLUTION_START
    assert response.content["resolution_id"] == "test_resolution_1"
    assert response.content["status"] == "started"

@pytest.mark.asyncio
async def test_resolve_missing_values(advanced_analytics_resolver, sample_data):
    """Test resolution of missing values"""
    result = await advanced_analytics_resolver._resolve_missing_values(
        sample_data,
        ["column1"],
        {"strategy": "mean"}
    )

    assert "resolved_data" in result
    assert "metrics" in result
    assert not result["resolved_data"]["column1"].isnull().any()
    assert "column1_missing_ratio" in result["metrics"]

@pytest.mark.asyncio
async def test_resolve_outliers(advanced_analytics_resolver, sample_data):
    """Test resolution of outliers"""
    # Add some outliers to the data
    sample_data.loc[5] = [1000, 1000, 1000]
    
    result = await advanced_analytics_resolver._resolve_outliers(
        sample_data,
        ["column1", "column2", "column3"],
        {"threshold": 3.0, "method": "isolation_forest"}
    )

    assert "resolved_data" in result
    assert "metrics" in result
    assert "column1_outlier_ratio" in result["metrics"]
    assert "column2_outlier_ratio" in result["metrics"]
    assert "column3_outlier_ratio" in result["metrics"]

@pytest.mark.asyncio
async def test_resolve_inconsistencies(advanced_analytics_resolver, sample_data):
    """Test resolution of inconsistencies"""
    # Add some inconsistent values
    sample_data.loc[5] = [1, 1, 1]
    sample_data.loc[6] = [1, 1, 1]
    
    result = await advanced_analytics_resolver._resolve_inconsistencies(
        sample_data,
        ["column1", "column2", "column3"],
        {"threshold": 0.95, "method": "statistical"}
    )

    assert "resolved_data" in result
    assert "metrics" in result
    assert "column1_consistency_ratio" in result["metrics"]
    assert "column2_consistency_ratio" in result["metrics"]
    assert "column3_consistency_ratio" in result["metrics"]

@pytest.mark.asyncio
async def test_start_resolution(advanced_analytics_resolver, sample_data):
    """Test starting resolution process"""
    resolution_id = "test_resolution_1"
    advanced_analytics_resolver.active_resolutions[resolution_id] = {
        "resolution_id": resolution_id,
        "analysis_id": "test_analysis_1",
        "issues": [
            {
                "type": "missing_values",
                "affected_columns": ["column1"]
            }
        ],
        "data": sample_data,
        "start_time": datetime.now(),
        "status": "pending"
    }

    await advanced_analytics_resolver._start_resolution(resolution_id)
    
    assert advanced_analytics_resolver.active_resolutions[resolution_id]["status"] == "completed"
    assert "resolved_data" in advanced_analytics_resolver.active_resolutions[resolution_id]
    assert "resolution_results" in advanced_analytics_resolver.active_resolutions[resolution_id]

@pytest.mark.asyncio
async def test_update_resolution_metrics(advanced_analytics_resolver):
    """Test updating resolution metrics"""
    resolution_id = "test_resolution_1"
    start_time = datetime.now()
    end_time = datetime.now()
    
    advanced_analytics_resolver.active_resolutions[resolution_id] = {
        "start_time": start_time,
        "end_time": end_time,
        "status": "completed",
        "issues": []
    }

    await advanced_analytics_resolver._update_resolution_metrics(resolution_id)
    
    assert resolution_id in advanced_analytics_resolver.resolution_metrics
    assert "duration" in advanced_analytics_resolver.resolution_metrics[resolution_id]
    assert "status" in advanced_analytics_resolver.resolution_metrics[resolution_id]
    assert "issues_resolved" in advanced_analytics_resolver.resolution_metrics[resolution_id]

@pytest.mark.asyncio
async def test_cleanup_resources(advanced_analytics_resolver):
    """Test cleanup of service resources"""
    # Add some test data
    advanced_analytics_resolver.active_resolutions["test_resolution_1"] = {}
    advanced_analytics_resolver.resolution_metrics["test_resolution_1"] = {}

    await advanced_analytics_resolver._cleanup_resources()
    
    assert len(advanced_analytics_resolver.active_resolutions) == 0
    assert len(advanced_analytics_resolver.resolution_metrics) == 0

@pytest.mark.asyncio
async def test_error_handling(advanced_analytics_resolver):
    """Test error handling in resolution process"""
    message = ProcessingMessage(
        message_type=MessageType.ANALYTICS_RESOLUTION_REQUEST,
        content={
            "resolution_id": "test_resolution_1",
            "analysis_id": "test_analysis_1",
            "data": {},  # Invalid data
            "issues": []
        }
    )

    response = await advanced_analytics_resolver._handle_resolution_request(message)
    assert response.message_type == MessageType.ANALYTICS_RESOLUTION_FAILED
    assert "error" in response.content

@pytest.mark.asyncio
async def test_large_data_handling(advanced_analytics_resolver):
    """Test handling of large datasets"""
    # Create a large dataset
    large_data = pd.DataFrame({
        "column1": np.random.rand(10000),
        "column2": np.random.rand(10000),
        "column3": np.random.rand(10000)
    })

    resolution_id = "test_resolution_1"
    advanced_analytics_resolver.active_resolutions[resolution_id] = {
        "resolution_id": resolution_id,
        "analysis_id": "test_analysis_1",
        "issues": [
            {
                "type": "missing_values",
                "affected_columns": ["column1"]
            }
        ],
        "data": large_data,
        "start_time": datetime.now(),
        "status": "pending"
    }

    await advanced_analytics_resolver._start_resolution(resolution_id)
    
    assert advanced_analytics_resolver.active_resolutions[resolution_id]["status"] == "completed"
    assert "resolved_data" in advanced_analytics_resolver.active_resolutions[resolution_id]

@pytest.mark.asyncio
async def test_concurrent_resolution_handling(advanced_analytics_resolver, sample_data):
    """Test handling of concurrent resolution requests"""
    resolution_ids = [f"test_resolution_{i}" for i in range(3)]
    
    for resolution_id in resolution_ids:
        advanced_analytics_resolver.active_resolutions[resolution_id] = {
            "resolution_id": resolution_id,
            "analysis_id": f"test_analysis_{i}",
            "issues": [
                {
                    "type": "missing_values",
                    "affected_columns": ["column1"]
                }
            ],
            "data": sample_data,
            "start_time": datetime.now(),
            "status": "pending"
        }

    # Start all resolutions concurrently
    await asyncio.gather(*[
        advanced_analytics_resolver._start_resolution(resolution_id)
        for resolution_id in resolution_ids
    ])

    # Verify all resolutions completed successfully
    for resolution_id in resolution_ids:
        assert advanced_analytics_resolver.active_resolutions[resolution_id]["status"] == "completed"
        assert "resolved_data" in advanced_analytics_resolver.active_resolutions[resolution_id]
        assert "resolution_results" in advanced_analytics_resolver.active_resolutions[resolution_id] 