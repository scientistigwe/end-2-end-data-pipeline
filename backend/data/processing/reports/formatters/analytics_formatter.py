# backend/data_pipeline/reporting/formatters/analytics_formatter.py

import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
import uuid

from .base_formatter import BaseFormatter
from ..types.report_types import (
    Report,
    AnalyticsReport,
    ReportSection,
    ReportVisualization,
    ReportFormat
)

logger = logging.getLogger(__name__)


class AnalyticsReportFormatter(BaseFormatter):
    """
    Formatter for advanced analytics reports.
    Handles formatting of model results, performance metrics, and predictions.
    """

    def __init__(self, template_dir: Path = None, config: Dict[str, Any] = None):
        super().__init__(
            template_dir=template_dir or Path("templates/analytics_templates"),
            config=config
        )
        self.supported_formats = [
            ReportFormat.HTML,
            ReportFormat.PDF,
            ReportFormat.JSON,
            ReportFormat.MARKDOWN
        ]

    async def format_report(self, report: AnalyticsReport) -> Dict[str, Any]:
        """Format complete analytics report"""
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

            # Add analytics-specific sections
            analytics_sections = self._create_analytics_sections(report)
            formatted_sections.extend(analytics_sections)

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
                    **self._create_metadata(),
                    'analysis_type': report.analysis_type
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
            logger.error(f"Failed to format analytics report: {str(e)}")
            return self._format_error_response(e)

    def _create_overview(self, report: AnalyticsReport) -> Dict[str, Any]:
        """Create analytics report overview"""
        model_performance = report.model_performance or {}
        return {
            'analysis_type': report.analysis_type,
            'model_performance': {
                'primary_metric': self._get_primary_metric(model_performance),
                'performance_summary': self._summarize_performance(model_performance)
            },
            'key_findings': self._extract_key_findings(report),
            'feature_importance': self._summarize_feature_importance(
                report.feature_importance
            ),
            'prediction_summary': self._summarize_predictions(report.predictions)
        }

    def _create_analytics_sections(self, report: AnalyticsReport) -> List[Dict[str, Any]]:
        """Create analytics-specific sections"""
        sections = []

        # Model Performance Section
        sections.append({
            'title': 'Model Performance Analysis',
            'content': self._format_model_performance(report.model_performance),
            'order': 1
        })

        # Feature Importance Section
        sections.append({
            'title': 'Feature Analysis',
            'content': self._format_feature_analysis(
                report.feature_importance
            ),
            'order': 2
        })

        # Predictions Section
        sections.append({
            'title': 'Prediction Analysis',
            'content': self._format_predictions(report.predictions),
            'order': 3
        })

        return sections

    def _format_model_performance(
            self,
            performance: Dict[str, float]
    ) -> Dict[str, Any]:
        """Format model performance metrics"""
        return {
            'type': 'model_performance',
            'metrics': {
                metric: {
                    'value': value,
                    'interpretation': self._interpret_metric(metric, value),
                    'benchmark': self._get_metric_benchmark(metric)
                }
                for metric, value in performance.items()
            },
            'overall_assessment': self._assess_model_performance(performance),
            'recommendations': self._generate_performance_recommendations(performance)
        }

    def _format_feature_analysis(
            self,
            feature_importance: Dict[str, float]
    ) -> Dict[str, Any]:
        """Format feature importance analysis"""
        # Sort features by importance
        sorted_features = sorted(
            feature_importance.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )

        # Group features by importance level
        top_features = sorted_features[:5]
        moderate_features = sorted_features[5:10]
        other_features = sorted_features[10:]

        return {
            'type': 'feature_analysis',
            'importance_groups': {
                'high_importance': [
                    {
                        'feature': feature,
                        'importance': value,
                        'interpretation': self._interpret_feature_importance(value)
                    }
                    for feature, value in top_features
                ],
                'moderate_importance': [
                    {
                        'feature': feature,
                        'importance': value,
                        'interpretation': self._interpret_feature_importance(value)
                    }
                    for feature, value in moderate_features
                ],
                'low_importance': [
                    {
                        'feature': feature,
                        'importance': value,
                        'interpretation': self._interpret_feature_importance(value)
                    }
                    for feature, value in other_features
                ]
            },
            'recommendations': self._generate_feature_recommendations(
                feature_importance
            )
        }

    def _format_predictions(self, predictions: Dict[str, Any]) -> Dict[str, Any]:
        """Format prediction analysis"""
        return {
            'type': 'predictions',
            'summary': {
                'total_predictions': len(predictions.get('values', [])),
                'distribution': self._analyze_prediction_distribution(predictions),
                'confidence_levels': self._analyze_confidence_levels(predictions)
            },
            'segments': self._analyze_prediction_segments(predictions),
            'notable_patterns': self._identify_prediction_patterns(predictions)
        }

    async def format_visualization(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format analytics visualization"""
        try:
            if visualization.viz_type == 'performance_metrics':
                return self._format_performance_viz(visualization)
            elif visualization.viz_type == 'feature_importance':
                return self._format_feature_importance_viz(visualization)
            elif visualization.viz_type == 'prediction_distribution':
                return self._format_prediction_distribution_viz(visualization)
            elif visualization.viz_type == 'error_analysis':
                return self._format_error_analysis_viz(visualization)
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

    def _get_primary_metric(self, performance: Dict[str, float]) -> Dict[str, Any]:
        """Get primary performance metric based on analysis type"""
        metric_priorities = {
            'classification': ['accuracy', 'f1_score', 'auc_roc'],
            'regression': ['r2_score', 'rmse', 'mae'],
            'clustering': ['silhouette_score', 'calinski_harabasz_score'],
            'ranking': ['ndcg', 'map', 'mrr']
        }

        # Iterate through metrics to find the primary one
        for metric in metric_priorities.get(self.analysis_type, []):
            if metric in performance:
                return {
                    'name': metric,
                    'value': performance[metric],
                    'interpretation': self._interpret_metric(
                        metric,
                        performance[metric]
                    )
                }

        # Return first available metric if no primary metric found
        first_metric = next(iter(performance.items()), None)
        if first_metric:
            return {
                'name': first_metric[0],
                'value': first_metric[1],
                'interpretation': self._interpret_metric(
                    first_metric[0],
                    first_metric[1]
                )
            }

        return {'name': 'unknown', 'value': 0.0, 'interpretation': 'No metrics available'}

    def _summarize_feature_importance(
            self,
            feature_importance: Dict[str, float]
    ) -> Dict[str, Any]:
        """Summarize feature importance analysis"""
        if not feature_importance:
            return {'error': 'No feature importance data available'}

        # Sort features by absolute importance
        sorted_features = sorted(
            feature_importance.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )

        return {
            'top_features': [
                {'name': f[0], 'importance': f[1]}
                for f in sorted_features[:5]
            ],
            'total_features': len(feature_importance),
            'importance_distribution': {
                'high': len([f for f in feature_importance.values() if abs(f) > 0.3]),
                'medium': len([f for f in feature_importance.values() if 0.1 < abs(f) <= 0.3]),
                'low': len([f for f in feature_importance.values() if abs(f) <= 0.1])
            }
        }

    def _interpret_metric(self, metric: str, value: float) -> str:
        """Interpret a metric value"""
        # Metric interpretation thresholds
        thresholds = {
            'accuracy': {'excellent': 0.9, 'good': 0.8, 'fair': 0.7},
            'f1_score': {'excellent': 0.9, 'good': 0.8, 'fair': 0.7},
            'auc_roc': {'excellent': 0.9, 'good': 0.8, 'fair': 0.7},
            'r2_score': {'excellent': 0.9, 'good': 0.7, 'fair': 0.5},
            'rmse': {'excellent': 0.1, 'good': 0.2, 'fair': 0.3},  # Lower is better
            'mae': {'excellent': 0.1, 'good': 0.2, 'fair': 0.3}  # Lower is better
        }

        if metric in thresholds:
            t = thresholds[metric]
            if value >= t['excellent']:
                return 'Excellent performance'
            elif value >= t['good']:
                return 'Good performance'
            elif value >= t['fair']:
                return 'Fair performance'
            else:
                return 'Needs improvement'

        return f'Value: {value}'

    def _analyze_prediction_distribution(
            self,
            predictions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze distribution of predictions"""
        values = predictions.get('values', [])
        if not values:
            return {'error': 'No prediction data available'}

        # Calculate basic statistics
        return {
            'min': min(values),
            'max': max(values),
            'mean': sum(values) / len(values),
            'quartiles': {
                'q1': self._calculate_percentile(values, 25),
                'q2': self._calculate_percentile(values, 50),
                'q3': self._calculate_percentile(values, 75)
            }
        }

    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(values) - 1)
        return sorted_values[int(round(index))]

    def _format_performance_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format performance metrics visualization"""
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'performance_metrics',
            'title': visualization.title,
            'data': {
                'metrics': visualization.data.get('metrics', {}),
                'benchmark_comparison': visualization.data.get('benchmarks', {}),
                'trend': visualization.data.get('trend', [])
            },
            'config': visualization.config
        }

    def _format_feature_importance_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format feature importance visualization"""
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'feature_importance',
            'title': visualization.title,
            'data': {
                'importance_scores': visualization.data.get('scores', {}),
                'feature_correlations': visualization.data.get('correlations', {}),
                'feature_groups': visualization.data.get('groups', [])
            },
            'config': visualization.config
        }

    def _format_prediction_distribution_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format prediction distribution visualization"""
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'prediction_distribution',
            'title': visualization.title,
            'data': {
                'distribution': visualization.data.get('distribution', {}),
                'segments': visualization.data.get('segments', {}),
                'outliers': visualization.data.get('outliers', [])
            },
            'config': visualization.config
        }

    def _format_error_analysis_viz(
            self,
            visualization: ReportVisualization
    ) -> Dict[str, Any]:
        """Format error analysis visualization"""
        return {
            'viz_id': str(visualization.viz_id),
            'type': 'error_analysis',
            'title': visualization.title,
            'data': {
                'error_distribution': visualization.data.get('error_dist', {}),
                'feature_correlation': visualization.data.get('feature_corr', {}),
                'error_segments': visualization.data.get('segments', [])
            },
            'config': visualization.config
        }