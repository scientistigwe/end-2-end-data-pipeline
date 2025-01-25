"""Custom exceptions for the data pipeline."""
from typing import Optional

class DataPipelineError(Exception):
    """Base exception class for all data pipeline errors."""

    def __init__(self, message: str = None):
        self.message = message or "An error occurred in the data pipeline"
        super().__init__(self.message)


class InvalidCloudProviderError(DataPipelineError):
    """Raised when an invalid cloud provider is specified."""

    def __init__(self, provider: str = None):
        message = f"Invalid cloud provider specified: {provider}" if provider else "Invalid cloud provider"
        super().__init__(message)


class CloudConnectionError(DataPipelineError):
    """Raised when there's an error connecting to cloud pipeline."""

    def __init__(self, service: str = None, details: str = None):
        message = f"Failed to connect to {service}: {details}" if service else "Cloud connection error"
        super().__init__(message)


class DataEncodingError(DataPipelineError):
    """Raised when there's an error encoding/decoding data."""

    def __init__(self, operation: str = None, details: str = None):
        message = f"Data {operation} error: {details}" if operation else "Data encoding error"
        super().__init__(message)


class StreamingConnectionError(DataPipelineError):
    """Raised when there's an error connecting to streaming pipeline."""

    def __init__(self, service: str = None, details: str = None):
        message = f"Failed to connect to streaming service {service}: {details}" if service else "Streaming connection error"
        super().__init__(message)


class StreamingDataLoadingError(DataPipelineError):
    """Raised when there's an error loading streaming data."""

    def __init__(self, details: str = None):
        message = f"Failed to load streaming data: {details}" if details else "Streaming data loading error"
        super().__init__(message)


class StreamingDataValidationError(DataPipelineError):
    """Raised when streaming data fails validation."""

    def __init__(self, details: str = None):
        message = f"Streaming data validation failed: {details}" if details else "Streaming data validation error"
        super().__init__(message)


class DatabaseConnectionError(DataPipelineError):
    """Raised when there's an error connecting to the db."""

    def __init__(self, database: str = None, details: str = None):
        message = f"Failed to connect to db {database}: {details}" if database else "Database connection error"
        super().__init__(message)


class DatabaseQueryError(DataPipelineError):
    """Raised when there's an error executing a db query."""

    def __init__(self, query: str = None, details: str = None):
        message = f"Query execution failed: {details}" if details else "Database query error"
        super().__init__(message)


class DataValidationError(DataPipelineError):
    """Raised when data fails validation."""

    def __init__(self, details: str = None):
        message = f"Data validation failed: {details}" if details else "Data validation error"
        super().__init__(message)


class InvalidDatabaseTypeError(Exception):
    pass


class CloudQueryError(Exception):
    pass


class DatabaseError(Exception):
    """Base exception for all db-related errors"""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class DatabaseConfigError(DatabaseError):
    """Configuration-related errors"""
    pass



class DatabaseSecurityError(DatabaseError):
    """Security-related errors"""
    pass


class DatabaseValidationError(DatabaseError):
    """Validation-related errors"""
    pass

