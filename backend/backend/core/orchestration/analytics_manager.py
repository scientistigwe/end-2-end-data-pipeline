# backend/core/managers/analytics_manager.py

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.base.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage, ProcessingStatus
from backend.core.formatters.report_formatter import ReportFormatter, ReportType

logger = logging.getLogger(__name__)


class AnalyticsPhase(Enum):
    """Analytics processing phases"""
    DATA_PREPARATION = "data_preparation"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    PREDICTIVE_MODELING = "predictive_modeling"
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_EVALUATION = "model_evaluation"
    VISUALIZATION = "visualization"
    REPORT_GENERATION = "report_generation"


@dataclass
class AnalyticsState:
    """Tracks analytics process state"""
    pipeline_id: str
    current_phase: AnalyticsPhase
    analysis_type: str
    parameters: Dict[str, Any]
    status: ProcessingStatus
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    results: Dict[str, Any] = field(default_factory=dict)
    report_config: Optional[Dict[str, Any]] = None


class AnalyticsManager(BaseManager):
    """
    Manages analytical processing and report generation
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "AnalyticsManager")
        self.report_formatter = ReportFormatter(message_broker)
        self.active_analytics: Dict[str, AnalyticsState] = {}

    def start_analytics(self, message: ProcessingMessage) -> None:
        """Entry point for analytics processing"""
        try:
            pipeline_id = message.content['pipeline_id']
            analysis_type = message.content['analysis_type']

            # Create analytics state
            analytics_state = AnalyticsState(
                pipeline_id=pipeline_id,
                current_phase=AnalyticsPhase.DATA_PREPARATION,
                analysis_type=analysis_type,
                parameters=message.content.get('parameters', {}),
                status=ProcessingStatus.PENDING,
                report_config=message.content.get('report_config', {})
            )

            self.active_analytics[pipeline_id] = analytics_state

            # Start data preparation
            self._process_data_preparation(pipeline_id, analytics_state.parameters)

        except Exception as e:
            self.logger.error(f"Failed to start analytics: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def _process_data_preparation(self, pipeline_id: str, parameters: Dict[str, Any]) -> None:
        """Process data preparation phase"""
        try:
            # Implement data preparation logic
            prepared_data = self._prepare_data(parameters)

            # Store results and move to next phase
            self._handle_phase_completion(pipeline_id, {
                'prepared_data': prepared_data
            })

        except Exception as e:
            self.logger.error(f"Error in data preparation: {str(e)}")
            self.handle_error(e, {"pipeline_id": pipeline_id})

    def _process_statistical_analysis(self, pipeline_id: str, input_data: Dict[str, Any]) -> None:
        """Process statistical analysis phase"""
        try:
            # Implement statistical analysis logic
            analysis_results = self._analyze_data(input_data)

            # Store results and move to next phase
            self._handle_phase_completion(pipeline_id, analysis_results)

        except Exception as e:
            self.logger.error(f"Error in statistical analysis: {str(e)}")
            self.handle_error(e, {"pipeline_id": pipeline_id})

    def _process_feature_engineering(self, pipeline_id: str, input_data: Dict[str, Any]) -> None:
        """Process feature engineering phase"""
        try:
            # Implement feature engineering logic
            engineered_features = self._engineer_features(input_data)

            # Store results and move to next phase
            self._handle_phase_completion(pipeline_id, engineered_features)

        except Exception as e:
            self.logger.error(f"Error in feature engineering: {str(e)}")
            self.handle_error(e, {"pipeline_id": pipeline_id})

    def _handle_phase_completion(self, pipeline_id: str, phase_results: Dict[str, Any]) -> None:
        """Handle completion of analytics phase"""
        try:
            analytics_state = self.active_analytics.get(pipeline_id)
            if not analytics_state:
                return

            # Store phase results
            analytics_state.results[analytics_state.current_phase.value] = phase_results

            # Get next phase
            next_phase = self._get_next_phase(analytics_state.current_phase)

            if next_phase:
                # Move to next phase
                analytics_state.current_phase = next_phase
                self._start_phase(pipeline_id, next_phase, phase_results)
            else:
                # Move to report generation
                analytics_state.current_phase = AnalyticsPhase.REPORT_GENERATION
                self._generate_analytics_report(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to handle phase completion: {str(e)}")
            self.handle_error(e, {"pipeline_id": pipeline_id})

    def _generate_analytics_report(self, pipeline_id: str) -> None:
        """Generate analytics report"""
        try:
            analytics_state = self.active_analytics.get(pipeline_id)
            if not analytics_state:
                return

            report_config = analytics_state.report_config or {}

            # Prepare report data
            report_data = {
                'analysis_type': analytics_state.analysis_type,
                'results': analytics_state.results,
                'metadata': {
                    'start_time': analytics_state.start_time.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'parameters': analytics_state.parameters
                }
            }

            # Format report using ReportFormatter
            self.report_formatter.format_report(
                pipeline_id=pipeline_id,
                report_type=report_config.get('type', 'analysis_summary'),
                parameters={
                    'data': report_data,
                    'format': report_config.get('format', 'json'),
                    'template': report_config.get('template'),
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to generate analytics report: {str(e)}")
            self.handle_error(e, {"pipeline_id": pipeline_id})

    def handle_report_complete(self, message: ProcessingMessage) -> None:
        """Handle report formatting completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            formatted_report = message.content.get('report_data')

            analytics_state = self.active_analytics.get(pipeline_id)
            if not analytics_state:
                return

            # Store formatted report in results
            analytics_state.results['formatted_report'] = formatted_report

            # Complete analytics process
            self._finalize_analytics(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to handle report completion: {str(e)}")
            self.handle_error(e, {"message": message.content})

    def _get_next_phase(self, current_phase: AnalyticsPhase) -> Optional[AnalyticsPhase]:
        """Determine next analytics phase"""
        phase_sequence = {
            AnalyticsPhase.DATA_PREPARATION: AnalyticsPhase.STATISTICAL_ANALYSIS,
            AnalyticsPhase.STATISTICAL_ANALYSIS: AnalyticsPhase.FEATURE_ENGINEERING,
            AnalyticsPhase.FEATURE_ENGINEERING: AnalyticsPhase.PREDICTIVE_MODELING,
            AnalyticsPhase.PREDICTIVE_MODELING: AnalyticsPhase.MODEL_EVALUATION,
            AnalyticsPhase.MODEL_EVALUATION: AnalyticsPhase.VISUALIZATION,
            AnalyticsPhase.VISUALIZATION: None
        }
        return phase_sequence.get(current_phase)

    def _start_phase(self, pipeline_id: str, phase: AnalyticsPhase,
                     previous_results: Dict[str, Any]) -> None:
        """Start specific analytics phase"""
        phase_processors = {
            AnalyticsPhase.STATISTICAL_ANALYSIS: self._process_statistical_analysis,
            AnalyticsPhase.FEATURE_ENGINEERING: self._process_feature_engineering,
            AnalyticsPhase.PREDICTIVE_MODELING: self._process_predictive_modeling,
            AnalyticsPhase.MODEL_EVALUATION: self._process_model_evaluation,
            AnalyticsPhase.VISUALIZATION: self._process_visualization
        }

        processor = phase_processors.get(phase)
        if processor:
            processor(pipeline_id, previous_results)

    def _finalize_analytics(self, pipeline_id: str) -> None:
        """Complete analytics process"""
        analytics_state = self.active_analytics.get(pipeline_id)
        if not analytics_state:
            return

        try:
            analytics_state.status = ProcessingStatus.COMPLETED
            analytics_state.end_time = datetime.now()

            # Send completion message
            self.send_message(
                MessageType.ANALYTICS_COMPLETE,
                {
                    'pipeline_id': pipeline_id,
                    'results': analytics_state.results,
                    'analysis_type': analytics_state.analysis_type,
                    'timestamp': datetime.now().isoformat()
                }
            )

            # Cleanup
            self._cleanup_analytics(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to finalize analytics: {str(e)}")
            self.handle_error(e, {"pipeline_id": pipeline_id})

    def get_analytics_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of analytics process"""
        analytics_state = self.active_analytics.get(pipeline_id)
        if not analytics_state:
            return None

        return {
            'pipeline_id': pipeline_id,
            'phase': analytics_state.current_phase.value,
            'analysis_type': analytics_state.analysis_type,
            'status': analytics_state.status.value,
            'start_time': analytics_state.start_time.isoformat(),
            'end_time': analytics_state.end_time.isoformat() if analytics_state.end_time else None,
            'results': analytics_state.results
        }

    def _cleanup_analytics(self, pipeline_id: str) -> None:
        """Clean up analytics resources"""
        if pipeline_id in self.active_analytics:
            del self.active_analytics[pipeline_id]

    def __del__(self):
        """Cleanup manager resources"""
        self.active_analytics.clear()
        super().__del__()