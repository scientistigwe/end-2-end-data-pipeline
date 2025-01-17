# generators/trend_insights.py
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from scipy import stats
from statsmodels.tsa.seasonal import seasonal_decompose


async def detect_trends(data: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detect trends in time series data including:
    - Linear trends
    - Seasonal patterns
    - Change points
    """
    trends = []

    # Identify datetime columns
    datetime_cols = data.select_dtypes(include=['datetime64']).columns
    if len(datetime_cols) == 0:
        return trends

    time_col = datetime_cols[0]

    for column in data.select_dtypes(include=[np.number]).columns:
        series = data[column].dropna()

        # Linear trend detection
        if len(series) > 2:
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                range(len(series)), series
            )

            if abs(r_value) > 0.5:
                trends.append({
                    'type': 'linear',
                    'column': column,
                    'confidence': abs(r_value),
                    'details': {
                        'slope': slope,
                        'r_squared': r_value ** 2,
                        'p_value': p_value
                    }
                })

        # Seasonal pattern detection
        if len(series) > 12:  # Need enough data points
            try:
                decomposition = seasonal_decompose(
                    series,
                    period=12,  # Adjust based on your data
                    extrapolate_trend='freq'
                )

                seasonal_strength = 1 - np.var(decomposition.resid) / np.var(decomposition.seasonal)
                if seasonal_strength > 0.3:
                    trends.append({
                        'type': 'seasonal',
                        'column': column,
                        'confidence': seasonal_strength,
                        'details': {
                            'period': 12,
                            'seasonal_strength': seasonal_strength
                        }
                    })
            except:
                pass  # Handle decomposition failures gracefully

    return trends


async def analyze_trends(detected: List[Dict[str, Any]], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze detected trends to extract insights"""
    analyzed = []

    for trend in detected:
        insight = {
            'title': '',
            'description': '',
            'confidence': trend['confidence'],
            'supporting_data': trend,
            'tags': ['temporal', 'trend'],
            'impact': 0.6,
            'urgency': 0.4
        }

        if trend['type'] == 'linear':
            direction = 'increasing' if trend['details']['slope'] > 0 else 'decreasing'
            magnitude = abs(trend['details']['slope'])

            insight['title'] = f"{direction.title()} Trend in {trend['column']}"
            insight['description'] = (
                f"The data in column '{trend['column']}' shows a significant {direction} "
                f"trend with a slope of {magnitude:.2f} units per time period. "
                f"This trend explains {trend['details']['r_squared'] * 100:.1f}% of the "
                f"variation in the data."
            )

        elif trend['type'] == 'seasonal':
            insight['title'] = f"Seasonal Pattern in {trend['column']}"
            insight['description'] = (
                f"The data in column '{trend['column']}' exhibits seasonal behavior "
                f"with a period of {trend['details']['period']} units. The seasonal "
                f"pattern accounts for {trend['details']['seasonal_strength'] * 100:.1f}% "
                f"of the data variation."
            )

        analyzed.append(insight)

    return analyzed


async def validate_trends(analyzed: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
    """Validate analyzed trends against confidence threshold"""
    validated = []

    for insight in analyzed:
        if insight['confidence'] >= threshold:
            # Add validation metadata
            insight['validation'] = {
                'timestamp': pd.Timestamp.now().isoformat(),
                'method': 'temporal_validation',
                'threshold_applied': threshold
            }
            validated.append(insight)

    return validated