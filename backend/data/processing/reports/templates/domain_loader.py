# backend/data_pipeline/reporting/templates/domain_loader.py

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DomainLoader:
    """
    Handles loading and managing domain-specific templates.
    Provides domain configuration for the business goal form.
    """

    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or Path(__file__).parent / 'domains'
        self.domains: Dict[str, Dict[str, Any]] = {}
        self._load_domains()

    def _load_domains(self) -> None:
        """Load all domain templates"""
        try:
            for template_file in self.template_dir.glob('*_template.json'):
                with open(template_file, 'r') as f:
                    domain_config = json.load(f)
                    domain_id = domain_config.get('domain')
                    if domain_id:
                        self.domains[domain_id] = domain_config
                    else:
                        logger.warning(f"Missing domain ID in {template_file}")
        except Exception as e:
            logger.error(f"Error loading domain templates: {str(e)}")
            raise

    def get_domain_config(self, domain_id: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for specific domain

        Args:
            domain_id: The identifier of the domain

        Returns:
            The domain configuration dictionary if domain exists, None otherwise
        """
        return self.domains.get(domain_id)

    def suggest_column_mappings(self, domain_id: str, columns: List[str]) -> Dict[str, str]:
        """Suggest mappings for provided columns based on domain knowledge"""
        domain = self.domains.get(domain_id, {})
        common_columns = domain.get('common_columns', {})

        suggestions = {}
        for column in columns:
            # Exact match
            if column in common_columns:
                suggestions[column] = common_columns[column]['purpose']
                continue

            # Fuzzy match based on common patterns
            lower_column = column.lower()
            for common_name, config in common_columns.items():
                if common_name.lower() in lower_column:
                    suggestions[column] = config['purpose']
                    break

        return suggestions

    def get_required_columns_for_analysis(self, domain_id: str, analysis_type: str) -> List[str]:
        """Get required columns for specific insight type"""
        domain = self.domains.get(domain_id, {})
        analysis_types = {
            at['id']: at['required_columns']
            for at in domain.get('analysis_types', [])
        }
        return analysis_types.get(analysis_type, [])
        self.domains.get(domain_id)

    def get_available_domains(self) -> List[Dict[str, Any]]:
        """Get list of available domains"""
        return [
            {
                'id': domain_id,
                'name': config.get('name', ''),
                'icon': config.get('icon', '')
            }
            for domain_id, config in self.domains.items()
        ]

    def get_common_columns(self, domain_id: str) -> Dict[str, Any]:
        """Get common columns for domain"""
        domain = self.domains.get(domain_id, {})
        return domain.get('common_columns', {})

    def get_common_metrics(self, domain_id: str) -> List[Dict[str, Any]]:
        """Get common metrics for domain"""
        domain = self.domains.get(domain_id, {})
        return domain.get('common_metrics', [])

    def get_analysis_types(self, domain_id: str) -> List[Dict[str, Any]]:
        """Get insight types for domain"""
        domain = self.domains.get(domain_id, {})
        return domain.get('analysis_types', [])

    def get_common_questions(self, domain_id: str) -> List[str]:
        """Get common questions for domain"""
        domain = self.domains.get(domain_id, {})
        return domain.get('common_questions', [])

    def get_visualizations(self, domain_id: str) -> List[Dict[str, Any]]:
        """Get visualizations for domain"""
        domain = self.domains.get(domain_id, {})
        return domain.get('visualizations', [])

    def get_success_criteria_templates(self, domain_id: str) -> List[Dict[str, Any]]:
        """Get success criteria templates for domain"""
        domain = self.domains.get(domain_id, {})
        return domain.get('success_criteria_templates', [])

    def validate_columns(self, domain_id: str, columns: List[str]) -> Dict[str, List[str]]:
        """Validate columns against domain requirements"""
        domain = self.domains.get(domain_id, {})
        common_columns = domain.get('common_columns', {})

        required_columns = {
            name for name, config in common_columns.items()
            if config.get('required', False)
        }

        missing_required = required_columns - set(columns)
        extra_columns = set(columns) - set(common_columns.keys())

        return {
            'missing_required': list(missing_required),
            'extra_columns': list(extra_columns)
        }