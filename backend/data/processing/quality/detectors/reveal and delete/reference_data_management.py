# import pandas as pd
# import re
# from collections import defaultdict
# from typing import Dict, List, Any


# class ReferenceDataManagementQualityDetector:
#     """
#     Detects reference data validation issues.
#         - Lookup missing
#         - Codelist outdated
#         - Terminology mismatch
#         - Range violation
#         - Reference invalid
#     """
#     def __init__(self, data: pd.DataFrame):
#         self.data = data

#     def detect_lookup_missing(self, columns: List[str], valid_lookup_values: Dict[str, List[str]]) -> Dict[str, Any]:
#         """
#         Detect missing lookup values in the specified columns by comparing with a list of valid lookup values.
#         """
#         issues = {}
#         for col, valid_values in valid_lookup_values.items():
#             if col in self.data:
#                 missing_lookups = self.data[col].apply(
#                     lambda x: x not in valid_values if pd.notnull(x) else False
#                 )
#                 issues[col] = missing_lookups.sum()
#         return {"lookup_missing": issues}

#     def detect_codelist_outdated(self, columns: List[str], valid_codes: Dict[str, List[str]]) -> Dict[str, Any]:
#         """
#         Detect outdated codelists by checking if the values are still valid according to the current codes.
#         """
#         issues = {}
#         for col, valid_codes_list in valid_codes.items():
#             if col in self.data:
#                 outdated_codes = self.data[col].apply(
#                     lambda x: x not in valid_codes_list if pd.notnull(x) else False
#                 )
#                 issues[col] = outdated_codes.sum()
#         return {"codelist_outdated": issues}

#     def detect_terminology_mismatch(self, columns: List[str], valid_terminologies: List[str]) -> Dict[str, Any]:
#         """
#         Detect terminology mismatches based on a list of valid terminology values.
#         """
#         issues = {}
#         for col in columns:
#             if col in self.data:
#                 mismatched_terminology = self.data[col].apply(
#                     lambda x: x not in valid_terminologies if pd.notnull(x) else False
#                 )
#                 issues[col] = mismatched_terminology.sum()
#         return {"terminology_mismatch": issues}

#     def detect_range_violation(self, columns: List[str], min_value: float, max_value: float) -> Dict[str, Any]:
#         """
#         Detect range violations in the specified columns, where values should fall within the given range.
#         """
#         issues = {}
#         for col in columns:
#             if col in self.data:
#                 range_violations = self.data[col].apply(
#                     lambda x: x < min_value or x > max_value if pd.notnull(x) else False
#                 )
#                 issues[col] = range_violations.sum()
#         return {"range_violation": issues}

#     def detect_reference_invalid(self, columns: List[str], valid_references: List[str]) -> Dict[str, Any]:
#         """
#         Detect invalid references in the specified columns by checking if values exist in the valid reference list.
#         """
#         issues = {}
#         for col in columns:
#             if col in self.data:
#                 invalid_references = self.data[col].apply(
#                     lambda x: x not in valid_references if pd.notnull(x) else False
#                 )
#                 issues[col] = invalid_references.sum()
#         return {"reference_invalid": issues}

#     def run(self, terminology_invalid_terms: List[str], instrument_valid_ids: List[str],
#             inventory_rule: str, specification_patterns: Dict[str, str], compliance_rules: Dict[str, str],
#             valid_lookup_values: Dict[str, List[str]], valid_codes: Dict[str, List[str]],
#             valid_terminologies: List[str], range_min_value: float, range_max_value: float,
#             valid_references: List[str]) -> Dict[str, Any]:
#         """
#         Run all domain-specific and reference data validation checks.
#         """
#         return {
#             "terminology_invalid": self.detect_terminology_invalid(self.data.columns, terminology_invalid_terms),
#             "instrument_invalid": self.detect_instrument_invalid(self.data.columns, instrument_valid_ids),
#             "inventory_rule_violation": self.detect_inventory_rule_violation(self.data.columns, inventory_rule),
#             "specification_mismatch": self.detect_specification_mismatch(self.data.columns, specification_patterns),
#             "compliance_violation": self.detect_compliance_violation(self.data.columns, compliance_rules),
#             "lookup_missing": self.detect_lookup_missing(self.data.columns, valid_lookup_values),
#             "codelist_outdated": self.detect_codelist_outdated(self.data.columns, valid_codes),
#             "terminology_mismatch": self.detect_terminology_mismatch(self.data.columns, valid_terminologies),
#             "range_violation": self.detect_range_violation(self.data.columns, range_min_value, range_max_value),
#             "reference_invalid": self.detect_reference_invalid(self.data.columns, valid_references)
#         }
