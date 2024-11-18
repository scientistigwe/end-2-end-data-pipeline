from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime


# ---- Basic Data Validation Module ---- #

class MissingValuePattern(Enum):
    COMPLETELY_MISSING = "completely_missing"
    PARTIALLY_MISSING = "partially_missing"
    PATTERN_MISSING = "pattern_missing"  # e.g., missing every nth row
    CONDITIONAL_MISSING = "conditional_missing"  # missing based on other column values
    STRUCTURAL_MISSING = "structural_missing"  # missing due to data structure


class MissingValueImpact(Enum):
    CRITICAL = "critical"  # Cannot proceed without this data
    HIGH = "high"  # Significantly impacts analysis
    MEDIUM = "medium"  # Impacts analysis but workarounds exist
    LOW = "low"  # Minor impact on analysis


class RecommendedAction(Enum):
    REMOVE_ROWS = "remove_rows"
    IMPUTE_MEAN = "impute_mean"
    IMPUTE_MEDIAN = "impute_median"
    IMPUTE_MODE = "impute_mode"
    IMPUTE_CUSTOM = "impute_custom"
    FLAG_FOR_COLLECTION = "flag_for_collection"
    NO_ACTION = "no_action"


@dataclass
class MissingValueAnalysis:
    column_name: str
    missing_count: int
    missing_percentage: float
    pattern_type: MissingValuePattern
    impact_level: MissingValueImpact
    recommended_action: RecommendedAction
    confidence_score: float  # How confident we are in the recommendation
    additional_insights: Dict[str, Any]


class BasicDataValidator:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.analysis_results = {}

    def analyze_missing_values(self) -> Dict[str, MissingValueAnalysis]:
        """Analyzes missing values in each column and provides detailed insights."""
        results = {}

        for column in self.df.columns:
            missing_count = self.df[column].isna().sum()
            missing_percentage = (missing_count / len(self.df)) * 100

            # Detect missing value pattern
            pattern = self._detect_missing_pattern(column)

            # Assess impact
            impact = self._assess_impact_level(column, missing_percentage)

            # Determine recommended action
            action, confidence = self._recommend_action(column, pattern, impact)

            # Gather additional insights
            insights = self._gather_additional_insights(column)

            results[column] = MissingValueAnalysis(
                column_name=column,
                missing_count=missing_count,
                missing_percentage=missing_percentage,
                pattern_type=pattern,
                impact_level=impact,
                recommended_action=action,
                confidence_score=confidence,
                additional_insights=insights
            )

        self.analysis_results = results
        return results

    def _detect_missing_pattern(self, column: str) -> MissingValuePattern:
        """Detects the pattern of missing values in a column."""
        missing_mask = self.df[column].isna()

        if missing_mask.all():
            return MissingValuePattern.COMPLETELY_MISSING

        # Check for pattern missing (every nth row)
        missing_indices = np.where(missing_mask)[0]
        if len(missing_indices) > 1:
            differences = np.diff(missing_indices)
            if len(set(differences)) == 1:
                return MissingValuePattern.PATTERN_MISSING

        # Check for conditional missing
        if self._is_conditional_missing(column):
            return MissingValuePattern.CONDITIONAL_MISSING

        return MissingValuePattern.PARTIALLY_MISSING

    def _is_conditional_missing(self, column: str) -> bool:
        """Checks if missing values are conditional on other columns."""
        other_columns = [col for col in self.df.columns if col != column]
        missing_mask = self.df[column].isna()

        for other_col in other_columns:
            if self.df[other_col].dtype in ['object', 'category']:
                correlation = self.df[other_col].fillna('MISSING').astype('category').cat.codes.corr(missing_mask)
            else:
                correlation = self.df[other_col].fillna(self.df[other_col].mean()).corr(missing_mask)

            if abs(correlation) > 0.7:  # Strong correlation threshold
                return True

        return False

    def _assess_impact_level(self, column: str, missing_percentage: float) -> MissingValueImpact:
        """Assesses the impact level of missing values."""
        # This could be customized based on domain knowledge or column importance
        if missing_percentage > 75:
            return MissingValueImpact.CRITICAL
        elif missing_percentage > 50:
            return MissingValueImpact.HIGH
        elif missing_percentage > 25:
            return MissingValueImpact.MEDIUM
        return MissingValueImpact.LOW

    def _recommend_action(self, column: str, pattern: MissingValuePattern,
                          impact: MissingValueImpact) -> tuple[RecommendedAction, float]:
        """Recommends action based on pattern and impact."""
        if impact == MissingValueImpact.CRITICAL:
            return RecommendedAction.FLAG_FOR_COLLECTION, 0.9

        if pattern == MissingValuePattern.PATTERN_MISSING:
            return RecommendedAction.IMPUTE_CUSTOM, 0.8

        if self.df[column].dtype in ['int64', 'float64']:
            if self._is_skewed(column):
                return RecommendedAction.IMPUTE_MEDIAN, 0.7
            return RecommendedAction.IMPUTE_MEAN, 0.7

        return RecommendedAction.IMPUTE_MODE, 0.6

    def _is_skewed(self, column: str) -> bool:
        """Checks if numerical data is skewed."""
        return abs(self.df[column].skew()) > 1.0

    def _gather_additional_insights(self, column: str) -> Dict[str, Any]:
        """Gathers additional insights about the missing values."""
        insights = {}

        # Temporal patterns if datetime index exists
        if isinstance(self.df.index, pd.DatetimeIndex):
            missing_by_month = self.df[column].isna().groupby(self.df.index.month).mean()
            insights['temporal_pattern'] = missing_by_month.to_dict()

        # Relationship with other columns
        correlations = {}
        for other_col in self.df.columns:
            if other_col != column and self.df[other_col].dtype in ['int64', 'float64']:
                corr = self.df[column].isna().corr(self.df[other_col])
                if abs(corr) > 0.3:  # Moderate correlation threshold
                    correlations[other_col] = corr
        insights['correlations'] = correlations

        return insights

    def generate_report(self) -> str:
        """Generates a human-readable report of the analysis."""
        if not self.analysis_results:
            self.analyze_missing_values()

        report = ["Data Quality Analysis Report\n"]

        for column, analysis in self.analysis_results.items():
            report.append(f"\nColumn: {column}")
            report.append(f"Missing Values: {analysis.missing_count} ({analysis.missing_percentage:.2f}%)")
            report.append(f"Pattern: {analysis.pattern_type.value}")
            report.append(f"Impact Level: {analysis.impact_level.value}")
            report.append(f"Recommended Action: {analysis.recommended_action.value}")
            report.append(f"Confidence in Recommendation: {analysis.confidence_score:.2f}")

            if analysis.additional_insights:
                report.append("\nAdditional Insights:")
                for key, value in analysis.additional_insights.items():
                    report.append(f"- {key}: {value}")

        return "\n".join(report)


# # Example usage:
# if __name__ == "__main__":
#     # Create sample data
#     df = pd.DataFrame({
#         'A': [1, np.nan, 3, np.nan, 5],
#         'B': [np.nan, 2, np.nan, 4, np.nan],
#         'C': [1, 2, 3, 4, 5],
#         'D': [np.nan, np.nan, np.nan, np.nan, np.nan]
#     })
#
#     validator = BasicDataValidator(df)
#     analysis = validator.analyze_missing_values()
#     print(validator.generate_report())