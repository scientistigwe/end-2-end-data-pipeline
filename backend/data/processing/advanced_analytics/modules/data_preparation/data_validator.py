# modules/data_preparation/data_validator.py
import pandas as pd
from typing import Dict, Any


async def validate_data(data: pd.DataFrame) -> Dict[str, Any]:
    """Validate transformed data"""
    validation_results = {
        'status': True,
        'issues': [],
        'metrics': {}
    }

    try:
        # Check for missing values
        missing_vals = data.isnull().sum()
        if missing_vals.any():
            validation_results['issues'].append({
                'type': 'missing_values',
                'details': missing_vals[missing_vals > 0].to_dict()
            })
            validation_results['status'] = False

        # Check for constant columns
        constant_cols = [col for col in data.columns if data[col].nunique() == 1]
        if constant_cols:
            validation_results['issues'].append({
                'type': 'constant_columns',
                'columns': constant_cols
            })
            validation_results['status'] = False

        # Calculate basic metrics
        validation_results['metrics'] = {
            'row_count': len(data),
            'column_count': len(data.columns),
            'missing_percentage': (data.isnull().sum().sum() / (data.shape[0] * data.shape[1])) * 100
        }

        return validation_results

    except Exception as e:
        print(f"Error in validate_data: {str(e)}")
        validation_results['status'] = False
        validation_results['issues'].append({
            'type': 'validation_error',
            'details': str(e)
        })
        return validation_results