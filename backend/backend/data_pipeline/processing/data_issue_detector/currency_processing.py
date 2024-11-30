import pandas as pd
import numpy as np
import re
from typing import Dict, Any, List, Set, Tuple
from dataclasses import dataclass
from statistics import mean, stdev
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ColumnClassification:
    """Enhanced classification for currency columns."""
    confidence_level: str
    confidence_score: float
    detected_currencies: List[str] = None
    sample_values: List[Any] = None
    total_rows: int = 0
    issues: Dict[str, int] = None
    recommendations: List[str] = None
    statistics: Dict[str, float] = None


class CurrencyQualityDetector:
    def __init__(self, data: pd.DataFrame,
                 confidence_thresholds: Dict[str, float] = None):
        """
        Initialize currency detector with input data and confidence thresholds.

        Args:
            data (pd.DataFrame): Input DataFrame to analyze
            confidence_thresholds (Dict[str, float], optional): Custom confidence levels
        """
        self.data = data
        self.confidence_thresholds = confidence_thresholds or {
            'HIGH': 70.0,
            'MEDIUM': 40.0,
            'LOW': 20.0
        }

        # Enhanced currency symbols dictionary
        self.currency_symbols: Dict[str, str] = {
            '$': 'USD', '£': 'GBP', '€': 'EUR', '¥': 'JPY',
            '₹': 'INR', '₩': 'KRW', '₽': 'RUB', 'R$': 'BRL',
            'CHF': 'CHF', 'A$': 'AUD', 'C$': 'CAD', 'HK$': 'HKD'
        }

        # Prepare currency-related patterns
        self.currency_codes: set = set(self.currency_symbols.values())
        self.currency_regex: str = '|'.join([re.escape(symbol) for symbol in self.currency_symbols.keys()])

        # Column name patterns for financial data
        self.column_patterns: List[str] = [
            r'(?i)(_cost|_price|_amount|_fee)|((cost|price|amount|fee)$)',
            r'(?i)(_)?((total_)?(price|amount|cost|revenue|sales|payment|fee))\b',
            r'(?i)(_)?((total_)?(currency|money|expense|income|invoice|bill|salary|wage))\b',
            r'(?i)(_)?((total_)?(profit|loss))\b',
            r'(?i)((unit|avg|list|net|gross)_?(price|amount|value))\b',
            r'(?i)((unit|transaction|order)_?(cost|price|value))\b',
        ]

        # Non-currency and exclusion patterns
        self.non_currency_patterns = [
            r'(?i)(^|_)(percent|pct|ratio|rate|share|quantity|count|units|number)($|_)',
            r'(?i)(^|_)(score|index|rank|rating|level|grade|tier|position)($|_)',
            r'(?i)(^|_)(age|year|month|day|date|time|duration)($|_)',
            r'(?i)(^|_)(margin|discount)($|_)',
            r'(?i).*(%|percentage|ratio).*',
            r'(?i).*(_)?id($|_|s$)',
        ]

        # Value patterns for currency detection
        self.value_patterns = [
            rf'^[{self.currency_regex}]?\s*\d+(?:,\d{{3}})*(?:\.\d{{2}})?$',
            r'^\d+(?:,\d{3})*(?:\.\d{2})?$',
            r'^-?\d+(?:,\d{3})*(?:\.\d{2})?$',
            rf'^[{self.currency_regex}]?\s*\d+(?:.\d{3})*(?:,\d{{2}})?$',
            r'^-?\d+k$|^-?\d+M$|^-?\d+B$'
        ]

    def _calculate_confidence(self, column: str, values: pd.Series) -> float:
        """Calculate confidence score for a column being a currency column."""
        column_lower = self.normalize_column_name(column)
        weights: Dict[str, float] = {
            'column_name': 45.0,
            'value_format': 30.0,
            'currency_symbols': 15.0,
            'statistical': 10.0
        }
        score: float = 0.0

        # Column name match
        score += sum(
            weights['column_name'] for pattern in self.column_patterns
            if re.search(pattern, column_lower)
        )

        # Value format analysis
        valid_values = sum(
            self._is_currency_value(val)
            for val in values
            if pd.notna(val)
        )
        if len(values) > 0:
            score += (valid_values / len(values)) * weights['value_format']

        # Currency symbol detection
        currency_detected = sum(
            bool(self._detect_currencies_in_values(str(val)))
            for val in values
            if pd.notna(val)
        )
        if len(values) > 0:
            score += (currency_detected / len(values)) * weights['currency_symbols']

        # Statistical validation
        stats = self._calculate_statistics(values)
        if stats:
            mean_val = stats.get("mean", 0.0)
            if 10.0 <= mean_val <= 1e7:
                score += weights['statistical']

        # Penalty for non-currency indicators
        if any(re.search(pattern, column_lower) for pattern in self.non_currency_patterns):
            score *= 0.3

        return min(max(score, 0.0), 100.0)

    def _calculate_enhanced_confidence(self, column: str, values: pd.Series) -> Tuple[float, str]:
        """
        Determine confidence score and level for a column.

        Returns:
        - Confidence score (0-100)
        - Confidence level ('HIGH', 'MEDIUM', 'LOW', 'INSUFFICIENT')
        """
        base_score = self._calculate_confidence(column, values)

        if base_score >= self.confidence_thresholds['HIGH']:
            return base_score, 'HIGH'
        elif base_score >= self.confidence_thresholds['MEDIUM']:
            return base_score, 'MEDIUM'
        elif base_score >= self.confidence_thresholds['LOW']:
            return base_score, 'LOW'
        else:
            return base_score, 'INSUFFICIENT'

    def _calculate_statistics(self, values: pd.Series) -> Dict[str, float]:
        """Calculate statistical measures for a column."""
        numeric_values = [self._extract_numeric_value(v) for v in values]
        numeric_values = [v for v in numeric_values if not np.isnan(v)]

        if not numeric_values:
            return {}

        try:
            return {
                "mean": mean(numeric_values),
                "std": stdev(numeric_values) if len(numeric_values) > 1 else 0,
                "min": min(numeric_values),
                "max": max(numeric_values),
                "q1": np.percentile(numeric_values, 25),
                "q3": np.percentile(numeric_values, 75)
            }
        except Exception:
            return {}

    def _extract_numeric_value(self, value: str) -> float:
        """Extract numeric value from currency string."""
        try:
            value_str = str(value).upper().strip()
            if value_str.endswith('K'):
                return float(value_str[:-1]) * 1000
            elif value_str.endswith('M'):
                return float(value_str[:-1]) * 1000000
            elif value_str.endswith('B'):
                return float(value_str[:-1]) * 1000000000

            cleaned = re.sub(r'[^\d.-]', '', str(value))
            return float(cleaned)
        except (ValueError, TypeError):
            return np.nan

    def _detect_currencies_in_values(self, value: str) -> Set[str]:
        """Detect currencies in values."""
        detected = set()
        value_str = str(value).strip()

        for symbol, code in self.currency_symbols.items():
            if symbol in value_str:
                detected.add(code)

        for code in self.currency_codes:
            if code in value_str.upper():
                detected.add(code)

        return detected

    def _is_currency_value(self, value: Any) -> bool:
        """Check if value matches currency format."""
        if pd.isna(value):
            return False

        value_str = str(value).strip()

        if any(symbol in value_str for symbol in self.currency_symbols):
            return True

        for pattern in self.value_patterns:
            if re.match(pattern, value_str):
                return True

        if re.match(r'^-?\d+(\.\d{2})?$', value_str):
            return True
        if re.match(r'^-?\d{1,3}(,\d{3})*(\.\d{2})?$', value_str):
            return True

        return False

    def normalize_column_name(self, column: str) -> str:
        """Normalize column name to handle special characters and compound words."""
        column = column.lower()
        column = re.sub(r'[^\w\s]', '_', column)
        column = re.sub(r'\s+', '_', column)
        column = re.sub(r'(?<!^)(?=[A-Z])', '_', column).lower()
        return column.strip('_')

    def _identify_issues(self, values: pd.Series) -> Dict[str, int]:
        """Identify potential issues in the column."""
        issues = {
            "missing_values": 0,
            "invalid_format": 0,
            "negative_values": 0,
            "inconsistent_currency": 0,
            "decimal_precision_issues": 0,
            "outliers": 0,
            "zero_values": 0,
            "mixed_formats": 0
        }

        stats = self._calculate_statistics(values)
        if not stats:
            return issues

        detected_currencies = set()
        formats_used = set()

        for value in values:
            if pd.isna(value):
                issues["missing_values"] += 1
                continue

            str_value = str(value)
            curr_symbols = self._detect_currencies_in_values(str_value)
            detected_currencies.update(curr_symbols)

            formats_used.add('symbol' if curr_symbols else 'no_symbol')

            try:
                numeric_value = self._extract_numeric_value(str_value)

                if np.isnan(numeric_value):
                    issues["invalid_format"] += 1
                    continue

                if numeric_value < 0:
                    issues["negative_values"] += 1
                if numeric_value == 0:
                    issues["zero_values"] += 1

                iqr = stats["q3"] - stats["q1"]
                if (numeric_value < stats["q1"] - 1.5 * iqr or
                        numeric_value > stats["q3"] + 1.5 * iqr):
                    issues["outliers"] += 1

                if '.' in str_value and len(str_value.split('.')[-1]) != 2:
                    issues["decimal_precision_issues"] += 1

            except (ValueError, TypeError):
                issues["invalid_format"] += 1

        if len(detected_currencies) > 1:
            issues["inconsistent_currency"] = len(values)
        if len(formats_used) > 1:
            issues["mixed_formats"] = len(values)

        return {k: v for k, v in issues.items() if v > 0}

    def _generate_recommendations(self, issues: Dict[str, int], total_rows: int) -> List[str]:
        """Generate recommendations based on detected issues."""
        recommendations = []

        issue_thresholds = {
            "missing_values": 0.05,
            "invalid_format": 0.02,
            "negative_values": 0.01,
            "inconsistent_currency": 0,
            "decimal_precision_issues": 0.05,
            "outliers": 0.01,
            "zero_values": 0.05,
            "mixed_formats": 0
        }

        recommendations_map = {
            "missing_values": "Handle missing values: consider imputation or removal.",
            "invalid_format": "Standardize currency format.",
            "negative_values": "Review negative values for transaction accuracy.",
            "inconsistent_currency": "Normalize to a single currency using exchange rates.",
            "decimal_precision_issues": "Standardize to two decimal places.",
            "outliers": "Investigate outlier values for data integrity.",
            "zero_values": "Validate zero value transactions.",
            "mixed_formats": "Standardize currency notation."
        }

        for issue, count in issues.items():
            if count / total_rows > issue_thresholds[issue]:
                recommendations.append(recommendations_map[issue])

        return recommendations

    def analyze_column(self, column: str) -> ColumnClassification:
        """Analyze a single column with multi-level confidence."""
        values = self.data[column].dropna()

        confidence_score, confidence_level = self._calculate_enhanced_confidence(column, values)

        if confidence_level == 'INSUFFICIENT':
            return None

        detected_currencies = set()
        for value in values:
            detected_currencies.update(self._detect_currencies_in_values(str(value)))

        issues = self._identify_issues(values)
        recommendations = self._generate_recommendations(issues, len(values))

        return ColumnClassification(
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            detected_currencies=list(detected_currencies),
            sample_values=values.head(5).tolist(),
            total_rows=len(values),
            issues=issues,
            recommendations=recommendations,
            statistics=self._calculate_statistics(values)
        )

    def run(self) -> Dict[str, ColumnClassification]:
        """Run analysis on all columns with currency potential."""
        results = {}
        for column in self.data.columns:
            analysis = self.analyze_column(column)
            if analysis is not None:
                results[column] = analysis

        return results


# Example usage
if __name__ == "__main__":
    filepath = r"C:\Users\admin\Downloads\South_Superstore_V1.csv"
    df = pd.read_csv(filepath, encoding='windows-1252')

    detector = CurrencyQualityDetector(df)
    report = detector.run()

    # Detailed reporting
    for column, analysis in report.items():
        print(f"\nColumn: {column}")
        print(f"Confidence Level: {analysis.confidence_level}")
        print(f"Confidence Score: {analysis.confidence_score:.2f}%")

        if analysis.detected_currencies:
            print(f"Detected Currencies: {analysis.detected_currencies}")

        if analysis.issues:
            print("\nIssues Detected:")
            for issue, count in analysis.issues.items():
                print(f"- {issue}: {count} occurrences")

        if analysis.recommendations:
            print("\nRecommendations:")
            for rec in analysis.recommendations:
                print(f"- {rec}")

        print("-" * 50)