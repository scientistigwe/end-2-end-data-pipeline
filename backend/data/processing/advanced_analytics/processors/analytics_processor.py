# backend/core/processors/analytics_processor.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    ModuleIdentifier,
    ComponentType,
    ProcessingStage,
    AnalyticsState,
    AnalyticsContext
)

# Direct module imports
from ..modules.data_preparation import (
    DataCleanerModule,
    DataTransformerModule,
    DataValidatorModule
)
from ..modules.feature_engineering import (
    FeatureExtractorModule,
    FeatureSelectorModule,
    FeatureTransformerModule
)
from ..modules.model_training import (
    ModelSelectorModule,
    ModelTrainerModule,
    ModelTunerModule
)
from ..modules.model_evaluation import (
    PerformanceEvaluatorModule,
    BiasCheckerModule,
    StabilityTesterModule
)

logger = logging.getLogger(__name__)


class AnalyticsProcessor:
    """
    Analytics Processor coordinates between modules and messaging system.
    Handles direct module interaction while maintaining message-based coordination.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.module_identifier = ModuleIdentifier(
            component_name="analytics_processor",
            component_type=ComponentType.ANALYTICS_PROCESSOR,
            department="analytics",
            role="processor"
        )

        # Initialize modules
        self._initialize_modules()

        # Track active processing
        self.active_processes: Dict[str, AnalyticsContext] = {}

        self._setup_message_handlers()

    def _initialize_modules(self) -> None:
        """Initialize processing modules"""
        # Data preparation modules
        self.data_cleaner = DataCleanerModule()
        self.data_transformer = DataTransformerModule()
        self.data_validator = DataValidatorModule()

        # Feature engineering modules
        self.feature_extractor = FeatureExtractorModule()
        self.feature_selector = FeatureSelectorModule()
        self.feature_transformer = FeatureTransformerModule()

        # Model training modules
        self.model_selector = ModelSelectorModule()
        self.model_trainer = ModelTrainerModule()
        self.model_tuner = ModelTunerModule()

        # Model evaluation modules
        self.performance_evaluator = PerformanceEvaluatorModule()
        self.bias_checker = BiasCheckerModule()
        self.stability_tester = StabilityTesterModule()

    def _setup_message_handlers(self) -> None:
        """Setup message handlers"""
        handlers = {
            MessageType.ANALYTICS_PROCESS_START: self._handle_process_start,
            MessageType.ANALYTICS_DATA_PREPARE: self._handle_data_preparation,
            MessageType.ANALYTICS_FEATURE_ENGINEER: self._handle_feature_engineering,
            MessageType.ANALYTICS_MODEL_TRAIN: self._handle_model_training,
            MessageType.ANALYTICS_MODEL_EVALUATE: self._handle_model_evaluation,
            MessageType.ANALYTICS_PROCESS_CANCEL: self._handle_process_cancel
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_process_start(self, message: ProcessingMessage) -> None:
        """Handle start of processing pipeline"""
        pipeline_id = message.content["pipeline_id"]
        try:
            # Create process context
            context = AnalyticsContext(
                pipeline_id=pipeline_id,
                correlation_id=message.metadata.correlation_id,
                state=AnalyticsState.INITIALIZING
            )
            self.active_processes[pipeline_id] = context

            # Begin with data preparation
            await self._begin_data_preparation(
                pipeline_id,
                message.content.get("data_config", {})
            )

        except Exception as e:
            await self._handle_processing_error(pipeline_id, str(e))

    async def _begin_data_preparation(self, pipeline_id: str, config: Dict[str, Any]) -> None:
        """Begin data preparation phase"""
        try:
            context = self.active_processes[pipeline_id]
            context.state = AnalyticsState.DATA_PREPARATION

            # Direct module interaction
            raw_data = config.get("data")

            # Step 1: Clean data
            cleaned_data = await self.data_cleaner.clean_data(
                raw_data,
                config.get("cleaning_params", {})
            )

            # Step 2: Transform data
            transformed_data = await self.data_transformer.transform_data(
                cleaned_data,
                config.get("transformation_params", {})
            )

            # Step 3: Validate data
            validation_results = await self.data_validator.validate_data(
                transformed_data,
                config.get("validation_params", {})
            )

            # Store results directly if needed
            await self._store_processing_results(
                pipeline_id,
                "data_preparation",
                {
                    "cleaned_data": cleaned_data,
                    "transformed_data": transformed_data,
                    "validation_results": validation_results
                }
            )

            # Proceed to feature engineering
            await self._begin_feature_engineering(
                pipeline_id,
                transformed_data,
                config.get("feature_config", {})
            )

        except Exception as e:
            await self._handle_processing_error(pipeline_id, str(e))

    async def _begin_feature_engineering(
            self,
            pipeline_id: str,
            data: Any,
            config: Dict[str, Any]
    ) -> None:
        """Begin feature engineering phase"""
        try:
            context = self.active_processes[pipeline_id]
            context.state = AnalyticsState.FEATURE_ENGINEERING

            # Direct module interaction
            extracted_features = await self.feature_extractor.extract_features(
                data,
                config.get("extraction_params", {})
            )

            selected_features = await self.feature_selector.select_features(
                extracted_features,
                config.get("selection_params", {})
            )

            transformed_features = await self.feature_transformer.transform_features(
                selected_features,
                config.get("transformation_params", {})
            )

            # Store results directly if needed
            await self._store_processing_results(
                pipeline_id,
                "feature_engineering",
                {
                    "extracted_features": extracted_features,
                    "selected_features": selected_features,
                    "transformed_features": transformed_features
                }
            )

            # Proceed to model training
            await self._begin_model_training(
                pipeline_id,
                transformed_features,
                config.get("model_config", {})
            )

        except Exception as e:
            await self._handle_processing_error(pipeline_id, str(e))

    async def _begin_model_training(
            self,
            pipeline_id: str,
            features: Any,
            config: Dict[str, Any]
    ) -> None:
        """Begin model training phase"""
        try:
            context = self.active_processes[pipeline_id]
            context.state = AnalyticsState.MODEL_TRAINING

            # Direct module interaction
            selected_model = await self.model_selector.select_model(
                features,
                config.get("selection_params", {})
            )

            trained_model = await self.model_trainer.train_model(
                selected_model,
                features,
                config.get("training_params", {})
            )

            tuned_model = await self.model_tuner.tune_model(
                trained_model,
                config.get("tuning_params", {})
            )

            # Store results directly if needed
            await self._store_processing_results(
                pipeline_id,
                "model_training",
                {
                    "selected_model": selected_model,
                    "trained_model": trained_model,
                    "tuned_model": tuned_model,
                    "training_metrics": trained_model.get_metrics()
                }
            )

            # Proceed to model evaluation
            await self._begin_model_evaluation(
                pipeline_id,
                tuned_model,
                features,
                config.get("evaluation_config", {})
            )

        except Exception as e:
            await self._handle_processing_error(pipeline_id, str(e))

    async def _begin_model_evaluation(
            self,
            pipeline_id: str,
            model: Any,
            features: Any,
            config: Dict[str, Any]
    ) -> None:
        """Begin model evaluation phase"""
        try:
            context = self.active_processes[pipeline_id]
            context.state = AnalyticsState.MODEL_EVALUATION

            # Direct module interaction
            performance_results = await self.performance_evaluator.evaluate_model(
                model,
                features,
                config.get("performance_params", {})
            )

            bias_results = await self.bias_checker.check_bias(
                model,
                features,
                config.get("bias_params", {})
            )

            stability_results = await self.stability_tester.test_stability(
                model,
                features,
                config.get("stability_params", {})
            )

            # Store results directly if needed
            final_results = {
                "performance": performance_results,
                "bias": bias_results,
                "stability": stability_results,
                "model": model
            }

            await self._store_processing_results(
                pipeline_id,
                "model_evaluation",
                final_results
            )

            # Complete processing
            await self._complete_processing(pipeline_id, final_results)

        except Exception as e:
            await self._handle_processing_error(pipeline_id, str(e))

    async def _store_processing_results(
            self,
            pipeline_id: str,
            stage: str,
            results: Dict[str, Any]
    ) -> None:
        """Store processing results directly"""
        # Implement direct storage logic here
        pass

    async def _complete_processing(
            self,
            pipeline_id: str,
            results: Dict[str, Any]
    ) -> None:
        """Handle processing completion"""
        try:
            context = self.active_processes[pipeline_id]
            context.state = AnalyticsState.COMPLETED

            # Notify completion via message
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_PROCESS_COMPLETE,
                    content={
                        "pipeline_id": pipeline_id,
                        "results": results,
                        "completion_time": datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="analytics_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            await self._handle_processing_error(pipeline_id, str(e))

    async def _handle_processing_error(self, pipeline_id: str, error: str) -> None:
        """Handle processing errors"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.ANALYTICS_PROCESS_ERROR,
                content={
                    "pipeline_id": pipeline_id,
                    "error": error,
                    "stage": context.state.value,
                    "timestamp": datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="analytics_handler"
                ),
                source_identifier=self.module_identifier
            )
        )

        await self._cleanup_process(pipeline_id)

    async def _cleanup_process(self, pipeline_id: str) -> None:
        """Clean up process resources"""
        if pipeline_id in self.active_processes:
            del self.active_processes[pipeline_id]

    async def cleanup(self) -> None:
        """Clean up processor resources"""
        try:
            # Clean up all active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self._cleanup_process(pipeline_id)

            # Unsubscribe from message broker
            await self.message_broker.unsubscribe_all(self.module_identifier)

        except Exception as e:
            logger.error(f"Processor cleanup failed: {str(e)}")