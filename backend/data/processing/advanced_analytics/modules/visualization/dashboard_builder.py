# modules/visualization/dashboard_builder.py
import pandas as pd
from typing import Dict, Any, List
import plotly.graph_objects as go
from plotly.subplots import make_subplots


async def create_dashboard(evaluation_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create comprehensive analytics dashboard"""
    try:
        dashboard_components = []

        # Overview section
        if 'metrics' in evaluation_data:
            dashboard_components.append(
                _create_metrics_overview(evaluation_data['metrics'])
            )

        # Model performance section
        if all(k in evaluation_data for k in ['predictions', 'feature_importance']):
            dashboard_components.append(
                _create_performance_section(evaluation_data)
            )

        # Error insight section
        if 'error_analysis' in evaluation_data:
            dashboard_components.append(
                _create_error_section(evaluation_data['error_analysis'])
            )

        # Feature insight section
        if 'feature_importance' in evaluation_data:
            dashboard_components.append(
                _create_feature_section(evaluation_data['feature_importance'])
            )

        return {
            'title': 'Model Analysis Dashboard',
            'components': dashboard_components,
            'layout': _generate_dashboard_layout(len(dashboard_components))
        }

    except Exception as e:
        print(f"Error in create_dashboard: {str(e)}")
        raise


def _create_metrics_overview(metrics: Dict[str, float]) -> Dict[str, Any]:
    """Create metrics overview cards"""
    return {
        'type': 'metrics_grid',
        'title': 'Performance Metrics',
        'items': [
            {
                'title': key.replace('_', ' ').title(),
                'value': f"{value:.3f}",
                'color': _get_metric_color(key, value)
            }
            for key, value in metrics.items()
        ]
    }


def _create_performance_section(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create model performance visualization section"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            'Predictions vs Actual',
            'Residuals Analysis',
            'Feature Importance',
            'Error Distribution'
        ]
    )

    # Add plots
    _add_predictions_plot(fig, data['predictions'], 1, 1)
    _add_residuals_plot(fig, data['predictions'], 1, 2)
    _add_feature_importance_plot(fig, data['feature_importance'], 2, 1)
    _add_error_distribution_plot(fig, data['predictions'], 2, 2)

    return {
        'type': 'plotly_figure',
        'title': 'Model Performance Analysis',
        'figure': fig.to_dict()
    }


def _create_error_section(error_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create error insight section"""
    return {
        'type': 'error_analysis',
        'title': 'Error Analysis',
        'components': [
            {
                'type': 'error_distribution',
                'data': error_data.get('error_distribution', {})
            },
            {
                'type': 'error_breakdown',
                'data': error_data.get('error_by_category', {})
            }
        ]
    }


def _create_feature_section(
        feature_importance: Dict[str, float]
) -> Dict[str, Any]:
    """Create feature insight section"""
    return {
        'type': 'feature_analysis',
        'title': 'Feature Analysis',
        'components': [
            {
                'type': 'importance_chart',
                'data': feature_importance
            },
            {
                'type': 'feature_correlation',
                'data': _calculate_feature_correlations(feature_importance)
            }
        ]
    }


def _get_metric_color(metric: str, value: float) -> str:
    """Determine color for metric based on value and type"""
    if 'error' in metric.lower():
        return '#ff4444' if value > 0.1 else '#00C851'
    return '#00C851' if value > 0.8 else '#ff4444'


def _generate_dashboard_layout(component_count: int) -> Dict[str, Any]:
    """Generate responsive dashboard layout"""
    return {
        'grid_template': f"repeat({(component_count + 1) // 2}, 1fr)",
        'gap': '20px',
        'padding': '20px'
    }


def _calculate_feature_correlations(
        feature_importance: Dict[str, float]
) -> Dict[str, float]:
    """Calculate correlations between important features"""
    features = pd.DataFrame(feature_importance.items(), columns=['feature', 'importance'])
    correlations = features.corr()
    return correlations.to_dict()