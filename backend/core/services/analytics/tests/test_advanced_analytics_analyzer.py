import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans

from core.messaging.message_broker import MessageBroker
from core.messaging.message_types import MessageType
from core.messaging.processing_message import ProcessingMessage
from core.services.analytics.advanced_analytics_analyzer import AdvancedAnalyticsAnalyzer

@pytest.fixture
def message_broker():
    broker = MagicMock(spec=MessageBroker)
    broker.request = AsyncMock()
    broker.publish = AsyncMock()
    return broker

@pytest.fixture
def advanced_analytics_analyzer(message_broker):
    analyzer = AdvancedAnalyticsAnalyzer(message_broker)
    return analyzer

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "feature1": np.random.rand(100),
        "feature2": np.random.rand(100),
        "target": np.random.randint(0, 2, 100)
    })

@pytest.mark.asyncio
async def test_initialize_service(advanced_analytics_analyzer):
    """Test service initialization"""
    await advanced_analytics_analyzer._initialize_service()
    assert len(advanced_analytics_analyzer.message_handlers) > 0
    assert MessageType.ANALYTICS_ANALYSIS_REQUEST in advanced_analytics_analyzer.message_handlers

@pytest.mark.asyncio
async def test_handle_analysis_request(advanced_analytics_analyzer, sample_data):
    """Test handling of analysis request message"""
    message = ProcessingMessage(
        message_type=MessageType.ANALYTICS_ANALYSIS_REQUEST,
        content={
            "analysis_id": "test_analysis_1",
            "data": sample_data.to_dict(),
            "analysis_type": "comprehensive",
            "parameters": {
                "statistical": True,
                "predictive": True,
                "clustering": True
            }
        }
    )

    response = await advanced_analytics_analyzer._handle_analysis_request(message)
    assert response.message_type == MessageType.ANALYTICS_ANALYSIS_START
    assert response.content["analysis_id"] == "test_analysis_1"
    assert response.content["status"] == "started"

@pytest.mark.asyncio
async def test_perform_comprehensive_analysis(advanced_analytics_analyzer, sample_data):
    """Test comprehensive analysis"""
    result = await advanced_analytics_analyzer._perform_comprehensive_analysis(sample_data)
    
    assert "statistical_analysis" in result
    assert "predictive_analysis" in result
    assert "clustering_analysis" in result
    assert "timestamp" in result

@pytest.mark.asyncio
async def test_perform_statistical_analysis(advanced_analytics_analyzer, sample_data):
    """Test statistical analysis"""
    result = await advanced_analytics_analyzer._perform_statistical_analysis(sample_data)
    
    assert "descriptive_stats" in result
    assert "inferential_stats" in result
    assert "correlation_analysis" in result
    assert "timestamp" in result

@pytest.mark.asyncio
async def test_perform_predictive_analysis(advanced_analytics_analyzer, sample_data):
    """Test predictive analysis"""
    result = await advanced_analytics_analyzer._perform_predictive_analysis(sample_data)
    
    assert "model_performance" in result
    assert "feature_importance" in result
    assert "predictions" in result
    assert "timestamp" in result

@pytest.mark.asyncio
async def test_perform_clustering_analysis(advanced_analytics_analyzer, sample_data):
    """Test clustering analysis"""
    result = await advanced_analytics_analyzer._perform_clustering_analysis(sample_data)
    
    assert "cluster_labels" in result
    assert "cluster_centers" in result
    assert "cluster_metrics" in result
    assert "timestamp" in result

@pytest.mark.asyncio
async def test_start_analysis(advanced_analytics_analyzer, sample_data):
    """Test starting analysis process"""
    analysis_id = "test_analysis_1"
    advanced_analytics_analyzer.active_analyses[analysis_id] = {
        "analysis_id": analysis_id,
        "data": sample_data,
        "analysis_type": "comprehensive",
        "parameters": {
            "statistical": True,
            "predictive": True,
            "clustering": True
        },
        "start_time": datetime.now(),
        "status": "pending"
    }

    await advanced_analytics_analyzer._start_analysis(analysis_id)
    
    assert advanced_analytics_analyzer.active_analyses[analysis_id]["status"] == "completed"
    assert "analysis_results" in advanced_analytics_analyzer.active_analyses[analysis_id]

@pytest.mark.asyncio
async def test_update_analysis_metrics(advanced_analytics_analyzer):
    """Test updating analysis metrics"""
    analysis_id = "test_analysis_1"
    start_time = datetime.now()
    end_time = datetime.now()
    
    advanced_analytics_analyzer.active_analyses[analysis_id] = {
        "start_time": start_time,
        "end_time": end_time,
        "status": "completed",
        "analysis_type": "comprehensive"
    }

    await advanced_analytics_analyzer._update_analysis_metrics(analysis_id)
    
    assert analysis_id in advanced_analytics_analyzer.analysis_metrics
    assert "duration" in advanced_analytics_analyzer.analysis_metrics[analysis_id]
    assert "status" in advanced_analytics_analyzer.analysis_metrics[analysis_id]
    assert "analysis_type" in advanced_analytics_analyzer.analysis_metrics[analysis_id]

