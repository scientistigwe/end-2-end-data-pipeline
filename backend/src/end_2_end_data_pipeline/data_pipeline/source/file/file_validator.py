import os
import pandas as pd
import logging
from typing import Dict, Tuple, Optional
from pandas.errors import EmptyDataError

class FileValidator:
    def __init__(self, required_columns: Optional[list] = None, expected_encoding: str = 'utf-8'):
        self.required_columns = required_columns if required_columns else []
        self.expected_encoding = expected_encoding
        self.logger = logging.getLogger(__name__)

    def validate_file_format(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate if the file format matches the expected format (CSV, Parquet, JSON)."""
        file_extension = os.path.splitext(file_path)[-1].lower()
        if file_extension in ['.csv', '.parquet', '.json']:
            return True, None
        return False, f"Invalid file format. Expected CSV, Parquet, or JSON, but got {file_extension}"

    def validate_completeness(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check if the file is not empty and if required columns are present."""
        try:
            if not os.path.exists(file_path):
                return False, "File does not exist."

            # Try to load the file into a DataFrame to check its contents.
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path, nrows=5)  # Read first 5 rows to check for content
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path, lines=True)  # For line-delimited JSON
            elif file_path.endswith('.parquet'):
                df = pd.read_parquet(file_path)
            else:
                return False, "Unsupported file format."

            if df.empty:
                return False, "File is empty."

            if self.required_columns and not all(col in df.columns for col in self.required_columns):
                missing_cols = [col for col in self.required_columns if col not in df.columns]
                return False, f"Missing required columns: {', '.join(missing_cols)}"

            return True, None
        except EmptyDataError:
            return False, "File is empty."
        except Exception as e:
            return False, f"Error reading file: {str(e)}"

    def validate_file_integrity(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate file integrity by ensuring it can be read without errors."""
        try:
            # Try loading the file into a DataFrame to check its integrity.
            if file_path.endswith('.csv'):
                pd.read_csv(file_path, nrows=5)  # Read first 5 rows to check integrity
            elif file_path.endswith('.json'):
                pd.read_json(file_path, lines=True)
            elif file_path.endswith('.parquet'):
                pd.read_parquet(file_path)
            else:
                return False, "Unsupported file format."

            return True, None
        except Exception as e:
            return False, f"File integrity check failed: {str(e)}"

    def validate_encoding(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate the file encoding (ensure it's UTF-8)."""
        try:
            with open(file_path, 'r', encoding=self.expected_encoding) as file:
                file.read()  # Try reading the file to check encoding
            return True, None
        except UnicodeDecodeError:
            return False, f"File encoding error: Expected {self.expected_encoding}, but got a different encoding."
        except Exception as e:
            return False, f"Error during encoding validation: {str(e)}"

    def validate_metadata(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Validate that the file has necessary metadata like headers for CSV."""
        try:
            if file_path.endswith('.csv'):
                with open(file_path, 'r', encoding=self.expected_encoding) as file:
                    first_line = file.readline()
                    if not first_line:
                        return False, "CSV file does not have headers."
            return True, None
        except Exception as e:
            return False, f"Metadata validation failed: {str(e)}"

    def validate_file(self, file_path: str) -> Dict:
        """Run all validation checks and return a quality gauge and report."""
        validation_results = {}

        # Validate file format
        is_valid_format, format_error = self.validate_file_format(file_path)
        validation_results["file_format"] = {"valid": is_valid_format, "error": format_error}

        # Validate completeness
        is_complete, completeness_error = self.validate_completeness(file_path)
        validation_results["completeness"] = {"valid": is_complete, "error": completeness_error}

        # Validate file integrity
        is_integrity_ok, integrity_error = self.validate_file_integrity(file_path)
        validation_results["integrity"] = {"valid": is_integrity_ok, "error": integrity_error}

        # Validate encoding
        is_encoding_valid, encoding_error = self.validate_encoding(file_path)
        validation_results["encoding"] = {"valid": is_encoding_valid, "error": encoding_error}

        # Validate metadata
        is_metadata_valid, metadata_error = self.validate_metadata(file_path)
        validation_results["metadata"] = {"valid": is_metadata_valid, "error": metadata_error}

        # Calculate the quality gauge
        valid_checks = sum(1 for result in validation_results.values() if result["valid"])
        total_checks = len(validation_results)
        quality_gauge = (valid_checks / total_checks) * 100

        # Recommendations based on validation results
        recommendations = []
        if quality_gauge < 90:
            recommendations.append("File quality is below 90%. Please check the errors and fix them.")
        if not validation_results["file_format"]["valid"]:
            recommendations.append(
                "Invalid file format. Ensure the file is of an accepted format (CSV, JSON, or Parquet).")
        if not validation_results["completeness"]["valid"]:
            recommendations.append("Ensure the file has all required columns and is not empty.")
        if not validation_results["integrity"]["valid"]:
            recommendations.append("Check the file for corruption or invalid content.")
        if not validation_results["encoding"]["valid"]:
            recommendations.append(f"Ensure the file encoding is {self.expected_encoding}.")
        if not validation_results["metadata"]["valid"]:
            recommendations.append("Check if the file contains the necessary headers or metadata.")

        return {
            "validation_results": validation_results,
            "quality_gauge": quality_gauge,
            "recommendations": recommendations
        }
