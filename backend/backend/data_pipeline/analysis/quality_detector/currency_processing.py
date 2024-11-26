import pandas as pd
import numpy as np
import re
from typing import Dict, Any, List, Set, Tuple
from dataclasses import dataclass
from statistics import mean, stdev

from sqlalchemy.testing.plugin.plugin_base import file_config


@dataclass
class ColumnAnalysis:
    identified_as: str
    confidence: float
    sample_values: List[Any]
    detected_currencies: List[str] = None
    total_rows: int = 0
    issues: Dict[str, int] = None
    recommendations: List[str] = None
    statistics: Dict[str, float] = None


class CurrencyProcessingQualityDetector:
    def __init__(self, data: pd.DataFrame, confidence_threshold: float = 30.0):
        self.data = data
        self.confidence_threshold = confidence_threshold
        self.currency_symbols = {
            '$': 'USD', '£': 'GBP', '€': 'EUR', '¥': 'JPY',
            '₹': 'INR', '₩': 'KRW', '₽': 'RUB', 'R$': 'BRL',
            'CHF': 'CHF', 'A$': 'AUD', 'C$': 'CAD', 'HK$': 'HKD'
        }

        # Enhanced currency patterns
        self.currency_codes = set(self.currency_symbols.values())
        self.currency_regex = '|'.join([re.escape(symbol) for symbol in self.currency_symbols.keys()])

        # Improved column name patterns for financial data
        self.column_patterns = [
            r'(?i)(^|_)(price|amount|cost|revenue|sales|payment|total|fee|charge|balance)($|_)',
            r'(?i)(^|_)(currency|money|expense|income|invoice|bill|salary|wage)($|_)',
            r'(?i)(^|_)(profit|loss|proceeds|return|gain)($|_)'
        ]

        # Enhanced non-currency patterns - expanded to catch more ID patterns
        self.non_currency_patterns = [
            r'(?i)(^|_)(percent|pct|ratio|rate|share|quantity|count|units|number)($|_)',
            r'(?i)(^|_)(score|index|rank|rating|level|grade|tier|position)($|_)',
            r'(?i)(^|_)(age|year|month|day|date|time|duration)($|_)',
            r'(?i)(^|_)(margin|discount)($|_)',
            r'(?i).*(%|percentage|ratio).*',
            # Added patterns for IDs and non-currency identifiers
            r'(?i).*(_)?id($|_|s$)',  # Catches ID, Id, _id, ids, etc.
            r'(?i)(^|_)(identifier|key|code|ref|reference|num|number)($|_)',
            r'(?i)(^|_)(row|record|entry|sequence|serial|order)(_)?num($|_)',
            r'(?i)(^|_)(category|status|type|group|class|flag)($|_)',
            r'(?i)(^|_)(name|description|title|label|comment|note)($|_)',
            r'(?i)(^|_)(email|phone|address|url|link|path)($|_)',
            r'(?i)(^|_)(latitude|longitude|lat|long|coord)($|_)'
        ]

        # Value patterns remain the same
        self.value_patterns = [
            rf'^[{self.currency_regex}]?\s*\d+(?:,\d{3})*(?:\.\d{{2}})?$',
            r'^\d+(?:,\d{3})*(?:\.\d{2})?$',
            r'^-?\d+(?:,\d{3})*(?:\.\d{2})?$',
            rf'^[{self.currency_regex}]?\s*\d+(?:.\d{3})*(?:,\d{{2}})?$',
            r'^\d+k$|^\d+M$|^\d+B$'
        ]

    def _calculate_confidence(self, column: str, values: pd.Series) -> float:
        """Enhanced confidence calculation with strict ID and non-currency pattern handling."""
        # Early return conditions for non-currency patterns
        column_lower = column.lower()

        # Check for ID patterns and non-currency patterns first
        if any(re.search(pattern, column_lower) for pattern in self.non_currency_patterns):
            return 0

        # Check for generic ID pattern (any column containing 'id' in any case)
        if 'id' in column_lower:
            return 0

        score = 0
        weights = {
            'column_name': 40,
            'value_format': 10,
            'currency_symbols': 40,
            'statistical': 10
        }

        # Early return for percentage-like columns
        if self._is_likely_percentage(values):
            return 0

        # Column name analysis (35%)
        if any(re.search(pattern, column_lower) for pattern in self.column_patterns):
            score += weights['column_name']

        # Value format analysis (35%)
        valid_values = sum(self._is_currency_value(val) for val in values if pd.notna(val))
        if len(values) > 0:
            format_score = (valid_values / len(values)) * weights['value_format']
            score += format_score

        # Currency symbol presence (20%)
        currency_detected = sum(bool(self._detect_currencies_in_values(str(val)))
                                for val in values if pd.notna(val))
        if len(values) > 0:
            symbol_score = (currency_detected / len(values)) * weights['currency_symbols']
            score += symbol_score

        # Statistical analysis (10%)
        stats = self._calculate_statistics(values)
        if stats:
            mean_val = stats.get("mean", 0)
            if mean_val < 0.0001 or mean_val > 1e8:
                score -= weights['statistical']
            elif 0.01 <= mean_val <= 1e8:
                score += weights['statistical']

        return min(max(score, 0), 100)

    # Rest of the methods remain the same
    def _is_likely_percentage(self, values: pd.Series) -> bool:
        """Check if values are likely to be percentages."""
        try:
            numeric_values = pd.to_numeric(values.dropna())
            between_0_1 = (numeric_values >= 0) & (numeric_values <= 1)
            between_0_100 = (numeric_values >= 0) & (numeric_values <= 100)

            if len(numeric_values) > 0:
                pct_0_1 = between_0_1.mean()
                pct_0_100 = between_0_100.mean()

                return pct_0_1 > 0.9 or pct_0_100 > 0.9
        except:
            return False
        return False

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

    def _calculate_statistics(self, values: pd.Series) -> Dict[str, float]:
        """Calculate statistical measures for the column."""
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

    def analyze_column(self, column: str) -> ColumnAnalysis:
        """Analyze a single column."""
        values = self.data[column].dropna()
        confidence = self._calculate_confidence(column, values)

        is_currency = confidence >= self.confidence_threshold
        detected_currencies = set()
        if is_currency:
            for value in values:
                detected_currencies.update(self._detect_currencies_in_values(str(value)))

        issues = self._identify_issues(values)
        recommendations = self._generate_recommendations(issues, len(values))
        statistics = self._calculate_statistics(values)

        return ColumnAnalysis(
            identified_as="CURRENCY" if is_currency else "NON_CURRENCY",
            confidence=confidence,
            sample_values=values.head(5).tolist(),
            detected_currencies=list(detected_currencies) if is_currency else None,
            total_rows=len(values),
            issues=issues,
            recommendations=recommendations,
            statistics=statistics
        )

    def _identify_issues(self, values: pd.Series) -> Dict[str, int]:
        """Identify issues in the column."""
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
        """Generate recommendations based on issues."""
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
            "missing_values": "Handle missing values: consider imputation or removal based on business context.",
            "invalid_format": "Standardize currency format across all values.",
            "negative_values": "Review negative values to ensure they represent valid transactions.",
            "inconsistent_currency": "Normalize all values to a single currency using appropriate exchange rates.",
            "decimal_precision_issues": "Standardize decimal precision to exactly two decimal places.",
            "outliers": "Investigate outlier values that may indicate data entry errors or unusual transactions.",
            "zero_values": "Review zero values to determine if they represent actual transactions or data errors.",
            "mixed_formats": "Standardize currency notation (either always use symbols or never use them)."
        }

        for issue, count in issues.items():
            if count / total_rows > issue_thresholds[issue]:
                recommendations.append(recommendations_map[issue])

        return recommendations

    def run(self) -> Dict[str, ColumnAnalysis]:
        """Run analysis on all columns."""
        all_results = {column: self.analyze_column(column) for column in self.data.columns}
        return {col: analysis for col, analysis in all_results.items()
                if analysis.identified_as == "CURRENCY"}

