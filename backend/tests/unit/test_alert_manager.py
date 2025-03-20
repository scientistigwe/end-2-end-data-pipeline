import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any, List
import uuid

from core.services.monitoring.alert_manager import AlertManager, AlertRuleType
from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    AlertSeverity,
    AlertRule,
    AlertCondition,
    AlertNotification,
    AlertHistory
)

@pytest.fixture
def mock_message_broker():
    broker = Mock(spec=MessageBroker)
    broker.subscribe = AsyncMock()
    broker.publish = AsyncMock()
    broker.is_connected = Mock(return_value=True)
    return broker

@pytest.fixture
def alert_manager(mock_message_broker):
    return AlertManager(mock_message_broker)

@pytest.fixture
def sample_alert_rule():
    return {
        'rule_id': str(uuid.uuid4()),
        'name': 'Test Rule',
        'description': 'Test alert rule',
        'rule_type': AlertRuleType.METRIC_THRESHOLD,
        'severity': AlertSeverity.WARNING,
        'message': 'Test alert message',
        'condition': {
            'metric_name': 'cpu_usage',
            'operator': '>',
            'threshold': 80.0
        },
        'notification_channels': ['email_channel', 'slack_channel'],
        'details': {'source': 'test'}
    }

@pytest.fixture
def sample_notification_channel():
    return {
        'channel_id': 'test_channel',
        'name': 'Test Channel',
        'type': 'email',
        'config': {
            'recipients': ['test@example.com'],
            'subject_template': 'Alert: {message}'
        }
    }

@pytest.mark.asyncio
async def test_initialization(alert_manager, mock_message_broker):
    """Test AlertManager initialization"""
    assert alert_manager.alert_history == []
    assert alert_manager.alert_rules == {}
    assert alert_manager.notification_channels == {}
    assert alert_manager.alert_cooldown == {}
    assert alert_manager.cooldown_period == 300
    
    # Verify message broker subscriptions
    mock_message_broker.subscribe.assert_called()

@pytest.mark.asyncio
async def test_handle_alert_rule_create(alert_manager, mock_message_broker, sample_alert_rule):
    """Test handling of alert rule creation request"""
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_ALERT_RULE_CREATE,
        content={'rule': sample_alert_rule}
    )
    
    await alert_manager._handle_alert_rule_create(message)
    
    # Verify alert rule was created
    assert sample_alert_rule['rule_id'] in alert_manager.alert_rules
    rule = alert_manager.alert_rules[sample_alert_rule['rule_id']]
    assert rule.name == sample_alert_rule['name']
    assert rule.rule_type == sample_alert_rule['rule_type']
    
    # Verify rule creation notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_ALERT_RULE_CREATED

@pytest.mark.asyncio
async def test_handle_alert_rule_update(alert_manager, mock_message_broker, sample_alert_rule):
    """Test handling of alert rule update request"""
    # Create initial rule
    alert_manager.alert_rules[sample_alert_rule['rule_id']] = AlertRule(**sample_alert_rule)
    
    # Update rule
    updated_rule = sample_alert_rule.copy()
    updated_rule['message'] = 'Updated alert message'
    
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_ALERT_RULE_UPDATE,
        content={
            'rule_id': sample_alert_rule['rule_id'],
            'rule': updated_rule
        }
    )
    
    await alert_manager._handle_alert_rule_update(message)
    
    # Verify alert rule was updated
    rule = alert_manager.alert_rules[sample_alert_rule['rule_id']]
    assert rule.message == 'Updated alert message'
    
    # Verify rule update notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_ALERT_RULE_UPDATED

@pytest.mark.asyncio
async def test_handle_alert_rule_delete(alert_manager, mock_message_broker, sample_alert_rule):
    """Test handling of alert rule deletion request"""
    # Create initial rule
    alert_manager.alert_rules[sample_alert_rule['rule_id']] = AlertRule(**sample_alert_rule)
    
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_ALERT_RULE_DELETE,
        content={'rule_id': sample_alert_rule['rule_id']}
    )
    
    await alert_manager._handle_alert_rule_delete(message)
    
    # Verify alert rule was deleted
    assert sample_alert_rule['rule_id'] not in alert_manager.alert_rules
    
    # Verify rule deletion notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_ALERT_RULE_DELETED

@pytest.mark.asyncio
async def test_handle_notification_create(alert_manager, mock_message_broker, sample_notification_channel):
    """Test handling of notification channel creation request"""
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_ALERT_NOTIFICATION_CREATE,
        content={'channel': sample_notification_channel}
    )
    
    await alert_manager._handle_notification_create(message)
    
    # Verify notification channel was created
    assert sample_notification_channel['channel_id'] in alert_manager.notification_channels
    channel = alert_manager.notification_channels[sample_notification_channel['channel_id']]
    assert channel['name'] == sample_notification_channel['name']
    assert channel['type'] == sample_notification_channel['type']
    
    # Verify channel creation notification was published
    mock_message_broker.publish.assert_called_once()
    published_message = mock_message_broker.publish.call_args[0][0]
    assert published_message.message_type == MessageType.MONITORING_ALERT_NOTIFICATION_CREATED

