# generators/relationship_insights.py
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from scipy import stats
from scipy.cluster import hierarchy


async def detect_relationships(data: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detect relationships between variables including:
    - Correlations
    - Mutual information
    - Hierarchical relationships
    """
    relationships = []

    # Get numeric columns
    numeric_cols = data.select_dtypes(include=[np.number]).columns

    # Correlation insight
    if len(numeric_cols) > 1:
        corr_matrix = data[numeric_cols].corr()

        # Extract significant correlations
        for col1 in numeric_cols:
            for col2 in numeric_cols:
                if col1 < col2:  # Avoid duplicates and self-correlations
                    corr = corr_matrix.loc[col1, col2]
                    if abs(corr) > 0.5:  # Significant correlation threshold
                        relationships.append({
                            'type': 'correlation',
                            'variables': [col1, col2],
                            'confidence': abs(corr),
                            'details': {
                                'correlation': corr,
                                'correlation_type': 'positive' if corr > 0 else 'negative'
                            }
                        })

    # Categorical relationship insight
    categorical_cols = data.select_dtypes(include=['object', 'category']).columns
    for col1 in categorical_cols:
        for col2 in categorical_cols:
            if col1 < col2:
                contingency = pd.crosstab(data[col1], data[col2])
                chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

                if p_value < 0.05:  # Significant relationship
                    strength = np.sqrt(chi2 / (chi2 + len(data)))  # Cramer's V
                    relationships.append({
                        'type': 'categorical_association',
                        'variables': [col1, col2],
                        'confidence': strength,
                        'details': {
                            'chi2_statistic': chi2,
                            'p_value': p_value,
                            'strength': strength
                        }
                    })

    return relationships


async def analyze_relationships(
        detected: List[Dict[str, Any]],
        metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Analyze detected relationships to extract insights"""
    analyzed = []

    for relationship in detected:
        insight = {
            'title': '',
            'description': '',
            'confidence': relationship['confidence'],
            'supporting_data': relationship,
            'tags': ['relationship', 'correlation'],
            'impact': 0.7,
            'urgency': 0.5
        }

        if relationship['type'] == 'correlation':
            vars = relationship['variables']
            corr_type = relationship['details']['correlation_type']
            corr_strength = abs(relationship['details']['correlation'])

            insight['title'] = f"Strong {corr_type} correlation between {vars[0]} and {vars[1]}"
            insight['description'] = (
                f"Found a {corr_type} correlation of {corr_strength:.2f} between "
                f"'{vars[0]}' and '{vars[1]}'. This suggests that as one variable "
                f"{'increases' if corr_type == 'positive' else 'decreases'}, the other "
                f"tends to {'increase' if corr_type == 'positive' else 'decrease'} "
                f"proportionally."
            )

        elif relationship['type'] == 'categorical_association':
            vars = relationship['variables']
            strength = relationship['details']['strength']

            insight['title'] = f"Association between {vars[0]} and {vars[1]}"
            insight['description'] = (
                f"Discovered a significant association between '{vars[0]}' and '{vars[1]}' "
                f"with a strength of {strength:.2f}. This indicates that these categorical "
                f"variables are not independent and certain combinations occur more "
                f"frequently than expected by chance."
            )

        analyzed.append(insight)

    return analyzed


async def validate_relationships(
        analyzed: List[Dict[str, Any]],
        threshold: float
) -> List[Dict[str, Any]]:
    """Validate analyzed relationships against confidence threshold"""
    validated = []

    for insight in analyzed:
        if insight['confidence'] >= threshold:
            # Add validation metadata
            insight['validation'] = {
                'timestamp': pd.Timestamp.now().isoformat(),
                'method': 'relationship_validation',
                'threshold_applied': threshold
            }
            validated.append(insight)

    return validated