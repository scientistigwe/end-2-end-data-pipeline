import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sklearn.ensemble import RandomForestClassifier

from core.messaging.message_broker import MessageBroker
from core.messaging.message_types import MessageType
from core.messaging.processing_message import ProcessingMessage
from core.services.analytics.advanced_analytics_validator import AdvancedAnalyticsValidator

@pytest.fixture
def message_broker():
    broker = MagicMock(spec=MessageBroker)
    broker.request = AsyncMock()
    broker.publish = AsyncMock()
    return broker

@pytest.fixture
def advanced_analytics_validator(message_broker):
    validator = AdvancedAnalyticsValidator(message_broker)
    return validator

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        "feature1": np.random.rand(100),
        "feature2": np.random.rand(100),
        "target": np.random.randint(0, 2, 100)
    })

@pytest.fixture
def sample_model():
    return RandomForestClassifier(n_estimators=10, random_state=42)

@pytest.mark.asyncio
async def test_initialize_service(advanced_analytics_validator):
    """Test service initialization"""
    await advanced_analytics_validator._initialize_service()
    assert len(advanced_analytics_validator.message_handlers) > 0
    assert MessageType.ANALYTICS_VALIDATION_REQUEST in advanced_analytics_validator.message_handlers

@pytest.mark.asyncio
async def test_handle_validation_request(advanced_analytics_validator, sample_data, sample_model):
    """Test handling of validation request message"""
    message = ProcessingMessage(
        message_type=MessageType.ANALYTICS_VALIDATION_REQUEST,
        content={
            "validation_id": "test_validation_1",
            "analysis_id": "test_analysis_1",
            "data": sample_data.to_dict(),
            "model": sample_model,
            "validation_type": "model"
        }
    )

    response = await advanced_analytics_validator._handle_validation_request(message)
    assert response.message_type == MessageType.ANALYTICS_VALIDATION_START
    assert response.content["validation_id"] == "test_validation_1"
    assert response.content["status"] == "started"

@pytest.mark.asyncio
async def test_validate_model(advanced_analytics_validator, sample_data, sample_model):
    """Test model validation"""
    result = await advanced_analytics_validator._validate_model(sample_data, sample_model)
    
    assert "metrics" in result
    assert "validation_status" in result
    assert "thresholds" in result
    assert "accuracy" in result["metrics"]
    assert "precision" in result["metrics"]
    assert "recall" in result["metrics"]
    assert "f1_score" in result["metrics"]

@pytest.mark.asyncio
async def test_validate_results(advanced_analytics_validator, sample_data):
    """Test results validation"""
    result = await advanced_analytics_validator._validate_results(sample_data)
    
    assert "data_quality" in result
    assert "statistical_validity" in result
    assert "business_rules" in result
    assert "validation_status" in result
    assert "timestamp" in result

@pytest.mark.asyncio
async def test_validate_data_quality(advanced_analytics_validator, sample_data):
    """Test data quality validation"""
    result = await advanced_analytics_validator._validate_data_quality(sample_data)
    
    assert "metrics" in result
    assert "status" in result
    assert "completeness" in result["metrics"]
    assert "consistency" in result["metrics"]
    assert "accuracy" in result["metrics"]

@pytest.mark.asyncio
async def test_validate_statistical_validity(advanced_analytics_validator, sample_data):
    """Test statistical validity validation"""
    result = await advanced_analytics_validator._validate_statistical_validity(sample_data)
    
    assert "metrics" in result
    assert "status" in result
    assert "normality" in result["metrics"]
    assert "outliers" in result["metrics"]
    assert "correlation" in result["metrics"]

@pytest.mark.asyncio
async def test_validate_business_rules(advanced_analytics_validator, sample_data):
    """Test business rules validation"""
    result = await advanced_analytics_validator._validate_business_rules(sample_data)
    
    assert "rules" in result
    assert "status" in result
    assert "value_ranges" in result["rules"]
    assert "relationships" in result["rules"]
    assert "constraints" in result["rules"]

