import pandas as pd
from datetime import datetime
from calendar import isleap
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import re
from dataclasses import dataclass

class DateTimeType(Enum):
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"


@dataclass
class ValidationResult:
    column_name: str
    column_type: DateTimeType
    original_dtype: str  # Added field for original data type
    total_rows: int
    detected_issues: Dict[str, List[Any]]
    suggestions: List[str]
    detected_formats: List[str]


class DateTimePatterns:
    """Centralized storage for datetime patterns"""

    DATE_PATTERNS = [
        # ISO and similar formats
        (r'^\d{4}-\d{2}-\d{2}$', 'ISO format (YYYY-MM-DD)'),
        (r'^\d{4}/\d{2}/\d{2}$', 'YYYY/MM/DD'),
        (r'^\d{8}$', 'YYYYMMDD'),

        # Common formats with different separators
        (r'^\d{2}[/.-]\d{2}[/.-]\d{4}$', 'DD/MM/YYYY'),
        (r'^\d{2}[/.-]\d{2}[/.-]\d{2}$', 'DD/MM/YY'),
        (r'^\d{1,2}[/.-]\d{1,2}[/.-]\d{4}$', 'D/M/YYYY'),

        # Month name formats
        (r'^\d{2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}$', 'DD MMM YYYY'),
        (r'^\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}$', 'D MMM YYYY'),
        (r'^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}$', 'MMM DD, YYYY'),
        (
        r'^(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}$',
        'Month DD, YYYY'),

        # Reversed formats
        (r'^\d{4}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}$', 'YYYY MMM DD'),

        # Unix timestamps
        (r'^\d{10}$', 'Unix Timestamp'),
        (r'^\d{13}$', 'Unix Timestamp (ms)'),
    ]

    TIME_PATTERNS = [
        # 24-hour format
        (r'^([01]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?$', 'HH:MM(:SS)'),
        (r'^([01]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?\.(\d{1,6})$', 'HH:MM:SS.micro'),

        # 12-hour format
        (r'^([0-9]|1[0-2]):[0-5][0-9]\s*[AaPp][Mm]$', 'HH:MM AM/PM'),
        (r'^([0-9]|1[0-2]):[0-5][0-9]:[0-5][0-9]\s*[AaPp][Mm]$', 'HH:MM:SS AM/PM'),

        # Simple formats
        (r'^([0-9]|1[0-2])[AaPp][Mm]$', 'HAM/PM'),
        (r'^([01]?[0-9]|2[0-3])[Hh]$', 'Hours only'),
    ]

    DATETIME_PATTERNS = [
        # ISO formats
        (r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}$', 'YYYY-MM-DD HH:MM:SS'),
        (r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\.\d+$', 'YYYY-MM-DD HH:MM:SS.micro'),
        (r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[+-]\d{2}:?\d{2}$', 'ISO with timezone'),
        (r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}Z$', 'ISO UTC'),

        # Common formats
        (r'^\d{2}[/.-]\d{2}[/.-]\d{4}\s+\d{2}:\d{2}:\d{2}$', 'DD/MM/YYYY HH:MM:SS'),
        (r'^\d{2}[/.-]\d{2}[/.-]\d{4}\s+\d{1,2}:\d{2}\s*[AaPp][Mm]$', 'DD/MM/YYYY HH:MM AM/PM'),

        # Month name formats
        (r'^\d{2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\s+\d{2}:\d{2}:\d{2}$',
         'DD MMM YYYY HH:MM:SS'),
        (r'^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\s+\d{2}:\d{2}:\d{2}$',
         'MMM DD, YYYY HH:MM:SS'),

        # Compact formats
        (r'^\d{8}T\d{6}$', 'YYYYMMDDTHHMMSS'),
        (r'^\d{14}$', 'YYYYMMDDHHMMSS'),
    ]

    # Flexible patterns for fuzzy matching
    FLEXIBLE_DATE_PATTERNS = [
        r'\d{2,4}[/\-\._\s]\d{1,2}[/\-\._\s]\d{2,4}',
        r'\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{2,4}',
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{1,2}[,\s]\s*\d{2,4}',
    ]


class DateTimePatternDetector:
    @staticmethod
    def detect_formats(value: str) -> List[str]:
        """Detect all matching formats for a given value"""
        formats = []
        value = str(value).strip()

        # Check datetime patterns first (more specific)
        for pattern, format_name in DateTimePatterns.DATETIME_PATTERNS:
            if re.match(pattern, value):
                formats.append(format_name)
                return formats  # Return immediately if datetime pattern is found

        # Check date patterns
        date_match = False
        for pattern, format_name in DateTimePatterns.DATE_PATTERNS:
            if re.match(pattern, value):
                formats.append(format_name)
                date_match = True

        # Check time patterns
        time_match = False
        for pattern, format_name in DateTimePatterns.TIME_PATTERNS:
            if re.match(pattern, value):
                formats.append(format_name)
                time_match = True

        # Only check flexible patterns if no strict patterns matched
        if not (date_match or time_match):
            for pattern in DateTimePatterns.FLEXIBLE_DATE_PATTERNS:
                if re.search(pattern, value):
                    formats.append("Flexible Date Format")
                    break

        return formats

    @staticmethod
    def _analyze_column(series: pd.Series) -> tuple[float, float, float, List[str]]:
        """Analyze a column and return confidence scores and detected formats"""
        valid_values = series.dropna().astype(str)
        if len(valid_values) == 0:
            return 0, 0, 0, []

        date_matches = 0
        time_matches = 0
        datetime_matches = 0
        total_values = len(valid_values)
        all_formats = []

        # Sample up to 100 values for analysis
        sample_size = min(100, total_values)
        sample_values = valid_values.sample(n=sample_size) if total_values > sample_size else valid_values

        for value in sample_values:
            value = str(value).strip()
            formats = DateTimePatternDetector.detect_formats(value)

            if formats:
                all_formats.extend(formats)

                # Update matching logic to better handle datetime formats
                if any("YYYY-MM-DD HH:MM:SS" in f or "ISO with timezone" in f or
                       "DD/MM/YYYY HH:MM:SS" in f or "MMM DD, YYYY HH:MM:SS" in f
                       for f in formats):
                    datetime_matches += 1
                elif any(f in [format_name for _, format_name in DateTimePatterns.DATE_PATTERNS]
                         for f in formats):
                    date_matches += 1
                elif any(f in [format_name for _, format_name in DateTimePatterns.TIME_PATTERNS]
                         for f in formats):
                    time_matches += 1

        # Calculate confidence scores
        date_confidence = date_matches / sample_size if sample_size > 0 else 0
        time_confidence = time_matches / sample_size if sample_size > 0 else 0
        datetime_confidence = datetime_matches / sample_size if sample_size > 0 else 0

        return date_confidence, time_confidence, datetime_confidence, list(set(all_formats))


class DateTimeProcessingQualityDetector:
    """Quality detector for datetime-related columns in a DataFrame."""

    def __init__(self, df: pd.DataFrame, threshold: float = 0.5):
        self.df = df
        self.threshold = threshold
        self.results = {}
        self.identification_info = {}

    def run(self) -> Dict:
        """
        Main method to run the datetime quality detection and return structured results.
        Returns a dictionary with quality metrics and issues.
        """
        # First identify and validate datetime columns
        self.validate_all_columns()

        # Structure the results in a format compatible with other quality detectors
        structured_results = {
            "metrics": self._generate_metrics(),
            "issues": self._generate_issues(),
            "suggestions": self._generate_suggestions(),
            "detailed_report": self.generate_report()
        }

        return structured_results

    def _calculate_confidence(self, column: str, values: pd.Series) -> float:
        """
        Calculate confidence score for date identification using multiple analysis methods.

        Args:
            column (str): Column name to analyze
            values (pd.Series): Series of values to check for date patterns

        Returns:
            float: Confidence score between 0 and 100
        """
        # Early return conditions
        if values.isna().all() or len(values) == 0:
            return 0

        # Initialize weights for different components
        weights = {
            'column_name': 20,  # Column name analysis
            'pattern_match': 30,  # Pattern matching
            'parse_success': 30,  # Successful parsing
            'statistical': 20  # Statistical validation
        }

        score = 0
        sample_size = min(100, len(values))
        sample_values = values.dropna().sample(n=sample_size) if len(values) > sample_size else values.dropna()

        # 1. Column name analysis (20%)
        column_lower = column.lower()
        date_indicators = ['date', 'dt', 'day', 'month', 'year', 'time', 'timestamp']
        if any(indicator in column_lower for indicator in date_indicators):
            score += weights['column_name']

        # Early return for ID-like columns
        if 'id' in column_lower or column_lower.endswith('_id'):
            return 0

        # 2. Pattern matching analysis (30%)
        pattern_matches = 0
        total_checked = 0

        # Define date patterns
        date_patterns = [
            # ISO and similar formats
            r'^\d{4}-\d{2}-\d{2}$',
            r'^\d{4}/\d{2}/\d{2}$',
            r'^\d{8}$',

            # Common formats with different separators
            r'^\d{2}[/.-]\d{2}[/.-]\d{4}$',
            r'^\d{2}[/.-]\d{2}[/.-]\d{2}$',
            r'^\d{1,2}[/.-]\d{1,2}[/.-]\d{4}$',

            # Month name formats
            r'^\d{2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}$',
            r'^\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}$',
            r'^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}$'
        ]

        for value in sample_values:
            if pd.notna(value):
                total_checked += 1
                if any(re.match(pattern, str(value)) for pattern in date_patterns):
                    pattern_matches += 1

        if total_checked > 0:
            pattern_score = (pattern_matches / total_checked) * weights['pattern_match']
            score += pattern_score

        # 3. Parse success analysis (30%)
        parse_successes = 0
        total_attempts = 0

        for value in sample_values:
            if pd.notna(value):
                total_attempts += 1
                try:
                    pd.to_datetime(value)
                    parse_successes += 1
                except:
                    continue

        if total_attempts > 0:
            parse_score = (parse_successes / total_attempts) * weights['parse_success']
            score += parse_score

        # 4. Statistical validation (20%)
        if parse_successes > 0:
            try:
                # Convert to datetime for statistical analysis
                dates = pd.to_datetime(sample_values, errors='coerce')
                valid_dates = dates.dropna()

                if len(valid_dates) > 0:
                    # Check date range validity
                    min_date = valid_dates.min()
                    max_date = valid_dates.max()
                    year_range = (max_date.year - min_date.year)

                    # Reasonable date range check (adjust these thresholds as needed)
                    if 1900 <= min_date.year <= 2100 and 1900 <= max_date.year <= 2100:
                        score += weights['statistical'] / 2

                    # Check for reasonable distribution
                    if year_range <= 150:  # Reasonable range for most business data
                        score += weights['statistical'] / 2
            except:
                pass

        # Normalize score to 0-100 range
        final_score = min(max(score, 0), 100)

        # Additional penalty for very low success rates
        if parse_successes / total_attempts < 0.3 if total_attempts > 0 else 0:
            final_score *= 0.5

        return final_score

    def _is_likely_date_column(self, column: str, values: pd.Series, threshold: float = 70) -> bool:
        """
        Determine if a column is likely to contain date values.

        Args:
            column (str): Column name to check
            values (pd.Series): Series of values to analyze
            threshold (float): Confidence threshold (0-100) for date identification

        Returns:
            bool: True if column is likely to contain dates, False otherwise
        """
        confidence = self._calculate_confidence(column, values)
        return confidence >= threshold

    def _generate_metrics(self) -> Dict:
        """Generate metrics about datetime columns."""
        metrics = {
            "total_datetime_columns": len(self.results),
            "columns_by_type": {
                "date": len([r for r in self.results.values() if r.column_type == DateTimeType.DATE]),
                "time": len([r for r in self.results.values() if r.column_type == DateTimeType.TIME]),
                "datetime": len([r for r in self.results.values() if r.column_type == DateTimeType.DATETIME])
            },
            "columns_with_issues": len([r for r in self.results.values() if r.detected_issues])
        }
        return metrics

    def _generate_issues(self) -> Dict:
        """Generate structured issues from validation results."""
        issues = {}
        for col, result in self.results.items():
            if result.detected_issues:
                issues[col] = {
                    "type": result.column_type.value,
                    "issues": result.detected_issues,
                    "formats": result.detected_formats
                }
        return issues

    def _generate_suggestions(self) -> Dict:
        """Generate structured suggestions from validation results."""
        suggestions = {}
        for col, result in self.results.items():
            if result.suggestions:
                suggestions[col] = {
                    "type": result.column_type.value,
                    "suggestions": result.suggestions
                }
        return suggestions

    def validate_all_columns(self) -> Dict[str, ValidationResult]:
        """Validate all datetime-related columns in the DataFrame"""
        datetime_columns = {}

        # First identify datetime columns and their formats
        for column in self.df.columns:
            if self.df[column].isna().all():
                continue

            sample_data = self.df[column].dropna().astype(str).str.strip()
            if len(sample_data) == 0:
                continue

            date_conf, time_conf, datetime_conf, formats = DateTimePatternDetector._analyze_column(sample_data)

            # Store identification info
            if any(conf >= self.threshold for conf in [date_conf, time_conf, datetime_conf]):
                self.identification_info[column] = {
                    'type': self._get_type_from_confidence(date_conf, time_conf, datetime_conf),
                    'confidence': max(date_conf, time_conf, datetime_conf),
                    'sample_values': sample_data.head().tolist(),
                    'formats': formats
                }

            # Assign type based on highest confidence above threshold
            if datetime_conf >= self.threshold:
                datetime_columns[column] = (DateTimeType.DATETIME, formats)
            elif date_conf >= self.threshold:
                datetime_columns[column] = (DateTimeType.DATE, formats)
            elif time_conf >= self.threshold:
                datetime_columns[column] = (DateTimeType.TIME, formats)

        # Now validate each identified column
        for column, (col_type, formats) in datetime_columns.items():
            self.results[column] = self._validate_column(column, col_type, formats)

        return self.results

    def _validate_column(self, column: str, col_type: DateTimeType, formats: List[str]) -> ValidationResult:
        """Validate a datetime column and return results."""
        values = self.df[column].dropna()
        issues = {}
        suggestions = []

        # Capture the original data type of the column
        original_dtype = str(self.df[column].dtype)

        # Basic validation
        invalid_values = self._validate_values(values, col_type)
        if invalid_values:
            issues['invalid_format'] = invalid_values
            suggestions.append(f"Found {len(invalid_values)} values that couldn't be parsed as {col_type.value}")

        # Check for anomalies
        anomalies = self._check_for_anomalies(values, col_type)
        issues.update(anomalies)

        if 'future_dates' in anomalies:
            suggestions.append("Contains future dates - verify if these are expected")
        if 'old_dates' in anomalies:
            suggestions.append("Contains dates before 1900 - verify if these are valid")
        if 'suspicious_times' in anomalies:
            suggestions.append("Contains an unusual number of midnight/noon times - verify if these are valid")

        # Check for mixed formats
        if len(formats) > 1:
            suggestions.append(f"Multiple formats detected: {', '.join(formats)}")
            suggestions.append("Consider standardizing the format for consistency")

        return ValidationResult(
            column_name=column,
            column_type=col_type,
            original_dtype=original_dtype,  # Pass the original data type here
            total_rows=len(values),
            detected_issues=issues,
            suggestions=suggestions,
            detected_formats=formats
        )

    def _check_pattern_match(self, value: str, patterns: List[tuple]) -> bool:
        """Check if string matches any pattern from the list"""
        try:
            return any(re.match(pattern, str(value)) for pattern, _ in patterns)
        except:
            return False

    def _check_flexible_pattern_match(self, value: str, patterns: List[str]) -> bool:
        """Check if string matches any flexible pattern"""
        try:
            return any(re.search(pattern, str(value)) for pattern in patterns)
        except:
            return False

    def _get_matching_formats(self, value: str) -> List[str]:
        """Get all matching format names for a value"""
        formats = []

        # Check strict patterns
        for pattern_list in [
            DateTimePatterns.DATETIME_PATTERNS,
            DateTimePatterns.DATE_PATTERNS,
            DateTimePatterns.TIME_PATTERNS
        ]:
            for pattern, format_name in pattern_list:
                if re.match(pattern, str(value)):
                    formats.append(format_name)

        # Check flexible patterns if no strict matches found
        if not formats:
            if self._check_flexible_pattern_match(value, DateTimePatterns.FLEXIBLE_DATE_PATTERNS):
                formats.append("Flexible Date Format")


        return formats

    def _validate_values(self, values: pd.Series, col_type: DateTimeType) -> List[Any]:
        """Validate values based on their type"""
        invalid_values = []
        for val in values.head(100):  # Sample first 100 values
            try:
                if col_type == DateTimeType.DATE:
                    pd.to_datetime(val).date()
                elif col_type == DateTimeType.TIME:
                    pd.to_datetime(f"2000-01-01 {val}").time()
                else:
                    pd.to_datetime(val)
            except:
                invalid_values.append(val)
        return invalid_values

    def _check_for_anomalies(self, values: pd.Series, col_type: DateTimeType) -> Dict[str, List[Any]]:
        """Check for various datetime anomalies"""
        issues = {}

        if col_type in [DateTimeType.DATE, DateTimeType.DATETIME]:
            # Check for future dates
            try:
                parsed_dates = pd.to_datetime(values, errors='coerce', dayfirst=True)
                future_dates = values[parsed_dates > pd.Timestamp.now()].head(5).tolist()
                if future_dates:
                    issues['future_dates'] = future_dates

                # Check for very old dates
                old_dates = values[parsed_dates < pd.Timestamp('1900-01-01')].head(5).tolist()
                if old_dates:
                    issues['old_dates'] = old_dates
            except:
                pass

        if col_type in [DateTimeType.TIME, DateTimeType.DATETIME]:
            # Check for unusual times (e.g., exactly midnight/noon)
            try:
                time_values = pd.to_datetime(values).dt.time
                exact_midnight = values[time_values == pd.Timestamp('00:00:00').time()].head(5).tolist()
                if len(exact_midnight) > len(values) * 0.5:  # If more than 50% are midnight
                    issues['suspicious_times'] = exact_midnight
            except:
                pass

        return issues

    def _identify_datetime_columns(self) -> Dict[str, DateTimeType]:
        """Identify datetime columns based on value patterns"""
        datetime_columns = {}
        self.identification_info = {}  # Store identification info for reporting

        for column in self.df.columns:
            if self.df[column].isna().all():
                continue

            # Convert to string and clean the data
            sample_data = self.df[column].dropna().astype(str).str.strip()
            if len(sample_data) == 0:
                continue

            date_conf, time_conf, datetime_conf, formats = DateTimePatternDetector._analyze_column(sample_data)

            # Store information only for date and datetime columns
            if datetime_conf >= self.threshold:
                datetime_columns[column] = DateTimeType.DATETIME
                self.identification_info[column] = {
                    'type': 'DATETIME',
                    'confidence': datetime_conf,
                    'sample_values': sample_data.head().tolist(),
                    'formats': formats
                }
            elif date_conf >= self.threshold:
                datetime_columns[column] = DateTimeType.DATE
                self.identification_info[column] = {
                    'type': 'DATE',
                    'confidence': date_conf,
                    'sample_values': sample_data.head().tolist(),
                    'formats': formats
                }

        return datetime_columns

    def _check_pattern_matches(self, values: pd.Series, patterns: List[tuple]) -> int:
        """Count how many values match any of the patterns"""
        matches = 0
        for val in values:
            if any(re.match(pattern, str(val)) for pattern, _ in patterns):
                matches += 1
        return matches

    def _check_invalid_format(self, values: pd.Series, column_type: DateTimeType) -> List[Any]:
        invalid_values = []
        for val in values:
            try:
                if column_type == DateTimeType.DATE:
                    pd.to_datetime(val).date()
                elif column_type == DateTimeType.TIME:
                    datetime.strptime(str(val), "%H:%M:%S").time()
                else:
                    pd.to_datetime(val)
            except:
                invalid_values.append(val)
                if len(invalid_values) >= 5:
                    break
        return invalid_values

    def _check_future_dates(self, values: pd.Series) -> List[Any]:
        future_values = []
        current_date = pd.Timestamp.now()

        for val in values:
            try:
                date_val = pd.to_datetime(val)
                if date_val > current_date:
                    future_values.append(val)
                    if len(future_values) >= 5:
                        break
            except:
                continue
        return future_values

    def _check_leap_years(self, values: pd.Series) -> List[Any]:
        invalid_leap_years = []

        for val in values:
            try:
                date_val = pd.to_datetime(val)
                if date_val.month == 2 and date_val.day == 29 and not isleap(date_val.year):
                    invalid_leap_years.append(val)
                    if len(invalid_leap_years) >= 5:
                        break
            except:
                continue
        return invalid_leap_years

    def _check_invalid_times(self, values: pd.Series) -> List[Any]:
        invalid_times = []

        for val in values:
            try:
                time_parts = str(val).split(':')
                if len(time_parts) >= 2:
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1])
                    if hours > 23 or minutes > 59:
                        invalid_times.append(val)
                        if len(invalid_times) >= 5:
                            break
            except:
                continue
        return invalid_times

    def _is_potential_datetime(self, column: str) -> bool:
        """Pre-check if column might contain datetime data"""
        sample = self.df[column].dropna().astype(str).head(1)
        if len(sample) == 0:
            return False
        return bool(re.search(r'\d{2}[-/:\s]\d{2}|^\d{4}', str(sample.iloc[0])))

    def _detect_column_type(self, column: str) -> Optional[DateTimeType]:
        """Detect the type of datetime column"""
        sample = self.df[column].dropna().astype(str).iloc[0]

        # Simple pattern matching for type detection
        if re.search(r'\d{4}[-/]\d{2}[-/]\d{2}\s\d{2}:\d{2}', str(sample)):
            return DateTimeType.DATETIME
        elif re.search(r'\d{4}[-/]\d{2}[-/]\d{2}', str(sample)):
            return DateTimeType.DATE
        elif re.search(r'\d{2}:\d{2}', str(sample)):
            return DateTimeType.TIME
        return None

    def _is_valid_date(self, value: Any) -> bool:
        """Check if a value is a valid date"""
        try:
            if isinstance(value, str):
                pd.to_datetime(value)
            return True
        except:
            return False

    def _is_valid_time(self, value: Any) -> bool:
        """Check if a value is a valid time"""
        try:
            if isinstance(value, str):
                datetime.strptime(value, "%H:%M:%S")
            return True
        except:
            return False

    def _is_valid_datetime(self, value: Any) -> bool:
        """Check if a value is a valid datetime"""
        try:
            if isinstance(value, str):
                pd.to_datetime(value)
            return True
        except:
            return False

    def _validate_dates(self, values: pd.Series, error_types: Dict, sample_errors: Dict, suggestions: List[str]):
        """Perform date-specific validations"""
        # Check for future dates
        future_dates = values[pd.to_datetime(values, errors='coerce') > pd.Timestamp.now()]
        if not future_dates.empty:
            error_types["future_dates"] = len(future_dates)
            sample_errors["future_dates"] = future_dates.head(5).tolist()
            suggestions.append("Consider validating future dates")

        # Check for very old dates
        old_dates = values[pd.to_datetime(values, errors='coerce') < pd.Timestamp('1900-01-01')]
        if not old_dates.empty:
            error_types["old_dates"] = len(old_dates)
            sample_errors["old_dates"] = old_dates.head(5).tolist()
            suggestions.append("Verify dates before 1900")

        # Check for invalid leap years
        leap_year_issues = values[values.apply(self._is_invalid_leap_year)]
        if not leap_year_issues.empty:
            error_types["leap_year_issues"] = len(leap_year_issues)
            sample_errors["leap_year_issues"] = leap_year_issues.head(5).tolist()
            suggestions.append("Check leap year dates")

    def _validate_times(self, values: pd.Series, error_types: Dict, sample_errors: Dict, suggestions: List[str]):
        """Perform time-specific validations"""
        # Check for invalid hours
        invalid_hours = values[values.apply(self._has_invalid_hours)]
        if not invalid_hours.empty:
            error_types["invalid_hours"] = len(invalid_hours)
            sample_errors["invalid_hours"] = invalid_hours.head(5).tolist()
            suggestions.append("Ensure hours are between 00-23")

        # Check for invalid minutes/seconds
        invalid_minutes = values[values.apply(self._has_invalid_minutes)]
        if not invalid_minutes.empty:
            error_types["invalid_minutes_seconds"] = len(invalid_minutes)
            sample_errors["invalid_minutes_seconds"] = invalid_minutes.head(5).tolist()
            suggestions.append("Ensure minutes and seconds are between 00-59")

    def _is_invalid_leap_year(self, value: str) -> bool:
        """Check if a date falls on February 29th of a non-leap year"""
        try:
            date = pd.to_datetime(value)
            return date.month == 2 and date.day == 29 and not isleap(date.year)
        except:
            return False

    def _has_invalid_hours(self, value: str) -> bool:
        """Check if time has invalid hours"""
        try:
            time_parts = value.split(':')
            hours = int(time_parts[0])
            return hours < 0 or hours > 23
        except:
            return False

    def _has_invalid_minutes(self, value: str) -> bool:
        """Check if time has invalid minutes or seconds"""
        try:
            time_parts = value.split(':')
            minutes = int(time_parts[1])
            seconds = int(time_parts[2]) if len(time_parts) > 2 else 0
            return minutes < 0 or minutes > 59 or seconds < 0 or seconds > 59
        except:
            return False

    def _detect_format(self, value: str) -> Optional[str]:
        """Detect the format of a datetime string"""
        for patterns in [
            DateTimePatterns.DATETIME_PATTERNS,
            DateTimePatterns.DATE_PATTERNS,
            DateTimePatterns.TIME_PATTERNS
        ]:
            for pattern, format_name in patterns:
                if re.match(pattern, str(value)):
                    return format_name
        return None

    def _get_type_conversion_suggestion(self, dtype: Union[str, type], col_type: DateTimeType) -> str:
        """
        Generate type conversion suggestion based on current dtype and target type.

        Args:
            dtype: Current data type of the column (can be string dtype name or type).
            col_type: Target datetime type (DATE, TIME, or DATETIME).

        Returns:
            str: Suggestion for type conversion.
        """
        # Convert type object to string representation if needed
        if isinstance(dtype, type):
            dtype = str(dtype)

        # Clean up dtype string (handle cases like "<class 'str'>")
        dtype = dtype.replace("<class '", "").replace("'>", "")

        if dtype in ['object', 'str']:
            if col_type == DateTimeType.DATE:
                return ("Current type is string (object). Convert to date using: "
                        "pd.to_datetime(column, format='mixed', errors='coerce').dt.date")
            elif col_type == DateTimeType.TIME:
                return ("Current type is string (object). Convert to time using: "
                        "pd.to_datetime(column, format='mixed', errors='coerce').dt.time")
            else:
                return ("Current type is string (object). Convert to datetime using: "
                        "pd.to_datetime(column, format='mixed', errors='coerce')")

        elif dtype in ['int', 'int64', 'int32']:
            if col_type == DateTimeType.DATE:
                return ("Current type is integer. For Unix timestamp, use: "
                        "pd.to_datetime(column, unit='s').dt.date")
            elif col_type == DateTimeType.TIME:
                return ("Current type is integer. For seconds since midnight, use: "
                        "pd.to_timedelta(column, unit='s').dt.time")
            else:
                return ("Current type is integer. For Unix timestamp, use: "
                        "pd.to_datetime(column, unit='s')")

        elif dtype in ['float', 'float64', 'float32']:
            if col_type == DateTimeType.DATE:
                return ("Current type is float. For Unix timestamp, use: "
                        "pd.to_datetime(column, unit='s').dt.date")
            elif col_type == DateTimeType.TIME:
                return ("Current type is float. For seconds since midnight, use: "
                        "pd.to_timedelta(column, unit='s').dt.time")
            else:
                return ("Current type is float. For Unix timestamp, use: "
                        "pd.to_datetime(column, unit='s')")

        elif 'datetime' in dtype.lower():
            if col_type == DateTimeType.DATE:
                return ("Current type is already datetime. Get date component using: column.dt.date")
            elif col_type == DateTimeType.TIME:
                return ("Current type is already datetime. Get time component using: column.dt.time")
            else:
                return "Column is already in datetime format"

        elif 'date' in dtype.lower():
            if col_type == DateTimeType.DATE:
                return "Column is already in date format"
            else:
                return "Current type is date. Convert to datetime using: pd.to_datetime(column)"

        elif 'time' in dtype.lower():
            if col_type == DateTimeType.TIME:
                return "Column is already in time format"
            else:
                return ("Current type is time. Convert to datetime by combining with a date, e.g., "
                        "`pd.to_datetime(date_column + ' ' + time_column)`")

        return (f"Unrecognized type {dtype}. If dealing with mixed formats, consider using: "
                "pd.to_datetime(column, format='mixed', errors='coerce')")

    def generate_report(self) -> str:
        """Generate a comprehensive report of datetime quality analysis."""
        if not hasattr(self, 'identification_info'):
            return "No identification process has been run yet."

        if not self.results:
            return "No date or datetime columns detected in the dataset."

        report_lines = []
        report_lines.append("Date/DateTime Column Analysis Report")
        report_lines.append("=" * 50)

        # Filter for date and datetime results
        date_results = {
            col: result for col, result in self.results.items()
            if result.column_type in [DateTimeType.DATE, DateTimeType.DATETIME]
        }

        for column, result in date_results.items():
            report_lines.append(f"\nColumn: {column}")

            # Add identification information
            if column in self.identification_info:
                info = self.identification_info[column]
                report_lines.append(f"Identified as: {info['type']}")
                report_lines.append(f"Confidence: {info['confidence']:.2%}")
                report_lines.append(f"Current Data Type: {result.original_dtype}")
                report_lines.append("\nSample Values:")
                for val in info['sample_values'][:5]:
                    report_lines.append(f"  - {val}")

            # Add validation results
            report_lines.append(f"\nValidation Results:")
            report_lines.append(f"Type: {result.column_type.value}")
            report_lines.append(f"Total rows: {result.total_rows}")

            if result.detected_formats:
                report_lines.append("\nDetected formats:")
                for format_name in result.detected_formats:
                    report_lines.append(f"  - {format_name}")

            if result.detected_issues:
                report_lines.append("\nIssues found:")
                for issue_type, examples in result.detected_issues.items():
                    report_lines.append(f"\n{issue_type.replace('_', ' ').title()}:")
                    report_lines.append("Example values:")
                    for ex in examples[:5]:
                        report_lines.append(f"  - {ex}")

            if result.suggestions:
                report_lines.append("\nSuggestions:")
                # Add general suggestions
                for suggestion in result.suggestions:
                    report_lines.append(f"  - {suggestion}")

            # Add type conversion suggestion
            conversion_suggestion = self._get_type_conversion_suggestion(
                dtype=result.original_dtype,
                col_type=result.column_type
            )
            report_lines.append("\nType Conversion Suggestion:")
            report_lines.append(f"  - {conversion_suggestion}")

            report_lines.append("-" * 50)

        return "\n".join(report_lines)

    @staticmethod
    def _get_type_from_confidence(date_conf: float, time_conf: float, datetime_conf: float) -> str:
        """Determine the type based on confidence scores."""
        max_conf = max(date_conf, time_conf, datetime_conf)
        if max_conf == datetime_conf:
            return "DATETIME"
        elif max_conf == date_conf:
            return "DATE"
        else:
            return "TIME"

