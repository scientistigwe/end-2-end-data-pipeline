import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import uuid
from backend.core.managers.monitoring_manager import MonitoringManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MonitoringContext,
    MonitoringState,
    ManagerState,
    MonitoringMetrics,
    MessageMetadata
)

@pytest.fixture
def mock_message_broker():
    broker = Mock(spec=MessageBroker)
    broker.publish = AsyncMock()
    broker.register_message_handler = AsyncMock()
    return broker

@pytest.fixture
def monitoring_manager(mock_message_broker):
    manager = MonitoringManager(
        message_broker=mock_message_broker,
        component_name="test_monitoring_manager",
        domain_type="monitoring"
    )
    return manager

@pytest.fixture
def sample_monitoring_config():
    return {
        "metrics": ["cpu_percent", "memory_percent", "disk_usage"],
        "thresholds": {
            "cpu_percent": {
                "warning": 80.0,
                "critical": 90.0
            },
            "memory_percent": {
                "warning": 80.0,
                "critical": 90.0
            },
            "disk_usage": {
                "warning": 80.0,
                "critical": 90.0
            }
        },
        "alerting": {
            "cooldown_period": 300,
            "max_alerts_per_hour": 10,
            "alert_channels": ["log", "message_broker"]
        }
    }

@pytest.fixture
def sample_monitoring_context(sample_monitoring_config):
    return MonitoringContext(
        monitoring_id=str(uuid.uuid4()),
        correlation_id=str(uuid.uuid4()),
        state=MonitoringState.INITIALIZING,
        config=sample_monitoring_config,
        metrics=MonitoringMetrics()
    )

