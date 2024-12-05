import logging
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
from colorama import Fore, Style, init
from tabulate import tabulate
import time
import psutil
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial

# Initialize Colorama
init(autoreset=True)

# Set up logging
logger = logging.getLogger('age_issue_detector')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


@dataclass
class DetectionResult:
    """Standard structure for detection results."""
    issue_type: str
    field_name: str
    field_type: str
    total_rows: int
    issue_count: int
    issue_ratio: float


class AgeIssueDetector:
    """Detects age-related issues in a dataset and generates a styled report."""

    def detect_column(self, column: str, data: pd.DataFrame) -> List[DetectionResult]:
        """
        Detect age-related issues in a single column.

        Args:
            column (str): Column name.
            data (pd.DataFrame): Input DataFrame.

        Returns:
            List[DetectionResult]: Detection results for the column.
        """
        results = []

        try:
            if 'age' in column.lower() or 'dob' in column.lower() or 'birth' in column.lower():
                # Check for inconsistent units
                if pd.api.types.is_integer_dtype(data[column]):
                    unique_units = data[column].apply(lambda x: 'years' if x > 1000 else ('months' if x > 12 else 'days')).nunique()
                    if unique_units > 1:
                        results.append(
                            DetectionResult(
                                issue_type='inconsistent_units',
                                field_name=column,
                                field_type=str(data[column].dtype),
                                total_rows=len(data),
                                issue_count=len(data),
                                issue_ratio=1.0
                            )
                        )

                # Check for calculated age fields
                if 'age' in column.lower() and any(col for col in data.columns if 'dob' in col.lower() or 'birth' in col.lower()):
                    results.append(
                        DetectionResult(
                            issue_type='calculated_age_field',
                            field_name=column,
                            field_type=str(data[column].dtype),
                            total_rows=len(data),
                            issue_count=data[column].notna().sum(),
                            issue_ratio=data[column].notna().mean()
                        )
                    )

                # Check for invalid values
                if pd.api.types.is_integer_dtype(data[column]):
                    invalid_count = ((data[column] < 0) | (data[column] > 120)).sum()
                elif pd.api.types.is_datetime64_any_dtype(data[column]):
                    invalid_count = (data[column] > pd.Timestamp.now()).sum()
                else:
                    invalid_count = 0

                if invalid_count > 0:
                    results.append(
                        DetectionResult(
                            issue_type='invalid_values',
                            field_name=column,
                            field_type=str(data[column].dtype),
                            total_rows=len(data),
                            issue_count=invalid_count,
                            issue_ratio=invalid_count / len(data)
                        )
                    )

        except Exception as e:
            logger.error(f"Error processing column {column}: {e}")

        return results

    def detect_chunk(self, chunk: pd.DataFrame, columns: List[str]) -> List[DetectionResult]:
        """
        Detect age-related issues in a chunk of data.

        Args:
            chunk (pd.DataFrame): Chunk of data.
            columns (List[str]): List of column names to process.

        Returns:
            List[DetectionResult]: Detection results for the chunk.
        """
        results = []

        for column in columns:
            results.extend(self.detect_column(column, chunk))

        return results

    def detect(self, data: pd.DataFrame, num_threads: int = 4, chunk_size: int = 10**6) -> Dict[str, List[DetectionResult]]:
        """
        Detect age-related issues in the provided DataFrame.

        Args:
            data (pd.DataFrame): Input DataFrame.
            num_threads (int): Number of threads to use for column-wise detection.
            chunk_size (int): Number of rows per chunk for row-wise detection.

        Returns:
            Dict[str, List[DetectionResult]]: Detection results.
        """
        logger.info(f"Starting age-related issue detection for {len(data.columns)} columns.")
        detection_results = []

        # Column-wise detection with multithreading
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            column_results = list(executor.map(partial(self.detect_column, data=data), data.columns))
            detection_results.extend([result for results in column_results for result in results])

        # Row-wise detection with parallel processing
        chunk_results = []
        with ProcessPoolExecutor() as executor:
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i+chunk_size]
                chunk_results.append(executor.submit(self.detect_chunk, chunk, data.columns))

            for future in chunk_results:
                detection_results.extend(future.result())

        logger.info(f"Detection complete. Found {len(detection_results)} issues related to age fields.")
        return {
            'detected_items': detection_results
        }
    
    def generate_report(self, results: Dict[str, List[DetectionResult]], data: pd.DataFrame, duration: float) -> None:
        """
        Generate and display a styled table report of age-related issue detection results.

        Args:
            results (Dict[str, List[DetectionResult]]): Detection results from the `detect` method.
            data (pd.DataFrame): Input DataFrame to extract metadata.
            duration (float): Duration of the detection process.
        """
        print(f"\n{Fore.CYAN + Style.BRIGHT}Age-Related Issue Detection Report:{Style.RESET_ALL}\n")

        # Metadata Section
        total_columns = len(data.columns)
        memory_usage_mb = data.memory_usage(deep=True).sum() / (1024 * 1024)  # in MB

        metadata = [
            ["Total Columns", total_columns],
            ["Memory Usage", f"{memory_usage_mb:.2f} MB"],
            ["Detection Duration", f"{duration:.2f} seconds"],
            ["Age-Related Issues Found", len(results['detected_items'])],
        ]

        print(tabulate(metadata, headers=["Metadata", "Value"], tablefmt="fancy_grid", stralign="left"))

        if not results['detected_items']:
            print(f"\n{Fore.GREEN}No age-related issues detected in the dataset.")
            return

        # Main Table Section
        table_data = [
            [result.issue_type, result.field_name, result.field_type, result.total_rows, result.issue_count, f"{result.issue_ratio:.2%}"]
            for result in results['detected_items']
        ]

        headers = ["Issue Type", "Column", "Data Type", "Total Rows", "Issue Count", "Issue Ratio"]
        print(f"\n{Fore.CYAN + Style.BRIGHT}Detailed Age-Related Issue Information:{Style.RESET_ALL}\n")
        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid", stralign="center", numalign="center"))

        print(f"\n{Fore.CYAN}Detection completed. Total Age-Related Issues: {len(results['detected_items'])}{Style.RESET_ALL}")


# Example Usage
if __name__ == "__main__":
    # Simulated DataFrame already in the pipeline
# Simulated DataFrame already in the pipeline
    rows = 10**5
    start_date = pd.Timestamp.now() - pd.Timedelta(days=rows)
    data = pd.DataFrame({
        'customer_id': [1, 2, 3, 4, 5] * (rows // 5),
        'dob': pd.date_range(start=start_date, periods=rows, freq='D'),
        'age_years': [25, 30, 35, 40, 45] * (rows // 5),
        'age_months': [300, 360, 420, 480, 540] * (rows // 5),
        'age_days': [9125, 10950, 12775, 14600, 16425] * (rows // 5),
        'xyz': [-5, 0, 10, 120, 150] * (rows // 5),
    })

    # Detect age-related issues and generate report
    detector = AgeIssueDetector()
    start_time = time.time()
    detection_results = detector.detect(data, num_threads=4, chunk_size=10**6)
    end_time = time.time()

    detector.generate_report(detection_results, data, duration=end_time - start_time)