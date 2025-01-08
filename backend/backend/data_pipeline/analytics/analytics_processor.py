# backend/data_pipeline/analytics/analytics_processor.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage

logger = logging.getLogger(__name__)


class AnalyticsPhase(Enum):
    """Analytics processing phases"""
    DATA_PREPARATION = "data_preparation"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    PREDICTIVE_MODELING = "predictive_modeling"
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_EVALUATION = "model_evaluation"
    VISUALIZATION = "visualization"


class AnalyticsType(Enum):
    """Types of analytics that can be performed"""
    DESCRIPTIVE = "descriptive"
    DIAGNOSTIC = "diagnostic"
    PREDICTIVE = "predictive"
    PRESCRIPTIVE = "prescriptive"
    TIME_SERIES = "time_series"
    COHORT = "cohort"
    AB_TESTING = "ab_testing"
    CLUSTERING = "clustering"


@dataclass
class AnalyticsContext:
    """Context for analytics processing"""
    pipeline_id: str
    current_phase: AnalyticsPhase
    analysis_type: AnalyticsType
    input_data: Dict[str, Any]
    parameters: Dict[str, Any]
    results: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"


@dataclass
class AnalyticsResult:
    """Results from analytics process"""
    pipeline_id: str
    analysis_type: AnalyticsType
    results: Dict[str, Any]
    metadata: Dict[str, Any]
    phase: AnalyticsPhase
    generated_at: datetime = field(default_factory=datetime.now)
    status: str = "completed"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary format"""
        return {
            'pipeline_id': self.pipeline_id,
            'analysis_type': self.analysis_type.value,
            'results': self.results,
            'metadata': self.metadata,
            'phase': self.phase.value,
            'generated_at': self.generated_at.isoformat(),
            'status': self.status,
            'error': self.error
        }


class AnalyticsProcessor:
    """
    Processes various types of analytics on data
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.logger = logging.getLogger(__name__)

        # Track active analytics processes
        self.active_processes: Dict[str, AnalyticsContext] = {}

    def start_analytics(self, pipeline_id: str, analysis_type: str,
                        data: Dict[str, Any], parameters: Dict[str, Any]) -> None:
        """Start analytics processing"""
        try:
            # Validate analytics type
            try:
                analytics_type = AnalyticsType(analysis_type.lower())
            except ValueError:
                raise ValueError(f"Invalid analytics type: {analysis_type}")

            # Create analytics context
            context = AnalyticsContext(
                pipeline_id=pipeline_id,
                current_phase=AnalyticsPhase.DATA_PREPARATION,
                analysis_type=analytics_type,
                input_data=data,
                parameters=parameters
            )

            self.active_processes[pipeline_id] = context

            # Start processing
            self._process_analytics(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to start analytics: {str(e)}")
            self._handle_analytics_error(pipeline_id, str(e))

    def _process_analytics(self, pipeline_id: str) -> None:
        """Process analytics based on type"""
        try:
            context = self.active_processes[pipeline_id]

            # Convert data to DataFrame if needed
            if not isinstance(context.input_data, pd.DataFrame):
                data_df = pd.DataFrame(context.input_data)
            else:
                data_df = context.input_data

            # Process based on analytics type
            processor = self._get_analytics_processor(context.analysis_type)
            if not processor:
                raise ValueError(f"No processor for type: {context.analysis_type}")

            # Process analytics
            self._send_status_update(pipeline_id, "Processing started")
            analytics_results = processor(data_df, context.parameters)

            # Store results
            context.results = analytics_results
            context.status = "completed"
            context.updated_at = datetime.now()

            # Notify completion
            self._notify_completion(pipeline_id)

        except Exception as e:
            self._handle_analytics_error(pipeline_id, str(e))

    def _get_analytics_processor(self, analytics_type: AnalyticsType):
        """Get appropriate analytics processor"""
        processors = {
            AnalyticsType.DESCRIPTIVE: self._process_descriptive_analytics,
            AnalyticsType.DIAGNOSTIC: self._process_diagnostic_analytics,
            AnalyticsType.PREDICTIVE: self._process_predictive_analytics,
            AnalyticsType.PRESCRIPTIVE: self._process_prescriptive_analytics,
            AnalyticsType.TIME_SERIES: self._process_time_series_analytics,
            AnalyticsType.COHORT: self._process_cohort_analytics,
            AnalyticsType.AB_TESTING: self._process_ab_testing,
            AnalyticsType.CLUSTERING: self._process_clustering_analytics
        }
        return processors.get(analytics_type)

    def _process_descriptive_analytics(self, data: pd.DataFrame,
                                       parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process descriptive analytics"""
        try:
            results = {}

            # Basic statistics
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            results['basic_stats'] = data[numeric_cols].describe().to_dict()

            # Distribution analysis
            for col in numeric_cols:
                results[f'{col}_distribution'] = {
                    'skewness': float(stats.skew(data[col].dropna())),
                    'kurtosis': float(stats.kurtosis(data[col].dropna())),
                    'histogram': np.histogram(data[col].dropna(), bins='auto')[0].tolist()
                }

            # Correlation analysis
            results['correlations'] = data[numeric_cols].corr().to_dict()

            return results

        except Exception as e:
            self.logger.error(f"Error in descriptive analytics: {str(e)}")
            raise

    def _process_diagnostic_analytics(self, data: pd.DataFrame,
                                      parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process diagnostic analytics"""
        try:
            results = {}

            # Outlier detection
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                z_scores = np.abs(stats.zscore(data[col].dropna()))
                results[f'{col}_outliers'] = {
                    'indices': list(data.index[z_scores > 3]),
                    'values': list(data[col][z_scores > 3])
                }

            # Pattern analysis
            results['patterns'] = self._analyze_patterns(data)

            # Root cause analysis
            results['root_causes'] = self._analyze_root_causes(data, parameters)

            return results

        except Exception as e:
            self.logger.error(f"Error in diagnostic analytics: {str(e)}")
            raise

    def _process_predictive_analytics(self, data: pd.DataFrame,
                                      parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process predictive analytics"""
        try:
            # Implement predictive analytics logic
            return {}

        except Exception as e:
            self.logger.error(f"Error in predictive analytics: {str(e)}")
            raise

    def _process_prescriptive_analytics(self, data: pd.DataFrame,
                                        parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process prescriptive analytics"""
        try:
            # Implement prescriptive analytics logic
            return {}

        except Exception as e:
            self.logger.error(f"Error in prescriptive analytics: {str(e)}")
            raise

    def _process_time_series_analytics(self, data: pd.DataFrame,
                                       parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process time series analytics"""
        try:
            results = {}

            # Trend analysis
            time_col = parameters.get('time_column', 'date')
            value_col = parameters.get('value_column', 'value')

            if time_col in data.columns and value_col in data.columns:
                # Convert to time series
                ts_data = data.set_index(time_col)[value_col]

                # Decompose time series
                from statsmodels.tsa.seasonal import seasonal_decompose
                decomposition = seasonal_decompose(ts_data, period=parameters.get('period', 12))

                results['decomposition'] = {
                    'trend': decomposition.trend.dropna().tolist(),
                    'seasonal': decomposition.seasonal.dropna().tolist(),
                    'residual': decomposition.resid.dropna().tolist()
                }

                # Calculate statistics
                results['statistics'] = {
                    'autocorrelation': float(ts_data.autocorr()),
                    'trend_direction': 'increasing' if ts_data.diff().mean() > 0 else 'decreasing'
                }

            return results

        except Exception as e:
            self.logger.error(f"Error in time series analytics: {str(e)}")
            raise

    def _process_cohort_analytics(self, data: pd.DataFrame,
                                  parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process cohort analytics"""
        try:
            results = {}

            cohort_column = parameters.get('cohort_column')
            metric_column = parameters.get('metric_column')

            if cohort_column and metric_column:
                # Calculate cohort metrics
                cohort_data = data.groupby(cohort_column).agg({
                    metric_column: ['mean', 'median', 'std', 'count']
                }).round(2)

                results['cohort_metrics'] = cohort_data.to_dict()

                # Calculate retention if time data available
                time_column = parameters.get('time_column')
                if time_column:
                    retention_matrix = self._calculate_retention(
                        data, cohort_column, time_column
                    )
                    results['retention'] = retention_matrix.to_dict()

            return results

        except Exception as e:
            self.logger.error(f"Error in cohort analytics: {str(e)}")
            raise

    def _process_ab_testing(self, data: pd.DataFrame,
                            parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process A/B testing analytics"""
        try:
            results = {}

            control_group = parameters.get('control_group')
            test_group = parameters.get('test_group')
            metric_column = parameters.get('metric_column')
            group_column = parameters.get('group_column')

            if all([control_group, test_group, metric_column, group_column]):
                # Split data into control and test groups
                control_data = data[data[group_column] == control_group][metric_column]
                test_data = data[data[group_column] == test_group][metric_column]

                # Perform t-test
                t_stat, p_value = stats.ttest_ind(control_data, test_data)

                results['test_results'] = {
                    'test_statistic': float(t_stat),
                    'p_value': float(p_value),
                    'significant': bool(p_value < 0.05),
                    'control_mean': float(control_data.mean()),
                    'test_mean': float(test_data.mean()),
                    'difference': float(test_data.mean() - control_data.mean()),
                    'percent_change': float((test_data.mean() - control_data.mean()) / control_data.mean() * 100)
                }

            return results

        except Exception as e:
            self.logger.error(f"Error in A/B testing analytics: {str(e)}")
            raise

    def _process_clustering_analytics(self, data: pd.DataFrame,
                                      parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process clustering analytics"""
        try:
            results = {}

            # Implement clustering analytics
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler

            # Prepare data
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            scaler = StandardScaler()
            scaled_data = scaler.fit_transform(data[numeric_cols])

            # Perform clustering
            n_clusters = parameters.get('n_clusters', 3)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(scaled_data)

            # Calculate cluster statistics
            results['clusters'] = {}
            for i in range(n_clusters):
                cluster_data = data[clusters == i]
                results['clusters'][f'cluster_{i}'] = {
                    'size': len(cluster_data),
                    'percentage': len(cluster_data) / len(data) * 100,
                    'center': dict(zip(numeric_cols, kmeans.cluster_centers_[i])),
                    'statistics': cluster_data[numeric_cols].describe().to_dict()
                }

            return results

        except Exception as e:
            self.logger.error(f"Error in clustering analytics: {str(e)}")
            raise

    def _analyze_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze patterns in data"""
        patterns = {}
        numeric_cols = data.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = data[col].dropna()
            patterns[col] = {
                'trend': self._detect_trend(series),
                'seasonality': self._detect_seasonality(series),
                'cyclicity': self._detect_cyclicity(series)
            }

        return patterns

    def _analyze_root_causes(self, data: pd.DataFrame,
                             parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze root causes"""
        causes = {}
        target = parameters.get('target_column')

        if target:
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                if col != target:
                    correlation = data[col].corr(data[target])
                    if abs(correlation) > 0.5:
                        causes[col] = {
                            'correlation': float(correlation),
                            'impact_score': float(abs(correlation))
                        }

        return causes

    def _detect_trend(self, series: pd.Series) -> str:
        """Detect trend in time series"""
        slope, _, _, _, _ = stats.linregress(range(len(series)), series)
        if slope > 0.05:
            return "increasing"
        elif slope < -0.05:
            return "decreasing"
        return "stable"

    def _detect_seasonality(self, series: pd.Series) -> Dict[str, Any]:
        """Detect seasonality in time series"""
        try:
            # Calculate autocorrelation at different lags
            autocorr = [series.autocorr(lag=i) for i in range(1, min(len(series), 13))]

            return {
                'has_seasonality': any(abs(corr) > 0.7 for corr in autocorr),
                'seasonal_lags': [i + 1 for i, corr in enumerate(autocorr) if abs(corr) > 0.7],
                'autocorrelation': autocorr
            }
        except Exception as e:
            self.logger.error(f"Error detecting seasonality: {str(e)}")
            return {'has_seasonality': False, 'seasonal_lags': [], 'autocorrelation': []}

    def _detect_cyclicity(self, series: pd.Series) -> Dict[str, Any]:
        """Detect cyclical patterns in time series"""
        try:
            from scipy import signal

            # Perform spectral analysis
            frequencies, spectrum = signal.periodogram(series.dropna())

            # Find dominant frequencies
            peak_frequencies = frequencies[signal.find_peaks(spectrum)[0]]

            return {
                'has_cycles': len(peak_frequencies) > 0,
                'cycle_lengths': [1 / f if f != 0 else float('inf') for f in peak_frequencies],
                'cycle_strengths': [spectrum[i] for i in signal.find_peaks(spectrum)[0]]
            }
        except Exception as e:
            self.logger.error(f"Error detecting cyclicity: {str(e)}")
            return {'has_cycles': False, 'cycle_lengths': [], 'cycle_strengths': []}

    def _calculate_retention(self, data: pd.DataFrame, cohort_column: str,
                             time_column: str) -> pd.DataFrame:
        """Calculate retention matrix for cohort analysis"""
        try:
            # Prepare cohort data
            cohorts = data.groupby(cohort_column).agg({
                time_column: lambda x: (x.max() - x.min()).days + 1
            }).reset_index()

            # Calculate retention for each cohort and time period
            retention_matrix = pd.pivot_table(
                data,
                values='user_id',
                index=cohort_column,
                columns=time_column,
                aggfunc='count'
            ).fillna(0)

            # Convert to percentages
            retention_matrix = retention_matrix.div(retention_matrix.iloc[:, 0], axis=0) * 100

            return retention_matrix

        except Exception as e:
            self.logger.error(f"Error calculating retention: {str(e)}")
            return pd.DataFrame()

    def _send_status_update(self, pipeline_id: str, status: str) -> None:
        """Send status update message"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        message = ProcessingMessage(
            message_type=MessageType.ANALYTICS_UPDATE,
            content={
                'pipeline_id': pipeline_id,
                'analysis_type': context.analysis_type.value,
                'phase': context.current_phase.value,
                'status': status,
                'timestamp': datetime.now().isoformat()
            }
        )

        self.message_broker.publish(message)

    def _notify_completion(self, pipeline_id: str) -> None:
        """Notify completion of analytics process"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        # Create AnalyticsResult
        result = AnalyticsResult(
            pipeline_id=pipeline_id,
            analysis_type=context.analysis_type,
            results=context.results,
            metadata=context.metadata,
            phase=context.current_phase
        )

        message = ProcessingMessage(
            message_type=MessageType.ANALYTICS_COMPLETE,
            content=result.to_dict()
        )

        self.message_broker.publish(message)
        self._cleanup_process(pipeline_id)

    def _handle_analytics_error(self, pipeline_id: str, error: str) -> None:
        """Handle analytics processing errors"""
        message = ProcessingMessage(
            message_type=MessageType.ANALYTICS_ERROR,
            content={
                'pipeline_id': pipeline_id,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
        )

        self.message_broker.publish(message)
        self._cleanup_process(pipeline_id)

    def _cleanup_process(self, pipeline_id: str) -> None:
        """Clean up analytics process resources"""
        if pipeline_id in self.active_processes:
            del self.active_processes[pipeline_id]

    def get_process_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of analytics process"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return None

        return {
            'pipeline_id': pipeline_id,
            'analysis_type': context.analysis_type.value,
            'current_phase': context.current_phase.value,
            'status': context.status,
            'has_results': bool(context.results),
            'created_at': context.created_at.isoformat(),
            'updated_at': context.updated_at.isoformat()
        }

    def __del__(self):
        """Cleanup processor resources"""
        self.active_processes.clear()