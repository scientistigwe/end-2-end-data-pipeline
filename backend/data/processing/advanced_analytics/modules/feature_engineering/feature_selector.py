# modules/feature_engineering/feature_selector.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_regression


async def select_features(data: pd.DataFrame) -> pd.DataFrame:
    """Select most important features"""
    try:
        # Separate features and target
        X = data.drop('target', axis=1) if 'target' in data.columns else data
        y = data['target'] if 'target' in data.columns else None

        selected_features = X.copy()

        # Remove highly correlated features
        correlation_matrix = selected_features.corr().abs()
        upper = correlation_matrix.where(
            np.triu(np.ones(correlation_matrix.shape), k=1).astype(bool)
        )
        to_drop = [
            column for column in upper.columns
            if any(upper[column] > 0.95)
        ]
        selected_features = selected_features.drop(to_drop, axis=1)

        # If target exists, use statistical feature selection
        if y is not None:
            if y.dtype in ['int64', 'bool']:
                selector = SelectKBest(score_func=f_classif, k='all')
            else:
                selector = SelectKBest(score_func=mutual_info_regression, k='all')

            selector.fit(selected_features, y)
            feature_scores = pd.DataFrame({
                'feature': selected_features.columns,
                'score': selector.scores_
            })

            # Keep features with scores above mean
            significant_features = feature_scores[
                feature_scores['score'] > feature_scores['score'].mean()
                ]['feature'].tolist()

            selected_features = selected_features[significant_features]

        return selected_features

    except Exception as e:
        print(f"Error in select_features: {str(e)}")
        raise