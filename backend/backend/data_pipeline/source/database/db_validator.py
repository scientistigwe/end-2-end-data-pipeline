from __future__ import annotations

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sqlparse
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
import pandas as pd

from backend.core.monitoring.process import ProcessMonitor
from backend.core.monitoring.collectors import MetricsCollector
from .db_config import Config

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Structured validation result"""
    passed: bool
    check_type: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    severity: ValidationLevel = ValidationLevel.ERROR


class DBValidator:
    """Enhanced database validator with comprehensive validation capabilities"""

    def __init__(
            self,
            config: Optional[Config] = None,
            metrics_collector: Optional[MetricsCollector] = None
    ):
        """Initialize validator with configuration"""
        self.config = config or Config()
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="db_validator",
            source_id="validator"
        )

        # Query validation settings
        self.validation_rules = {
            'max_table_joins': 5,
            'max_subqueries': 3,
            'max_union_depth': 2,
            'max_cte_depth': 3,
            'prohibited_keywords': [
                'TRUNCATE', 'DROP', 'DELETE', 'UPDATE', 'INSERT',
                'GRANT', 'REVOKE', 'ALTER', 'CREATE'
            ]
        }

        # Data type mapping
        self.type_mapping = {
            'INTEGER': 'int64',
            'BIGINT': 'int64',
            'NUMERIC': 'float64',
            'FLOAT': 'float64',
            'TIMESTAMP': 'datetime64[ns]',
            'DATE': 'datetime64[ns]',
            'VARCHAR': 'object',
            'TEXT': 'object',
            'BOOLEAN': 'bool'
        }

    async def validate_connection_params(
            self,
            connection_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate database connection parameters

        Args:
            connection_data: Connection parameters to validate

        Returns:
            Dictionary containing validation results
        """
        try:
            validation_start = datetime.now()
            results = []

            # Execute validations concurrently
            validation_tasks = [
                self.validate_database_type(connection_data.get('type')),
                self.validate_credentials(connection_data.get('credentials', {})),
                self.validate_connection_string(connection_data)
            ]

            # Gather results
            results.extend(await asyncio.gather(*validation_tasks, return_exceptions=True))

            # Filter out exceptions and create error validations
            filtered_results = []
            for result in results:
                if isinstance(result, Exception):
                    filtered_results.append(ValidationResult(
                        passed=False,
                        check_type='error',
                        message=f"Validation error: {str(result)}",
                        details={'error': str(result)},
                        severity=ValidationLevel.ERROR
                    ))
                else:
                    filtered_results.append(result)

            # Compile results
            validation_summary = self._compile_validation_results(filtered_results)

            # Record metrics
            await self.process_monitor.record_operation_metric(
                'connection_validation',
                success=validation_summary['passed'],
                duration=(datetime.now() - validation_start).total_seconds(),
                check_count=len(filtered_results)
            )

            return validation_summary

        except Exception as e:
            logger.error(f"Connection validation error: {str(e)}", exc_info=True)
            return {
                'passed': False,
                'error': str(e),
                'checks': []
            }

    async def validate_database_type(
            self,
            db_type: Optional[str]
    ) -> ValidationResult:
        """Validate database type"""
        try:
            if not db_type:
                return ValidationResult(
                    passed=False,
                    check_type='database_type',
                    message="Database type is required",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            if db_type not in self.config.SUPPORTED_DATABASES:
                return ValidationResult(
                    passed=False,
                    check_type='database_type',
                    message=f"Unsupported database type: {db_type}",
                    details={
                        'type': db_type,
                        'supported_types': list(self.config.SUPPORTED_DATABASES.keys())
                    },
                    severity=ValidationLevel.ERROR
                )

            return ValidationResult(
                passed=True,
                check_type='database_type',
                message="Database type is valid",
                details={'type': db_type},
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='database_type',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_credentials(
            self,
            credentials: Dict[str, Any]
    ) -> ValidationResult:
        """Validate database credentials"""
        try:
            required_fields = ['username', 'password']
            missing_fields = [
                field for field in required_fields
                if field not in credentials
            ]

            if missing_fields:
                return ValidationResult(
                    passed=False,
                    check_type='credentials',
                    message=f"Missing required credentials: {', '.join(missing_fields)}",
                    details={'missing_fields': missing_fields},
                    severity=ValidationLevel.ERROR
                )

            # Basic credential format validation
            if not credentials['username'] or len(credentials['username']) < 3:
                return ValidationResult(
                    passed=False,
                    check_type='credentials',
                    message="Invalid username format",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            if not credentials['password'] or len(credentials['password']) < 8:
                return ValidationResult(
                    passed=False,
                    check_type='credentials',
                    message="Invalid password format",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            return ValidationResult(
                passed=True,
                check_type='credentials',
                message="Credentials format is valid",
                details={
                    'fields_provided': list(credentials.keys())
                },
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='credentials',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_connection_string(
            self,
            connection_data: Dict[str, Any]
    ) -> ValidationResult:
        """Validate database connection string format"""
        try:
            required_fields = ['host', 'port', 'database']
            missing_fields = [
                field for field in required_fields
                if field not in connection_data
            ]

            if missing_fields:
                return ValidationResult(
                    passed=False,
                    check_type='connection_string',
                    message=f"Missing connection parameters: {', '.join(missing_fields)}",
                    details={'missing_fields': missing_fields},
                    severity=ValidationLevel.ERROR
                )

            # Validate host format
            import re
            host_pattern = r'^[a-zA-Z0-9.-]+$'
            if not re.match(host_pattern, connection_data['host']):
                return ValidationResult(
                    passed=False,
                    check_type='connection_string',
                    message="Invalid host format",
                    details={'host': connection_data['host']},
                    severity=ValidationLevel.ERROR
                )

            # Validate port
            try:
                port = int(connection_data['port'])
                if not (0 < port <= 65535):
                    raise ValueError("Port out of range")
            except (ValueError, TypeError):
                return ValidationResult(
                    passed=False,
                    check_type='connection_string',
                    message="Invalid port number",
                    details={'port': connection_data['port']},
                    severity=ValidationLevel.ERROR
                )

            # Validate database name format
            db_pattern = r'^[a-zA-Z0-9_-]+$'
            if not re.match(db_pattern, connection_data['database']):
                return ValidationResult(
                    passed=False,
                    check_type='connection_string',
                    message="Invalid database name format",
                    details={'database': connection_data['database']},
                    severity=ValidationLevel.ERROR
                )

            return ValidationResult(
                passed=True,
                check_type='connection_string',
                message="Connection string format is valid",
                details={
                    'host': connection_data['host'],
                    'port': port,
                    'database': connection_data['database']
                },
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='connection_string',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_query_comprehensive(
            self,
            query: str,
            params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Perform comprehensive query validation"""
        try:
            validation_start = datetime.now()
            results = []

            # Execute validations concurrently
            validation_tasks = [
                self.validate_query_syntax(query),
                self.validate_query_security(query),
                self.validate_query_complexity(query),
                self.validate_query_parameters(query, params or {})
            ]

            # Gather results
            results.extend(await asyncio.gather(*validation_tasks, return_exceptions=True))

            # Compile results
            validation_summary = self._compile_validation_results(results)

            # Record metrics
            await self.process_monitor.record_operation_metric(
                'query_validation',
                success=validation_summary['passed'],
                duration=(datetime.now() - validation_start).total_seconds()
            )

            # Add recommendations if needed
            validation_summary['recommendations'] = (
                self._generate_query_recommendations(validation_summary)
            )

            return validation_summary

        except Exception as e:
            logger.error(f"Query validation error: {str(e)}")
            return {
                'passed': False,
                'error': str(e),
                'checks': []
            }

    async def validate_query_syntax(
            self,
            query: str
    ) -> ValidationResult:
        """Validate SQL query syntax"""
        try:
            # Parse query
            parsed = sqlparse.parse(query)
            if not parsed:
                return ValidationResult(
                    passed=False,
                    check_type='syntax',
                    message="Empty or invalid query",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            # Analyze query structure
            stmt = parsed[0]
            if not stmt.get_type():
                return ValidationResult(
                    passed=False,
                    check_type='syntax',
                    message="Unable to determine query type",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            # Check basic structure
            if stmt.get_type().upper() != 'SELECT':
                return ValidationResult(
                    passed=False,
                    check_type='syntax',
                    message="Only SELECT statements are allowed",
                    details={'query_type': stmt.get_type()},
                    severity=ValidationLevel.ERROR
                )

            return ValidationResult(
                passed=True,
                check_type='syntax',
                message="Query syntax is valid",
                details={
                    'query_type': stmt.get_type(),
                    'tokens': len(stmt.tokens)
                },
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='syntax',
                message=f"Syntax validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_query_security(
            self,
            query: str
    ) -> ValidationResult:
        """Validate query security"""
        try:
            # Check for prohibited keywords
            query_upper = query.upper()
            found_keywords = [
                keyword for keyword in self.validation_rules['prohibited_keywords']
                if keyword in query_upper
            ]

            if found_keywords:
                return ValidationResult(
                    passed=False,
                    check_type='security',
                    message="Query contains prohibited keywords",
                    details={'keywords': found_keywords},
                    severity=ValidationLevel.ERROR
                )

            # Check for SQL injection patterns
            injection_patterns = [
                '--', ';--', ';', '/*', '*/', 'UNION ALL',
                'UNION SELECT', 'EXEC', 'EXECUTE'
            ]
            found_patterns = [
                pattern for pattern in injection_patterns
                if pattern in query_upper
            ]

            if found_patterns:
                return ValidationResult(
                    passed=False,
                    check_type='security',
                    message="Potential SQL injection detected",
                    details={'patterns': found_patterns},
                    severity=ValidationLevel.ERROR
                )

            return ValidationResult(
                passed=True,
                check_type='security',
                message="Query passes security checks",
                details={},
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='security',
                message=f"Security validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_query_complexity(
            self,
            query: str
    ) -> ValidationResult:
        """Validate query complexity"""
        try:
            # Parse query
            parsed = sqlparse.parse(query)[0]
            complexity_metrics = {
                'join_count': self._count_joins(query),
                'subquery_count': self._count_subqueries(query),
                'union_count': query.upper().count('UNION'),
                'cte_count': self._count_ctes(query),
                'where_conditions': self._count_where_conditions(parsed),
                'group_by_count': query.upper().count('GROUP BY'),
                'having_count': query.upper().count('HAVING')
            }

            # Check against thresholds
            issues = []
            if complexity_metrics['join_count'] > self.validation_rules['max_table_joins']:
                issues.append(f"Too many joins ({complexity_metrics['join_count']})")

            if complexity_metrics['subquery_count'] > self.validation_rules['max_subqueries']:
                issues.append(f"Too many subqueries ({complexity_metrics['subquery_count']})")

            if complexity_metrics['union_count'] > self.validation_rules['max_union_depth']:
                issues.append(f"Too many UNION operations ({complexity_metrics['union_count']})")

            if complexity_metrics['cte_count'] > self.validation_rules['max_cte_depth']:
                issues.append(f"Too many CTEs ({complexity_metrics['cte_count']})")

            severity = (
                ValidationLevel.ERROR if issues
                else ValidationLevel.WARNING if sum(complexity_metrics.values()) > 10
                else ValidationLevel.INFO
            )

            return ValidationResult(
                passed=len(issues) == 0,
                check_type='complexity',
                message="Query complexity analysis complete",
                details={
                    'metrics': complexity_metrics,
                    'issues': issues
                },
                severity=severity
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='complexity',
                message=f"Complexity validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_query_parameters(
            self,
            query: str,
            params: Dict[str, Any]
    ) -> ValidationResult:
        """Validate query parameters"""
        try:
            # Extract parameter placeholders
            placeholders = self._extract_placeholders(query)

            # Compare with provided parameters
            missing_params = placeholders - set(params.keys())
            extra_params = set(params.keys()) - placeholders

            issues = []
            if missing_params:
                issues.append(f"Missing parameters: {', '.join(missing_params)}")
            if extra_params:
                issues.append(f"Unexpected parameters: {', '.join(extra_params)}")

            # Validate parameter types
            invalid_types = []
            for param, value in params.items():
                if not self._is_valid_parameter_type(value):
                    invalid_types.append(param)

            if invalid_types:
                issues.append(f"Invalid parameter types: {', '.join(invalid_types)}")

            severity = (
                ValidationLevel.ERROR if missing_params
                else ValidationLevel.WARNING if issues
                else ValidationLevel.INFO
            )

            return ValidationResult(
                passed=len(issues) == 0,
                check_type='parameters',
                message="Parameter validation complete",
                details={
                    'placeholders': list(placeholders),
                    'provided_params': list(params.keys()),
                    'issues': issues
                },
                severity=severity
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='parameters',
                message=f"Parameter validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def verify_access_permissions(
            self,
            engine: Engine,
            database: str,
            schema: str
    ) -> Dict[str, Any]:
        """Verify database access permissions"""
        try:
            permissions = []
            restrictions = []

            inspector = inspect(engine)

            # Check schema access
            try:
                schemas = inspector.get_schema_names()
                if schema in schemas:
                    permissions.append('schema_access')
                else:
                    restrictions.append('schema_restricted')
            except Exception as e:
                restrictions.append('schema_list_restricted')

            # Check table access
            try:
                tables = inspector.get_table_names(schema=schema)
                if tables:
                    permissions.append('table_access')
            except Exception as e:
                restrictions.append('table_list_restricted')

            # Check view access
            try:
                views = inspector.get_view_names(schema=schema)
                if views:
                    permissions.append('view_access')
            except Exception as e:
                restrictions.append('view_list_restricted')

            return {
                'has_access': bool(permissions),
                'permissions': permissions,
                'restrictions': restrictions,
                'message': (
                    "Access verified" if permissions
                    else "Insufficient permissions"
                )
            }

        except Exception as e:
            logger.error(f"Access verification error: {str(e)}")
            return {
                'has_access': False,
                'message': str(e)
            }

    def _count_joins(self, query: str) -> int:
        """Count number of JOIN operations"""
        return sum(
            1 for join_type in ['JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN']
            if join_type in query.upper()
        )

    def _count_subqueries(self, query: str) -> int:
        """Count number of subqueries"""
        return query.upper().count('SELECT') - 1  # Subtract main query

    def _count_ctes(self, query: str) -> int:
        """Count number of CTEs (Common Table Expressions)"""
        return query.upper().count('WITH')

    def _count_where_conditions(self, parsed_query) -> int:
        """Count WHERE conditions"""
        count = 0
        for token in parsed_query.tokens:
            if token.is_group:
                count += self._count_where_conditions(token)
            elif token.ttype is None and token.value.upper() == 'WHERE':
                count += 1
        return count

    def _extract_placeholders(self, query: str) -> set:
        """Extract parameter placeholders from query"""
        import re
        # Match both :name and %(name)s style placeholders
        placeholders = set()
        placeholders.update(re.findall(r':(\w+)', query))
        placeholders.update(re.findall(r'%\((\w+)\)s', query))
        return placeholders

    def _is_valid_parameter_type(self, value: Any) -> bool:
        """Check if parameter type is valid for database"""
        return isinstance(value, (str, int, float, bool, datetime, bytes))

    def _compile_validation_results(
            self,
            results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """Compile validation results into summary"""
        return {
            'passed': all(result.passed for result in results),
            'checks': [
                {
                    'type': result.check_type,
                    'passed': result.passed,
                    'message': result.message,
                    'details': result.details,
                    'severity': result.severity.value,
                    'timestamp': result.timestamp.isoformat()
                }
                for result in results
            ],
            'summary': {
                'total_checks': len(results),
                'passed_checks': sum(1 for result in results if result.passed),
                'failed_checks': sum(1 for result in results if not result.passed),
                'highest_severity': max(
                    (result.severity for result in results),
                    default=ValidationLevel.INFO
                ).value
            }
        }

    def _generate_query_recommendations(
            self,
            validation_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate query improvement recommendations"""
        recommendations = []

        for check in validation_summary['checks']:
            if check['type'] == 'complexity' and check['details'].get('metrics'):
                metrics = check['details']['metrics']

                if metrics['join_count'] > 3:
                    recommendations.append({
                        'type': 'performance',
                        'category': 'joins',
                        'message': "Consider optimizing join operations",
                        'suggestion': "Review join conditions and table order"
                    })

                if metrics['subquery_count'] > 2:
                    recommendations.append({
                        'type': 'performance',
                        'category': 'subqueries',
                        'message': "High number of subqueries detected",
                        'suggestion': "Consider using CTEs or join operations"
                    })

            elif check['type'] == 'parameters' and not check['passed']:
                recommendations.append({
                    'type': 'safety',
                    'category': 'parameters',
                    'message': "Parameter validation issues detected",
                    'suggestion': "Ensure all parameters are properly defined and typed"
                })

        return recommendations