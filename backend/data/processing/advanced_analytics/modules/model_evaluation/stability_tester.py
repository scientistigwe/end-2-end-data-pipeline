# modules/model_evaluation/stability_tester.py
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error, accuracy_score


async def test_model_stability(model_info: Dict[str, Any]) -> Dict[str, Any]:
    """Test model stability across different data splits and conditions"""
    try:
        model = model_info['tuned_model']
        stability_metrics = {}

        # Cross-validation stability
        cv_scores = _check_cross_validation_stability(model, X, y)
        stability_metrics['cv_stability'] = {
            'mean_score': np.mean(cv_scores),
            'std_score': np.std(cv_scores),
            'coefficient_of_variation': np.std(cv_scores) / np.mean(cv_scores)
        }

        # Feature stability
        feature_stability = _check_feature_stability(model, X, y)
        stability_metrics['feature_stability'] = feature_stability

        # Performance stability under noise
        noise_stability = _check_noise_stability(model, X, y)
        stability_metrics['noise_stability'] = noise_stability

        return {
            'stability_metrics': stability_metrics,
            'stability_score': _calculate_overall_stability(stability_metrics),
            'recommendations': _generate_stability_recommendations(stability_metrics)
        }

    except Exception as e:
        print(f"Error in test_model_stability: {str(e)}")
        raise


def _check_cross_validation_stability(
        model: Any,
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = 5
) -> List[float]:
    """Check model stability across different data splits"""
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    scores = []

    for train_idx, test_idx in kf.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        score = (
            accuracy_score(y_test, y_pred) if y.dtype in ['int64', 'bool']
            else mean_squared_error(y_test, y_pred)
        )
        scores.append(score)

    return scores


def _check_feature_stability(
        model: Any,
        X: pd.DataFrame,
        y: pd.Series
) -> Dict[str, float]:
    """Check model stability when removing features"""
    baseline_score = _get_model_score(model, X, y)
    feature_impacts = {}

    for column in X.columns:
        X_reduced = X.drop(column, axis=1)
        reduced_score = _get_model_score(model, X_reduced, y)
        feature_impacts[column] = abs(baseline_score - reduced_score)

    return {
        'feature_impacts': feature_impacts,
        'max_impact': max(feature_impacts.values()),
        'mean_impact': np.mean(list(feature_impacts.values()))
    }


def _check_noise_stability(
        model: Any,
        X: pd.DataFrame,
        y: pd.Series,
        noise_levels: List[float] = [0.01, 0.05, 0.1]
) -> Dict[str, float]:
    """Check model stability under different noise levels"""
    baseline_score = _get_model_score(model, X, y)
    noise_impacts = {}

    for noise_level in noise_levels:
        X_noisy = X + np.random.normal(0, noise_level, X.shape)
        noisy_score = _get_model_score(model, X_noisy, y)
        noise_impacts[f'noise_{noise_level}'] = abs(baseline_score - noisy_score)

    return {
        'noise_impacts': noise_impacts,
        'max_impact': max(noise_impacts.values()),
        'mean_impact': np.mean(list(noise_impacts.values()))
    }


def _get_model_score(model: Any, X: pd.DataFrame, y: pd.Series) -> float:
    """Get model score based on problem type"""
    y_pred = model.predict(X)
    return (
        accuracy_score(y, y_pred) if y.dtype in ['int64', 'bool']
        else mean_squared_error(y, y_pred)
    )


def _calculate_overall_stability(metrics: Dict[str, Any]) -> float:
    """Calculate overall stability score"""
    cv_stability = 1 - metrics['cv_stability']['coefficient_of_variation']
    feature_stability = 1 - metrics['feature_stability']['mean_impact']
    noise_stability = 1 - metrics['noise_stability']['mean_impact']

    return np.mean([cv_stability, feature_stability, noise_stability])


def _generate_stability_recommendations(
        metrics: Dict[str, Any]
) -> List[str]:
    """Generate recommendations for improving model stability"""
    recommendations = []

    if metrics['cv_stability']['coefficient_of_variation'] > 0.1:
        recommendations.append(
            "Consider collecting more training data or using regularization "
            "to improve cross-validation stability"
        )

    if metrics['feature_stability']['max_impact'] > 0.1:
        recommendations.append(
            "Some features have high impact on model performance. "
            "Consider feature selection or engineering to reduce dependency"
        )

    if metrics['noise_stability']['max_impact'] > 0.1:
        recommendations.append(
            "Model is sensitive to noise. Consider adding regularization "
            "or using more robust model architectures"
        )

    return recommendations