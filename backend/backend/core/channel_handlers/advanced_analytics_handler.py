import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID

from backend.core.channel_handlers.base_channel_handler import BaseChannelHandler
from backend.core.channel_handlers.core_process_handler import CoreProcessHandler
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ProcessingStage,
    ModuleIdentifier,
    ComponentType
)
from backend.data_pipeline.advanced_analytics.analytics_processor import (
    AnalyticsProcessor,
    AnalyticsPhase
)

logger = logging.getLogger(__name__)


class AdvancedAnalyticsHandler(BaseChannelHandler):
    """
    Handles communication and routing for advanced analytics messages

    Responsibilities:
    - Route analytics-related messages
    - Coordinate with analytics processor
    - Interface with analytics manager
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            process_handler: Optional[CoreProcessHandler] = None,
            analytics_processor: Optional[AnalyticsProcessor] = None
    ):
        """Initialize advanced analytics handler"""
        super().__init__(message_broker, "advanced_analytics_handler")

        # Initialize dependencies
        self.process_handler = process_handler or CoreProcessHandler(message_broker)
        self.analytics_processor = analytics_processor or AnalyticsProcessor(message_broker)

        # Register message handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register message handlers for analytics processing"""
        self.register_callback(
            MessageType.ANALYTICS_START,
            self._handle_analytics_start
        )
        self.register_callback(
            MessageType.ANALYTICS_COMPLETE,
            self._handle_analytics_complete
        )
        self.register_callback(
            MessageType.ANALYTICS_UPDATE,
            self._handle_analytics_update
        )
        self.register_callback(
            MessageType.ANALYTICS_ERROR,
            self._handle_analytics_error
        )

    def _handle_analytics_start(self, message: ProcessingMessage) -> None:
        """Handle analytics process start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            data = message.content.get('data', {})
            context = message.content.get('context', {})

            # Create response message to analytics manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="advanced_analytics_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_analytics_start"
                ),
                message_type=MessageType.ANALYTICS_STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'status': 'started',
                    'phase': AnalyticsPhase.DATA_PREPARATION.value
                }
            )

            # Execute process via process handler
            self.process_handler.execute_process(
                self._run_analytics_process,
                pipeline_id=pipeline_id,
                stage=ProcessingStage.ADVANCED_ANALYTICS,
                message_type=MessageType.ANALYTICS_START,
                data=data,
                context=context
            )

            # Publish response to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to start analytics process: {e}")
            self._handle_analytics_error(
                ProcessingMessage(
                    source_identifier=self.module_id,
                    target_identifier=ModuleIdentifier(
                        component_name="advanced_analytics_manager",
                        component_type=ComponentType.MANAGER
                    ),
                    message_type=MessageType.ANALYTICS_ERROR,
                    content={
                        'error': str(e),
                        'pipeline_id': message.content.get('pipeline_id')
                    }
                )
            )

    async def _run_analytics_process(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Core analytics process execution logic"""
        try:
            # Run data preparation phase
            prepared_data = await self.analytics_processor.prepare_data(
                context.get('run_id'),
                data,
                context
            )

            # Run statistical analysis phase
            analysis_results = await self.analytics_processor.run_statistical_analysis(
                context.get('run_id'),
                prepared_data
            )

            # Run feature engineering phase
            engineered_features = await self.analytics_processor.engineer_features(
                context.get('run_id'),
                analysis_results
            )

            # Run predictive modeling phase
            model_results = await self.analytics_processor.run_predictive_modeling(
                context.get('run_id'),
                engineered_features,
                context
            )

            # Run model evaluation phase
            evaluation_results = await self.analytics_processor.evaluate_model(
                context.get('run_id'),
                model_results
            )

            # Run visualization phase
            visualization_results = await self.analytics_processor.generate_visualizations(
                context.get('run_id'),
                evaluation_results
            )

            return {
                'prepared_data': prepared_data,
                'analysis_results': analysis_results,
                'engineered_features': engineered_features,
                'model_results': model_results,
                'evaluation_results': evaluation_results,
                'visualization_results': visualization_results,
                'pipeline_id': context.get('pipeline_id')
            }

        except Exception as e:
            logger.error(f"Analytics process failed: {e}")
            raise

    def _handle_analytics_complete(self, message: ProcessingMessage) -> None:
        """Handle analytics process completion"""
        try:
            # Create completion response for manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="advanced_analytics_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_analytics_complete"
                ),
                message_type=MessageType.ANALYTICS_COMPLETE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'results': message.content.get('results', {}),
                    'status': 'completed'
                }
            )

            # Publish completion to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling analytics completion: {e}")

    def _handle_analytics_update(self, message: ProcessingMessage) -> None:
        """Handle analytics process updates"""
        try:
            # Forward update to analytics manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="advanced_analytics_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_analytics_update"
                ),
                message_type=MessageType.ANALYTICS_STATUS_UPDATE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'status': message.content.get('status'),
                    'progress': message.content.get('progress')
                }
            )

            # Publish update to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling analytics update: {e}")

        def _handle_analytics_error(self, message: ProcessingMessage) -> None:
            """Handle analytics process errors"""
            try:
                # Forward error to analytics manager
                error_response = ProcessingMessage(
                    source_identifier=self.module_id,
                    target_identifier=ModuleIdentifier(
                        component_name="advanced_analytics_manager",
                        component_type=ComponentType.MANAGER,
                        method_name="handle_analytics_error"
                    ),
                    message_type=MessageType.ANALYTICS_ERROR,
                    content={
                        'pipeline_id': message.content.get('pipeline_id'),
                        'error': message.content.get('error')
                    }
                )

                # Publish error to manager
                self.message_broker.publish(error_response)

            except Exception as e:
                logger.error(f"Error handling analytics error: {e}")

        def _handle_model_performance_update(self, message: ProcessingMessage) -> None:
            """Handle model performance updates"""
            try:
                # Forward model performance update to analytics manager
                performance_response = ProcessingMessage(
                    source_identifier=self.module_id,
                    target_identifier=ModuleIdentifier(
                        component_name="advanced_analytics_manager",
                        component_type=ComponentType.MANAGER,
                        method_name="handle_model_performance_update"
                    ),
                    message_type=MessageType.MODEL_PERFORMANCE_UPDATE,
                    content={
                        'pipeline_id': message.content.get('pipeline_id'),
                        'performance_metrics': message.content.get('metrics', {}),
                        'feature_importance': message.content.get('feature_importance', {})
                    }
                )

                # Publish performance update
                self.message_broker.publish(performance_response)

            except Exception as e:
                logger.error(f"Error handling model performance update: {e}")

        def _handle_feature_engineering_complete(self, message: ProcessingMessage) -> None:
            """Handle feature engineering completion"""
            try:
                # Forward feature engineering results to analytics manager
                feature_response = ProcessingMessage(
                    source_identifier=self.module_id,
                    target_identifier=ModuleIdentifier(
                        component_name="advanced_analytics_manager",
                        component_type=ComponentType.MANAGER,
                        method_name="handle_feature_engineering_complete"
                    ),
                    message_type=MessageType.FEATURE_ENGINEERING_COMPLETE,
                    content={
                        'pipeline_id': message.content.get('pipeline_id'),
                        'engineered_features': message.content.get('features', []),
                        'feature_metadata': message.content.get('metadata', {})
                    }
                )

                # Publish feature engineering results
                self.message_broker.publish(feature_response)

            except Exception as e:
                logger.error(f"Error handling feature engineering completion: {e}")

        def get_process_status(self, run_id: str) -> Optional[Dict[str, Any]]:
            """Get current process status"""
            return self.process_handler.get_process_status(run_id)

        async def cleanup(self) -> None:
            """Cleanup handler resources"""
            try:
                # Cleanup process handler
                if hasattr(self.process_handler, 'cleanup'):
                    await self.process_handler.cleanup()

                # Cleanup analytics processor
                if hasattr(self.analytics_processor, 'cleanup'):
                    await self.analytics_processor.cleanup()

                # Call parent cleanup
                await super().cleanup()

            except Exception as e:
                logger.error(f"Error during analytics handler cleanup: {e}")