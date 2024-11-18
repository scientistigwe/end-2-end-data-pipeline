from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from dataclasses import dataclass
from enum import Enum

from message_broker import MessageBroker, UserDecision, DecisionStatus


class ResolutionStrategy(Enum):
    SIMPLE = "simple"  # Basic imputation strategies
    ADVANCED = "advanced"  # More sophisticated methods like KNN, MICE
    CUSTOM = "custom"  # Custom user-defined strategies


@dataclass
class ResolutionResult:
    """Data class for storing resolution results"""
    cleaned_data: pd.DataFrame
    resolution_details: Dict[str, Any]
    verification_results: Dict[str, Any]
    documentation: Dict[str, Any]
    quality_metrics: Dict[str, float]


class MissingValueResolver:
    """
    Resolver for handling missing value issues based on user decisions.
    Works with MessageBroker to receive and process decisions.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.resolution_history: List[Dict[str, Any]] = []

        # Subscribe to missing value decisions
        self.message_broker.subscribe_to_decisions(
            self._handle_decision,
            'missing_value'
        )

    def _handle_decision(self, decision: UserDecision) -> None:
        """Processes incoming decisions from the message broker"""
        try:
            # Update status to IN_PROGRESS
            self.message_broker.update_decision_status(
                decision.issue_id,
                DecisionStatus.IN_PROGRESS
            )

            # Apply resolution
            result = self._apply_resolution(decision)

            # Update status based on result
            if result.verification_results['success']:
                self.message_broker.update_decision_status(
                    decision.issue_id,
                    DecisionStatus.COMPLETED
                )
            else:
                self.message_broker.update_decision_status(
                    decision.issue_id,
                    DecisionStatus.FAILED
                )

            # Store in history
            self._update_resolution_history(decision, result)

        except Exception as e:
            self.message_broker.update_decision_status(
                decision.issue_id,
                DecisionStatus.FAILED
            )
            raise e

    def _apply_resolution(self, decision: UserDecision) -> ResolutionResult:
        """Applies the resolution based on the user decision"""
        data = self._get_data_from_decision(decision)
        analysis_results = self._get_analysis_from_decision(decision)

        resolver = self._create_resolver_instance(decision)
        return resolver.resolve(data, analysis_results)

    def _get_data_from_decision(self, decision: UserDecision) -> pd.DataFrame:
        """Extracts data from decision metadata"""
        data = decision.metadata.get('data')
        if data is None:
            raise ValueError("No data provided in decision metadata")
        return data

    def _get_analysis_from_decision(self, decision: UserDecision) -> Dict[str, Any]:
        """Extracts analysis results from decision metadata"""
        analysis_results = decision.metadata.get('analysis_results')
        if analysis_results is None:
            raise ValueError("No analysis results provided in decision metadata")
        return analysis_results

    def _create_resolver_instance(self, decision: UserDecision) -> 'BasicResolver':
        """Creates a resolver instance based on decision parameters"""
        strategy = ResolutionStrategy(decision.decision_type)
        params = decision.parameters or {}

        return BasicResolver(
            strategy=strategy,
            custom_imputers=params.get('custom_imputers', {}),
            verification_threshold=params.get('verification_threshold', 0.8)
        )

    def _update_resolution_history(self,
                                   decision: UserDecision,
                                   result: ResolutionResult) -> None:
        """Updates the resolution history with new result"""
        self.resolution_history.append({
            'decision': decision.to_dict(),
            'result': result,
            'timestamp': datetime.now().isoformat()
        })

    def get_resolution_history(self) -> List[Dict[str, Any]]:
        """Returns the complete resolution history"""
        return self.resolution_history

    def get_resolution_statistics(self) -> Dict[str, Any]:
        """Calculates statistics about resolutions"""
        total = len(self.resolution_history)
        if total == 0:
            return {'error': 'No resolution history available'}

        successful = sum(
            1 for entry in self.resolution_history
            if entry['decision']['status'] == DecisionStatus.COMPLETED.value
        )

        return {
            'total_resolutions': total,
            'successful_resolutions': successful,
            'success_rate': successful / total,
            'average_quality': np.mean([
                list(entry['result'].quality_metrics.values())[0]
                for entry in self.resolution_history
                if hasattr(entry['result'], 'quality_metrics')
            ])
        }


class BasicResolver:
    """Handles the actual resolution logic"""

    def __init__(self,
                 strategy: ResolutionStrategy,
                 custom_imputers: Dict[str, Any] = None,
                 verification_threshold: float = 0.8):
        self.strategy = strategy
        self.custom_imputers = custom_imputers or {}
        self.verification_threshold = verification_threshold

    def resolve(self,
                data: pd.DataFrame,
                analysis_results: Dict[str, Any]) -> ResolutionResult:
        """Main resolution method"""
        # Implementation remains the same as in your original code
        # Include all the resolution logic here
        pass  # Add your implementation

    # Include all other helper methods from your original implementation
    # _validate_issues, _apply_resolution, _verify_resolution, etc.


class ResolutionStrategy(Enum):
    SIMPLE = "simple"  # Basic imputation strategies
    ADVANCED = "advanced"  # More sophisticated methods like KNN, MICE
    CUSTOM = "custom"  # Custom user-defined strategies


class ImputationMethod(Enum):
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    KNN = "knn"
    MICE = "mice"
    FORWARD_FILL = "ffill"
    BACKWARD_FILL = "bfill"
    CUSTOM = "custom"


@dataclass
class ResolutionResult:
    """Data class for storing resolution results"""
    cleaned_data: pd.DataFrame
    resolution_details: Dict[str, Any]
    verification_results: Dict[str, Any]
    documentation: Dict[str, Any]
    quality_metrics: Dict[str, float]


class MissingValueResolver:
    """
    Enhanced resolver for handling missing value issues in datasets.
    Integrates with MissingValueAnalysis results and provides multiple
    resolution strategies.
    """

    def __init__(self,
                 strategy: ResolutionStrategy = ResolutionStrategy.SIMPLE,
                 custom_imputers: Dict[str, Any] = None,
                 verification_threshold: float = 0.8):
        self.name = "missing_value_resolver"
        self.strategy = strategy
        self.custom_imputers = custom_imputers or {}
        self.verification_threshold = verification_threshold
        self.resolution_history: List[Dict[str, Any]] = []

    def validate_issues(self,
                        data: pd.DataFrame,
                        analysis_results: Dict[str, 'MissingValueAnalysis']) -> Dict[str, bool]:
        """
        Validates the missing value issues and determines if resolution is possible.
        """
        validation_results = {
            'valid_issues': True,
            'resolution_possible': True,
            'validation_details': {}
        }

        for column, analysis in analysis_results.items():
            column_validation = {
                'missing_percentage': analysis.missing_percentage,
                'can_resolve': True,
                'warnings': []
            }

            # Check if column exists in data
            if column not in data.columns:
                column_validation['can_resolve'] = False
                column_validation['warnings'].append(f"Column {column} not found in data")
                validation_results['valid_issues'] = False
                continue

            # Check if resolution is feasible based on missing percentage
            if analysis.missing_percentage == 100:
                column_validation['can_resolve'] = False
                column_validation['warnings'].append("Column is completely missing")
                validation_results['resolution_possible'] = False

            # Check if recommended action is feasible
            if analysis.recommended_action not in self._get_available_methods():
                column_validation['warnings'].append(
                    f"Recommended action {analysis.recommended_action} not available"
                )

            validation_results['validation_details'][column] = column_validation

        return validation_results

    def apply_resolution(self,
                         data: pd.DataFrame,
                         analysis_results: Dict[str, 'MissingValueAnalysis'],
                         validated_issues: Dict[str, bool]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Applies the appropriate resolution methods based on analysis results.
        """
        resolved_data = data.copy()
        resolution_details = {
            'methods_applied': {},
            'changes_made': {},
            'success_rate': 0.0
        }

        successful_columns = 0
        total_columns = len(analysis_results)

        for column, analysis in analysis_results.items():
            if not validated_issues['validation_details'][column]['can_resolve']:
                continue

            try:
                # Select imputation method based on analysis
                imputer = self._get_imputer(analysis)

                # Apply imputation
                if isinstance(imputer, (SimpleImputer, KNNImputer, IterativeImputer)):
                    resolved_data[column] = imputer.fit_transform(
                        resolved_data[[column]]
                    ).ravel()
                else:
                    resolved_data[column] = self._apply_custom_imputation(
                        resolved_data[column],
                        imputer,
                        analysis
                    )

                # Record changes
                resolution_details['methods_applied'][column] = str(analysis.recommended_action)
                resolution_details['changes_made'][column] = {
                    'original_missing': analysis.missing_count,
                    'remaining_missing': resolved_data[column].isna().sum()
                }
                successful_columns += 1

            except Exception as e:
                resolution_details['changes_made'][column] = {
                    'error': str(e),
                    'status': 'failed'
                }

        resolution_details['success_rate'] = successful_columns / total_columns
        return resolved_data, resolution_details

    def verify_resolution(self,
                          original_data: pd.DataFrame,
                          cleaned_data: pd.DataFrame,
                          resolution_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifies the quality of the resolution by comparing original and cleaned data.
        """
        verification_results = {
            'success': True,
            'metrics': {},
            'warnings': []
        }

        # Calculate overall metrics
        verification_results['metrics'] = self._calculate_verification_metrics(
            original_data, cleaned_data, resolution_details
        )

        # Check if verification meets threshold
        if verification_results['metrics']['overall_quality'] < self.verification_threshold:
            verification_results['success'] = False
            verification_results['warnings'].append(
                f"Overall quality {verification_results['metrics']['overall_quality']:.2f} "
                f"below threshold {self.verification_threshold}"
            )

        return verification_results

    def _calculate_verification_metrics(self,
                                        original_data: pd.DataFrame,
                                        cleaned_data: pd.DataFrame,
                                        resolution_details: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculates various metrics to verify the quality of the resolution.
        """
        metrics = {}

        # Calculate metrics for each resolved column
        for column in resolution_details['methods_applied'].keys():
            if original_data[column].dtype in ['int64', 'float64']:
                # Distribution similarity (if numerical)
                metrics[f"{column}_distribution_similarity"] = self._calculate_distribution_similarity(
                    original_data[column],
                    cleaned_data[column]
                )

                # Value range consistency
                metrics[f"{column}_range_consistency"] = self._check_range_consistency(
                    original_data[column],
                    cleaned_data[column]
                )

        # Overall quality score (weighted average of all metrics)
        metrics['overall_quality'] = np.mean(list(metrics.values()))

        return metrics

    def _calculate_distribution_similarity(self,
                                           original_series: pd.Series,
                                           cleaned_series: pd.Series) -> float:
        """
        Calculates similarity between original and cleaned data distributions.
        """
        # Remove missing values for comparison
        original_clean = original_series.dropna()

        if len(original_clean) == 0:
            return 1.0  # If original was all missing, any imputation is acceptable

        # Compare basic statistics
        orig_stats = original_clean.describe()
        clean_stats = cleaned_series.describe()

        # Calculate normalized difference in key statistics
        stat_diffs = []
        for stat in ['mean', 'std', 'min', 'max']:
            if orig_stats[stat] != 0:
                diff = abs(orig_stats[stat] - clean_stats[stat]) / abs(orig_stats[stat])
                stat_diffs.append(1 - min(diff, 1))
            else:
                stat_diffs.append(1 if clean_stats[stat] == 0 else 0)

        return np.mean(stat_diffs)

    def _check_range_consistency(self,
                                 original_series: pd.Series,
                                 cleaned_series: pd.Series) -> float:
        """
        Checks if imputed values maintain reasonable range consistency.
        """
        original_range = (original_series.dropna().min(), original_series.dropna().max())
        cleaned_range = (cleaned_series.min(), cleaned_series.max())

        # Calculate how many imputed values fall outside original range
        imputed_mask = original_series.isna()
        imputed_values = cleaned_series[imputed_mask]

        if len(imputed_values) == 0:
            return 1.0

        within_range = ((imputed_values >= original_range[0]) &
                        (imputed_values <= original_range[1])).mean()

        return within_range

    def _get_imputer(self, analysis: 'MissingValueAnalysis') -> Any:
        """
        Returns appropriate imputer based on analysis results.
        """
        if analysis.recommended_action == RecommendedAction.IMPUTE_MEAN:
            return SimpleImputer(strategy='mean')
        elif analysis.recommended_action == RecommendedAction.IMPUTE_MEDIAN:
            return SimpleImputer(strategy='median')
        elif analysis.recommended_action == RecommendedAction.IMPUTE_MODE:
            return SimpleImputer(strategy='most_frequent')
        elif analysis.recommended_action == RecommendedAction.IMPUTE_CUSTOM:
            if self.strategy == ResolutionStrategy.ADVANCED:
                return KNNImputer(n_neighbors=5)
            elif self.custom_imputers and analysis.column_name in self.custom_imputers:
                return self.custom_imputers[analysis.column_name]

        # Default to mean imputation
        return SimpleImputer(strategy='mean')

    def _apply_custom_imputation(self,
                                 series: pd.Series,
                                 imputer: Any,
                                 analysis: 'MissingValueAnalysis') -> pd.Series:
        """
        Applies custom imputation method to a series.
        """
        if callable(imputer):
            return imputer(series)
        elif isinstance(imputer, str) and imputer == 'ffill':
            return series.ffill()
        elif isinstance(imputer, str) and imputer == 'bfill':
            return series.bfill()
        else:
            raise ValueError(f"Invalid custom imputer for column {analysis.column_name}")

    def _get_available_methods(self) -> List[RecommendedAction]:
        """
        Returns list of available imputation methods based on strategy.
        """
        methods = [
            RecommendedAction.IMPUTE_MEAN,
            RecommendedAction.IMPUTE_MEDIAN,
            RecommendedAction.IMPUTE_MODE,
        ]

        if self.strategy == ResolutionStrategy.ADVANCED:
            methods.extend([
                RecommendedAction.IMPUTE_CUSTOM
            ])

        return methods

    def resolve(self,
                data: pd.DataFrame,
                analysis_results: Dict[str, 'MissingValueAnalysis']) -> ResolutionResult:
        """
        Main method to resolve missing values based on analysis results.
        """
        # Validate issues
        validated_issues = self.validate_issues(data, analysis_results)

        # Apply resolution
        cleaned_data, resolution_details = self.apply_resolution(
            data, analysis_results, validated_issues
        )

        # Verify results
        verification_results = self.verify_resolution(
            data, cleaned_data, resolution_details
        )

        # Document changes
        documentation = self.document_changes(resolution_details, verification_results)

        # Calculate quality metrics
        quality_metrics = self._calculate_verification_metrics(
            data, cleaned_data, resolution_details
        )

        # Record in history
        self.resolution_history.append(documentation)

        return ResolutionResult(
            cleaned_data=cleaned_data,
            resolution_details=resolution_details,
            verification_results=verification_results,
            documentation=documentation,
            quality_metrics=quality_metrics
        )

    def document_changes(self,
                         resolution_details: Dict[str, Any],
                         verification_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates detailed documentation of the resolution process.
        """
        documentation = {
            'timestamp': datetime.now().isoformat(),
            'changes': resolution_details,
            'verification': verification_results,
            'metadata': {
                'resolver_name': self.name,
                'strategy': self.strategy.value
            }
        }
        return documentation

    def get_resolution_report(self) -> Dict[str, Any]:
        """
        Generates a comprehensive report of all resolutions performed.
        """
        if not self.resolution_history:
            return {'error': 'No resolution history available'}

        # Calculate overall statistics
        success_rate = sum(1 for res in self.resolution_history
                           if res['verification']['success']) / len(self.resolution_history)

        # Aggregate metrics across all resolutions
        all_metrics = []
        for resolution in self.resolution_history:
            if 'metrics' in resolution['verification']:
                all_metrics.append(resolution['verification']['metrics'])

        avg_metrics = {}
        if all_metrics:
            for metric in all_metrics[0].keys():
                avg_metrics[metric] = np.mean([m[metric] for m in all_metrics])

        return {
            'summary': {
                'total_resolutions': len(self.resolution_history),
                'success_rate': success_rate,
                'average_metrics': avg_metrics
            },
            'resolution_history': self.resolution_history,
            'metadata': {
                'resolver_name': self.name,
                'strategy': self.strategy.value,
                'verification_threshold': self.verification_threshold
            }
        }


# Example usage:
if __name__ == "__main__":
    # Create sample data
    df = pd.DataFrame({
        'A': [1, np.nan, 3, np.nan, 5],
        'B': [np.nan, 2, np.nan, 4, np.nan],
        'C': [1, 2, 3, 4, 5],
        'D': [np.nan, np.nan, np.nan, np.nan, np.nan],
        'E': ['a', None, 'c', None, 'e'],
        'F': pd.date_range('2023-01-01', periods=5)
    })

    # First analyze the missing values
    analyzer = BasicDataValidator(df)
    analysis_results = analyzer.analyze_missing_values()

    # Create resolver with different strategies
    # Simple strategy
    simple_resolver = MissingValueResolver(strategy=ResolutionStrategy.SIMPLE)
    simple_result = simple_resolver.resolve(df, analysis_results)
    print("\nSimple Resolution Results:")
    print(simple_resolver.get_resolution_report()['summary'])

    # Advanced strategy
    advanced_resolver = MissingValueResolver(
        strategy=ResolutionStrategy.ADVANCED,
        verification_threshold=0.7
    )
    advanced_result = advanced_resolver.resolve(df, analysis_results)
    print("\nAdvanced Resolution Results:")
    print(advanced_resolver.get_resolution_report()['summary'])

    # Custom strategy with custom imputers
    custom_imputers = {
        'E': lambda x: x.fillna('missing'),  # Custom function for categorical
        'F': 'ffill'  # Forward fill for dates
    }
    custom_resolver = MissingValueResolver(
        strategy=ResolutionStrategy.CUSTOM,
        custom_imputers=custom_imputers
    )
    custom_result = custom_resolver.resolve(df, analysis_results)
    print("\nCustom Resolution Results:")
    print(custom_resolver.get_resolution_report()['summary'])

    # Compare results
    print("\nComparison of Different Strategies:")
    print("\nOriginal Data:")
    print(df.isnull().sum())

    print("\nSimple Resolution:")
    print(simple_result.cleaned_data.isnull().sum())

    print("\nAdvanced Resolution:")
    print(advanced_result.cleaned_data.isnull().sum())

    print("\nCustom Resolution:")
    print(custom_result.cleaned_data.isnull().sum())

    # Example of accessing quality metrics
    print("\nQuality Metrics for Simple Resolution:")
    for column, metrics in simple_result.quality_metrics.items():
        if isinstance(metrics, float):
            print(f"{column}: {metrics:.2f}")

    # Example of checking resolution details
    print("\nDetailed Resolution Changes:")
    for column, changes in simple_result.resolution_details['changes_made'].items():
        print(f"\nColumn: {column}")
        print(f"Original missing: {changes.get('original_missing', 'N/A')}")
        print(f"Remaining missing: {changes.get('remaining_missing', 'N/A')}")

    # Example of verification results
    print("\nVerification Results:")
    print(f"Success: {simple_result.verification_results['success']}")
    if 'warnings' in simple_result.verification_results:
        print("Warnings:", simple_result.verification_results['warnings'])