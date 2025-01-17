# generators/business_goal_insight.py
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from ..types.insight_types import InsightType, InsightCategory, InsightPriority


async def detect_business_insights(
        data: pd.DataFrame,
        business_goal: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Detect insights based on specific business goals and criteria
    submitted through the business goal form.
    """
    insights = []

    try:
        # Extract key components from business goal
        metrics = business_goal.get('metrics', [])
        success_criteria = business_goal.get('successCriteria', [])
        constraints = business_goal.get('constraints', [])
        questions = business_goal.get('questions', [])

        # Analyze metrics against success criteria
        for metric in metrics:
            matching_criteria = [
                criterion for criterion in success_criteria
                if criterion['metric'].lower() == metric.lower()
            ]

            for criterion in matching_criteria:
                target = float(criterion['target'])
                direction = criterion['direction']

                if metric in data.columns:
                    current_value = data[metric].mean()
                    performance_gap = (
                        ((current_value - target) / target * 100)
                        if target != 0 else float('inf')
                    )

                    # Check if performance aligns with desired direction
                    meets_direction = (
                            (direction == 'increase' and performance_gap > 0) or
                            (direction == 'decrease' and performance_gap < 0) or
                            (direction == 'maintain' and abs(performance_gap) <= 5)
                    )

                    insights.append({
                        'type': 'metric_performance',
                        'metric': metric,
                        'confidence': 0.9,
                        'details': {
                            'current_value': current_value,
                            'target_value': target,
                            'direction': direction,
                            'performance_gap': performance_gap,
                            'meets_direction': meets_direction
                        }
                    })

        # Analyze grouping patterns
        groupings = business_goal.get('groupings', [])
        for group in groupings:
            if group in data.columns:
                group_stats = data.groupby(group).agg({
                    metric: ['mean', 'std', 'count']
                    for metric in metrics
                    if metric in data.columns
                }).reset_index()

                for metric in metrics:
                    if metric in data.columns:
                        # Identify significant variations
                        mean_val = group_stats[(metric, 'mean')].mean()
                        std_val = group_stats[(metric, 'std')].mean()

                        significant_groups = group_stats[
                            abs(group_stats[(metric, 'mean')] - mean_val) > std_val
                            ]

                        if not significant_groups.empty:
                            insights.append({
                                'type': 'group_variation',
                                'metric': metric,
                                'grouping': group,
                                'confidence': 0.85,
                                'details': {
                                    'significant_groups': significant_groups.to_dict('records'),
                                    'mean_value': mean_val,
                                    'std_value': std_val
                                }
                            })

        # Question-based insights
        for question in questions:
            # Analyze based on question type (you can extend this based on common question patterns)
            if 'trend' in question.lower():
                for metric in metrics:
                    if metric in data.columns:
                        trend_analysis = analyze_trend_for_question(data[metric])
                        if trend_analysis:
                            insights.append({
                                'type': 'question_based',
                                'metric': metric,
                                'question': question,
                                'confidence': 0.8,
                                'details': trend_analysis
                            })

            elif 'compare' in question.lower() or 'versus' in question.lower():
                comparison_insights = analyze_comparisons(data, metrics, groupings)
                insights.extend(comparison_insights)

    except Exception as e:
        print(f"Error in detect_business_insights: {str(e)}")

    return insights


async def analyze_business_insights(
        detected: List[Dict[str, Any]],
        metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Analyze detected business insights to extract meaningful findings"""
    analyzed = []

    for insight in detected:
        insight_analysis = {
            'title': '',
            'description': '',
            'confidence': insight['confidence'],
            'supporting_data': insight,
            'tags': ['business', 'goal_aligned'],
            'impact': 0.8,
            'urgency': 0.7
        }

        if insight['type'] == 'metric_performance':
            gap = insight['details']['performance_gap']
            direction = insight['details']['direction']
            meets = insight['details']['meets_direction']

            insight_analysis.update({
                'title': f"Performance Gap Analysis: {insight['metric']}",
                'description': (
                    f"The {insight['metric']} is currently "
                    f"{'meeting' if meets else 'not meeting'} the target. "
                    f"There is a {abs(gap):.1f}% {direction} gap from the target. "
                    f"This requires {'immediate' if abs(gap) > 20 else 'moderate'} attention."
                )
            })

        elif insight['type'] == 'group_variation':
            insight_analysis.update({
                'title': f"Significant Variations in {insight['metric']} by {insight['grouping']}",
                'description': (
                    f"Identified significant variations in {insight['metric']} "
                    f"across different {insight['grouping']} groups. "
                    f"Some groups deviate more than one standard deviation "
                    f"from the mean, indicating potential areas for focus."
                )
            })

        elif insight['type'] == 'question_based':
            insight_analysis.update({
                'title': f"Analysis: {insight['question']}",
                'description': generate_question_based_description(insight)
            })

        analyzed.append(insight_analysis)

    return analyzed


async def validate_business_insights(
        analyzed: List[Dict[str, Any]],
        threshold: float
) -> List[Dict[str, Any]]:
    """Validate analyzed business insights against confidence threshold"""
    validated = []

    for insight in analyzed:
        if insight['confidence'] >= threshold:
            # Add validation metadata
            insight['validation'] = {
                'timestamp': pd.Timestamp.now().isoformat(),
                'method': 'business_goal_validation',
                'threshold_applied': threshold
            }
            validated.append(insight)

    return validated


def analyze_trend_for_question(series: pd.Series) -> Optional[Dict[str, Any]]:
    """Analyze trend for a specific metric"""
    try:
        slope, intercept = np.polyfit(range(len(series)), series, 1)
        return {
            'trend_type': 'increasing' if slope > 0 else 'decreasing',
            'slope': slope,
            'significance': abs(slope) / series.mean() if series.mean() != 0 else 0
        }
    except:
        return None


def analyze_comparisons(
        data: pd.DataFrame,
        metrics: List[str],
        groupings: List[str]
) -> List[Dict[str, Any]]:
    """Analyze comparisons between groups"""
    comparison_insights = []

    for metric in metrics:
        if metric not in data.columns:
            continue

        for group in groupings:
            if group not in data.columns:
                continue

            group_stats = data.groupby(group)[metric].agg(['mean', 'std'])

            # Find significant differences between groups
            overall_mean = group_stats['mean'].mean()

            significant_diffs = group_stats[
                abs(group_stats['mean'] - overall_mean) > group_stats['std']
                ]

            if not significant_diffs.empty:
                comparison_insights.append({
                    'type': 'comparison',
                    'metric': metric,
                    'group': group,
                    'confidence': 0.85,
                    'details': {
                        'significant_differences': significant_diffs.to_dict('index')
                    }
                })

    return comparison_insights


def generate_question_based_description(insight: Dict[str, Any]) -> str:
    """Generate description for question-based insights"""
    if 'trend' in insight['question'].lower():
        trend = insight['details']['trend_type']
        significance = insight['details']['significance']

        return (
            f"Analysis shows a {trend} trend with "
            f"{'high' if significance > 0.1 else 'moderate' if significance > 0.05 else 'low'} "
            f"significance. The rate of change is {abs(insight['details']['slope']):.2f} "
            f"units per period."
        )

    return "Analysis complete. Please review the detailed findings."