import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from backend.core.managers.staging_manager import StagingManager
from backend.core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    StagingContext,
    StagingState,
    ManagerState
)
from db.repository.staging import StagingRepository

# Fixtures
@pytest.fixture
def mock_message_broker():
    broker = Mock()
    broker.publish = AsyncMock()
    broker.register_message_handler = AsyncMock()
    return broker

@pytest.fixture
def mock_repository():
    repository = Mock(spec=StagingRepository)
    repository.store = AsyncMock()
    repository.retrieve = AsyncMock()
    repository.delete = AsyncMock()
    repository.list_files = AsyncMock()
    return repository

@pytest.fixture
def storage_path(tmp_path):
    return tmp_path / "staging"

@pytest.fixture
def staging_manager(mock_message_broker, mock_repository, storage_path):
    manager = StagingManager(
        message_broker=mock_message_broker,
        repository=mock_repository,
        storage_path=storage_path,
        component_name="test_staging_manager",
        domain_type="staging"
    )
    return manager

@pytest.fixture
def sample_staging_context():
    return StagingContext(
        pipeline_id="test_pipeline",
        state=StagingState.INITIALIZING,
        metadata={
            "source_type": "analytics",
            "created_at": datetime.now().isoformat()
        }
    )

# Test Class
class TestStagingManager:
    """Test suite for StagingManager"""

    @pytest.mark.asyncio
    async def test_initialization(self, staging_manager, mock_message_broker, mock_repository, storage_path):
        """Test StagingManager initialization"""
        assert staging_manager.component_name == "test_staging_manager"
        assert staging_manager.state == ManagerState.INITIALIZING
        assert staging_manager.message_broker == mock_message_broker
        assert staging_manager.repository == mock_repository
        assert staging_manager.storage_path == storage_path
        assert staging_manager.staging_limits is not None
        assert staging_manager.storage_metrics is not None

    @pytest.mark.asyncio
    async def test_handle_store_request(self, staging_manager, sample_staging_context):
        """Test handling of store request"""
        # Arrange
        pipeline_id = "test_pipeline"
        data = b"test data"
        message = ProcessingMessage(
            message_type=MessageType.STAGING_STORE_REQUEST,
            content={
                "pipeline_id": pipeline_id,
                "data": data,
                "metadata": sample_staging_context.metadata
            },
            metadata=MessageMetadata(
                correlation_id="test_correlation",
                source_component="test_source",
                target_component="staging_manager",
                domain_type="staging"
            )
        )

        # Act
        await staging_manager._handle_store_request(message)

        # Assert
        staging_manager.message_broker.publish.assert_called()
        assert staging_manager.active_operations > 0
        assert staging_manager.storage_metrics.storage_operations > 0

    @pytest.mark.asyncio
    async def test_handle_retrieve_request(self, staging_manager, sample_staging_context):
        """Test handling of retrieve request"""
        # Arrange
        pipeline_id = "test_pipeline"
        message = ProcessingMessage(
            message_type=MessageType.STAGING_RETRIEVE_REQUEST,
            content={
                "pipeline_id": pipeline_id,
                "reference": "test_reference"
            },
            metadata=MessageMetadata(
                correlation_id="test_correlation",
                source_component="test_source",
                target_component="staging_manager",
                domain_type="staging"
            )
        )

        # Act
        await staging_manager._handle_retrieve_request(message)

        # Assert
        staging_manager.message_broker.publish.assert_called()
        staging_manager.repository.retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_delete_request(self, staging_manager, sample_staging_context):
        """Test handling of delete request"""
        # Arrange
        pipeline_id = "test_pipeline"
        message = ProcessingMessage(
            message_type=MessageType.STAGING_DELETE_REQUEST,
            content={
                "pipeline_id": pipeline_id,
                "reference": "test_reference"
            },
            metadata=MessageMetadata(
                correlation_id="test_correlation",
                source_component="test_source",
                target_component="staging_manager",
                domain_type="staging"
            )
        )

        # Act
        await staging_manager._handle_delete_request(message)

        # Assert
        staging_manager.message_broker.publish.assert_called()
        staging_manager.repository.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_access_request(self, staging_manager, sample_staging_context):
        """Test handling of access request"""
        # Arrange
        pipeline_id = "test_pipeline"
        message = ProcessingMessage(
            message_type=MessageType.STAGING_ACCESS_REQUEST,
            content={
                "pipeline_id": pipeline_id,
                "reference": "test_reference",
                "requester_id": "test_user"
            },
            metadata=MessageMetadata(
                correlation_id="test_correlation",
                source_component="test_source",
                target_component="staging_manager",
                domain_type="staging"
            )
        )

        # Act
        await staging_manager._handle_access_request(message)

        # Assert
        staging_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_cleanup_request(self, staging_manager, sample_staging_context):
        """Test handling of cleanup request"""
        # Arrange
        pipeline_id = "test_pipeline"
        message = ProcessingMessage(
            message_type=MessageType.STAGING_CLEANUP_REQUEST,
            content={
                "pipeline_id": pipeline_id,
                "force": False
            },
            metadata=MessageMetadata(
                correlation_id="test_correlation",
                source_component="test_source",
                target_component="staging_manager",
                domain_type="staging"
            )
        )

        # Act
        await staging_manager._handle_cleanup_request(message)

        # Assert
        staging_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_metrics_update(self, staging_manager, sample_staging_context):
        """Test handling of metrics update"""
        # Arrange
        pipeline_id = "test_pipeline"
        message = ProcessingMessage(
            message_type=MessageType.STAGING_METRICS_UPDATE,
            content={
                "pipeline_id": pipeline_id,
                "metrics": {
                    "storage_usage": 5.5,
                    "active_operations": 3,
                    "total_stored_bytes": 1024
                }
            },
            metadata=MessageMetadata(
                correlation_id="test_correlation",
                source_component="test_source",
                target_component="staging_manager",
                domain_type="staging"
            )
        )

        # Act
        await staging_manager._handle_metrics_update(message)

        # Assert
        staging_manager.message_broker.publish.assert_called()
        assert staging_manager.storage_metrics.current_storage_usage == 5.5
        assert staging_manager.storage_metrics.active_stages == 3

    @pytest.mark.asyncio
    async def test_handle_service_error(self, staging_manager, sample_staging_context):
        """Test handling of service error"""
        # Arrange
        pipeline_id = "test_pipeline"
        error_message = "Test error"
        message = ProcessingMessage(
            message_type=MessageType.STAGING_SERVICE_ERROR,
            content={
                "pipeline_id": pipeline_id,
                "error": error_message
            },
            metadata=MessageMetadata(
                correlation_id="test_correlation",
                source_component="test_source",
                target_component="staging_manager",
                domain_type="staging"
            )
        )

        # Act
        await staging_manager._handle_service_error(message)

        # Assert
        staging_manager.message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_backpressure(self, staging_manager):
        """Test handling of backpressure"""
        # Arrange
        staging_manager.active_operations = staging_manager.staging_limits['max_concurrent_operations']

        # Act
        await staging_manager._handle_backpressure()

        # Assert
        staging_manager.message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_data(self, staging_manager, sample_staging_context):
        """Test store_data method"""
        # Arrange
        data = "test data"
        metadata = sample_staging_context.metadata
        source_type = "analytics"

        # Act
        result = await staging_manager.store_data(data, metadata, source_type)

        # Assert
        assert result is not None
        assert "reference" in result
        assert "status" in result
        staging_manager.repository.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_data(self, staging_manager):
        """Test retrieve_data method"""
        # Arrange
        reference = "test_reference"
        requester_id = "test_user"

        # Act
        result = await staging_manager.retrieve_data(reference, requester_id)

        # Assert
        assert result is not None
        staging_manager.repository.retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_staged_files(self, staging_manager):
        """Test get_staged_files method"""
        # Arrange
        filter_params = {
            "source_type": "analytics",
            "created_after": datetime.now().isoformat()
        }

        # Act
        result = await staging_manager.get_staged_files(filter_params)

        # Assert
        assert isinstance(result, list)
        staging_manager.repository.list_files.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_files(self, staging_manager):
        """Test list_files method"""
        # Arrange
        user_id = "test_user"

        # Act
        result = await staging_manager.list_files(user_id)

        # Assert
        assert isinstance(result, list)
        staging_manager.repository.list_files.assert_called_once() 