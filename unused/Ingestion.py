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


from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests
import sqlalchemy
from sqlalchemy import create_engine
import yaml
import boto3
from concurrent.futures import ThreadPoolExecutor
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """Supported data source types"""
    CSV = "csv"
    API = "api"
    DATABASE = "database"
    PARQUET = "parquet"
    EXCEL = "excel"
    S3 = "s3"


@dataclass
class DataSourceConfig:
    """Configuration for data sources"""
    source_type: DataSourceType
    connection_details: Dict[str, Any]
    schema: Dict[str, str]
    validation_rules: Dict[str, Any]


class ValidationResult:
    """Stores validation results and statistics"""

    def __init__(self):
        self.total_checks = 0
        self.passed_checks = 0
        self.failed_checks = []
        self.warnings = []

    @property
    def pass_rate(self) -> float:
        """Calculate the percentage of passed checks"""
        return (self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0

    def add_result(self, passed: bool, check_name: str, message: str = ""):
        """Add a validation result"""
        self.total_checks += 1
        if passed:
            self.passed_checks += 1
        else:
            self.failed_checks.append({"check": check_name, "message": message})

    def is_acceptable(self, threshold: float = 95.0) -> bool:
        """Check if the validation results meet the acceptable threshold"""
        return self.pass_rate >= threshold


class DataReader(ABC):
    """Abstract base class for data readers"""

    @abstractmethod
    def read(self) -> Tuple[pd.DataFrame, ValidationResult]:
        """Read data from source and perform initial validation"""
        pass

    @staticmethod
    def get_reader(config: DataSourceConfig) -> 'DataReader':
        """Factory method to get appropriate reader"""
        readers = {
            DataSourceType.CSV: CSVReader,
            DataSourceType.API: APIReader,
            DataSourceType.DATABASE: DatabaseReader,
            DataSourceType.PARQUET: ParquetReader,
            DataSourceType.EXCEL: ExcelReader,
            DataSourceType.S3: S3Reader
        }
        return readers[config.source_type](config)


class CSVReader(DataReader):
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.chunk_size = 100000  # Adjustable based on memory constraints

    def read(self) -> Tuple[pd.DataFrame, ValidationResult]:
        file_path = self.config.connection_details['file_path']
        file_size = os.path.getsize(file_path)
        validation_result = ValidationResult()

        # Validate file existence and size
        validation_result.add_result(
            os.path.exists(file_path),
            "file_existence",
            "File does not exist"
        )
        validation_result.add_result(
            file_size > 0,
            "file_size",
            "File is empty"
        )

        if file_size > 1e9:  # 1GB
            return self._read_in_chunks(file_path, validation_result)
        else:
            return self._read_full(file_path, validation_result)

    def _read_full(self, file_path: str, validation_result: ValidationResult) -> Tuple[pd.DataFrame, ValidationResult]:
        try:
            df = pd.read_csv(file_path)
            validation_result.add_result(True, "read_success")
            return df, validation_result
        except Exception as e:
            validation_result.add_result(False, "read_success", str(e))
            raise

    def _read_in_chunks(self, file_path: str, validation_result: ValidationResult) -> Tuple[
        pd.DataFrame, ValidationResult]:
        chunks = []
        for chunk in pd.read_csv(file_path, chunksize=self.chunk_size):
            chunks.append(chunk)
        df = pd.concat(chunks)
        validation_result.add_result(True, "chunk_read_success")
        return df, validation_result


class APIReader(DataReader):
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.timeout = config.connection_details.get('timeout', 30)

    def read(self) -> Tuple[pd.DataFrame, ValidationResult]:
        validation_result = ValidationResult()
        url = self.config.connection_details['url']
        headers = self.config.connection_details.get('headers', {})

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            validation_result.add_result(
                response.status_code == 200,
                "api_response",
                f"API returned status code {response.status_code}"
            )

            data = response.json()
            df = pd.DataFrame(data)
            validation_result.add_result(True, "data_parsing")
            return df, validation_result

        except Exception as e:
            validation_result.add_result(False, "api_connection", str(e))
            raise


class DatabaseReader(DataReader):
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.batch_size = 50000

    def read(self) -> Tuple[pd.DataFrame, ValidationResult]:
        validation_result = ValidationResult()
        connection_string = self.config.connection_details['connection_string']
        query = self.config.connection_details['query']

        try:
            engine = create_engine(connection_string)
            with engine.connect() as connection:
                # Test connection
                validation_result.add_result(
                    connection.execute("SELECT 1").scalar() == 1,
                    "database_connection"
                )

                # Check if query is too large
                count_query = f"SELECT COUNT(*) FROM ({query}) as subquery"
                row_count = connection.execute(count_query).scalar()

                if row_count > self.batch_size:
                    return self._read_in_batches(connection, query, validation_result)
                else:
                    df = pd.read_sql(query, connection)
                    validation_result.add_result(True, "query_execution")
                    return df, validation_result

        except Exception as e:
            validation_result.add_result(False, "database_operation", str(e))
            raise

    def _read_in_batches(self, connection, query: str, validation_result: ValidationResult) -> Tuple[
        pd.DataFrame, ValidationResult]:
        frames = []
        offset = 0
        while True:
            batch_query = f"{query} LIMIT {self.batch_size} OFFSET {offset}"
            batch = pd.read_sql(batch_query, connection)
            if batch.empty:
                break
            frames.append(batch)
            offset += self.batch_size

        df = pd.concat(frames)
        validation_result.add_result(True, "batch_query_execution")
        return df, validation_result


class DataValidator:
    """Validates data quality"""

    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.validation_rules = config.validation_rules

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        result = ValidationResult()

        # Schema validation
        self._validate_schema(df, result)

        # Data quality checks
        self._validate_nulls(df, result)
        self._validate_duplicates(df, result)
        self._validate_data_types(df, result)
        self._validate_custom_rules(df, result)

        return result

    def _validate_schema(self, df: pd.DataFrame, result: ValidationResult):
        expected_columns = set(self.config.schema.keys())
        actual_columns = set(df.columns)

        result.add_result(
            expected_columns.issubset(actual_columns),
            "schema_validation",
            f"Missing columns: {expected_columns - actual_columns}"
        )

    def _validate_nulls(self, df: pd.DataFrame, result: ValidationResult):
        for column in self.validation_rules.get('required_fields', []):
            null_count = df[column].isnull().sum()
            result.add_result(
                null_count == 0,
                f"null_check_{column}",
                f"Column {column} has {null_count} null values"
            )

    def _validate_duplicates(self, df: pd.DataFrame, result: ValidationResult):
        key_columns = self.validation_rules.get('unique_fields', [])
        if key_columns:
            duplicates = df.duplicated(subset=key_columns, keep='first').sum()
            result.add_result(
                duplicates == 0,
                "duplicate_check",
                f"Found {duplicates} duplicate records"
            )

    def _validate_data_types(self, df: pd.DataFrame, result: ValidationResult):
        for column, expected_type in self.config.schema.items():
            if column in df.columns:
                try:
                    df[column].astype(expected_type)
                    result.add_result(True, f"type_check_{column}")
                except:
                    result.add_result(
                        False,
                        f"type_check_{column}",
                        f"Column {column} cannot be cast to {expected_type}"
                    )

    def _validate_custom_rules(self, df: pd.DataFrame, result: ValidationResult):
        custom_rules = self.validation_rules.get('custom_rules', {})
        for rule_name, rule_config in custom_rules.items():
            try:
                rule_result = eval(rule_config['condition'], {"df": df})
                result.add_result(
                    rule_result,
                    f"custom_rule_{rule_name}",
                    rule_config.get('message', '')
                )
            except Exception as e:
                result.add_result(
                    False,
                    f"custom_rule_{rule_name}",
                    f"Error evaluating rule: {str(e)}"
                )


class DataOptimizer:
    """Optimizes data storage based on size and usage patterns"""

    @staticmethod
    def optimize(df: pd.DataFrame, size_bytes: int) -> Tuple[Any, str]:
        """
        Determine the optimal storage format and return the converted data
        Returns: (converted_data, format_type)
        """
        if size_bytes < 1e8:  # 100MB
            return df, 'pandas'
        elif size_bytes < 1e9:  # 1GB
            return DataOptimizer._to_parquet(df), 'parquet'
        else:
            return DataOptimizer._to_partitioned_parquet(df), 'partitioned_parquet'

    @staticmethod
    def _to_parquet(df: pd.DataFrame) -> bytes:
        return df.to_parquet()

    @staticmethod
    def _to_partitioned_parquet(df: pd.DataFrame) -> str:
        # Partition by date if available, otherwise by first column
        partition_col = next((col for col in df.columns if 'date' in col.lower()), df.columns[0])
        return df.to_parquet('partitioned_data', partition_cols=[partition_col])


class DataIngestionManager:
    """Main class orchestrating the data ingestion process"""

    def __init__(self, config_path: str):
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
        self.config = DataSourceConfig(**config_dict)

    def ingest(self) -> Tuple[Any, ValidationResult]:
        """
        Main ingestion process
        Returns: (processed_data, validation_result)
        """
        # 1. Read data
        reader = DataReader.get_reader(self.config)
        df, read_validation = reader.read()

        # 2. Validate data
        validator = DataValidator(self.config)
        validation_result = validator.validate(df)

        # 3. Combine validation results
        for check in read_validation.failed_checks:
            validation_result.failed_checks.append(check)
        validation_result.total_checks += read_validation.total_checks
        validation_result.passed_checks += read_validation.passed_checks

        # 4. Check if validation meets threshold
        if not validation_result.is_acceptable():
            raise ValueError(
                f"Data quality check failed. Pass rate: {validation_result.pass_rate}%\n"
                f"Failed checks: {json.dumps(validation_result.failed_checks, indent=2)}"
            )

        # 5. Optimize storage
        size_bytes = df.memory_usage(deep=True).sum()
        optimized_data, format_type = DataOptimizer.optimize(df, size_bytes)

        logger.info(f"Data ingestion completed successfully. Format: {format_type}")
        return optimized_data, validation_result


# Example usage
if __name__ == "__main__":
    # Example configuration
    config = {
        "source_type": DataSourceType.CSV,
        "connection_details": {
            "file_path": "data.csv"
        },
        "schema": {
            "id": "int64",
            "name": "string",
            "value": "float64"
        },
        "validation_rules": {
            "required_fields": ["id", "name"],
            "unique_fields": ["id"],
            "custom_rules": {
                "value_range": {
                    "condition": "df['value'].between(0, 100).all()",
                    "message": "Values must be between 0 and 100"
                }
            }
        }
    }

    with open("config.yaml", "w") as f:
        yaml.dump(config, f)

    try:
        manager = DataIngestionManager("config.yaml")
        data, validation_result = manager.ingest()
        print(f"Ingestion successful! Validation pass rate: {validation_result.pass_rate}%")
    except Exception as e:
        print(f"Ingestion failed: {str(e)}")