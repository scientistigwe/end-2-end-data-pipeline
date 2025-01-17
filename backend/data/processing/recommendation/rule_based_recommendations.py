# backend/data_pipeline/decision/recommendation_engine/rule_based_recommendations.py

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def generate(context_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate recommendations based on predefined rules"""
    try:
        rules = context_data.get('business_rules', {})
        input_data = context_data.get('input_data', {})

        recommendations = []
        for rule_name, rule_config in rules.items():
            if _check_rule_applicability(rule_config, input_data):
                recommendations.append({
                    'rule_name': rule_name,
                    'action': rule_config.get('action'),
                    'confidence': rule_config.get('confidence', 0.8),
                    'reason': rule_config.get('reason', 'Rule-based recommendation')
                })

        return recommendations
    except Exception as e:
        logger.error(f"Error in rule-based recommendation generation: {e}")
        return []


def validate(recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate rule-based recommendations"""
    try:
        valid_recommendations = []
        for rec in recommendations:
            if rec.get('confidence', 0) > 0.5:  # Basic confidence threshold
                valid_recommendations.append(rec)
        return valid_recommendations
    except Exception as e:
        logger.error(f"Error in rule-based recommendation validation: {e}")
        return []


def _check_rule_applicability(rule_config: Dict[str, Any],
                              input_data: Dict[str, Any]) -> bool:
    """Check if a rule is applicable to the input data"""
    try:
        conditions = rule_config.get('conditions', {})
        return all(
            input_data.get(key) == value
            for key, value in conditions.items()
        )
    except Exception:
        return False

