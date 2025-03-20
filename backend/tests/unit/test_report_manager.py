import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import uuid
from backend.core.managers.report_manager import ReportManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ReportContext,
    ReportState,
    ManagerState,
    ReportMetrics,
    MessageMetadata,
    ReportFormat,
    ReportType
)

@pytest.fixture
def mock_message_broker():
    broker = Mock(spec=MessageBroker)
    broker.publish = AsyncMock()
    broker.register_message_handler = AsyncMock()
    return broker

@pytest.fixture
def report_manager(mock_message_broker):
    manager = ReportManager(
        message_broker=mock_message_broker,
        component_name="test_report_manager",
        domain_type="reporting"
    )
    return manager

@pytest.fixture
def sample_report_config():
    return {
        "report_type": ReportType.PERFORMANCE,
        "format": ReportFormat.PDF,
        "schedule": {
            "frequency": "daily",
            "time": "00:00",
            "timezone": "UTC"
        },
        "parameters": {
            "metrics": ["cpu_percent", "memory_percent", "disk_usage"],
            "time_range": "last_24h",
            "aggregation": "average"
        },
        "delivery": {
            "channels": ["email", "message_broker"],
            "recipients": ["admin@example.com"]
        }
    }

@pytest.fixture
def sample_report_context(sample_report_config):
    return ReportContext(
        report_id=str(uuid.uuid4()),
        correlation_id=str(uuid.uuid4()),
        state=ReportState.INITIALIZING,
        config=sample_report_config,
        metrics=ReportMetrics()
    )

