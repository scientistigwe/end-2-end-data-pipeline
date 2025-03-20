import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import Dict, Any

from backend.core.managers.recommendation_manager import RecommendationManager
from backend.core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    RecommendationContext,
    RecommendationState,
    ManagerState
)

# Fixtures
@pytest.fixture
def mock_message_broker():
    broker = Mock()
    broker.publish = AsyncMock()
    broker.register_message_handler = AsyncMock()
    return broker

@pytest.fixture
def recommendation_manager(mock_message_broker):
    manager = RecommendationManager(
        message_broker=mock_message_broker,
        component_name="test_recommendation_manager",
        domain_type="recommendation"
    )
    return manager

@pytest.fixture
def sample_recommendation_config():
    return {
        "recommendation_type": "hybrid",
        "engines": {
            "content": {
                "type": "content",
                "weight": 0.4,
                "parameters": {
                    "feature_extraction": "tfidf",
                    "similarity_metric": "cosine"
                }
            },
            "collaborative": {
                "type": "collaborative",
                "weight": 0.3,
                "parameters": {
                    "algorithm": "user_based",
                    "neighborhood_size": 50
                }
            },
            "contextual": {
                "type": "contextual",
                "weight": 0.3,
                "parameters": {
                    "context_features": ["time", "location", "device"]
                }
            }
        },
        "filters": {
            "diversity": {
                "type": "diversity",
                "parameters": {
                    "min_diversity_score": 0.3
                },
                "order": 1
            },
            "business_rules": {
                "type": "business_rules",
                "parameters": {
                    "rules": ["availability", "pricing"]
                },
                "order": 2
            }
        },
        "max_recommendations": 10,
        "ensure_diversity": True
    }

@pytest.fixture
def sample_recommendation_context(sample_recommendation_config):
    return RecommendationContext(
        pipeline_id="test_pipeline",
        correlation_id="test_correlation",
        state=RecommendationState.INITIALIZING,
        config=sample_recommendation_config,
        created_at=datetime.now()
    )

