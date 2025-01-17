# modules/model_training/model_tuner.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor


async def tune_model(
        training_info: Dict[str, Any],
        data: pd.DataFrame
) -> Dict[str, Any]:
    """Tune model hyperparameters"""
    try:
        # Separate features and target
        X = data.drop('target', axis=1) if 'target' in data.columns else data
        y = data['target'] if 'target' in data.columns else None

        if y is None:
            raise ValueError("No target column found in data")

        model = training_info['trained_model']

        # Define parameter grid based on model type
        param_grid = _get_parameter_grid(model)

        if not param_grid:
            return {
                'tuned_model': model,
                'best_params': {},
                'tuning_scores': {}
            }

        # Perform grid search
        grid_search = GridSearchCV(
            model, param_grid,
            cv=5,
            n_jobs=-1,
            scoring='accuracy' if y.dtype in ['int64', 'bool'] else 'r2'
        )

        grid_search.fit(X, y)

        return {
            'tuned_model': grid_search.best_estimator_,
            'best_params': grid_search.best_params_,
            'tuning_scores': {
                'best_score': grid_search.best_score_,
                'cv_results': grid_search.cv_results_
            }
        }

    except Exception as e:
        print(f"Error in tune_model: {str(e)}")
        raise


def _get_parameter_grid(model: Any) -> Dict[str, list]:
    """Get parameter grid based on model type"""
    if isinstance(model, (RandomForestClassifier, RandomForestRegressor)):
        return {
            'n_estimators': [100, 200, 300],
            'max_depth': [10, 20, 30, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
    # Add more model-specific grids as needed
    return {}