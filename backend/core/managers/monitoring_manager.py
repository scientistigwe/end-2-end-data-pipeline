import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MonitoringContext,
    MessageMetadata
)
from ..control.cpm import ControlPointManager
from .base.base_manager import BaseManager
from ..staging.staging_manager import StagingManager
from core.handlers.channel.monitoring_handler import MonitoringHandler
from data.processing.monitoring.types import (
    MonitoringSource,
    MonitoringState,
    MonitoringPhase,
    MonitoringStatus,
    ComponentMetrics
)
from db.models.staging.monitoring_output_model import StagedMonitoringOutput

logger = logging.getLogger(__name__)


class MonitoringManager(BaseManager):
    """
    Comprehensive System Monitoring Management

    Orchestrates monitoring workflows, coordinates metrics collection,
    and manages system health tracking across pipeline components.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            control_point_manager: ControlPointManager,
            staging_manager: StagingManager
    ):
        super().__init__(
            message_broker=message_broker,
            control_point_manager=control_point_manager,
            component_name="monitoring_manager",
            domain_type="monitoring"
        )

        self.staging_manager = staging_manager
        self.monitoring_handler = MonitoringHandler(
            message_broker=message_broker,
            staging_manager=staging_manager
        )

        # Active monitoring tracking
        self.active_monitoring_tasks: Dict[str, MonitoringState] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup handlers for monitoring-related messages"""
        self.register_message_handler(
            MessageType.METRICS_COLLECTION_REQUEST,
            self._handle_metrics_request
        )
        self.register_message_handler(
            MessageType.METRICS_SUBMIT,
            self._handle_metrics_submit
        )
        self.register_message_handler(
            MessageType.METRICS_UPDATE,
            self._handle_metrics_update
        )
        self.register_message_handler(
            MessageType.METRICS_COLLECTION_COMPLETE,
            self._handle_metrics_collection_complete
        )
        self.register_message_handler(
            MessageType.SYSTEM_ALERT,
            self._handle_system_alert
        )

    async def _handle_metrics_request(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle metrics collection request"""
        try:
            pipeline_id = message.content['pipeline_id']
            source = message.metadata.source_component

            # Create monitoring context
            context = MonitoringContext(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.MONITORING,
                status=ProcessingStatus.PENDING,
                source_component=source,
                metrics_types=message.content.get('metrics_types', []),
                collectors=message.content.get('collectors', []),
                thresholds=message.content.get('thresholds', {})
            )

            # Create control point
            await self.control_point_manager.create_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.MONITORING,
                metadata={
                    'source': source,
                    'context': self._format_context(context)
                }
            )

            # Initialize monitoring state
            self.active_monitoring_tasks[pipeline_id] = MonitoringState(
                pipeline_id=pipeline_id,
                current_metrics=[],
                pending_metrics=[],
                completed_metrics=[],
                status=MonitoringStatus.COLLECTING,
                phase=MonitoringPhase.INITIAL
            )

            # Forward to handler
            await self.monitoring_handler._handle_metrics_request(message)

        except Exception as e:
            logger.error(f"Failed to handle metrics request: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_metrics_submit(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle metrics submission"""
        try:
            pipeline_id = message.content['pipeline_id']
            metrics_data = message.content['metrics']

            state = self.active_monitoring_tasks.get(pipeline_id)
            if not state:
                raise ValueError(f"No active monitoring task for pipeline: {pipeline_id}")

            # Update control point
            await self.control_point_manager.update_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.MONITORING,
                status=ProcessingStatus.IN_PROGRESS,
                metadata={
                    'metrics': metrics_data,
                    'submitted_at': datetime.now().isoformat()
                }
            )

            # Create staged monitoring output
            staged_output = StagedMonitoringOutput(
                reference_id=str(uuid.uuid4()),
                pipeline_id=pipeline_id,
                data=metrics_data,
                metadata={
                    'source': message.metadata.source_component,
                    'submitted_at': datetime.now().isoformat()
                }
            )

            # Forward to handler
            await self.monitoring_handler._handle_metrics_submit(message)

        except Exception as e:
            logger.error(f"Failed to handle metrics submission: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_metrics_update(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle metrics collection updates"""
        try:
            pipeline_id = message.content['pipeline_id']
            update_data = message.content['update']

            state = self.active_monitoring_tasks.get(pipeline_id)
            if state:
                # Update state based on update type
                if update_data.get('type') == 'progress':
                    state.status = MonitoringStatus.IN_PROGRESS
                elif update_data.get('type') == 'anomaly':
                    state.status = MonitoringStatus.ANOMALY_DETECTED

                state.metadata.update(update_data)
                state.updated_at = datetime.now()

            # Update control point
            await self.control_point_manager.update_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.MONITORING,
                metadata={
                    'update': update_data,
                    'updated_at': datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Failed to handle metrics update: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_metrics_collection_complete(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle metrics collection completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            result = message.content['result']

            state = self.active_monitoring_tasks.get(pipeline_id)
            if state:
                # Update state
                state.status = MonitoringStatus.COMPLETED
                state.completed_metrics.append(
                    ComponentMetrics(**result['metrics'])
                )

                # Cleanup
                del self.active_monitoring_tasks[pipeline_id]

            # Update control point
            await self.control_point_manager.update_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.MONITORING,
                status=ProcessingStatus.COMPLETED,
                metadata={
                    'result': result,
                    'completed_at': datetime.now().isoformat()
                }
            )

            # Notify completion
            await self._notify_completion(pipeline_id, result)

        except Exception as e:
            logger.error(f"Failed to handle metrics collection complete: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_system_alert(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle system-wide alerts"""
        try:
            pipeline_id = message.content.get('pipeline_id', str(uuid.uuid4()))
            alert_details = message.content['alert']

            # Create staged monitoring output for alert
            alert_output = StagedMonitoringOutput(
                reference_id=str(uuid.uuid4()),
                pipeline_id=pipeline_id,
                data={
                    'alert_type': alert_details.get('type'),
                    'severity': alert_details.get('severity'),
                    'details': alert_details
                },
                metadata={
                    'source': message.metadata.source_component,
                    'timestamp': datetime.now().isoformat()
                }
            )

            # Notify pipeline manager
            await self._notify_alert(pipeline_id, alert_details)

        except Exception as e:
            logger.error(f"Failed to handle system alert: {str(e)}")
            await self._handle_error(message, e)

    async def _notify_completion(
            self,
            pipeline_id: str,
            result: Dict[str, Any]
    ) -> None:
        """Notify about metrics collection completion"""
        message = ProcessingMessage(
            message_type=MessageType.METRICS_COLLECTION_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'result': result,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component="monitoring_manager",
                target_component="pipeline_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_alert(
            self,
            pipeline_id: str,
            alert_details: Dict[str, Any]
    ) -> None:
        """Notify about system alerts"""
        message = ProcessingMessage(
            message_type=MessageType.SYSTEM_ALERT,
            content={
                'pipeline_id': pipeline_id,
                'alert': alert_details,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component="monitoring_manager",
                target_component="pipeline_manager"
            )
        )
        await self.message_broker.publish(message)

    def _format_context(self, context: MonitoringContext) -> Dict[str, Any]:
        """Format context for storage"""
        return {
            'stage': context.stage.value,
            'status': context.status.value,
            'source_component': context.source_component,
            'metrics_types': context.metrics_types,
            'collectors': context.collectors,
            'thresholds': context.thresholds
        }

    async def get_monitoring_status(
            self,
            pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current status of monitoring process"""
        try:
            state = self.active_monitoring_tasks.get(pipeline_id)
            if not state:
                return None

            control_point = await self.control_point_manager.get_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.MONITORING
            )

            return {
                'pipeline_id': pipeline_id,
                'status': state.status.value,
                'phase': state.phase.value,
                'pending_metrics': len(state.pending_metrics),
                'completed_metrics': len(state.completed_metrics),
                'control_point': control_point,
                'updated_at': state.updated_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get monitoring status: {str(e)}")
            return None

    async def cleanup(self) -> None:
        """Cleanup manager resources"""
        try:
            # Cleanup active monitoring tasks
            self.active_monitoring_tasks.clear()

            # Cleanup handler
            await self.monitoring_handler.cleanup()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise

    @classmethod
    async def create(
            cls,
            message_broker: MessageBroker,
            control_point_manager: ControlPointManager,
            staging_manager: StagingManager
    ) -> 'MonitoringManager':
        """Factory method to create and initialize MonitoringManager"""
        manager = cls(
            message_broker=message_broker,
            control_point_manager=control_point_manager,
            staging_manager=staging_manager
        )

        # Initialize the manager
        await manager.initialize()
        return manager