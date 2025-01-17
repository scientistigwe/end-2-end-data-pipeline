"""
Enhanced Missing Value Resolution System Using Strategy Pattern
----------------------------------------------------------
A comprehensive system for resolving missing values using a clean strategy pattern implementation.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer, KNNImputer
import logging

from ...analyzers.basic_data_validation.analyse_missing_value import AnalysisResult

logger = logging.getLogger(__name__)

@dataclass
class ResolutionStrategy:
    """Defines a specific strategy for handling missing values"""
    method: str
    params: Dict[str, Any]
    confidence: float
    reason: str
    requirements: List[str]
    description: str  # User-friendly description


@dataclass
class ResolutionCommand:
    """User's decision for resolving missing values"""
    field_name: str
    approved: bool  # Whether to proceed with resolution
    selected_strategy: ResolutionStrategy
    custom_params: Dict[str, Any] = None


@dataclass
class ResolutionResult:
    """Results of applying a resolution strategy"""
    field_name: str
    strategy_used: ResolutionStrategy
    original_missing: int
    resolved_missing: int
    success: bool
    metrics: Dict[str, float]
    validation_results: Dict[str, bool]
    error_message: Optional[str] = None


class ResolutionMethod(Enum):
    """Available resolution methods aligned with analyzer recommendations"""
    # Basic imputation methods
    MEAN = "mean_imputation"  # For balanced distributions
    MEDIAN = "median_imputation"  # For skewed distributions
    MODE = "mode_imputation"  # For categorical with clear modes
    ROBUST = "robust_imputation"  # For data with outliers

    # Temporal methods
    INTERPOLATION = "interpolation"  # For simple temporal patterns
    TIME_INTERPOLATION = "time_interpolation"  # For complex temporal patterns
    MOVING_AVERAGE = "moving_average"  # For irregular intervals

    # Structural methods
    CONDITIONAL = "conditional_imputation"  # For related columns
    KNN = "knn_imputation"  # For clustered patterns

    # Advanced methods
    ADVANCED = "advanced_imputation"  # For complex patterns
    HYBRID = "hybrid_imputation"  # For mixed patterns

    # Categorical methods
    GROUP_RARE = "group_rare"  # For many rare categories
    CREATE_MISSING_CATEGORY = "create_missing_category"  # For meaningful missing

    # Complete missing
    COMPLETE_MISSINGNESS = "complete_missingness"  # For completely missing columns


@dataclass
class ResolutionParams:
    """Base parameters for resolution strategies"""
    field_name: str
    confidence: float = 0.5
    requirements: List[str] = None
    custom_params: Dict[str, Any] = None


