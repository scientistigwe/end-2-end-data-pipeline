from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from colorama import init, Fore, Back, Style
import numpy as np
import logging
from backend.backend.data_pipeline.quality_analysis.data_issue_analyser.basic_data_validation.analyse_missing_value import \
    MissingValueAnalyzer, AnalysisResult,  MissingValuePattern
from backend.backend.data_pipeline.quality_analysis.data_issue_detector.basic_data_validation.detect_missing_value import \
    MissingValueDetector, DetectionResult
from backend.backend.data_pipeline.quality_analysis.data_issue_resolver.basic_data_validation.resolved_missing_value import \
    MissingValueResolver, ResolutionResult, ResolutionCommand

logger = logging.getLogger(__name__)

init(autoreset=True)


@dataclass
class StageReport:
    """Container for stage-specific reporting data"""
    stage_name: str
    execution_time: float
    success: bool
    metadata: Dict[str, Any]
    results: Any  # Stage-specific results
    details: Dict[str, Any]  # Detailed information for each stage
    error_message: Optional[str] = None


@dataclass
class ProcessSummary:
    """Overall process summary including all stages"""
    total_fields: int
    fields_with_missing: int
    start_time: datetime
    end_time: datetime
    total_missing_count: int
    resolved_count: int
    stage_reports: Dict[str, StageReport]


