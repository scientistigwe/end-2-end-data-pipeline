import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
import os

from core.services.quality.quality_reporter import QualityReporter
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
def quality_reporter(message_broker):
    reporter = QualityReporter(message_broker)
    return reporter

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
async def test_initialize_service(quality_reporter):
    """Test service initialization"""
    await quality_reporter._initialize_service()
    
    # Verify message handlers are registered
    assert MessageType.QUALITY_REPORT_REQUEST in quality_reporter._message_handlers
    assert MessageType.QUALITY_REPORT_START in quality_reporter._message_handlers
    assert MessageType.QUALITY_REPORT_PROGRESS in quality_reporter._message_handlers
    assert MessageType.QUALITY_REPORT_COMPLETE in quality_reporter._message_handlers
    assert MessageType.QUALITY_REPORT_FAILED in quality_reporter._message_handlers

@pytest.mark.asyncio
async def test_handle_report_request(quality_reporter, sample_data, sample_metrics):
    """Test handling report request message"""
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_REPORT_REQUEST,
        content={
            "pipeline_id": "test_pipeline",
            "data_id": "test_data",
            "data": sample_data.to_dict(),
            "metrics": sample_metrics,
            "report_type": "summary",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_reporter._handle_report_request(message)
    
    # Verify response
    assert response.success
    assert "report_id" in response.content
    assert response.content["pipeline_id"] == "test_pipeline"
    
    # Verify report was created
    report_id = response.content["report_id"]
    assert report_id in quality_reporter.active_reports
    assert quality_reporter.active_reports[report_id]["pipeline_id"] == "test_pipeline"

@pytest.mark.asyncio
async def test_generate_summary_report(quality_reporter, sample_data, sample_metrics):
    """Test generating summary report"""
    # Create test report context
    context = {
        "data": sample_data,
        "metrics": sample_metrics,
        "report_type": "summary"
    }
    
    # Generate report
    result = await quality_reporter._generate_summary_report(context)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "report_content" in result.content
    assert "report_format" in result.content
    assert "report_path" in result.content

@pytest.mark.asyncio
async def test_generate_detailed_report(quality_reporter, sample_data, sample_metrics):
    """Test generating detailed report"""
    # Create test report context
    context = {
        "data": sample_data,
        "metrics": sample_metrics,
        "report_type": "detailed"
    }
    
    # Generate report
    result = await quality_reporter._generate_detailed_report(context)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "report_content" in result.content
    assert "report_format" in result.content
    assert "report_path" in result.content

@pytest.mark.asyncio
async def test_generate_trend_report(quality_reporter, sample_metrics):
    """Test generating trend report"""
    # Create test trend data
    trend_data = {
        "dates": pd.date_range(start='2023-01-01', periods=5, freq='D').tolist(),
        "metrics": [sample_metrics for _ in range(5)]
    }
    
    # Generate report
    result = await quality_reporter._generate_trend_report(trend_data)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "report_content" in result.content
    assert "report_format" in result.content
    assert "report_path" in result.content

@pytest.mark.asyncio
async def test_generate_custom_report(quality_reporter, sample_data, sample_metrics):
    """Test generating custom report"""
    # Create test report context
    context = {
        "data": sample_data,
        "metrics": sample_metrics,
        "report_type": "custom",
        "custom_config": {
            "sections": ["overview", "metrics", "issues"],
            "charts": ["quality_trend", "issue_distribution"]
        }
    }
    
    # Generate report
    result = await quality_reporter._generate_custom_report(context)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "report_content" in result.content
    assert "report_format" in result.content
    assert "report_path" in result.content

@pytest.mark.asyncio
async def test_create_visualizations(quality_reporter, sample_data, sample_metrics):
    """Test creating visualizations"""
    # Create test visualization context
    context = {
        "data": sample_data,
        "metrics": sample_metrics,
        "chart_types": ["bar", "line", "pie"]
    }
    
    # Create visualizations
    result = await quality_reporter._create_visualizations(context)
    
    # Verify result
    assert result is not None
    assert "charts" in result
    assert len(result["charts"]) > 0
    assert all(chart["type"] in ["bar", "line", "pie"] for chart in result["charts"])

@pytest.mark.asyncio
async def test_save_report(quality_reporter):
    """Test saving report"""
    # Create test report content
    report_content = {
        "title": "Test Report",
        "content": "Test content",
        "charts": []
    }
    
    # Save report
    result = await quality_reporter._save_report(report_content)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "report_path" in result.content
    assert os.path.exists(result.content["report_path"])

@pytest.mark.asyncio
async def test_update_report_metrics(quality_reporter):
    """Test updating report metrics"""
    # Create test metrics
    test_metrics = {
        "total_reports": 10,
        "successful_reports": 8,
        "average_duration": 1.5
    }
    
    # Update metrics
    await quality_reporter._update_report_metrics(test_metrics)
    
    # Verify metrics were updated
    assert quality_reporter.report_metrics["total_reports"] == 10
    assert quality_reporter.report_metrics["successful_reports"] == 8
    assert quality_reporter.report_metrics["average_duration"] == 1.5
    assert "last_update" in quality_reporter.report_metrics

@pytest.mark.asyncio
async def test_cleanup_resources(quality_reporter):
    """Test resource cleanup"""
    # Create test report
    report_id = "test_report"
    quality_reporter.active_reports[report_id] = {
        "pipeline_id": "test_pipeline",
        "start_time": datetime.now(),
        "status": "running"
    }
    
    # Cleanup resources
    await quality_reporter._cleanup_resources()
    
    # Verify resources were cleaned up
    assert not quality_reporter.active_reports
    assert not quality_reporter.report_metrics

@pytest.mark.asyncio
async def test_error_handling(quality_reporter):
    """Test error handling"""
    # Create test message with invalid data
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_REPORT_REQUEST,
        content={
            "pipeline_id": "test_pipeline",
            "data_id": "test_data",
            "data": None,  # Invalid data
            "metrics": None,  # Invalid metrics
            "report_type": "summary",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_reporter._handle_report_request(message)
    
    # Verify error response
    assert not response.success
    assert "error" in response.content
    assert "Invalid data format" in response.content["error"]

@pytest.mark.asyncio
async def test_large_data_handling(quality_reporter):
    """Test handling large datasets"""
    # Create large dataset
    large_data = pd.DataFrame({
        'numeric': np.random.randn(10000),
        'categorical': np.random.choice(['A', 'B', 'C'], 10000)
    })
    
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_REPORT_REQUEST,
        content={
            "pipeline_id": "test_pipeline",
            "data_id": "test_data",
            "data": large_data.to_dict(),
            "metrics": {"test": "metrics"},
            "report_type": "summary",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_reporter._handle_report_request(message)
    
    # Verify response
    assert response.success
    assert "report_id" in response.content
    
    # Verify batch processing
    report_id = response.content["report_id"]
    assert quality_reporter.active_reports[report_id]["batch_size"] <= quality_reporter.config["max_rows_per_batch"] 