class MissingValueResolver:
    """
    Resolves missing values based on analysis results and user decisions.
    """

    def __init__(self):
        self.strategy_registry = self._build_strategy_registry()
        self._setup_resolution_methods()

    def _build_strategy_registry(self) -> Dict[str, ResolutionStrategy]:
        """Build registry mapping analyzer recommendations to resolution strategies"""
        return {
            # Basic imputation strategies
            'impute_mean': ResolutionStrategy(
                method=ResolutionMethod.MEAN.value,
                params={"strategy": "mean"},
                confidence=0.8,
                reason="Suitable for numeric data with balanced distribution",
                requirements=["numeric"],
                description="Fill missing values with mean"
            ),
            "impute_median": ResolutionStrategy(
                method=ResolutionMethod.MEDIAN.value,
                params={"strategy": "median"},
                confidence=0.9,
                reason="Suitable for skewed numeric distributions",
                requirements=["numeric"],
                description="Fill missing values with median"
            ),
            "impute_mode": ResolutionStrategy(
                method=ResolutionMethod.MODE.value,
                params={"strategy": "most_frequent"},
                confidence=0.8,
                reason="Suitable for categorical data with dominant values",
                requirements=["categorical"],
                description="Fill missing values with mode"
            ),

            # Robust methods
            "robust_imputation": ResolutionStrategy(
                method=ResolutionMethod.ROBUST.value,
                params={"trim_ratio": 0.1},
                confidence=0.85,
                reason="Handles outliers and extreme values",
                requirements=["numeric"],
                description="Impute using robust statistics"
            ),

            # Temporal strategies
            "simple_interpolation": ResolutionStrategy(
                method=ResolutionMethod.INTERPOLATION.value,
                params={"method": "linear"},
                confidence=0.85,
                reason="For simple temporal gaps",
                requirements=["numeric"],
                description="Linear interpolation for gaps"
            ),
            "time_interpolation": ResolutionStrategy(
                method=ResolutionMethod.TIME_INTERPOLATION.value,
                params={"method": "time"},
                confidence=0.9,
                reason="For complex temporal patterns",
                requirements=["numeric", "time_series"],
                description="Time-based interpolation"
            ),
            "moving_average": ResolutionStrategy(
                method=ResolutionMethod.MOVING_AVERAGE.value,
                params={"window": "auto"},
                confidence=0.8,
                reason="For irregular temporal gaps",
                requirements=["numeric", "time_series"],
                description="Moving average imputation"
            ),

            # Structural strategies
            "conditional_imputation": ResolutionStrategy(
                method=ResolutionMethod.CONDITIONAL.value,
                params={},
                confidence=0.85,
                reason="Uses relationships between columns",
                requirements=["numeric"],
                description="Conditional imputation using related columns"
            ),
            "knn_imputation": ResolutionStrategy(
                method=ResolutionMethod.KNN.value,
                params={"n_neighbors": 5},
                confidence=0.8,
                reason="For clustered missing patterns",
                requirements=["numeric"],
                description="KNN-based imputation"
            ),

            # Advanced methods
            "advanced_imputation": ResolutionStrategy(
                method=ResolutionMethod.ADVANCED.value,
                params={"methods": ["interpolate", "knn", "mean"]},
                confidence=0.9,
                reason="For complex missing patterns",
                requirements=["numeric"],
                description="Advanced multi-method imputation"
            ),
            "hybrid_approach": ResolutionStrategy(
                method=ResolutionMethod.HYBRID.value,
                params={},
                confidence=0.85,
                reason="For mixed missing patterns",
                requirements=["numeric"],
                description="Hybrid imputation approach"
            ),

            # Categorical methods
            "group_rare": ResolutionStrategy(
                method=ResolutionMethod.GROUP_RARE.value,
                params={"threshold": 0.01},
                confidence=0.8,
                reason="For many rare categories",
                requirements=["categorical"],
                description="Group rare categories"
            ),
            "missing_category": ResolutionStrategy(
                method=ResolutionMethod.CREATE_MISSING_CATEGORY.value,
                params={"missing_label": "Missing"},
                confidence=0.9,
                reason="When missing is meaningful",
                requirements=["categorical"],
                description="Create explicit missing category"
            ),

            # Complete missing
            "complete_missingness": ResolutionStrategy(
                method=ResolutionMethod.COMPLETE_MISSINGNESS.value,
                params={},
                confidence=1.0,
                reason="Column is completely missing",
                requirements=[],
                description="Remove column"
            ),

            # Investigation mappings to concrete implementations
            "investigate_temporal": ResolutionStrategy(
                method=ResolutionMethod.TIME_INTERPOLATION.value,
                params={"method": "time"},
                confidence=0.7,
                reason="Maps to time interpolation",
                requirements=["numeric", "time_series"],
                description="Time-based imputation"
            ),
            "investigate_pattern": ResolutionStrategy(
                method=ResolutionMethod.HYBRID.value,
                params={},
                confidence=0.6,
                reason="Maps to hybrid approach",
                requirements=["numeric"],
                description="Hybrid imputation strategy"
            ),
            "investigate_relationships": ResolutionStrategy(
                method=ResolutionMethod.KNN.value,
                params={},
                confidence=0.65,
                reason="Maps to conditional imputation",
                requirements=["numeric"],
                description="Conditional imputation strategy"
            )
        }

    def _map_recommendation_to_strategy(self, recommendation_action: str) -> str:
        """Exact 1:1 mapping between analyzer recommendations and resolver implementations"""
        strategy_map = {
            # Basic imputation
            'impute_mean': 'mean_imputation',
            'mean': 'mean_imputation',  # Add this mapping
            'impute_median': 'median_imputation',
            'impute_mode': 'mode_imputation',

            # Robust methods
            'robust_imputation': 'robust_imputation',
            'robust_mean': 'robust_imputation',

            # Temporal methods
            'time_interpolation': 'time_interpolation',
            'simple_interpolation': 'interpolation',
            'moving_average': 'moving_average',

            # Structural methods
            'conditional_imputation': 'conditional_imputation',
            'investigate_relationships': 'knn_imputation',

            # Advanced methods
            'advanced_imputation': 'advanced_imputation',
            'hybrid_approach': 'hybrid_imputation',

            # Categorical methods
            'reduce_categories': 'group_rare',
            'missing_category': 'create_missing_category',
            'group_rare': 'group_rare',

            # Investigation/Pattern
            'investigate_temporal': 'time_interpolation',
            'investigate_pattern': 'hybrid_imputation',

            # Complete missing
            'complete_missingness': 'complete_missingness',
            'evaluate_importance': 'complete_missingness'
        }

        mapped_strategy = strategy_map.get(recommendation_action)
        if not mapped_strategy:
            logger.warning(f"No mapping found for recommendation: {recommendation_action}")
            return 'mean_imputation'  # Safe default

        return mapped_strategy

    def _setup_resolution_methods(self):
            """Setup corresponding implementation methods for each strategy"""
            self._resolution_methods = {
                # Basic imputation implementations
                'mean_imputation': self._mean_imputation,
                'median_imputation': self._median_imputation,
                'mode_imputation': self._mode_imputation,

                # Robust implementations
                'robust_imputation': self._robust_imputation,

                # Temporal implementations
                'interpolation': self._interpolation,
                'time_interpolation': self._time_interpolation,
                'moving_average': self._moving_average_imputation,

                # Structural implementations
                'conditional_imputation': self._knn_imputation,
                'knn_imputation': self._knn_imputation,
                # Advanced implementations
                'advanced_imputation': self._advanced_imputation,
                'hybrid_imputation': self._hybrid_imputation,

                # Categorical implementations
                'group_rare': self._group_rare_categories,
                'create_missing_category': self._create_missing_category,

                # Other implementations
                'complete_missingness': self._complete_missingness
            }

    def update_strategy_confidence(self, analysis_results: Dict[str, AnalysisResult]) -> None:
        """Update strategies with confidence and reason from analysis"""
        for field_name, analysis in analysis_results.items():
            strategy_name = analysis.recommendation['action']
            if strategy_name in self.strategy_registry:
                strategy = self.strategy_registry[strategy_name]
                # Update from analysis results
                strategy.confidence = analysis.recommendation['confidence']
                strategy.reason = analysis.recommendation['reason']

    def resolve(self, data: pd.DataFrame, analysis_results: Dict[str, AnalysisResult],
                resolution_commands: List[ResolutionCommand]) -> Tuple[pd.DataFrame, List[ResolutionResult]]:
        """Modified resolve method with proper complete missingness handling"""
        try:
            resolved_data = data.copy()
            results = []

            for command in resolution_commands:
                try:
                    # Get analysis result
                    analysis = analysis_results.get(command.field_name)
                    if not analysis:
                        continue

                    # Get strategy
                    strategy_name = self._map_recommendation_to_strategy(
                        analysis.recommendation['action']
                    )

                    if not strategy_name:
                        continue

                    # Get resolution method
                    resolution_method = self._resolution_methods.get(strategy_name)
                    if not resolution_method:
                        continue

                    # Track original missing count before resolution
                    original_missing = resolved_data[command.field_name].isna().sum()

                    # Apply resolution
                    resolved_data = resolution_method(
                        resolved_data,
                        command.field_name,
                        command.custom_params or {}
                    )

                    # Special handling for complete missingness
                    if strategy_name == 'complete_missingness':
                        current_missing = 0  # Column was dropped, so all values are "resolved"
                        success = command.field_name not in resolved_data.columns
                    else:
                        current_missing = (
                            0 if command.field_name not in resolved_data.columns
                            else resolved_data[command.field_name].isna().sum()
                        )
                        success = current_missing < original_missing

                    # Create result with proper metrics
                    results.append(ResolutionResult(
                        field_name=command.field_name,
                        strategy_used=command.selected_strategy,
                        original_missing=original_missing,
                        resolved_missing=current_missing,
                        success=success,
                        metrics=self._calculate_resolution_metrics(
                            data[command.field_name],
                            None if strategy_name == 'complete_missingness' else resolved_data[command.field_name]
                        ),
                        validation_results={}  # No validation needed for dropped columns
                    ))

                except Exception as method_error:
                    logger.error(f"Resolution method failed: {str(method_error)}")
                    results.append(self._create_error_result(
                        command, data, str(method_error)
                    ))

            return resolved_data, results

        except Exception as e:
            logger.error(f"Resolution process failed: {str(e)}")
            return data, []

    def _create_error_result(self, command: ResolutionCommand, data: pd.DataFrame,
                             error_message: str) -> ResolutionResult:
        """Create error result when resolution fails."""
        return ResolutionResult(
            field_name=command.field_name,
            strategy_used=command.selected_strategy,
            original_missing=data[command.field_name].isna().sum(),
            resolved_missing=data[command.field_name].isna().sum(),
            success=False,
            metrics={},
            validation_results={},
            error_message=error_message
        )

    def _apply_resolution(
            self,
            data: pd.DataFrame,
            field_name: str,
            strategy: ResolutionStrategy,
            custom_params: Dict[str, Any] = None
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """Apply selected resolution strategy and compute quality metrics"""
        try:
            # Get the recommendation action from the strategy
            recommendation_action = next(
                action for action, registered_strategy in self.strategy_registry.items()
                if registered_strategy == strategy
            )

            # Special handling for complete missing case
            if recommendation_action == "complete_missingness":
                resolved_data = self._complete_missingness(data, field_name, {})
                metrics = {
                    'missing_count_before': data[field_name].isna().sum() if field_name in data.columns else 0,
                    'missing_count_after': 0,
                    'resolution_rate': 1.0
                }
                return resolved_data, metrics

            # Get the implementation method based on the recommendation action
            resolution_method = self._resolution_methods.get(recommendation_action)
            if not resolution_method:
                raise ValueError(f"No implementation found for recommendation action: {recommendation_action}")

            # Merge strategy params with custom params
            params = {**strategy.params, **(custom_params or {})}

            # Apply resolution
            resolved_data = resolution_method(data, field_name, params)

            # Calculate metrics
            metrics = self._calculate_resolution_metrics(
                original_series=data[field_name],
                resolved_series=resolved_data[field_name]
            )

            return resolved_data, metrics

        except Exception as e:
            raise ValueError(f"Resolution failed: {str(e)}")

    def _validate_resolution(self, resolved_series: pd.Series, original_series: pd.Series,
                             analysis_result: AnalysisResult) -> Dict[str, bool]:
        """
        Validate resolution results using analysis information
        """
        validation_results = {}

        # Basic validation
        original_missing = original_series.isna().sum()
        resolved_missing = resolved_series.isna().sum()
        validation_results['reduced_missing'] = resolved_missing < original_missing

        # For numeric data, use analysis results to set appropriate thresholds
        if pd.api.types.is_numeric_dtype(original_series):
            original_stats = original_series.describe()
            resolved_stats = resolved_series.describe()

            # Use analysis confidence to adjust tolerance
            tolerance = max(0.1, 1 - analysis_result.recommendation['confidence'])

            # Check value ranges with dynamic tolerance
            validation_results['within_range'] = (
                    resolved_stats['min'] >= original_stats['min'] * (1 - tolerance) and
                    resolved_stats['max'] <= original_stats['max'] * (1 + tolerance)
            )

            # Check distribution preservation
            mean_change = abs(original_stats['mean'] - resolved_stats['mean']) / original_stats['std']
            std_change = abs(original_stats['std'] - resolved_stats['std']) / original_stats['std']

            max_allowed_change = 2 * (1 + tolerance)  # Adjust threshold based on confidence
            validation_results['distribution_preserved'] = (
                    mean_change < max_allowed_change and
                    std_change < max_allowed_change
            )

        return validation_results

    def get_available_strategies(self, analysis_results: Dict[str, AnalysisResult]) -> Dict[str, Dict[str, Any]]:
        """
        Return available resolution strategies with confidence from analysis
        """
        # First update confidences
        self.update_strategy_confidence(analysis_results)

        return {name: {
            'description': strategy.description,
            'confidence': strategy.confidence,
            'reason': strategy.reason,
            'requirements': strategy.requirements
        } for name, strategy in self.strategy_registry.items()}

    def _calculate_resolution_metrics(self, original_series: pd.Series, resolved_series: pd.Series) -> Dict[str, float]:
        """Calculate comprehensive metrics for resolution quality."""
        metrics = {}

        # Check if the series was dropped (entire column missing)
        if resolved_series is None or resolved_series.empty:
            total_missing = original_series.isna().sum()
            metrics = {
                'missing_count_before': total_missing,
                'missing_count_after': 0,  # Column is entirely resolved (dropped)
                'resolved_count': total_missing,
                'resolution_rate': 1.0,  # All missing data resolved
                'mean_difference': None,
                'std_difference': None,
                'range_difference': None,
            }
            return metrics

        # Handle normal resolution cases
        metrics = {
            'missing_count_before': original_series.isna().sum(),
            'missing_count_after': resolved_series.isna().sum()
        }

        if pd.api.types.is_numeric_dtype(original_series):
            original_stats = original_series.dropna().describe()
            resolved_stats = resolved_series.dropna().describe()

            metrics.update({
                'mean_difference': abs(original_stats['mean'] - resolved_stats['mean']) / original_stats['std'],
                'std_difference': abs(original_stats['std'] - resolved_stats['std']) / original_stats['std'],
                'range_difference': abs(original_stats['max'] - original_stats['min']) /
                                    abs(resolved_stats['max'] - resolved_stats['min']) - 1
            })
        else:
            # If non-numeric, these metrics are not applicable
            metrics.update({
                'mean_difference': None,
                'std_difference': None,
                'range_difference': None,
            })

        # Calculate resolution rate
        total_missing = metrics['missing_count_before']
        resolved_count = total_missing - metrics['missing_count_after']
        metrics['resolved_count'] = resolved_count
        metrics['resolution_rate'] = resolved_count / total_missing if total_missing > 0 else 1.0

        return metrics

    @staticmethod
    def _validate_column(data: pd.DataFrame, field_name: str) -> bool:
        """Validate if the column exists in the DataFrame."""
        if field_name not in data.columns:
            raise ValueError(f"Column '{field_name}' does not exist in the DataFrame.")
        return True

    @staticmethod
    def _validate_numeric(data: pd.DataFrame, field_name: str) -> bool:
        """Ensure the column is numeric."""
        if not pd.api.types.is_numeric_dtype(data[field_name]):
            raise ValueError(f"Column '{field_name}' must be numeric for this operation.")
        return True

    def _mean_imputation(self, data: pd.DataFrame, field_name: str, parameters: Dict[str, Any]) -> pd.DataFrame:
            """Implementation for random pattern with balanced distribution."""
            try:
                self._validate_numeric(data, field_name)
                result = data.copy()
                # Use simple mean for well-behaved numeric data
                imputer = SimpleImputer(strategy='mean')
                result[field_name] = imputer.fit_transform(result[[field_name]])
                return result
            except Exception as e:
                logger.error(f"Mean imputation failed: {str(e)}")
                return data

    def _median_imputation(self, data: pd.DataFrame, field_name: str, parameters: Dict[str, Any]) -> pd.DataFrame:
            """Implementation for random pattern with skewed distribution."""
            try:
                self._validate_numeric(data, field_name)
                result = data.copy()
                series = result[field_name]
                if series.skew() > 1.0:  # Confirm skewness
                    imputer = SimpleImputer(strategy='median')
                    result[field_name] = imputer.fit_transform(result[[field_name]])
                return result
            except Exception as e:
                logger.error(f"Median imputation failed: {str(e)}")
                return data

    def _mode_imputation(self, data: pd.DataFrame, field_name: str, parameters: Dict[str, Any]) -> pd.DataFrame:
            """Implementation for categorical data with clear modes."""
            try:
                result = data.copy()
                value_counts = result[field_name].value_counts()
                if value_counts.iloc[0] / len(result) > 0.5:  # Clear dominant value
                    mode_value = value_counts.index[0]
                    result[field_name] = result[field_name].fillna(mode_value)
                return result
            except Exception as e:
                logger.error(f"Mode imputation failed: {str(e)}")
                return data

    def _robust_imputation(self, data: pd.DataFrame, field_name: str, parameters: Dict[str, Any]) -> pd.DataFrame:
            """Implementation for random pattern with outliers/extreme values."""
            try:
                self._validate_numeric(data, field_name)
                result = data.copy()
                series = result[field_name].dropna()

                # Calculate robust statistics
                q1, q3 = series.quantile([0.25, 0.75])
                iqr = q3 - q1
                valid_data = series[
                    (series >= (q1 - 1.5 * iqr)) &
                    (series <= (q3 + 1.5 * iqr))
                    ]

                # Use trimmed mean for imputation
                robust_value = valid_data.mean()
                result[field_name] = result[field_name].fillna(robust_value)
                return result
            except Exception as e:
                logger.error(f"Robust imputation failed: {str(e)}")
                return data

    def _interpolation(self, data: pd.DataFrame, field_name: str, parameters: Dict[str, Any]) -> pd.DataFrame:
            """Implementation for simple temporal patterns."""
            try:
                self._validate_numeric(data, field_name)
                result = data.copy()

                # Linear interpolation for gaps
                result[field_name] = result[field_name].interpolate(method='linear')

                # Handle edges with forward/backward fill
                if result[field_name].isna().any():
                    result[field_name] = result[field_name].fillna(method='ffill').fillna(method='bfill')

                return result
            except Exception as e:
                logger.error(f"Interpolation failed: {str(e)}")
                return data

    def _time_interpolation(self, data: pd.DataFrame, field_name: str, parameters: Dict[str, Any]) -> pd.DataFrame:
        """Implementation for complex temporal patterns with timestamp."""
        try:
            self._validate_numeric(data, field_name)
            result = data.copy()

            # Ensure timestamp is available and sorted
            if 'timestamp' not in result.columns:
                raise ValueError("Timestamp column required for time interpolation")

            result['timestamp'] = pd.to_datetime(result['timestamp'])
            result = result.sort_values('timestamp')

            # Set the timestamp as the index for time-based interpolation
            result.set_index('timestamp', inplace=True)

            # Time-based interpolation with polynomial for complex patterns
            result[field_name] = result[field_name].interpolate(
                method='time',
                limit_direction='both',
                order=2
            )

            # Reset the index back to its original form
            result.reset_index(inplace=True)

            return result
        except Exception as e:
            logger.error(f"Time interpolation failed: {str(e)}")
            return data

    def _moving_average_imputation(self, data: pd.DataFrame, field_name: str,
                                       parameters: Dict[str, Any]) -> pd.DataFrame:
            """Implementation for temporal pattern with irregular intervals."""
            try:
                self._validate_numeric(data, field_name)
                result = data.copy()

                # Calculate window size based on data
                window = parameters.get('window',
                                        max(3, int(len(result) * 0.01)))  # Dynamic window

                # Apply rolling average with minimum periods
                result[field_name] = (
                    result[field_name]
                    .rolling(window=window, min_periods=1, center=True)
                    .mean()
                )
                return result
            except Exception as e:
                logger.error(f"Moving average failed: {str(e)}")
                return data

    def _conditional_imputation(self, data: pd.DataFrame, field_name: str,
                                    parameters: Dict[str, Any]) -> pd.DataFrame:
            """Implementation for structural patterns with related columns."""
            try:
                self._validate_numeric(data, field_name)
                result = data.copy()

                # Find correlated columns
                numeric_cols = result.select_dtypes(include=[np.number]).columns
                correlations = {}

                for col in numeric_cols:
                    if col != field_name:
                        corr = abs(result[field_name].corr(result[col]))
                        if not np.isnan(corr) and corr > 0.3:
                            correlations[col] = corr

                if correlations:
                    # Use best predictor for grouping
                    best_predictor = max(correlations.items(), key=lambda x: x[1])[0]
                    result[field_name] = (
                        result[field_name]
                        .fillna(result.groupby(best_predictor)[field_name].transform('mean'))
                    )

                return result
            except Exception as e:
                logger.error(f"Conditional imputation failed: {str(e)}")
                return data

    def _advanced_imputation(self, data: pd.DataFrame, field_name: str, parameters: Dict[str, Any]) -> pd.DataFrame:
            """Implementation for complex patterns requiring multiple methods."""
            try:
                self._validate_numeric(data, field_name)
                result = data.copy()

                # Try methods in sequence
                methods = [
                    ('interpolate', None),
                    ('knn', 5),
                    ('mean', None)
                ]

                for method, param in methods:
                    if result[field_name].isna().any():
                        if method == 'knn':
                            imputer = KNNImputer(n_neighbors=param)
                            result[field_name] = imputer.fit_transform(result[[field_name]])
                        elif method == 'interpolate':
                            result[field_name] = result[field_name].interpolate()
                        else:  # mean
                            result[field_name] = result[field_name].fillna(result[field_name].mean())

                return result
            except Exception as e:
                logger.error(f"Advanced imputation failed: {str(e)}")
                return data

    def _hybrid_imputation(self, data: pd.DataFrame, field_name: str, parameters: Dict[str, Any]) -> pd.DataFrame:
            """Implementation for partial patterns requiring pattern-specific handling."""
            try:
                self._validate_numeric(data, field_name)
                result = data.copy()
                series = result[field_name]

                # Split into segments
                is_missing = series.isna()
                missing_runs = self._get_runs_of_true(is_missing)

                if any(run > len(series) * 0.1 for run in missing_runs):
                    # Large gaps: use interpolation
                    result[field_name] = series.interpolate(method='polynomial', order=2)
                else:
                    # Small gaps: use local averaging
                    window = max(3, min(missing_runs))
                    result[field_name] = series.fillna(
                        series.rolling(window=window, min_periods=1).mean()
                    )

                return result
            except Exception as e:
                logger.error(f"Hybrid imputation failed: {str(e)}")
                return data

    def _group_rare_categories(self, data: pd.DataFrame, field_name: str,
                                   parameters: Dict[str, Any]) -> pd.DataFrame:
            """Implementation for categorical data with many rare categories."""
            try:
                result = data.copy()

                # Calculate category frequencies
                value_counts = result[field_name].value_counts(normalize=True)
                threshold = parameters.get('threshold', 0.01)

                # Identify rare categories
                rare_categories = value_counts[value_counts < threshold].index

                # Group rare categories
                result[field_name] = result[field_name].apply(
                    lambda x: 'Other' if x in rare_categories else x
                )

                # Fill remaining missing with mode
                result[field_name] = result[field_name].fillna(result[field_name].mode()[0])
                return result
            except Exception as e:
                logger.error(f"Group rare categories failed: {str(e)}")
                return data

    def _create_missing_category(self, data: pd.DataFrame, field_name: str,
                                     parameters: Dict[str, Any]) -> pd.DataFrame:
            """Implementation for categorical data where missing is meaningful."""
            try:
                result = data.copy()
                missing_label = parameters.get('missing_label', 'Missing')

                # Create explicit missing category
                result[field_name] = result[field_name].fillna(missing_label)
                return result
            except Exception as e:
                logger.error(f"Create missing category failed: {str(e)}")
                return data

    def _complete_missingness(self, data: pd.DataFrame, field_name: str, parameters: Dict[str, Any]) -> pd.DataFrame:
        """Handle columns that are missing or entirely unimportant."""
        try:
            result = data.copy()

            # Check if the column exists
            if field_name in result.columns:
                # Check if the column is entirely missing or unimportant (all NaNs)
                if result[field_name].isna().all():
                    logger.info(f"Column '{field_name}' is entirely missing (all NaNs) and will be dropped.")
                    result = result.drop(columns=[field_name])
                else:
                    logger.info(f"Column '{field_name}' exists but is not entirely missing.")
            else:
                logger.warning(f"Column '{field_name}' does not exist in the DataFrame.")

            return result
        except Exception as e:
            logger.error(f"Complete missingness handling failed: {str(e)}")
            return data

    def _knn_imputation(self, data: pd.DataFrame, field_name: str, parameters: Dict[str, Any]) -> pd.DataFrame:
        """Impute missing values using KNN with proper handling."""
        try:
            self._validate_column(data, field_name)
            self._validate_numeric(data, field_name)

            # Get numeric columns except the target
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            numeric_cols = [col for col in numeric_cols if col != field_name]

            if not numeric_cols:
                # Fallback to mean imputation if no numeric columns available
                return self._mean_imputation(data, field_name, parameters)

            # Create imputer
            n_neighbors = parameters.get('n_neighbors', 5)
            imputer = KNNImputer(n_neighbors=min(n_neighbors, len(data) - 1))

            # Prepare data for imputation
            impute_data = pd.DataFrame({
                'target': data[field_name],
                **{col: data[col] for col in numeric_cols[:3]}  # Use up to 3 related columns
            })

            # Perform imputation
            imputed_values = imputer.fit_transform(impute_data)

            # Update only the target column
            result = data.copy()
            result[field_name] = imputed_values[:, 0]

            return result

        except Exception as e:
            logger.error(f"KNN imputation failed for '{field_name}': {str(e)}")
            # Fallback to mean imputation
            return self._mean_imputation(data, field_name, parameters)


