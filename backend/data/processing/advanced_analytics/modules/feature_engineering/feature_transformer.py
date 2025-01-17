# modules/feature_engineering/feature_transformer.py
import pandas as pd
import numpy as np
from typing import Dict, Any
from sklearn.preprocessing import StandardScaler, RobustScaler


async def transform_features(data: pd.DataFrame) -> pd.DataFrame:
    """Transform features for modeling"""
    try:
        transformed = data.copy()

        # Handle numeric features
        numeric_cols = transformed.select_dtypes(
            include=['int64', 'float64']
        ).columns

        if len(numeric_cols) > 0:
            # Use RobustScaler for outlier-resistant scaling
            scaler = RobustScaler()
            transformed[numeric_cols] = scaler.fit_transform(
                transformed[numeric_cols]
            )

        # Handle skewed features
        for col in numeric_cols:
            skewness = transformed[col].skew()
            if abs(skewness) > 1:
                # Apply Box-Cox transformation for highly skewed features
                if min(transformed[col]) > 0:
                    transformed[col] = np.log1p(transformed[col])

        return transformed

    except Exception as e:
        print(f"Error in transform_features: {str(e)}")
        raise