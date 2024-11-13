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

