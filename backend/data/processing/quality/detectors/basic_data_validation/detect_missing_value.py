import logging
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
from colorama import Fore, Style, init
from tabulate import tabulate
import time
import psutil

# Initialize Colorama
init(autoreset=True)

# Set up logging
logger = logging.getLogger('missing_value_detector')
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
    missing_count: int
    missing_ratio: float


class MissingValueDetector:
    """Detects missing values in a dataset and generates a styled report."""

    def detect(self, data: pd.DataFrame) -> Dict[str, List[DetectionResult]]:
        """
        Detect missing values in the provided DataFrame.

        Args:
            data (pd.DataFrame): Input DataFrame.

        Returns:
            Dict[str, List[DetectionResult]]: Detection results.
        """
        logger.info(f"Starting missing value detection for {len(data.columns)} columns.")
        detection_results = []

        for column in data.columns:
            try:
                missing_count = data[column].isna().sum()
                total_rows = len(data)
                if missing_count > 0:
                    logger.info(f"Detected missing values in column: {column} | Missing Count: {missing_count}")
                    detection_results.append(
                        DetectionResult(
<<<<<<< HEAD
                            issue_type='templates',
=======
                            issue_type='missing_value',
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
                            field_name=column,
                            field_type=str(data[column].dtype),
                            total_rows=total_rows,
                            missing_count=missing_count,
                            missing_ratio=missing_count / total_rows
                        )
                    )
            except Exception as e:
                logger.error(f"Error processing column {column}: {e}")

        logger.info(f"Detection complete. Found {len(detection_results)} columns with missing values.")
        return {
<<<<<<< HEAD
            'issue_type': 'templates',
=======
            'issue_type': 'missing_value',
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
            'detected_items': detection_results
        }

    def generate_report(self, results: Dict[str, List[DetectionResult]], data: pd.DataFrame, duration: float) -> None:
        """
        Generate and display a styled table report of missing value detection results.

        Args:
            results (Dict[str, List[DetectionResult]]): Detection results from the `detect` method.
            data (pd.DataFrame): Input DataFrame to extract metadata.
            duration (float): Duration of the detection process.
        """
        print(f"\n{Fore.CYAN + Style.BRIGHT}Missing Value Detection Report:{Style.RESET_ALL}\n")

        # Metadata Section
        total_columns = len(data.columns)
        memory_usage_mb = data.memory_usage(deep=True).sum() / (1024 * 1024)  # in MB

        metadata = [
            ["Total Columns", total_columns],
            ["Memory Usage", f"{memory_usage_mb:.2f} MB"],
            ["Detection Duration", f"{duration:.2f} seconds"],
            ["Columns with Missing Values", len(results['detected_items'])],
        ]

        print(tabulate(metadata, headers=["Metadata", "Value"], tablefmt="fancy_grid", stralign="left"))

        if not results['detected_items']:
            print(f"\n{Fore.GREEN}No missing values detected in the dataset.")
            return

        # Main Table Section
        table_data = [
            [result.field_name, result.field_type, result.total_rows, result.missing_count, f"{result.missing_ratio:.2%}"]
            for result in results['detected_items']
        ]

        headers = ["Column", "Data Type", "Total Rows", "Missing Count", "Missing Ratio"]
        print(f"\n{Fore.CYAN + Style.BRIGHT}Detailed Missing Values Information:{Style.RESET_ALL}\n")
        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid", stralign="center", numalign="center"))

        print(f"\n{Fore.CYAN}Detection completed. Total Columns with Missing Values: {len(results['detected_items'])}{Style.RESET_ALL}")


# Example Usage
if __name__ == "__main__":
    # Simulated DataFrame already in the pipeline
    rows = 10**6
    data = pd.DataFrame({
        'A': [1, None, 3, None, 5] * (rows // 5),
        'B': [None, None, 3, 4, 5] * (rows // 5),
        'C': [1, 2, None, None, None] * (rows // 5),
        'D': [1, 2, 3, 4, 5] * (rows // 5),
    })

    # Detect missing values and generate report
    detector = MissingValueDetector()
    start_time = time.time()
    detection_results = detector.detect(data)
    end_time = time.time()

    detector.generate_report(detection_results, data, duration=end_time - start_time)
