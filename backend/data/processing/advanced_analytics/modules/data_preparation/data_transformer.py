# modules/data_preparation/data_transformer.py
import pandas as pd
from typing import Dict, Any


async def transform_data(data: pd.DataFrame) -> pd.DataFrame:
    """Transform data for analysis"""
    try:
        # Apply standard transformations
        transformed_data = data.copy()

        # Handle numeric transformations
        numeric_cols = transformed_data.select_dtypes(include=['int64', 'float64']).columns
        for col in numeric_cols:
            # Remove outliers using IQR method
            Q1 = transformed_data[col].quantile(0.25)
            Q3 = transformed_data[col].quantile(0.75)
            IQR = Q3 - Q1
            transformed_data = transformed_data[
                (transformed_data[col] >= (Q1 - 1.5 * IQR)) &
                (transformed_data[col] <= (Q3 + 1.5 * IQR))
                ]

            # Apply normalization
            transformed_data[col] = (transformed_data[col] - transformed_data[col].mean()) / transformed_data[col].std()

        # Handle categorical transformations
        categorical_cols = transformed_data.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            # Apply one-hot encoding
            dummies = pd.get_dummies(transformed_data[col], prefix=col)
            transformed_data = pd.concat([transformed_data, dummies], axis=1)
            transformed_data = transformed_data.drop(col, axis=1)

        return transformed_data

    except Exception as e:
        print(f"Error in transform_data: {str(e)}")
        raise