import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import asyncio
from datetime import timedelta

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    MonitoringContext,
    MonitoringState,
    ManagerState,
    ComponentType,
    ModuleIdentifier
)
from .base.base_manager import BaseManager

logger = logging.getLogger(__name__)

class MonitoringManager(BaseManager):
    """
    Monitoring Manager that coordinates monitoring workflow through message broker.
    Maintains state and manages transitions through message-based communication.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(
            message_broker=message_broker,
            component_name="monitoring_manager",
            domain_type="monitoring"
        )

        self.module_identifier = ModuleIdentifier(
            component_name="monitoring_manager",
            component_type=ComponentType.MONITORING_MANAGER,
            department="monitoring",
            role="manager"
        )

        # State management
        self.active_processes: Dict[str, MonitoringContext] = {}
        self.state = ManagerState.INITIALIZING

        # Initialize manager
        self._initialize_manager()

    def _initialize_manager(self) -> None:
        """Initialize manager components"""
        self._setup_message_handlers()
        self._start_monitoring_tasks()
        self.state = ManagerState.ACTIVE

    def _setup_message_handlers(self) -> None:
        """Setup subscriptions for all monitoring-related messages"""
        handlers = {
            # Service Layer Responses
            MessageType.MONITORING_SERVICE_COMPLETE: self._handle_service_complete,
            MessageType.MONITORING_SERVICE_ERROR: self._handle_service_error,
            MessageType.MONITORING_SERVICE_STATUS: self._handle_service_status,

            # Monitoring Flow Messages
            MessageType.MONITORING_METRICS_READY: self._handle_metrics_ready,
            MessageType.MONITORING_HEALTH_STATUS: self._handle_health_status,
            MessageType.MONITORING_ALERT_NOTIFY: self._handle_alert_notification,
            MessageType.MONITORING_THRESHOLD_BREACH: self._handle_threshold_breach,

            # Control Point Messages
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.CONTROL_POINT_UPDATED: self._handle_control_point_updated,
            MessageType.CONTROL_POINT_DECISION_SUBMIT: self._handle_control_point_decision,

            # Resource Messages
            MessageType.RESOURCE_ALLOCATED: self._handle_resource_allocated,
            MessageType.RESOURCE_RELEASED: self._handle_resource_released,

            # System Messages
            MessageType.MONITORING_HEALTH_CHECK: self._handle_health_check,
            MessageType.MONITORING_CONFIG_UPDATE: self._handle_config_update
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def request_monitoring(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> str:
        """Initiate monitoring process through service layer"""
        correlation_id = str(uuid.uuid4())

        try:
            # Create monitoring context
            context = MonitoringContext(
                pipeline_id=pipeline_id,
                correlation_id=correlation_id,
                monitor_state=MonitoringState.INITIALIZING,
                metric_types=config.get('metric_types', []),
                collectors_enabled=config.get('collectors', []),
                collection_interval=config.get('interval', 60)
            )

            self.active_processes[pipeline_id] = context

            # Request through service layer
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_SERVICE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': config
                    },
                    metadata=MessageMetadata(
                        correlation_id=correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_service",
                        domain_type="monitoring",
                        processing_stage=ProcessingStage.MONITORING
                    ),
                    source_identifier=self.module_identifier
                )
            )

            logger.info(f"Monitoring request initiated for pipeline: {pipeline_id}")
            return correlation_id

        except Exception as e:
            logger.error(f"Failed to initiate monitoring request: {str(e)}")
            raise

    async def _handle_metrics_ready(self, message: ProcessingMessage) -> None:
        """Handle metrics data availability"""
        pipeline_id = message.content["pipeline_id"]
        metrics = message.content.get("metrics", {})
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            context.update_metrics(metrics)

            # Check thresholds
            await self._check_thresholds(pipeline_id, metrics)

        except Exception as e:
            logger.error(f"Metrics handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_health_status(self, message: ProcessingMessage) -> None:
        """Handle health status update"""
        pipeline_id = message.content["pipeline_id"]
        health_status = message.content.get("health_status", {})
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            context.update_health_check(health_status)

            if health_status.get("status") != "healthy":
                await self._handle_health_issue(pipeline_id, health_status)

        except Exception as e:
            logger.error(f"Health status handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_alert_notification(self, message: ProcessingMessage) -> None:
        """Handle monitoring alert notification"""
        pipeline_id = message.content["pipeline_id"]
        alert = message.content.get("alert", {})
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            context.add_alert(alert)

            if alert.get("severity") in ["critical", "high"]:
                await self._handle_critical_alert(pipeline_id, alert)

        except Exception as e:
            logger.error(f"Alert handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_service_complete(self, message: ProcessingMessage) -> None:
        """Handle completion message from service layer"""
        pipeline_id = message.content["pipeline_id"]
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context
            context.monitor_state = MonitoringState.COMPLETED
            context.completed_at = datetime.now()
            context.metrics = message.content.get("metrics", {})

            # Notify completion
            await self._notify_completion(pipeline_id, context.metrics)

            # Cleanup
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Service completion handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_error(self, pipeline_id: str, error: str) -> None:
        """Handle errors in monitoring process"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            context.monitor_state = MonitoringState.FAILED
            context.error = error

            # Notify error
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'state': context.monitor_state.value
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="control_point_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def _notify_completion(self, pipeline_id: str, metrics: Dict[str, Any]) -> None:
        """Notify monitoring completion"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.MONITORING_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'metrics': metrics,
                    'completion_time': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _cleanup_process(self, pipeline_id: str) -> None:
        """Clean up process resources"""
        if pipeline_id in self.active_processes:
            del self.active_processes[pipeline_id]

    async def cleanup(self) -> None:
        """Clean up manager resources"""
        self.state = ManagerState.SHUTDOWN

        try:
            # Clean up all active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self._cleanup_process(pipeline_id)

            # Unsubscribe from all messages
            await self.message_broker.unsubscribe_all(self.module_identifier)

        except Exception as e:
            logger.error(f"Manager cleanup failed: {str(e)}")
            raise

    async def _handle_service_error(self, message: ProcessingMessage) -> None:
        """
        Handle error message from service layer

        Args:
            message (ProcessingMessage): Error message from service
        """
        pipeline_id = message.content.get("pipeline_id")
        error = message.content.get("error", "Unknown service error")

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update context
            context.monitor_state = MonitoringState.FAILED
            context.error = error

            # Publish error
            await self._handle_error(pipeline_id, error)

        except Exception as e:
            logger.error(f"Service error handling failed: {str(e)}")


    async def _handle_service_status(self, message: ProcessingMessage) -> None:
        """
        Handle status update from service layer

        Args:
            message (ProcessingMessage): Status update message
        """
        pipeline_id = message.content.get("pipeline_id")
        status = message.content.get("status")
        progress = message.content.get("progress", 0.0)

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update context
            context.status = status
            context.progress = progress

            # Publish status update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_STATUS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': status,
                        'progress': progress,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="control_point_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Service status handling failed: {str(e)}")


    async def _handle_threshold_breach(self, message: ProcessingMessage) -> None:
        """
        Handle monitoring threshold breaches

        Args:
            message (ProcessingMessage): Threshold breach message
        """
        pipeline_id = message.content.get("pipeline_id")
        breach_details = message.content.get("breach", {})

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Log threshold breach
            context.add_threshold_breach(breach_details)

            # Publish threshold breach notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT,
                    content={
                        'pipeline_id': pipeline_id,
                        'breach': breach_details,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="control_point_manager"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Potentially trigger corrective action
            await self._trigger_corrective_action(pipeline_id, breach_details)

        except Exception as e:
            logger.error(f"Threshold breach handling failed: {str(e)}")


    async def _trigger_corrective_action(self, pipeline_id: str, breach_details: Dict[str, Any]) -> None:
        """
        Trigger corrective actions for threshold breaches

        Args:
            pipeline_id (str): Pipeline identifier
            breach_details (Dict[str, Any]): Details of the threshold breach
        """
        try:
            # Determine corrective action based on breach type
            corrective_actions = {
                'cpu_usage': self._handle_cpu_breach,
                'memory_usage': self._handle_memory_breach,
                'network_latency': self._handle_network_breach,
                # Add more specific handlers as needed
            }

            breach_type = breach_details.get('type')
            action_handler = corrective_actions.get(breach_type)

            if action_handler:
                await action_handler(pipeline_id, breach_details)
            else:
                logger.warning(f"No corrective action defined for breach type: {breach_type}")

        except Exception as e:
            logger.error(f"Corrective action triggering failed: {str(e)}")


    async def _handle_cpu_breach(self, pipeline_id: str, breach_details: Dict[str, Any]) -> None:
        """
        Handle CPU usage threshold breach

        Args:
            pipeline_id (str): Pipeline identifier
            breach_details (Dict[str, Any]): CPU breach details
        """
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.SYSTEM_RESOURCE_ADJUSTMENT,
                content={
                    'pipeline_id': pipeline_id,
                    'resource_type': 'cpu',
                    'action': 'scale_down',
                    'current_usage': breach_details.get('current_usage'),
                    'timestamp': datetime.now().isoformat()
                },
                source_identifier=self.module_identifier
            )
        )


    async def _handle_memory_breach(self, pipeline_id: str, breach_details: Dict[str, Any]) -> None:
        """
        Handle memory usage threshold breach

        Args:
            pipeline_id (str): Pipeline identifier
            breach_details (Dict[str, Any]): Memory breach details
        """
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.SYSTEM_RESOURCE_ADJUSTMENT,
                content={
                    'pipeline_id': pipeline_id,
                    'resource_type': 'memory',
                    'action': 'release_cache',
                    'current_usage': breach_details.get('current_usage'),
                    'timestamp': datetime.now().isoformat()
                },
                source_identifier=self.module_identifier
            )
        )


    async def _handle_network_breach(self, pipeline_id: str, breach_details: Dict[str, Any]) -> None:
        """
        Handle network latency threshold breach

        Args:
            pipeline_id (str): Pipeline identifier
            breach_details (Dict[str, Any]): Network breach details
        """
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.SYSTEM_NETWORK_ADJUSTMENT,
                content={
                    'pipeline_id': pipeline_id,
                    'action': 'switch_route',
                    'current_latency': breach_details.get('current_latency'),
                    'timestamp': datetime.now().isoformat()
                },
                source_identifier=self.module_identifier
            )
        )


    async def _check_thresholds(self, pipeline_id: str, metrics: Dict[str, Any]) -> None:
        """
        Check metrics against predefined thresholds

        Args:
            pipeline_id (str): Pipeline identifier
            metrics (Dict[str, Any]): Collected metrics
        """
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Define threshold configuration
            thresholds = {
                'cpu_usage': 90,  # 90% CPU usage
                'memory_usage': 85,  # 85% memory usage
                'network_latency': 200  # 200ms latency
            }

            # Check each metric against thresholds
            for metric, threshold in thresholds.items():
                if metric in metrics and metrics[metric] > threshold:
                    await self._handle_threshold_breach(
                        ProcessingMessage(
                            message_type=MessageType.MONITORING_THRESHOLD_BREACH,
                            content={
                                'pipeline_id': pipeline_id,
                                'breach': {
                                    'type': metric,
                                    'current_usage': metrics[metric],
                                    'threshold': threshold
                                }
                            }
                        )
                    )

        except Exception as e:
            logger.error(f"Threshold checking failed: {str(e)}")


    async def _handle_critical_alert(self, pipeline_id: str, alert: Dict[str, Any]) -> None:
        """
        Handle critical monitoring alerts

        Args:
            pipeline_id (str): Pipeline identifier
            alert (Dict[str, Any]): Alert details
        """
        try:
            # Publish high-priority alert
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.CRITICAL_MONITORING_ALERT,
                    content={
                        'pipeline_id': pipeline_id,
                        'alert': alert,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="incident_response_system"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Log critical alert
            logger.critical(f"Critical alert for pipeline {pipeline_id}: {alert}")

        except Exception as e:
            logger.error(f"Critical alert handling failed: {str(e)}")


    def _start_monitoring_tasks(self) -> None:
        """
        Start background monitoring tasks
        """
        import asyncio

        # Periodic health checks
        asyncio.create_task(self._periodic_health_checks())

        # Long-running process monitoring
        asyncio.create_task(self._monitor_long_running_processes())


    async def _periodic_health_checks(self) -> None:
        """
        Perform periodic system health checks
        """
        while self.state == ManagerState.ACTIVE:
            try:
                # Collect system health metrics
                system_health = await self._collect_system_health_metrics()

                # Check overall system health
                if not system_health.get('is_healthy', True):
                    await self._handle_system_health_issue(system_health)

                # Wait before next check
                await asyncio.sleep(600)  # Check every 10 minutes

            except Exception as e:
                logger.error(f"Periodic health check failed: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry


    async def _collect_system_health_metrics(self) -> Dict[str, Any]:
        """
        Collect comprehensive system health metrics

        Returns:
            Dict[str, Any]: System health metrics
        """
        try:
            import psutil

            return {
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_connections': len(psutil.net_connections()),
                'is_healthy': all([
                    psutil.cpu_percent() < 90,
                    psutil.virtual_memory().percent < 85,
                    psutil.disk_usage('/').percent < 90
                ])
            }
        except Exception as e:
            logger.error(f"System metrics collection failed: {str(e)}")
            return {'is_healthy': False, 'error': str(e)}


    async def _monitor_long_running_processes(self) -> None:
        """
        Monitor and handle long-running monitoring processes
        """
        while self.state == ManagerState.ACTIVE:
            try:
                current_time = datetime.now()
                timeout_threshold = current_time - timedelta(hours=4)  # 4-hour timeout

                # Check for and handle timed-out processes
                for pipeline_id, context in list(self.active_processes.items()):
                    if context.created_at < timeout_threshold:
                        await self._handle_error(
                            pipeline_id,
                            "Monitoring process exceeded maximum time limit"
                        )

                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                logger.error(f"Long-running process monitoring failed: {str(e)}")