# backend/data_pipeline/reporting/formatters/base_formatter.py

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from ..types.reports_types import (
    Report,
    ReportSection,
    ReportContent,
    ReportVisualization,
    ReportFormat
)

logger = logging.getLogger(__name__)


class BaseFormatter(ABC):
    """
    Base class for report formatters.
    Defines interface and common functionality for formatting reports.
    """

    def __init__(
            self,
            template_dir: Optional[Path] = None,
            config: Optional[Dict[str, Any]] = None
    ):
        self.template_dir = template_dir or Path("templates")
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    async def format_report(self, report: Report) -> Dict[str, Any]:
        """Format complete report"""
        pass

    @abstractmethod
    async def format_section(self, section: ReportSection) -> Dict[str, Any]:
        """Format report section"""
        pass

    @abstractmethod
    async def format_visualization(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format visualization"""
        pass

    async def load_template(self, template_name: str) -> str:
        """Load template file"""
        try:
            template_path = self.template_dir / f"{template_name}.template"
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_name}")

            return template_path.read_text()

        except Exception as e:
            self.logger.error(f"Failed to load template {template_name}: {str(e)}")
            raise

    def validate_report(self, report: Report) -> bool:
        """Validate report structure and content"""
        try:
            # Check required fields
            if not report.report_id:
                raise ValueError("Report ID is required")
            if not report.pipeline_id:
                raise ValueError("Pipeline ID is required")
            if not report.title:
                raise ValueError("Report title is required")
            if not report.sections:
                raise ValueError("Report must contain at least one section")

            # Validate sections
            for section in report.sections:
                self._validate_section(section)

            return True

        except Exception as e:
            self.logger.error(f"Report validation failed: {str(e)}")
            return False

    def _validate_section(self, section: ReportSection) -> None:
        """Validate section structure"""
        if not section.section_id:
            raise ValueError("Section ID is required")
        if not section.title:
            raise ValueError("Section title is required")
        if not section.content:
            raise ValueError("Section must contain content")

        # Validate visualizations if present
        for viz in section.visualizations:
            self._validate_visualization(viz)

    def _validate_visualization(self, visualization: ReportVisualization) -> None:
        """Validate visualization structure"""
        if not visualization.viz_id:
            raise ValueError("Visualization ID is required")
        if not visualization.title:
            raise ValueError("Visualization title is required")
        if not visualization.data:
            raise ValueError("Visualization must contain data")

    def get_supported_formats(self) -> List[ReportFormat]:
        """Get list of supported output formats"""
        return [ReportFormat.JSON]  # Base formatter only supports JSON

    def _create_metadata(self) -> Dict[str, Any]:
        """Create standard metadata for reports"""
        return {
            'generated_at': datetime.now().isoformat(),
            'formatter_version': '1.0',
            'generated_by': 'report_formatter'
        }

    def _format_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'error': str(error),
            'timestamp': datetime.now().isoformat(),
            'status': 'error'
        }

    def cleanup(self) -> None:
        """Cleanup formatter resources"""
        pass  # Base implementation does nothing