@pytest.mark.asyncio
async def test_cleanup_resources(advanced_analytics_analyzer):
    """Test cleanup of service resources"""
    # Add some test data
    advanced_analytics_analyzer.active_analyses["test_analysis_1"] = {}
    advanced_analytics_analyzer.analysis_metrics["test_analysis_1"] = {}

    await advanced_analytics_analyzer._cleanup_resources()
    
    assert len(advanced_analytics_analyzer.active_analyses) == 0
    assert len(advanced_analytics_analyzer.analysis_metrics) == 0

@pytest.mark.asyncio
async def test_error_handling(advanced_analytics_analyzer):
    """Test error handling in analysis process"""
    message = ProcessingMessage(
        message_type=MessageType.ANALYTICS_ANALYSIS_REQUEST,
        content={
            "analysis_id": "test_analysis_1",
            "data": {},  # Invalid data
            "analysis_type": "comprehensive"
        }
    )

    response = await advanced_analytics_analyzer._handle_analysis_request(message)
    assert response.message_type == MessageType.ANALYTICS_ANALYSIS_FAILED
    assert "error" in response.content

@pytest.mark.asyncio
async def test_large_data_handling(advanced_analytics_analyzer):
    """Test handling of large datasets"""
    # Create a large dataset
    large_data = pd.DataFrame({
        "feature1": np.random.rand(10000),
        "feature2": np.random.rand(10000),
        "target": np.random.randint(0, 2, 10000)
    })

    analysis_id = "test_analysis_1"
    advanced_analytics_analyzer.active_analyses[analysis_id] = {
        "analysis_id": analysis_id,
        "data": large_data,
        "analysis_type": "comprehensive",
        "parameters": {
            "statistical": True,
            "predictive": True,
            "clustering": True
        },
        "start_time": datetime.now(),
        "status": "pending"
    }

    await advanced_analytics_analyzer._start_analysis(analysis_id)
    
    assert advanced_analytics_analyzer.active_analyses[analysis_id]["status"] == "completed"
    assert "analysis_results" in advanced_analytics_analyzer.active_analyses[analysis_id]

@pytest.mark.asyncio
async def test_concurrent_analysis_handling(advanced_analytics_analyzer, sample_data):
    """Test handling of concurrent analysis requests"""
    analysis_ids = [f"test_analysis_{i}" for i in range(3)]
    
    for analysis_id in analysis_ids:
        advanced_analytics_analyzer.active_analyses[analysis_id] = {
            "analysis_id": analysis_id,
            "data": sample_data,
            "analysis_type": "comprehensive",
            "parameters": {
                "statistical": True,
                "predictive": True,
                "clustering": True
            },
            "start_time": datetime.now(),
            "status": "pending"
        }

    # Start all analyses concurrently
    await asyncio.gather(*[
        advanced_analytics_analyzer._start_analysis(analysis_id)
        for analysis_id in analysis_ids
    ])

    # Verify all analyses completed successfully
    for analysis_id in analysis_ids:
        assert advanced_analytics_analyzer.active_analyses[analysis_id]["status"] == "completed"
        assert "analysis_results" in advanced_analytics_analyzer.active_analyses[analysis_id]

@pytest.mark.asyncio
async def test_calculate_descriptive_stats(advanced_analytics_analyzer, sample_data):
    """Test calculation of descriptive statistics"""
    result = advanced_analytics_analyzer._calculate_descriptive_stats(sample_data)
    
    assert "mean" in result
    assert "std" in result
    assert "min" in result
    assert "max" in result
    assert "quartiles" in result

@pytest.mark.asyncio
async def test_calculate_inferential_stats(advanced_analytics_analyzer, sample_data):
    """Test calculation of inferential statistics"""
    result = advanced_analytics_analyzer._calculate_inferential_stats(sample_data)
    
    assert "t_test" in result
    assert "anova" in result
    assert "chi_square" in result
    assert "p_values" in result

@pytest.mark.asyncio
async def test_calculate_correlation_analysis(advanced_analytics_analyzer, sample_data):
    """Test correlation analysis"""
    result = advanced_analytics_analyzer._calculate_correlation_analysis(sample_data)
    
    assert "correlation_matrix" in result
    assert "correlation_heatmap" in result
    assert "significant_correlations" in result

@pytest.mark.asyncio
async def test_train_predictive_model(advanced_analytics_analyzer, sample_data):
    """Test training of predictive model"""
    result = advanced_analytics_analyzer._train_predictive_model(sample_data)
    
    assert "model" in result
    assert "performance_metrics" in result
    assert "feature_importance" in result
    assert "predictions" in result

@pytest.mark.asyncio
async def test_perform_clustering(advanced_analytics_analyzer, sample_data):
    """Test clustering analysis"""
    result = advanced_analytics_analyzer._perform_clustering(sample_data)
    
    assert "cluster_labels" in result
    assert "cluster_centers" in result
    assert "cluster_metrics" in result
    assert "cluster_visualization" in result

@pytest.mark.asyncio
async def test_validate_analysis_request(advanced_analytics_analyzer):
    """Test validation of analysis request"""
    content = {
        "analysis_id": "test_analysis_1",
        "data": pd.DataFrame().to_dict(),
        "analysis_type": "comprehensive",
        "parameters": {
            "statistical": True,
            "predictive": True,
            "clustering": True
        }
    }
    
    assert advanced_analytics_analyzer._validate_analysis_request(content)

    invalid_content = {
        "analysis_id": "test_analysis_1",
        "data": {}  # Missing required fields
    }
    
    assert not advanced_analytics_analyzer._validate_analysis_request(invalid_content) 