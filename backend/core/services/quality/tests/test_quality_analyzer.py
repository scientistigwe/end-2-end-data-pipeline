import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from core.services.quality.quality_analyzer import QualityAnalyzer
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
def quality_analyzer(message_broker):
    analyzer = QualityAnalyzer(message_broker)
    return analyzer

@pytest.fixture
def sample_data():
    """Create sample data for testing"""
    data = {
        'numeric': [1, 2, 3, 4, 5, np.nan, 7, 8, 9, 10],
        'categorical': ['A', 'B', 'A', 'C', 'B', 'A', 'B', 'C', 'A', 'B'],
        'text': ['text1', 'text2', 'text3', 'text4', 'text5', 'text6', 'text7', 'text8', 'text9', 'text10'],
        'date': pd.date_range(start='2023-01-01', periods=10, freq='D')
    }
    return pd.DataFrame(data)

@pytest.mark.asyncio
async def test_initialize_service(quality_analyzer):
    """Test service initialization"""
    await quality_analyzer._initialize_service()
    
    # Verify message handlers are registered
    assert MessageType.QUALITY_ANALYSIS_REQUEST in quality_analyzer._message_handlers
    assert MessageType.QUALITY_ANALYSIS_START in quality_analyzer._message_handlers
    assert MessageType.QUALITY_ANALYSIS_PROGRESS in quality_analyzer._message_handlers
    assert MessageType.QUALITY_ANALYSIS_COMPLETE in quality_analyzer._message_handlers
    assert MessageType.QUALITY_ANALYSIS_FAILED in quality_analyzer._message_handlers

