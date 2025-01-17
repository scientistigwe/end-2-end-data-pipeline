# backend/data_pipeline/reporting/config_handler.py

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .templates.domain_loader import DomainLoader
from .utils.validation import BusinessGoalValidator

logger = logging.getLogger(__name__)


class ConfigurationHandler:
    """
    Manages configuration and templates for business goal forms.
    Coordinates between domain loader and validation.
    """

    def __init__(self, template_dir: Optional[Path] = None):
        self.domain_loader = DomainLoader(template_dir)
        self.validator = BusinessGoalValidator(self.domain_loader)

    def get_initial_config(self) -> Dict[str, Any]:
        """Get initial configuration for business goal form"""
        return {
            'available_domains': self.domain_loader.get_available_domains(),
            'output_formats': self._get_output_formats(),
            'default_visualizations': self._get_default_visualizations()
        }

    def get_domain_config(self, domain_id: str) -> Dict[str, Any]:
        """Get configuration for specific domain"""
        domain_config = self.domain_loader.get_domain_config(domain_id)
        if not domain_config:
            raise ValueError(f"Invalid domain ID: {domain_id}")

        return {
            'common_columns': domain_config.get('common_columns', {}),
            'common_metrics': domain_config.get('common_metrics', []),
            'analysis_types': domain_config.get('analysis_types', []),
            'visualizations': domain_config.get('visualizations', []),
            'common_questions': domain_config.get('common_questions', []),
            'success_criteria_templates': domain_config.get('success_criteria_templates', [])
        }

    def validate_business_goal(
        self,
        form_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate business goal form data"""
        # Validate form data
        validation_result = self.validator.validate_form(form_data)

        # Get improvement suggestions
        suggestions = []
        if validation_result.is_valid:
            suggestions = self.validator.suggest_improvements(form_data)

        return {
            'is_valid': validation_result.is_valid,
            'errors': [
                {
                    'field': error.field,
                    'message': error.message,
                    'code': error.code,
                    'details': error.details
                }
                for error in validation_result.errors
            ],
            'warnings': [
                {
                    'field': warning.field,
                    'message': warning.message,
                    'code': warning.code,
                    'details': warning.details
                }
                for warning in validation_result.warnings
            ],
            'suggestions': suggestions
        }

    def get_column_suggestions(
        self,
        domain_id: str,
        columns: List[str]
    ) -> Dict[str, Any]:
        """Get suggestions for column mappings"""
        return {
            'mappings': self.domain_loader.suggest_column_mappings(domain_id, columns),
            'required_columns': self._get_required_columns(domain_id)
        }

    def _get_output_formats(self) -> List[Dict[str, Any]]:
        """Get available output formats"""
        return [
            {
                'id': 'dashboard',
                'name': 'Interactive Dashboard',
                'description': 'Interactive web-based dashboard with filters and drill-down capabilities',
                'icon': '📊'
            },
            {
                'id': 'report',
                'name': 'Detailed Report',
                'description': 'Comprehensive PDF report with analysis and recommendations',
                'icon': '📑'
            },
            {
                'id': 'presentation',
                'name': 'Executive Presentation',
                'description': 'PowerPoint presentation with key findings and visualizations',
                'icon': '📽️'
            },
            {
                'id': 'excel',
                'name': 'Excel Analysis',
                'description': 'Excel workbook with detailed data analysis and pivot tables',
                'icon': '📈'
            },
            {
                'id': 'api',
                'name': 'API Integration',
                'description': 'REST API endpoints for integrating results with other systems',
                'icon': '🔌'
            }
        ]

    def _get_default_visualizations(self) -> List[Dict[str, Any]]:
        """Get default visualization types"""
        return [
            {
                'id': 'line_chart',
                'name': 'Line Chart',
                'description': 'Show trends over time',
                'preview': '/assets/viz/line_chart.svg',
                'suitable_for': ['trends', 'time_series']
            },
            {
                'id': 'bar_chart',
                'name': 'Bar Chart',
                'description': 'Compare values across categories',
                'preview': '/assets/viz/bar_chart.svg',
                'suitable_for': ['comparison', 'ranking']
            },
            {
                'id': 'pie_chart',
                'name': 'Pie Chart',
                'description': 'Show composition and proportions',
                'preview': '/assets/viz/pie_chart.svg',
                'suitable_for': ['distribution', 'composition']
            },
            {
                'id': 'scatter_plot',
                'name': 'Scatter Plot',
                'description': 'Show relationships between variables',
                'preview': '/assets/viz/scatter_plot.svg',
                'suitable_for': ['correlation', 'relationships']
            },
            {
                'id': 'heatmap',
                'name': 'Heatmap',
                'description': 'Show patterns in matrix data',
                'preview': '/assets/viz/heatmap.svg',
                'suitable_for': ['patterns', 'matrix_data']
            },
            {
                'id': 'box_plot',
                'name': 'Box Plot',
                'description': 'Show distribution and outliers',
                'preview': '/assets/viz/box_plot.svg',
                'suitable_for': ['distribution', 'outliers']
            }
        ]

    def _get_required_columns(self, domain_id: str) -> List[str]:
        """Get required columns for domain"""
        domain_config = self.domain_loader.get_domain_config(domain_id)
        if not domain_config:
            return []

        return [
            col_name
            for col_name, col_config in domain_config.get('common_columns', {}).items()
            if col_config.get('required', False)
        ]

    def get_analysis_requirements(
        self,
        domain_id: str,
        analysis_types: List[str]
    ) -> Dict[str, Any]:
        """Get requirements for selected analysis types"""
        requirements = {
            'required_columns': set(),
            'recommended_metrics': set(),
            'suggested_visualizations': set()
        }

        for analysis_type in analysis_types:
            # Get required columns
            required_cols = self.domain_loader.get_required_columns_for_analysis(
                domain_id,
                analysis_type
            )
            requirements['required_columns'].update(required_cols)

            # Get analysis configuration
            domain_config = self.domain_loader.get_domain_config(domain_id)
            if domain_config:
                analysis_config = next(
                    (a for a in domain_config.get('analysis_types', [])
                     if a['id'] == analysis_type),
                    {}
                )

                # Add recommended metrics
                recommendations = analysis_config.get('recommended_metrics', [])
                requirements['recommended_metrics'].update(recommendations)

                # Add suggested visualizations
                visualizations = analysis_config.get('suggested_visualizations', [])
                requirements['suggested_visualizations'].update(visualizations)

        return {
            'required_columns': list(requirements['required_columns']),
            'recommended_metrics': list(requirements['recommended_metrics']),
            'suggested_visualizations': list(requirements['suggested_visualizations'])
        }

    def generate_analysis_plan(
        self,
        form_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate analysis plan from form data"""
        domain_id = form_data.get('domain')
        if not domain_id:
            raise ValueError("Domain ID is required")

        # Validate form data first
        validation_result = self.validate_business_goal(form_data)
        if not validation_result['is_valid']:
            raise ValueError("Invalid form data")

        # Get domain configuration
        domain_config = self.domain_loader.get_domain_config(domain_id)

        # Create analysis plan
        return {
            'plan_id': str(uuid.uuid4()),
            'domain': domain_config['name'],
            'objectives': {
                'questions': form_data.get('questions', []),
                'required_insights': form_data.get('insights', ''),
                'success_criteria': form_data.get('successCriteria', [])
            },
            'data_requirements': {
                'required_columns': self._get_required_columns(domain_id),
                'column_mappings': form_data.get('columns', []),
                'metrics': self._get_plan_metrics(domain_id, form_data)
            },
            'analysis_components': {
                'types': form_data.get('analysisTypes', []),
                'requirements': self.get_analysis_requirements(
                    domain_id,
                    form_data.get('analysisTypes', [])
                )
            },
            'output_requirements': {
                'formats': form_data.get('outputFormats', []),
                'visualizations': form_data.get('visualizations', [])
            },
            'constraints': form_data.get('constraints', []),
            'implementation': {
                'phases': self._generate_implementation_phases(form_data),
                'dependencies': self._identify_dependencies(form_data)
            }
        }

    def _get_plan_metrics(
        self,
        domain_id: str,
        form_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get detailed metric configurations for plan"""
        selected_metrics = form_data.get('metrics', [])
        common_metrics = self.domain_loader.get_common_metrics(domain_id)

        return [
            metric for metric in common_metrics
            if metric['id'] in selected_metrics
        ]

    def _generate_implementation_phases(
        self,
        form_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate implementation phases for analysis plan"""
        return [
            {
                'phase': 'data_preparation',
                'name': 'Data Preparation',
                'tasks': [
                    'Validate required columns',
                    'Handle missing values',
                    'Format data types',
                    'Create derived features'
                ]
            },
            {
                'phase': 'analysis',
                'name': 'Analysis Execution',
                'tasks': [task for analysis_type in form_data.get('analysisTypes', [])
                         for task in self._get_analysis_tasks(analysis_type)]
            },
            {
                'phase': 'output_generation',
                'name': 'Output Generation',
                'tasks': [f"Generate {format}" for format in form_data.get('outputFormats', [])]
            }
        ]

    def _get_analysis_tasks(self, analysis_type: str) -> List[str]:
        """Get tasks for specific analysis type"""
        # This would be expanded based on analysis type
        return [
            f"Execute {analysis_type} analysis",
            f"Generate visualizations for {analysis_type}",
            f"Prepare findings for {analysis_type}"
        ]

    def _identify_dependencies(
        self,
        form_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify dependencies between analysis components"""
        dependencies = []
        analysis_types = form_data.get('analysisTypes', [])

        # Example dependency identification
        if 'trend_analysis' in analysis_types and 'forecasting' in analysis_types:
            dependencies.append({
                'source': 'trend_analysis',
                'target': 'forecasting',
                'type': 'prerequisite',
                'description': 'Trend analysis should be completed before forecasting'
            })

        return dependencies

    def save_business_goal(
        self,
        form_data: Dict[str, Any]
    ) -> str:
        """Save business goal configuration"""
        # This would be implemented to save to database
        goal_id = str(uuid.uuid4())
        # Save logic here
        return goal_id

    def load_business_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Load saved business goal configuration"""
        # This would be implemented to load from database
        return None