class TestMonitoringManager:
    """Test suite for MonitoringManager class"""

    @pytest.mark.asyncio
    async def test_initialization(self, monitoring_manager, mock_message_broker):
        """Test proper initialization of MonitoringManager"""
        assert monitoring_manager.component_name == "test_monitoring_manager"
        assert monitoring_manager.domain_type == "monitoring"
        assert monitoring_manager.state == ManagerState.INITIALIZING
        assert monitoring_manager.message_broker == mock_message_broker
        assert isinstance(monitoring_manager.active_contexts, dict)
        assert isinstance(monitoring_manager.metric_history, dict)
        assert isinstance(monitoring_manager.alert_history, dict)
        assert isinstance(monitoring_manager.last_alert_time, dict)

    @pytest.mark.asyncio
    async def test_handle_start_request(self, monitoring_manager, sample_monitoring_config, mock_message_broker):
        """Test handling of monitoring start request"""
        # Arrange
        monitoring_id = str(uuid.uuid4())
        message = ProcessingMessage(
            message_type=MessageType.MONITORING_START_REQUEST,
            content={
                'monitoring_id': monitoring_id,
                'config': sample_monitoring_config
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="monitoring_manager"
            )
        )

        # Act
        await monitoring_manager._handle_start_request(message)

        # Assert
        assert monitoring_id in monitoring_manager.active_contexts
        context = monitoring_manager.active_contexts[monitoring_id]
        assert context.state == MonitoringState.INITIALIZING
        assert context.config == sample_monitoring_config
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_start(self, monitoring_manager, sample_monitoring_context, mock_message_broker):
        """Test handling of monitoring start"""
        # Arrange
        monitoring_id = sample_monitoring_context.monitoring_id
        monitoring_manager.active_contexts[monitoring_id] = sample_monitoring_context
        message = ProcessingMessage(
            message_type=MessageType.MONITORING_START,
            content={'monitoring_id': monitoring_id},
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="monitoring_manager"
            )
        )

        # Act
        await monitoring_manager._handle_start(message)

        # Assert
        context = monitoring_manager.active_contexts[monitoring_id]
        assert context.state == MonitoringState.ACTIVE
        mock_message_broker.publish.assert_called()

    @pytest.mark.asyncio
    async def test_handle_progress(self, monitoring_manager, sample_monitoring_context):
        """Test handling of monitoring progress updates"""
        # Arrange
        monitoring_id = sample_monitoring_context.monitoring_id
        monitoring_manager.active_contexts[monitoring_id] = sample_monitoring_context
        progress = 50
        message = ProcessingMessage(
            message_type=MessageType.MONITORING_PROGRESS,
            content={
                'monitoring_id': monitoring_id,
                'progress': progress
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="monitoring_manager"
            )
        )

        # Act
        await monitoring_manager._handle_progress(message)

        # Assert
        context = monitoring_manager.active_contexts[monitoring_id]
        assert context.progress == progress

    @pytest.mark.asyncio
    async def test_handle_complete(self, monitoring_manager, sample_monitoring_context, mock_message_broker):
        """Test handling of monitoring completion"""
        # Arrange
        monitoring_id = sample_monitoring_context.monitoring_id
        monitoring_manager.active_contexts[monitoring_id] = sample_monitoring_context
        results = {"status": "success", "metrics": {"cpu_percent": 75.0}}
        message = ProcessingMessage(
            message_type=MessageType.MONITORING_COMPLETE,
            content={
                'monitoring_id': monitoring_id,
                'results': results
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="monitoring_manager"
            )
        )

        # Act
        await monitoring_manager._handle_complete(message)

        # Assert
        context = monitoring_manager.active_contexts[monitoring_id]
        assert context.state == MonitoringState.COMPLETED
        assert context.results == results
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_failed(self, monitoring_manager, sample_monitoring_context, mock_message_broker):
        """Test handling of monitoring failure"""
        # Arrange
        monitoring_id = sample_monitoring_context.monitoring_id
        monitoring_manager.active_contexts[monitoring_id] = sample_monitoring_context
        error = "Test error"
        message = ProcessingMessage(
            message_type=MessageType.MONITORING_FAILED,
            content={
                'monitoring_id': monitoring_id,
                'error': error
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="monitoring_manager"
            )
        )

        # Act
        await monitoring_manager._handle_failed(message)

        # Assert
        context = monitoring_manager.active_contexts[monitoring_id]
        assert context.state == MonitoringState.ERROR
        assert context.error == error
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_metric_collect(self, monitoring_manager, sample_monitoring_context, mock_message_broker):
        """Test handling of metric collection"""
        # Arrange
        monitoring_id = sample_monitoring_context.monitoring_id
        monitoring_manager.active_contexts[monitoring_id] = sample_monitoring_context
        metric = "cpu_percent"
        message = ProcessingMessage(
            message_type=MessageType.MONITORING_METRIC_COLLECT,
            content={
                'monitoring_id': monitoring_id,
                'metric': metric
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="monitoring_manager"
            )
        )

        # Act
        await monitoring_manager._handle_metric_collect(message)

        # Assert
        context = monitoring_manager.active_contexts[monitoring_id]
        assert hasattr(context.metrics, metric)
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_metric_update(self, monitoring_manager, sample_monitoring_context, mock_message_broker):
        """Test handling of metric updates"""
        # Arrange
        monitoring_id = sample_monitoring_context.monitoring_id
        monitoring_manager.active_contexts[monitoring_id] = sample_monitoring_context
        metric = "cpu_percent"
        value = 75.0
        message = ProcessingMessage(
            message_type=MessageType.MONITORING_METRIC_UPDATE,
            content={
                'monitoring_id': monitoring_id,
                'metric': metric,
                'value': value
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="monitoring_manager"
            )
        )

        # Act
        await monitoring_manager._handle_metric_update(message)

        # Assert
        context = monitoring_manager.active_contexts[monitoring_id]
        assert getattr(context.metrics, metric) == value
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_threshold_violation(self, monitoring_manager, sample_monitoring_context, mock_message_broker):
        """Test handling of threshold violations"""
        # Arrange
        monitoring_id = sample_monitoring_context.monitoring_id
        monitoring_manager.active_contexts[monitoring_id] = sample_monitoring_context
        metric = "cpu_percent"
        value = 95.0
        threshold = monitoring_manager.monitoring_config["thresholds"][metric]
        severity = "critical"

        # Act
        await monitoring_manager._handle_threshold_violation(monitoring_id, metric, value, threshold, severity)

        # Assert
        assert monitoring_id in monitoring_manager.alert_history
        assert len(monitoring_manager.alert_history[monitoring_id]) > 0
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_alert_create(self, monitoring_manager, sample_monitoring_context, mock_message_broker):
        """Test handling of alert creation"""
        # Arrange
        monitoring_id = sample_monitoring_context.monitoring_id
        monitoring_manager.active_contexts[monitoring_id] = sample_monitoring_context
        alert = {
            "alert_id": str(uuid.uuid4()),
            "metric": "cpu_percent",
            "value": 95.0,
            "severity": "critical",
            "timestamp": datetime.now().isoformat()
        }
        message = ProcessingMessage(
            message_type=MessageType.MONITORING_ALERT_CREATE,
            content={
                'monitoring_id': monitoring_id,
                'alert': alert
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="monitoring_manager"
            )
        )

        # Act
        await monitoring_manager._handle_alert_create(message)

        # Assert
        assert monitoring_id in monitoring_manager.alert_history
        assert len(monitoring_manager.alert_history[monitoring_id]) > 0
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_alert_resolve(self, monitoring_manager, sample_monitoring_context, mock_message_broker):
        """Test handling of alert resolution"""
        # Arrange
        monitoring_id = sample_monitoring_context.monitoring_id
        monitoring_manager.active_contexts[monitoring_id] = sample_monitoring_context
        alert_id = str(uuid.uuid4())
        monitoring_manager.alert_history[monitoring_id] = [{
            "alert_id": alert_id,
            "status": "active"
        }]
        message = ProcessingMessage(
            message_type=MessageType.MONITORING_ALERT_RESOLVE,
            content={
                'monitoring_id': monitoring_id,
                'alert_id': alert_id
            },
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="monitoring_manager"
            )
        )

        # Act
        await monitoring_manager._handle_alert_resolve(message)

        # Assert
        alert = monitoring_manager.alert_history[monitoring_id][0]
        assert alert["status"] == "resolved"
        assert "resolved_at" in alert
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_health_check(self, monitoring_manager, sample_monitoring_context, mock_message_broker):
        """Test handling of health check requests"""
        # Arrange
        monitoring_id = sample_monitoring_context.monitoring_id
        monitoring_manager.active_contexts[monitoring_id] = sample_monitoring_context
        message = ProcessingMessage(
            message_type=MessageType.MONITORING_HEALTH_CHECK,
            content={'monitoring_id': monitoring_id},
            metadata=MessageMetadata(
                source_component="test_source",
                target_component="monitoring_manager"
            )
        )

        # Act
        await monitoring_manager._handle_health_check(message)

        # Assert
        mock_message_broker.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_monitoring(self, monitoring_manager, sample_monitoring_context):
        """Test cleanup of monitoring resources"""
        # Arrange
        monitoring_id = sample_monitoring_context.monitoring_id
        monitoring_manager.active_contexts[monitoring_id] = sample_monitoring_context
        monitoring_manager.metric_history[monitoring_id] = []
        monitoring_manager.alert_history[monitoring_id] = []
        monitoring_manager.last_alert_time[monitoring_id] = datetime.now()

        # Act
        await monitoring_manager._cleanup_monitoring(monitoring_id)

        # Assert
        assert monitoring_id not in monitoring_manager.active_contexts
        assert monitoring_id not in monitoring_manager.metric_history
        assert monitoring_id not in monitoring_manager.alert_history
        assert monitoring_id not in monitoring_manager.last_alert_time

    @pytest.mark.asyncio
    async def test_handle_error(self, monitoring_manager, sample_monitoring_context, mock_message_broker):
        """Test handling of monitoring errors"""
        # Arrange
        monitoring_id = sample_monitoring_context.monitoring_id
        monitoring_manager.active_contexts[monitoring_id] = sample_monitoring_context
        error = "Test error"

        # Act
        await monitoring_manager._handle_error(monitoring_id, error)

        # Assert
        context = monitoring_manager.active_contexts[monitoring_id]
        assert context.state == MonitoringState.ERROR
        assert context.error == error
        mock_message_broker.publish.assert_called_once() 