class TestReportManager:
    """Test suite for ReportManager class"""

    @pytest.mark.asyncio
    async def test_initialization(self, report_manager, mock_message_broker):
        """Test proper initialization of ReportManager"""
        assert report_manager.component_name == "test_report_manager"
        assert report_manager.domain_type == "reporting"
        assert report_manager.state == ManagerState.INITIALIZING
        assert report_manager.message_broker == mock_message_broker
        assert isinstance(report_manager.active_contexts, dict)
        assert isinstance(report_manager.report_history, dict)
        assert isinstance(report_manager.scheduled_reports, dict)

    @pytest.mark.asyncio
    async def test_handle_report_request(self, report_manager, sample_report_config, mock_message_broker):
        """Test handling of report generation request"""
        # Arrange
        report_id = str(uuid.uuid4())
        message = ProcessingMessage(
            message_type=MessageType.REPORT_GENERATE_REQUEST,
            content={
                'report_id': report_id,
                'config': sample_report_config
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="report_manager"
            )
        )

        # Act
        await report_manager._handle_report_request(message)

        # Assert
        assert report_id in report_manager.active_contexts
        context = report_manager.active_contexts[report_id]
        assert context.state == ReportState.INITIALIZING
        assert context.config == sample_report_config
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_report_start(self, report_manager, sample_report_context, mock_message_broker):
        """Test handling of report generation start"""
        # Arrange
        report_id = sample_report_context.report_id
        report_manager.active_contexts[report_id] = sample_report_context
        message = ProcessingMessage(
            message_type=MessageType.REPORT_GENERATE_START,
            content={'report_id': report_id},
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="report_manager"
            )
        )

        # Act
        await report_manager._handle_report_start(message)

        # Assert
        context = report_manager.active_contexts[report_id]
        assert context.state == ReportState.GENERATING
        mock_message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_report_progress(self, report_manager, sample_report_context):
        """Test handling of report generation progress updates"""
        # Arrange
        report_id = sample_report_context.report_id
        report_manager.active_contexts[report_id] = sample_report_context
        progress = 50
        message = ProcessingMessage(
            message_type=MessageType.REPORT_GENERATE_PROGRESS,
            content={
                'report_id': report_id,
                'progress': progress
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="report_manager"
            )
        )

        # Act
        await report_manager._handle_report_progress(message)

        # Assert
        context = report_manager.active_contexts[report_id]
        assert context.progress == progress

    @pytest.mark.asyncio
    async def test_handle_report_complete(self, report_manager, sample_report_context, mock_message_broker):
        """Test handling of report generation completion"""
        # Arrange
        report_id = sample_report_context.report_id
        report_manager.active_contexts[report_id] = sample_report_context
        report_data = {
            "status": "success",
            "metrics": {
                "cpu_percent": 75.0,
                "memory_percent": 65.0,
                "disk_usage": 45.0
            },
            "timestamp": datetime.now().isoformat()
        }
        message = ProcessingMessage(
            message_type=MessageType.REPORT_GENERATE_COMPLETE,
            content={
                'report_id': report_id,
                'report_data': report_data
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="report_manager"
            )
        )

        # Act
        await report_manager._handle_report_complete(message)

        # Assert
        context = report_manager.active_contexts[report_id]
        assert context.state == ReportState.COMPLETED
        assert context.report_data == report_data
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_report_failed(self, report_manager, sample_report_context, mock_message_broker):
        """Test handling of report generation failure"""
        # Arrange
        report_id = sample_report_context.report_id
        report_manager.active_contexts[report_id] = sample_report_context
        error = "Test error"
        message = ProcessingMessage(
            message_type=MessageType.REPORT_GENERATE_FAILED,
            content={
                'report_id': report_id,
                'error': error
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="report_manager"
            )
        )

        # Act
        await report_manager._handle_report_failed(message)

        # Assert
        context = report_manager.active_contexts[report_id]
        assert context.state == ReportState.ERROR
        assert context.error == error
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_report_schedule(self, report_manager, sample_report_config, mock_message_broker):
        """Test handling of report scheduling"""
        # Arrange
        report_id = str(uuid.uuid4())
        message = ProcessingMessage(
            message_type=MessageType.REPORT_SCHEDULE,
            content={
                'report_id': report_id,
                'config': sample_report_config
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="report_manager"
            )
        )

        # Act
        await report_manager._handle_report_schedule(message)

        # Assert
        assert report_id in report_manager.scheduled_reports
        assert report_manager.scheduled_reports[report_id]["config"] == sample_report_config
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_report_delivery(self, report_manager, sample_report_context, mock_message_broker):
        """Test handling of report delivery"""
        # Arrange
        report_id = sample_report_context.report_id
        report_manager.active_contexts[report_id] = sample_report_context
        delivery_status = {
            "status": "success",
            "channels": ["email", "message_broker"],
            "timestamp": datetime.now().isoformat()
        }
        message = ProcessingMessage(
            message_type=MessageType.REPORT_DELIVERY_COMPLETE,
            content={
                'report_id': report_id,
                'delivery_status': delivery_status
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="report_manager"
            )
        )

        # Act
        await report_manager._handle_report_delivery(message)

        # Assert
        context = report_manager.active_contexts[report_id]
        assert context.delivery_status == delivery_status
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_report_archive(self, report_manager, sample_report_context, mock_message_broker):
        """Test handling of report archiving"""
        # Arrange
        report_id = sample_report_context.report_id
        report_manager.active_contexts[report_id] = sample_report_context
        archive_info = {
            "location": "archive/reports/2024/01",
            "filename": f"report_{report_id}.pdf",
            "timestamp": datetime.now().isoformat()
        }
        message = ProcessingMessage(
            message_type=MessageType.REPORT_ARCHIVE,
            content={
                'report_id': report_id,
                'archive_info': archive_info
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="report_manager"
            )
        )

        # Act
        await report_manager._handle_report_archive(message)

        # Assert
        assert report_id in report_manager.report_history
        assert report_manager.report_history[report_id]["archive_info"] == archive_info
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_report_retrieve(self, report_manager, sample_report_context, mock_message_broker):
        """Test handling of report retrieval requests"""
        # Arrange
        report_id = sample_report_context.report_id
        report_manager.report_history[report_id] = {
            "report_data": {"test": "data"},
            "archive_info": {
                "location": "archive/reports/2024/01",
                "filename": f"report_{report_id}.pdf"
            }
        }
        message = ProcessingMessage(
            message_type=MessageType.REPORT_RETRIEVE_REQUEST,
            content={'report_id': report_id},
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="report_manager"
            )
        )

        # Act
        await report_manager._handle_report_retrieve(message)

        # Assert
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_report_delete(self, report_manager, sample_report_context, mock_message_broker):
        """Test handling of report deletion"""
        # Arrange
        report_id = sample_report_context.report_id
        report_manager.active_contexts[report_id] = sample_report_context
        report_manager.report_history[report_id] = {"test": "data"}
        message = ProcessingMessage(
            message_type=MessageType.REPORT_DELETE_REQUEST,
            content={'report_id': report_id},
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="report_manager"
            )
        )

        # Act
        await report_manager._handle_report_delete(message)

        # Assert
        assert report_id not in report_manager.active_contexts
        assert report_id not in report_manager.report_history
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_report_template_update(self, report_manager, sample_report_config, mock_message_broker):
        """Test handling of report template updates"""
        # Arrange
        template_id = str(uuid.uuid4())
        template_data = {
            "name": "Performance Report Template",
            "description": "Template for performance reports",
            "config": sample_report_config
        }
        message = ProcessingMessage(
            message_type=MessageType.REPORT_TEMPLATE_UPDATE,
            content={
                'template_id': template_id,
                'template_data': template_data
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="report_manager"
            )
        )

        # Act
        await report_manager._handle_report_template_update(message)

        # Assert
        assert template_id in report_manager.report_templates
        assert report_manager.report_templates[template_id] == template_data
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_error(self, report_manager, sample_report_context, mock_message_broker):
        """Test handling of report generation errors"""
        # Arrange
        report_id = sample_report_context.report_id
        report_manager.active_contexts[report_id] = sample_report_context
        error = "Test error"

        # Act
        await report_manager._handle_error(report_id, error)

        # Assert
        context = report_manager.active_contexts[report_id]
        assert context.state == ReportState.ERROR
        assert context.error == error
        mock_message_broker.publish.assert_called_once() 