# backend/utils/validation.py

from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
import re
import pandas as pd
import numpy as np
from enum import Enum


class ValidationType(Enum):
    """Types of validation checks"""
    DATA_TYPE = "data_type"
    FORMAT = "format"
    RANGE = "range"
    REQUIRED = "required"
    UNIQUE = "unique"
    PATTERN = "pattern"
    DEPENDENCY = "dependency"
    CUSTOM = "custom"


class ValidationLevel(Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationResult:
    """Result of a validation check"""

    def __init__(self,
                 is_valid: bool,
                 validation_type: ValidationType,
                 level: ValidationLevel = ValidationLevel.ERROR,
                 message: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.is_valid = is_valid
        self.validation_type = validation_type
        self.level = level
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary"""
        return {
            'is_valid': self.is_valid,
            'type': self.validation_type.value,
            'level': self.level.value,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class DataValidator:
    """Core data validation utilities"""

    @staticmethod
    def validate_data_type(value: Any, expected_type: Union[type, Tuple[type, ...]]) -> ValidationResult:
        """Validate data type of a value"""
        is_valid = isinstance(value, expected_type)
        return ValidationResult(
            is_valid=is_valid,
            validation_type=ValidationType.DATA_TYPE,
            message=f"Expected type {expected_type}, got {type(value)}" if not is_valid else None
        )

    @staticmethod
    def validate_format(value: str, format_pattern: str) -> ValidationResult:
        """Validate string format using regex pattern"""
        try:
            is_valid = bool(re.match(format_pattern, value))
            return ValidationResult(
                is_valid=is_valid,
                validation_type=ValidationType.FORMAT,
                message=f"Value does not match pattern {format_pattern}" if not is_valid else None
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                validation_type=ValidationType.FORMAT,
                message=f"Format validation error: {str(e)}"
            )

    @staticmethod
    def validate_range(value: Union[int, float],
                       min_value: Optional[Union[int, float]] = None,
                       max_value: Optional[Union[int, float]] = None) -> ValidationResult:
        """Validate numeric value range"""
        is_valid = True
        message = None

        if min_value is not None and value < min_value:
            is_valid = False
            message = f"Value {value} is less than minimum {min_value}"
        elif max_value is not None and value > max_value:
            is_valid = False
            message = f"Value {value} is greater than maximum {max_value}"

        return ValidationResult(
            is_valid=is_valid,
            validation_type=ValidationType.RANGE,
            message=message
        )

    @staticmethod
    def validate_required(value: Any) -> ValidationResult:
        """Validate required value"""
        is_valid = value is not None and value != ""
        return ValidationResult(
            is_valid=is_valid,
            validation_type=ValidationType.REQUIRED,
            message="Value is required" if not is_valid else None
        )

    @staticmethod
    def validate_unique(values: List[Any]) -> ValidationResult:
        """Validate uniqueness of values"""
        unique_values = set(values)
        is_valid = len(values) == len(unique_values)

        details = None
        if not is_valid:
            # Find duplicates
            value_counts = pd.Series(values).value_counts()
            duplicates = value_counts[value_counts > 1].to_dict()
            details = {'duplicates': duplicates}

        return ValidationResult(
            is_valid=is_valid,
            validation_type=ValidationType.UNIQUE,
            message="Duplicate values found" if not is_valid else None,
            details=details
        )


class DomainValidator:
    """Domain-specific validation utilities"""

    @staticmethod
    def validate_health_data(data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate health domain data"""
        results = []

        # Patient ID validation
        if 'patient_id' in data:
            results.append(
                DataValidator.validate_format(
                    str(data['patient_id']),
                    r'^[A-Z]{2}\d{6}$'  # Example: AB123456
                )
            )

        # Age validation
        if 'age' in data:
            results.append(
                DataValidator.validate_range(
                    data['age'],
                    min_value=0,
                    max_value=120
                )
            )

        return results

    @staticmethod
    def validate_financial_data(data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate financial domain data"""
        results = []

        # Account number validation
        if 'account_number' in data:
            results.append(
                DataValidator.validate_format(
                    str(data['account_number']),
                    r'^\d{10}$'  # Example: 10 digits
                )
            )

        # Amount validation
        if 'amount' in data:
            results.append(
                DataValidator.validate_range(
                    data['amount'],
                    min_value=0
                )
            )

        return results


class SchemaValidator:
    """Schema validation utilities"""

    @staticmethod
    def validate_schema(data: Dict[str, Any],
                        schema: Dict[str, Dict[str, Any]]) -> List[ValidationResult]:
        """Validate data against schema"""
        results = []

        for field, rules in schema.items():
            if field not in data:
                if rules.get('required', False):
                    results.append(ValidationResult(
                        is_valid=False,
                        validation_type=ValidationType.REQUIRED,
                        message=f"Required field {field} is missing"
                    ))
                continue

            value = data[field]

            # Type validation
            if 'type' in rules:
                results.append(
                    DataValidator.validate_data_type(value, rules['type'])
                )

            # Format validation
            if 'format' in rules:
                results.append(
                    DataValidator.validate_format(str(value), rules['format'])
                )

            # Range validation
            if 'range' in rules:
                results.append(
                    DataValidator.validate_range(
                        value,
                        rules['range'].get('min'),
                        rules['range'].get('max')
                    )
                )

            # Custom validation
            if 'validator' in rules and callable(rules['validator']):
                try:
                    custom_result = rules['validator'](value)
                    results.append(ValidationResult(
                        is_valid=custom_result[0],
                        validation_type=ValidationType.CUSTOM,
                        message=custom_result[1] if not custom_result[0] else None
                    ))
                except Exception as e:
                    results.append(ValidationResult(
                        is_valid=False,
                        validation_type=ValidationType.CUSTOM,
                        message=f"Custom validation error: {str(e)}"
                    ))

        return results


class DataFrameValidator:
    """Pandas DataFrame validation utilities"""

    @staticmethod
    def validate_dataframe(df: pd.DataFrame,
                           rules: Dict[str, Dict[str, Any]]) -> Dict[str, List[ValidationResult]]:
        """Validate DataFrame against rules"""
        results = {}

        for column, column_rules in rules.items():
            results[column] = []

            # Check if column exists
            if column not in df.columns:
                if column_rules.get('required', False):
                    results[column].append(ValidationResult(
                        is_valid=False,
                        validation_type=ValidationType.REQUIRED,
                        message=f"Required column {column} is missing"
                    ))
                continue

            # Data type validation
            if 'dtype' in column_rules:
                is_valid = df[column].dtype == column_rules['dtype']
                results[column].append(ValidationResult(
                    is_valid=is_valid,
                    validation_type=ValidationType.DATA_TYPE,
                    message=f"Expected type {column_rules['dtype']}, got {df[column].dtype}"
                    if not is_valid else None
                ))

            # Null check
            if not column_rules.get('allow_null', True):
                null_count = df[column].isnull().sum()
                is_valid = null_count == 0
                results[column].append(ValidationResult(
                    is_valid=is_valid,
                    validation_type=ValidationType.REQUIRED,
                    message=f"Column contains {null_count} null values"
                    if not is_valid else None,
                    details={'null_count': null_count} if not is_valid else None
                ))

            # Unique check
            if column_rules.get('unique', False):
                duplicate_count = df[column].duplicated().sum()
                is_valid = duplicate_count == 0
                results[column].append(ValidationResult(
                    is_valid=is_valid,
                    validation_type=ValidationType.UNIQUE,
                    message=f"Column contains {duplicate_count} duplicate values"
                    if not is_valid else None,
                    details={'duplicate_count': duplicate_count} if not is_valid else None
                ))

            # Range check for numeric columns
            if 'range' in column_rules and pd.api.types.is_numeric_dtype(df[column]):
                min_val = column_rules['range'].get('min')
                max_val = column_rules['range'].get('max')

                if min_val is not None:
                    below_min = df[column] < min_val
                    if below_min.any():
                        results[column].append(ValidationResult(
                            is_valid=False,
                            validation_type=ValidationType.RANGE,
                            message=f"{below_min.sum()} values below minimum {min_val}",
                            details={'count': below_min.sum()}
                        ))

                if max_val is not None:
                    above_max = df[column] > max_val
                    if above_max.any():
                        results[column].append(ValidationResult(
                            is_valid=False,
                            validation_type=ValidationType.RANGE,
                            message=f"{above_max.sum()} values above maximum {max_val}",
                            details={'count': above_max.sum()}
                        ))

        return results