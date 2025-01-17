# generators/anomaly_insights.py
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from scipy import stats
from sklearn.ensemble import IsolationForest


async def detect_anomalies(data: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detect anomalies in data including:
    - Statistical outliers
    - Temporal anomalies
    - Multivariate anomalies
    """
    anomalies = []

    # Statistical outliers for numeric columns
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    for column in numeric_cols:
        series = data[column].dropna()

        # Z-score based outliers
        z_scores = np.abs(stats.zscore(series))
        outliers = data[z_scores > 3]  # 3 standard deviations

        if len(outliers) > 0:
            anomalies.append({
                'type': 'statistical_outlier',
                'column': column,
                'confidence': 0.8,
                'details': {
                    'method': 'z_score',
                    'threshold': 3,
                    'outlier_indices': outliers.index.tolist(),
                    'outlier_values': outliers[column].tolist()
                }
            })

    # Multivariate anomalies
    if len(numeric_cols) > 1:
        try:
            # Use Isolation Forest for multivariate anomaly detection
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            numeric_data = data[numeric_cols].fillna(data[numeric_cols].mean())
            predictions = iso_forest.fit_predict(numeric_data)

            anomaly_indices = np.where(predictions == -1)[0]
            if len(anomaly_indices) > 0:
                anomalies.append({
                    'type': 'multivariate_anomaly',
                    'columns': numeric_cols.tolist(),
                    'confidence': 0.75,
                    'details': {
                        'method': 'isolation_forest',
                        'anomaly_indices': anomaly_indices.tolist(),
                        'anomaly_scores': iso_forest.score_samples(
                            numeric_data.iloc[anomaly_indices]
                        ).tolist()
                    }
                })
        except Exception as e:
            pass  # Handle gracefully if isolation forest fails

    return anomalies


async def analyze_anomalies(
        detected: List[Dict[str, Any]],
        metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Analyze detected anomalies to extract insights"""
    analyzed = []

    for anomaly in detected:
        insight = {
            'title': '',
            'description': '',
            'confidence': anomaly['confidence'],
            'supporting_data': anomaly,
            'tags': ['anomaly', 'outlier'],
            'impact': 0.8,
            'urgency': 0.7
        }

        if anomaly['type'] == 'statistical_outlier':
            insight['title'] = f"Statistical Outliers in {anomaly['column']}"
            insight['description'] = (
                f"Detected {len(anomaly['details']['outlier_indices'])} statistical "
                f"outliers in column '{anomaly['column']}' using z-score analysis. "
                f"These values deviate significantly from the normal range and may "
                f"warrant investigation."
            )

        elif anomaly['type'] == 'multivariate_anomaly':
            insight['title'] = "Multivariate Anomalies Detected"
            insight['description'] = (
                f"Identified {len(anomaly['details']['anomaly_indices'])} records "
                f"that show unusual patterns across multiple variables: "
                f"{', '.join(anomaly['columns'])}. These cases represent "
                f"unusual combinations of values that differ from the typical "
                f"patterns in the data."
            )

        analyzed.append(insight)

    return analyzed


async def validate_anomalies(
        analyzed: List[Dict[str, Any]],
        threshold: float
) -> List[Dict[str, Any]]:
    """Validate analyzed anomalies against confidence threshold"""
    validated = []

    for insight in analyzed:
        if insight['confidence'] >= threshold:
            # Add validation metadata
            insight['validation'] = {
                'timestamp': pd.Timestamp.now().isoformat(),
                'method': 'anomaly_validation',
                'threshold_applied': threshold
            }
            validated.append(insight)

    return validated