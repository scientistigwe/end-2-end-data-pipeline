# backend/data_pipeline/reporting/templates/template_loader.py

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
import json

from .filters import register_filters

logger = logging.getLogger(__name__)


class TemplateLoader:
    """
    Handles loading and initialization of report templates.
    Manages template environment and custom filters.
    """

    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or Path(__file__).parent / 'templates'
        self.env = self._create_environment()

        # Cache for compiled templates
        self._template_cache: Dict[str, Any] = {}

    def _create_environment(self) -> Environment:
        """Create and configure Jinja environment"""
        env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Register custom filters
        register_filters(env)

        # Add global functions
        env.globals.update({
            'include_file': self._include_file,
            'load_chart_config': self._load_chart_config
        })

        return env

    def get_template(self, template_name: str) -> Any:
        """Get template by name"""
        try:
            if template_name not in self._template_cache:
                self._template_cache[template_name] = self.env.get_template(template_name)
            return self._template_cache[template_name]
        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {str(e)}")
            raise

    def render_template(self, template_name: str, data: Dict[str, Any]) -> str:
        """Render template with data"""
        try:
            template = self.get_template(template_name)
            return template.render(**data)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {str(e)}")
            raise

    def clear_cache(self) -> None:
        """Clear template cache"""
        self._template_cache.clear()

    def reload_templates(self) -> None:
        """Reload all templates"""
        self.clear_cache()
        self.env = self._create_environment()

    def _include_file(self, filename: str) -> str:
        """Include file content in template"""
        try:
            file_path = self.template_dir / filename
            return file_path.read_text()
        except Exception as e:
            logger.error(f"Failed to include file {filename}: {str(e)}")
            return f"<!-- Failed to include {filename} -->"

    def _load_chart_config(self, chart_type: str) -> Dict[str, Any]:
        """Load chart configuration from JSON"""
        try:
            config_path = self.template_dir / 'charts' / f"{chart_type}.json"
            return json.loads(config_path.read_text())
        except Exception as e:
            logger.error(f"Failed to load chart config {chart_type}: {str(e)}")
            return {}