# backend/data_pipeline/reporting/formatters/quality_formatter.py

import logging
from typing import Dict, Any, List
from pathlib import Path
import json
from datetime import datetime

from .base_formatter import BaseFormatter
from ..types.reports_types import (
    Report,
    QualityReport,
    ReportSection,
    ReportVisualization,
    ReportFormat
)

logger = logging.getLogger(__name__)


class QualityReportFormatter(BaseFormatter):
    """
    Formatter for data quality insight reports.
    Handles formatting of quality metrics, issues, and recommendations.
    """

    def __init__(self, template_dir: Path = None, config: Dict[str, Any] = None):
        super().__init__(
            template_dir=template_dir or Path("templates/quality_templates"),
            config=config
        )
        self.supported_formats = [
            ReportFormat.HTML,
            ReportFormat.PDF,
            ReportFormat.JSON,
            ReportFormat.MARKDOWN
        ]

    async def format_report(self, report: QualityReport) -> Dict[str, Any]:
        """Format complete quality report"""
        try:
            if not self.validate_report(report):
                raise ValueError("Invalid report structure")

            # Create report overview
            overview = self._create_overview(report)

            # Format each section
            formatted_sections = []
            for section in report.sections:
                formatted_section = await self.format_section(section)
                formatted_sections.append(formatted_section)

            # Add quality-specific sections
            quality_sections = self._create_quality_sections(report)
            formatted_sections.extend(quality_sections)

            # Combine all components
            formatted_report = {
                'report_id': str(report.report_id),
                'pipeline_id': report.pipeline_id,
                'title': report.title,
                'description': report.description,
                'overview': overview,
                'sections': formatted_sections,
                'metadata': {
                    **report.metadata,
                    **self._create_metadata()
                }
            }

            # Apply format-specific formatting
            if report.format == ReportFormat.HTML:
                return await self._format_as_html(formatted_report)
            elif report.format == ReportFormat.PDF:
                return await self._format_as_pdf(formatted_report)
            elif report.format == ReportFormat.MARKDOWN:
                return await self._format_as_markdown(formatted_report)
            else:
                return formatted_report  # Default JSON format

        except Exception as e:
            logger.error(f"Failed to format quality report: {str(e)}")
            return self._format_error_response(e)

    async def format_section(self, section: ReportSection) -> Dict[str, Any]:
        """Format quality report section"""
        try:
            # Format section content
            formatted_content = []
            for content in section.content:
                if content.content_type == 'metrics':
                    formatted_content.append(
                        self._format_metrics(content.content)
                    )
                elif content.content_type == 'issues':
                    formatted_content.append(
                        self._format_issues(content.content)
                    )
                elif content.content_type == 'recommendations':
                    formatted_content.append(
                        self._format_recommendations(content.content)
                    )
                else:
                    formatted_content.append(content.content)

            # Format visualizations
            formatted_viz = []
            for viz in section.visualizations:
                formatted_viz.append(
                    await self.format_visualization(viz)
                )

            return {
                'section_id': str(section.section_id),
                'title': section.title,
                'description': section.description,
                'content': formatted_content,
                'visualizations': formatted_viz,
                'metadata': section.metadata,
                'order': section.order
            }

        except Exception as e:
            logger.error(f"Failed to format section: {str(e)}")
            return self._format_error_response(e)

    async def format_visualization(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format quality visualization"""
        try:
            # Apply specific formatting based on visualization type
            if visualization.viz_type == 'quality_score':
                return self._format_quality_score_viz(visualization)
            elif visualization.viz_type == 'issue_distribution':
                return self._format_issue_distribution_viz(visualization)
            elif visualization.viz_type == 'metric_trend':
                return self._format_metric_trend_viz(visualization)
            else:
                return {
                    'viz_id': str(visualization.viz_id),
                    'title': visualization.title,
                    'type': visualization.viz_type,
                    'data': visualization.data,
                    'config': visualization.config,
                    'metadata': visualization.metadata
                }

        except Exception as e:
            logger.error(f"Failed to format visualization: {str(e)}")
            return self._format_error_response(e)

    def _format_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Format quality metrics content"""
        formatted_metrics = {
            'type': 'metrics',
            'categories': []
        }

        for category, metrics_data in metrics.items():
            category_metrics = {
                'name': category,
                'metrics': []
            }

            for metric_name, metric_value in metrics_data.items():
                category_metrics['metrics'].append({
                    'name': metric_name,
                    'value': metric_value,
                    'format': self._detect_metric_format(metric_value)
                })

            formatted_metrics['categories'].append(category_metrics)

        return formatted_metrics

    def _format_issues(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format quality issues content"""
        severity_order = ['critical', 'high', 'medium', 'low']

        # Group issues by severity
        grouped_issues = {}
        for severity in severity_order:
            grouped_issues[severity] = [
                issue for issue in issues
                if issue.get('severity', 'low') == severity
            ]

        return {
            'type': 'issues',
            'total_count': len(issues),
            'by_severity': grouped_issues,
            'summary': {
                severity: len(issues)
                for severity, issues in grouped_issues.items()
            }
        }

    def _format_recommendations(
            self,
            recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format quality recommendations content"""
        # Group recommendations by priority
        priority_order = ['critical', 'high', 'medium', 'low']
        grouped_recommendations = {}

        for priority in priority_order:
            grouped_recommendations[priority] = []
            for rec in recommendations:
                if rec.get('priority') == priority:
                    formatted_rec = {
                        'id': rec.get('id'),
                        'title': rec.get('title'),
                        'description': rec.get('description'),
                        'action_items': rec.get('action_items', []),
                        'impact': rec.get('impact', 'unknown'),
                        'effort': rec.get('effort', 'unknown'),
                        'priority': priority
                    }
                    grouped_recommendations[priority].append(formatted_rec)

        return {
            'type': 'recommendations',
            'total_count': len(recommendations),
            'by_priority': grouped_recommendations,
            'summary': {
                priority: len(recs)
                for priority, recs in grouped_recommendations.items()
            }
        }

    def _format_quality_score_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format quality score visualization"""
        score_data = visualization.data
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'quality_score',
            'title': visualization.title,
            'data': {
                'score': score_data.get('score', 0),
                'previous_score': score_data.get('previous_score'),
                'change': score_data.get('change'),
                'breakdown': score_data.get('breakdown', {}),
                'threshold': visualization.config.get('threshold', 0.8)
            },
            'config': visualization.config,
            'metadata': visualization.metadata
        }

    def _format_issue_distribution_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format issue distribution visualization"""
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'issue_distribution',
            'title': visualization.title,
            'data': {
                'distribution': visualization.data.get('distribution', {}),
                'total_issues': sum(
                    visualization.data.get('distribution', {}).values()
                ),
                'categories': list(
                    visualization.data.get('distribution', {}).keys()
                )
            },
            'config': visualization.config,
            'metadata': visualization.metadata
        }

    def _format_metric_trend_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format metric trend visualization"""
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'metric_trend',
            'title': visualization.title,
            'data': {
                'trend_data': visualization.data.get('trend_data', []),
                'metric_name': visualization.data.get('metric_name', ''),
                'time_range': visualization.data.get('time_range', {}),
                'benchmark': visualization.data.get('benchmark')
            },
            'config': visualization.config,
            'metadata': visualization.metadata
        }

    def _create_overview(self, report: QualityReport) -> Dict[str, Any]:
        """Create quality report overview"""
        return {
            'quality_score': report.quality_score,
            'issues_summary': {
                'total_issues': report.issues_found,
                'critical': len([r for r in report.recommendations if r.get('priority') == 'critical']),
                'high': len([r for r in report.recommendations if r.get('priority') == 'high']),
                'medium': len([r for r in report.recommendations if r.get('priority') == 'medium']),
                'low': len([r for r in report.recommendations if r.get('priority') == 'low'])
            },
            'recommendations_count': len(report.recommendations),
            'profile_summary': self._summarize_profile_data(report.profile_data)
        }

    def _summarize_profile_data(
            self,
            profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create summary of profile data"""
        return {
            'total_columns': profile_data.get('total_columns', 0),
            'total_rows': profile_data.get('total_rows', 0),
            'missing_cells': profile_data.get('missing_cells', 0),
            'duplicate_rows': profile_data.get('duplicate_rows', 0),
            'data_types': profile_data.get('data_types', {}),
            'generated_at': profile_data.get('generated_at', datetime.now().isoformat())
        }

    def _detect_metric_format(self, value: Any) -> str:
        """Detect appropriate format for metric value"""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'percentage' if 0 <= value <= 1 else 'float'
        elif isinstance(value, str):
            return 'string'
        else:
            return 'unknown'

    async def _format_as_html(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format report as HTML"""
        try:
            template = await self.load_template('quality_report.html')
            # Template rendering logic would go here
            return {
                'format': 'html',
                'content': template,  # Replace with actual rendered HTML
                'metadata': report_data['metadata']
            }
        except Exception as e:
            logger.error(f"HTML formatting failed: {str(e)}")
            return report_data

    async def _format_as_pdf(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format report as PDF"""
        try:
            # PDF generation logic would go here
            return {
                'format': 'pdf',
                'content': b'',  # Replace with actual PDF content
                'metadata': report_data['metadata']
            }
        except Exception as e:
            logger.error(f"PDF formatting failed: {str(e)}")
            return report_data

    async def _format_as_markdown(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format report as Markdown"""
        try:
            template = await self.load_template('quality_report.md')
            # Markdown rendering logic would go here
            return {
                'format': 'markdown',
                'content': template,  # Replace with actual rendered markdown
                'metadata': report_data['metadata']
            }
        except Exception as e:
            logger.error(f"Markdown formatting failed: {str(e)}")
            return report_data