class MissingValueReportHandler:
    """
    Coordinates the missing value handling pipeline and generates reports
    for each stage and final summary.
    """

    def __init__(self):
        self.detector = MissingValueDetector()
        self.analyzer = MissingValueAnalyzer()
        self.resolver = MissingValueResolver()
        self.start_time = None
        self.end_time = None

    def process_dataset(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, ProcessSummary]:
        """
        Process dataset through all stages and generate comprehensive reports.
        """
        try:
            self.start_time = datetime.now()

            # Initialize process summary
            total_fields = len(data.columns)
            initial_missing_count = data.isna().sum().sum()

            if initial_missing_count == 0:
                print(f"{Fore.GREEN}No missing values detected in the dataset.")
                return data, None

            # Execute pipeline stages
            detection_report = self._run_detection_stage(data)
            if not detection_report.success:
                print(f"{Fore.RED}Detection stage failed: {detection_report.error_message}")
                return data, None

            if not detection_report.results.get('detected_items'):
                print(f"{Fore.GREEN}No missing values detected in the dataset.")
                return data, None

            # Continue with analysis and resolution if detection was successful
            analysis_report = self._run_analysis_stage(data, detection_report.results)
            if not analysis_report.success:
                print(f"{Fore.RED}Analysis stage failed: {analysis_report.error_message}")
                return data, None

            resolved_data, resolution_report = self._run_resolution_stage(
                data, analysis_report.results
            )

            # Generate process summary
            self.end_time = datetime.now()
            summary = self._create_process_summary(
                data=data,
                resolved_data=resolved_data,
                total_fields=total_fields,
                stage_reports={
                    'detection': detection_report,
                    'analysis': analysis_report,
                    'resolution': resolution_report
                }
            )

            # Print reports
            self._print_detection_report(detection_report)
            self._print_analysis_report(analysis_report)
            self._print_resolution_report(resolution_report)
            self._print_process_summary(summary)

            return resolved_data, summary

        except Exception as e:
            print(f"{Fore.RED}Error processing dataset: {str(e)}")
            return data, None

    def _run_detection_stage(self, data: pd.DataFrame) -> StageReport:
        """Execute detection stage and generate report"""
        stage_start = datetime.now()
        try:
            # Run detection
            results = self.detector.detect(data)
            execution_time = (datetime.now() - stage_start).total_seconds()

            # Format details for reporting
            details = {
                'fields': {}
            }

            # Process each detected item
            for item in results['detected_items']:
                details['fields'][item.field_name] = {
                    'type': item.field_type,
                    'missing_count': item.missing_count,
                    'missing_ratio': item.detection_metadata['missing_ratio'],
                    'pattern_info': item.detection_metadata['pattern_info'],
                    'related_fields': item.detection_metadata['related_fields']
                }

            return StageReport(
                stage_name="Detection",
                execution_time=execution_time,
                success=True,
                metadata={
                    'fields_analyzed': len(data.columns),
                    'fields_with_missing': len(results['detected_items'])
                },
                results=results,
                details=details
            )
        except Exception as e:
            print(f"{Fore.RED}Detection stage error: {str(e)}")
            return StageReport(
                stage_name="Detection",
                execution_time=0.0,
                success=False,
                metadata={},
                results={},
                details={},
                error_message=str(e)
            )

    def _run_analysis_stage(self, data: pd.DataFrame,
                            detection_results: Dict[str, List[DetectionResult]]) -> StageReport:
        """Execute analysis stage and generate detailed report"""
        stage_start = datetime.now()
        try:
            results = self.analyzer.analyze(data)
            execution_time = (datetime.now() - stage_start).total_seconds()

            # Prepare detailed analysis information
            details = {
                'field_analysis': {
                    field: {
                        'pattern': result.pattern.value,
                        'mechanism': result.mechanism.value,
                        'missing_percentage': result.missing_percentage,
                        'recommendation': result.recommendation,
                        'total_count': result.total_count,
                        'missing_count': result.missing_count
                    }
                    for field, result in results.items()
                }
            }

            return StageReport(
                stage_name="Analysis",
                execution_time=execution_time,
                success=True,
                metadata={
                    'fields_analyzed': len(detection_results['detected_items']),
                    'patterns_identified': self._count_patterns(results)
                },
                results=results,
                details=details
            )
        except Exception as e:
            return StageReport(
                stage_name="Analysis",
                execution_time=0.0,
                success=False,
                metadata={},
                results={},
                details={},
                error_message=str(e)
            )

    def _run_resolution_stage(self, data: pd.DataFrame, analysis_results: Dict[str, AnalysisResult]) -> Tuple[
        pd.DataFrame, StageReport]:
        """Execute resolution stage and generate detailed report"""
        stage_start = datetime.now()
        try:
            # Create resolution commands from analysis results
            resolution_commands = []
            for field_name, analysis in analysis_results.items():
                if analysis.missing_count > 0:
                    # Get recommended strategy
                    strategy_name = self.resolver._map_recommendation_to_strategy(
                        analysis.recommendation['action']
                    )
                    strategy = self.resolver.strategy_registry[strategy_name]  # Use direct access instead of get()

                    # Always create command for fields with missing values
                    resolution_commands.append(
                        ResolutionCommand(
                            field_name=field_name,
                            approved=True,  # By default approve all recommendations
                            selected_strategy=strategy,
                            custom_params=None
                        )
                    )

            # Apply resolutions
            resolved_data, resolution_results = self.resolver.resolve(
                data=data,
                analysis_results=analysis_results,
                resolution_commands=resolution_commands
            )

            execution_time = (datetime.now() - stage_start).total_seconds()

            # Calculate resolution statistics
            field_resolutions = {}
            total_missing = 0
            total_resolved = 0

            field_resolutions = {}
            for result in resolution_results:
                field_resolutions[result.field_name] = {
                    'strategy': result.strategy_used.method,
                    'success': result.success,
                    'original_missing': result.original_missing,
                    'resolved_missing': result.resolved_missing,
                    'resolved_count': result.original_missing - result.resolved_missing,
                    'metrics': result.metrics,
                    'validation_results': result.validation_results,
                    'error': result.error_message if not result.success else None
                }

            details = {
                'field_resolutions': field_resolutions,
                'total_statistics': {
                    'total_missing': total_missing,
                    'total_resolved': total_resolved,
                    'resolution_rate': (total_resolved / total_missing) if total_missing > 0 else 0.0
                }
            }

            return resolved_data, StageReport(
                stage_name="Resolution",
                execution_time=execution_time,
                success=True,
                metadata={
                    'fields_resolved': len(resolution_results),
                    'successful_resolutions': len([r for r in resolution_results if r.success]),
                    'total_missing': total_missing,
                    'total_resolved': total_resolved
                },
                results=resolution_results,
                details=details
            )

        except Exception as e:
            print(f"Resolution stage error: {str(e)}")
            return data, StageReport(
                stage_name="Resolution",
                execution_time=0.0,
                success=False,
                metadata={},
                results=[],
                details={},
                error_message=str(e)
            )

    def _print_detection_report(self, report: StageReport) -> None:
        """Print detailed detection report"""
        print(f"\n{Back.BLUE}{Fore.WHITE} DETECTION STAGE REPORT {Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'-' * 80}")
        print(f"{Fore.WHITE}Execution Time: {Fore.YELLOW}{report.execution_time:.2f} seconds")
        print(f"{Fore.WHITE}Status: {self._format_status(report.success)}")

        if report.error_message:
            print(f"{Fore.RED}Error: {report.error_message}")
            return

        if not report.details.get('fields'):
            print(f"{Fore.YELLOW}No missing values detected in the dataset.")
            return

        print(f"\n{Fore.CYAN}Field-Level Detection Results:")
        for field_name, details in report.details['fields'].items():
            print(f"\n{Fore.WHITE}Field: {Fore.YELLOW}{field_name}")
            print(f"{Fore.WHITE}  Type: {Fore.CYAN}{details['type']}")
            print(f"{Fore.WHITE}  Missing Values: {Fore.RED}{details['missing_count']:,} "
                  f"({details['missing_ratio']:.1%})")

            # Print pattern information
            if 'pattern_info' in details:
                pattern_desc = details['pattern_info'].get('description', 'Unknown pattern')
                print(f"{Fore.WHITE}  Pattern: {Fore.YELLOW}{pattern_desc}")

            # Print related fields if any
            if details.get('related_fields'):
                print(f"{Fore.WHITE}  Related Fields: {Fore.CYAN}{', '.join(details['related_fields'])}")

    def _print_analysis_report(self, report: StageReport) -> None:
        """Print detailed analysis report"""
        print(f"\n{Back.BLUE}{Fore.WHITE} ANALYSIS STAGE REPORT {Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'-' * 80}")
        print(f"{Fore.WHITE}Execution Time: {Fore.YELLOW}{report.execution_time:.2f} seconds")
        print(f"{Fore.WHITE}Status: {self._format_status(report.success)}")

        if report.error_message:
            print(f"{Fore.RED}Error: {report.error_message}")
            return

        print(f"\n{Fore.CYAN}Field-Level Analysis Results:")
        for field_name, analysis in report.details['field_analysis'].items():
            print(f"\n{Fore.WHITE}Field: {Fore.YELLOW}{field_name}")
            print(f"{Fore.WHITE}  Pattern: {Fore.CYAN}{analysis['pattern']}")
            print(f"{Fore.WHITE}  Mechanism: {Fore.CYAN}{analysis['mechanism']}")
            print(f"{Fore.WHITE}  Missing Values: {Fore.RED}{analysis['missing_count']:,} "
                  f"({analysis['missing_percentage']:.1f}%)")

            # Print recommendation with confidence color
            confidence = analysis['recommendation']['confidence']
            confidence_color = (Fore.GREEN if confidence > 0.8 else
                                (Fore.YELLOW if confidence > 0.6 else Fore.RED))

            print(f"{Fore.WHITE}  Recommendation: {Fore.CYAN}{analysis['recommendation']['description']}")
            print(f"{Fore.WHITE}  Confidence: {confidence_color}{confidence:.2f}")
            print(f"{Fore.WHITE}  Reason: {Fore.CYAN}{analysis['recommendation']['reason']}")

    def _print_resolution_report(self, report: StageReport) -> None:
        """Print detailed resolution report"""
        print(f"\n{Back.BLUE}{Fore.WHITE} RESOLUTION STAGE REPORT {Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'-' * 80}")
        print(f"{Fore.WHITE}Execution Time: {Fore.YELLOW}{report.execution_time:.2f} seconds")
        print(f"{Fore.WHITE}Status: {self._format_status(report.success)}")

        if report.error_message:
            print(f"{Fore.RED}Error: {report.error_message}")
            return

        print(f"\n{Fore.CYAN}Field-Level Resolution Results:")
        total_original_missing = 0
        total_resolved = 0

        for field_name, details in report.details['field_resolutions'].items():
            original_missing = details['original_missing']
            resolved_missing = details['resolved_missing']

            if details['strategy'] == 'complete_missingness':
                resolved_count = original_missing  # All values resolved by dropping
            else:
                resolved_count = original_missing - resolved_missing

            total_original_missing += original_missing
            total_resolved += resolved_count if details['success'] else 0

            print(f"\n{Fore.WHITE}Field: {Fore.YELLOW}{field_name}")
            print(f"{Fore.WHITE}  Strategy: {Fore.CYAN}{details['strategy']}")
            print(f"{Fore.WHITE}  Status: {self._format_status(details['success'])}")
            print(f"{Fore.WHITE}  Missing Values: {Fore.RED}{original_missing:,} → {resolved_missing:,} "
                  f"(Resolved: {resolved_count:,})")

            if details['success']:
                if details['metrics']:
                    print(f"{Fore.WHITE}  Resolution Rate: "
                          f"{self._format_percentage(resolved_count / original_missing)}")
            else:
                print(f"{Fore.RED}  Error: {details['error']}")

        # Print overall statistics
        if total_original_missing > 0:
            overall_rate = total_resolved / total_original_missing
            print(f"\n{Fore.WHITE}Overall Resolution Statistics:")
            print(f"{Fore.WHITE}Total Missing Values: {Fore.YELLOW}{total_original_missing:,}")
            print(f"{Fore.WHITE}Total Resolved: {Fore.YELLOW}{total_resolved:,} "
                  f"({self._format_percentage(overall_rate)})")

    def _create_process_summary(self, data: pd.DataFrame, resolved_data: pd.DataFrame,
                                total_fields: int, stage_reports: Dict[str, StageReport]) -> ProcessSummary:
        """Create overall process summary with corrected resolution stats"""
        resolution_report = stage_reports['resolution']

        # Calculate resolution statistics
        total_missing = 0
        total_resolved = 0

        if 'field_resolutions' in resolution_report.details:
            for details in resolution_report.details['field_resolutions'].values():
                original_missing = details['original_missing']
                total_missing += original_missing

                if details['success']:
                    if 'complete_missingness' in details['strategy']:
                        # For dropped columns, count all missing values as resolved
                        total_resolved += original_missing
                    else:
                        # For other strategies, use the difference
                        total_resolved += original_missing - details['resolved_missing']

        return ProcessSummary(
            total_fields=total_fields,
            fields_with_missing=len(stage_reports['detection'].results['detected_items']),
            start_time=self.start_time,
            end_time=self.end_time,
            total_missing_count=total_missing,
            resolved_count=total_resolved,
            stage_reports=stage_reports
        )

    def _count_patterns(self, analysis_results: Dict[str, AnalysisResult]) -> Dict[str, int]:
        """Count occurrences of each missing value pattern"""
        pattern_counts = {}
        for result in analysis_results.values():
            pattern = result.pattern.value
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        return pattern_counts

    def _print_process_summary(self, summary: ProcessSummary) -> None:
        """Print comprehensive process summary with detailed statistics"""
        print(f"\n{Back.BLUE}{Fore.WHITE} MISSING VALUE RESOLUTION SUMMARY {Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'=' * 80}")

        # Dataset Overview
        print(f"{Fore.GREEN}Dataset Overview:")
        print(f"{Fore.WHITE}Total Fields in Dataset: {Fore.YELLOW}{summary.total_fields}")
        print(f"{Fore.WHITE}Fields with Missing Values: {Fore.YELLOW}{summary.fields_with_missing}")

        # Detailed Missing Value Statistics
        resolution_report = summary.stage_reports['resolution']
        missing_fields = []
        field_statistics = {}

        if 'field_resolutions' in resolution_report.details:
            for field_name, details in resolution_report.details['field_resolutions'].items():
                missing_fields.append({
                    'name': field_name,
                    'original': details['original_missing'],
                    'remaining': details['resolved_missing'],
                    'resolved': details['original_missing'] - details['resolved_missing'],
                    'success': details['success']
                })

        # Print Missing Value Details by Field
        print(f"\n{Fore.GREEN}Missing Value Details by Field:")
        print(f"{Fore.BLUE}{'-' * 80}")
        print(f"{Fore.CYAN}{'Field Name':<30} {'Original MV':>12} {'Resolved':>12} {'Remaining':>12} {'Rate':>8}")
        print(f"{Fore.BLUE}{'-' * 80}")

        total_original = 0
        total_resolved = 0
        total_remaining = 0

        for field in missing_fields:
            total_original += field['original']
            total_resolved += field['resolved']
            total_remaining += field['remaining']

            resolution_rate = (field['resolved'] / field['original'] * 100) if field['original'] > 0 else 0
            status_color = Fore.GREEN if field['success'] else Fore.RED

            print(f"{status_color}{field['name']:<30} {field['original']:>12,} {field['resolved']:>12,} "
                  f"{field['remaining']:>12,} {resolution_rate:>7.1f}%")

        print(f"{Fore.BLUE}{'-' * 80}")
        total_rate = (total_resolved / total_original * 100) if total_original > 0 else 0
        print(f"{Fore.WHITE}{'TOTAL':<30} {total_original:>12,} {total_resolved:>12,} "
              f"{total_remaining:>12,} {total_rate:>7.1f}%")

        # Resolution Performance
        print(f"\n{Fore.GREEN}Resolution Performance:")
        print(f"{Fore.BLUE}{'-' * 80}")
        successful_fields = sum(1 for f in missing_fields if f['success'])
        print(f"{Fore.WHITE}Successfully Processed Fields: {Fore.YELLOW}{successful_fields} of {len(missing_fields)}")
        print(f"{Fore.WHITE}Total Missing Values: {Fore.YELLOW}{total_original:,}")
        print(f"{Fore.WHITE}Successfully Resolved: {Fore.YELLOW}{total_resolved:,} ({total_rate:.1f}%)")
        print(f"{Fore.WHITE}Remaining Missing Values: {Fore.YELLOW}{total_remaining:,}")

        # Execution Statistics
        print(f"\n{Fore.GREEN}Execution Statistics:")
        print(f"{Fore.BLUE}{'-' * 80}")
        duration = (summary.end_time - summary.start_time).total_seconds()
        print(f"{Fore.WHITE}Total Duration: {Fore.YELLOW}{duration:.2f} seconds")

        # Methods Used
        print(f"\n{Fore.GREEN}Resolution Methods Used:")
        print(f"{Fore.BLUE}{'-' * 80}")
        methods_used = {}
        for field in resolution_report.details['field_resolutions'].values():
            method = field['strategy']
            methods_used[method] = methods_used.get(method, 0) + 1

        for method, count in methods_used.items():
            print(f"{Fore.WHITE}{method}: {Fore.YELLOW}{count} field(s)")

        # Print any warnings or notes
        if total_remaining > 0:
            print(f"\n{Fore.YELLOW}Note: {total_remaining:,} missing values could not be resolved. "
                  f"Consider reviewing the resolution strategies for affected fields.")

        print(f"\n{Fore.BLUE}{'=' * 80}")

    def _format_status(self, success: bool) -> str:
        """Format success/failure status with color"""
        return f"{Fore.GREEN}✓ Success" if success else f"{Fore.RED}✗ Failed"

    def _format_percentage(self, value: float) -> str:
        """Format percentage with color based on value"""
        color = Fore.GREEN if value >= 0.8 else (Fore.YELLOW if value >= 0.5 else Fore.RED)
        return f"{color}{value:.1%}"


