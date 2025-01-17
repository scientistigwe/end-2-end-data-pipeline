# generators/pattern_insights.py
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from scipy import stats


async def detect_patterns(data: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detect patterns in data including:
    - Repeated sequences
    - Value distributions
    - Cyclic patterns
    """
    patterns = []

    # Check for periodic patterns in numeric columns
    for column in data.select_dtypes(include=[np.number]).columns:
        series = data[column].dropna()

        # Check for value distribution patterns
        if len(series) > 10:
            # Test for normal distribution
            stat, p_value = stats.normaltest(series)
            if p_value > 0.05:
                patterns.append({
                    'type': 'distribution',
                    'subtype': 'normal',
                    'column': column,
                    'confidence': 0.8,
                    'details': {
                        'mean': series.mean(),
                        'std': series.std(),
                        'p_value': p_value
                    }
                })

        # Check for repeating sequences
        if len(series) > 20:
            autocorr = pd.Series(series).autocorr(lag=1)
            if abs(autocorr) > 0.7:
                patterns.append({
                    'type': 'sequence',
                    'subtype': 'repeating',
                    'column': column,
                    'confidence': abs(autocorr),
                    'details': {
                        'autocorrelation': autocorr
                    }
                })

    return patterns


async def analyze_patterns(detected: List[Dict[str, Any]], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze detected patterns to extract insights"""
    analyzed = []

    for pattern in detected:
        insight = {
            'title': '',
            'description': '',
            'confidence': pattern['confidence'],
            'supporting_data': pattern,
            'tags': ['statistical', 'pattern'],
            'impact': 0.5,
            'urgency': 0.3
        }

        if pattern['type'] == 'distribution':
            insight['title'] = f"Normal Distribution in {pattern['column']}"
            insight['description'] = (
                f"The data in column '{pattern['column']}' follows a normal distribution "
                f"with mean {pattern['details']['mean']:.2f} and standard deviation "
                f"{pattern['details']['std']:.2f}. This suggests natural variation "
                f"around a central tendency."
            )

        elif pattern['type'] == 'sequence':
            insight['title'] = f"Repeating Pattern in {pattern['column']}"
            insight['description'] = (
                f"The data in column '{pattern['column']}' shows a strong repeating pattern "
                f"with autocorrelation of {pattern['details']['autocorrelation']:.2f}. "
                f"This suggests cyclical behavior or seasonal effects."
            )

        analyzed.append(insight)

    return analyzed


async def validate_patterns(analyzed: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
    """Validate analyzed patterns against confidence threshold"""
    validated = []

    for insight in analyzed:
        if insight['confidence'] >= threshold:
            # Add validation metadata
            insight['validation'] = {
                'timestamp': pd.Timestamp.now().isoformat(),
                'method': 'statistical_validation',
                'threshold_applied': threshold
            }
            validated.append(insight)

    return validated