@pytest.mark.asyncio
async def test_handle_metrics_update(alert_manager, mock_message_broker, sample_alert_rule):
    """Test handling of metrics update and alert rule evaluation"""
    # Create metric threshold rule
    alert_manager.alert_rules[sample_alert_rule['rule_id']] = AlertRule(**sample_alert_rule)
    
    # Send metrics update
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_METRICS_UPDATE,
        content={'metrics': {'cpu_usage': 90.0}}
    )
    
    await alert_manager._handle_metrics_update(message)
    
    # Verify alert was generated
    assert len(alert_manager.alert_history) == 1
    alert = alert_manager.alert_history[0]
    assert alert.rule_id == sample_alert_rule['rule_id']
    assert alert.value == 90.0

@pytest.mark.asyncio
async def test_handle_health_result(alert_manager, mock_message_broker):
    """Test handling of health check results and status-based alert rules"""
    # Create status change rule
    status_rule = {
        'rule_id': str(uuid.uuid4()),
        'name': 'Status Rule',
        'rule_type': AlertRuleType.STATUS_CHANGE,
        'severity': AlertSeverity.WARNING,
        'message': 'Component status changed',
        'condition': {
            'component_id': 'test_component',
            'operator': '==',
            'threshold': 'error'
        },
        'notification_channels': ['email_channel']
    }
    alert_manager.alert_rules[status_rule['rule_id']] = AlertRule(**status_rule)
    
    # Send health result
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_HEALTH_RESULT,
        content={
            'result': {
                'components': {
                    'test_component': {'status': 'error'}
                }
            }
        }
    )
    
    await alert_manager._handle_health_result(message)
    
    # Verify alert was generated
    assert len(alert_manager.alert_history) == 1
    alert = alert_manager.alert_history[0]
    assert alert.rule_id == status_rule['rule_id']
    assert alert.value == 'error'

@pytest.mark.asyncio
async def test_handle_anomaly_detected(alert_manager, mock_message_broker):
    """Test handling of anomaly detection results and anomaly-based alert rules"""
    # Create anomaly detection rule
    anomaly_rule = {
        'rule_id': str(uuid.uuid4()),
        'name': 'Anomaly Rule',
        'rule_type': AlertRuleType.ANOMALY_DETECTION,
        'severity': AlertSeverity.WARNING,
        'message': 'Anomaly detected',
        'condition': {
            'metric_name': 'response_time',
            'operator': '>',
            'threshold': 2.0
        },
        'notification_channels': ['email_channel']
    }
    alert_manager.alert_rules[anomaly_rule['rule_id']] = AlertRule(**anomaly_rule)
    
    # Send anomaly detection result
    message = ProcessingMessage(
        message_type=MessageType.MONITORING_ANOMALY_DETECTED,
        content={
            'anomaly': {
                'response_time': 2.5
            }
        }
    )
    
    await alert_manager._handle_anomaly_detected(message)
    
    # Verify alert was generated
    assert len(alert_manager.alert_history) == 1
    alert = alert_manager.alert_history[0]
    assert alert.rule_id == anomaly_rule['rule_id']
    assert alert.value == 2.5

@pytest.mark.asyncio
async def test_check_condition(alert_manager):
    """Test alert condition checking"""
    condition = AlertCondition(
        metric_name='test_metric',
        operator='>',
        threshold=100
    )
    
    # Test greater than
    assert alert_manager._check_condition(condition, 150) is True
    assert alert_manager._check_condition(condition, 50) is False
    
    # Test less than
    condition.operator = '<'
    assert alert_manager._check_condition(condition, 50) is True
    assert alert_manager._check_condition(condition, 150) is False
    
    # Test equals
    condition.operator = '=='
    condition.threshold = 100
    assert alert_manager._check_condition(condition, 100) is True
    assert alert_manager._check_condition(condition, 50) is False

@pytest.mark.asyncio
async def test_alert_cooldown(alert_manager, mock_message_broker, sample_alert_rule):
    """Test alert cooldown mechanism"""
    # Create alert rule
    alert_manager.alert_rules[sample_alert_rule['rule_id']] = AlertRule(**sample_alert_rule)
    
    # Generate first alert
    await alert_manager._generate_alert(
        alert_manager.alert_rules[sample_alert_rule['rule_id']],
        90.0
    )
    
    # Verify first alert was generated
    assert len(alert_manager.alert_history) == 1
    
    # Try to generate second alert immediately
    await alert_manager._generate_alert(
        alert_manager.alert_rules[sample_alert_rule['rule_id']],
        95.0
    )
    
    # Verify second alert was not generated due to cooldown
    assert len(alert_manager.alert_history) == 1

@pytest.mark.asyncio
async def test_cleanup_old_alerts(alert_manager):
    """Test cleanup of old alerts"""
    # Add old and recent alerts
    old_time = datetime.now() - timedelta(days=31)
    recent_time = datetime.now()
    
    alert_manager.alert_history = [
        AlertHistory(
            alert_id=str(uuid.uuid4()),
            rule_id=str(uuid.uuid4()),
            severity=AlertSeverity.WARNING,
            message='Old alert',
            timestamp=old_time,
            value=100,
            details={}
        ),
        AlertHistory(
            alert_id=str(uuid.uuid4()),
            rule_id=str(uuid.uuid4()),
            severity=AlertSeverity.WARNING,
            message='Recent alert',
            timestamp=recent_time,
            value=200,
            details={}
        )
    ]
    
    # Clean up old alerts
    alert_manager._cleanup_old_alerts()
    
    # Verify only recent alert remains
    assert len(alert_manager.alert_history) == 1
    assert alert_manager.alert_history[0].message == 'Recent alert' 