# modules/feature_engineering/feature_extractor.py
import pandas as pd
import numpy as np
from typing import Dict, Any


async def extract_features(data: pd.DataFrame) -> pd.DataFrame:
    """Extract features from data"""
    try:
        features = data.copy()

        # Extract datetime features
        datetime_cols = features.select_dtypes(include=['datetime64']).columns
        for col in datetime_cols:
            features[f'{col}_year'] = features[col].dt.year
            features[f'{col}_month'] = features[col].dt.month
            features[f'{col}_day'] = features[col].dt.day
            features[f'{col}_dayofweek'] = features[col].dt.dayofweek
            features = features.drop(col, axis=1)

        # Extract numeric features
        numeric_cols = features.select_dtypes(include=['int64', 'float64']).columns
        for col in numeric_cols:
            # Add squared terms
            features[f'{col}_squared'] = features[col] ** 2
            # Add log terms (handling negative values)
            if features[col].min() > 0:
                features[f'{col}_log'] = np.log(features[col])

        return features

    except Exception as e:
        print(f"Error in extract_features: {str(e)}")
        raise