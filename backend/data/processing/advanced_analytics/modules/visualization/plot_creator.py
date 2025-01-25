# modules/visualization/plot_creator.py
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


async def create_plots(evaluation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate advanced analytical plots"""
    try:
        plots = []

        # Residuals insight plots
        if all(k in evaluation_data for k in ['actual', 'predicted']):
            plots.extend(_create_residual_plots(evaluation_data))

        # Distribution plots
        if 'predictions' in evaluation_data:
            plots.append(_create_distribution_plots(evaluation_data['predictions']))

        # Error insight plots
        if 'error_analysis' in evaluation_data:
            plots.append(_create_error_analysis_plots(evaluation_data['error_analysis']))

        # Model stability plots
        if 'stability_metrics' in evaluation_data:
            plots.append(
                _create_stability_plots(evaluation_data['stability_metrics'])
            )

        return plots

    except Exception as e:
        print(f"Error in create_plots: {str(e)}")
        raise


def _create_residual_plots(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create residual insight plots"""
    residuals = np.array(data['predicted']) - np.array(data['actual'])

    # Residuals vs Predicted
    fig1 = go.Figure(data=[
        go.Scatter(
            x=data['predicted'],
            y=residuals,
            mode='markers',
            marker=dict(size=8, color='blue', opacity=0.6)
        )
    ])

    fig1.update_layout(
        title="Residuals vs Predicted Values",
        xaxis_title="Predicted Values",
        yaxis_title="Residuals"
    )

    # QQ Plot
    sorted_residuals = np.sort(residuals)
    theoretical_quantiles = stats.norm.ppf(
        np.linspace(0.01, 0.99, len(residuals))
    )

    fig2 = go.Figure(data=[
        go.Scatter(
            x=theoretical_quantiles,
            y=sorted_residuals,
            mode='markers',
            marker=dict(size=8, color='blue', opacity=0.6)
        )
    ])

    fig2.update_layout(
        title="Q-Q Plot of Residuals",
        xaxis_title="Theoretical Quantiles",
        yaxis_title="Sample Quantiles"
    )

    return [
        {
            'id': 'residuals_predicted',
            'title': 'Residuals Analysis',
            'type': 'scatter',
            'data': fig1.to_dict()
        },
        {
            'id': 'qq_plot',
            'title': 'Q-Q Plot',
            'type': 'scatter',
            'data': fig2.to_dict()
        }
    ]


def _create_distribution_plots(predictions: Dict[str, Any]) -> Dict[str, Any]:
    """Create distribution comparison plots"""
    fig = make_subplots(rows=1, cols=2)

    # Actual distribution
    fig.add_trace(
        go.Histogram(
            x=predictions['actual'],
            name='Actual',
            opacity=0.75
        ),
        row=1, col=1
    )

    # Predicted distribution
    fig.add_trace(
        go.Histogram(
            x=predictions['predicted'],
            name='Predicted',
            opacity=0.75
        ),
        row=1, col=2
    )

    fig.update_layout(
        title="Distribution Comparison: Actual vs Predicted",
        showlegend=True
    )

    return {
        'id': 'distribution_comparison',
        'title': 'Distribution Analysis',
        'type': 'histogram',
        'data': fig.to_dict()
    }


def _create_error_analysis_plots(error_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create error insight plots"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            'Error Distribution',
            'Error by Feature',
            'Error Heatmap',
            'Error Timeline'
        ]
    )

    # Error distribution
    fig.add_trace(
        go.Histogram(x=error_data['errors']),
        row=1, col=1
    )

    # Error by feature
    if 'error_by_feature' in error_data:
        fig.add_trace(
            go.Bar(
                x=list(error_data['error_by_feature'].keys()),
                y=list(error_data['error_by_feature'].values())
            ),
            row=1, col=2
        )

    # Error heatmap
    if 'error_matrix' in error_data:
        fig.add_trace(
            go.Heatmap(z=error_data['error_matrix']),
            row=2, col=1
        )

    # Error timeline
    if 'error_timeline' in error_data:
        fig.add_trace(
            go.Scatter(
                x=error_data['error_timeline']['timestamps'],
                y=error_data['error_timeline']['errors'],
                mode='lines+markers'
            ),
            row=2, col=2
        )

    fig.update_layout(
        height=800,
        title_text="Comprehensive Error Analysis",
        showlegend=False
    )

    return {
        'id': 'error_analysis',
        'title': 'Error Analysis Dashboard',
        'type': 'multi_plot',
        'data': fig.to_dict()
    }


def _create_stability_plots(stability_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Create model stability insight plots"""
    fig = make_subplots(rows=2, cols=2)

    # CV stability
    if 'cv_scores' in stability_metrics:
        fig.add_trace(
            go.Box(y=stability_metrics['cv_scores'], name='CV Scores'),
            row=1, col=1
        )

    # Feature stability
    if 'feature_stability' in stability_metrics:
        fig.add_trace(
            go.Bar(
                x=list(stability_metrics['feature_stability'].keys()),
                y=list(stability_metrics['feature_stability'].values()),
                name='Feature Stability'
            ),
            row=1, col=2
        )

    # Noise stability
    if 'noise_impact' in stability_metrics:
        fig.add_trace(
            go.Scatter(
                x=list(stability_metrics['noise_impact'].keys()),
                y=list(stability_metrics['noise_impact'].values()),
                mode='lines+markers',
                name='Noise Impact'
            ),
            row=2, col=1
        )

    fig.update_layout(
        height=800,
        title_text="Model Stability Analysis",
        showlegend=True
    )

    return {
        'id': 'stability_analysis',
        'title': 'Stability Analysis',
        'type': 'multi_plot',
        'data': fig.to_dict()
    }