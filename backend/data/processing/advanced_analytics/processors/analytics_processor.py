<<<<<<< HEAD
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
=======
# backend/data_pipeline/advanced_analytics/processor/analytics_processor.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage
from backend.core.staging.staging_manager import StagingManager

# Import analytics modules
from ..modules.data_preparation import (
    data_cleaner,
    data_transformer,
    data_validator
)
from ..modules.feature_engineering import (
    feature_extractor,
    feature_selector,
    feature_transformer
)
from ..modules.model_training import (
    model_selector,
    model_trainer,
    model_tuner
)
from ..modules.model_evaluation import (
    performance_evaluator,
    bias_checker,
    stability_tester
)
from ..modules.visualization import (
    chart_generator,
    plot_creator,
    dashboard_builder
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
)

logger = logging.getLogger(__name__)


<<<<<<< HEAD
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
=======
class AnalyticsPhase(Enum):
    """Advanced analytics processing phases"""
    DATA_PREPARATION = "data_preparation"
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_TRAINING = "model_training"
    MODEL_EVALUATION = "model_evaluation"
    VISUALIZATION = "visualization"


@dataclass
class AnalyticsContext:
    """Context for analytics processing"""
    pipeline_id: str
    staged_id: str
    current_phase: AnalyticsPhase
    data_config: Dict[str, Any]
    model_config: Dict[str, Any]
    phase_results: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class AnalyticsProcessor:
    """
    Processor for advanced analytics operations.
    Integrates directly with Staging Area for data access and storage.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        self.message_broker = message_broker
        self.staging_manager = staging_manager
        self.logger = logging.getLogger(__name__)

        # Track active analyses
        self.active_analyses: Dict[str, AnalyticsContext] = {}

    async def prepare_data(
            self,
            pipeline_id: str,
            staged_id: str,
            config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare data for analysis"""
        try:
            # Create analytics context
            context = AnalyticsContext(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                current_phase=AnalyticsPhase.DATA_PREPARATION,
                data_config=config.get('data_config', {}),
                model_config=config.get('model_config', {})
            )
            self.active_analyses[pipeline_id] = context

            # Fetch data from staging area
            staged_data = await self.staging_manager.get_staged_data(staged_id)
            if not staged_data:
                raise ValueError(f"No data found in staging for ID: {staged_id}")

            raw_data = staged_data.get('data')
            results = {}

            # Run data preparation steps
            results['cleaned_data'] = await data_cleaner.clean_data(raw_data)
            results['transformed_data'] = await data_transformer.transform_data(
                results['cleaned_data']
            )
            validation_results = await data_validator.validate_data(
                results['transformed_data']
            )

            # Store results in staging
            results_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=results,
                metadata={
                    'phase': AnalysisPhase.DATA_PREPARATION.value,
                    'pipeline_id': pipeline_id,
                    'validation_status': validation_results['status']
                }
            )

            context.phase_results['data_preparation'] = {
                'staged_id': results_staged_id,
                'validation_results': validation_results
            }

            return results

        except Exception as e:
            self.logger.error(f"Data preparation failed: {str(e)}")
            raise

    async def engineer_features(
            self,
            pipeline_id: str,
            staged_id: str,
            config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Engineer features for modeling"""
        try:
            context = self.active_analyses[pipeline_id]
            context.current_phase = AnalyticsPhase.FEATURE_ENGINEERING

            # Fetch prepared data from staging
            prepared_data = await self.staging_manager.get_staged_data(staged_id)
            if not prepared_data:
                raise ValueError("No prepared data found in staging")

            results = {}

            # Run feature engineering steps
            results['extracted_features'] = await feature_extractor.extract_features(
                prepared_data['data']
            )
            results['selected_features'] = await feature_selector.select_features(
                results['extracted_features']
            )
            results['transformed_features'] = await feature_transformer.transform_features(
                results['selected_features']
            )

            # Store results in staging
            results_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=results,
                metadata={
                    'phase': AnalysisPhase.FEATURE_ENGINEERING.value,
                    'pipeline_id': pipeline_id,
                    'feature_count': len(results['selected_features'])
                }
            )

            context.phase_results['feature_engineering'] = {
                'staged_id': results_staged_id,
                'feature_metadata': {
                    'total_features': len(results['extracted_features']),
                    'selected_features': len(results['selected_features'])
                }
            }

            return results

        except Exception as e:
            self.logger.error(f"Feature engineering failed: {str(e)}")
            raise

    async def train_model(
            self,
            pipeline_id: str,
            staged_id: str,
            config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Train analytical types"""
        try:
            context = self.active_analyses[pipeline_id]
            context.current_phase = AnalysisPhase.MODEL_TRAINING

            # Fetch engineered features from staging
            feature_data = await self.staging_manager.get_staged_data(staged_id)
            if not feature_data:
                raise ValueError("No feature data found in staging")

            results = {}

            # Run model training steps
            selected_model = await model_selector.select_model(
                feature_data['data'],
                context.model_config
            )
            trained_model = await model_trainer.train_model(
                selected_model,
                feature_data['data']
            )
            tuned_model = await model_tuner.tune_model(
                trained_model,
                feature_data['data']
            )

            results['model'] = tuned_model
            results['training_metrics'] = trained_model.get_metrics()
            results['tuning_results'] = tuned_model.get_tuning_info()

            # Store results in staging
            results_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=results,
                metadata={
                    'phase': AnalysisPhase.MODEL_TRAINING.value,
                    'pipeline_id': pipeline_id,
                    'model_type': selected_model.type,
                    'model_version': tuned_model.version
                }
            )

            context.phase_results['model_training'] = {
                'staged_id': results_staged_id,
                'model_metadata': {
                    'type': selected_model.type,
                    'version': tuned_model.version,
                    'metrics': results['training_metrics']
                }
            }

            return results

        except Exception as e:
            self.logger.error(f"Model training failed: {str(e)}")
            raise

    async def evaluate_model(
            self,
            pipeline_id: str,
            staged_id: str,
            config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate model performance"""
        try:
            context = self.active_analyses[pipeline_id]
            context.current_phase = AnalysisPhase.MODEL_EVALUATION

            # Fetch trained model from staging
            model_data = await self.staging_manager.get_staged_data(staged_id)
            if not model_data:
                raise ValueError("No model data found in staging")

            results = {}

            # Run model evaluation steps
            results['performance'] = await performance_evaluator.evaluate_model(
                model_data['data']['model']
            )
            results['bias_check'] = await bias_checker.check_model_bias(
                model_data['data']['model']
            )
            results['stability'] = await stability_tester.test_model_stability(
                model_data['data']['model']
            )

            # Store results in staging
            results_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=results,
                metadata={
                    'phase': AnalysisPhase.MODEL_EVALUATION.value,
                    'pipeline_id': pipeline_id,
                    'performance_summary': results['performance']['summary']
                }
            )

            context.phase_results['model_evaluation'] = {
                'staged_id': results_staged_id,
                'evaluation_summary': results['performance']['summary']
            }

            return results

        except Exception as e:
            self.logger.error(f"Model evaluation failed: {str(e)}")
            raise

    async def generate_visualizations(
            self,
            pipeline_id: str,
            staged_id: str,
            config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate visualizations of results"""
        try:
            context = self.active_analyses[pipeline_id]
            context.current_phase = AnalysisPhase.VISUALIZATION

            # Fetch evaluation results from staging
            eval_data = await self.staging_manager.get_staged_data(staged_id)
            if not eval_data:
                raise ValueError("No evaluation data found in staging")

            results = {}

            # Generate visualizations
            results['charts'] = await chart_generator.create_charts(
                eval_data['data']
            )
            results['plots'] = await plot_creator.create_plots(
                eval_data['data']
            )
            results['dashboard'] = await dashboard_builder.create_dashboard(
                eval_data['data']
            )

            # Store results in staging
            results_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=results,
                metadata={
                    'phase': AnalysisPhase.VISUALIZATION.value,
                    'pipeline_id': pipeline_id,
                    'visualization_types': list(results.keys())
                }
            )

            context.phase_results['visualization'] = {
                'staged_id': results_staged_id,
                'visualization_summary': {
                    'chart_count': len(results['charts']),
                    'plot_count': len(results['plots'])
                }
            }

            return results

        except Exception as e:
            self.logger.error(f"Visualization generation failed: {str(e)}")
            raise

    def get_analysis_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of analysis process"""
        context = self.active_analyses.get(pipeline_id)
        if not context:
            return None

        return {
            'pipeline_id': pipeline_id,
            'staged_id': context.staged_id,
            'current_phase': context.current_phase.value,
            'phases_completed': list(context.phase_results.keys()),
            'created_at': context.created_at.isoformat(),
            'updated_at': context.updated_at.isoformat()
        }

    async def cleanup(self) -> None:
        """Cleanup processor resources"""
        self.active_analyses.clear()
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
