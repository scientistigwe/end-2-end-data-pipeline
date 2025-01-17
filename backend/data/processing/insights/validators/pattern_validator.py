# validators/pattern_validator.py
import pandas as pd
from typing import Dict, Any


async def validate_pattern_insight(insight: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate pattern insights by checking:
    - Statistical significance
    - Pattern strength
    - Data quality requirements
    """
    validation_result = {
        'status': False,
        'score': 0.0,
        'details': {}
    }

    try:
        pattern_type = insight['supporting_data']['type']

        # Validation criteria for distribution patterns
        if pattern_type == 'distribution':
            p_value = insight['supporting_data']['details'].get('p_value', 1.0)
            sample_size = len(insight['supporting_data'].get('details', {}).get('data', []))

            validation_score = _calculate_distribution_score(
                p_value=p_value,
                sample_size=sample_size,
                confidence=insight['confidence']
            )

            validation_result.update({
                'status': validation_score >= 0.7,
                'score': validation_score,
                'details': {
                    'criteria': {
                        'p_value_check': p_value < 0.05,
                        'sample_size_check': sample_size >= 30,
                        'confidence_check': insight['confidence'] >= 0.8
                    }
                }
            })

        # Validation criteria for sequence patterns
        elif pattern_type == 'sequence':
            autocorr = abs(insight['supporting_data']['details'].get('autocorrelation', 0))

            validation_score = _calculate_sequence_score(
                autocorrelation=autocorr,
                confidence=insight['confidence']
            )

            validation_result.update({
                'status': validation_score >= 0.7,
                'score': validation_score,
                'details': {
                    'criteria': {
                        'autocorrelation_check': autocorr >= 0.7,
                        'confidence_check': insight['confidence'] >= 0.8
                    }
                }
            })

    except Exception as e:
        validation_result['details']['error'] = str(e)

    return validation_result


def _calculate_distribution_score(
        p_value: float,
        sample_size: int,
        confidence: float
) -> float:
    """Calculate validation score for distribution patterns"""
    p_value_score = 1.0 if p_value < 0.05 else 0.5
    sample_score = min(1.0, sample_size / 100)
    confidence_score = confidence

    # Weighted average of criteria
    weights = {'p_value': 0.4, 'sample': 0.3, 'confidence': 0.3}
    return (
            weights['p_value'] * p_value_score +
            weights['sample'] * sample_score +
            weights['confidence'] * confidence_score
    )


def _calculate_sequence_score(
        autocorrelation: float,
        confidence: float
) -> float:
    """Calculate validation score for sequence patterns"""
    autocorr_score = min(1.0, autocorrelation)
    confidence_score = confidence

    # Weighted average of criteria
    weights = {'autocorr': 0.6, 'confidence': 0.4}
    return (
            weights['autocorr'] * autocorr_score +
            weights['confidence'] * confidence_score
    )