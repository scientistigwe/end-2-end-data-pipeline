import pandas as pd
import numpy as np
from typing import Dict, List, Set, Tuple, Any
from dataclasses import dataclass
import difflib
import jellyfish
import re
from datetime import datetime
from collections import defaultdict
from statistics import mean, stdev

from fuzzywuzzy import fuzz


@dataclass
class DuplicateAnalysis:
    column_name: str
    identified_as: str  # DUPLICATE or NON_DUPLICATE
    confidence: float
    duplicate_types: Dict[str, List[Tuple]]
    sample_duplicates: List[Tuple]
    total_duplicates: int
    duplicate_percentage: float
    issues: Dict[str, int]
    recommendations: List[str]
    statistics: Dict[str, float]


class DuplicateDetectionQualityDetector:
    """
    A comprehensive duplicate detector that identifies various types of duplicates in datasets
    with a similar structure to the CurrencyProcessingQualityDetector.
    """

    def __init__(self, data: pd.DataFrame, confidence_threshold: float = 30.0):
        self.data = data
        self.confidence_threshold = confidence_threshold

        # Column pattern indicators for likely duplicate-containing columns
        self.duplicate_prone_patterns = [
            r'(?i)(^|_)(name|title|description|address|location)($|_)',
            r'(?i)(^|_)(company|organization|business|entity)($|_)',
            r'(?i)(^|_)(identifier|reference|code|key)($|_)',
            r'(?i)(^|_)(email|phone|contact|url)($|_)'
        ]

        # Patterns that suggest unique values are expected
        self.unique_value_patterns = [
            r'(?i)(^|_)(id|uuid|guid)($|_)',
            r'(?i)(^|_)(hash|checksum|digest)($|_)',
            r'(?i)(^|_)(timestamp|datetime|date|time)($|_)',
            r'(?i)(^|_)(sequence|serial|auto)($|_)'
        ]

    def _calculate_confidence(self, column: str, duplicates_info: Dict[str, List[Tuple]]) -> float:
        """Calculate confidence score for duplicate detection."""
        score = 0
        weights = {
            'column_name': 30,
            'duplicate_types': 40,
            'value_distribution': 30
        }

        # Column name analysis
        column_lower = column.lower()
        if any(re.search(pattern, column_lower) for pattern in self.duplicate_prone_patterns):
            score += weights['column_name']
        if any(re.search(pattern, column_lower) for pattern in self.unique_value_patterns):
            score -= weights['column_name']

        # Duplicate type analysis
        total_duplicates = sum(len(dupes) for dupes in duplicates_info.values())
        if total_duplicates > 0:
            types_score = min(len(duplicates_info) * 10, weights['duplicate_types'])
            score += types_score

        # Value distribution analysis
        unique_ratio = len(self.data[column].unique()) / len(self.data[column])
        distribution_score = (1 - unique_ratio) * weights['value_distribution']
        score += distribution_score

        return min(max(score, 0), 100)

    def _detect_exact_duplicates(self, values: pd.Series) -> List[Tuple]:
        """Detect completely identical values."""
        duplicates = []
        value_counts = values.value_counts()
        duplicate_values = value_counts[value_counts > 1].index

        for value in duplicate_values:
            indices = values[values == value].index.tolist()
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    duplicates.append((indices[i], indices[j], value, value))

        return duplicates

    def _detect_case_duplicates(self, values: pd.Series) -> List[Tuple]:
        """Detect values that differ only in letter case."""
        case_duplicates = []
        lowercase_dict = defaultdict(list)

        for idx, value in values.items():
            if pd.notna(value):
                lowercase_dict[str(value).lower()].append((idx, value))

        for entries in lowercase_dict.values():
            if len(entries) > 1:
                for i in range(len(entries)):
                    for j in range(i + 1, len(entries)):
                        if entries[i][1] != entries[j][1]:
                            case_duplicates.append((
                                entries[i][0],
                                entries[j][0],
                                entries[i][1],
                                entries[j][1]
                            ))

        return case_duplicates

    def _detect_fuzzy_duplicates(self, values: pd.Series, threshold: float = 80.0) -> List[Tuple]:
        """Detect similar but not exactly matching values."""
        fuzzy_duplicates = []
        values_list = values.dropna()

        for i, val1 in enumerate(values_list):
            for j, val2 in enumerate(values_list[i + 1:], i + 1):
                ratio = fuzz.ratio(str(val1), str(val2))
                if ratio >= threshold and val1 != val2:
                    fuzzy_duplicates.append((
                        values_list.index[i],
                        values_list.index[j],
                        val1,
                        val2
                    ))

        return fuzzy_duplicates

    def _calculate_statistics(self, duplicates_info: Dict[str, List[Tuple]]) -> Dict[str, float]:
        """Calculate statistical measures for duplicates."""
        all_duplicates = [item for sublist in duplicates_info.values() for item in sublist]
        if not all_duplicates:
            return {}

        unique_indices = set()
        for dup in all_duplicates:
            unique_indices.add(dup[0])
            unique_indices.add(dup[1])

        return {
            "total_duplicate_pairs": len(all_duplicates),
            "unique_values_involved": len(unique_indices),
            "average_duplicates_per_value": len(all_duplicates) / (len(unique_indices) or 1),
            "duplicate_types_found": len(duplicates_info)
        }

    def _identify_issues(self, duplicates_info: Dict[str, List[Tuple]], total_rows: int) -> Dict[str, int]:
        """Identify issues in the duplicate detection results."""
        issues = {
            "exact_duplicates": len(duplicates_info.get("exact", [])),
            "case_inconsistencies": len(duplicates_info.get("case", [])),
            "fuzzy_matches": len(duplicates_info.get("fuzzy", [])),
            "format_inconsistencies": len(duplicates_info.get("whitespace", [])) +
                                      len(duplicates_info.get("punctuation", [])),
            "multiple_representations": len(duplicates_info.get("abbreviation", [])) +
                                        len(duplicates_info.get("transposition", []))
        }

        return {k: v for k, v in issues.items() if v > 0}

    def _generate_recommendations(self, issues: Dict[str, int], total_rows: int) -> List[str]:
        """Generate recommendations based on identified issues."""
        recommendations = []

        issue_thresholds = {
            "exact_duplicates": 0.01,
            "case_inconsistencies": 0.02,
            "fuzzy_matches": 0.05,
            "format_inconsistencies": 0.03,
            "multiple_representations": 0.02
        }

        recommendations_map = {
            "exact_duplicates": "Remove or merge exact duplicate records",
            "case_inconsistencies": "Standardize case formatting across all values",
            "fuzzy_matches": "Review and resolve similar entries that may represent the same entity",
            "format_inconsistencies": "Implement consistent formatting rules for whitespace and punctuation",
            "multiple_representations": "Standardize abbreviations and value representations"
        }

        for issue, count in issues.items():
            if count / total_rows > issue_thresholds[issue]:
                recommendations.append(recommendations_map[issue])

        return recommendations

    def analyze_column(self, column: str) -> DuplicateAnalysis:
        """Analyze a single column for duplicates."""
        values = self.data[column].dropna()

        # Detect various types of duplicates
        duplicates_info = {
            "exact": self._detect_exact_duplicates(values),
            "case": self._detect_case_duplicates(values),
            "fuzzy": self._detect_fuzzy_duplicates(values)
        }

        # Calculate confidence score
        confidence = self._calculate_confidence(column, duplicates_info)

        # Calculate total duplicates and percentage
        total_duplicates = sum(len(dupes) for dupes in duplicates_info.values())
        duplicate_percentage = (total_duplicates / len(values)) * 100 if len(values) > 0 else 0

        # Identify issues and generate recommendations
        issues = self._identify_issues(duplicates_info, len(values))
        recommendations = self._generate_recommendations(issues, len(values))

        # Calculate statistics
        statistics = self._calculate_statistics(duplicates_info)

        return DuplicateAnalysis(
            column_name=column,
            identified_as="DUPLICATE" if confidence >= self.confidence_threshold else "NON_DUPLICATE",
            confidence=confidence,
            duplicate_types=duplicates_info,
            sample_duplicates=list(duplicates_info.get("exact", []))[:5],
            total_duplicates=total_duplicates,
            duplicate_percentage=duplicate_percentage,
            issues=issues,
            recommendations=recommendations,
            statistics=statistics
        )

    def run(self) -> Dict[str, DuplicateAnalysis]:
        """Run analysis on all columns."""
        results = {column: self.analyze_column(column) for column in self.data.columns}
        return {col: analysis for col, analysis in results.items()
                if analysis.identified_as == "DUPLICATE"}


# Example usage
if __name__ == "__main__":
    # Example data
    data = {
        "name": ["John Smith", "john smith", "John  Smith", "Jane Doe", "Jane  Doe"],
        "email": ["john@example.com", "john@example.com", "jane@example.com", "jane@example.com", "jane@test.com"],
        "id": ["001", "002", "003", "004", "005"]
    }
    df = pd.DataFrame(data)

    detector = DuplicateDetectionQualityDetector(df)
    report = detector.run()

    # Display results
    for column, analysis in report.items():
        print(f"\nColumn: {column}")
        print(f"Classification: {analysis.identified_as}")
        print(f"Confidence: {analysis.confidence:.2f}%")
        print(f"Total Duplicates: {analysis.total_duplicates}")
        print(f"Duplicate Percentage: {analysis.duplicate_percentage:.2f}%")

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
                print(f"- {stat}: {value}")