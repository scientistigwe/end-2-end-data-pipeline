import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict
from colorama import Fore, Style, init
from tabulate import tabulate
import time

# Initialize Colorama
init(autoreset=True)


@dataclass
class DefaultValueResult:
    """Results for default/placeholder value detection"""
    field_name: str
    total_rows: int
    default_count: int
    default_ratio: float
    detected_values: List[str]
    is_suspicious: bool
    value_category: str  # Added to classify type of default/placeholder


class RequiredFieldDetector:
    """Detects potentially meaningless or default values in data"""

    def __init__(self):
        self.suspicious_values = {
            'placeholder': ['xxx', 'test', 'dummy', 'sample', 'placeholder'],
            'pending': ['tbd', 'pending', 'todo', 'later', 'upcoming'],
            'unknown': ['unknown', 'undefined', 'tbc', 'na', 'n/a'],
            'default': ['default', 'none', 'null', '-', '.']
        }
        self.numeric_defaults = [0, -1, -999, 999, 9999]

    def is_default_numeric(self, series: pd.Series) -> bool:
        unique_values = series.unique()
        return (len(unique_values) == 1 and
                pd.to_numeric(unique_values[0], errors='coerce') in self.numeric_defaults)

    def get_value_category(self, value: str) -> str:
        """Determine which category a suspicious value belongs to"""
        value = str(value).lower().strip()
        for category, patterns in self.suspicious_values.items():
            if value in patterns:
                return category
        return 'numeric_default'

    def detect(self, data: pd.DataFrame) -> Dict:
        """Detect columns that might contain only default/placeholder values."""
        start_time = time.time()
        results = []

        for column in data.columns:
            series = data[column]
            total_rows = len(series)

            if pd.api.types.is_numeric_dtype(series):
                if self.is_default_numeric(series):
                    results.append(
                        DefaultValueResult(
                            field_name=column,
                            total_rows=total_rows,
                            default_count=total_rows,
                            default_ratio=1.0,
                            detected_values=series.unique().tolist(),
                            is_suspicious=True,
                            value_category='numeric_default'
                        )
                    )

            else:
                suspicious_values = []
                default_count = 0

                # Convert to string and process
                str_series = series.fillna('').astype(str).str.lower().str.strip()
                for val in str_series.unique():
                    if any(val in patterns for patterns in self.suspicious_values.values()):
                        count = (str_series == val).sum()
                        default_count += count
                        suspicious_values.append(str(series[str_series == val].iloc[0]))

                if default_count > 0:
                    default_ratio = default_count / total_rows
                    value_category = self.get_value_category(suspicious_values[0])

                    results.append(
                        DefaultValueResult(
                            field_name=column,
                            total_rows=total_rows,
                            default_count=default_count,
                            default_ratio=default_ratio,
                            detected_values=suspicious_values[:3],
                            is_suspicious=default_ratio > 0.5,
                            value_category=value_category
                        )
                    )

        duration = time.time() - start_time
        return {
            'issue_type': 'default_value_check',
            'total_columns': len(data.columns),
            'suspicious_columns': len(results),
            'detected_items': results,
            'duration': duration
        }

    def generate_report(self, results: Dict, data: pd.DataFrame) -> None:
        """Generate a styled tabular report of findings"""
        print(f"\n{Fore.CYAN + Style.BRIGHT}Default/Placeholder Value Detection Report{Style.RESET_ALL}\n")

        # Metadata Section
        metadata = [
            ["Total Columns", len(data.columns)],
            ["Total Rows", f"{len(data):,}"],
            ["Memory Usage", f"{data.memory_usage(deep=True).sum() / (1024 * 1024):.2f} MB"],
            ["Detection Duration", f"{results['duration']:.2f} seconds"],
            ["Suspicious Columns", results['suspicious_columns']],
        ]

        print(tabulate(metadata, headers=["Metadata", "Value"],
                       tablefmt="fancy_grid", stralign="left"))

        if not results['detected_items']:
            print(f"\n{Fore.GREEN}No suspicious default values detected.")
            return

        # Detailed Results Table
        table_data = []
        for item in results['detected_items']:
            sample_values = ', '.join(str(x) for x in item.detected_values)
            risk_level = (f"{Fore.RED}HIGH{Style.RESET_ALL}" if item.is_suspicious
                          else f"{Fore.GREEN}LOW{Style.RESET_ALL}")

            table_data.append([
                item.field_name,
                item.value_category.upper(),
                f"{item.default_count:,}",
                f"{item.default_ratio:.1%}",
                sample_values,
                risk_level
            ])

        headers = ["Column", "Pattern Type", "Default Count", "Ratio",
                   "Sample Values", "Risk Level"]
        print(f"\n{Fore.CYAN + Style.BRIGHT}Detailed Analysis:{Style.RESET_ALL}\n")
        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid",
                       stralign="center", numalign="center"))

        # Summary of high-risk columns
        high_risk = sum(1 for item in results['detected_items'] if item.is_suspicious)
        if high_risk > 0:
            print(f"\n{Fore.YELLOW}Summary:{Style.RESET_ALL}")
            print(f"Found {high_risk} high-risk columns with majority default/placeholder values")


if __name__ == "__main__":
    # Example usage
    data = pd.DataFrame({
        'user_id': [0] * 1000,  # All zeros
        'score': [-999] * 500 + [100] * 500,  # Half default values
        'status': ['PENDING'] * 800 + ['ACTIVE'] * 200,  # Mostly pending
        'description': ['test data'] * 300 + ['real description'] * 700,  # Some test data
        'notes': ['TBC', 'undefined', 'N/A'] * 333 + ['actual note'],  # Mixed placeholders
        'category': ['Electronics', 'Books', 'Clothing'] * 333 + ['Food'],  # Normal data
    })

    detector = RequiredFieldDetector()
    results = detector.detect(data)
    detector.generate_report(results, data)