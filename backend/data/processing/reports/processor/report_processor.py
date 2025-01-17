# backend/data_pipeline/reporting/processor/report_processor.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from pathlib import Path

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus
)

from data.processing.reports.types.reports_types import (
    Report,
    QualityReport,
    InsightReport,
    AnalyticsReport,
    PipelineSummaryReport,
    ReportStage,
    ReportStatus,
    ReportFormat
)

from ..formatters.quality_formatter import QualityReportFormatter

logger = logging.getLogger(__name__)


class ReportProcessor:
    """
    Orchestrates report generation process.
    Coordinates between different formatters and data sources.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            template_dir: Optional[Path] = None,
            config: Optional[Dict[str, Any]] = None
    ):
        self.message_broker = message_broker
        self.template_dir = template_dir or Path("templates")
        self.config = config or {}

        # Initialize formatters
        self.formatters = {
            ReportStage.DATA_QUALITY: QualityReportFormatter(
                template_dir=self.template_dir / "quality_templates",
                config=self.config.get('quality_formatter', {})
            )
            # More formatters will be added as we create them
        }

        # Track active reports
        self.active_reports: Dict[str, Report] = {}

    async def process_report_request(
            self,
            pipeline_id: str,
            stage: ReportStage,
            data: Dict[str, Any],
            format: ReportFormat = ReportFormat.HTML
    ) -> Dict[str, Any]:
        """Process report generation request"""
        try:
            # Create report instance based on stage
            report = await self._create_report(
                pipeline_id,
                stage,
                data,
                format
            )

            # Store active report
            self.active_reports[pipeline_id] = report

            # Send start notification
            await self._notify_start(pipeline_id, stage)

            # Get appropriate formatter
            formatter = self.formatters.get(stage)
            if not formatter:
                raise ValueError(f"No formatter found for stage: {stage}")

            # Format report
            formatted_report = await formatter.format_report(report)

            # Update report status
            report.status = ReportStatus.READY_FOR_REVIEW
            report.updated_at = datetime.now()

            # Send completion notification
            await self._notify_completion(pipeline_id, formatted_report)

            return formatted_report

        except Exception as e:
            logger.error(f"Failed to process report request: {str(e)}")
            await self._notify_error(pipeline_id, str(e))
            raise

    async def _create_report(
            self,
            pipeline_id: str,
            stage: ReportStage,
            data: Dict[str, Any],
            format: ReportFormat
    ) -> Report:
        """Create appropriate report instance based on stage"""
        base_args = {
            'report_id': uuid.uuid4(),
            'pipeline_id': pipeline_id,
            'stage': stage,
            'format': format,
            'status': ReportStatus.PENDING,
            'metadata': self._create_metadata()
        }

        if stage == ReportStage.DATA_QUALITY:
            return QualityReport(
                **base_args,
                title="Data Quality Analysis Report",
                description="Comprehensive analysis of data quality metrics and issues",
                sections=[],  # Will be populated during formatting
                quality_score=data.get('quality_score', 0.0),
                issues_found=len(data.get('issues', [])),
                recommendations=data.get('recommendations', []),
                profile_data=data.get('profile_data', {})
            )
        elif stage == ReportStage.INSIGHT_ANALYSIS:
            return InsightReport(
                **base_args,
                title="Insight Analysis Report",
                description="Analysis of business insights and recommendations",
                sections=[],
                business_goals=data.get('business_goals', []),
                insights_found=len(data.get('insights', [])),
                goal_alignment_score=data.get('goal_alignment_score', 0.0),
                analytics_recommendations=data.get('analytics_recommendations', [])
            )
        elif stage == ReportStage.ADVANCED_ANALYTICS:
            return AnalyticsReport(
                **base_args,
                title="Advanced Analytics Report",
                description="Results of advanced analytics processing",
                sections=[],
                analysis_type=data.get('analysis_type', ''),
                model_performance=data.get('model_performance', {}),
                predictions=data.get('predictions', {}),
                feature_importance=data.get('feature_importance', {})
            )
        elif stage == ReportStage.PIPELINE_SUMMARY:
            return PipelineSummaryReport(
                **base_args,
                title="Pipeline Summary Report",
                description="Overall summary of pipeline processing and results",
                sections=[],
                total_duration=data.get('total_duration', 0.0),
                stages_completed=data.get('stages_completed', []),
                key_decisions=data.get('key_decisions', []),
                final_recommendations=data.get('final_recommendations', []),
                quality_summary=data.get('quality_summary', {}),
                insight_summary=data.get('insight_summary', {}),
                analytics_summary=data.get('analytics_summary')
            )
        else:
            raise ValueError(f"Unsupported report stage: {stage}")

    async def _notify_start(self, pipeline_id: str, stage: ReportStage) -> None:
        """Notify about report generation start"""
        message = ProcessingMessage(
            message_type=MessageType.REPORT_START,
            content={
                'pipeline_id': pipeline_id,
                'stage': stage.value,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    async def _notify_completion(
            self,
            pipeline_id: str,
            report_data: Dict[str, Any]
    ) -> None:
        """Notify about report generation completion"""
        message = ProcessingMessage(
            message_type=MessageType.REPORT_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'report_data': report_data,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    async def _notify_error(self, pipeline_id: str, error: str) -> None:
        """Notify about report generation error"""
        message = ProcessingMessage(
            message_type=MessageType.REPORT_ERROR,
            content={
                'pipeline_id': pipeline_id,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    def _create_metadata(self) -> Dict[str, Any]:
        """Create standard metadata for reports"""
        return {
            'generated_at': datetime.now().isoformat(),
            'processor_version': '1.0',
            'config_version': self.config.get('version', '1.0')
        }

    def get_report_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get status of report generation"""
        report = self.active_reports.get(pipeline_id)
        if not report:
            return None

        return {
            'pipeline_id': pipeline_id,
            'stage': report.stage.value,
            'status': report.status.value,
            'format': report.format.value,
            'created_at': report.created_at.isoformat(),
            'updated_at': report.updated_at.isoformat()
        }

    async def process_quality_report(
            self,
            pipeline_id: str,
            quality_data: Dict[str, Any]
    ) -> QualityReport:
        """Process quality analysis data into report"""
        try:
            # Extract quality metrics
            metrics = self._extract_quality_metrics(quality_data)

            # Process issues and recommendations
            issues = self._process_quality_issues(quality_data.get('issues', []))
            recommendations = self._generate_quality_recommendations(
                quality_data.get('issues', []),
                quality_data.get('metrics', {})
            )

            # Create report structure
            report = QualityReport(
                report_id=uuid.uuid4(),
                pipeline_id=pipeline_id,
                stage=ReportStage.DATA_QUALITY,
                title="Data Quality Analysis Report",
                description="Comprehensive analysis of data quality metrics and issues",
                sections=self._create_quality_sections(metrics, issues, recommendations),
                metadata=self._create_report_metadata(quality_data),
                status=ReportStatus.GENERATING,
                quality_score=self._calculate_quality_score(metrics),
                issues_found=len(issues),
                recommendations=recommendations,
                profile_data=quality_data.get('profile_data', {})
            )

            return report

        except Exception as e:
            logger.error(f"Error processing quality report: {str(e)}")
            raise

    async def process_insight_report(
            self,
            pipeline_id: str,
            insight_data: Dict[str, Any]
    ) -> InsightReport:
        """Process insight analysis data into report"""
        try:
            # Process insights
            insights = self._process_insights(insight_data.get('insights', []))

            # Extract business goals and alignment
            goals = insight_data.get('business_goals', [])
            goal_alignment = self._calculate_goal_alignment(
                insights,
                goals,
                insight_data.get('metrics', {})
            )

            # Process analytics recommendations
            recommendations = self._process_analytics_recommendations(
                insight_data.get('opportunities', [])
            )

            # Create report structure
            report = InsightReport(
                report_id=uuid.uuid4(),
                pipeline_id=pipeline_id,
                stage=ReportStage.INSIGHT_ANALYSIS,
                title="Business Insight Analysis Report",
                description="Analysis of business insights and opportunities",
                sections=self._create_insight_sections(insights, goals, recommendations),
                metadata=self._create_report_metadata(insight_data),
                status=ReportStatus.GENERATING,
                business_goals=goals,
                insights_found=len(insights),
                goal_alignment_score=goal_alignment,
                analytics_recommendations=recommendations
            )

            return report

        except Exception as e:
            logger.error(f"Error processing insight report: {str(e)}")
            raise

    async def process_analytics_report(
            self,
            pipeline_id: str,
            analytics_data: Dict[str, Any]
    ) -> AnalyticsReport:
        """Process analytics results into report"""
        try:
            # Process model results
            model_performance = self._process_model_performance(
                analytics_data.get('performance', {})
            )

            # Process predictions and features
            predictions = self._process_predictions(analytics_data.get('predictions', {}))
            feature_importance = self._process_feature_importance(
                analytics_data.get('features', {})
            )

            # Create report structure
            report = AnalyticsReport(
                report_id=uuid.uuid4(),
                pipeline_id=pipeline_id,
                stage=ReportStage.ADVANCED_ANALYTICS,
                title="Advanced Analytics Report",
                description="Results of advanced analytics processing",
                sections=self._create_analytics_sections(
                    model_performance,
                    predictions,
                    feature_importance
                ),
                metadata=self._create_report_metadata(analytics_data),
                status=ReportStatus.GENERATING,
                analysis_type=analytics_data.get('type', 'unknown'),
                model_performance=model_performance,
                predictions=predictions,
                feature_importance=feature_importance
            )

            return report

        except Exception as e:
            logger.error(f"Error processing analytics report: {str(e)}")
            raise

    async def process_summary_report(
            self,
            pipeline_id: str,
            pipeline_data: Dict[str, Any]
    ) -> PipelineSummaryReport:
        """Process pipeline summary into report"""
        try:
            # Extract stage summaries
            quality_summary = pipeline_data.get('quality_summary', {})
            insight_summary = pipeline_data.get('insight_summary', {})
            analytics_summary = pipeline_data.get('analytics_summary', {})

            # Process decisions and recommendations
            decisions = self._process_pipeline_decisions(
                pipeline_data.get('decisions', [])
            )
            recommendations = self._generate_pipeline_recommendations(
                pipeline_data
            )

            # Calculate pipeline metrics
            total_duration = self._calculate_pipeline_duration(pipeline_data)
            stages_completed = pipeline_data.get('completed_stages', [])

            # Create report structure
            report = PipelineSummaryReport(
                report_id=uuid.uuid4(),
                pipeline_id=pipeline_id,
                stage=ReportStage.PIPELINE_SUMMARY,
                title="Pipeline Summary Report",
                description="Comprehensive summary of pipeline processing and results",
                sections=self._create_summary_sections(
                    pipeline_data,
                    decisions,
                    recommendations
                ),
                metadata=self._create_report_metadata(pipeline_data),
                status=ReportStatus.GENERATING,
                total_duration=total_duration,
                stages_completed=stages_completed,
                key_decisions=decisions,
                final_recommendations=recommendations,
                quality_summary=quality_summary,
                insight_summary=insight_summary,
                analytics_summary=analytics_summary
            )

            return report

        except Exception as e:
            logger.error(f"Error processing summary report: {str(e)}")
            raise

    def _extract_quality_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and process quality metrics"""
        metrics = data.get('metrics', {})
        processed_metrics = {}

        # Process each metric category
        for category, values in metrics.items():
            processed_metrics[category] = {
                'values': values,
                'summary': self._calculate_metric_summary(values),
                'trends': self._calculate_metric_trends(values)
            }

        return processed_metrics

    def _process_quality_issues(
            self,
            issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process quality issues"""
        processed_issues = []

        for issue in issues:
            processed_issue = {
                'id': str(uuid.uuid4()),
                'type': issue.get('type', 'unknown'),
                'severity': issue.get('severity', 'low'),
                'description': issue.get('description', ''),
                'affected_columns': issue.get('columns', []),
                'impact': self._calculate_issue_impact(issue),
                'suggested_actions': issue.get('suggestions', [])
            }
            processed_issues.append(processed_issue)

        return sorted(
            processed_issues,
            key=lambda x: self._severity_score(x['severity']),
            reverse=True
        )

    def _generate_quality_recommendations(
            self,
            issues: List[Dict[str, Any]],
            metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate quality improvement recommendations"""
        recommendations = []

        # Process critical issues first
        critical_issues = [i for i in issues if i.get('severity') == 'critical']
        for issue in critical_issues:
            recommendations.append({
                'id': str(uuid.uuid4()),
                'priority': 'high',
                'type': 'issue_resolution',
                'title': f"Resolve {issue['type']} Issue",
                'description': issue.get('description', ''),
                'action_items': issue.get('suggestions', []),
                'impact': issue.get('impact', {})
            })

        # Add metric-based recommendations
        for metric, value in metrics.items():
            if self._is_metric_below_threshold(metric, value):
                recommendations.append({
                    'id': str(uuid.uuid4()),
                    'priority': 'medium',
                    'type': 'metric_improvement',
                    'title': f"Improve {metric}",
                    'description': f"Current {metric} is below acceptable threshold",
                    'action_items': self._generate_metric_actions(metric, value)
                })

        return recommendations

    def _process_insights(
            self,
            insights: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process business insights"""
        processed_insights = []

        for insight in insights:
            processed_insight = {
                'id': str(uuid.uuid4()),
                'title': insight.get('title', ''),
                'description': insight.get('description', ''),
                'category': insight.get('category', 'general'),
                'confidence': insight.get('confidence', 0.0),
                'impact': self._calculate_insight_impact(insight),
                'supporting_data': insight.get('supporting_data', {}),
                'related_goals': insight.get('related_goals', []),
                'recommendations': insight.get('recommendations', [])
            }
            processed_insights.append(processed_insight)

        return sorted(
            processed_insights,
            key=lambda x: (x['confidence'], x['impact']['score']),
            reverse=True
        )

    def _calculate_goal_alignment(
            self,
            insights: List[Dict[str, Any]],
            goals: List[str],
            metrics: Dict[str, Any]
    ) -> float:
        """Calculate alignment between insights and business goals"""
        if not goals:
            return 0.0

        goal_scores = {}
        for goal in goals:
            # Calculate coverage
            relevant_insights = [
                i for i in insights
                if goal in i.get('related_goals', [])
            ]
            coverage = len(relevant_insights) / len(insights) if insights else 0

            # Calculate metric alignment
            metric_alignment = self._calculate_metric_goal_alignment(
                metrics,
                goal
            )

            # Combine scores
            goal_scores[goal] = (coverage * 0.6) + (metric_alignment * 0.4)

        return sum(goal_scores.values()) / len(goal_scores)

    def _create_report_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create standard report metadata"""
        return {
            'generated_at': datetime.now().isoformat(),
            'generator_version': '1.0',
            'source_data': {
                'timestamp': data.get('timestamp'),
                'version': data.get('version'),
                'source': data.get('source')
            }
        }

    def _severity_score(self, severity: str) -> int:
        """Convert severity to numeric score"""
        return {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }.get(severity.lower(), 0)

    def _is_metric_below_threshold(
            self,
            metric: str,
            value: float
    ) -> bool:
        """Check if metric is below acceptable threshold"""
        thresholds = {
            'completeness': 0.95,
            'accuracy': 0.90,
            'consistency': 0.85,
            'timeliness': 0.80
        }
        return value < thresholds.get(metric, 0.90)

    async def _notify_progress(
            self,
            pipeline_id: str,
            stage: str,
            progress: float
    ) -> None:
        """Notify progress update"""
        message = ProcessingMessage(
            message_type=MessageType.REPORT_STATUS_UPDATE,
            content={
                'pipeline_id': pipeline_id,
                'stage': stage,
                'progress': progress,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    async def cleanup(self) -> None:
        """Cleanup processor resources"""
        # Cleanup formatters
        for formatter in self.formatters.values():
            formatter.cleanup()

        # Clear active reports
        self.active_reports.clear()
