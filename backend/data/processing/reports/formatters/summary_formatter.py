# backend/data_pipeline/reporting/formatters/summary_formatter.py

import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import uuid

from .base_formatter import BaseFormatter
from ..types.report_types import (
    Report,
    PipelineSummaryReport,
    ReportSection,
    ReportVisualization,
    ReportFormat,
    ReportStage
)

logger = logging.getLogger(__name__)


class PipelineSummaryFormatter(BaseFormatter):
    """
    Formatter for pipeline summary reports.
    Combines and summarizes results from all pipeline stages.
    """

    def __init__(self, template_dir: Path = None, config: Dict[str, Any] = None):
        super().__init__(
            template_dir=template_dir or Path("templates/summary_templates"),
            config=config
        )
        self.supported_formats = [
            ReportFormat.HTML,
            ReportFormat.PDF,
            ReportFormat.JSON,
            ReportFormat.MARKDOWN
        ]

    async def format_report(self, report: PipelineSummaryReport) -> Dict[str, Any]:
        """Format complete pipeline summary report"""
        try:
            if not self.validate_report(report):
                raise ValueError("Invalid report structure")

            # Create executive summary
            executive_summary = self._create_executive_summary(report)

            # Format stage summaries
            stage_summaries = self._create_stage_summaries(report)

            # Format decisions and key points
            decisions_summary = self._format_decisions(report.key_decisions)

            # Combine all components
            formatted_report = {
                'report_id': str(report.report_id),
                'pipeline_id': report.pipeline_id,
                'title': report.title,
                'description': report.description,
                'executive_summary': executive_summary,
                'stage_summaries': stage_summaries,
                'decisions_summary': decisions_summary,
                'recommendations': self._format_recommendations(
                    report.final_recommendations
                ),
                'metadata': {
                    **report.metadata,
                    **self._create_metadata(),
                    'pipeline_duration': report.total_duration,
                    'completion_time': datetime.now().isoformat()
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
            logger.error(f"Failed to format summary report: {str(e)}")
            return self._format_error_response(e)

    def _create_executive_summary(
            self,
            report: PipelineSummaryReport
    ) -> Dict[str, Any]:
        """Create executive summary"""
        return {
            'pipeline_overview': {
                'total_duration': report.total_duration,
                'stages_completed': len(report.stages_completed),
                'key_decisions_made': len(report.key_decisions),
                'final_recommendations': len(report.final_recommendations)
            },
            'quality_highlights': self._extract_quality_highlights(
                report.quality_summary
            ),
            'insight_highlights': self._extract_insight_highlights(
                report.insight_summary
            ),
            'analytics_highlights': self._extract_analytics_highlights(
                report.analytics_summary
            ) if report.analytics_summary else None,
            'key_achievements': self._identify_key_achievements(report),
            'major_findings': self._summarize_major_findings(report)
        }

    def _create_stage_summaries(
            self,
            report: PipelineSummaryReport
    ) -> List[Dict[str, Any]]:
        """Create summary for each pipeline stage"""
        stage_summaries = []

        # Quality Analysis Stage
        if report.quality_summary:
            stage_summaries.append({
                'stage': ReportStage.DATA_QUALITY.value,
                'title': 'Data Quality Analysis',
                'content': self._format_quality_summary(report.quality_summary),
                'order': 1
            })

        # Insight Analysis Stage
        if report.insight_summary:
            stage_summaries.append({
                'stage': ReportStage.INSIGHT_ANALYSIS.value,
                'title': 'Insight Analysis',
                'content': self._format_insight_summary(report.insight_summary),
                'order': 2
            })

        # Advanced Analytics Stage (if performed)
        if report.analytics_summary:
            stage_summaries.append({
                'stage': ReportStage.ADVANCED_ANALYTICS.value,
                'title': 'Advanced Analytics',
                'content': self._format_analytics_summary(report.analytics_summary),
                'order': 3
            })

        return stage_summaries

    def _format_quality_summary(
            self,
            quality_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format quality analysis summary"""
        return {
            'type': 'quality_summary',
            'metrics': {
                'quality_score': quality_summary.get('quality_score', 0),
                'issues_found': quality_summary.get('issues_found', 0),
                'issues_resolved': quality_summary.get('issues_resolved', 0)
            },
            'key_findings': quality_summary.get('key_findings', []),
            'improvements_made': quality_summary.get('improvements', []),
            'impact': self._assess_quality_impact(quality_summary)
        }

    def _format_insight_summary(
            self,
            insight_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format insight analysis summary"""
        return {
            'type': 'insight_summary',
            'metrics': {
                'insights_found': insight_summary.get('total_insights', 0),
                'goal_alignment': insight_summary.get('goal_alignment_score', 0),
                'actionable_insights': len(
                    insight_summary.get('actionable_insights', [])
                )
            },
            'key_insights': insight_summary.get('key_insights', []),
            'business_impact': self._assess_insight_impact(insight_summary)
        }

    def _format_analytics_summary(
            self,
            analytics_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format advanced analytics summary"""
        return {
            'type': 'analytics_summary',
            'analysis_type': analytics_summary.get('analysis_type', ''),
            'performance': analytics_summary.get('performance_metrics', {}),
            'key_findings': analytics_summary.get('key_findings', []),
            'business_value': self._assess_analytics_value(analytics_summary)
        }

    def _format_decisions(
            self,
            decisions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format pipeline decisions summary"""
        return {
            'type': 'decisions_summary',
            'total_decisions': len(decisions),
            'by_stage': self._group_decisions_by_stage(decisions),
            'key_decision_points': self._identify_key_decisions(decisions),
            'impact_assessment': self._assess_decision_impact(decisions)
        }

    def _format_recommendations(
            self,
            recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format final recommendations"""
        # Group recommendations by category
        categorized_recs = {}
        for rec in recommendations:
            category = rec.get('category', 'general')
            if category not in categorized_recs:
                categorized_recs[category] = []
            categorized_recs[category].append(rec)

        return {
            'type': 'recommendations',
            'total_count': len(recommendations),
            'by_category': {
                category: {
                    'recommendations': recs,
                    'count': len(recs),
                    'priority_distribution': self._get_priority_distribution(recs)
                }
                for category, recs in categorized_recs.items()
            },
            'implementation_plan': self._create_implementation_plan(recommendations)
        }

    def _extract_quality_highlights(
            self,
            quality_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract key highlights from quality analysis"""
        highlights = []

        # Quality score highlight
        if 'quality_score' in quality_summary:
            highlights.append({
                'type': 'quality_score',
                'title': 'Overall Data Quality',
                'value': quality_summary['quality_score'],
                'interpretation': self._interpret_quality_score(
                    quality_summary['quality_score']
                )
            })

        # Issues highlight
        if 'issues_found' in quality_summary:
            highlights.append({
                'type': 'issues',
                'title': 'Quality Issues',
                'value': quality_summary['issues_found'],
                'resolved': quality_summary.get('issues_resolved', 0)
            })

        # Major improvements
        if 'improvements' in quality_summary:
            highlights.append({
                'type': 'improvements',
                'title': 'Major Improvements',
                'count': len(quality_summary['improvements']),
                'key_improvements': quality_summary['improvements'][:3]
            })

        return highlights

    def _extract_insight_highlights(
            self,
            insight_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract key highlights from insight analysis"""
        highlights = []

        # Goal alignment highlight
        if 'goal_alignment_score' in insight_summary:
            highlights.append({
                'type': 'goal_alignment',
                'title': 'Business Goal Alignment',
                'value': insight_summary['goal_alignment_score'],
                'interpretation': self._interpret_alignment_score(
                    insight_summary['goal_alignment_score']
                )
            })

        # Key insights highlight
        if 'key_insights' in insight_summary:
            highlights.append({
                'type': 'key_insights',
                'title': 'Key Business Insights',
                'count': len(insight_summary['key_insights']),
                'top_insights': insight_summary['key_insights'][:3]
            })

        return highlights

    def _extract_analytics_highlights(
            self,
            analytics_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract key highlights from advanced analytics"""
        if not analytics_summary:
            return []

        highlights = []

        # Model performance highlight
        if 'performance_metrics' in analytics_summary:
            highlights.append({
                'type': 'model_performance',
                'title': 'Model Performance',
                'metrics': analytics_summary['performance_metrics'],
                'interpretation': self._interpret_model_performance(
                    analytics_summary['performance_metrics']
                )
            })

        # Key findings highlight
        if 'key_findings' in analytics_summary:
            highlights.append({
                'type': 'analytics_findings',
                'title': 'Analytics Insights',
                'count': len(analytics_summary['key_findings']),
                'top_findings': analytics_summary['key_findings'][:3]
            })

        return highlights

    def _identify_key_achievements(
            self,
            report: PipelineSummaryReport
    ) -> List[Dict[str, Any]]:
        """Identify key achievements across pipeline stages"""
        achievements = []

        # Quality achievements
        if report.quality_summary:
            quality_achievements = self._extract_quality_achievements(
                report.quality_summary
            )
            achievements.extend(quality_achievements)

        # Insight achievements
        if report.insight_summary:
            insight_achievements = self._extract_insight_achievements(
                report.insight_summary
            )
            achievements.extend(insight_achievements)

        # Analytics achievements
        if report.analytics_summary:
            analytics_achievements = self._extract_analytics_achievements(
                report.analytics_summary
            )
            achievements.extend(analytics_achievements)

        # Sort achievements by impact
        achievements.sort(key=lambda x: x.get('impact_score', 0), reverse=True)

        return achievements[:5]  # Return top 5 achievements

    def _summarize_major_findings(
            self,
            report: PipelineSummaryReport
    ) -> List[Dict[str, Any]]:
        """Summarize major findings across all stages"""
        findings = []

        # Collect findings from each stage
        if report.quality_summary:
            findings.extend(self._extract_quality_findings(report.quality_summary))
        if report.insight_summary:
            findings.extend(self._extract_insight_findings(report.insight_summary))
        if report.analytics_summary:
            findings.extend(
                self._extract_analytics_findings(report.analytics_summary)
            )

        # Prioritize and categorize findings
        prioritized_findings = self._prioritize_findings(findings)

        return self._categorize_findings(prioritized_findings)

    def _get_priority_distribution(
            self,
            recommendations: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Get distribution of recommendation priorities"""
        distribution = {'high': 0, 'medium': 0, 'low': 0}
        for rec in recommendations:
            priority = rec.get('priority', 'medium').lower()
            if priority in distribution:
                distribution[priority] += 1
        return distribution

    def _create_implementation_plan(
            self,
            recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create implementation plan for recommendations"""
        # Sort recommendations by priority and effort
        sorted_recs = sorted(
            recommendations,
            key=lambda x: (
                self._priority_score(x.get('priority', 'medium')),
                -self._effort_score(x.get('effort', 'medium'))
            ),
            reverse=True
        )

        return {
            'phases': [
                {
                    'phase': 'immediate',
                    'timeframe': 'Within 1 month',
                    'recommendations': [
                        r for r in sorted_recs
                        if r.get('priority') == 'high' and
                           r.get('effort', 'medium') != 'high'
                    ]
                },
                {
                    'phase': 'short_term',
                    'timeframe': '1-3 months',
                    'recommendations': [
                        r for r in sorted_recs
                        if r.get('priority') in ['high', 'medium'] and
                           r.get('effort') == 'medium'
                    ]
                },
                {
                    'phase': 'long_term',
                    'timeframe': '3+ months',
                    'recommendations': [
                        r for r in sorted_recs
                        if r.get('priority') == 'low' or
                           r.get('effort') == 'high'
                    ]
                }
            ],
            'dependencies': self._identify_recommendation_dependencies(recommendations),
            'resource_requirements': self._estimate_resource_requirements(recommendations)
        }

    def _priority_score(self, priority: str) -> int:
        """Convert priority string to numeric score"""
        return {'high': 3, 'medium': 2, 'low': 1}.get(priority.lower(), 0)

    def _effort_score(self, effort: str) -> int:
        """Convert effort string to numeric score"""
        return {'high': 3, 'medium': 2, 'low': 1}.get(effort.lower(), 0)

    def _identify_recommendation_dependencies(
            self,
            recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify dependencies between recommendations"""
        dependencies = []
        for rec in recommendations:
            if 'dependencies' in rec:
                dependencies.append({
                    'recommendation_id': rec.get('id'),
                    'depends_on': rec['dependencies'],
                    'type': 'required'  # or 'optional'
                })
        return dependencies

    def _estimate_resource_requirements(
            self,
            recommendations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Estimate resource requirements for recommendations"""
        total_effort = sum(self._effort_score(r.get('effort', 'medium'))
                           for r in recommendations)

        return {
            'total_effort_score': total_effort,
            'estimated_timeline': self._calculate_timeline(total_effort),
            'resource_types': self._identify_required_resources(recommendations)
        }

    def _calculate_timeline(self, effort_score: int) -> str:
        """Calculate estimated timeline based on effort score"""
        if effort_score <= 5:
            return "1-2 months"
        elif effort_score <= 10:
            return "3-6 months"
        else:
            return "6+ months"

    def _identify_required_resources(
            self,
            recommendations: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Identify required resource types and counts"""
        resources = {}
        for rec in recommendations:
            for resource in rec.get('required_resources', []):
                resources[resource] = resources.get(resource, 0) + 1
        return resources

    def _group_decisions_by_stage(
            self,
            decisions: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group decisions by pipeline stage"""
        grouped = {}
        for decision in decisions:
            stage = decision.get('stage', 'unknown')
            if stage not in grouped:
                grouped[stage] = []
            grouped[stage].append({
                'decision_id': decision.get('id'),
                'type': decision.get('type'),
                'description': decision.get('description'),
                'impact': decision.get('impact'),
                'rationale': decision.get('rationale')
            })
        return grouped

    def _identify_key_decisions(
            self,
            decisions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify key decision points in the pipeline"""
        key_decisions = []
        for decision in decisions:
            if decision.get('impact_level', 'low') in ['high', 'critical']:
                key_decisions.append({
                    'decision_id': decision.get('id'),
                    'stage': decision.get('stage'),
                    'description': decision.get('description'),
                    'impact': decision.get('impact'),
                    'outcome': decision.get('outcome'),
                    'consequences': decision.get('consequences', [])
                })
        return sorted(key_decisions,
                      key=lambda x: self._impact_score(x.get('impact', {})),
                      reverse=True)

    def _assess_decision_impact(
            self,
            decisions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess overall impact of pipeline decisions"""
        impact_scores = []
        for decision in decisions:
            impact = decision.get('impact', {})
            impact_scores.append(self._impact_score(impact))

        return {
            'overall_impact_score': sum(impact_scores) / len(impact_scores) if impact_scores else 0,
            'major_impacts': self._summarize_major_impacts(decisions),
            'improvement_opportunities': self._identify_improvement_opportunities(decisions)
        }

    def _impact_score(self, impact: Dict[str, Any]) -> float:
        """Calculate numeric impact score"""
        scope_score = {'local': 1, 'stage': 2, 'pipeline': 3, 'global': 4}
        severity_score = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}

        scope = impact.get('scope', 'local')
        severity = impact.get('severity', 'low')

        return (scope_score.get(scope, 1) * severity_score.get(severity, 1)) / 16.0

    def _summarize_major_impacts(
            self,
            decisions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Summarize major impacts of decisions"""
        major_impacts = []
        for decision in decisions:
            impact = decision.get('impact', {})
            if self._impact_score(impact) > 0.5:
                major_impacts.append({
                    'decision_id': decision.get('id'),
                    'impact_description': impact.get('description'),
                    'affected_areas': impact.get('affected_areas', []),
                    'metrics_affected': impact.get('metrics', {})
                })
        return major_impacts

    def _identify_improvement_opportunities(
            self,
            decisions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify opportunities for improvement in decision-making"""
        opportunities = []
        for decision in decisions:
            if 'alternatives' in decision and decision.get('confidence', 1.0) < 0.8:
                opportunities.append({
                    'decision_id': decision.get('id'),
                    'type': 'alternative_analysis',
                    'suggestion': 'Consider alternative options more thoroughly',
                    'potential_improvements': decision.get('alternatives', [])
                })
            if 'constraints' in decision:
                opportunities.append({
                    'decision_id': decision.get('id'),
                    'type': 'constraint_relaxation',
                    'suggestion': 'Review decision constraints',
                    'constraints': decision.get('constraints', [])
                })
        return opportunities

    async def format_visualization(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format pipeline summary visualization"""
        try:
            if visualization.viz_type == 'pipeline_flow':
                return self._format_pipeline_flow_viz(visualization)
            elif visualization.viz_type == 'decision_tree':
                return self._format_decision_tree_viz(visualization)
            elif visualization.viz_type == 'impact_analysis':
                return self._format_impact_analysis_viz(visualization)
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

    def _format_pipeline_flow_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format pipeline flow visualization"""
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'pipeline_flow',
            'title': visualization.title,
            'data': {
                'stages': visualization.data.get('stages', []),
                'connections': visualization.data.get('connections', []),
                'metrics': visualization.data.get('metrics', {})
            },
            'config': {
                **visualization.config,
                'show_metrics': True,
                'show_durations': True
            }
        }

    def _format_decision_tree_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format decision tree visualization"""
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'decision_tree',
            'title': visualization.title,
            'data': {
                'decisions': visualization.data.get('decisions', []),
                'paths': visualization.data.get('paths', []),
                'outcomes': visualization.data.get('outcomes', {})
            },
            'config': visualization.config
        }

    def _format_impact_analysis_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format impact analysis visualization"""
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'impact_analysis',
            'title': visualization.title,
            'data': {
                'impacts': visualization.data.get('impacts', {}),
                'dependencies': visualization.data.get('dependencies', []),
                'metrics': visualization.data.get('metrics', {})
            },
            'config': visualization.config
        }