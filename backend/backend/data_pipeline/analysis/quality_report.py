import pandas as pd
from ydata_profiling import ProfileReport
import colorama
from colorama import Fore, Style
from datetime import datetime
from tabulate import tabulate
from backend.data_pipeline.analysis.quality_detector.basic_data_validation import BasicDataValidationQualityDetector
from backend.data_pipeline.analysis.quality_detector.text_standardization import TextStandardizationQualityDetector
from backend.data_pipeline.analysis.quality_detector.datetime_processing import DateTimeProcessingQualityDetector
from backend.data_pipeline.analysis.quality_detector.currency_processing import CurrencyProcessingQualityDetector
from backend.data_pipeline.analysis.quality_detector.address_location import AddressLocationQualityDetector
from backend.data_pipeline.analysis.quality_detector.duplication_management import DuplicateDetector
# from backend.data_pipeline.analysis.quality_detector.code_classification import CodeClassificationQualityDetector
# from backend.data_pipeline.analysis.quality_detector.domain_specific_validation import DomainSpecificValidationQualityDetector
# from backend.data_pipeline.analysis.quality_detector.reference_data_management import ReferenceDataManagementQualityDetector

colorama.init()

class DataQualityReport:
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
        # Print overall analysis start
        self.print_section_header("Data Quality Analysis Report")
        print(f"Analysis started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Analyzing dataset with {len(self.data):,} rows and {len(self.data.columns):,} columns\n")

        # Basic Data Validation
        self.print_section_header("Basic Data Validation Report")
        basic_validation = BasicDataValidationQualityDetector(self.data)
        basic_results = basic_validation.run()
        print(basic_results)

        # Text Standardization
        self.print_section_header("Text Standardization Report")
        text_standard = TextStandardizationQualityDetector(self.data)
        text_results = text_standard.run()
        print(text_results)

        # DateTime Processing
        self.print_section_header("DateTime Processing Report")
        datetime_proc = DateTimeProcessingQualityDetector(self.data)
        datetime_results = datetime_proc.run()
        print(datetime_results)

        # Currency Processing
        self.print_section_header("Currency Processing Report")
        currency_proc = CurrencyProcessingQualityDetector(self.data)
        currency_results = currency_proc.run()
        print(currency_results)

        # Address/Location
        self.print_section_header("Address/Location Analysis Report")
        address_loc = AddressLocationQualityDetector(self.data)
        address_results = address_loc.run()
        print(address_results)

        # Duplication Management
        self.print_section_header("Duplication Analysis Report")
        duplicate_detector = DuplicateDetector(
            near_match_threshold=0.3
        )

        # Pass the data to run_analysis instead of accessing it internally
        duplication_report = duplicate_detector.run_analysis(self.data)
        print(duplication_report)

        # YData Profiling (Optional - generates HTML report)
        self.print_section_header("Generating YData Profiling Report")
        profile = ProfileReport(self.data, title="YData Profiling Report", explorative=True)
        report_path = "ydata_profiling_report.html"
        profile.to_file(report_path)
        print(f"{Fore.GREEN}YData Profiling report saved at: {report_path}{Style.RESET_ALL}")

        # Analysis Summary
        execution_time = (datetime.now() - self.start_time).total_seconds()
        self.print_section_header("Analysis Summary")
        summary_table = [
            ["Analysis Start Time", self.start_time.strftime('%Y-%m-%d %H:%M:%S')],
            ["Total Execution Time", f"{execution_time:.2f} seconds"],
            ["Rows Analyzed", f"{len(self.data):,}"],
            ["Columns Analyzed", f"{len(self.data.columns):,}"],
            ["Reports Generated", "7 (including YData Profiling)"]
        ]
        print(tabulate(summary_table, tablefmt='grid'))


# Example Usage
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

    # Generate and display reports
    dq_report = DataQualityReport(sample_data)
    dq_report.generate_reports()