# Example usage
if __name__ == "__main__":
    # Example data
    data = {
        "amount": ["$19.99", "50.00", "€100.50", "$500", "₹1000.00", "-1000", "1000000", "1,000,000.99", "$10.99"],
        "total_cost": ["$10", "£100", "€99.99", "-200", "₹5000", "120", "$1,000.99", "$500.00", "$200"],
        "profit": ["1000", "1500", "$2000", "$5000", "1000.25", "150.75", "$25000", "$25000", "Invalid"],
        "percentages": [0.1, 0.25, 0.5, 0.75, 1, 0.15, 0.33, 0.66, 0.99]
    }
    # file_path = r"C:\Users\admin\Downloads\South_Superstore_V1.csv"
    file_path = r"C:\Users\admin\Downloads\fifa21_raw_data_v2.csv"
    df = pd.read_csv(file_path, encoding='utf-8')
    #df = pd.DataFrame(data)
    detector = CurrencyProcessingQualityDetector(df)
    report = detector.run()

    # Display detailed results for currency columns only
    for column, analysis in report.items():
        print(f"\nColumn: {column}")
        print(f"Classification: {analysis.identified_as}")
        print(f"Confidence: {analysis.confidence:.2f}%")
        print(f"Sample Values: {analysis.sample_values}")

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

        if analysis.statistics:
            print("\nStatistics:")
            for stat, value in analysis.statistics.items():
                print(f"- {stat}: {value:.2f}")

        print("-" * 50)