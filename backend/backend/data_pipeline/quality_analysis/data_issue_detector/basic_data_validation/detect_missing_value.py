import logging
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np

# Set up logging
logger = logging.getLogger('missing_value_detector')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


@dataclass
class DetectionResult:
    """Standard structure for detection results"""
    issue_type: str
    field_name: str
    field_type: str
    total_rows: int
    missing_count: int
    detection_metadata: Dict[str, Any]


class MissingValueDetector:
    """Detects missing values irrespective of column type"""

    def detect(self, data: pd.DataFrame) -> Dict[str, List[DetectionResult]]:
        """Main detection method"""
        detection_results = []

        logger.info(f"Starting missing value detection for {len(data.columns)} columns.")

        for column in data.columns:
            missing_count = data[column].isna().sum()

            # Only process columns with missing values
            if missing_count > 0:
                logger.info(f"Field: {column} | Missing Count: {missing_count} | Total Rows: {len(data)}")

                # Get pattern info for the column
                pattern_info = self._get_pattern_hints(data[column])

                detection_results.append(
                    DetectionResult(
                        issue_type='missing_value',
                        field_name=column,
                        field_type=str(data[column].dtype),
                        total_rows=len(data),
                        missing_count=missing_count,
                        detection_metadata={
                            'missing_ratio': missing_count / len(data),
                            'pattern_info': pattern_info,
                            'related_fields': self._find_related_fields(data, column)
                        }
                    )
                )

        logger.info(f"Detection complete. Found {len(detection_results)} columns with missing values.")
        return {
            'issue_type': 'missing_value',
            'detected_items': detection_results
        }

    def _get_pattern_hints(self, series: pd.Series) -> Dict[str, str]:
        """
        Identify the most prominent missing value pattern with user-friendly description.
        """
        try:
            missing_mask = series.isna()
            missing_ratio = missing_mask.mean()

            # Check patterns in order of priority
            if missing_ratio > 0.95:
                return {
                    'pattern': 'complete_missing',
                    'description': "Almost all values are missing in this field. This might indicate an optional or redundant field."
                }

            if self._check_strong_consecutive(series):
                return {
                    'pattern': 'consecutive_missing',
                    'description': "Missing values appear in continuous blocks. This often indicates system downtime or batch data collection issues."
                }

            if self._check_clear_periodic(series):
                return {
                    'pattern': 'periodic_missing',
                    'description': "Missing values occur at regular intervals. This typically suggests scheduled maintenance or periodic data collection gaps."
                }

            if self._check_strong_edge_pattern(series):
                return {
                    'pattern': 'edge_missing',
                    'description': "Missing values are concentrated at the beginning or end of the dataset. This often indicates changes in data collection processes."
                }

            if missing_ratio > 0.001:
                return {
                    'pattern': 'scattered_missing',
                    'description': "Missing values appear randomly throughout the data. This might be due to various factors like data entry errors or optional fields."
                }

            return {
                'pattern': 'minimal_missing',
                'description': "Very few missing values detected. These could be occasional data entry gaps or rare collection issues."
            }

        except Exception as e:
            logger.error(f"Error in detecting pattern: {e}")
            return {
                'pattern': 'unknown',
                'description': "Unable to determine a clear pattern in missing values."
            }

    def _check_strong_consecutive(self, series: pd.Series, window: int = 3) -> bool:
        """Check for strong consecutive missing pattern"""
        try:
            missing_mask = series.isna()
            if missing_mask.sum() < window:
                return False

            # Count runs of consecutive missing values
            runs = self._get_runs_of_true(missing_mask)
            if not runs:
                return False

            # Consider it strong if average run length is >= window
            avg_run_length = sum(runs) / len(runs)
            return avg_run_length >= window
        except Exception as e:
            logger.error(f"Error checking consecutive missing: {e}")
            return False

    def _check_clear_periodic(self, series: pd.Series, num_chunks: int = 10) -> bool:
        """Check for clear periodic pattern"""
        try:
            missing_mask = series.isna()
            if len(missing_mask) < num_chunks * 2:
                return False

            # Split into chunks and check for regular pattern
            chunk_size = len(series) // num_chunks
            missing_ratios = []

            for i in range(num_chunks):
                start_idx = i * chunk_size
                end_idx = start_idx + chunk_size
                ratio = missing_mask[start_idx:end_idx].mean()
                if not np.isnan(ratio):
                    missing_ratios.append(ratio)

            if len(missing_ratios) < 3:
                return False

            # Check for alternating pattern or regular intervals
            differences = np.diff(missing_ratios)
            return np.std(differences) < 0.05
        except Exception as e:
            logger.error(f"Error checking periodic missing: {e}")
            return False

    def _check_strong_edge_pattern(self, series: pd.Series, edge_ratio: float = 0.1) -> bool:
        """Check for strong concentration at edges"""
        try:
            if len(series) < 10:
                return False

            edge_size = max(int(len(series) * edge_ratio), 1)
            start_missing = series.iloc[:edge_size].isna().mean()
            end_missing = series.iloc[-edge_size:].isna().mean()
            middle_missing = series.iloc[edge_size:-edge_size].isna().mean()

            # Strong edge pattern if either edge has 3x the missing rate of middle
            return (start_missing > middle_missing * 3) or (end_missing > middle_missing * 3)
        except Exception as e:
            logger.error(f"Error checking edge missing: {e}")
            return False

    def _get_runs_of_true(self, bool_series: pd.Series) -> List[int]:
        """Helper function to get lengths of consecutive True runs"""
        runs = []
        current_run = 0

        for value in bool_series:
            if value:
                current_run += 1
            elif current_run > 0:
                runs.append(current_run)
                current_run = 0

        if current_run > 0:
            runs.append(current_run)

        return runs

    def _find_related_fields(self, data: pd.DataFrame, target_column: str) -> List[str]:
        """Find potentially related fields based on missing pattern"""
        related = []
        try:
            target_missing = data[target_column].isna()

            for col in data.columns:
                if col != target_column:
                    col_missing = data[col].isna()
                    # Use a safer correlation calculation
                    if col_missing.nunique() > 1 and target_missing.nunique() > 1:
                        corr = self._safe_correlation(target_missing, col_missing)
                        if corr is not None and abs(corr) > 0.5:
                            related.append(col)
        except Exception as e:
            logger.error(f"Error finding related fields: {e}")

        return related

    def _safe_correlation(self, series1: pd.Series, series2: pd.Series) -> Optional[float]:
        """Calculate correlation safely between two series"""
        try:
            # Convert to numeric and handle correlation
            s1 = pd.to_numeric(series1, errors='coerce')
            s2 = pd.to_numeric(series2, errors='coerce')

            # Remove any rows where either series has NaN
            mask = ~(s1.isna() | s2.isna())
            s1_clean = s1[mask]
            s2_clean = s2[mask]

            if len(s1_clean) > 2 and s1_clean.nunique() > 1 and s2_clean.nunique() > 1:
                correlation = s1_clean.corr(s2_clean, method='spearman')
                return correlation if not np.isnan(correlation) else None
            return None
        except Exception as e:
            logger.error(f"Error in correlation calculation: {e}")
            return None