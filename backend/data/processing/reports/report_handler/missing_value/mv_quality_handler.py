"""
Missing Value Quality Handler
----------------------------
A comprehensive system for coordinating missing value detection, analysis, and resolution
while providing detailed reporting capabilities. Acts as both a communication coordinator
with the processing handler and a reporting engine.

Features:
- Full communication pipeline with orchestrator
- User decision integration points
- Detailed stage-by-stage reporting
- Colored console output for analysis
- Process statistics and metrics
- Trigger-based resolution mapping

Flow:
1. Detection: Identifies missing values and their patterns
2. Analysis: Determines mechanisms and generates recommendations
3. User Decision: Presents recommendations and awaits approval
4. Resolution: Executes approved resolution strategies
5. Reporting: Generates comprehensive reports at each stage

The handler maintains state throughout the process and provides detailed reporting
while facilitating communication between the orchestrator and quality components.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import pandas as pd
from datetime import datetime
from colorama import init, Fore, Back, Style

from backend.core.messaging.types import MessageType, ProcessingMessage
from backend.data_pipeline.quality_analysis.data_issue_detector.basic_data_validation.detect_missing_value import (
    MissingValueDetector, DetectionResult
)
from backend.data_pipeline.quality_analysis.data_issue_analyser.basic_data_validation.analyse_missing_value import (
    MissingValueAnalyzer, AnalysisResult, MissingValuePattern
)
from backend.data_pipeline.quality_analysis.data_issue_resolver.basic_data_validation.resolved_missing_value import (
    MissingValueResolver, ResolutionCommand, ResolutionResult, ResolutionStrategy
)
from .missing_value_handler import (
    MissingValueReportHandler, StageReport, ProcessSummary
)

logger = logging.getLogger(__name__)
init(autoreset=True)


class QualityPhase(Enum):
    """Phases of the quality check process"""
    DETECTION = "detection"
    ANALYSIS = "analysis"
    RESOLUTION = "resolution"
    COMPLETE = "complete"


@dataclass
class QualityDecision:
    """User decision for quality resolution"""
    field_name: str
    issue_type: str
    action: str
    approved: bool
    custom_params: Optional[Dict[str, Any]] = None


class TriggerPoint(Enum):
    """
    Strict mapping between user decisions and resolution methods.
    Each trigger corresponds to exactly one resolution method.
    """
    # Numeric data patterns
    RANDOM_BALANCED = ("impute_mean", "mean_imputation")  # For balanced distributions
    RANDOM_SKEWED = ("impute_median", "median_imputation")  # For skewed data
    OUTLIERS_PRESENT = ("robust_imputation", "robust_imputation")  # For data with outliers

    # Temporal patterns
    SIMPLE_TEMPORAL = ("interpolation", "interpolation")  # For simple gaps
    COMPLEX_TEMPORAL = ("time_interpolation", "time_interpolation")  # For time series
    IRREGULAR_TEMPORAL = ("moving_average", "moving_average_imputation")  # For irregular gaps

    # Structural patterns
    RELATED_COLUMNS = ("conditional_imputation", "conditional_imputation")  # For correlated data
    CLUSTERED_PATTERN = ("knn_imputation", "knn_imputation")  # For clustered data

    # Partial patterns
    PARTIAL_MISSING = ("partial_imputation", "hybrid_imputation")  # For partial segments

    # Advanced patterns
    COMPLEX_PATTERN = ("advanced_imputation", "advanced_imputation")  # For complex cases
    MIXED_PATTERN = ("hybrid_imputation", "hybrid_imputation")  # For mixed patterns

    # Categorical patterns
    RARE_CATEGORIES = ("group_rare", "group_rare_categories")  # For rare categories
    MEANINGFUL_MISSING = ("create_missing_category", "create_missing_category")  # For meaningful NAs

    # Special cases
    COMPLETE_MISSING = ("complete_missingness", "complete_missingness")  # For empty columns

    def __init__(self, action: str, method: str):
        self.action = action  # User-facing action name
        self.method = method  # Corresponding resolver method


class MissingValueQualityHandler:
    """
    Coordinates quality analysis pipeline with reporting capabilities.
    Serves as both a communication coordinator and reporting engine.
    """

    def __init__(self, message_broker):
        self.message_broker = message_broker

        # Initialize components
        self.report_handler = MissingValueReportHandler()
        self.detector = MissingValueDetector()
        self.analyzer = MissingValueAnalyzer()
        self.resolver = MissingValueResolver()

        # Track active processes
        self.active_processes: Dict[str, Dict[str, Any]] = {}

    def initiate_quality_check(self, pipeline_id: str, data: pd.DataFrame) -> None:
        """
        Start the quality check process with integrated reporting.

        Args:
            pipeline_id: Unique identifier for the pipeline
            data: DataFrame to analyze

        Triggers:
            - Detection phase
            - Analysis phase (if issues found)
            - Quality updates to processing handler
        """
        try:
            logger.info(f"Initiating quality check for pipeline {pipeline_id}")

            # Initialize process tracking
            self.active_processes[pipeline_id] = {
                'data': data,
                'phase': QualityPhase.DETECTION,
                'start_time': datetime.now(),
                'reports': {},
                'pending_actions': []
            }

            # Run detection with reporting
            detection_report = self.report_handler._run_detection_stage(data)
            self.active_processes[pipeline_id]['reports']['detection'] = detection_report

            # Notify processing handler
            self._send_quality_update(
                pipeline_id,
                QualityPhase.DETECTION,
                {
                    'report': detection_report,
                    'has_issues': bool(detection_report.results.get('detected_items'))
                }
            )

            if detection_report.success and detection_report.results.get('detected_items'):
                self._proceed_to_analysis(pipeline_id)
            else:
                self._complete_quality_check(pipeline_id)

        except Exception as e:
            logger.error(f"Quality check initiation failed: {str(e)}")
            self._send_quality_error(pipeline_id, str(e), QualityPhase.DETECTION)

    def _proceed_to_analysis(self, pipeline_id: str) -> None:
        """
        Proceed to analysis phase with reporting.

        Args:
            pipeline_id: Unique identifier for the pipeline
        """
        try:
            logger.info(f"Proceeding to analysis phase for pipeline {pipeline_id}")
            process = self.active_processes[pipeline_id]
            process['phase'] = QualityPhase.ANALYSIS

            # Run analysis with reporting
            analysis_report = self.report_handler._run_analysis_stage(
                process['data'],
                process['reports']['detection'].results
            )
            process['reports']['analysis'] = analysis_report

            # Generate pending actions
            pending_actions = self._generate_pending_actions(analysis_report.results)
            process['pending_actions'] = pending_actions

            # Notify processing handler
            self._send_quality_update(
                pipeline_id,
                QualityPhase.ANALYSIS,
                {
                    'report': analysis_report,
                    'pending_actions': pending_actions
                }
            )

        except Exception as e:
            logger.error(f"Analysis phase failed: {str(e)}")
            self._send_quality_error(pipeline_id, str(e), QualityPhase.ANALYSIS)

    def _create_resolution_commands(self,
                                    decisions: List[QualityDecision]) -> List[ResolutionCommand]:
        """
        Create resolution commands from user decisions.

        Args:
            decisions: List of user decisions

        Returns:
            List of resolution commands for approved decisions
        """
        commands = []
        for decision in decisions:
            if decision.approved:
                strategy = self._get_resolution_strategy(decision)
                if strategy:
                    commands.append(
                        ResolutionCommand(
                            field_name=decision.field_name,
                            approved=True,
                            selected_strategy=strategy,
                            custom_params=decision.custom_params
                        )
                    )
        return commands

    def _get_resolution_strategy(self, decision: QualityDecision) -> Optional[ResolutionStrategy]:
        """
        Get the specific resolution strategy based on user decision.
        Ensures only the chosen method is triggered.

        Args:
            decision: User decision containing action

        Returns:
            Corresponding resolution strategy or None if not found

        Logs:
            - Selected resolution method
            - Any mapping failures
        """
        try:
            # Find matching trigger point
            trigger = next(
                (t for t in TriggerPoint
                 if t.action == decision.action),
                None
            )

            if trigger is None:
                logger.warning(f"No trigger point found for action: {decision.action}")
                return None

            # Get the specific strategy
            strategy_name = trigger.method
            strategy = self.resolver.strategy_registry.get(strategy_name)

            if strategy:
                logger.info(
                    f"Mapped action '{decision.action}' to resolution method '{strategy_name}' "
                    f"for field '{decision.field_name}'"
                )
            else:
                logger.error(f"Strategy not found for method: {strategy_name}")

            return strategy

        except Exception as e:
            logger.error(f"Error getting resolution strategy: {str(e)}")
            return None

    def process_user_decisions(self, pipeline_id: str, decisions: List[QualityDecision]) -> None:
        """
        Process user decisions, ensuring only approved methods are triggered.
        """
        try:
            process = self.active_processes.get(pipeline_id)
            if not process:
                raise ValueError(f"No active process found for pipeline {pipeline_id}")

            # Track which fields were processed with which methods
            processed_fields = {}
            resolution_commands = []

            for decision in decisions:
                if decision.approved:
                    strategy = self._get_resolution_strategy(decision)
                    if strategy:
                        if decision.field_name in processed_fields:
                            logger.warning(
                                f"Field '{decision.field_name}' already processed with "
                                f"method '{processed_fields[decision.field_name]}'"
                            )
                            continue

                        resolution_commands.append(
                            ResolutionCommand(
                                field_name=decision.field_name,
                                approved=True,
                                selected_strategy=strategy,
                                custom_params=decision.custom_params
                            )
                        )
                        processed_fields[decision.field_name] = strategy.method

                        logger.info(
                            f"Created resolution command for field '{decision.field_name}' "
                            f"using method '{strategy.method}'"
                        )

            if resolution_commands:
                self._execute_resolution(pipeline_id, resolution_commands)
            else:
                logger.info("No approved resolution commands to execute")
                self._complete_quality_check(pipeline_id)

        except Exception as e:
            logger.error(f"Processing user decisions failed: {str(e)}")
            self._send_quality_error(pipeline_id, str(e), QualityPhase.RESOLUTION)

    def _generate_pending_actions(self,
                                  analysis_results: Dict[str, AnalysisResult]) -> List[Dict[str, Any]]:
        """
        Generate list of pending actions requiring user decisions.

        Args:
            analysis_results: Results from analysis phase

        Returns:
            List of pending actions with recommendations
        """
        pending_actions = []

        for field_name, analysis in analysis_results.items():
            pending_actions.append({
                'field_name': field_name,
                'issue_type': 'missing_value',
                'pattern': analysis.pattern.value,
                'mechanism': analysis.mechanism.value,
                'recommendation': analysis.recommendation,
                'missing_count': analysis.missing_count,
                'missing_percentage': analysis.missing_percentage,
                'total_count': analysis.total_count
            })

        return pending_actions

    def _print_stage_reports(self, reports: Dict[str, StageReport],
                             summary: ProcessSummary) -> None:
        """
        Print all stage reports and final summary.

        Args:
            reports: Dictionary of stage reports
            summary: Final process summary
        """
        self.report_handler._print_detection_report(reports['detection'])
        self.report_handler._print_analysis_report(reports['analysis'])
        self.report_handler._print_resolution_report(reports['resolution'])
        self.report_handler._print_process_summary(summary)

    def _complete_quality_check(self, pipeline_id: str) -> None:
        """
        Complete the quality check process with final reporting.

        Args:
            pipeline_id: Unique identifier for the pipeline

        Triggers:
            - Final quality update to processing handler
            - Process cleanup
        """
        try:
            logger.info(f"Completing quality check for pipeline {pipeline_id}")
            process = self.active_processes[pipeline_id]
            process['end_time'] = datetime.now()

            # Generate final summary if we have all reports
            if all(k in process['reports'] for k in ['detection', 'analysis', 'resolution']):
                summary = self.report_handler._create_process_summary(
                    data=process['data'],
                    resolved_data=process['data'],
                    total_fields=len(process['data'].columns),
                    stage_reports=process['reports']
                )
            else:
                summary = None

            # Notify processing handler
            self._send_quality_update(
                pipeline_id,
                QualityPhase.COMPLETE,
                {
                    'final_data': process['data'],
                    'summary': summary
                }
            )

            # Cleanup
            del self.active_processes[pipeline_id]

        except Exception as e:
            logger.error(f"Quality check completion failed: {str(e)}")
            self._send_quality_error(pipeline_id, str(e), QualityPhase.COMPLETE)

    def _send_quality_update(self, pipeline_id: str, phase: QualityPhase,
                             content: Dict[str, Any]) -> None:
        """
        Send quality update to processing handler.

        Args:
            pipeline_id: Unique identifier for the pipeline
            phase: Current quality phase
            content: Update content including reports
        """
        try:
            message = {
                'pipeline_id': pipeline_id,
                'phase': phase.value,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }

            self.message_broker.publish(
                MessageType.QUALITY_UPDATE,
                message
            )

            logger.info(f"Sent quality update for pipeline {pipeline_id} phase {phase.value}")
        except Exception as e:
            logger.error(f"Failed to send quality update: {str(e)}")

    def _send_quality_error(self, pipeline_id: str, error: str,
                            phase: QualityPhase) -> None:
        """
        Send error notification to processing handler.

        Args:
            pipeline_id: Unique identifier for the pipeline
            error: Error message
            phase: Phase where error occurred
        """
        try:
            message = {
                'pipeline_id': pipeline_id,
                'phase': phase.value,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }

            self.message_broker.publish(
                MessageType.QUALITY_ERROR,
                message
            )

            logger.error(f"Sent quality error for pipeline {pipeline_id}: {error}")
        except Exception as e:
            logger.error(f"Failed to send quality error: {str(e)}")

    def get_process_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of quality process.

        Args:
            pipeline_id: Unique identifier for the pipeline

        Returns:
            Dictionary with current process status or None if not found
        """
        process = self.active_processes.get(pipeline_id)
        if not process:
            return None

        return {
            'pipeline_id': pipeline_id,
            'phase': process['phase'].value,
            'start_time': process['start_time'].isoformat(),
            'end_time': process.get('end_time', '').isoformat() if process.get('end_time') else None,
            'has_detection': 'detection' in process['reports'],
            'has_analysis': 'analysis' in process['reports'],
            'has_resolution': 'resolution' in process['reports'],
            'pending_actions_count': len(process.get('pending_actions', [])),
            'data_shape': process['data'].shape
        }