# Test Class
class TestRecommendationManager:
    """Test suite for RecommendationManager"""

    @pytest.mark.asyncio
    async def test_initialization(self, recommendation_manager, mock_message_broker):
        """Test RecommendationManager initialization"""
        assert recommendation_manager.component_name == "test_recommendation_manager"
        assert recommendation_manager.state == ManagerState.INITIALIZING
        assert recommendation_manager.message_broker == mock_message_broker
        assert recommendation_manager.recommendation_thresholds is not None

    @pytest.mark.asyncio
    async def test_handle_generate_request(self, recommendation_manager, sample_recommendation_config):
        """Test handling of recommendation generation request"""
        # Arrange
        pipeline_id = "test_pipeline"
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_GENERATE_REQUEST,
            content={
                "pipeline_id": pipeline_id,
                "config": sample_recommendation_config
            },
            metadata=MessageMetadata(
                correlation_id="test_correlation",
                source_component="test_source",
                target_component="recommendation_manager",
                domain_type="recommendation"
            )
        )

        # Act
        await recommendation_manager._handle_generate_request(message)

        # Assert
        assert pipeline_id in recommendation_manager.active_processes
        context = recommendation_manager.active_processes[pipeline_id]
        assert context.state == RecommendationState.INITIALIZING
        assert context.config == sample_recommendation_config
        recommendation_manager.message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_process_start(self, recommendation_manager, sample_recommendation_context):
        """Test handling of process start"""
        # Arrange
        pipeline_id = "test_pipeline"
        recommendation_manager.active_processes[pipeline_id] = sample_recommendation_context
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_PROCESS_START,
            content={
                "pipeline_id": pipeline_id,
                "config": sample_recommendation_context.config
            }
        )

        # Act
        await recommendation_manager._handle_process_start(message)

        # Assert
        context = recommendation_manager.active_processes[pipeline_id]
        assert context.state == RecommendationState.INITIALIZING
        recommendation_manager.message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_candidates_generate(self, recommendation_manager, sample_recommendation_context):
        """Test handling of candidate generation"""
        # Arrange
        pipeline_id = "test_pipeline"
        recommendation_manager.active_processes[pipeline_id] = sample_recommendation_context
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_CANDIDATES_GENERATE_REQUEST,
            content={
                "pipeline_id": pipeline_id,
                "config": sample_recommendation_context.config
            }
        )

        # Act
        await recommendation_manager._handle_candidates_generate(message)

        # Assert
        context = recommendation_manager.active_processes[pipeline_id]
        assert context.state == RecommendationState.GENERATING
        recommendation_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_filter_request(self, recommendation_manager, sample_recommendation_context):
        """Test handling of filter request"""
        # Arrange
        pipeline_id = "test_pipeline"
        recommendation_manager.active_processes[pipeline_id] = sample_recommendation_context
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_FILTER_REQUEST,
            content={
                "pipeline_id": pipeline_id,
                "filters": sample_recommendation_context.config["filters"]
            }
        )

        # Act
        await recommendation_manager._handle_filter_request(message)

        # Assert
        context = recommendation_manager.active_processes[pipeline_id]
        assert context.state == RecommendationState.FILTERING
        recommendation_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_rank_request(self, recommendation_manager, sample_recommendation_context):
        """Test handling of rank request"""
        # Arrange
        pipeline_id = "test_pipeline"
        recommendation_manager.active_processes[pipeline_id] = sample_recommendation_context
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_RANK_REQUEST,
            content={
                "pipeline_id": pipeline_id,
                "ranking_config": {"criteria": ["score", "diversity"]}
            }
        )

        # Act
        await recommendation_manager._handle_rank_request(message)

        # Assert
        context = recommendation_manager.active_processes[pipeline_id]
        assert context.state == RecommendationState.RANKING
        recommendation_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_validate_request(self, recommendation_manager, sample_recommendation_context):
        """Test handling of validate request"""
        # Arrange
        pipeline_id = "test_pipeline"
        recommendation_manager.active_processes[pipeline_id] = sample_recommendation_context
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_VALIDATE_REQUEST,
            content={
                "pipeline_id": pipeline_id,
                "validation_config": {"rules": ["quality", "diversity"]}
            }
        )

        # Act
        await recommendation_manager._handle_validate_request(message)

        # Assert
        context = recommendation_manager.active_processes[pipeline_id]
        assert context.state == RecommendationState.VALIDATION
        recommendation_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_validate_complete(self, recommendation_manager, sample_recommendation_context):
        """Test handling of validation completion"""
        # Arrange
        pipeline_id = "test_pipeline"
        recommendation_manager.active_processes[pipeline_id] = sample_recommendation_context
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_VALIDATE_COMPLETE,
            content={
                "pipeline_id": pipeline_id,
                "validation_results": {"passed": True, "metrics": {}}
            }
        )

        # Act
        await recommendation_manager._handle_validate_complete(message)

        # Assert
        context = recommendation_manager.active_processes[pipeline_id]
        assert context.validation_results == {"passed": True, "metrics": {}}
        recommendation_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_validate_reject(self, recommendation_manager, sample_recommendation_context):
        """Test handling of validation rejection"""
        # Arrange
        pipeline_id = "test_pipeline"
        recommendation_manager.active_processes[pipeline_id] = sample_recommendation_context
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_VALIDATE_REJECT,
            content={
                "pipeline_id": pipeline_id,
                "reason": "Failed quality check"
            }
        )

        # Act
        await recommendation_manager._handle_validate_reject(message)

        # Assert
        context = recommendation_manager.active_processes[pipeline_id]
        assert context.validation_results["rejected"] is True
        assert context.validation_results["rejection_reason"] == "Failed quality check"
        recommendation_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_diversity_ensure(self, recommendation_manager, sample_recommendation_context):
        """Test handling of diversity enforcement"""
        # Arrange
        pipeline_id = "test_pipeline"
        recommendation_manager.active_processes[pipeline_id] = sample_recommendation_context
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_DIVERSITY_ENSURE,
            content={
                "pipeline_id": pipeline_id,
                "diversity_config": {"min_diversity_score": 0.3}
            }
        )

        # Act
        await recommendation_manager._handle_diversity_ensure(message)

        # Assert
        recommendation_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_feedback_incorporate(self, recommendation_manager, sample_recommendation_context):
        """Test handling of feedback incorporation"""
        # Arrange
        pipeline_id = "test_pipeline"
        recommendation_manager.active_processes[pipeline_id] = sample_recommendation_context
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_FEEDBACK_INCORPORATE,
            content={
                "pipeline_id": pipeline_id,
                "feedback": {
                    "user_id": "test_user",
                    "item_id": "test_item",
                    "rating": 5
                }
            }
        )

        # Act
        await recommendation_manager._handle_feedback_incorporate(message)

        # Assert
        recommendation_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_business_rules(self, recommendation_manager, sample_recommendation_context):
        """Test handling of business rules"""
        # Arrange
        pipeline_id = "test_pipeline"
        recommendation_manager.active_processes[pipeline_id] = sample_recommendation_context
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_BUSINESS_RULES,
            content={
                "pipeline_id": pipeline_id,
                "business_rules": {
                    "rules": ["availability", "pricing"],
                    "parameters": {}
                }
            }
        )

        # Act
        await recommendation_manager._handle_business_rules(message)

        # Assert
        recommendation_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_metrics_update(self, recommendation_manager, sample_recommendation_context):
        """Test handling of metrics update"""
        # Arrange
        pipeline_id = "test_pipeline"
        recommendation_manager.active_processes[pipeline_id] = sample_recommendation_context
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_METRICS_UPDATE,
            content={
                "pipeline_id": pipeline_id,
                "metrics": {
                    "precision": 0.85,
                    "recall": 0.78,
                    "ndcg": 0.92
                }
            }
        )

        # Act
        await recommendation_manager._handle_metrics_update(message)

        # Assert
        recommendation_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_config_update(self, recommendation_manager, sample_recommendation_context):
        """Test handling of configuration update"""
        # Arrange
        pipeline_id = "test_pipeline"
        recommendation_manager.active_processes[pipeline_id] = sample_recommendation_context
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_CONFIG_UPDATE,
            content={
                "pipeline_id": pipeline_id,
                "config": {
                    "max_recommendations": 15,
                    "ensure_diversity": True
                },
                "restart_required": False
            }
        )

        # Act
        await recommendation_manager._handle_config_update(message)

        # Assert
        context = recommendation_manager.active_processes[pipeline_id]
        assert context.config["max_recommendations"] == 15
        recommendation_manager.message_broker.publish.assert_called() 