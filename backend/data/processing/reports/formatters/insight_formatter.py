# backend/data_pipeline/reporting/formatters/insight_formatter.py

import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from .base_formatter import BaseFormatter
from ..types.report_types import (
    Report,
    InsightReport,
    ReportSection,
    ReportVisualization,
    ReportFormat
)

logger = logging.getLogger(__name__)


class InsightReportFormatter(BaseFormatter):
    """
    Formatter for insight analysis reports.
    Handles formatting of business insights, goal alignments, and analytics recommendations.
    """

    def __init__(self, template_dir: Path = None, config: Dict[str, Any] = None):
        super().__init__(
            template_dir=template_dir or Path("templates/insight_templates"),
            config=config
        )
        self.supported_formats = [
            ReportFormat.HTML,
            ReportFormat.PDF,
            ReportFormat.JSON,
            ReportFormat.MARKDOWN
        ]

    async def format_report(self, report: InsightReport) -> Dict[str, Any]:
        """Format complete insight report"""
        try:
            if not self.validate_report(report):
                raise ValueError("Invalid report structure")

            # Create report overview
            overview = self._create_overview(report)

            # Format sections
            formatted_sections = []
            for section in report.sections:
                formatted_section = await self.format_section(section)
                formatted_sections.append(formatted_section)

            # Add insight-specific sections
            insight_sections = self._create_insight_sections(report)
            formatted_sections.extend(insight_sections)

            # Combine components
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
                return formatted_report

        except Exception as e:
            logger.error(f"Failed to format insight report: {str(e)}")
            return self._format_error_response(e)

    def _create_overview(self, report: InsightReport) -> Dict[str, Any]:
        """Create insight report overview"""
        return {
            'total_insights': report.insights_found,
            'goal_alignment': {
                'score': report.goal_alignment_score,
                'status': self._get_alignment_status(report.goal_alignment_score)
            },
            'business_goals': {
                'total': len(report.business_goals),
                'addressed': self._count_addressed_goals(report)
            },
            'analytics_opportunities': len(report.analytics_recommendations),
            'key_metrics': self._extract_key_metrics(report)
        }

    def _create_insight_sections(self, report: InsightReport) -> List[Dict[str, Any]]:
        """Create insight-specific sections"""
        sections = []

        # Business Goals Analysis
        if report.business_goals:
            sections.append({
                'title': 'Business Goals Analysis',
                'content': self._format_business_goals(
                    report.business_goals,
                    report.goal_alignment_score
                ),
                'order': 1
            })

        # Key Insights
        sections.append({
            'title': 'Key Insights',
            'content': self._format_key_insights(report),
            'order': 2
        })

        # Analytics Recommendations
        if report.analytics_recommendations:
            sections.append({
                'title': 'Advanced Analytics Opportunities',
                'content': self._format_analytics_recommendations(
                    report.analytics_recommendations
                ),
                'order': 3
            })

        return sections

    def _format_business_goals(
            self,
            goals: List[str],
            alignment_score: float
    ) -> Dict[str, Any]:
        """Format business goals analysis"""
        return {
            'type': 'business_goals',
            'goals': [
                {
                    'goal': goal,
                    'status': 'aligned' if alignment_score > 0.7 else 'partial'
                }
                for goal in goals
            ],
            'overall_alignment': alignment_score,
            'recommendations': self._generate_goal_recommendations(
                goals,
                alignment_score
            )
        }

    def _format_key_insights(self, report: InsightReport) -> Dict[str, Any]:
        """Format key insights"""
        insights = []
        for insight in report.insights_found:
            formatted_insight = {
                'id': str(uuid.uuid4()),  # Generate unique ID for each insight
                'title': insight.get('title', ''),
                'description': insight.get('description', ''),
                'impact': insight.get('impact', 'medium'),
                'confidence': insight.get('confidence', 0.0),
                'metrics': insight.get('supporting_metrics', {}),
                'recommendations': insight.get('recommendations', []),
                'related_goals': insight.get('related_goals', [])
            }
            insights.append(formatted_insight)

        # Group insights by impact
        grouped_insights = {
            'high_impact': [i for i in insights if i['impact'] == 'high'],
            'medium_impact': [i for i in insights if i['impact'] == 'medium'],
            'low_impact': [i for i in insights if i['impact'] == 'low']
        }

        return {
            'type': 'insights',
            'total_count': len(insights),
            'by_impact': grouped_insights,
            'summary': {
                impact: len(insights)
                for impact, insights in grouped_insights.items()
            }
        }

    def _format_analytics_recommendations(
            self,
            recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format analytics recommendations"""
        formatted_recs = []
        for rec in recommendations:
            formatted_rec = {
                'id': str(uuid.uuid4()),
                'analysis_type': rec.get('type', ''),
                'description': rec.get('description', ''),
                'expected_impact': rec.get('expected_impact', {}),
                'required_data': rec.get('required_data', []),
                'complexity': rec.get('complexity', 'medium'),
                'estimated_effort': rec.get('estimated_effort', ''),
                'potential_value': rec.get('potential_value', 'medium')
            }
            formatted_recs.append(formatted_rec)

        # Group by complexity
        grouped_recs = {
            'high_value': [r for r in formatted_recs if r['potential_value'] == 'high'],
            'medium_value': [r for r in formatted_recs if r['potential_value'] == 'medium'],
            'low_value': [r for r in formatted_recs if r['potential_value'] == 'low']
        }

        return {
            'type': 'analytics_recommendations',
            'recommendations': grouped_recs,
            'summary': {
                'total_opportunities': len(formatted_recs),
                'by_value': {
                    value: len(recs)
                    for value, recs in grouped_recs.items()
                }
            }
        }

    def _get_alignment_status(self, score: float) -> str:
        """Get alignment status based on score"""
        if score >= 0.8:
            return 'strong_alignment'
        elif score >= 0.6:
            return 'moderate_alignment'
        elif score >= 0.4:
            return 'partial_alignment'
        else:
            return 'weak_alignment'

    def _count_addressed_goals(self, report: InsightReport) -> int:
        """Count number of business goals addressed by insights"""
        addressed_goals = set()
        for insight in report.insights_found:
            addressed_goals.update(
                insight.get('related_goals', [])
            )
        return len(addressed_goals)

    def _extract_key_metrics(self, report: InsightReport) -> Dict[str, Any]:
        """Extract key metrics from insights"""
        metrics = {}
        for insight in report.insights_found:
            metrics.update(insight.get('supporting_metrics', {}))
        return metrics

    def _generate_goal_recommendations(
            self,
            goals: List[str],
            alignment_score: float
    ) -> List[Dict[str, Any]]:
        """Generate recommendations for improving goal alignment"""
        recommendations = []
        if alignment_score < 0.8:
            recommendations.append({
                'type': 'alignment',
                'description': 'Consider additional data collection to better address business goals',
                'priority': 'high' if alignment_score < 0.6 else 'medium'
            })
        return recommendations

    async def format_visualization(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format insight visualization"""
        try:
            if visualization.viz_type == 'goal_alignment':
                return self._format_goal_alignment_viz(visualization)
            elif visualization.viz_type == 'insight_impact':
                return self._format_insight_impact_viz(visualization)
            elif visualization.viz_type == 'metric_correlation':
                return self._format_metric_correlation_viz(visualization)
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

    def _format_goal_alignment_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format goal alignment visualization"""
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'goal_alignment',
            'title': visualization.title,
            'data': visualization.data,
            'config': {
                **visualization.config,
                'threshold_lines': {
                    'strong': 0.8,
                    'moderate': 0.6,
                    'weak': 0.4
                }
            }
        }

    def _format_insight_impact_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format insight impact visualization"""
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'insight_impact',
            'title': visualization.title,
            'data': {
                'impact_distribution': visualization.data.get('distribution', {}),
                'confidence_levels': visualization.data.get('confidence_levels', {})
            },
            'config': visualization.config
        }

    def _format_metric_correlation_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format metric correlation visualization"""
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'metric_correlation',
            'title': visualization.title,
            'data': {
                'correlation_matrix': visualization.data.get('matrix', {}),
                'significant_correlations': visualization.data.get('significant', [])
            },
            'config': visualization.config
        }