def format_time(seconds):
    """Convert seconds into a human-readable format"""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{int(minutes)} minutes and {remaining_seconds:.2f} seconds"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        return f"{int(hours)} hours, {int(remaining_minutes)} minutes and {remaining_seconds:.2f} seconds"

if __name__ == "__main__":
    # Test data with various datetime formats
    test_data = {
        "strict_dates": ["2023-01-01", "2023-02-02", "2023-03-03"],
        "mixed_dates": ["01/01/2023", "2023.02.02", "03-Mar-2023"],
        "strict_times": ["14:30:00", "15:45:00", "16:30:00"],
        "mixed_times": ["2:30 PM", "15:45", "4PM"],
        "strict_datetime": ["2023-01-01 14:30:00", "2023-02-02 15:45:00", "2023-02-02 15:45:00"],
        "mixed_datetime": ["01/01/2023 2:30 PM", "2023.02.02 15:45", "03-Mar-2023 4PM"],
        "not_dates": ["apple", "banana", "cherry"]
    }

    # Create test DataFrame
    # test_df = pd.DataFrame(test_data)

    filepath = r"C:\Users\admin\Downloads\South_Superstore_V1.csv"
    test_df = pd.read_csv(filepath, encoding='windows-1252')

    print("Input DataFrame:")
    print("\nStarting validation process...")

    # Create validator with lower threshold for testing
    validator = DateTimeProcessingQualityDetector(test_df, threshold=0.3)

    # First identify datetime columns
    datetime_columns = validator._identify_datetime_columns()
    print("\nIdentified datetime columns:", datetime_columns)

    # Validate all columns and store results
    results = validator.validate_all_columns()
    print("\nValidation complete. Number of datetime columns found:", len(results))

    # Generate and print report
    report = validator.generate_report()
    print("\nValidation Report:")
    print(report)

