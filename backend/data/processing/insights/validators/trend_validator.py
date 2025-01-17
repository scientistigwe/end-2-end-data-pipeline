# validators/trend_validator.py
import pandas as pd
from typing import Dict, Any


async def validate_trend_insight(insight: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate trend insights by checking:
    - Statistical significance
    - Trend strength
    - Time series requirements
    """
    validation_result = {
        'status': False,
        'score': 0.0,
        'details': {}
    }

    try:
        trend_type = insight['supporting_data']['type']

        # Validation criteria for linear trends
        if trend_type == 'linear':
            r_squared = insight['supporting_data']['details'].get('r_squared', 0)
            p_value = insight['supporting_data']['details'].get('p_value', 1.0)

            validation_score = _calculate_linear_trend_score(
                r_squared=r_squared,
                p_value=p_value,
                confidence=insight['confidence']
            )

            validation_result.update({
                'status': validation_score >= 0.7,
                'score': validation_score,
                'details': {
                    'criteria': {
                        'r_squared_check': r_squared >= 0.3,
                        'significance_check': p_value < 0.05,
                        'confidence_check': insight['confidence'] >= 0.7
                    }
                }
            })

        # Validation criteria for seasonal trends
        elif trend_type == 'seasonal':
            seasonal_strength = insight['supporting_data']['details'].get('seasonal_strength', 0)

            validation_score = _calculate_seasonal_trend_score(
                seasonal_strength=seasonal_strength,
                confidence=insight['confidence']
            )

            validation_result.update({
                'status': validation_score >= 0.7,
                'score': validation_score,
                'details': {
                    'criteria': {
                        'seasonal_strength_check': seasonal_strength >= 0.3,
                        'confidence_check': insight['confidence'] >= 0.7
                    }
                }
            })

    except Exception as e:
        validation_result['details']['error'] = str(e)

    return validation_result


def _calculate_linear_trend_score(
        r_squared: float,
        p_value: float,
        confidence: float
) -> float:
    """Calculate validation score for linear trends"""
    r_squared_score = min(1.0, r_squared / 0.3)
    significance_score = 1.0 if p_value < 0.05 else 0.5
    confidence_score = confidence

    # Weighted average of criteria
    weights = {'r_squared': 0.4, 'significance': 0.3, 'confidence': 0.3}
    return (
            weights['r_squared'] * r_squared_score +
            weights['significance'] * significance_score +
            weights['confidence'] * confidence_score
    )


def _calculate_seasonal_trend_score(
        seasonal_strength: float,
        confidence: float
) -> float:
    """Calculate validation score for seasonal trends"""
    strength_score = min(1.0, seasonal_strength / 0.3)
    confidence_score = confidence

    # Weighted average of criteria
    weights = {'strength': 0.6, 'confidence': 0.4}
    return (
            weights['strength'] * strength_score +
            weights['confidence'] * confidence_score
    )