# backend/source_handlers/database/db_validator.py

import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DatabaseValidationConfig:
    """Configuration for database source validation"""

    REQUEST_TIMEOUT: int = 30  # 30 seconds default timeout

    # Supported database types with their default ports
    supported_sources: Dict[str, Dict[str, Optional[int]]] = field(default_factory=lambda: {
        'postgresql': {'default_port': 5432},
        'mysql': {'default_port': 3306},
        'mssql': {'default_port': 1433},
        'oracle': {'default_port': 1521},
        'sqlite': {'default_port': None}
    })

    # Validation constraints
    min_database_length: int = 1
    max_database_length: int = 128
    min_host_length: int = 1
    max_host_length: int = 255

    # Regular expression patterns
    allowed_database_chars: str = r'^[a-zA-Z0-9_\-\.]+$'
    allowed_host_chars: str = r'^[a-zA-Z0-9.-]+$'
    allowed_username_chars: str = r'^[a-zA-Z0-9_\-\.]+$'

    # Sensitive information patterns
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r'password', r'secret', r'key', r'token', r'credential'
    ])


class DatabaseSourceValidator:
    """Enhanced database source validator with integrated config"""

    def __init__(self, config: Optional[DatabaseValidationConfig] = None):
        self.config = config or DatabaseValidationConfig()

    async def validate_source(
            self,
            source_data: Dict[str, Any],
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of database source configuration

        Args:
            source_data: Database source configuration
            metadata: Additional metadata for validation

        Returns:
            Validation result with issues and warnings
        """
        try:
            issues = []
            warnings = []

            # Validate source type
            source_type_validation = await self._validate_source_type(
                source_data.get('source_type', '')
            )
            issues.extend(source_type_validation.get('issues', []))
            warnings.extend(source_type_validation.get('warnings', []))

            # Validate host
            host_validation = await self._validate_host(
                source_data.get('host', '')
            )
            issues.extend(host_validation.get('issues', []))
            warnings.extend(host_validation.get('warnings', []))

            # Validate port
            port_validation = await self._validate_port(
                source_data.get('port'),
                source_data.get('source_type')
            )
            issues.extend(port_validation.get('issues', []))
            warnings.extend(port_validation.get('warnings', []))

            # Validate database name
            db_validation = await self._validate_database_name(
                source_data.get('database', '')
            )
            issues.extend(db_validation.get('issues', []))
            warnings.extend(db_validation.get('warnings', []))

            # Validate username
            username_validation = await self._validate_username(
                source_data.get('username', '')
            )
            issues.extend(username_validation.get('issues', []))
            warnings.extend(username_validation.get('warnings', []))

            return self._build_result(
                passed=len(issues) == 0,
                issues=issues,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"Database source validation error: {str(e)}")
            return self._build_result(
                passed=False,
                issues=[str(e)],
                warnings=[]
            )

    async def _validate_source_type(self, source_type: str) -> Dict[str, Any]:
        """Validate database source type"""
        issues = []
        warnings = []

        # Check for empty source type
        if not source_type:
            issues.append("Source type is required")
            return {'issues': issues, 'warnings': warnings}

        # Normalize source type to lowercase
        source_type = source_type.lower()

        # Validate against supported sources
        if source_type not in self.config.supported_sources:
            issues.append(f"Unsupported database type: {source_type}")
            issues.append(f"Supported types: {', '.join(self.config.supported_sources.keys())}")

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_host(self, host: str) -> Dict[str, Any]:
        """Validate host format and length"""
        issues = []
        warnings = []

        # Check for empty host
        if not host:
            issues.append("Host is required")
            return {'issues': issues, 'warnings': warnings}

        # Check host length
        if not (self.config.min_host_length <= len(host) <= self.config.max_host_length):
            issues.append(
                f"Host length must be between {self.config.min_host_length} and {self.config.max_host_length} characters")

        # Validate host format
        if not re.match(self.config.allowed_host_chars, host):
            issues.append("Invalid host format")

        # Check for potentially sensitive information
        if any(re.search(pattern, host, re.IGNORECASE) for pattern in self.config.blocked_patterns):
            warnings.append("Potential sensitive information in host")

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_port(self, port: Optional[int], source_type: Optional[str] = None) -> Dict[str, Any]:
        """Validate port number"""
        issues = []
        warnings = []

        # If no port provided, check if it's acceptable for the source type
        if port is None:
            # For most databases except SQLite, a port is required
            if source_type and source_type.lower() != 'sqlite':
                issues.append("Port is required for this database type")
            return {'issues': issues, 'warnings': warnings}

        try:
            port_num = int(port)

            # Port range validation
            if not (0 < port_num <= 65535):
                issues.append("Port must be between 1 and 65535")

        except (ValueError, TypeError):
            issues.append("Invalid port format")

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_database_name(self, database: str) -> Dict[str, Any]:
        """Validate database name"""
        issues = []
        warnings = []

        # Check for empty database name
        if not database:
            issues.append("Database name is required")
            return {'issues': issues, 'warnings': warnings}

        # Check database name length
        if not (self.config.min_database_length <= len(database) <= self.config.max_database_length):
            issues.append(
                f"Database name length must be between {self.config.min_database_length} and {self.config.max_database_length} characters")

        # Validate database name characters
        if not re.match(self.config.allowed_database_chars, database):
            issues.append("Database name contains invalid characters")

        # Check for potentially sensitive information
        if any(re.search(pattern, database, re.IGNORECASE) for pattern in self.config.blocked_patterns):
            warnings.append("Potential sensitive information in database name")

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_username(self, username: str) -> Dict[str, Any]:
        """Validate username"""
        issues = []
        warnings = []

        # Check for empty username
        if not username:
            issues.append("Username is required")
            return {'issues': issues, 'warnings': warnings}

        # Validate username format
        if not re.match(self.config.allowed_username_chars, username):
            issues.append("Invalid username format")

        # Check for potentially sensitive information
        if any(re.search(pattern, username, re.IGNORECASE) for pattern in self.config.blocked_patterns):
            warnings.append("Potential sensitive information in username")

        return {
            'issues': issues,
            'warnings': warnings
        }

    def _build_result(
            self,
            passed: bool,
            issues: List[str],
            warnings: List[str]
    ) -> Dict[str, Any]:
        """Build structured validation result"""
        return {
            'passed': passed,
            'issues': issues,
            'warnings': warnings,
            'validation_time': datetime.utcnow().isoformat()
        }