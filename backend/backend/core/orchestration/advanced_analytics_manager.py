import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID
import uuid

from backend.core.orchestration.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ProcessingStage,
    ComponentType,
    ModuleIdentifier
)
from backend.core.channel_handlers.advanced_analytics_handler import AdvancedAnalyticsHandler
from backend.database.repository.advanced_analytics_repository import AdvancedAnalyticsRepository
from backend.core.orchestration.pipeline_manager_helper import (
    PipelineState,
    PipelineStateManager
)
from backend.data_pipeline.advanced_analytics.analytics_processor import (
    AnalyticsPhase,
    AnalyticsResult
)

logger = logging.getLogger(__name__)

class AdvancedAnalyticsManager(BaseManager):
    """
    Advanced Analytics manager orchestrating complex analytical processes
    Responsible for coordinating advanced analytics and managing their lifecycle
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            repository: Optional[AdvancedAnalyticsRepository] = None,
            analytics_handler: Optional[AdvancedAnalyticsHandler] = None,
            state_manager: Optional[PipelineStateManager] = None,
            component_name: str = "AdvancedAnalyticsManager"
    ):
        """Initialize advanced analytics manager with comprehensive components"""
        # Initialize base manager
        super().__init__(
            message_broker=message_broker,
            component_name=component_name
        )

        # Dependency injection
        self.repository = repository
        self.analytics_handler = analytics_handler or AdvancedAnalyticsHandler(message_broker)
        self.state_manager = state_manager or PipelineStateManager()

        # Setup event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Setup message handlers for analytics-related events"""
        try:
            # Subscribe to analytics handler message patterns
            self.message_broker.subscribe(
                component=self.module_id,
                pattern="advanced_analytics_handler.*",
                callback=self._handle_handler_messages
            )

        except Exception as e:
            logger.error(f"Failed to setup event handlers: {str(e)}")
            self._handle_error(None, e)

    async def _handle_handler_messages(self, message: ProcessingMessage) -> None:
        """Central routing for messages from analytics handler"""
        try:
            if message.message_type == MessageType.ANALYTICS_STATUS_UPDATE:
                await self.handle_analytics_status_update(message)
            elif message.message_type == MessageType.ANALYTICS_COMPLETE:
                await self.handle_analytics_complete(message)
            elif message.message_type == MessageType.ANALYTICS_ERROR:
                await self.handle_analytics_error(message)
            elif message.message_type == MessageType.MODEL_PERFORMANCE_UPDATE:
                await self.handle_model_performance_update(message)
            elif message.message_type == MessageType.FEATURE_ENGINEERING_COMPLETE:
                await self.handle_feature_engineering_complete(message)

        except Exception as e:
            logger.error(f"Error routing handler message: {str(e)}")
            await self._handle_error(
                message.content.get('pipeline_id'),
                e
            )

    async def initiate_analytics_process(
            self,
            pipeline_id: str,
            data: Dict[str, Any],
            analysis_config: Dict[str, Any]
    ) -> UUID:
        """Initiate an advanced analytics process for a specific pipeline"""
        try:
            # Generate unique run ID
            run_id = UUID(uuid.uuid4())

            # Create pipeline state if not exists
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if not pipeline_state:
                pipeline_state = PipelineState(
                    pipeline_id=pipeline_id,
                    current_stage=ProcessingStage.ADVANCED_ANALYTICS,
                    status=ProcessingStatus.PENDING
                )
                self.state_manager.add_pipeline(pipeline_state)

            # Create initial run record in repository
            if self.repository:
                await self.repository.create_analytics_run({
                    'pipeline_id': pipeline_id,
                    'run_id': str(run_id),
                    'analysis_type': analysis_config.get('type', 'advanced_analysis'),
                    'parameters': analysis_config.get('parameters', {}),
                    'status': 'pending',
                    'created_at': datetime.utcnow()
                })

            # Prepare analytics process message
            analytics_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="advanced_analytics_handler",
                    component_type=ComponentType.HANDLER
                ),
                message_type=MessageType.ANALYTICS_START,
                content={
                    'pipeline_id': pipeline_id,
                    'data': data,
                    'context': {
                        'run_id': str(run_id),
                        'pipeline_id': pipeline_id,
                        'config': analysis_config
                    }
                }
            )

            # Publish message to analytics handler
            await self.message_broker.publish(analytics_message)

            return run_id

        except Exception as e:
            logger.error(f"Failed to initiate analytics process: {str(e)}")
            await self._handle_error(pipeline_id, e)
            raise

    async def handle_analytics_status_update(self, message: ProcessingMessage) -> None:
        """Handle status updates from analytics handler"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            status = message.content.get('status')
            progress = message.content.get('progress', 0)
            phase = message.content.get('phase')

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus(status)
                pipeline_state.current_progress = progress

            # Update repository if available
            if self.repository:
                await self.repository.update_run_status(
                    pipeline_id,
                    status=status,
                    progress=progress,
                    phase=phase
                )

        except Exception as e:
            logger.error(f"Error handling analytics status update: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_model_performance_update(self, message: ProcessingMessage) -> None:
        """Handle model performance updates"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            metrics = message.content.get('performance_metrics', {})
            feature_importance = message.content.get('feature_importance', {})

            # Save model performance in repository
            if self.repository:
                await self.repository.save_analytics_model(
                    pipeline_id,
                    {
                        'model_type': metrics.get('model_type'),
                        'parameters': metrics.get('parameters', {}),
                        'metrics': metrics,
                        'feature_importance': feature_importance
                    }
                )

        except Exception as e:
            logger.error(f"Error handling model performance update: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_feature_engineering_complete(self, message: ProcessingMessage) -> None:
        """Handle feature engineering completion"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            features = message.content.get('engineered_features', [])
            metadata = message.content.get('feature_metadata', {})

            # Save engineered features in repository
            if self.repository:
                await self.repository.save_engineered_features(
                    pipeline_id,
                    features
                )

        except Exception as e:
            logger.error(f"Error handling feature engineering completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_analytics_complete(self, message: ProcessingMessage) -> None:
        """Handle analytics process completion"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            results = message.content.get('results', {})

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus.COMPLETED
                pipeline_state.current_stage = ProcessingStage.REPORT_GENERATION
                pipeline_state.current_progress = 100.0

            # Save results in repository
            if self.repository:
                await self.repository.save_analytics_results(
                    pipeline_id,
                    results
                )

                # Save visualizations if present
                if 'visualization_results' in results:
                    for viz in results['visualization_results']:
                        await self.repository.save_visualization(
                            pipeline_id,
                            viz
                        )

            # Notify pipeline manager about stage completion
            completion_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="pipeline_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.STAGE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.ADVANCED_ANALYTICS.value,
                    'results': results
                }
            )
            await self.message_broker.publish(completion_message)

        except Exception as e:
            logger.error(f"Error handling analytics completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_analytics_error(self, message: ProcessingMessage) -> None:
        """Handle analytics process errors"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            error = message.content.get('error')

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus.FAILED
                pipeline_state.add_error(error)

            # Persist error in repository
            if self.repository:
                await self.repository.log_analytics_error(
                    pipeline_id,
                    error,
                    stage=ProcessingStage.ADVANCED_ANALYTICS.value
                )

            # Notify pipeline manager about stage failure
            error_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="pipeline_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.STAGE_FAILED,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.ADVANCED_ANALYTICS.value,
                    'error': error
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Error handling analytics error: {str(e)}")

        async def _handle_error(
                self,
                pipeline_id: Optional[str],
                error: Exception
        ) -> None:
            """Comprehensive error handling"""
            try:
                # Log error
                logger.error(f"Advanced analytics manager error: {str(error)}")

                # Update pipeline state
                if pipeline_id:
                    pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
                    if pipeline_state:
                        pipeline_state.status = ProcessingStatus.FAILED
                        pipeline_state.add_error(str(error))

                # Publish error message
                error_message = ProcessingMessage(
                    source_identifier=self.module_id,
                    target_identifier=ModuleIdentifier(
                        component_name="pipeline_manager",
                        component_type=ComponentType.MANAGER
                    ),
                    message_type=MessageType.STAGE_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage': ProcessingStage.ADVANCED_ANALYTICS.value,
                        'error': str(error)
                    }
                )
                await self.message_broker.publish(error_message)

            except Exception as e:
                logger.error(f"Critical error in advanced analytics manager error handling: {str(e)}")

        def get_analytics_status(self, run_id: UUID) -> Optional[Dict[str, Any]]:
            """Retrieve status of a specific analytics run"""
            try:
                # Get status from repository
                if self.repository:
                    analytics_run = self.repository.get_run(run_id)

                    # Get process status from handler
                    process_status = self.analytics_handler.get_process_status(str(run_id))

                    if analytics_run:
                        status_details = {
                            'run_id': str(run_id),
                            'status': analytics_run.status,
                            'analysis_type': analytics_run.analysis_type,
                            'created_at': analytics_run.created_at.isoformat(),
                            'updated_at': analytics_run.updated_at.isoformat(),
                            'parameters': analytics_run.parameters
                        }

                        # Enhance with process details if available
                        if process_status:
                            status_details.update({
                                'phase': process_status.get('phase'),
                                'progress': process_status.get('progress', 0),
                                'active': True,
                                'metadata': process_status.get('metadata', {})
                            })

                        # Add model performance if available
                        model_performance = self.repository.get_model_performance(run_id)
                        if model_performance:
                            status_details['model_performance'] = model_performance

                        return status_details

                return None

            except Exception as e:
                logger.error(f"Error retrieving analytics status: {str(e)}")
                return None

        async def get_analytics_results(self, run_id: UUID) -> Optional[Dict[str, Any]]:
            """Retrieve comprehensive results of an analytics run"""
            try:
                if self.repository:
                    run = self.repository.get_run(run_id)
                    if run:
                        results = {
                            'run_id': str(run_id),
                            'analysis_type': run.analysis_type,
                            'parameters': run.parameters,
                            'status': run.status,
                            'created_at': run.created_at.isoformat(),
                        }

                        # Add models if available
                        if hasattr(run, 'models') and run.models:
                            results['models'] = [
                                {
                                    'model_type': model.model_type,
                                    'metrics': model.metrics,
                                    'feature_importance': model.feature_importance
                                }
                                for model in run.models
                            ]

                        # Add features if available
                        if hasattr(run, 'features') and run.features:
                            results['engineered_features'] = [
                                {
                                    'name': feature.name,
                                    'type': feature.feature_type,
                                    'description': feature.description,
                                    'metadata': feature.metadata
                                }
                                for feature in run.features
                            ]

                        # Add visualizations if available
                        if hasattr(run, 'visualizations') and run.visualizations:
                            results['visualizations'] = [
                                {
                                    'type': viz.viz_type,
                                    'config': viz.config,
                                    'data': viz.data
                                }
                                for viz in run.visualizations
                            ]

                        return results

                return None

            except Exception as e:
                logger.error(f"Error retrieving analytics results: {str(e)}")
                return None

        async def cleanup(self) -> None:
            """Comprehensive cleanup of advanced analytics manager resources"""
            try:
                # Cancel all active pipelines
                for pipeline_id in self.state_manager.get_active_pipelines():
                    state = self.state_manager.get_pipeline_state(pipeline_id)
                    if state and state.status == ProcessingStatus.RUNNING:
                        state.status = ProcessingStatus.CANCELLED

                        # Publish cancellation message
                        cancellation_message = ProcessingMessage(
                            source_identifier=self.module_id,
                            target_identifier=ModuleIdentifier(
                                component_name="pipeline_manager",
                                component_type=ComponentType.MANAGER
                            ),
                            message_type=MessageType.STAGE_CANCELLED,
                            content={
                                'pipeline_id': pipeline_id,
                                'stage': ProcessingStage.ADVANCED_ANALYTICS.value
                            }
                        )
                        await self.message_broker.publish(cancellation_message)

                # Reset state manager
                self.state_manager = PipelineStateManager()

                # Cleanup analytics handler
                if hasattr(self.analytics_handler, 'cleanup'):
                    await self.analytics_handler.cleanup()

                # Call parent cleanup
                await super().cleanup()

            except Exception as e:
                logger.error(f"Error during advanced analytics manager cleanup: {str(e)}")

            # Factory method for easy instantiation

        @classmethod
        def create(
                cls,
                message_broker: Optional[MessageBroker] = None,
                repository: Optional[AdvancedAnalyticsRepository] = None
        ) -> 'AdvancedAnalyticsManager':
            """Factory method to create AdvancedAnalyticsManager with optional dependencies"""
            # Import global message broker if not provided
            if message_broker is None:
                from backend.core.messaging.broker import message_broker

            return cls(
                message_broker=message_broker,
                repository=repository
            )