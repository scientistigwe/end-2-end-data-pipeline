# modules/model_evaluation/bias_checker.py
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from sklearn.metrics import confusion_matrix


async def check_model_bias(model_info: Dict[str, Any]) -> Dict[str, Any]:
    """Check for potential biases in model predictions"""
    try:
        model = model_info['tuned_model']
        bias_metrics = {}

        # Calculate prediction distributions
        pred_distribution = pd.Series(y_pred).value_counts(normalize=True)
        actual_distribution = pd.Series(y_test).value_counts(normalize=True)

        # Check for prediction bias
        bias_metrics['distribution_bias'] = _calculate_distribution_bias(
            pred_distribution, actual_distribution
        )

        # Check for demographic bias if available
        if 'demographic_features' in X_test.columns:
            bias_metrics['demographic_bias'] = _check_demographic_bias(
                model, X_test, y_test
            )

        # Calculate confusion matrix for classification
        if is_classification:
            cm = confusion_matrix(y_test, y_pred)
            bias_metrics['error_bias'] = _analyze_error_distribution(cm)

        return {
            'bias_metrics': bias_metrics,
            'recommendations': _generate_bias_recommendations(bias_metrics)
        }

    except Exception as e:
        print(f"Error in check_model_bias: {str(e)}")
        raise


def _calculate_distribution_bias(
        pred_dist: pd.Series,
        actual_dist: pd.Series
) -> float:
    """Calculate bias in prediction distribution"""
    return np.abs(pred_dist - actual_dist).mean()


def _check_demographic_bias(
        model: Any,
        X: pd.DataFrame,
        y: pd.Series
) -> Dict[str, float]:
    """Check for bias across demographic groups"""
    demographic_metrics = {}
    for demo_col in X.columns:
        if 'demographic' in demo_col:
            for group in X[demo_col].unique():
                mask = X[demo_col] == group
                group_preds = model.predict(X[mask])
                group_actual = y[mask]
                demographic_metrics[f"{demo_col}_{group}"] = (
                    accuracy_score(group_actual, group_preds)
                )
    return demographic_metrics


def _analyze_error_distribution(cm: np.ndarray) -> Dict[str, float]:
    """Analyze distribution of errors across classes"""
    return {
        'false_positive_rate': cm[0, 1] / (cm[0, 0] + cm[0, 1]),
        'false_negative_rate': cm[1, 0] / (cm[1, 0] + cm[1, 1])
    }


def _generate_bias_recommendations(metrics: Dict[str, Any]) -> List[str]:
    """Generate recommendations for addressing bias"""
    recommendations = []

    if metrics.get('distribution_bias', 0) > 0.1:
        recommendations.append(
            "Consider resampling techniques to balance prediction distribution"
        )

    return recommendations