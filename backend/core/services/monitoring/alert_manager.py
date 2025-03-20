import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json

from ..base.base_service import BaseService
from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    HealthStatus,
    AlertSeverity,
    AlertRule,
    AlertCondition,
    AlertNotification,
    AlertHistory
)

logger = logging.getLogger(__name__)

class AlertRuleType(Enum):
    """Types of alert rules"""
    METRIC_THRESHOLD = "metric_threshold"
    STATUS_CHANGE = "status_change"
    ANOMALY_DETECTION = "anomaly_detection"
    CUSTOM = "custom"

class AlertManager(BaseService):
    """
    Service for managing alert rules, conditions, and notifications.
    Handles alert generation, notification delivery, and alert history.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker)
        
        # Service identifier
        self.module_identifier = ModuleIdentifier(
            component_name="alert_manager",
            component_type=ComponentType.MONITORING_SERVICE,
            department="monitoring",
            role="alerting"
        )

        # Alert configuration
        self.alert_history: List[AlertHistory] = []
        self.alert_rules: Dict[str, AlertRule] = {}
        self.notification_channels: Dict[str, Any] = {}
        self.alert_cooldown: Dict[str, datetime] = {}
        self.cooldown_period = 300  # 5 minutes
        
        # Setup message handlers
        self._setup_message_handlers()

    async def _setup_message_handlers(self) -> None:
        """Setup handlers for alert-related messages"""
        handlers = {
            MessageType.MONITORING_ALERT_RULE_CREATE: self._handle_alert_rule_create,
            MessageType.MONITORING_ALERT_RULE_UPDATE: self._handle_alert_rule_update,
            MessageType.MONITORING_ALERT_RULE_DELETE: self._handle_alert_rule_delete,
            MessageType.MONITORING_ALERT_NOTIFICATION_CREATE: self._handle_notification_create,
            MessageType.MONITORING_ALERT_NOTIFICATION_UPDATE: self._handle_notification_update,
            MessageType.MONITORING_ALERT_NOTIFICATION_DELETE: self._handle_notification_delete,
            MessageType.MONITORING_METRICS_UPDATE: self._handle_metrics_update,
            MessageType.MONITORING_HEALTH_RESULT: self._handle_health_result,
            MessageType.MONITORING_ANOMALY_DETECTED: self._handle_anomaly_detected
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_alert_rule_create(self, message: ProcessingMessage) -> None:
        """Handle alert rule creation request"""
        try:
            rule_data = message.content.get('rule')
            if not rule_data:
                raise ValueError("Alert rule data is required")

            # Create alert rule
            rule = AlertRule(**rule_data)
            self.alert_rules[rule.rule_id] = rule

            # Publish rule creation notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_RULE_CREATED,
                    content={'rule_id': rule.rule_id},
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to create alert rule: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_alert_rule_update(self, message: ProcessingMessage) -> None:
        """Handle alert rule update request"""
        try:
            rule_id = message.content.get('rule_id')
            rule_data = message.content.get('rule')
            if not rule_id or not rule_data:
                raise ValueError("Rule ID and rule data are required")

            if rule_id not in self.alert_rules:
                raise ValueError(f"Alert rule {rule_id} not found")

            # Update alert rule
            self.alert_rules[rule_id] = AlertRule(**rule_data)

            # Publish rule update notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_RULE_UPDATED,
                    content={'rule_id': rule_id},
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to update alert rule: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_alert_rule_delete(self, message: ProcessingMessage) -> None:
        """Handle alert rule deletion request"""
        try:
            rule_id = message.content.get('rule_id')
            if not rule_id:
                raise ValueError("Rule ID is required")

            if rule_id not in self.alert_rules:
                raise ValueError(f"Alert rule {rule_id} not found")

            # Delete alert rule
            del self.alert_rules[rule_id]

            # Publish rule deletion notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_RULE_DELETED,
                    content={'rule_id': rule_id},
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to delete alert rule: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_notification_create(self, message: ProcessingMessage) -> None:
        """Handle notification channel creation request"""
        try:
            channel_data = message.content.get('channel')
            if not channel_data:
                raise ValueError("Notification channel data is required")

            channel_id = channel_data.get('channel_id')
            if not channel_id:
                raise ValueError("Channel ID is required")

            # Create notification channel
            self.notification_channels[channel_id] = channel_data

            # Publish channel creation notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_NOTIFICATION_CREATED,
                    content={'channel_id': channel_id},
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to create notification channel: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_notification_update(self, message: ProcessingMessage) -> None:
        """Handle notification channel update request"""
        try:
            channel_id = message.content.get('channel_id')
            channel_data = message.content.get('channel')
            if not channel_id or not channel_data:
                raise ValueError("Channel ID and channel data are required")

            if channel_id not in self.notification_channels:
                raise ValueError(f"Notification channel {channel_id} not found")

            # Update notification channel
            self.notification_channels[channel_id] = channel_data

            # Publish channel update notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_NOTIFICATION_UPDATED,
                    content={'channel_id': channel_id},
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to update notification channel: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_notification_delete(self, message: ProcessingMessage) -> None:
        """Handle notification channel deletion request"""
        try:
            channel_id = message.content.get('channel_id')
            if not channel_id:
                raise ValueError("Channel ID is required")

            if channel_id not in self.notification_channels:
                raise ValueError(f"Notification channel {channel_id} not found")

            # Delete notification channel
            del self.notification_channels[channel_id]

            # Publish channel deletion notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_NOTIFICATION_DELETED,
                    content={'channel_id': channel_id},
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to delete notification channel: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_metrics_update(self, message: ProcessingMessage) -> None:
        """Handle metrics update and evaluate alert rules"""
        try:
            metrics = message.content.get('metrics')
            if not metrics:
                return

            # Evaluate metric-based alert rules
            for rule in self.alert_rules.values():
                if rule.rule_type == AlertRuleType.METRIC_THRESHOLD:
                    await self._evaluate_metric_rule(rule, metrics)

        except Exception as e:
            logger.error(f"Failed to handle metrics update: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_health_result(self, message: ProcessingMessage) -> None:
        """Handle health check results and evaluate status-based alert rules"""
        try:
            health_result = message.content.get('result')
            if not health_result:
                return

            # Evaluate status-based alert rules
            for rule in self.alert_rules.values():
                if rule.rule_type == AlertRuleType.STATUS_CHANGE:
                    await self._evaluate_status_rule(rule, health_result)

        except Exception as e:
            logger.error(f"Failed to handle health result: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_anomaly_detected(self, message: ProcessingMessage) -> None:
        """Handle anomaly detection results and evaluate anomaly-based alert rules"""
        try:
            anomaly_data = message.content.get('anomaly')
            if not anomaly_data:
                return

            # Evaluate anomaly-based alert rules
            for rule in self.alert_rules.values():
                if rule.rule_type == AlertRuleType.ANOMALY_DETECTION:
                    await self._evaluate_anomaly_rule(rule, anomaly_data)

        except Exception as e:
            logger.error(f"Failed to handle anomaly detection: {str(e)}")
            await self._handle_error(message, str(e))

    async def _evaluate_metric_rule(self, rule: AlertRule, metrics: Dict[str, Any]) -> None:
        """Evaluate metric-based alert rule"""
        try:
            metric_name = rule.condition.metric_name
            if metric_name not in metrics:
                return

            metric_value = metrics[metric_name]
            if self._check_condition(rule.condition, metric_value):
                await self._generate_alert(rule, metric_value)

        except Exception as e:
            logger.error(f"Failed to evaluate metric rule: {str(e)}")

    async def _evaluate_status_rule(self, rule: AlertRule, health_result: Dict[str, Any]) -> None:
        """Evaluate status-based alert rule"""
        try:
            component_id = rule.condition.component_id
            if component_id not in health_result.get('components', {}):
                return

            component_status = health_result['components'][component_id]['status']
            if self._check_condition(rule.condition, component_status):
                await self._generate_alert(rule, component_status)

        except Exception as e:
            logger.error(f"Failed to evaluate status rule: {str(e)}")

    async def _evaluate_anomaly_rule(self, rule: AlertRule, anomaly_data: Dict[str, Any]) -> None:
        """Evaluate anomaly-based alert rule"""
        try:
            metric_name = rule.condition.metric_name
            if metric_name not in anomaly_data:
                return

            anomaly_value = anomaly_data[metric_name]
            if self._check_condition(rule.condition, anomaly_value):
                await self._generate_alert(rule, anomaly_value)

        except Exception as e:
            logger.error(f"Failed to evaluate anomaly rule: {str(e)}")

    def _check_condition(self, condition: AlertCondition, value: Any) -> bool:
        """Check if a condition is met"""
        try:
            if condition.operator == '>':
                return value > condition.threshold
            elif condition.operator == '<':
                return value < condition.threshold
            elif condition.operator == '>=':
                return value >= condition.threshold
            elif condition.operator == '<=':
                return value <= condition.threshold
            elif condition.operator == '==':
                return value == condition.threshold
            elif condition.operator == '!=':
                return value != condition.threshold
            else:
                return False

        except Exception as e:
            logger.error(f"Failed to check condition: {str(e)}")
            return False

    async def _generate_alert(self, rule: AlertRule, value: Any) -> None:
        """Generate and send alert"""
        try:
            # Check alert cooldown
            if rule.rule_id in self.alert_cooldown:
                if datetime.now() - self.alert_cooldown[rule.rule_id] < timedelta(seconds=self.cooldown_period):
                    return

            # Create alert notification
            notification = AlertNotification(
                alert_id=str(uuid.uuid4()),
                rule_id=rule.rule_id,
                severity=rule.severity,
                message=rule.message,
                timestamp=datetime.now(),
                value=value,
                details=rule.details
            )

            # Send notifications to all configured channels
            for channel_id in rule.notification_channels:
                if channel_id in self.notification_channels:
                    await self._send_notification(channel_id, notification)

            # Update alert cooldown
            self.alert_cooldown[rule.rule_id] = datetime.now()

            # Add to alert history
            self.alert_history.append(AlertHistory(
                alert_id=notification.alert_id,
                rule_id=rule.rule_id,
                severity=rule.severity,
                message=rule.message,
                timestamp=notification.timestamp,
                value=value,
                details=rule.details
            ))

            # Clean up old alerts
            self._cleanup_old_alerts()

            # Publish alert notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_GENERATED,
                    content={'notification': notification.dict()},
                    metadata=MessageMetadata(
                        correlation_id=str(uuid.uuid4()),
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to generate alert: {str(e)}")

    async def _send_notification(self, channel_id: str, notification: AlertNotification) -> None:
        """Send notification through specified channel"""
        try:
            channel = self.notification_channels[channel_id]
            channel_type = channel.get('type')

            if channel_type == 'email':
                await self._send_email_notification(channel, notification)
            elif channel_type == 'slack':
                await self._send_slack_notification(channel, notification)
            elif channel_type == 'webhook':
                await self._send_webhook_notification(channel, notification)
            else:
                logger.warning(f"Unsupported notification channel type: {channel_type}")

        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")

    async def _send_email_notification(self, channel: Dict[str, Any], notification: AlertNotification) -> None:
        """Send email notification"""
        # Implement email notification logic
        pass

    async def _send_slack_notification(self, channel: Dict[str, Any], notification: AlertNotification) -> None:
        """Send Slack notification"""
        # Implement Slack notification logic
        pass

    async def _send_webhook_notification(self, channel: Dict[str, Any], notification: AlertNotification) -> None:
        """Send webhook notification"""
        # Implement webhook notification logic
        pass

    def _cleanup_old_alerts(self) -> None:
        """Remove old alerts from history"""
        cutoff_time = datetime.now() - timedelta(days=30)
        self.alert_history = [
            alert for alert in self.alert_history
            if alert.timestamp > cutoff_time
        ] 