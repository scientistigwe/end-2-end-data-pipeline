import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from core.services.quality.quality_validator import QualityValidator
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
def quality_validator(message_broker):
    validator = QualityValidator(message_broker)
    return validator

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

@pytest.mark.asyncio
async def test_initialize_service(quality_validator):
    """Test service initialization"""
    await quality_validator._initialize_service()
    
    # Verify message handlers are registered
    assert MessageType.QUALITY_VALIDATION_REQUEST in quality_validator._message_handlers
    assert MessageType.QUALITY_VALIDATION_START in quality_validator._message_handlers
    assert MessageType.QUALITY_VALIDATION_PROGRESS in quality_validator._message_handlers
    assert MessageType.QUALITY_VALIDATION_COMPLETE in quality_validator._message_handlers
    assert MessageType.QUALITY_VALIDATION_FAILED in quality_validator._message_handlers

@pytest.mark.asyncio
async def test_handle_validation_request(quality_validator, sample_data):
    """Test handling validation request message"""
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_VALIDATION_REQUEST,
        content={
            "pipeline_id": "test_pipeline",
            "data_id": "test_data",
            "data": sample_data.to_dict(),
            "validation_type": "comprehensive",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_validator._handle_validation_request(message)
    
    # Verify response
    assert response.success
    assert "validation_id" in response.content
    assert response.content["pipeline_id"] == "test_pipeline"
    
    # Verify validation was created
    validation_id = response.content["validation_id"]
    assert validation_id in quality_validator.active_validations
    assert quality_validator.active_validations[validation_id]["pipeline_id"] == "test_pipeline"

@pytest.mark.asyncio
async def test_perform_validation(quality_validator, sample_data):
    """Test performing validation"""
    # Create test validation
    validation = {
        "data": sample_data,
        "validation_type": "comprehensive",
        "rules": {
            "completeness": 0.95,
            "consistency": 0.9,
            "accuracy": 0.85,
            "timeliness": 0.9
        }
    }
    
    # Perform validation
    result = await quality_validator._perform_validation(validation)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "validation_results" in result.content
    assert "validation_score" in result.content
    assert "validation_details" in result.content

@pytest.mark.asyncio
async def test_validate_data(quality_validator, sample_data):
    """Test validating data"""
    # Create test validation context
    context = {
        "data": sample_data,
        "rules": {
            "completeness": 0.95,
            "consistency": 0.9,
            "accuracy": 0.85,
            "timeliness": 0.9
        }
    }
    
    # Validate data
    result = await quality_validator._validate_data(context)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "validation_results" in result.content
    assert "validation_score" in result.content
    assert "validation_details" in result.content

@pytest.mark.asyncio
async def test_validate_completeness(quality_validator, sample_data):
    """Test validating completeness"""
    # Add missing values
    sample_data.loc[5, 'numeric'] = np.nan
    
    # Validate completeness
    result = await quality_validator._validate_completeness(sample_data)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "completeness_score" in result.content
    assert "missing_values" in result.content
    assert result.content["completeness_score"] < 1.0

@pytest.mark.asyncio
async def test_validate_consistency(quality_validator, sample_data):
    """Test validating consistency"""
    # Add inconsistent values
    sample_data.loc[5, 'numeric'] = 'invalid'
    
    # Validate consistency
    result = await quality_validator._validate_consistency(sample_data)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "consistency_score" in result.content
    assert "inconsistent_values" in result.content
    assert result.content["consistency_score"] < 1.0

@pytest.mark.asyncio
async def test_validate_accuracy(quality_validator, sample_data):
    """Test validating accuracy"""
    # Add inaccurate values
    sample_data.loc[5, 'numeric'] = 100
    
    # Validate accuracy
    result = await quality_validator._validate_accuracy(sample_data)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "accuracy_score" in result.content
    assert "inaccurate_values" in result.content
    assert result.content["accuracy_score"] < 1.0

@pytest.mark.asyncio
async def test_validate_timeliness(quality_validator, sample_data):
    """Test validating timeliness"""
    # Add outdated values
    sample_data.loc[5, 'date'] = pd.Timestamp('2022-01-01')
    
    # Validate timeliness
    result = await quality_validator._validate_timeliness(sample_data)
    
    # Verify result
    assert result is not None
    assert result.success
    assert "timeliness_score" in result.content
    assert "outdated_values" in result.content
    assert result.content["timeliness_score"] < 1.0

@pytest.mark.asyncio
async def test_calculate_quality_score(quality_validator):
    """Test calculating quality score"""
    # Create test validation results
    validation_results = {
        "completeness": 0.95,
        "consistency": 0.9,
        "accuracy": 0.85,
        "timeliness": 0.9
    }
    
    # Calculate quality score
    score = await quality_validator._calculate_quality_score(validation_results)
    
    # Verify score
    assert score is not None
    assert 0 <= score <= 1
    assert abs(score - 0.9) < 0.1  # Expected weighted average

@pytest.mark.asyncio
async def test_update_validation_metrics(quality_validator):
    """Test updating validation metrics"""
    # Create test metrics
    test_metrics = {
        "total_validations": 10,
        "successful_validations": 8,
        "average_duration": 1.5
    }
    
    # Update metrics
    await quality_validator._update_validation_metrics(test_metrics)
    
    # Verify metrics were updated
    assert quality_validator.validation_metrics["total_validations"] == 10
    assert quality_validator.validation_metrics["successful_validations"] == 8
    assert quality_validator.validation_metrics["average_duration"] == 1.5
    assert "last_update" in quality_validator.validation_metrics

@pytest.mark.asyncio
async def test_cleanup_resources(quality_validator):
    """Test resource cleanup"""
    # Create test validation
    validation_id = "test_validation"
    quality_validator.active_validations[validation_id] = {
        "pipeline_id": "test_pipeline",
        "start_time": datetime.now(),
        "status": "running"
    }
    
    # Cleanup resources
    await quality_validator._cleanup_resources()
    
    # Verify resources were cleaned up
    assert not quality_validator.active_validations
    assert not quality_validator.validation_metrics

@pytest.mark.asyncio
async def test_error_handling(quality_validator):
    """Test error handling"""
    # Create test message with invalid data
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_VALIDATION_REQUEST,
        content={
            "pipeline_id": "test_pipeline",
            "data_id": "test_data",
            "data": None,  # Invalid data
            "validation_type": "comprehensive",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_validator._handle_validation_request(message)
    
    # Verify error response
    assert not response.success
    assert "error" in response.content
    assert "Invalid data format" in response.content["error"]

@pytest.mark.asyncio
async def test_large_data_handling(quality_validator):
    """Test handling large datasets"""
    # Create large dataset
    large_data = pd.DataFrame({
        'numeric': np.random.randn(10000),
        'categorical': np.random.choice(['A', 'B', 'C'], 10000)
    })
    
    # Create test message
    message = ProcessingMessage(
        message_type=MessageType.QUALITY_VALIDATION_REQUEST,
        content={
            "pipeline_id": "test_pipeline",
            "data_id": "test_data",
            "data": large_data.to_dict(),
            "validation_type": "comprehensive",
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Handle message
    response = await quality_validator._handle_validation_request(message)
    
    # Verify response
    assert response.success
    assert "validation_id" in response.content
    
    # Verify batch processing
    validation_id = response.content["validation_id"]
    assert quality_validator.active_validations[validation_id]["batch_size"] <= quality_validator.config["max_rows_per_batch"] 