@pytest.mark.asyncio
async def test_handle_analysis_request(quality_analyzer, sample_data):
    """Test handling analysis request message"""
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_ANALYSIS_REQUEST,
        content={
            "pipeline_id": "test_pipeline",
            "data_id": "test_data",
            "analysis_type": "comprehensive",
            "data": sample_data.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_analyzer._handle_analysis_request(message)
    
    # Verify response
    assert response.success
    assert "analysis_id" in response.content
    assert response.content["pipeline_id"] == "test_pipeline"
    
    # Verify analysis was created
    analysis_id = response.content["analysis_id"]
    assert analysis_id in quality_analyzer.active_analyses
    assert quality_analyzer.active_analyses[analysis_id]["pipeline_id"] == "test_pipeline"

@pytest.mark.asyncio
async def test_perform_context_analysis(quality_analyzer, sample_data):
    """Test performing context analysis"""
    # Create test context
    context = {
        "data": sample_data,
        "schema": {
            "numeric": "float64",
            "categorical": "object",
            "text": "object",
            "date": "datetime64[ns]"
        }
    }
    
    # Perform analysis
    result = await quality_analyzer._perform_context_analysis(context)
    
    # Verify result
    assert result is not None
    assert "data_types" in result
    assert "missing_values" in result
    assert "unique_values" in result
    assert "value_ranges" in result

@pytest.mark.asyncio
async def test_analyze_column(quality_analyzer, sample_data):
    """Test analyzing a single column"""
    # Test numeric column
    numeric_profile = await quality_analyzer._analyze_column(sample_data['numeric'])
    assert numeric_profile.name == "numeric"
    assert numeric_profile.data_type == "float64"
    assert numeric_profile.total_rows == 10
    assert numeric_profile.missing_count == 1
    assert "mean" in numeric_profile.stats
    assert "std" in numeric_profile.stats
    
    # Test categorical column
    categorical_profile = await quality_analyzer._analyze_column(sample_data['categorical'])
    assert categorical_profile.name == "categorical"
    assert categorical_profile.data_type == "object"
    assert categorical_profile.total_rows == 10
    assert categorical_profile.missing_count == 0
    assert categorical_profile.unique_values == 3

@pytest.mark.asyncio
async def test_detect_functional_dependencies(quality_analyzer, sample_data):
    """Test detecting functional dependencies"""
    # Create data with known dependencies
    data = pd.DataFrame({
        'id': range(1, 11),
        'value': [i * 2 for i in range(1, 11)],
        'category': ['A', 'B', 'A', 'B', 'A', 'B', 'A', 'B', 'A', 'B']
    })
    
    # Detect dependencies
    dependencies = await quality_analyzer._detect_functional_dependencies(data)
    
    # Verify dependencies
    assert dependencies is not None
    assert len(dependencies) > 0
    assert any(dep['strength'] > 0.8 for dep in dependencies)

@pytest.mark.asyncio
async def test_check_missing_values(quality_analyzer, sample_data):
    """Test checking for missing values"""
    # Add missing values
    sample_data.loc[5, 'numeric'] = np.nan
    
    # Check missing values
    issues = await quality_analyzer._check_missing_values(sample_data)
    
    # Verify issues
    assert len(issues) > 0
    assert any(issue['type'] == 'missing_values' for issue in issues)
    assert any(issue['column'] == 'numeric' for issue in issues)

@pytest.mark.asyncio
async def test_check_duplicates(quality_analyzer, sample_data):
    """Test checking for duplicates"""
    # Add duplicates
    sample_data = pd.concat([sample_data, sample_data.iloc[:2]])
    
    # Check duplicates
    issues = await quality_analyzer._check_duplicates(sample_data)
    
    # Verify issues
    assert len(issues) > 0
    assert any(issue['type'] == 'duplicates' for issue in issues)

@pytest.mark.asyncio
async def test_check_anomalies(quality_analyzer, sample_data):
    """Test checking for anomalies"""
    # Add anomalies
    sample_data.loc[5, 'numeric'] = 100
    
    # Check anomalies
    issues = await quality_analyzer._check_anomalies(sample_data)
    
    # Verify issues
    assert len(issues) > 0
    assert any(issue['type'] == 'anomalies' for issue in issues)
    assert any(issue['column'] == 'numeric' for issue in issues)

@pytest.mark.asyncio
async def test_check_data_type_consistency(quality_analyzer, sample_data):
    """Test checking data type consistency"""
    # Add mixed types
    sample_data.loc[5, 'numeric'] = 'invalid'
    
    # Check type consistency
    issues = await quality_analyzer._check_data_type_consistency(sample_data)
    
    # Verify issues
    assert len(issues) > 0
    assert any(issue['type'] == 'mixed_types' for issue in issues)
    assert any(issue['column'] == 'numeric' for issue in issues)

@pytest.mark.asyncio
async def test_check_value_constraints(quality_analyzer, sample_data):
    """Test checking value constraints"""
    # Add constraint violations
    sample_data.loc[5, 'numeric'] = -1
    
    # Check constraints
    issues = await quality_analyzer._check_value_constraints(sample_data)
    
    # Verify issues
    assert len(issues) > 0
    assert any(issue['type'] == 'constraint_violations' for issue in issues)
    assert any(issue['column'] == 'numeric' for issue in issues)

@pytest.mark.asyncio
async def test_update_analysis_metrics(quality_analyzer):
    """Test updating analysis metrics"""
    # Create test metrics
    test_metrics = {
        "total_analyses": 10,
        "successful_analyses": 8,
        "average_duration": 1.5
    }
    
    # Update metrics
    await quality_analyzer._update_analysis_metrics(test_metrics)
    
    # Verify metrics were updated
    assert quality_analyzer.analysis_metrics["total_analyses"] == 10
    assert quality_analyzer.analysis_metrics["successful_analyses"] == 8
    assert quality_analyzer.analysis_metrics["average_duration"] == 1.5
    assert "last_update" in quality_analyzer.analysis_metrics

@pytest.mark.asyncio
async def test_cleanup_resources(quality_analyzer):
    """Test resource cleanup"""
    # Create test analysis
    analysis_id = "test_analysis"
    quality_analyzer.active_analyses[analysis_id] = {
        "pipeline_id": "test_pipeline",
        "start_time": datetime.now(),
        "status": "running"
    }
    
    # Cleanup resources
    await quality_analyzer._cleanup_resources()
    
    # Verify resources were cleaned up
    assert not quality_analyzer.active_analyses
    assert not quality_analyzer.analysis_metrics

@pytest.mark.asyncio
async def test_error_handling(quality_analyzer):
    """Test error handling"""
    # Create test message with invalid data
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_ANALYSIS_REQUEST,
        content={
            "pipeline_id": "test_pipeline",
            "data_id": "test_data",
            "analysis_type": "comprehensive",
            "data": None,  # Invalid data
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_analyzer._handle_analysis_request(message)
    
    # Verify error response
    assert not response.success
    assert "error" in response.content
    assert "Invalid data format" in response.content["error"]

@pytest.mark.asyncio
async def test_large_data_handling(quality_analyzer):
    """Test handling large datasets"""
    # Create large dataset
    large_data = pd.DataFrame({
        'numeric': np.random.randn(10000),
        'categorical': np.random.choice(['A', 'B', 'C'], 10000)
    })
    
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_ANALYSIS_REQUEST,
        content={
            "pipeline_id": "test_pipeline",
            "data_id": "test_data",
            "analysis_type": "comprehensive",
            "data": large_data.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_analyzer._handle_analysis_request(message)
    
    # Verify response
    assert response.success
    assert "analysis_id" in response.content
    
    # Verify batch processing
    analysis_id = response.content["analysis_id"]
    assert quality_analyzer.active_analyses[analysis_id]["batch_size"] <= quality_analyzer.config["max_rows_per_batch"] 