import pandas as pd
import re
from typing import Dict, Any, List

class CodeClassificationQualityDetector:
    """
    Detector for code classification issues in datasets, including medical, transaction,
    batch, jurisdiction, and funding codes.
    """
    def __init__(self, data: pd.DataFrame):
        self.data = data

    def detect_medical_code_invalid(self, columns: List[str], valid_codes: List[str]) -> Dict[str, Any]:
        """
        Detect invalid medical codes by checking if values are part of the valid code list.
        """
        issues = {}
        for col in columns:
            if col in self.data:
                invalid_medical_code_rows = self.data[col].dropna().apply(
                    lambda x: x not in valid_codes
                )
                issues[col] = invalid_medical_code_rows.sum()
        return {"invalid_medical_code": issues}

    def detect_transaction_code(self, columns: List[str], valid_codes: List[str]) -> Dict[str, Any]:
        """
        Detect invalid transaction codes by checking if values are part of the valid code list.
        """
        issues = {}
        for col in columns:
            if col in self.data:
                invalid_transaction_code_rows = self.data[col].dropna().apply(
                    lambda x: x not in valid_codes
                )
                issues[col] = invalid_transaction_code_rows.sum()
        return {"invalid_transaction_code": issues}

    def detect_batch_code(self, columns: List[str], pattern: str) -> Dict[str, Any]:
        """
        Detect invalid batch codes by checking if they match the expected pattern.
        """
        issues = {}
        for col in columns:
            if col in self.data:
                invalid_batch_code_rows = self.data[col].dropna().apply(
                    lambda x: not re.match(pattern, str(x))
                )
                issues[col] = invalid_batch_code_rows.sum()
        return {"invalid_batch_code": issues}

    def detect_jurisdiction_code(self, columns: List[str], valid_codes: List[str]) -> Dict[str, Any]:
        """
        Detect invalid jurisdiction codes by checking if they are part of the valid jurisdiction codes.
        """
        issues = {}
        for col in columns:
            if col in self.data:
                invalid_jurisdiction_code_rows = self.data[col].dropna().apply(
                    lambda x: x not in valid_codes
                )
                issues[col] = invalid_jurisdiction_code_rows.sum()
        return {"invalid_jurisdiction_code": issues}

    def detect_funding_code(self, columns: List[str], valid_codes: List[str]) -> Dict[str, Any]:
        """
        Detect invalid funding codes by checking if they are part of the valid funding codes.
        """
        issues = {}
        for col in columns:
            if col in self.data:
                invalid_funding_code_rows = self.data[col].dropna().apply(
                    lambda x: x not in valid_codes
                )
                issues[col] = invalid_funding_code_rows.sum()
        return {"invalid_funding_code": issues}

    def run(self, medical_code_columns: List[str], valid_medical_codes: List[str],
            transaction_code_columns: List[str], valid_transaction_codes: List[str],
            batch_code_columns: List[str], batch_code_pattern: str,
            jurisdiction_code_columns: List[str], valid_jurisdiction_codes: List[str],
            funding_code_columns: List[str], valid_funding_codes: List[str]) -> Dict[str, Any]:
        """
        Run all code classification issue detectors and return a summary of issues.
        """
        return {
            "invalid_medical_code": self.detect_medical_code_invalid(medical_code_columns, valid_medical_codes),
            "invalid_transaction_code": self.detect_transaction_code(transaction_code_columns, valid_transaction_codes),
            "invalid_batch_code": self.detect_batch_code(batch_code_columns, batch_code_pattern),
            "invalid_jurisdiction_code": self.detect_jurisdiction_code(jurisdiction_code_columns, valid_jurisdiction_codes),
            "invalid_funding_code": self.detect_funding_code(funding_code_columns, valid_funding_codes)
        }
