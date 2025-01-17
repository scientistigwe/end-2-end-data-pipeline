import logging
from dataclasses import dataclass
from typing import List, Dict
import pandas as pd
import numpy as np
from colorama import Fore, Style, init
from tabulate import tabulate
import time
import psutil
import gc

# Initialize Colorama
init(autoreset=True)

# Set up logging
logger = logging.getLogger('data_type_detector')
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
    expected_type: str
    detected_type: str
    total_rows: int
    invalid_count: int
    mismatch_ratio: float
    sample_invalid_values: List


class DataTypeMismatchDetector:
    """Memory-efficient detector for data type mismatches in large datasets."""

    def _get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)

    def _validate_numeric(self, series: pd.Series, expected_type: str) -> np.ndarray:
        """Vectorized validation for numeric types."""
        # Start with null check
        valid = pd.notna(series).to_numpy()

        if not valid.any():
            return valid

        # Convert to numeric, setting errors to null
        numeric_series = pd.to_numeric(series, errors='coerce')

        # Update valid mask for failed conversions
        valid &= pd.notna(numeric_series).to_numpy()

        if expected_type == 'int64':
            # Efficient integer check using modulo
            valid &= (numeric_series % 1 == 0).to_numpy()

        return valid

    def _validate_boolean(self, series: pd.Series) -> np.ndarray:
        """Vectorized validation for boolean types."""
        # Valid boolean values
        bool_values = {True, False, 1, 0, '1', '0', 'true', 'false', 'True', 'False'}
        return series.isin(bool_values).to_numpy()

    def _chunk_iterator(self, df: pd.DataFrame, chunk_size: int = 1_000_000):
        """Memory-efficient chunk iterator."""
        total_rows = len(df)
        for start_idx in range(0, total_rows, chunk_size):
            end_idx = min(start_idx + chunk_size, total_rows)
            yield df.iloc[start_idx:end_idx]

    def detect(self, data: pd.DataFrame, expected_types: Dict[str, str],
               chunk_size: int = 1_000_000) -> Dict[str, List[DetectionResult]]:
        """
        Memory-efficient detection of data type mismatches.

        Args:
            data (pd.DataFrame): Input DataFrame
            expected_types (Dict[str, str]): Expected types ('int64', 'float64', 'str', 'bool')
            chunk_size (int): Number of rows to process at once
        """
        initial_memory = self._get_memory_usage()
        logger.info(f"Starting validation. Initial memory usage: {initial_memory:.2f} MB")
        logger.info(f"Processing {len(data):,} rows in chunks of {chunk_size:,}")

        detection_results = []
        total_rows = len(data)

        for column in data.columns:
            if column not in expected_types:
                continue

            expected_type = expected_types[column]
            current_type = str(data[column].dtype)
            invalid_count = 0
            sample_invalids = []

            # Process in chunks
            for chunk in self._chunk_iterator(data[[column]], chunk_size):
                if expected_type in ('int64', 'float64'):
                    valid_mask = self._validate_numeric(chunk[column], expected_type)
                elif expected_type == 'bool':
                    valid_mask = self._validate_boolean(chunk[column])
                else:  # str type
                    valid_mask = pd.notna(chunk[column]).to_numpy()

                chunk_invalid_count = (~valid_mask).sum()
                invalid_count += chunk_invalid_count

                # Collect samples only from the first chunk if needed
                if chunk_invalid_count > 0 and not sample_invalids:
                    invalid_values = chunk[column][~valid_mask]
                    sample_invalids.extend(invalid_values.head(3).tolist())

                # Clear memory
                del valid_mask
                gc.collect()

            if invalid_count > 0:
                logger.info(
                    f"Column '{column}': Found {invalid_count:,} invalid values "
                    f"({invalid_count / total_rows:.1%})"
                )

                detection_results.append(
                    DetectionResult(
                        issue_type='data_type_mismatch',
                        field_name=column,
                        expected_type=expected_type,
                        detected_type=current_type,
                        total_rows=total_rows,
                        invalid_count=invalid_count,
                        mismatch_ratio=invalid_count / total_rows,
                        sample_invalid_values=sample_invalids
                    )
                )

        final_memory = self._get_memory_usage()
        logger.info(f"Validation complete. Final memory usage: {final_memory:.2f} MB "
                    f"(Change: {final_memory - initial_memory:.2f} MB)")

        return {
            'issue_type': 'data_type_mismatch',
            'detected_items': detection_results
        }

    def generate_report(self, results: Dict[str, List[DetectionResult]], data: pd.DataFrame,
                        duration: float) -> None:
        """Generate and display a memory-efficient report."""
        print(f"\n{Fore.CYAN + Style.BRIGHT}Data Type Validation Report{Style.RESET_ALL}\n")

        metadata = [
            ["Total Columns", len(data.columns)],
            ["Total Rows", f"{len(data):,}"],
            ["Memory Usage", f"{data.memory_usage(deep=True).sum() / (1024 * 1024):.2f} MB"],
            ["Validation Duration", f"{duration:.2f} seconds"],
            ["Columns with Issues", len(results['detected_items'])],
            ["Rows/Second", f"{len(data) / duration:,.0f}"]
        ]

        print(tabulate(metadata, headers=["Metadata", "Value"],
                       tablefmt="fancy_grid", stralign="left"))

        if not results['detected_items']:
            print(f"\n{Fore.GREEN}No data type issues detected.")
            return

        table_data = []
        for result in results['detected_items']:
            sample_values = ', '.join(str(x) for x in result.sample_invalid_values[:3])
            table_data.append([
                result.field_name,
                result.expected_type,
                result.detected_type,
                f"{result.invalid_count:,}",
                f"{result.mismatch_ratio:.2%}",
                sample_values
            ])

        headers = ["Column", "Expected", "Current", "Invalid Count",
                   "Invalid Ratio", "Sample Invalid Values"]
        print(f"\n{Fore.CYAN + Style.BRIGHT}Validation Results:{Style.RESET_ALL}\n")
        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))


if __name__ == "__main__":
    # Test with 100 million rows
    rows = 100_000_000
    chunk_size = 1_000_000

    print(f"Generating test data with {rows:,} rows...")

    # Generate data in chunks to manage memory
    data_chunks = []
    chunk_count = rows // chunk_size

    for i in range(chunk_count):
        if i % 10 == 0:
            print(f"Generating chunk {i + 1}/{chunk_count}...")

        chunk = pd.DataFrame({
            'int_col': np.random.choice([1, None, 3.5, "4", 5], chunk_size),
            'float_col': np.random.choice([1.0, None, "3.5", 4, "invalid"], chunk_size),
            'str_col': np.random.choice(["text", 2, None, True, 3.14], chunk_size),
            'bool_col': np.random.choice([True, False, 1, 0, "true", "invalid"], chunk_size)
        })
        data_chunks.append(chunk)

    data = pd.concat(data_chunks, ignore_index=True)
    del data_chunks
    gc.collect()

    expected_types = {
        'int_col': 'int64',
        'float_col': 'float64',
        'str_col': 'str',
        'bool_col': 'bool'
    }

    detector = DataTypeMismatchDetector()
    start_time = time.time()
    detection_results = detector.detect(data, expected_types, chunk_size=chunk_size)
    end_time = time.time()

    detector.generate_report(detection_results, data, duration=end_time - start_time)