@pytest.mark.asyncio
async def test_start_validation(advanced_analytics_validator, sample_data, sample_model):
    """Test starting validation process"""
    validation_id = "test_validation_1"
    advanced_analytics_validator.active_validations[validation_id] = {
        "validation_id": validation_id,
        "analysis_id": "test_analysis_1",
        "data": sample_data,
        "model": sample_model,
        "validation_type": "model",
        "start_time": datetime.now(),
        "status": "pending"
    }

    await advanced_analytics_validator._start_validation(validation_id)
    
    assert advanced_analytics_validator.active_validations[validation_id]["status"] == "completed"
    assert "validation_results" in advanced_analytics_validator.active_validations[validation_id]

@pytest.mark.asyncio
async def test_update_validation_metrics(advanced_analytics_validator):
    """Test updating validation metrics"""
    validation_id = "test_validation_1"
    start_time = datetime.now()
    end_time = datetime.now()
    
    advanced_analytics_validator.active_validations[validation_id] = {
        "start_time": start_time,
        "end_time": end_time,
        "status": "completed",
        "validation_type": "model"
    }

    await advanced_analytics_validator._update_validation_metrics(validation_id)
    
    assert validation_id in advanced_analytics_validator.validation_metrics
    assert "duration" in advanced_analytics_validator.validation_metrics[validation_id]
    assert "status" in advanced_analytics_validator.validation_metrics[validation_id]
    assert "validation_type" in advanced_analytics_validator.validation_metrics[validation_id]

@pytest.mark.asyncio
async def test_cleanup_resources(advanced_analytics_validator):
    """Test cleanup of service resources"""
    # Add some test data
    advanced_analytics_validator.active_validations["test_validation_1"] = {}
    advanced_analytics_validator.validation_metrics["test_validation_1"] = {}

    await advanced_analytics_validator._cleanup_resources()
    
    assert len(advanced_analytics_validator.active_validations) == 0
    assert len(advanced_analytics_validator.validation_metrics) == 0

@pytest.mark.asyncio
async def test_error_handling(advanced_analytics_validator):
    """Test error handling in validation process"""
    message = ProcessingMessage(
        message_type=MessageType.ANALYTICS_VALIDATION_REQUEST,
        content={
            "validation_id": "test_validation_1",
            "analysis_id": "test_analysis_1",
            "data": {},  # Invalid data
            "validation_type": "model"
        }
    )

    response = await advanced_analytics_validator._handle_validation_request(message)
    assert response.message_type == MessageType.ANALYTICS_VALIDATION_FAILED
    assert "error" in response.content

@pytest.mark.asyncio
async def test_large_data_handling(advanced_analytics_validator):
    """Test handling of large datasets"""
    # Create a large dataset
    large_data = pd.DataFrame({
        "feature1": np.random.rand(10000),
        "feature2": np.random.rand(10000),
        "target": np.random.randint(0, 2, 10000)
    })

    validation_id = "test_validation_1"
    advanced_analytics_validator.active_validations[validation_id] = {
        "validation_id": validation_id,
        "analysis_id": "test_analysis_1",
        "data": large_data,
        "validation_type": "results",
        "start_time": datetime.now(),
        "status": "pending"
    }

    await advanced_analytics_validator._start_validation(validation_id)
    
    assert advanced_analytics_validator.active_validations[validation_id]["status"] == "completed"
    assert "validation_results" in advanced_analytics_validator.active_validations[validation_id]

@pytest.mark.asyncio
async def test_concurrent_validation_handling(advanced_analytics_validator, sample_data, sample_model):
    """Test handling of concurrent validation requests"""
    validation_ids = [f"test_validation_{i}" for i in range(3)]
    
    for validation_id in validation_ids:
        advanced_analytics_validator.active_validations[validation_id] = {
            "validation_id": validation_id,
            "analysis_id": f"test_analysis_{i}",
            "data": sample_data,
            "model": sample_model,
            "validation_type": "model",
            "start_time": datetime.now(),
            "status": "pending"
        }

    # Start all validations concurrently
    await asyncio.gather(*[
        advanced_analytics_validator._start_validation(validation_id)
        for validation_id in validation_ids
    ])

    # Verify all validations completed successfully
    for validation_id in validation_ids:
        assert advanced_analytics_validator.active_validations[validation_id]["status"] == "completed"
        assert "validation_results" in advanced_analytics_validator.active_validations[validation_id]

