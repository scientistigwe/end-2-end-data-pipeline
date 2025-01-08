# backend/data_pipeline/insight/insight_processor.py

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage
from backend.data_pipeline.insight_analysis.data_quality_gauge import DataQualityGauge
from backend.data_pipeline.insight_analysis.insight_report import InsightReport

logger = logging.getLogger(__name__)


class InsightPhase(Enum):
    """Insight processing phases"""
    INITIAL_ANALYSIS = "initial_analysis"
    BUSINESS_GOAL_ANALYSIS = "business_goal_analysis"
    ADDITIONAL_INSIGHTS = "additional_insights"
    INSIGHT_VALIDATION = "insight_validation"


@dataclass
class InsightContext:
    """Context for insight processing"""
    pipeline_id: str
    current_phase: InsightPhase
    data_analysis: Dict[str, Any]  # Results from initial data analysis
    business_goals: Dict[str, Any]
    metadata: Dict[str, Any]
    initial_insights: Optional[Dict[str, Any]] = None
    business_insights: Optional[Dict[str, Any]] = None
    additional_insights: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class InsightAnalysisResult:
    """Results from insight analysis process"""
    pipeline_id: str
    initial_insights: Dict[str, Any]
    business_insights: Dict[str, Any]
    additional_insights: Dict[str, Any]
    business_goals: Dict[str, Any]
    metadata: Dict[str, Any]
    phase: InsightPhase
    generated_at: datetime = field(default_factory=datetime.now)
    status: str = "completed"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary format"""
        return {
            'pipeline_id': self.pipeline_id,
            'initial_insights': self.initial_insights,
            'business_insights': self.business_insights,
            'additional_insights': self.additional_insights,
            'business_goals': self.business_goals,
            'metadata': self.metadata,
            'phase': self.phase.value,
            'generated_at': self.generated_at.isoformat(),
            'status': self.status,
            'error': self.error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InsightAnalysisResult':
        """Create instance from dictionary"""
        return cls(
            pipeline_id=data['pipeline_id'],
            initial_insights=data.get('initial_insights', {}),
            business_insights=data.get('business_insights', {}),
            additional_insights=data.get('additional_insights', {}),
            business_goals=data.get('business_goals', {}),
            metadata=data.get('metadata', {}),
            phase=InsightPhase(data['phase']),
            generated_at=datetime.fromisoformat(data['generated_at'])
                if 'generated_at' in data else datetime.now(),
            status=data.get('status', 'completed'),
            error=data.get('error')
        )


class BusinessGoalAnalyzer:
    """Analyzes data in context of business goals"""

    def analyze_goal(self, data: pd.DataFrame, goal: Dict[str, Any]) -> Dict[str, Any]:
        goal_type = goal.get('type', '').lower()
        target_metric = goal.get('target_metric')

        if not goal_type or not target_metric:
            raise ValueError("Invalid goal configuration")

        if goal_type == 'growth':
            return self._analyze_growth(data, target_metric, goal)
        elif goal_type == 'optimization':
            return self._analyze_optimization(data, target_metric, goal)
        elif goal_type == 'efficiency':
            return self._analyze_efficiency(data, target_metric, goal)
        elif goal_type == 'comparison':
            return self._analyze_comparison(data, target_metric, goal)
        else:
            raise ValueError(f"Unsupported goal type: {goal_type}")

    def _analyze_growth(self, data: pd.DataFrame, metric: str,
                        goal: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze growth patterns in the metric"""
        try:
            target_growth = goal.get('target_value', 0)
            time_column = goal.get('time_dimension', 'date')

            # Calculate growth rates
            growth_rates = data.groupby(time_column)[metric].pct_change()
            actual_growth = growth_rates.mean() * 100

            return {
                'goal_type': 'growth',
                'metric': metric,
                'target_growth': target_growth,
                'actual_growth': actual_growth,
                'achievement_rate': (actual_growth / target_growth) * 100 if target_growth else 0,
                'trend': self._calculate_trend(growth_rates),
                'recommendations': self._generate_growth_recommendations(
                    actual_growth, target_growth, growth_rates
                )
            }
        except Exception as e:
            logger.error(f"Error in growth analysis: {str(e)}")
            return {'error': str(e)}

    def _analyze_optimization(self, data: pd.DataFrame, metric: str,
                              goal: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze optimization opportunities"""
        try:
            target_value = goal.get('target_value')
            optimization_type = goal.get('optimization_type', 'maximize')

            current_value = data[metric].mean()
            variance = data[metric].std()

            return {
                'goal_type': 'optimization',
                'metric': metric,
                'current_value': current_value,
                'target_value': target_value,
                'gap': abs(target_value - current_value) if target_value else None,
                'variance': variance,
                'optimization_opportunities': self._identify_optimization_opportunities(
                    data, metric, optimization_type
                )
            }
        except Exception as e:
            logger.error(f"Error in optimization analysis: {str(e)}")
            return {'error': str(e)}

    def _analyze_efficiency(self, data: pd.DataFrame, metric: str,
                            goal: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze efficiency metrics"""
        try:
            baseline = goal.get('baseline', 0)
            input_metric = goal.get('input_metric')
            output_metric = goal.get('output_metric')

            if input_metric and output_metric:
                efficiency_ratio = data[output_metric] / data[input_metric]

                return {
                    'goal_type': 'efficiency',
                    'metric': metric,
                    'current_efficiency': efficiency_ratio.mean(),
                    'baseline': baseline,
                    'improvement': ((efficiency_ratio.mean() - baseline) / baseline) * 100,
                    'efficiency_distribution': self._analyze_efficiency_distribution(
                        efficiency_ratio
                    )
                }
            else:
                raise ValueError("Missing input/output metrics for efficiency analysis")
        except Exception as e:
            logger.error(f"Error in efficiency analysis: {str(e)}")
            return {'error': str(e)}

    def _analyze_comparison(self, data: pd.DataFrame, metric: str,
                            goal: Dict[str, Any]) -> Dict[str, Any]:
        """Compare metric across different segments"""
        try:
            segment_column = goal.get('segment_column')
            baseline_segment = goal.get('baseline_segment')

            if not segment_column or not baseline_segment:
                raise ValueError("Missing segment information for comparison")

            segment_stats = data.groupby(segment_column)[metric].agg(['mean', 'std'])
            baseline_value = segment_stats.loc[baseline_segment, 'mean']

            comparisons = {}
            for segment in segment_stats.index:
                if segment != baseline_segment:
                    diff_pct = ((segment_stats.loc[segment, 'mean'] - baseline_value)
                                / baseline_value * 100)
                    comparisons[segment] = {
                        'difference_pct': diff_pct,
                        'is_significant': self._check_significance(
                            data[data[segment_column] == baseline_segment][metric],
                            data[data[segment_column] == segment][metric]
                        )
                    }

            return {
                'goal_type': 'comparison',
                'metric': metric,
                'baseline_segment': baseline_segment,
                'baseline_value': baseline_value,
                'comparisons': comparisons
            }
        except Exception as e:
            logger.error(f"Error in comparison analysis: {str(e)}")
            return {'error': str(e)}

    def _calculate_trend(self, series: pd.Series) -> str:
        slope, _, _, _, _ = stats.linregress(range(len(series)), series)
        if slope > 0.05:
            return "increasing"
        elif slope < -0.05:
            return "decreasing"
        return "stable"

    def _identify_optimization_opportunities(self, data: pd.DataFrame,
                                             metric: str,
                                             optimization_type: str) -> List[Dict[str, Any]]:
        opportunities = []
        # Implement optimization opportunity identification
        return opportunities

    def _analyze_efficiency_distribution(self, efficiency_ratio: pd.Series) -> Dict[str, Any]:
        return {
            'mean': efficiency_ratio.mean(),
            'median': efficiency_ratio.median(),
            'std': efficiency_ratio.std(),
            'quartiles': efficiency_ratio.quantile([0.25, 0.75]).to_dict()
        }

    def _check_significance(self, baseline_data: pd.Series,
                            comparison_data: pd.Series) -> bool:
        _, p_value = stats.ttest_ind(baseline_data, comparison_data)
        return p_value < 0.05


class AdditionalInsightGenerator:
    """Generates additional insights beyond business goals"""

    def generate_insights(self, data: pd.DataFrame,
                          existing_insights: Dict[str, Any]) -> Dict[str, Any]:
        insights = {}

        # Anomaly Detection
        insights['anomalies'] = self._detect_anomalies(data)

        # Pattern Recognition
        insights['patterns'] = self._identify_patterns(data)

        # Correlation Analysis
        insights['correlations'] = self._analyze_correlations(data)

        # Time-based Analysis (if applicable)
        if self._has_time_dimension(data):
            insights['temporal_insights'] = self._analyze_temporal_patterns(data)

        return insights

    def _detect_anomalies(self, data: pd.DataFrame) -> Dict[str, Any]:
        anomalies = {}
        for column in data.select_dtypes(include=[np.number]).columns:
            series = data[column]
            z_scores = np.abs(stats.zscore(series.dropna()))
            anomalies[column] = {
                'count': sum(z_scores > 3),
                'indices': series.index[z_scores > 3].tolist(),
                'values': series[z_scores > 3].tolist()
            }
        return anomalies

    def _identify_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        patterns = {}
        numeric_columns = data.select_dtypes(include=[np.number]).columns

        for column in numeric_columns:
            series = data[column].dropna()
            patterns[column] = {
                'trend': self._detect_trend(series),
                'seasonality': self._detect_seasonality(series),
                'distribution': self._analyze_distribution(series)
            }
        return patterns

    def _analyze_correlations(self, data: pd.DataFrame) -> Dict[str, Any]:
        numeric_data = data.select_dtypes(include=[np.number])
        correlations = numeric_data.corr()

        strong_correlations = []
        for i in range(len(correlations.columns)):
            for j in range(i):
                if abs(correlations.iloc[i, j]) > 0.7:
                    strong_correlations.append({
                        'variables': (correlations.columns[i], correlations.columns[j]),
                        'correlation': correlations.iloc[i, j]
                    })

        return {
            'strong_correlations': strong_correlations,
            'correlation_matrix': correlations.to_dict()
        }

    def _has_time_dimension(self, data: pd.DataFrame) -> bool:
        return any(data[col].dtype.kind in 'M' for col in data.columns)

    def _analyze_temporal_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        temporal_insights = {}
        date_columns = [col for col in data.columns if data[col].dtype.kind in 'M']

        for date_col in date_columns:
            temporal_insights[date_col] = {
                'periodicity': self._detect_periodicity(data[date_col]),
                'gaps': self._detect_time_gaps(data[date_col]),
                'trends': self._analyze_time_trends(data, date_col)
            }

        return temporal_insights

    def _detect_trend(self, series: pd.Series) -> str:
        slope, _, _, _, _ = stats.linregress(range(len(series)), series)
        return "increasing" if slope > 0.05 else "decreasing" if slope < -0.05 else "stable"

    def _detect_seasonality(self, series: pd.Series) -> Dict[str, Any]:
        # Implement seasonality detection
        return {}

    def _analyze_distribution(self, series: pd.Series) -> Dict[str, Any]:
        return {
            'skewness': series.skew(),
            'kurtosis': series.kurtosis(),
            'distribution_type': self._determine_distribution_type(series)
        }

    def _determine_distribution_type(self, series: pd.Series) -> str:
        # Implement distribution type detection
        return "unknown"

    def _detect_periodicity(self, date_series: pd.Series) -> Dict[str, Any]:
        # Implement periodicity detection
        return {}

    def _detect_time_gaps(self, date_series: pd.Series) -> List[Dict[str, Any]]:
        # Implement time gap detection
        return []

    def _analyze_time_trends(self, data: pd.DataFrame,
                             date_column: str) -> Dict[str, Any]:
        # Implement time trend analysis
        return {}


class InsightProcessor:
    """
    Enhanced insight processor with business goal analysis
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.logger = logging.getLogger(__name__)

        # Track insight processes
        self.active_processes: Dict[str, InsightContext] = {}

        # Initialize components
        self.quality_gauge = DataQualityGauge()
        self.insight_report = InsightReport()
        self.business_analyzer = BusinessGoalAnalyzer()
        self.additional_generator = AdditionalInsightGenerator()

    def start_insight_process(self, pipeline_id: str,
                              data_analysis: Dict[str, Any],
                              business_goals: Dict[str, Any],
                              metadata: Dict[str, Any]) -> None:
        """Start insight processing"""
        try:
            insight_context = InsightContext(
                pipeline_id=pipeline_id,
                current_phase=InsightPhase.INITIAL_ANALYSIS,
                data_analysis=data_analysis,
                business_goals=business_goals,
                metadata=metadata
            )

            self.active_processes[pipeline_id] = insight_context

            # Start with initial analysis
            self._process_initial_analysis(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to start insight process: {str(e)}")
            self._handle_insight_error(pipeline_id, "startup", str(e))

    def _process_initial_analysis(self, pipeline_id: str) -> None:
        """Process initial data analysis results"""
        try:
            context = self.active_processes[pipeline_id]

            # Convert analysis results to DataFrame if needed
            data = pd.DataFrame(context.data_analysis.get('data', {}))

            # Generate initial insights
            context.initial_insights = self.insight_report.generate_insight(
                data, "summary"
            )

            context.current_phase = InsightPhase.BUSINESS_GOAL_ANALYSIS
            context.updated_at = datetime.now()

            self._send_phase_update(
                pipeline_id,
                "Initial analysis completed",
                {'has_initial_insights': True}
            )

            # Move to business goal analysis
            self._analyze_business_goals(pipeline_id)

        except Exception as e:
            self._handle

    def _analyze_business_goals(self, pipeline_id: str) -> None:
        """Analyze data against business goals"""
        try:
            context = self.active_processes[pipeline_id]
            data = pd.DataFrame(context.data_analysis.get('data', {}))

            business_insights = {}
            for goal_name, goal_config in context.business_goals.items():
                business_insights[goal_name] = self.business_analyzer.analyze_goal(
                    data, goal_config
                )

            context.business_insights = business_insights
            context.current_phase = InsightPhase.ADDITIONAL_INSIGHTS
            context.updated_at = datetime.now()

            self._send_phase_update(
                pipeline_id,
                "Business goal analysis completed",
                {'goals_analyzed': len(business_insights)}
            )

            # Move to additional insights
            self._generate_additional_insights(pipeline_id)

        except Exception as e:
            self._handle_insight_error(pipeline_id, "business_goal_analysis", str(e))


    def _generate_additional_insights(self, pipeline_id: str) -> None:
        """Generate additional insights beyond business goals"""
        try:
            context = self.active_processes[pipeline_id]
            data = pd.DataFrame(context.data_analysis.get('data', {}))

            # Generate additional insights
            context.additional_insights = self.additional_generator.generate_insights(
                data,
                {
                    'initial': context.initial_insights,
                    'business': context.business_insights
                }
            )

            context.current_phase = InsightPhase.INSIGHT_VALIDATION
            context.updated_at = datetime.now()

            self._send_phase_update(
                pipeline_id,
                "Additional insights generated",
                {'insight_types': list(context.additional_insights.keys())}
            )

            # Move to validation
            self._validate_insights(pipeline_id)

        except Exception as e:
            self._handle_insight_error(pipeline_id, "additional_insights", str(e))


    def _validate_insights(self, pipeline_id: str) -> None:
        """Validate all generated insights"""
        try:
            context = self.active_processes[pipeline_id]

            # Validate each type of insight
            validation_results = {
                'initial_insights': self._validate_initial_insights(context.initial_insights),
                'business_insights': self._validate_business_insights(
                    context.business_insights,
                    context.business_goals
                ),
                'additional_insights': self._validate_additional_insights(context.additional_insights)
            }

            # Check overall validation
            if all(result['is_valid'] for result in validation_results.values()):
                # Notify completion
                self._notify_completion(pipeline_id)
            else:
                issues = []
                for insight_type, result in validation_results.items():
                    if not result['is_valid']:
                        issues.extend(f"{insight_type}: {issue}" for issue in result['issues'])
                raise ValueError(f"Insight validation failed: {'; '.join(issues)}")

        except Exception as e:
            self._handle_insight_error(pipeline_id, "insight_validation", str(e))


    def _validate_initial_insights(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """Validate initial insights"""
        validation = {'is_valid': True, 'issues': []}

        if not insights:
            validation['is_valid'] = False
            validation['issues'].append("No initial insights generated")
            return validation

        # Add specific validation logic for initial insights
        return validation


    def _validate_business_insights(self, insights: Dict[str, Any],
                                    goals: Dict[str, Any]) -> Dict[str, Any]:
        """Validate business goal-related insights"""
        validation = {'is_valid': True, 'issues': []}

        if not insights:
            validation['is_valid'] = False
            validation['issues'].append("No business insights generated")
            return validation

        # Check coverage of business goals
        for goal in goals:
            if goal not in insights:
                validation['is_valid'] = False
                validation['issues'].append(f"Missing insights for goal: {goal}")
            elif 'error' in insights[goal]:
                validation['is_valid'] = False
                validation['issues'].append(f"Error in {goal} insights: {insights[goal]['error']}")

        return validation


    def _validate_additional_insights(self, insights: Dict[str, Any]) -> Dict[str, Any]:
        """Validate additional insights"""
        validation = {'is_valid': True, 'issues': []}

        if not insights:
            validation['is_valid'] = False
            validation['issues'].append("No additional insights generated")
            return validation

        expected_types = {'anomalies', 'patterns', 'correlations'}
        missing_types = expected_types - set(insights.keys())

        if missing_types:
            validation['is_valid'] = False
            validation['issues'].append(f"Missing insight types: {missing_types}")

        return validation


    def _send_phase_update(self, pipeline_id: str, status: str,
                           details: Dict[str, Any]) -> None:
        """Send phase update message"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        message = ProcessingMessage(
            message_type=MessageType.INSIGHT_UPDATE,
            content={
                'pipeline_id': pipeline_id,
                'phase': context.current_phase.value,
                'status': status,
                'details': details,
                'timestamp': datetime.now().isoformat()
            }
        )

        self.message_broker.publish(message)

    def _notify_completion(self, pipeline_id: str) -> None:
        """Notify completion of insight process"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        # Create InsightAnalysisResult
        result = InsightAnalysisResult(
            pipeline_id=pipeline_id,
            initial_insights=context.initial_insights or {},
            business_insights=context.business_insights or {},
            additional_insights=context.additional_insights or {},
            business_goals=context.business_goals,
            metadata=context.metadata,
            phase=context.current_phase
        )

        message = ProcessingMessage(
            message_type=MessageType.INSIGHT_COMPLETE,
            content=result.to_dict()
        )

        self.message_broker.publish(message)
        self._cleanup_process(pipeline_id)

    def _handle_insight_error(self, pipeline_id: str, phase: str,
                              error: str) -> None:
        """Handle errors in insight processing"""
        message = ProcessingMessage(
            message_type=MessageType.INSIGHT_ERROR,
            content={
                'pipeline_id': pipeline_id,
                'phase': phase,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
        )

        self.message_broker.publish(message)
        self._cleanup_process(pipeline_id)


    def _cleanup_process(self, pipeline_id: str) -> None:
        """Clean up process resources"""
        if pipeline_id in self.active_processes:
            del self.active_processes[pipeline_id]


    def get_process_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of insight process"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return None

        return {
            'pipeline_id': pipeline_id,
            'phase': context.current_phase.value,
            'has_initial_insights': bool(context.initial_insights),
            'has_business_insights': bool(context.business_insights),
            'has_additional_insights': bool(context.additional_insights),
            'created_at': context.created_at.isoformat(),
            'updated_at': context.updated_at.isoformat(),
            'business_goals': list(context.business_goals.keys())
        }


    def __del__(self):
        """Cleanup processor resources"""
        self.active_processes.clear()