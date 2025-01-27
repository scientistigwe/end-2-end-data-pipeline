# modules/visualization/chart_generator.py
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import plotly.graph_objects as go
import plotly.express as px


async def create_charts(evaluation_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate interactive charts for model evaluation"""
    try:
        charts = []

        # Performance metrics chart
        if 'metrics' in evaluation_data:
            charts.append(_create_metrics_chart(evaluation_data['metrics']))

        # Feature importance chart
        if 'feature_importance' in evaluation_data:
            charts.append(
                _create_feature_importance_chart(
                    evaluation_data['feature_importance']
                )
            )

        # Model predictions vs actual
        if 'predictions' in evaluation_data:
            charts.append(
                _create_predictions_chart(
                    evaluation_data['predictions']
                )
            )

        return charts

    except Exception as e:
        print(f"Error in create_charts: {str(e)}")
        raise


def _create_metrics_chart(metrics: Dict[str, float]) -> Dict[str, Any]:
    """Create bar chart of performance metrics"""
    fig = go.Figure(data=[
        go.Bar(
            x=list(metrics.keys()),
            y=list(metrics.values()),
            text=[f"{v:.2f}" for v in metrics.values()],
            textposition='auto',
        )
    ])

    fig.update_layout(
        title="Model Performance Metrics",
        xaxis_title="Metric",
        yaxis_title="Value"
    )

    return {
        'id': 'metrics_chart',
        'title': 'Performance Metrics',
        'type': 'bar',
        'data': fig.to_dict()
    }


def _create_feature_importance_chart(
        feature_importance: Dict[str, float]
) -> Dict[str, Any]:
    """Create horizontal bar chart of feature importance"""
    sorted_features = dict(
        sorted(
            feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )
    )

    fig = go.Figure(data=[
        go.Bar(
            y=list(sorted_features.keys()),
            x=list(sorted_features.values()),
            orientation='h'
        )
    ])

    fig.update_layout(
        title="Feature Importance",
        xaxis_title="Importance",
        yaxis_title="Feature"
    )

    return {
        'id': 'feature_importance_chart',
        'title': 'Feature Importance',
        'type': 'bar',
        'data': fig.to_dict()
    }


def _create_predictions_chart(predictions: Dict[str, Any]) -> Dict[str, Any]:
    """Create scatter plot of predicted vs actual values"""
    fig = go.Figure(data=[
        go.Scatter(
            x=predictions['actual'],
            y=predictions['predicted'],
            mode='markers',
            marker=dict(
                size=8,
                color='blue',
                opacity=0.6
            )
        )
    ])

    fig.update_layout(
        title="Predicted vs Actual Values",
        xaxis_title="Actual Values",
        yaxis_title="Predicted Values"
    )

    # Add 45-degree line
    fig.add_trace(
        go.Scatter(
            x=[min(predictions['actual']), max(predictions['actual'])],
            y=[min(predictions['actual']), max(predictions['actual'])],
            mode='lines',
            line=dict(color='red', dash='dash'),
            name='Perfect Prediction'
        )
    )

    return {
        'id': 'predictions_chart',
        'title': 'Predictions vs Actual',
        'type': 'scatter',
        'data': fig.to_dict()
    }