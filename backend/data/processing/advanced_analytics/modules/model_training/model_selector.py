# modules/model_training/model_selector.py
import pandas as pd
from typing import Dict, Any
from sklearn.model_selection import cross_val_score
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.svm import SVR, SVC


async def select_model(
        data: pd.DataFrame,
        config: Dict[str, Any]
) -> Dict[str, Any]:
    """Select best performing model"""
    try:
        # Separate features and target
        X = data.drop('target', axis=1) if 'target' in data.columns else data
        y = data['target'] if 'target' in data.columns else None

        if y is None:
            raise ValueError("No target column found in data")

        # Define candidate models based on problem type
        is_classification = y.dtype in ['int64', 'bool']
        models = {
            'linear': (
                LogisticRegression() if is_classification
                else LinearRegression()
            ),
            'random_forest': (
                RandomForestClassifier() if is_classification
                else RandomForestRegressor()
            ),
            'svm': SVC() if is_classification else SVR()
        }

        # Evaluate models
        model_scores = {}
        for name, model in models.items():
            scores = cross_val_score(
                model, X, y,
                cv=5,
                scoring='accuracy' if is_classification else 'r2'
            )
            model_scores[name] = {
                'mean_score': scores.mean(),
                'std_score': scores.std(),
                'model': model
            }

        # Select best model
        best_model_name = max(
            model_scores.keys(),
            key=lambda k: model_scores[k]['mean_score']
        )

        return {
            'selected_model': model_scores[best_model_name]['model'],
            'model_type': best_model_name,
            'evaluation_scores': model_scores
        }

    except Exception as e:
        print(f"Error in select_model: {str(e)}")
        raise