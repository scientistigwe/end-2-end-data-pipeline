import pandas as pd
import re
from collections import defaultdict
from typing import Dict, List, Any


class DomainSpecificValidationQualityDetector:
    """
    Detector for domain-specific and reference data validation issues including:
    - Terminology invalid
    - Instrument invalid
    - Inventory rule violation
    - Specification mismatch
    - Compliance violation
    """
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def detect_terminology_invalid(self, columns: List[str], invalid_terms: List[str]) -> Dict[str, Any]:
        """
        Detect invalid terminology based on a list of terms.
        """
        issues = {}
        for col in columns:
            if col in self.data:
                invalid_terminology = self.data[col].apply(
                    lambda x: any(term in str(x) for term in invalid_terms) if pd.notnull(x) else False
                )
                issues[col] = invalid_terminology.sum()
        return {"terminology_invalid": issues}

    def detect_instrument_invalid(self, columns: List[str], valid_instruments: List[str]) -> Dict[str, Any]:
        """
        Detect invalid instruments based on a list of valid instrument IDs.
        """
        issues = {}
        for col in columns:
            if col in self.data:
                invalid_instruments = self.data[col].apply(
                    lambda x: x not in valid_instruments if pd.notnull(x) else False
                )
                issues[col] = invalid_instruments.sum()
        return {"instrument_invalid": issues}

    def detect_inventory_rule_violation(self, columns: List[str], rule: str) -> Dict[str, Any]:
        """
        Detect inventory rule violations based on a specified rule.
        """
        issues = {}
        for col in columns:
            if col in self.data:
                violations = self.data[col].apply(
                    lambda x: re.match(rule, str(x)) is None if pd.notnull(x) else False
                )
                issues[col] = violations.sum()
        return {"inventory_rule_violation": issues}

    def detect_specification_mismatch(self, columns: List[str], specification_patterns: Dict[str, str]) -> Dict[str, Any]:
        """
        Detect specification mismatches based on a list of patterns for each specification.
        """
        issues = {}
        for col, pattern in specification_patterns.items():
            if col in self.data:
                mismatches = self.data[col].apply(
                    lambda x: re.match(pattern, str(x)) is None if pd.notnull(x) else False
                )
                issues[col] = mismatches.sum()
        return {"specification_mismatch": issues}

    def detect_compliance_violation(self, columns: List[str], compliance_rules: Dict[str, str]) -> Dict[str, Any]:
        """
        Detect compliance violations based on rules for each column.
        """
        issues = {}
        for col, rule in compliance_rules.items():
            if col in self.data:
                violations = self.data[col].apply(
                    lambda x: re.match(rule, str(x)) is None if pd.notnull(x) else False
                )
                issues[col] = violations.sum()
        return {"compliance_violation": issues}

    def run(
            self, terminology_invalid_terms: List[str], instrument_valid_ids: List[str],
            inventory_rule: str, specification_patterns: Dict[str, str], compliance_rules: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Run all domain-specific validation checks.
        """
        return {
            "terminology_invalid": self.detect_terminology_invalid(self.data.columns, terminology_invalid_terms),
            "instrument_invalid": self.detect_instrument_invalid(self.data.columns, instrument_valid_ids),
            "inventory_rule_violation": self.detect_inventory_rule_violation(self.data.columns, inventory_rule),
            "specification_mismatch": self.detect_specification_mismatch(self.data.columns, specification_patterns),
            "compliance_violation": self.detect_compliance_violation(self.data.columns, compliance_rules),
        }
