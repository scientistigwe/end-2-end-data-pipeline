# validators/business_goal_validator.py
from typing import Dict, Any


async def validate_business_goal_insight(insight: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate business goal insights by checking:
    - Alignment with business objectives
    - Data quality
    - Statistical significance
    - Impact assessment
    """
    validation_result = {
        'status': False,
        'score': 0.0,
        'details': {}
    }

    try:
        # Calculate validation score based on multiple criteria
        confidence_score = insight.get('confidence', 0)
        impact_score = insight.get('impact', 0)
        data_quality_score = _assess_data_quality(insight)
        business_alignment_score = _assess_business_alignment(insight)

        # Weighted validation score
        validation_score = (
                confidence_score * 0.3 +
                impact_score * 0.3 +
                data_quality_score * 0.2 +
                business_alignment_score * 0.2
        )

        validation_result.update({
            'status': validation_score >= 0.7,
            'score': validation_score,
            'details': {
                'confidence_score': confidence_score,
                'impact_score': impact_score,
                'data_quality_score': data_quality_score,
                'business_alignment_score': business_alignment_score
            }
        })

    except Exception as e:
        validation_result['details']['error'] = str(e)

    return validation_result


def _assess_data_quality(insight: Dict[str, Any]) -> float:
    """Assess the quality of data supporting the insight"""
    try:
        supporting_data = insight.get('supporting_data', {})
        sample_size = supporting_data.get('sample_size', 0)
        completeness = supporting_data.get('completeness', 0)

        return min(1.0, (sample_size / 100 + completeness) / 2)
    except:
        return 0.0


def _assess_business_alignment(insight: Dict[str, Any]) -> float:
    """Assess how well the insight aligns with business goals"""
    try:
        metadata = insight.get('metadata', {})
        goal_alignment = metadata.get('goal_alignment', 0)
        kpi_relevance = metadata.get('kpi_relevance', 0)

        return (goal_alignment + kpi_relevance) / 2
    except:
        return 0.0