@pytest.mark.asyncio
async def test_calculate_consistency(advanced_analytics_validator, sample_data):
    """Test consistency calculation"""
    # Add some duplicate rows
    sample_data.loc[100] = sample_data.iloc[0]
    sample_data.loc[101] = sample_data.iloc[1]
    
    consistency = advanced_analytics_validator._calculate_consistency(sample_data)
    assert 0 <= consistency <= 1

@pytest.mark.asyncio
async def test_calculate_accuracy(advanced_analytics_validator, sample_data):
    """Test accuracy calculation"""
    # Add some negative values
    sample_data.loc[100] = [-1, -1, -1]
    
    accuracy = advanced_analytics_validator._calculate_accuracy(sample_data)
    assert 0 <= accuracy <= 1

@pytest.mark.asyncio
async def test_check_normality(advanced_analytics_validator, sample_data):
    """Test normality checking"""
    result = advanced_analytics_validator._check_normality(sample_data)
    
    assert "tests" in result
    assert "status" in result
    for column in sample_data.select_dtypes(include=[np.number]).columns:
        assert column in result["tests"]
        assert "p_value" in result["tests"][column]
        assert "status" in result["tests"][column]

@pytest.mark.asyncio
async def test_check_outliers(advanced_analytics_validator, sample_data):
    """Test outlier checking"""
    # Add some outliers
    sample_data.loc[100] = [1000, 1000, 1000]
    
    result = advanced_analytics_validator._check_outliers(sample_data)
    
    assert "checks" in result
    assert "status" in result
    for column in sample_data.select_dtypes(include=[np.number]).columns:
        assert column in result["checks"]
        assert "outlier_ratio" in result["checks"][column]
        assert "status" in result["checks"][column]

@pytest.mark.asyncio
async def test_check_correlation(advanced_analytics_validator, sample_data):
    """Test correlation checking"""
    result = advanced_analytics_validator._check_correlation(sample_data)
    
    assert "high_correlations" in result
    assert "status" in result
    assert isinstance(result["high_correlations"], list)

@pytest.mark.asyncio
async def test_check_value_ranges(advanced_analytics_validator, sample_data):
    """Test value range checking"""
    # Configure value ranges
    advanced_analytics_validator.config["value_ranges"] = {
        "feature1": {"min": 0, "max": 1},
        "feature2": {"min": 0, "max": 1}
    }
    
    result = advanced_analytics_validator._check_value_ranges(sample_data)
    
    assert "checks" in result
    assert "status" in result
    for column in ["feature1", "feature2"]:
        assert column in result["checks"]
        assert "violations" in result["checks"][column]
        assert "status" in result["checks"][column]

@pytest.mark.asyncio
async def test_check_relationships(advanced_analytics_validator, sample_data):
    """Test relationship checking"""
    # Configure relationships
    advanced_analytics_validator.config["relationships"] = [
        {"condition": "data['feature1'] >= 0"}
    ]
    
    result = advanced_analytics_validator._check_relationships(sample_data)
    
    assert "checks" in result
    assert "status" in result
    assert "data['feature1'] >= 0" in result["checks"]
    assert "violations" in result["checks"]["data['feature1'] >= 0"]
    assert "status" in result["checks"]["data['feature1'] >= 0"]

@pytest.mark.asyncio
async def test_check_constraints(advanced_analytics_validator, sample_data):
    """Test constraint checking"""
    # Configure constraints
    advanced_analytics_validator.config["constraints"] = [
        {"condition": "data['feature1'] >= 0"}
    ]
    
    result = advanced_analytics_validator._check_constraints(sample_data)
    
    assert "checks" in result
    assert "status" in result
    assert "data['feature1'] >= 0" in result["checks"]
    assert "violations" in result["checks"]["data['feature1'] >= 0"]
    assert "status" in result["checks"]["data['feature1'] >= 0"] 