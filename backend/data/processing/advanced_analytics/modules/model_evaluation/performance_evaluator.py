# modules/model_evaluation/performance_evaluator.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, r2_score, mean_absolute_error
)


async def evaluate_model(model_info: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate model performance comprehensively"""
    try:
        model = model_info['tuned_model']
        metrics = {}

        # Get predictions
        y_pred = model.predict(X_test)

        # Classification metrics
        if is_classification:
            metrics.update({
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred, average='weighted'),
                'recall': recall_score(y_test, y_pred, average='weighted'),
                'f1': f1_score(y_test, y_pred, average='weighted')
            })
        # Regression metrics
        else:
            metrics.update({
                'r2': r2_score(y_test, y_pred),
                'mse': mean_squared_error(y_test, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
                'mae': mean_absolute_error(y_test, y_pred)
            })

        return {
            'metrics': metrics,
            'feature_importance': model_info.get('feature_importance', {}),
            'performance_summary': _generate_performance_summary(metrics)
        }

    except Exception as e:
        print(f"Error in evaluate_model: {str(e)}")
        raise


def _generate_performance_summary(metrics: Dict[str, float]) -> str:
    """Generate human-readable performance summary"""
    if 'accuracy' in metrics:
        return (
            f"Model achieves {metrics['accuracy']:.2%} accuracy with "
            f"F1 score of {metrics['f1']:.2f}"
        )
    return (
        f"Model explains {metrics['r2']:.2%} of variance with "
        f"RMSE of {metrics['rmse']:.2f}"
    )