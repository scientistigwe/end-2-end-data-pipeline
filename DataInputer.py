from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Type, Union
import pandas as pd
import sqlalchemy
from pathlib import Path


class DataSourceType(Enum):
    """Enumeration of supported data source types."""
    CSV = auto()
    API = auto()
    DATABASE = auto()
    EXCEL = auto()
    CLOUD = auto()
    UNKNOWN = auto()


@dataclass
class ValidationResult:
    """Stores the result of a validation check."""
    is_valid: bool
    message: str
    check_name: str


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, message: str, validation_results: List[ValidationResult]):
        super().__init__(message)
        self.validation_results = validation_results


class DataValidator(ABC):
    """Abstract base class for data validators."""

    @abstractmethod
    def validate(self) -> List[ValidationResult]:
        """Execute validation checks and return results."""
        pass


class SchemaValidator(DataValidator):
    """Validates data schema against expected schema."""

    def __init__(self, data: pd.DataFrame, expected_schema: Dict[str, Type]):
        self.data = data
        self.expected_schema = expected_schema

    def validate(self) -> List[ValidationResult]:
        results = []

        for field, expected_type in self.expected_schema.items():
            if field not in self.data.columns:
                results.append(ValidationResult(
                    False,
                    f"Missing field: {field}",
                    "schema_validation"
                ))
            elif not self.data[field].map(type).eq(expected_type).all():
                results.append(ValidationResult(
                    False,
                    f"Invalid type for field {field}. Expected {expected_type}",
                    "schema_validation"
                ))

        return results or [ValidationResult(True, "Schema validation passed", "schema_validation")]


class FreshnessValidator(DataValidator):
    """Validates data freshness based on last modified date."""

    def __init__(self, last_modified: datetime, threshold_days: int = 2):
        self.last_modified = last_modified
        self.threshold_days = threshold_days

    def validate(self) -> List[ValidationResult]:
        is_fresh = datetime.now() - self.last_modified <= timedelta(days=self.threshold_days)
        return [ValidationResult(
            is_fresh,
            "Data freshness check passed" if is_fresh else "Data is not fresh",
            "freshness_validation"
        )]


class NullValidator(DataValidator):
    """Validates presence of null values in mandatory fields."""

    def __init__(self, data: pd.DataFrame, mandatory_fields: List[str]):
        self.data = data
        self.mandatory_fields = mandatory_fields

    def validate(self) -> List[ValidationResult]:
        null_fields = [field for field in self.mandatory_fields
                       if self.data[field].isnull().any()]

        return [ValidationResult(
            not bool(null_fields),
            "No null values found" if not null_fields else f"Null values found in: {', '.join(null_fields)}",
            "null_validation"
        )]


class DataQualityChecker:
    """Main class for running data quality checks."""

    def __init__(self, data: Any, source_type: Optional[DataSourceType] = None):
        self.data = data
        self.source_type = source_type or self._determine_source_type()
        self.validators: List[DataValidator] = []

    def _determine_source_type(self) -> DataSourceType:
        """Determine the type of data source."""
        if isinstance(self.data, dict) and 'api' in self.data.get('source', '').lower():
            return DataSourceType.API
        elif isinstance(self.data, pd.DataFrame):
            return DataSourceType.CSV if 'csv' in self.data.attrs.get('source_type', '').lower() \
                else DataSourceType.EXCEL
        elif isinstance(self.data, str) and 's3://' in self.data:
            return DataSourceType.CLOUD
        elif isinstance(self.data, sqlalchemy.engine.ResultProxy):
            return DataSourceType.DATABASE
        return DataSourceType.UNKNOWN

    def add_validator(self, validator: DataValidator) -> None:
        """Add a validator to the checker."""
        self.validators.append(validator)

    def run_checks(self) -> List[ValidationResult]:
        """Run all registered validators."""
        results = []
        for validator in self.validators:
            results.extend(validator.validate())
        return results


class DataReader:
    """Utility class for reading data from various sources."""

    MAX_IN_MEMORY_SIZE_MB = 100

    @staticmethod
    def read_file(file_path: Union[str, Path], chunk_size: Optional[int] = None) -> pd.DataFrame:
        """Read data from a file, optionally in chunks."""
        file_path = Path(file_path)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)

        if chunk_size and file_size_mb > DataReader.MAX_IN_MEMORY_SIZE_MB:
            return DataReader._read_in_chunks(file_path, chunk_size)
        return DataReader._read_full_file(file_path)

    @staticmethod
    def _read_full_file(file_path: Path) -> pd.DataFrame:
        """Read entire file into memory."""
        if file_path.suffix == '.csv':
            return pd.read_csv(file_path)
        elif file_path.suffix == '.xlsx':
            return pd.read_excel(file_path)
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    @staticmethod
    def _read_in_chunks(file_path: Path, chunk_size: int):
        """Generator to read file in chunks."""
        if file_path.suffix == '.csv':
            return pd.read_csv(file_path, chunksize=chunk_size)
        raise NotImplementedError(f"Chunk reading not implemented for {file_path.suffix}")


# Example usage
def main():
    # Example with CSV data
    data = pd.DataFrame({
        'id': [1, 2, 3],
        'timestamp': ['2024-11-10', '2024-11-11', '2024-11-12'],
        'value': [100.5, 200.7, 150.1]
    })
    data.attrs['source_type'] = 'csv'

    # Initialize quality checker
    checker = DataQualityChecker(data)

    # Add validators
    checker.add_validator(SchemaValidator(data, {
        'id': int,
        'timestamp': str,
        'value': float
    }))
    checker.add_validator(NullValidator(data, ['id', 'timestamp', 'value']))
    checker.add_validator(FreshnessValidator(datetime.now()))

    # Run checks
    try:
        results = checker.run_checks()
        for result in results:
            print(f"{result.check_name}: {'✓' if result.is_valid else '✗'} - {result.message}")
    except ValidationError as e:
        print(f"Validation failed: {str(e)}")
        for result in e.validation_results:
            print(f"- {result.message}")


if __name__ == "__main__":
    main()