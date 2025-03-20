import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from core.services.quality.quality_resolver import QualityResolver
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
def quality_resolver(message_broker):
    resolver = QualityResolver(message_broker)
    return resolver

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
async def test_initialize_service(quality_resolver):
    """Test service initialization"""
    await quality_resolver._initialize_service()
    
    # Verify message handlers are registered
    assert MessageType.QUALITY_RESOLUTION_REQUEST in quality_resolver._message_handlers
    assert MessageType.QUALITY_RESOLUTION_START in quality_resolver._message_handlers
    assert MessageType.QUALITY_RESOLUTION_PROGRESS in quality_resolver._message_handlers
    assert MessageType.QUALITY_RESOLUTION_COMPLETE in quality_resolver._message_handlers
    assert MessageType.QUALITY_RESOLUTION_FAILED in quality_resolver._message_handlers

@pytest.mark.asyncio
async def test_handle_resolution_request(quality_resolver, sample_data):
    """Test handling resolution request message"""
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_RESOLUTION_REQUEST,
        content={
            "pipeline_id": "test_pipeline",
            "issue_id": "test_issue",
            "data": sample_data.to_dict(),
            "issue_type": "missing_values",
            "column": "numeric",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_resolver._handle_resolution_request(message)
    
    # Verify response
    assert response.success
    assert "resolution_id" in response.content
    assert response.content["pipeline_id"] == "test_pipeline"
    
    # Verify resolution was created
    resolution_id = response.content["resolution_id"]
    assert resolution_id in quality_resolver.active_resolutions
    assert quality_resolver.active_resolutions[resolution_id]["pipeline_id"] == "test_pipeline"

@pytest.mark.asyncio
async def test_perform_resolution(quality_resolver, sample_data):
    """Test performing resolution"""
    # Create test resolution
    resolution = {
        "data": sample_data,
        "issue_type": "missing_values",
        "column": "numeric",
        "strategy": "mean"
    }
    
    # Perform resolution
    result = await quality_resolver._perform_resolution(resolution)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "resolved_data" in result.content
    assert "resolution_details" in result.content
    
    # Verify data was resolved
    resolved_data = pd.DataFrame(result.content["resolved_data"])
    assert resolved_data["numeric"].isna().sum() == 0
    assert abs(resolved_data["numeric"].mean() - sample_data["numeric"].mean()) < 0.1

@pytest.mark.asyncio
async def test_determine_resolution_strategy(quality_resolver):
    """Test determining resolution strategy"""
    # Test missing values strategy
    missing_strategy = await quality_resolver._determine_resolution_strategy(
        "missing_values",
        {"column": "numeric", "data_type": "float64"}
    )
    assert missing_strategy in ["mean", "median", "mode"]
    
    # Test duplicates strategy
    duplicate_strategy = await quality_resolver._determine_resolution_strategy(
        "duplicates",
        {"column": "id", "data_type": "int64"}
    )
    assert duplicate_strategy in ["remove", "merge"]

@pytest.mark.asyncio
async def test_resolve_missing_values(quality_resolver, sample_data):
    """Test resolving missing values"""
    # Test mean imputation
    mean_result = await quality_resolver._resolve_missing_values(
        sample_data,
        "numeric",
        "mean"
    )
    assert mean_result.success
    assert mean_result.content["resolved_data"]["numeric"].isna().sum() == 0
    
    # Test median imputation
    median_result = await quality_resolver._resolve_missing_values(
        sample_data,
        "numeric",
        "median"
    )
    assert median_result.success
    assert median_result.content["resolved_data"]["numeric"].isna().sum() == 0

@pytest.mark.asyncio
async def test_resolve_duplicates(quality_resolver, sample_data):
    """Test resolving duplicates"""
    # Add duplicates
    data_with_duplicates = pd.concat([sample_data, sample_data.iloc[:2]])
    
    # Test remove strategy
    remove_result = await quality_resolver._resolve_duplicates(
        data_with_duplicates,
        "remove"
    )
    assert remove_result.success
    assert len(remove_result.content["resolved_data"]) == len(sample_data)
    
    # Test merge strategy
    merge_result = await quality_resolver._resolve_duplicates(
        data_with_duplicates,
        "merge"
    )
    assert merge_result.success
    assert len(merge_result.content["resolved_data"]) == len(sample_data)

@pytest.mark.asyncio
async def test_resolve_anomalies(quality_resolver, sample_data):
    """Test resolving anomalies"""
    # Add anomalies
    sample_data.loc[5, 'numeric'] = 100
    
    # Test winsorization
    winsorize_result = await quality_resolver._resolve_anomalies(
        sample_data,
        "numeric",
        "winsorize"
    )
    assert winsorize_result.success
    assert winsorize_result.content["resolved_data"]["numeric"].max() < 100
    
    # Test z-score
    zscore_result = await quality_resolver._resolve_anomalies(
        sample_data,
        "numeric",
        "zscore"
    )
    assert zscore_result.success
    assert zscore_result.content["resolved_data"]["numeric"].max() < 100

@pytest.mark.asyncio
async def test_resolve_mixed_types(quality_resolver, sample_data):
    """Test resolving mixed types"""
    # Add mixed types
    sample_data.loc[5, 'numeric'] = 'invalid'
    
    # Test type conversion
    convert_result = await quality_resolver._resolve_mixed_types(
        sample_data,
        "numeric",
        "convert"
    )
    assert convert_result.success
    assert pd.api.types.is_numeric_dtype(convert_result.content["resolved_data"]["numeric"])
    
    # Test standardization
    standardize_result = await quality_resolver._resolve_mixed_types(
        sample_data,
        "numeric",
        "standardize"
    )
    assert standardize_result.success
    assert pd.api.types.is_numeric_dtype(standardize_result.content["resolved_data"]["numeric"])

@pytest.mark.asyncio
async def test_resolve_constraints(quality_resolver, sample_data):
    """Test resolving constraint violations"""
    # Add constraint violations
    sample_data.loc[5, 'numeric'] = -1
    
    # Test constraint enforcement
    enforce_result = await quality_resolver._resolve_constraints(
        sample_data,
        "numeric",
        "enforce"
    )
    assert enforce_result.success
    assert enforce_result.content["resolved_data"]["numeric"].min() >= 0
    
    # Test constraint relaxation
    relax_result = await quality_resolver._resolve_constraints(
        sample_data,
        "numeric",
        "relax"
    )
    assert relax_result.success
    assert relax_result.content["resolved_data"]["numeric"].min() >= -1

@pytest.mark.asyncio
async def test_validate_resolution(quality_resolver, sample_data):
    """Test validating resolution results"""
    # Create test resolution result
    resolution_result = {
        "resolved_data": sample_data.to_dict(),
        "resolution_details": {
            "strategy": "mean",
            "affected_rows": 1,
            "changes": ["imputed missing value"]
        }
    }
    
    # Validate resolution
    validation_result = await quality_resolver._validate_resolution(resolution_result)
    
    # Verify validation
    assert validation_result.success
    assert "validation_score" in validation_result.content
    assert "validation_details" in validation_result.content

@pytest.mark.asyncio
async def test_update_resolution_metrics(quality_resolver):
    """Test updating resolution metrics"""
    # Create test metrics
    test_metrics = {
        "total_resolutions": 10,
        "successful_resolutions": 8,
        "average_duration": 1.5
    }
    
    # Update metrics
    await quality_resolver._update_resolution_metrics(test_metrics)
    
    # Verify metrics were updated
    assert quality_resolver.resolution_metrics["total_resolutions"] == 10
    assert quality_resolver.resolution_metrics["successful_resolutions"] == 8
    assert quality_resolver.resolution_metrics["average_duration"] == 1.5
    assert "last_update" in quality_resolver.resolution_metrics

@pytest.mark.asyncio
async def test_cleanup_resources(quality_resolver):
    """Test resource cleanup"""
    # Create test resolution
    resolution_id = "test_resolution"
    quality_resolver.active_resolutions[resolution_id] = {
        "pipeline_id": "test_pipeline",
        "start_time": datetime.now(),
        "status": "running"
    }
    
    # Cleanup resources
    await quality_resolver._cleanup_resources()
    
    # Verify resources were cleaned up
    assert not quality_resolver.active_resolutions
    assert not quality_resolver.resolution_metrics

@pytest.mark.asyncio
async def test_error_handling(quality_resolver):
    """Test error handling"""
    # Create test message with invalid data
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_RESOLUTION_REQUEST,
        content={
            "pipeline_id": "test_pipeline",
            "issue_id": "test_issue",
            "data": None,  # Invalid data
            "issue_type": "missing_values",
            "column": "numeric",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_resolver._handle_resolution_request(message)
    
    # Verify error response
    assert not response.success
    assert "error" in response.content
    assert "Invalid data format" in response.content["error"]

@pytest.mark.asyncio
async def test_large_data_handling(quality_resolver):
    """Test handling large datasets"""
    # Create large dataset
    large_data = pd.DataFrame({
        'numeric': np.random.randn(10000),
        'categorical': np.random.choice(['A', 'B', 'C'], 10000)
    })
    
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_RESOLUTION_REQUEST,
        content={
            "pipeline_id": "test_pipeline",
            "issue_id": "test_issue",
            "data": large_data.to_dict(),
            "issue_type": "missing_values",
            "column": "numeric",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_resolver._handle_resolution_request(message)
    
    # Verify response
    assert response.success
    assert "resolution_id" in response.content
    
    # Verify batch processing
    resolution_id = response.content["resolution_id"]
    assert quality_resolver.active_resolutions[resolution_id]["batch_size"] <= quality_resolver.config["max_rows_per_batch"] 