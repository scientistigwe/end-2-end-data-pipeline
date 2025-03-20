import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from ..base.base_service import BaseService
from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    DashboardData,
    DashboardConfig,
    DashboardLayout,
    DashboardWidget,
    DashboardUpdate
)

logger = logging.getLogger(__name__)

class DashboardService(BaseService):
    """
    Service for managing the monitoring dashboard.
    Handles dashboard configuration, data aggregation, and real-time updates.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker)
        
        # Service identifier
        self.module_identifier = ModuleIdentifier(
            component_name="dashboard_service",
            component_type=ComponentType.MONITORING_SERVICE,
            department="monitoring",
            role="dashboard"
        )

        # Dashboard configuration
        self.dashboard_configs: Dict[str, DashboardConfig] = {}
        self.dashboard_layouts: Dict[str, DashboardLayout] = {}
        self.dashboard_data: Dict[str, Dict[str, Any]] = {}
        self.update_interval = 5  # seconds
        
        # Setup message handlers
        self._setup_message_handlers()

    async def _setup_message_handlers(self) -> None:
        """Setup handlers for dashboard-related messages"""
        handlers = {
            MessageType.MONITORING_DASHBOARD_CREATE: self._handle_dashboard_create,
            MessageType.MONITORING_DASHBOARD_UPDATE: self._handle_dashboard_update,
            MessageType.MONITORING_DASHBOARD_DELETE: self._handle_dashboard_delete,
            MessageType.MONITORING_DASHBOARD_LAYOUT_UPDATE: self._handle_layout_update,
            MessageType.MONITORING_DASHBOARD_WIDGET_ADD: self._handle_widget_add,
            MessageType.MONITORING_DASHBOARD_WIDGET_UPDATE: self._handle_widget_update,
            MessageType.MONITORING_DASHBOARD_WIDGET_DELETE: self._handle_widget_delete,
            MessageType.MONITORING_METRICS_UPDATE: self._handle_metrics_update,
            MessageType.MONITORING_HEALTH_RESULT: self._handle_health_result,
            MessageType.MONITORING_ALERT_GENERATED: self._handle_alert_generated
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_dashboard_create(self, message: ProcessingMessage) -> None:
        """Handle dashboard creation request"""
        try:
            dashboard_data = message.content.get('dashboard')
            if not dashboard_data:
                raise ValueError("Dashboard data is required")

            dashboard_id = dashboard_data.get('dashboard_id')
            if not dashboard_id:
                raise ValueError("Dashboard ID is required")

            # Create dashboard configuration
            config = DashboardConfig(**dashboard_data)
            self.dashboard_configs[dashboard_id] = config

            # Initialize dashboard data
            self.dashboard_data[dashboard_id] = {}

            # Create default layout
            layout = DashboardLayout(
                layout_id=f"{dashboard_id}_layout",
                dashboard_id=dashboard_id,
                widgets=[]
            )
            self.dashboard_layouts[dashboard_id] = layout

            # Publish dashboard creation notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_DASHBOARD_CREATED,
                    content={'dashboard_id': dashboard_id},
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to create dashboard: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_dashboard_update(self, message: ProcessingMessage) -> None:
        """Handle dashboard update request"""
        try:
            dashboard_id = message.content.get('dashboard_id')
            dashboard_data = message.content.get('dashboard')
            if not dashboard_id or not dashboard_data:
                raise ValueError("Dashboard ID and data are required")

            if dashboard_id not in self.dashboard_configs:
                raise ValueError(f"Dashboard {dashboard_id} not found")

            # Update dashboard configuration
            self.dashboard_configs[dashboard_id] = DashboardConfig(**dashboard_data)

            # Publish dashboard update notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_DASHBOARD_UPDATED,
                    content={'dashboard_id': dashboard_id},
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to update dashboard: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_dashboard_delete(self, message: ProcessingMessage) -> None:
        """Handle dashboard deletion request"""
        try:
            dashboard_id = message.content.get('dashboard_id')
            if not dashboard_id:
                raise ValueError("Dashboard ID is required")

            if dashboard_id not in self.dashboard_configs:
                raise ValueError(f"Dashboard {dashboard_id} not found")

            # Delete dashboard configuration and data
            del self.dashboard_configs[dashboard_id]
            del self.dashboard_layouts[dashboard_id]
            del self.dashboard_data[dashboard_id]

            # Publish dashboard deletion notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_DASHBOARD_DELETED,
                    content={'dashboard_id': dashboard_id},
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to delete dashboard: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_layout_update(self, message: ProcessingMessage) -> None:
        """Handle dashboard layout update request"""
        try:
            dashboard_id = message.content.get('dashboard_id')
            layout_data = message.content.get('layout')
            if not dashboard_id or not layout_data:
                raise ValueError("Dashboard ID and layout data are required")

            if dashboard_id not in self.dashboard_layouts:
                raise ValueError(f"Dashboard {dashboard_id} not found")

            # Update dashboard layout
            self.dashboard_layouts[dashboard_id] = DashboardLayout(**layout_data)

            # Publish layout update notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_DASHBOARD_LAYOUT_UPDATED,
                    content={'dashboard_id': dashboard_id},
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to update dashboard layout: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_widget_add(self, message: ProcessingMessage) -> None:
        """Handle widget addition request"""
        try:
            dashboard_id = message.content.get('dashboard_id')
            widget_data = message.content.get('widget')
            if not dashboard_id or not widget_data:
                raise ValueError("Dashboard ID and widget data are required")

            if dashboard_id not in self.dashboard_layouts:
                raise ValueError(f"Dashboard {dashboard_id} not found")

            # Add widget to layout
            widget = DashboardWidget(**widget_data)
            self.dashboard_layouts[dashboard_id].widgets.append(widget)

            # Initialize widget data
            if dashboard_id not in self.dashboard_data:
                self.dashboard_data[dashboard_id] = {}
            self.dashboard_data[dashboard_id][widget.widget_id] = {}

            # Publish widget addition notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_DASHBOARD_WIDGET_ADDED,
                    content={
                        'dashboard_id': dashboard_id,
                        'widget_id': widget.widget_id
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to add widget: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_widget_update(self, message: ProcessingMessage) -> None:
        """Handle widget update request"""
        try:
            dashboard_id = message.content.get('dashboard_id')
            widget_id = message.content.get('widget_id')
            widget_data = message.content.get('widget')
            if not dashboard_id or not widget_id or not widget_data:
                raise ValueError("Dashboard ID, widget ID, and widget data are required")

            if dashboard_id not in self.dashboard_layouts:
                raise ValueError(f"Dashboard {dashboard_id} not found")

            # Update widget in layout
            layout = self.dashboard_layouts[dashboard_id]
            widget_index = next(
                (i for i, w in enumerate(layout.widgets) if w.widget_id == widget_id),
                -1
            )
            if widget_index == -1:
                raise ValueError(f"Widget {widget_id} not found")

            layout.widgets[widget_index] = DashboardWidget(**widget_data)

            # Publish widget update notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_DASHBOARD_WIDGET_UPDATED,
                    content={
                        'dashboard_id': dashboard_id,
                        'widget_id': widget_id
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to update widget: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_widget_delete(self, message: ProcessingMessage) -> None:
        """Handle widget deletion request"""
        try:
            dashboard_id = message.content.get('dashboard_id')
            widget_id = message.content.get('widget_id')
            if not dashboard_id or not widget_id:
                raise ValueError("Dashboard ID and widget ID are required")

            if dashboard_id not in self.dashboard_layouts:
                raise ValueError(f"Dashboard {dashboard_id} not found")

            # Remove widget from layout
            layout = self.dashboard_layouts[dashboard_id]
            layout.widgets = [w for w in layout.widgets if w.widget_id != widget_id]

            # Remove widget data
            if dashboard_id in self.dashboard_data and widget_id in self.dashboard_data[dashboard_id]:
                del self.dashboard_data[dashboard_id][widget_id]

            # Publish widget deletion notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_DASHBOARD_WIDGET_DELETED,
                    content={
                        'dashboard_id': dashboard_id,
                        'widget_id': widget_id
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to delete widget: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_metrics_update(self, message: ProcessingMessage) -> None:
        """Handle metrics update and update relevant widgets"""
        try:
            metrics = message.content.get('metrics')
            if not metrics:
                return

            # Update dashboard data for metric widgets
            for dashboard_id, layout in self.dashboard_layouts.items():
                for widget in layout.widgets:
                    if widget.type == 'metric':
                        await self._update_metric_widget(dashboard_id, widget, metrics)

        except Exception as e:
            logger.error(f"Failed to handle metrics update: {str(e)}")

    async def _handle_health_result(self, message: ProcessingMessage) -> None:
        """Handle health check results and update relevant widgets"""
        try:
            health_result = message.content.get('result')
            if not health_result:
                return

            # Update dashboard data for health widgets
            for dashboard_id, layout in self.dashboard_layouts.items():
                for widget in layout.widgets:
                    if widget.type == 'health':
                        await self._update_health_widget(dashboard_id, widget, health_result)

        except Exception as e:
            logger.error(f"Failed to handle health result: {str(e)}")

    async def _handle_alert_generated(self, message: ProcessingMessage) -> None:
        """Handle alert generation and update relevant widgets"""
        try:
            alert = message.content.get('notification')
            if not alert:
                return

            # Update dashboard data for alert widgets
            for dashboard_id, layout in self.dashboard_layouts.items():
                for widget in layout.widgets:
                    if widget.type == 'alert':
                        await self._update_alert_widget(dashboard_id, widget, alert)

        except Exception as e:
            logger.error(f"Failed to handle alert generation: {str(e)}")

    async def _update_metric_widget(self, dashboard_id: str, widget: DashboardWidget, metrics: Dict[str, Any]) -> None:
        """Update metric widget data"""
        try:
            metric_name = widget.config.get('metric_name')
            if metric_name not in metrics:
                return

            # Update widget data
            self.dashboard_data[dashboard_id][widget.widget_id] = {
                'value': metrics[metric_name],
                'timestamp': datetime.now().isoformat()
            }

            # Publish widget update
            await self._publish_widget_update(dashboard_id, widget)

        except Exception as e:
            logger.error(f"Failed to update metric widget: {str(e)}")

    async def _update_health_widget(self, dashboard_id: str, widget: DashboardWidget, health_result: Dict[str, Any]) -> None:
        """Update health widget data"""
        try:
            component_id = widget.config.get('component_id')
            if not component_id or 'components' not in health_result:
                return

            component_status = health_result['components'].get(component_id, {})
            if not component_status:
                return

            # Update widget data
            self.dashboard_data[dashboard_id][widget.widget_id] = {
                'status': component_status.get('status'),
                'details': component_status.get('details', {}),
                'timestamp': datetime.now().isoformat()
            }

            # Publish widget update
            await self._publish_widget_update(dashboard_id, widget)

        except Exception as e:
            logger.error(f"Failed to update health widget: {str(e)}")

    async def _update_alert_widget(self, dashboard_id: str, widget: DashboardWidget, alert: Dict[str, Any]) -> None:
        """Update alert widget data"""
        try:
            # Get current alerts
            current_alerts = self.dashboard_data[dashboard_id][widget.widget_id].get('alerts', [])
            
            # Add new alert
            current_alerts.append({
                'id': alert.get('alert_id'),
                'severity': alert.get('severity'),
                'message': alert.get('message'),
                'timestamp': datetime.now().isoformat()
            })

            # Keep only recent alerts
            max_alerts = widget.config.get('max_alerts', 100)
            current_alerts = current_alerts[-max_alerts:]

            # Update widget data
            self.dashboard_data[dashboard_id][widget.widget_id] = {
                'alerts': current_alerts,
                'timestamp': datetime.now().isoformat()
            }

            # Publish widget update
            await self._publish_widget_update(dashboard_id, widget)

        except Exception as e:
            logger.error(f"Failed to update alert widget: {str(e)}")

    async def _publish_widget_update(self, dashboard_id: str, widget: DashboardWidget) -> None:
        """Publish widget update notification"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_DASHBOARD_WIDGET_UPDATED,
                    content={
                        'dashboard_id': dashboard_id,
                        'widget_id': widget.widget_id,
                        'data': self.dashboard_data[dashboard_id][widget.widget_id]
                    },
                    metadata=MessageMetadata(
                        correlation_id=str(uuid.uuid4()),
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to publish widget update: {str(e)}") 