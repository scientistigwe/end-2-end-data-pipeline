# backend/core/handlers/channel/analytics_handler.py

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

from ...messaging.broker import MessageBroker
from ...messaging.types import (
    MessageType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage,
    MessageMetadata
)
from ...staging.staging_manager import StagingManager
from ..base.base_handler import BaseChannelHandler, HandlerState, ProcessingTask
from ....data_pipeline.advanced_analytics.processor.analytics_processor import (
    AnalyticsProcessor,
    AnalyticsPhase,
    AnalyticsContext
)


class AdvancedAnalyticsHandler(BaseChannelHandler):
    """
    Handler for advanced analytics operations.
    Coordinates between manager, processor, and staging area.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        super().__init__(
            message_broker=message_broker,
            handler_name="advanced_analytics_handler",
            domain_type="analytics"
        )

        # Initialize components
        self.staging_manager = staging_manager
        self.analytics_processor = AnalyticsProcessor(
            message_broker=message_broker,
            staging_manager=staging_manager
        )

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup handlers for analytics-specific messages"""
        self.register_message_handler(
            MessageType.ANALYTICS_START,
            self._handle_analytics_start
        )
        self.register_message_handler(
            MessageType.ANALYTICS_UPDATE,
            self._handle_analytics_update
        )
        self.register_message_handler(
            MessageType.ANALYTICS_REFINE,
            self._handle_analytics_refine
        )
        self.register_message_handler(
            MessageType.MODEL_PERFORMANCE_UPDATE,
            self._handle_model_performance
        )

    async def _handle_analytics_start(self, message: ProcessingMessage) -> None:
        """Handle start of analytics process"""
        pipeline_id = message.content.get('pipeline_id')
        staged_id = message.content.get('staged_id')
        config = message.content.get('config', {})

        try:
            # Create processing task
            task = ProcessingTask(
                task_id=pipeline_id,
                message=message,
                processor_context={
                    'staged_id': staged_id,
                    'config': config
                }
            )
            self._active_tasks[task.task_id] = task

            # Run data preparation phase
            await self._run_data_preparation(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                config=config
            )

            # Notify about process start
            await self._notify_process_status(
                pipeline_id=pipeline_id,
                phase=AnalyticsPhase.DATA_PREPARATION,
                status="started",
                metadata={
                    'staged_id': staged_id,
                    'config_summary': self._get_config_summary(config)
                }
            )

        except Exception as e:
            await self._handle_analytics_error(
                pipeline_id=pipeline_id,
                phase="initialization",
                error=str(e)
            )

    async def _run_data_preparation(
            self,
            pipeline_id: str,
            staged_id: str,
            config: Dict[str, Any]
    ) -> None:
        """Execute data preparation phase"""
        try:
            results = await self.analytics_processor.prepare_data(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                config=config
            )

            # Store phase results in staging
            prep_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=results,
                metadata={
                    'phase': AnalyticsPhase.DATA_PREPARATION.value,
                    'pipeline_id': pipeline_id
                }
            )

            # Proceed to feature engineering
            await self._run_feature_engineering(
                pipeline_id=pipeline_id,
                staged_id=prep_staged_id,
                config=config
            )

        except Exception as e:
            await self._handle_analytics_error(
                pipeline_id=pipeline_id,
                phase=AnalyticsPhase.DATA_PREPARATION.value,
                error=str(e)
            )

    async def _run_feature_engineering(
            self,
            pipeline_id: str,
            staged_id: str,
            config: Dict[str, Any]
    ) -> None:
        """Execute feature engineering phase"""
        try:
            results = await self.analytics_processor.engineer_features(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                config=config
            )

            # Store phase results
            feature_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=results,
                metadata={
                    'phase': AnalyticsPhase.FEATURE_ENGINEERING.value,
                    'pipeline_id': pipeline_id
                }
            )

            # Notify about phase completion
            await self._notify_phase_completion(
                pipeline_id=pipeline_id,
                phase=AnalyticsPhase.FEATURE_ENGINEERING,
                results=results,
                staged_id=feature_staged_id
            )

            # Proceed to model training
            await self._run_model_training(
                pipeline_id=pipeline_id,
                staged_id=feature_staged_id,
                config=config
            )

        except Exception as e:
            await self._handle_analytics_error(
                pipeline_id=pipeline_id,
                phase=AnalyticsPhase.FEATURE_ENGINEERING.value,
                error=str(e)
            )

    async def _run_model_training(
            self,
            pipeline_id: str,
            staged_id: str,
            config: Dict[str, Any]
    ) -> None:
        """Execute model training phase"""
        try:
            results = await self.analytics_processor.train_model(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                config=config
            )

            # Store phase results
            model_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=results,
                metadata={
                    'phase': AnalyticsPhase.MODEL_TRAINING.value,
                    'pipeline_id': pipeline_id
                }
            )

            # Notify about phase completion
            await self._notify_phase_completion(
                pipeline_id=pipeline_id,
                phase=AnalyticsPhase.MODEL_TRAINING,
                results=results,
                staged_id=model_staged_id
            )

            # Proceed to model evaluation
            await self._run_model_evaluation(
                pipeline_id=pipeline_id,
                staged_id=model_staged_id,
                config=config
            )

        except Exception as e:
            await self._handle_analytics_error(
                pipeline_id=pipeline_id,
                phase=AnalyticsPhase.MODEL_TRAINING.value,
                error=str(e)
            )

    async def _run_model_evaluation(
            self,
            pipeline_id: str,
            staged_id: str,
            config: Dict[str, Any]
    ) -> None:
        """Execute model evaluation phase"""
        try:
            results = await self.analytics_processor.evaluate_model(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                config=config
            )

            # Store phase results
            eval_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=results,
                metadata={
                    'phase': AnalyticsPhase.MODEL_EVALUATION.value,
                    'pipeline_id': pipeline_id
                }
            )

            # Notify about phase completion
            await self._notify_phase_completion(
                pipeline_id=pipeline_id,
                phase=AnalyticsPhase.MODEL_EVALUATION,
                results=results,
                staged_id=eval_staged_id
            )

            # Proceed to visualization
            await self._run_visualization(
                pipeline_id=pipeline_id,
                staged_id=eval_staged_id,
                config=config
            )

        except Exception as e:
            await self._handle_analytics_error(
                pipeline_id=pipeline_id,
                phase=AnalyticsPhase.MODEL_EVALUATION.value,
                error=str(e)
            )

    async def _run_visualization(
            self,
            pipeline_id: str,
            staged_id: str,
            config: Dict[str, Any]
    ) -> None:
        """Execute visualization generation phase"""
        try:
            results = await self.analytics_processor.generate_visualizations(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                config=config
            )

            # Store phase results
            viz_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=results,
                metadata={
                    'phase': AnalyticsPhase.VISUALIZATION.value,
                    'pipeline_id': pipeline_id
                }
            )

            # Notify about process completion
            await self._notify_process_completion(
                pipeline_id=pipeline_id,
                final_results=results,
                final_staged_id=viz_staged_id
            )

        except Exception as e:
            await self._handle_analytics_error(
                pipeline_id=pipeline_id,
                phase=AnalyticsPhase.VISUALIZATION.value,
                error=str(e)
            )

    async def _notify_phase_completion(
            self,
            pipeline_id: str,
            phase: AnalyticsPhase,
            results: Dict[str, Any],
            staged_id: str
    ) -> None:
        """Notify about phase completion"""
        message = ProcessingMessage(
            message_type=MessageType.ANALYTICS_UPDATE,
            content={
                'pipeline_id': pipeline_id,
                'phase': phase.value,
                'staged_id': staged_id,
                'summary': self._get_phase_summary(results)
            },
            metadata=MessageMetadata(
                source_component=self.handler_name,
                target_component="advanced_analytics_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_process_completion(
            self,
            pipeline_id: str,
            final_results: Dict[str, Any],
            final_staged_id: str
    ) -> None:
        """Notify about process completion"""
        message = ProcessingMessage(
            message_type=MessageType.ANALYTICS_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'staged_id': final_staged_id,
                'summary': self._get_process_summary(final_results)
            },
            metadata=MessageMetadata(
                source_component=self.handler_name,
                target_component="advanced_analytics_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _handle_analytics_error(
            self,
            pipeline_id: str,
            phase: str,
            error: str
    ) -> None:
        """Handle analytics processing errors"""
        try:
            # Create error message
            error_message = ProcessingMessage(
                message_type=MessageType.ANALYTICS_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'phase': phase,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.handler_name,
                    target_component="advanced_analytics_manager"
                )
            )

            # Publish error
            await self.message_broker.publish(error_message)

            # Cleanup task
            if pipeline_id in self._active_tasks:
                del self._active_tasks[pipeline_id]

        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")

    def _get_config_summary(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of configuration settings"""
        return {
            'data_config': list(config.get('data_config', {}).keys()),
            'model_config': list(config.get('model_config', {}).keys())
        }

    def _get_phase_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of phase results"""
        return {
            'result_types': list(results.keys()),
            'timestamp': datetime.now().isoformat()
        }

    def _get_process_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of complete process results"""
        return {
            'charts_generated': len(results.get('charts', [])),
            'plots_generated': len(results.get('plots', [])),
            'completion_time': datetime.now().isoformat()
        }

    async def cleanup(self) -> None:
        """Cleanup handler resources"""
        try:
            # Cleanup processor
            await self.analytics_processor.cleanup()

            # Cleanup base handler
            await super().cleanup()

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise