import pandas as pd
import re
from typing import Dict, Any, List
from spellchecker import SpellChecker


class TextStandardizationQualityDetector:
    """
    Detector for text standardization issues in datasets.
    """
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.spell_checker = SpellChecker()

    def detect_case_inconsistencies(self) -> Dict[str, Dict[str, int]]:
        """
        Detect critical inconsistencies across all columns in the DataFrame.

        Returns a dictionary with column names as keys and dictionaries of inconsistency counts as values.
        """
        spell = SpellChecker()
        inconsistencies = {}

        for col in self.data.columns:
            # Initialize inconsistency tracking for this column
            inconsistencies[col] = {
                'mixed_case': 0,
                'capitalization_errors': 0,
                'word_capitalization': 0,
                'spelling_errors': 0
            }

            # Skip non-string columns
            if not self.data[col].dtype == 'object':
                continue

            for row in self.data[col]:
                if isinstance(row, str):
                    # Check for mixed case
                    if not row.islower() and not row.isupper() and not row.istitle():
                        inconsistencies[col]['mixed_case'] += 1

                    # Check for capitalization errors
                    if not re.match(r'^[A-Z][a-z]*$', row) and not re.match(r'^[a-z]+$', row):
                        inconsistencies[col]['capitalization_errors'] += 1

                    # Check for word capitalization
                    if ' ' in row:
                        words = row.split()
                        if not all(word.istitle() for word in words):
                            inconsistencies[col]['word_capitalization'] += 1

                    # Spell check
                    words = row.split()
                    for word in words:
                        if spell.unknown([word]):
                            inconsistencies[col]['spelling_errors'] += 1

        return inconsistencies

    def run(self) -> Dict[str, Any]:
        """
        Run all text standardization issue detectors on all columns and return a summary of issues.
        """
        result = {
            "case_inconsistencies": self.detect_case_inconsistencies(),
            "whitespace_irregularities": self.detect_whitespace_irregularities(),
            "special_character_issues": self.detect_special_characters(allowed_chars=""),
            "typo_issues": self.detect_typos(dictionary=None),
            "pattern_normalization_issues": self.detect_pattern_normalization_issues()
        }

        return {"text_standardization_issues": result}

    # Other methods remain the same as in the original implementation
    def detect_whitespace_irregularities(self) -> Dict[str, Any]:
        issues = {}
        for col in self.data.columns:
            if isinstance(self.data[col].iloc[0], str):
                irregular_rows = self.data[col].apply(
                    lambda x: isinstance(x, str) and (x != x.strip() or "  " in x)
                )
                issues[col] = irregular_rows.sum()
        return issues

    def detect_special_characters(self, allowed_chars: str = "") -> Dict[str, Any]:
        pattern = f"[^{re.escape(allowed_chars)}a-zA-Z0-9 ]"
        issues = {}
        for col in self.data.columns:
            if isinstance(self.data[col].iloc[0], str):
                special_char_rows = self.data[col].apply(
                    lambda x: isinstance(x, str) and re.search(pattern, x) is not None
                )
                issues[col] = special_char_rows.sum()
        return issues

    def detect_typos(self, dictionary: List[str] = None) -> Dict[str, Any]:
        issues = {}
        if dictionary:
            self.spell_checker.word_frequency.load_words(dictionary)

        for col in self.data.columns:
            if isinstance(self.data[col].iloc[0], str):
                typo_rows = self.data[col].apply(
                    lambda x: isinstance(x, str) and any(
                        word for word in x.split() if word.lower() not in self.spell_checker)
                )
                issues[col] = typo_rows.sum()
        return issues

    def suggest_pattern_for_column(self, column_name: str) -> str:
        pattern_suggestions = {
            'phone': 'US phone numbers',
            'email': 'Email addresses',
            'zip': 'ZIP codes',
            'url': 'URLs',
            'address': 'Postal codes',
            'ssn': 'SSN',
            'credit_card': 'Credit card numbers'
        }

        lower_col_name = column_name.lower()

        for key in pattern_suggestions:
            if key in lower_col_name:
                return pattern_suggestions[key]

        return None

    def detect_pattern_normalization_issues(self) -> Dict[str, Any]:
        issues = {}
        common_patterns = [
            {'pattern': r'^\d{3}$', 'description': 'US phone numbers'},
            {'pattern': r'^\w+@\w+\.\w+$', 'description': 'Email addresses'},
            {'pattern': r'^\d{13}$', 'description': 'International phone numbers'},
            {'pattern': r'^\d{5}$', 'description': 'ZIP codes'},
            {'pattern': r'^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$', 'description': 'URLs'},
            {'pattern': r'\b\d{3}\s?\b', 'description': 'Phone area codes'},
            {'pattern': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'description': 'Phone numbers'},
            {'pattern': r'\b\d{5}-\d{4}\b', 'description': 'Postal codes'},
            {'pattern': r'\b\d{8}\b', 'description': 'SSN'},
            {'pattern': r'\b\d{16}\b', 'description': 'Credit card numbers'},
        ]

        for col in self.data.columns:
            if isinstance(self.data[col].iloc[0], str):
                suggested_pattern = self.suggest_pattern_for_column(col)

                if suggested_pattern:
                    description = f"{col}_{suggested_pattern}"
                else:
                    description = f"{col}_general"

                non_matching_rows = self.data[col].apply(
                    lambda x: isinstance(x, str) and not re.fullmatch(common_patterns[0]['pattern'], x)
                )

                # Apply each common pattern
                for pattern_dict in common_patterns:
                    pattern = pattern_dict['pattern']
                    issues[f"{col}_{description}_{pattern_dict['description']}"] = non_matching_rows.sum()

        return issues