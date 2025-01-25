import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MonitoringContext,
    MessageMetadata
)
from core.handlers.base.base_handler import BaseChannelHandler
from data.processing.monitoring.types import (
    MonitoringSource,
    MonitoringRequest,
    ComponentMetrics,
    MonitoringState,
    ComponentUpdate,
    MonitoringPhase,
    MonitoringStatus
)
from core.staging.staging_manager import StagingManager
from data.processing.monitoring.processor.monitoring_processor import MonitoringProcessor

logger = logging.getLogger(__name__)


class MonitoringHandler(BaseChannelHandler):
    """
    Handles communication and routing for monitoring-related messages.
    Coordinates between monitoring manager and monitoring processor.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        super().__init__(
            message_broker=message_broker,
            handler_name="monitoring_handler",
            domain_type="monitoring"
        )

        self.staging_manager = staging_manager
        self.processor = MonitoringProcessor(message_broker, staging_manager)

    async def _handle_metrics_request(
            self,
            message: ProcessingMessage
    ) -> None:
        """
        Handle incoming metrics collection request

        Processes and routes metrics collection requests from various system components
        """
        try:
            pipeline_id = message.content['pipeline_id']
            source = MonitoringSource(message.content['source'])

            # Create monitoring context
            context = MonitoringContext(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.MONITORING,
                status=ProcessingStatus.PENDING,
                source_component=message.metadata.source_component,
                metrics_types=message.content.get('metrics_types', []),
                collectors=message.content.get('collectors', []),
                thresholds=message.content.get('thresholds', {}),
                required_validations=message.content.get('required_validations', []),
                timeout_minutes=message.content.get('timeout_minutes')
            )

            # Process request through processor
            request = await self.processor.handle_component_request(
                pipeline_id,
                source,
                message.content,
                context
            )

            # Create response message
            response = message.create_response(
                MessageType.METRICS_COLLECTION_OPTIONS,
                {
                    'pipeline_id': pipeline_id,
                    'request_id': request['request_id'],
                    'metrics_types': request['metrics_types'],
                    'requires_confirmation': request.get('requires_confirmation', False),
                    'context': self._format_context(context)
                }
            )

            await self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to handle metrics request: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_metrics_submit(
            self,
            message: ProcessingMessage
    ) -> None:
        """
        Handle submitted metrics from system components

        Processes and validates metrics submissions
        """
        try:
            pipeline_id = message.content['pipeline_id']
            metrics = message.content['metrics']

            # Process metrics through processor
            component_metrics = await self.processor.process_metrics(
                pipeline_id,
                ComponentMetrics(
                    metrics_id=str(uuid.uuid4()),
                    request_id=metrics['request_id'],
                    pipeline_id=pipeline_id,
                    source=MonitoringSource(metrics['source']),
                    collected_metrics=metrics['collected_metrics'],
                    anomalies=metrics.get('anomalies', []),
                    user_confirmation=metrics.get('user_confirmation', False),
                    metadata=metrics.get('metadata', {})
                )
            )

            # Determine response type based on validation
            response_type = (
                MessageType.METRICS_COLLECTION_COMPLETE
                if component_metrics['validated']
                else MessageType.METRICS_COLLECTION_ERROR
            )

            response = message.create_response(
                response_type,
                {
                    'pipeline_id': pipeline_id,
                    'metrics_id': component_metrics['metrics_id'],
                    'status': 'completed' if component_metrics['validated'] else 'failed',
                    'anomalies': component_metrics.get('anomalies', []),
                    'metadata': component_metrics.get('metadata', {})
                }
            )

            await self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to handle metrics submission: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_system_alert(
            self,
            message: ProcessingMessage
    ) -> None:
        """
        Handle system-wide alert processing

        Coordinates alert processing and notification
        """
        try:
            alert_details = message.content.get('alert', {})
            pipeline_id = message.content.get('pipeline_id')

            # Process alert through processor
            processed_alert = await self.processor.process_system_alert(
                pipeline_id=pipeline_id,
                alert_details=alert_details
            )

            # Create response message
            response = message.create_response(
                MessageType.SYSTEM_ALERT_PROCESSED,
                {
                    'pipeline_id': pipeline_id,
                    'alert_id': processed_alert.get('id'),
                    'status': processed_alert.get('status', 'processed'),
                    'severity': processed_alert.get('severity'),
                    'metadata': processed_alert.get('metadata', {})
                }
            )

            await self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to handle system alert: {str(e)}")
            await self._handle_error(message, e)

    def _format_context(self, context: MonitoringContext) -> Dict[str, Any]:
        """
        Format monitoring context for response

        Converts monitoring context to a serializable dictionary
        """
        return {
            'source_component': context.source_component,
            'metrics_types': context.metrics_types,
            'collectors': context.collectors,
            'thresholds': context.thresholds,
            'required_validations': context.required_validations,
            'timeout_minutes': context.timeout_minutes
        }

    async def _handle_error(
            self,
            message: ProcessingMessage,
            error: Exception
    ) -> None:
        """
        Handle processing errors with comprehensive error messaging

        Creates and publishes error response messages
        """
        error_message = message.create_response(
            MessageType.METRICS_COLLECTION_ERROR,
            {
                'error': str(error),
                'pipeline_id': message.content.get('pipeline_id'),
                'source': message.metadata.source_component,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(error_message)

    async def cleanup(self) -> None:
        """
        Cleanup handler resources

        Performs necessary cleanup operations for the monitoring handler
        """
        try:
            # Cleanup processor
            await self.processor.cleanup()
        except Exception as e:
            logger.error(f"Monitoring handler cleanup failed: {str(e)}")
            raise