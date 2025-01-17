from __future__ import annotations

import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class ValidationResult:
    """Structured validation result"""
    passed: bool
    check_type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    severity: ValidationLevel = ValidationLevel.ERROR

class DatabaseSourceValidator:
    """Comprehensive validator for db source configuration"""
    
    # Supported db types with their default ports
    SUPPORTED_DATABASES = {
        'postgresql': {'default_port': 5432},
        'mysql': {'default_port': 3306},
        'mssql': {'default_port': 1433},
        'oracle': {'default_port': 1521},
        'sqlite': {'default_port': None}
    }

    def __init__(self):
        """Initialize validator with validation rules"""
        self.validation_rules = {
            'min_database_length': 1,
            'max_database_length': 128,
            'min_host_length': 1,
            'max_host_length': 255,
            'allowed_chars': r'^[a-zA-Z0-9_\-\.]+$'
        }

    def validate_source_configuration(self, config: Dict[str, Any]) -> List[ValidationResult]:
        """
        Comprehensive validation of db source configuration
        
        Args:
            config: Database source configuration dictionary
        
        Returns:
            List of validation results
        """
        validation_results = []

        # Validate source type
        validation_results.append(self._validate_source_type(config.get('source_type')))

        # Validate host
        validation_results.append(self._validate_host(config.get('host')))

        # Validate port
        validation_results.append(self._validate_port(config.get('port'), config.get('source_type')))

        # Validate db name
        validation_results.append(self._validate_database_name(config.get('db')))

        # Validate username
        validation_results.append(self._validate_username(config.get('username')))

        return validation_results

    def _validate_source_type(self, source_type: Optional[str]) -> ValidationResult:
        """
        Validate db source type
        
        Args:
            source_type: Database source type to validate
        
        Returns:
            Validation result
        """
        if not source_type:
            return ValidationResult(
                passed=False,
                check_type='source_type',
                message="Source type is required",
                details={'supported_types': list(self.SUPPORTED_DATABASES.keys())},
                severity=ValidationLevel.ERROR
            )

        source_type_lower = source_type.lower()
        if source_type_lower not in self.SUPPORTED_DATABASES:
            return ValidationResult(
                passed=False,
                check_type='source_type',
                message=f"Unsupported db type: {source_type}",
                details={'supported_types': list(self.SUPPORTED_DATABASES.keys())},
                severity=ValidationLevel.ERROR
            )

        return ValidationResult(
            passed=True,
            check_type='source_type',
            message="Valid source type",
            details={'source_type': source_type_lower},
            severity=ValidationLevel.INFO
        )

    def _validate_host(self, host: Optional[str]) -> ValidationResult:
        """
        Validate host format and length
        
        Args:
            host: Hostname or IP address to validate
        
        Returns:
            Validation result
        """
        if not host:
            return ValidationResult(
                passed=False,
                check_type='host',
                message="Host is required",
                severity=ValidationLevel.ERROR
            )

        # Check host length
        if not (self.validation_rules['min_host_length'] <= len(host) <= self.validation_rules['max_host_length']):
            return ValidationResult(
                passed=False,
                check_type='host',
                message=f"Host length must be between {self.validation_rules['min_host_length']} and {self.validation_rules['max_host_length']} characters",
                details={'host': host},
                severity=ValidationLevel.ERROR
            )

        # Validate host format
        host_pattern = r'^[a-zA-Z0-9.-]+$'
        if not re.match(host_pattern, host):
            return ValidationResult(
                passed=False,
                check_type='host',
                message="Invalid host format",
                details={'host': host},
                severity=ValidationLevel.ERROR
            )

        return ValidationResult(
            passed=True,
            check_type='host',
            message="Valid host format",
            details={'host': host},
            severity=ValidationLevel.INFO
        )

    def _validate_port(self, port: Optional[int], source_type: Optional[str] = None) -> ValidationResult:
        """
        Validate port number
        
        Args:
            port: Port number to validate
            source_type: Database source type (for default port reference)
        
        Returns:
            Validation result
        """
        # If no port provided, check if it's acceptable for the source type
        if port is None:
            # For most databases except SQLite, a port is required
            if source_type and source_type.lower() != 'sqlite':
                return ValidationResult(
                    passed=False,
                    check_type='port',
                    message="Port is required for this db type",
                    severity=ValidationLevel.ERROR
                )
            return ValidationResult(
                passed=True,
                check_type='port',
                message="No port specified (acceptable for some db types)",
                severity=ValidationLevel.INFO
            )

        try:
            port_num = int(port)
            if not (0 < port_num <= 65535):
                return ValidationResult(
                    passed=False,
                    check_type='port',
                    message="Port must be between 1 and 65535",
                    details={'port': port_num},
                    severity=ValidationLevel.ERROR
                )

            return ValidationResult(
                passed=True,
                check_type='port',
                message="Valid port number",
                details={'port': port_num},
                severity=ValidationLevel.INFO
            )
        except (ValueError, TypeError):
            return ValidationResult(
                passed=False,
                check_type='port',
                message="Invalid port format",
                details={'port': port},
                severity=ValidationLevel.ERROR
            )

    def _validate_database_name(self, database: Optional[str]) -> ValidationResult:
        """
        Validate db name
        
        Args:
            database: Database name to validate
        
        Returns:
            Validation result
        """
        if not database:
            return ValidationResult(
                passed=False,
                check_type='database_name',
                message="Database name is required",
                severity=ValidationLevel.ERROR
            )

        # Check db name length
        if not (self.validation_rules['min_database_length'] <= len(database) <= self.validation_rules['max_database_length']):
            return ValidationResult(
                passed=False,
                check_type='database_name',
                message=f"Database name length must be between {self.validation_rules['min_database_length']} and {self.validation_rules['max_database_length']} characters",
                details={'db': database},
                severity=ValidationLevel.ERROR
            )

        # Validate db name characters
        if not re.match(self.validation_rules['allowed_chars'], database):
            return ValidationResult(
                passed=False,
                check_type='database_name',
                message="Database name contains invalid characters",
                details={'db': database, 'allowed_pattern': self.validation_rules['allowed_chars']},
                severity=ValidationLevel.ERROR
            )

        return ValidationResult(
            passed=True,
            check_type='database_name',
            message="Valid db name",
            details={'db': database},
            severity=ValidationLevel.INFO
        )

    def _validate_username(self, username: Optional[str]) -> ValidationResult:
        """
        Validate username
        
        Args:
            username: Username to validate
        
        Returns:
            Validation result
        """
        if not username:
            return ValidationResult(
                passed=False,
                check_type='username',
                message="Username is required",
                severity=ValidationLevel.ERROR
            )

        # Basic username validation
        username_pattern = r'^[a-zA-Z0-9_\-\.]+$'
        if not re.match(username_pattern, username):
            return ValidationResult(
                passed=False,
                check_type='username',
                message="Invalid username format",
                details={'username': username},
                severity=ValidationLevel.ERROR
            )

        return ValidationResult(
            passed=True,
            check_type='username',
            message="Valid username",
            details={'username': username},
            severity=ValidationLevel.INFO
        )

    def validate_connection_credentials(self, credentials: Dict[str, Any]) -> bool:
        """
        Quick check if credentials are valid for connection attempt
        
        Args:
            credentials: Credentials to validate
        
        Returns:
            Boolean indicating if credentials are valid
        """
        # Validate source configuration
        validation_results = self.validate_source_configuration(credentials)
        
        # Check if all validations passed
        return all(result.passed for result in validation_results)