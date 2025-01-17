# validators/anomaly_validator.py
import pandas as pd
import numpy as np
from typing import Dict, Any, List


async def validate_anomaly_insight(insight: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate anomaly insights by checking:
    - Statistical significance
    - Anomaly severity
    - Context relevance
    - Detection method reliability
    """
    validation_result = {
        'status': False,
        'score': 0.0,
        'details': {}
    }

    try:
        anomaly_type = insight['supporting_data']['type']

        # Validation criteria for statistical outliers
        if anomaly_type == 'statistical_outlier':
            outlier_values = insight['supporting_data']['details'].get('outlier_values', [])
            z_scores = insight['supporting_data']['details'].get('z_scores', [])

            validation_score = _calculate_outlier_score(
                outlier_count=len(outlier_values),
                max_z_score=max(z_scores) if z_scores else 3.0,
                confidence=insight['confidence']
            )

            validation_result.update({
                'status': validation_score >= 0.7,
                'score': validation_score,
                'details': {
                    'criteria': {
                        'outlier_presence': len(outlier_values) > 0,
                        'severity_check': max(z_scores) >= 3.0 if z_scores else True,
                        'confidence_check': insight['confidence'] >= 0.7
                    }
                }
            })

        # Validation criteria for multivariate anomalies
        elif anomaly_type == 'multivariate_anomaly':
            anomaly_scores = insight['supporting_data']['details'].get('anomaly_scores', [])

            validation_score = _calculate_multivariate_score(
                anomaly_scores=anomaly_scores,
                confidence=insight['confidence']
            )

            validation_result.update({
                'status': validation_score >= 0.7,
                'score': validation_score,
                'details': {
                    'criteria': {
                        'anomaly_presence': len(anomaly_scores) > 0,
                        'severity_check': min(anomaly_scores) < -0.5 if anomaly_scores else True,
                        'confidence_check': insight['confidence'] >= 0.7
                    }
                }
            })

    except Exception as e:
        validation_result['details']['error'] = str(e)

    return validation_result


def _calculate_outlier_score(
        outlier_count: int,
        max_z_score: float,
        confidence: float
) -> float:
    """Calculate validation score for statistical outliers"""
    # Normalize outlier count (cap at 20 for scoring)
    count_score = min(1.0, outlier_count / 20)

    # Z-score severity (normalized to 1.0 at z=5)
    severity_score = min(1.0, max_z_score / 5)

    confidence_score = confidence

    # Weighted average of criteria
    weights = {'count': 0.3, 'severity': 0.4, 'confidence': 0.3}
    return (
            weights['count'] * count_score +
            weights['severity'] * severity_score +
            weights['confidence'] * confidence_score
    )


def _calculate_multivariate_score(
        anomaly_scores: List[float],
        confidence: float
) -> float:
    """Calculate validation score for multivariate anomalies"""
    if not anomaly_scores:
        return 0.0

    # Average anomaly score (normalized)
    avg_score = abs(np.mean(anomaly_scores))
    score_magnitude = min(1.0, avg_score / 0.5)

    # Number of anomalies (normalized)
    count_score = min(1.0, len(anomaly_scores) / 20)

    confidence_score = confidence

    # Weighted average of criteria
    weights = {'magnitude': 0.4, 'count': 0.3, 'confidence': 0.3}
    return (
            weights['magnitude'] * score_magnitude +
            weights['count'] * count_score +
            weights['confidence'] * confidence_score
    )