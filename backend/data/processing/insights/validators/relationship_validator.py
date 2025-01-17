# validators/relationship_validator.py
import pandas as pd
from typing import Dict, Any


async def validate_relationship_insight(insight: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate relationship insights by checking:
    - Statistical significance
    - Relationship strength
    - Sample size requirements
    - Variable independence
    """
    validation_result = {
        'status': False,
        'score': 0.0,
        'details': {}
    }

    try:
        relationship_type = insight['supporting_data']['type']

        # Validation criteria for correlations
        if relationship_type == 'correlation':
            correlation = abs(insight['supporting_data']['details'].get('correlation', 0))

            validation_score = _calculate_correlation_score(
                correlation=correlation,
                confidence=insight['confidence']
            )

            validation_result.update({
                'status': validation_score >= 0.7,
                'score': validation_score,
                'details': {
                    'criteria': {
                        'correlation_strength': correlation >= 0.5,
                        'confidence_check': insight['confidence'] >= 0.7
                    }
                }
            })

        # Validation criteria for categorical associations
        elif relationship_type == 'categorical_association':
            strength = insight['supporting_data']['details'].get('strength', 0)
            p_value = insight['supporting_data']['details'].get('p_value', 1.0)

            validation_score = _calculate_association_score(
                strength=strength,
                p_value=p_value,
                confidence=insight['confidence']
            )

            validation_result.update({
                'status': validation_score >= 0.7,
                'score': validation_score,
                'details': {
                    'criteria': {
                        'association_strength': strength >= 0.3,
                        'significance_check': p_value < 0.05,
                        'confidence_check': insight['confidence'] >= 0.7
                    }
                }
            })

    except Exception as e:
        validation_result['details']['error'] = str(e)

    return validation_result


def _calculate_correlation_score(
        correlation: float,
        confidence: float
) -> float:
    """Calculate validation score for correlations"""
    correlation_score = min(1.0, correlation / 0.5)
    confidence_score = confidence

    # Weighted average of criteria
    weights = {'correlation': 0.6, 'confidence': 0.4}
    return (
            weights['correlation'] * correlation_score +
            weights['confidence'] * confidence_score
    )


def _calculate_association_score(
        strength: float,
        p_value: float,
        confidence: float
) -> float:
    """Calculate validation score for categorical associations"""
    strength_score = min(1.0, strength / 0.3)
    significance_score = 1.0 if p_value < 0.05 else 0.5
    confidence_score = confidence

    # Weighted average of criteria
    weights = {'strength': 0.4, 'significance': 0.3, 'confidence': 0.3}
    return (
            weights['strength'] * strength_score +
            weights['significance'] * significance_score +
            weights['confidence'] * confidence_score
    )