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
)

logger = logging.getLogger(__name__)


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