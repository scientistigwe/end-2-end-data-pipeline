# backend/data_pipeline/insight/quality_report_generator.py

import logging
import pandas as pd
from ydata_profiling import ProfileReport
import colorama
from colorama import Fore, Style
from datetime import datetime
from tabulate import tabulate
try:
    from backend.data_pipeline.analysis.quality_detector.basic_data_validation import BasicDataValidationQualityDetector
    from backend.data_pipeline.analysis.quality_detector.datetime_processing import DateTimeProcessingQualityDetector
    from backend.data_pipeline.analysis.quality_detector.currency_processing import CurrencyQualityDetector
    from backend.data_pipeline.analysis.quality_detector.address_location import AddressLocationQualityDetector
    from backend.data_pipeline.analysis.quality_detector.duplication_management import DuplicateDetector

    # Make text standardization import optional
    from backend.data_pipeline.analysis.quality_detector.text_standardization import TextStandardizationQualityDetector
    TEXT_STANDARDIZATION_AVAILABLE = True
except ImportError:
    TEXT_STANDARDIZATION_AVAILABLE = False

logger = logging.getLogger(__name__)
colorama.init()

class QualityReportGenerator:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.start_time = datetime.now()

    def print_section_header(self, title: str):
        print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{title}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}\n")

    def print_subsection_header(self, title: str):
        print(f"\n{Fore.YELLOW}{title}:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'-' * 40}{Style.RESET_ALL}")

    def generate_reports(self):
        results = {}

        # Print overall insight start
        self.print_section_header("Data Quality Analysis Report")
        results['analysis_start'] = self.start_time.strftime('%Y-%m-%d %H:%M:%S')
        results['dataset_info'] = {
            'rows': len(self.data),
            'columns': len(self.data.columns)
        }

        # Basic Data Validation
        self.print_section_header("Basic Data Validation Report")
        basic_validation = BasicDataValidationQualityDetector(self.data)
        results['basic_validation'] = basic_validation.run()

        # Text Standardization (if available)
        if TEXT_STANDARDIZATION_AVAILABLE:
            self.print_section_header("Text Standardization Report")
            text_standard = TextStandardizationQualityDetector(self.data)
            results['text_standardization'] = text_standard.run()
        else:
            logger.warning("Text standardization module not available - skipping")
            results['text_standardization'] = {
                "status": "skipped",
                "reason": "Module dependencies not available"
            }

        # DateTime Processing
        self.print_section_header("DateTime Processing Report")
        datetime_proc = DateTimeProcessingQualityDetector(self.data)
        results['datetime_processing'] = datetime_proc.run()

        # Currency Processing
        self.print_section_header("Currency Processing Report")
        currency_proc = CurrencyQualityDetector(self.data)
        results['currency_processing'] = currency_proc.run()

        # Address/Location
        self.print_section_header("Address/Location Analysis Report")
        address_loc = AddressLocationQualityDetector(self.data)
        results['address_location'] = address_loc.run()

        # Duplication Management
        self.print_section_header("Duplication Analysis Report")
        duplicate_detector = DuplicateDetector(near_match_threshold=0.3)
        results['duplication'] = duplicate_detector.run_analysis(self.data)

        # YData Profiling
        self.print_section_header("Generating YData Profiling Report")
        profile = ProfileReport(self.data, title="YData Profiling Report", explorative=True)
        report_path = "ydata_profiling_report.html"
        profile.to_file(report_path)
        results['ydata_profile_path'] = report_path

        # Analysis Summary
        execution_time = (datetime.now() - self.start_time).total_seconds()
        results['execution_summary'] = {
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'execution_time': f"{execution_time:.2f}",
            'rows_analyzed': len(self.data),
            'columns_analyzed': len(self.data.columns),
            'reports_generated': 6 if not TEXT_STANDARDIZATION_AVAILABLE else 7
        }

        return results

if __name__ == "__main__":
    # Sample data for testing
    sample_data = pd.DataFrame({
        "Name": ["Alice", "Bob", None, "ALICE", "Bob"],
        "Age": [25, 30, None, 25, 30],
        "Email": ["alice@example.com", None, "", "ALICE@example.com", "bob@example.com"],
        "Code": ["123", "456", "123", "789", "123"],
        "date": ["2023/12/2", "2-10-2022", "22.04.08", "20/02/2021", None],
        "profit": ["1000", "1500", "$5000", "-3000", "Invalid"]
    })

    # Test the report generator
    report_generator = QualityReportGenerator(sample_data)
    report_generator.generate_reports()