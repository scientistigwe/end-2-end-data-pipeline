"""
Enhanced Missing Value Analysis System
------------------------------------
A comprehensive system for analyzing missing values in datasets with improved
memory efficiency, statistical robustness, and modular design.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from collections import defaultdict
from datetime import datetime, timedelta
import time
import psutil
import humanize
from colorama import init, Fore, Back, Style
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime
import logging

init(autoreset=True)  # Initialize colorama

logger = logging.getLogger(__name__)


class MissingValuePattern(Enum):
    """Enumeration of missing value patterns with clear descriptions."""
    COMPLETE = "complete_missing"  # All values are missing
    STRUCTURAL = "structural_missing"  # Missing values follow a structural pattern
    TEMPORAL = "temporal_missing"  # Missing values follow a time-based pattern
    RANDOM = "random_missing"  # Missing values appear randomly
    PARTIAL = "partial_missing"  # Some values are missing without clear pattern


class MissingMechanism(Enum):
    """Classification of missing data mechanisms."""
    MNAR = "missing_not_at_random"  # Value-dependent
    MAR = "missing_at_random"  # Related to other variables
    MCAR = "missing_completely_at_random"  # Pure random


@dataclass
class MissingValueStats:
    field_name: str
    total_count: int
    missing_count: int
    missing_ratio: float
    data_type: str

    @classmethod
    def from_series(cls, series: pd.Series) -> 'MissingValueStats':
        missing_mask = series.isna()
        return cls(
            field_name=series.name,
            total_count=len(series),
            missing_count=missing_mask.sum(),
            missing_ratio=missing_mask.mean(),
            data_type=str(series.dtype)
        )

    @property
    def has_missing_values(self) -> bool:
        """Check if there are any missing values."""
        return self.missing_count > 0


@dataclass
class AnalysisResult:
    """Results of missing value analysis for a single column."""
    field_name: str
    total_count: int
    missing_count: int
    missing_percentage: float
    pattern: MissingValuePattern
    mechanism: MissingMechanism
    recommendation: Dict[str, Any]  # Single specific recommendation

    def __str__(self):
        """String representation for printing results."""
        return (
            f"\nColumn: {self.field_name}\n"
            f"Missing Values: {self.missing_count:,} ({self.missing_percentage:.1f}%)\n"
            f"Pattern: {self.pattern.value}\n"
            f"Mechanism: {self.mechanism.value}\n"
            f"Recommendation: {self.recommendation['description']}\n"
            f"Reason: {self.recommendation['reason']}\n"
        )


class MissingValueAnalyzer:
    """Core analyzer class for missing value patterns."""

    def __init__(self, chunk_size: int = 100_000):
        self.chunk_size = chunk_size

    def analyze(self, data: pd.DataFrame) -> Dict[str, AnalysisResult]:
        """Analyze missing values in all columns of a dataset."""
        results = {}

        for column in data.columns:
            missing_count = data[column].isna().sum()
            if missing_count > 0:
                stats = MissingValueStats.from_series(data[column])
                pattern = self._detect_pattern(data, column, stats)
                mechanism = self._detect_mechanism(data, column, stats)
                recommendation = self._generate_recommendations(data, pattern, mechanism, stats)  # Fixed argument order

                results[column] = AnalysisResult(
                    field_name=column,
                    total_count=stats.total_count,
                    missing_count=stats.missing_count,
                    missing_percentage=(stats.missing_count / stats.total_count) * 100,
                    pattern=pattern,
                    mechanism=mechanism,
                    recommendation=recommendation
                )

        return results

    def _analyze_column(self, data: pd.DataFrame, column: str, stats: MissingValueStats) -> AnalysisResult:
        """Analyze a single column with missing values."""
        pattern = self._detect_pattern(data, column)
        mechanism = self._detect_mechanism(data, column)

        missing_pct = (stats.missing_count / stats.total_count) * 100

        return AnalysisResult(
            field_name=column,
            total_count=stats.total_count,
            missing_count=stats.missing_count,
            missing_percentage=missing_pct,
            pattern=pattern,
            mechanism=mechanism,
            recommendation=self._generate_recommendation(data, column, pattern, mechanism)
        )

    def _structural_score(self, data: pd.DataFrame, field: str,
                          stats: MissingValueStats) -> float:
        """Calculate structural pattern score."""
        if not stats.related_fields:
            return 0.0

        correlations = []
        for rel_field in stats.related_fields:
            if rel_field in data.columns:
                corr = data[field].corr(data[rel_field])
                if not np.isnan(corr):
                    correlations.append(abs(corr))

        return max(correlations) if correlations else 0.0

    def _temporal_score(self, data: pd.DataFrame, field: str,
                        stats: MissingValueStats) -> float:
        """Calculate temporal pattern score."""
        if 'timestamp' not in data.columns:
            return 0.0

        try:
            # Convert to datetime if needed
            timestamps = pd.to_datetime(data['timestamp'])
            missing_mask = data[field].isna()

            # Calculate time gaps between missing values
            missing_gaps = timestamps[missing_mask].diff()

            if missing_gaps.empty:
                return 0.0

            # Calculate regularity score
            mean_gap = missing_gaps.mean().total_seconds()
            std_gap = missing_gaps.std().total_seconds()

            if mean_gap == 0:
                return 0.0

            cv = std_gap / mean_gap
            regularity_score = 1 / (1 + cv)

            return regularity_score

        except Exception:
            return 0.0

    def _random_score(self, data: pd.DataFrame, field: str,
                      stats: MissingValueStats) -> float:
        """Calculate random pattern score."""
        missing_mask = data[field].isna()

        # Calculate runs test
        runs = self._calculate_runs(missing_mask)
        expected_runs = len(missing_mask) * stats.missing_ratio * (1 - stats.missing_ratio)

        if expected_runs == 0:
            return 0.0

        # Score based on how close actual runs are to expected
        return 1 - abs(runs - expected_runs) / expected_runs

    def _calculate_runs(self, series: pd.Series) -> int:
        """Calculate number of runs in a boolean series."""
        return (series != series.shift()).sum() // 2

    def _check_value_dependency(self, series: pd.Series) -> bool:
        """Check if missing values depend on the values themselves."""
        values_before = series.shift(1)
        missing_values = values_before[series.isna()].dropna()
        present_values = values_before[~series.isna()].dropna()

        if len(missing_values) < 2 or len(present_values) < 2:
            return False

        try:
            _, p_value = stats.ks_2samp(missing_values, present_values)
            return p_value < 0.05
        except Exception:
            return False

    def _check_variable_relationships(self, data: pd.DataFrame, field: str,
                                      related_fields: List[str]) -> bool:
        """Check for relationships between missing values and other variables."""
        missing_mask = data[field].isna()

        for rel_field in related_fields:
            if rel_field not in data.columns:
                continue

            try:
                # Calculate correlation with missing indicator
                corr = data[rel_field].corr(missing_mask)
                if not np.isnan(corr) and abs(corr) > 0.5:
                    return True
            except Exception:
                continue

        return False

    def _calculate_confidence(self, stats: MissingValueStats,
                              pattern: MissingValuePattern,
                              mechanism: MissingMechanism) -> float:
        """Calculate confidence score for the analysis."""
        base_confidence = min(np.log10(stats.total_count) / 5, 1.0)

        pattern_strength = self._calculate_pattern_strength(stats.field_name, pattern)
        data_quality = self._calculate_data_quality(stats.field_name)

        # Define weights for each factor
        base_confidence_weight = 0.4
        pattern_strength_weight = 0.4
        data_quality_weight = 0.2

        # Combine factors with weights
        confidence = (
                base_confidence * base_confidence_weight +
                pattern_strength * pattern_strength_weight +
                data_quality * data_quality_weight
        )

        return round(confidence, 2)

    def _calculate_impact(self, stats: MissingValueStats,
                          pattern: MissingValuePattern,
                          mechanism: MissingMechanism) -> float:
        """Calculate impact score of missing values."""
        base_impact = stats.missing_ratio

        pattern_factors = {
            MissingValuePattern.COMPLETE: 2.0,
            MissingValuePattern.STRUCTURAL: 1.3,
            MissingValuePattern.TEMPORAL: 1.2,
            MissingValuePattern.RANDOM: 1.0,
            MissingValuePattern.PARTIAL: 1.1
        }

        mechanism_factors = {
            MissingMechanism.MNAR: 1.5,
            MissingMechanism.MAR: 1.2,
            MissingMechanism.MCAR: 1.0
        }

        return min(base_impact * pattern_factors[pattern] * mechanism_factors[mechanism], 1.0)

    def _calculate_bias_risk(self, stats: MissingValueStats,
                             mechanism: MissingMechanism) -> float:
        """Calculate risk of bias from missing values."""
        base_risk = stats.missing_ratio

        if mechanism == MissingMechanism.MNAR:
            return min(0.9 + base_risk * 0.1, 1.0)
        elif mechanism == MissingMechanism.MAR:
            return 0.5 + base_risk * 0.3
        else:  # MCAR
            return 0.2 + base_risk * 0.2

    def _detect_mechanism(self, data: pd.DataFrame, column: str, stats: MissingValueStats) -> MissingMechanism:
        """Detect the missing data mechanism with improved checks."""
        missing_mask = data[column].isna()

        # Check for MNAR (value dependency)
        if data[column].dtype in ['int64', 'float64']:
            non_missing_values = data[column].dropna()
            try:
                # Check if higher/lower values are more likely to be missing
                quantiles = non_missing_values.quantile([0.25, 0.75])
                high_missing = missing_mask[data[column] > quantiles[0.75]].mean()
                low_missing = missing_mask[data[column] < quantiles[0.25]].mean()

                if abs(high_missing - low_missing) > 0.1:  # Significant difference
                    return MissingMechanism.MNAR
            except:
                pass

        # Check for MAR (relationship with other variables)
        for other_col in data.columns:
            if other_col != column and data[other_col].dtype in ['int64', 'float64']:
                try:
                    corr = data[other_col].corr(missing_mask)
                    if abs(corr) > 0.3:  # Strong correlation with missingness
                        return MissingMechanism.MAR
                except:
                    continue

        return MissingMechanism.MCAR

    def _detect_pattern(self, data: pd.DataFrame, column: str, stats: MissingValueStats) -> MissingValuePattern:
        """
        Enhanced pattern detection with improved exclusions for strict categorization.
        """
        try:
            missing_mask = data[column].isna()
            total_rows = len(data)
            missing_count = missing_mask.sum()
            missing_ratio = missing_count / total_rows

            # 1. Complete Missing Check
            if missing_ratio >= 0.95:
                return MissingValuePattern.COMPLETE

            # 2. Random Pattern Check
            if self._check_random_pattern(missing_mask):
                return MissingValuePattern.RANDOM

            # 3. Partial Pattern Check
            if self._check_partial_pattern(missing_mask):
                return MissingValuePattern.PARTIAL

            # 4. Structural Pattern Check
            if self._check_structural_pattern(data, column, missing_mask):
                return MissingValuePattern.STRUCTURAL

            # 5. Temporal Pattern Check
            if 'timestamp' in data.columns and self._check_temporal_pattern(data, missing_mask):
                return MissingValuePattern.TEMPORAL

            return MissingValuePattern.UNKNOWN  # Default to UNKNOWN if no patterns match

        except Exception as e:
            logger.error(f"Error in pattern detection for column {column}: {str(e)}")
            return MissingValuePattern.UNKNOWN  # Safe default if detection fails

    def _check_random_pattern(self, missing_mask: pd.Series) -> bool:
        """Detect random pattern in missing values with strict criteria."""
        try:
            missing_indices = np.where(missing_mask)[0]
            if len(missing_indices) < 2:
                return False

            gaps = np.diff(missing_indices)
            mean_gap = np.mean(gaps)
            std_gap = np.std(gaps)
            cv = std_gap / mean_gap if mean_gap > 0 else float('inf')

            # Strict randomness criteria
            is_random = (
                    cv > 0.7 and
                    not np.any(np.bincount(gaps) > len(gaps) * 0.1) and  # No dominant period
                    all(run <= len(missing_mask) * 0.05  # No large continuous blocks
                        for run in self._get_runs_of_true(missing_mask))
            )

            # Uniform gap distribution
            _, p_value = stats.kstest(gaps, 'uniform', args=(min(gaps), max(gaps)))

            return is_random and p_value > 0.1  # Uniformity test with relaxed p-value

        except Exception as e:
            logger.error(f"Error in random pattern check: {str(e)}")
            return False

    def _check_partial_pattern(self, missing_mask: pd.Series) -> bool:
        """Detect partial/block missing patterns with strict criteria."""
        try:
            runs = self._get_runs_of_true(missing_mask)
            if not runs:
                return False

            n = len(missing_mask)
            max_run = max(runs)
            total_missing = missing_mask.sum()

            # Strict partial criteria
            is_partial = (
                    max_run > n * 0.2 and  # Long continuous blocks
                    total_missing / n > 0.1 and  # Significant proportion of missing values
                    all(run > 2 for run in runs)  # Avoid random single gaps
            )

            return is_partial

        except Exception as e:
            logger.error(f"Error in partial pattern check: {str(e)}")
            return False

    def _check_temporal_pattern(self, data: pd.DataFrame, missing_mask: pd.Series) -> bool:
        """Detect temporal patterns with strict criteria."""
        try:
            if self._check_random_pattern(missing_mask) or self._check_partial_pattern(missing_mask):
                return False  # Exclude random or partial patterns

            timestamps = pd.to_datetime(data['timestamp'])
            missing_indices = np.where(missing_mask)[0]

            if len(missing_indices) < 2:
                return False

            time_diffs = np.diff(timestamps[missing_indices])
            hours_diff = time_diffs.astype('timedelta64[h]').astype(float)

            return (
                    self._has_daily_pattern(hours_diff) or
                    self._has_weekly_pattern(hours_diff) or
                    self._has_monthly_pattern(hours_diff) or
                    self._has_regular_interval(hours_diff)
            )

        except Exception as e:
            logger.error(f"Error in temporal pattern check: {str(e)}")
            return False

    def _check_structural_pattern(self, data: pd.DataFrame, column: str, missing_mask: pd.Series) -> bool:
        """Detect structural dependencies in missing values with strict criteria."""
        try:
            if self._check_random_pattern(missing_mask) or self._check_partial_pattern(missing_mask):
                return False

            if pd.api.types.is_numeric_dtype(data[column]):
                values = data[column].dropna()
                if len(values) > 0:
                    median = values.median()
                    high_missing_rate = missing_mask[data[column] > median].mean()
                    low_missing_rate = missing_mask[data[column] <= median].mean()
                    if abs(high_missing_rate - low_missing_rate) > 0.2:
                        return True

            for other_col in data.columns:
                if other_col != column and other_col != 'timestamp':
                    if pd.api.types.is_numeric_dtype(data[other_col]):
                        corr = self._safe_correlation(missing_mask, data[other_col])
                        if corr is not None and abs(corr) > 0.3:
                            return True

            return False

        except Exception as e:
            logger.error(f"Error in structural pattern check: {str(e)}")
            return False

    def _get_runs_of_true(self, bool_series: pd.Series) -> List[int]:
        """Get lengths of consecutive True runs in a boolean series."""
        try:
            # Convert to numpy array for faster processing
            arr = bool_series.astype(int).values
            runs = []
            current_run = 0

            for val in arr:
                if val:
                    current_run += 1
                elif current_run > 0:
                    runs.append(current_run)
                    current_run = 0

            if current_run > 0:
                runs.append(current_run)

            return runs

        except Exception as e:
            logger.error(f"Error in getting runs: {str(e)}")
            return []

    def _safe_correlation(self, series1: pd.Series, series2: pd.Series) -> Optional[float]:
        """Safely calculate correlation between two series."""
        try:
            if len(series1) != len(series2):
                return None

            # Convert to numeric and handle correlation
            s1 = pd.to_numeric(series1, errors='coerce')
            s2 = pd.to_numeric(series2, errors='coerce')

            # Remove any rows where either series has NaN
            mask = ~(s1.isna() | s2.isna())
            s1_clean = s1[mask]
            s2_clean = s2[mask]

            if len(s1_clean) > 2 and s1_clean.nunique() > 1 and s2_clean.nunique() > 1:
                correlation = s1_clean.corr(s2_clean, method='spearman')
                return correlation if not np.isnan(correlation) else None

            return None

        except Exception as e:
            logger.error(f"Error in correlation calculation: {str(e)}")
            return None

    # Helper methods for temporal pattern checks
    def _is_regular_interval(self, hours_diff: np.ndarray) -> bool:
        """Check for regular time intervals"""
        if len(hours_diff) < 2:
            return False
        std_dev = np.std(hours_diff)
        mean_diff = np.mean(hours_diff)
        return (std_dev / mean_diff) < 0.1  # Very regular intervals

    def _has_daily_pattern(self, hours_diff: np.ndarray) -> bool:
        """Check for daily patterns (24-hour multiples)"""
        remainder = hours_diff % 24
        return np.any(np.isclose(remainder, 0, atol=1))

    def _has_weekly_pattern(self, hours_diff: np.ndarray) -> bool:
        """Check for weekly patterns (168-hour multiples)"""
        remainder = hours_diff % 168
        return np.any(np.isclose(remainder, 0, atol=2))

    def _has_monthly_pattern(self, hours_diff: np.ndarray) -> bool:
        """Check for monthly patterns (~730 hours)"""
        remainder = hours_diff % 730
        return np.any(np.isclose(remainder, 0, atol=24))

    def _calculate_pattern_strength(self, series: pd.Series, pattern: MissingValuePattern) -> float:
        """Calculate how strong/clear the detected pattern is"""
        try:
            missing_mask = series.isna()

            if pattern == MissingValuePattern.COMPLETE:
                return 1.0 if missing_mask.all() else 0.0

            elif pattern == MissingValuePattern.RANDOM:
                # Check how random the distribution is using runs test
                runs = len(missing_mask.ne(missing_mask.shift()).dropna())
                expected_runs = 2 * missing_mask.mean() * (1 - missing_mask.mean()) * len(missing_mask)
                randomness = 1 - abs(runs - expected_runs) / expected_runs if expected_runs > 0 else 0
                return randomness

            elif pattern == MissingValuePattern.STRUCTURAL:
                # Calculate autocorrelation
                autocorr = missing_mask.autocorr() if len(missing_mask) > 1 else 0
                return abs(autocorr) if not np.isnan(autocorr) else 0

            elif pattern == MissingValuePattern.TEMPORAL:
                # Check regularity of gaps
                gaps = np.diff(np.where(missing_mask)[0])
                if len(gaps) > 1:
                    cv = np.std(gaps) / np.mean(gaps) if np.mean(gaps) > 0 else 0
                    return 1 / (1 + cv)
                return 0

            return 0.5  # Default for partial or unclear patterns

        except Exception:
            return 0.5

    def _calculate_data_quality(self, series: pd.Series) -> float:
        """Calculate data quality score based on various metrics"""
        try:
            non_missing = series.dropna()
            if len(non_missing) == 0:
                return 0.0

            if pd.api.types.is_numeric_dtype(series):
                # For numeric data, consider distribution characteristics
                skewness = abs(non_missing.skew())
                kurtosis = abs(non_missing.kurtosis())

                # Penalize for extreme distributions
                distribution_score = 1 / (1 + skewness / 2 + kurtosis / 10)

                # Check for outliers
                z_scores = abs((non_missing - non_missing.mean()) / non_missing.std())
                outlier_ratio = (z_scores > 3).mean()
                outlier_score = 1 - outlier_ratio

                return (distribution_score + outlier_score) / 2

            else:
                # For categorical data, consider cardinality and balance
                value_counts = non_missing.value_counts(normalize=True)
                n_categories = len(value_counts)

                # Calculate entropy as a measure of balance
                entropy = -sum(p * np.log2(p) for p in value_counts)
                max_entropy = np.log2(n_categories) if n_categories > 0 else 1
                normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

                # Score based on reasonable number of categories and good balance
                return (1 / (1 + np.log10(n_categories))) * normalized_entropy

        except Exception:
            return 0.5

    def _generate_recommendations(self, data: pd.DataFrame, pattern: MissingValuePattern,
                                  mechanism: MissingMechanism, stats: MissingValueStats) -> Dict[str, Any]:
        """Generate recommendations with dynamically calculated confidence"""

        # Calculate base confidence for this field
        confidence = self._calculate_confidence(stats, pattern, mechanism)

        if pattern == MissingValuePattern.COMPLETE:
            return {
                'action': 'complete_missingness',
                'description': "Consider removing this column as it contains no data",
                'reason': "This field is completely empty, suggesting it might be unused or no longer relevant",
                'confidence': confidence
            }

        elif pattern == MissingValuePattern.RANDOM:
            recommendation = self._get_random_recommendation(data, stats)
            recommendation['confidence'] = confidence
            return recommendation

        elif pattern == MissingValuePattern.STRUCTURAL:
            recommendation = self._get_structural_recommendation(data, stats)
            recommendation['confidence'] = confidence
            return recommendation

        elif pattern == MissingValuePattern.TEMPORAL:
            recommendation = self._get_temporal_recommendation(data, stats)
            recommendation['confidence'] = confidence
            return recommendation

        else:  # PARTIAL
            recommendation = self._get_partial_recommendation(data, stats)
            recommendation['confidence'] = confidence
            return recommendation

    def _get_random_recommendation(self, data: pd.DataFrame, stats: MissingValueStats) -> Dict[str, Any]:
        """Enhanced recommendation for randomly missing values"""
        if stats.data_type in ('int64', 'float64'):
            try:
                series = data[stats.field_name].dropna()
                skewness = abs(series.skew())
                std = series.std()
                mean = series.mean()
                cv = std / mean if mean != 0 else float('inf')

                if cv > 1.5 or skewness > 2.0:  # High variation or strong skew
                    return {
                        'action': 'robust_imputation',
                        'description': f"Fill missing values using robust statistical methods",
                        'reason': "The data shows high variability or skewness. Using robust methods will handle outliers better"
                    }
                elif skewness > 1.0:  # Moderate skew
                    return {
                        'action': 'impute_median',
                        'description': f"Fill missing values with the median",
                        'reason': "The data shows moderate skewness. Using median will be more robust than mean"
                    }
                else:  # Well-behaved data
                    return {
                        'action': 'impute_mean',
                        'description': f"Fill missing values with the mean",
                        'reason': "The data follows a balanced distribution. Using mean is appropriate"
                    }
            except:
                pass

        # For categorical or fallback
        return {
            'action': 'impute_mode',
            'description': f"Fill missing values with the most common value",
            'reason': "For this type of data, using the most frequent value is most appropriate"
        }

    def _get_structural_recommendation(self, data: pd.DataFrame, stats: MissingValueStats) -> Dict[str, Any]:
        """Enhanced recommendation for structurally missing values"""
        correlations = {}

        for col in data.columns:
            if col != stats.field_name and data[col].dtype in ('int64', 'float64'):
                try:
                    corr = abs(data[stats.field_name].corr(data[col]))
                    if not np.isnan(corr):
                        correlations[col] = corr
                except:
                    continue

        if correlations:
            best_predictor = max(correlations.items(), key=lambda x: x[1])
            return {
                'action': 'conditional_imputation',
                'description': f"Use related information from '{best_predictor[0]}' to predict missing values",
                'reason': f"There's a strong connection between this field and '{best_predictor[0]}'. Using this relationship will give more accurate estimates for the missing values"
            }

        return {
            'action': 'investigate_relationships',
            'description': "Look deeper into what might be causing these missing values",
            'reason': "There seems to be a pattern to when values are missing, but we need more information to understand why. Consider checking if specific business rules or data collection processes might explain this"
        }

    def _get_temporal_recommendation(self, data: pd.DataFrame, stats: MissingValueStats) -> Dict[str, Any]:
        """Enhanced recommendation for time-based missing patterns"""
        if 'timestamp' not in data.columns:
            return {
                'action': 'investigate_temporal',
                'description': "Add time information to better understand the missing values",
                'reason': "The missing values follow a time-based pattern, but we need timestamp information to handle this properly"
            }

        try:
            timestamps = pd.to_datetime(data['timestamp'])
            missing_gaps = timestamps[data[stats.field_name].isna()].diff()
            cv = missing_gaps.std() / missing_gaps.mean()

            if cv < 0.5:  # Regular intervals
                return {
                    'action': 'time_interpolation',
                    'description': f"Fill missing values based on the time pattern in your data",
                    'reason': "Missing values occur at regular time intervals. Using time-based filling will maintain the natural progression of your data"
                }
            else:
                return {
                    'action': 'moving_average',
                    'description': f"Use a rolling average to fill gaps in your data",
                    'reason': "Values are missing at different time intervals. Using recent values to estimate missing ones will help maintain data trends"
                }
        except:
            return {
                'action': 'simple_interpolation',
                'description': f"Fill missing values using nearby data points",
                'reason': "While there's a time-based pattern, a simple approach using nearby values would work best given the data structure"
            }

    def _get_partial_recommendation(self, data: pd.DataFrame, stats: MissingValueStats) -> Dict[str, Any]:
        """Enhanced recommendation for partially missing values"""
        try:
            if stats.missing_ratio > 0.7:
                return {
                    'action': 'evaluate_importance',
                    'description': "Consider if this field is still needed for your analysis",
                    'reason': "Most of the data is missing. It might be better to exclude this field unless it's absolutely crucial for your analysis"
                }

            if stats.data_type in ('int64', 'float64'):
                return {
                    'action': 'advanced_imputation',
                    'description': "Use advanced statistical methods to fill missing values",
                    'reason': "The missing values show a complex pattern. Advanced methods will help maintain the relationships in your data"
                }

            return {
                'action': 'hybrid_approach',
                'description': "Use a combination of methods to fill missing values",
                'reason': "The missing values follow multiple patterns. A combined approach will give the most reliable results"
            }

        except Exception as e:
            return {
                'action': 'investigate_pattern',
                'description': "Investigate why values are missing before deciding how to handle them",
                'reason': "The pattern of missing values is unclear and needs more investigation to determine the best approach"
            }

    def _numeric_recommendations(self, data: pd.DataFrame, stats: MissingValueStats) -> Dict[str, Any]:
        """
        Generate user-friendly recommendations for numeric fields based on their distribution.
        """
        try:
            values = data[stats.field_name].dropna()
            skewness = abs(values.skew())
            kurtosis = abs(values.kurtosis())

            # Check for extreme values
            z_scores = abs((values - values.mean()) / values.std())
            has_outliers = (z_scores > 3).sum() / len(values) > 0.01

            if skewness > 2.0:  # Severely skewed
                return {
                    'action': 'robust_imputation',
                    'description': "Use advanced statistical methods that handle extreme values",
                    'reason': "Your data has many extreme values on one side. Simple averages won't work well here. Advanced methods will better preserve the data's natural patterns"
                }
            elif skewness > 1.0:  # Moderately skewed
                return {
                    'action': 'impute_median',
                    'description': "Fill missing values with the middle value from your existing data",
                    'reason': "Your data isn't evenly balanced around the average. Using the middle value will help avoid bias from extreme values"
                }
            elif has_outliers:  # Outliers present
                return {
                    'action': 'robust_mean',
                    'description': "Use a smart averaging method that ignores extreme values",
                    'reason': "While your data is mostly well-behaved, it contains some unusual values. Using a method that ignores these outliers will give better results"
                }
            else:  # Well-behaved distribution
                return {
                    'action': 'impute_mean',
                    'description': "Fill missing values with the average of existing data",
                    'reason': "Your data follows a nice, balanced pattern. Using the average value will maintain this balance"
                }

        except Exception as e:
            return {
                'action': 'impute_median',
                'description': "Use the middle value from your existing data",
                'reason': "We encountered some issues analyzing your data. Using the middle value is a safe approach that works in most cases"
            }

    def _categorical_recommendations(self, data: pd.DataFrame, stats: MissingValueStats) -> Dict[str, Any]:
        """
        Generate user-friendly recommendations for categorical fields based on their distribution.
        """
        try:
            value_counts = data[stats.field_name].value_counts()
            n_categories = len(value_counts)
            total = len(data)

            # Calculate distribution metrics
            proportions = value_counts / total
            mode_proportion = proportions.iloc[0]
            entropy = -sum(p * np.log2(p) for p in proportions)
            max_entropy = np.log2(n_categories)
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

            # Additional metrics
            category_ratio = n_categories / total

            if n_categories > 100:  # Too many categories
                return {
                    'action': 'reduce_categories',
                    'description': "Simplify your categories before filling missing values",
                    'reason': f"This field has {n_categories} different categories, which is quite high. Grouping similar categories together first will make the filling process more reliable"
                }
            elif mode_proportion > 0.8:  # Highly dominant category
                return {
                    'action': 'impute_mode',
                    'description': "Use the most common category to fill missing values",
                    'reason': f"One category appears {mode_proportion:.1%} of the time. Using this dominant value is likely to be correct in most cases"
                }
            elif normalized_entropy > 0.9:  # Very uniform distribution
                return {
                    'action': 'missing_category',
                    'description': "Create a new 'Missing' category instead of filling values",
                    'reason': "Your categories are very evenly distributed. When data is missing, it might mean something specific rather than being a random occurrence"
                }
            elif category_ratio > 0.1:  # High category to row ratio
                return {
                    'action': 'group_rare',
                    'description': "Group uncommon categories together before filling missing values",
                    'reason': "There are many rare categories in your data. Grouping the less common ones will make the filling process more reliable"
                }
            else:  # Standard case
                return {
                    'action': 'impute_mode',
                    'description': "Use the most common category to fill missing values",
                    'reason': f"Your data has a reasonable number of categories ({n_categories}) with a natural distribution. Using the most common value is a reliable approach"
                }

        except Exception as e:
            return {
                'action': 'impute_mode',
                'description': "Use the most common category to fill missing values",
                'reason': "While we had some issues analyzing your categories in detail, using the most common value is generally a safe approach"
            }