def create_test_data_with_patterns():
    """Create test data with specific missing value patterns"""

    # Create base dataset
    np.random.seed(42)
    n_rows = 1000
    date_range = pd.date_range(start='2023-01-01', periods=n_rows, freq='h')

    data = pd.DataFrame({
        # Temporal pattern (missing every 24 hours)
        'temporal_series': np.random.normal(100, 15, n_rows),

        # Structural pattern (missing based on another variable)
        'predictor': np.random.normal(0, 1, n_rows),
        'structural_dependent': np.random.normal(50, 10, n_rows),

        # Complete missing
        'complete_missing': [np.nan] * n_rows,

        # Random missing (20% missing at random)
        'random_missing': np.random.normal(75, 20, n_rows),

        # Partial missing (missing in specific range)
        'partial_missing': np.random.normal(60, 12, n_rows),

        'timestamp': date_range
    })

    # Add temporal missing pattern (every 24 hours + some noise)
    temporal_mask = (np.arange(n_rows) % 24 == 0)
    data.loc[temporal_mask, 'temporal_series'] = np.nan

    # Add structural missing pattern
    structural_mask = (data['predictor'] > 1.5)  # Missing when predictor > 1.5 std
    data.loc[structural_mask, 'structural_dependent'] = np.nan

    # Add random missing values
    random_mask = np.random.random(n_rows) < 0.2
    data.loc[random_mask, 'random_missing'] = np.nan

    # Add partial missing values (missing in middle section)
    start_idx = n_rows // 3
    end_idx = (2 * n_rows) // 3
    data.loc[start_idx:end_idx, 'partial_missing'] = np.nan

    return data


def test_missing_value_pipeline():
    """Test the entire missing value pipeline"""

    # Create test data
    data = create_test_data_with_patterns()

    # Initialize handlers
    detector = MissingValueDetector()
    analyzer = MissingValueAnalyzer()
    resolver = MissingValueResolver()
    report_handler = MissingValueReportHandler()

    # Process the dataset
    print("\nProcessing dataset with various missing value patterns...\n")

    resolved_data, process_summary = report_handler.process_dataset(data)



if __name__ == "__main__":
    test_missing_value_pipeline()