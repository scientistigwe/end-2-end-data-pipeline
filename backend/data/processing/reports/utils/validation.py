# backend/data_pipeline/reporting/utils/validation.py

from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class ValidationError:
    """Represents a validation error"""
    field: str
    message: str
    code: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result of validation check"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]


class BusinessGoalValidator:
    """
    Validates business goal form data and provides detailed feedback.
    """

    def __init__(self, domain_loader):
        self.domain_loader = domain_loader

    def validate_form(self, form_data: Dict[str, Any]) -> ValidationResult:
        """Validate complete form data"""
        errors = []
        warnings = []

        # Required field checks
        required_fields = [
            ('domain', 'Domain selection is required'),
            ('datasetOverview', 'Dataset overview is required'),
            ('questions', 'At least one business question is required'),
            ('metrics', 'At least one metric must be selected')
        ]

        for field, message in required_fields:
            if not form_data.get(field):
                errors.append(ValidationError(
                    field=field,
                    message=message,
                    code='required_field_missing'
                ))

        # Domain-specific validation
        domain_id = form_data.get('domain')
        if domain_id:
            domain_errors, domain_warnings = self._validate_domain_requirements(
                domain_id,
                form_data
            )
            errors.extend(domain_errors)
            warnings.extend(domain_warnings)

        # Column validation
        if 'columns' in form_data:
            column_errors = self._validate_columns(
                domain_id,
                form_data['columns']
            )
            errors.extend(column_errors)

        # Metric validation
        if 'metrics' in form_data:
            metric_errors = self._validate_metrics(
                domain_id,
                form_data['metrics']
            )
            errors.extend(metric_errors)

        # Analysis type validation
        if 'analysisTypes' in form_data:
            analysis_errors = self._validate_analysis_types(
                domain_id,
                form_data['analysisTypes'],
                form_data.get('columns', [])
            )
            errors.extend(analysis_errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _validate_domain_requirements(
            self,
            domain_id: str,
            form_data: Dict[str, Any]
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate domain-specific requirements"""
        errors = []
        warnings = []

        domain_config = self.domain_loader.get_domain_config(domain_id)
        if not domain_config:
            errors.append(ValidationError(
                field='domain',
                message=f"Invalid domain selected: {domain_id}",
                code='invalid_domain'
            ))
            return errors, warnings

        # Check required columns
        missing_columns = self.domain_loader.validate_columns(
            domain_id,
            [col['name'] for col in form_data.get('columns', [])]
        )

        if missing_columns['missing_required']:
            errors.append(ValidationError(
                field='columns',
                message="Missing required columns for selected domain",
                code='missing_required_columns',
                details={'missing_columns': missing_columns['missing_required']}
            ))

        if missing_columns['extra_columns']:
            warnings.append(ValidationError(
                field='columns',
                message="Some columns are not standard for this domain",
                code='non_standard_columns',
                details={'extra_columns': missing_columns['extra_columns']}
            ))

        return errors, warnings

    def _validate_columns(
            self,
            domain_id: str,
            columns: List[Dict[str, Any]]
    ) -> List[ValidationError]:
        """Validate column configurations"""
        errors = []

        # Check column names are unique
        column_names = [col['name'] for col in columns]
        duplicates = [name for name in set(column_names)
                      if column_names.count(name) > 1]
        if duplicates:
            errors.append(ValidationError(
                field='columns',
                message="Duplicate column names found",
                code='duplicate_columns',
                details={'duplicate_names': duplicates}
            ))

        # Validate column types
        for column in columns:
            if not column.get('type'):
                errors.append(ValidationError(
                    field='columns',
                    message=f"Column type not specified for {column['name']}",
                    code='missing_column_type',
                    details={'column_name': column['name']}
                ))

        return errors

    def _validate_metrics(
            self,
            domain_id: str,
            metrics: List[str]
    ) -> List[ValidationError]:
        """Validate metric selections"""
        errors = []

        available_metrics = {
            metric['id'] for metric in
            self.domain_loader.get_common_metrics(domain_id)
        }

        invalid_metrics = [
            metric for metric in metrics
            if metric not in available_metrics
        ]

        if invalid_metrics:
            errors.append(ValidationError(
                field='metrics',
                message="Invalid metrics selected",
                code='invalid_metrics',
                details={'invalid_metrics': invalid_metrics}
            ))

        return errors

    def _validate_analysis_types(
            self,
            domain_id: str,
            analysis_types: List[str],
            columns: List[Dict[str, Any]]
    ) -> List[ValidationError]:
        """Validate insight type selections"""
        errors = []

        column_names = {col['name'] for col in columns}

        for analysis_type in analysis_types:
            required_columns = self.domain_loader.get_required_columns_for_analysis(
                domain_id,
                analysis_type
            )

            missing_columns = set(required_columns) - column_names
            if missing_columns:
                errors.append(ValidationError(
                    field='analysisTypes',
                    message=f"Missing required columns for {analysis_type}",
                    code='missing_analysis_columns',
                    details={
                        'analysis_type': analysis_type,
                        'missing_columns': list(missing_columns)
                    }
                ))

        return errors

    def validate_success_criteria(
            self,
            success_criteria: List[Dict[str, Any]]
    ) -> List[ValidationError]:
        """Validate success criteria"""
        errors = []

        for criteria in success_criteria:
            if not criteria.get('metric'):
                errors.append(ValidationError(
                    field='successCriteria',
                    message="Success criteria metric is required",
                    code='missing_criteria_metric'
                ))

            if not criteria.get('target'):
                errors.append(ValidationError(
                    field='successCriteria',
                    message="Success criteria target is required",
                    code='missing_criteria_target'
                ))

            # Validate target value format if specified
            target_value = criteria.get('target')
            if target_value and not self._is_valid_target_value(target_value):
                errors.append(ValidationError(
                    field='successCriteria',
                    message="Invalid target value format",
                    code='invalid_target_value',
                    details={'value': target_value}
                ))

        return errors

    def _is_valid_target_value(self, value: str) -> bool:
        """Check if target value is in valid format"""
        # Support percentage format (e.g., "10%")
        if re.match(r'^\d+(\.\d+)?%$', value):
            return True

        # Support numeric format
        if re.match(r'^\d+(\.\d+)?$', value):
            return True

        # Support comparison format (e.g., ">10", "<=5.5")
        if re.match(r'^[<>]=?\d+(\.\d+)?$', value):
            return True

        return False

    def suggest_improvements(
            self,
            form_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Suggest potential improvements to the business goal definition"""
        suggestions = []

        domain_id = form_data.get('domain')
        if not domain_id:
            return suggestions

        # Check for commonly used metrics
        common_metrics = self.domain_loader.get_common_metrics(domain_id)
        selected_metrics = set(form_data.get('metrics', []))

        for metric in common_metrics:
            if metric['id'] not in selected_metrics:
                suggestions.append({
                    'type': 'metric_suggestion',
                    'message': f"Consider adding {metric['name']} to your metrics",
                    'details': {
                        'metric_id': metric['id'],
                        'description': metric['description']
                    }
                })

        # Suggest relevant insight types
        selected_analyses = set(form_data.get('analysisTypes', []))
        available_analyses = self.domain_loader.get_analysis_types(domain_id)

        for analysis in available_analyses:
            if analysis['id'] not in selected_analyses:
                suggestions.append({
                    'type': 'analysis_suggestion',
                    'message': f"Consider including {analysis['name']} in your insight",
                    'details': {
                        'analysis_id': analysis['id'],
                        'description': analysis['description']
                    }
                })

        return suggestions