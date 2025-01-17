# modules/model_training/model_trainer.py
import pandas as pd
from typing import Dict, Any
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, r2_score, mean_squared_error


async def train_model(
        model_info: Dict[str, Any],
        data: pd.DataFrame
) -> Dict[str, Any]:
    """Train selected model"""
    try:
        # Separate features and target
        X = data.drop('target', axis=1) if 'target' in data.columns else data
        y = data['target'] if 'target' in data.columns else None

        if y is None:
            raise ValueError("No target column found in data")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Train model
        model = model_info['selected_model']
        model.fit(X_train, y_train)

        # Generate predictions
        y_pred = model.predict(X_test)

        # Calculate metrics
        is_classification = y.dtype in ['int64', 'bool']
        metrics = {
            'test_score': (
                accuracy_score(y_test, y_pred) if is_classification
                else r2_score(y_test, y_pred)
            ),
            'mse': mean_squared_error(y_test, y_pred),
            'training_samples': len(X_train),
            'test_samples': len(X_test)
        }

        return {
            'trained_model': model,
            'metrics': metrics,
            'feature_importance': _get_feature_importance(model, X.columns)
        }

    except Exception as e:
        print(f"Error in train_model: {str(e)}")
        raise


def _get_feature_importance(model: Any, feature_names: pd.Index) -> Dict[str, float]:
    """Extract feature importance if available"""
    if hasattr(model, 'feature_importances_'):
        return dict(zip(feature_names, model.feature_importances_))
    elif hasattr(model, 'coef_'):
        return dict(zip(feature_names, model.coef_))
    return {}