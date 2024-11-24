import pandas as pd
from ydata_profiling import ProfileReport
from backend.data_pipeline.analysis.quality_detector.basic_data_validation import BasicDataValidationQualityDetector
from backend.data_pipeline.analysis.quality_detector.text_standardization import TextStandardizationQualityDetector
from backend.data_pipeline.analysis.quality_detector.datetime_processing import DateTimeProcessingQualityDetector
from backend.data_pipeline.analysis.quality_detector.currency_processing import CurrencyProcessingQualityDetector
# from backend.data_pipeline.analysis.quality_detector.code_classification import CodeClassificationQualityDetector
from backend.data_pipeline.analysis.quality_detector.address_location import AddressLocationQualityDetector
# from backend.data_pipeline.analysis.quality_detector.duplication_management import DuplicationManagementQualityDetector
# from backend.data_pipeline.analysis.quality_detector.domain_specific_validation import DomainSpecificValidationQualityDetector
# from backend.data_pipeline.analysis.quality_detector.reference_data_management import ReferenceDataManagementQualityDetector



class DataQualityReport:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.report = {}

    def generate_category_reports(self):
        # Run all quality detectors for different categories
        self.report["Basic Data Validation"] = BasicDataValidationQualityDetector(self.data).run()
        self.report["Text Standardization"] = TextStandardizationQualityDetector(self.data).run()
        self.report["DateTime Processing"] = DateTimeProcessingQualityDetector(self.data).run()
        self.report["Currency Processing"] = CurrencyProcessingQualityDetector(self.data).run()
        # self.report["Code Classification"] = CodeClassificationQualityDetector(self.data).run()
        self.report["Address/Location"] = AddressLocationQualityDetector(self.data).run()
        # self.report["Duplication Management"] = DuplicationManagementQualityDetector(self.data).run()
        # self.report["Domain Specific Validation"] = DomainSpecificValidationQualityDetector(self.data).run()
        # self.report["Reference Data Management"] = ReferenceDataManagementQualityDetector(self.data).run()

    def generate_ydata_profiling_report(self):
        profile = ProfileReport(self.data, title="YData Profiling Report", explorative=True)
        profile.to_file("ydata_profiling_report.html")
        return "ydata_profiling_report.html"

    def generate_combined_report(self):
        # Generate category reports and YData profiling report
        self.generate_category_reports()
        profiling_report = self.generate_ydata_profiling_report()

        # Return a combined dictionary with both reports
        return {
            "ydata_profiling": profiling_report,
            "categorized_quality_issues": self.report,
        }


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

    # Generate the combined data quality report
    dq_report = DataQualityReport(sample_data)
    combined_report = dq_report.generate_combined_report()

    # Output the combined report
    print("Combined Data Quality Report:")
    print(combined_report["categorized_quality_issues"])
    print(f"YData Profiling saved at: {combined_report['ydata_profiling']}")
