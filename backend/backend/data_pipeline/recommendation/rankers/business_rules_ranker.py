# backend/data_pipeline/recommendation/rankers/business_rules_ranker.py

from typing import Dict, Any, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def rank(items: List[Dict[str, Any]], user_id: str,
         context_type: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Rank items based on business rules"""
    try:
        business_rules = metadata.get('business_rules', {})

        # Apply business rules and calculate scores
        for item in items:
            business_score = _apply_business_rules(
                item,
                business_rules,
                context_type,
                metadata.get('current_time', datetime.now())
            )
            item['business_score'] = business_score

        # Combine with other scores and rank
        ranked_items = _apply_final_ranking(items, business_rules)

        return ranked_items

    except Exception as e:
        logger.error(f"Error in business rules ranking: {str(e)}")
        return items


def _apply_business_rules(item: Dict[str, Any],
                          rules: Dict[str, Any],
                          context_type: str,
                          current_time: datetime) -> float:
    """Apply business rules to calculate score"""
    try:
        score = 1.0  # Base score

        # Apply promotion rules
        if _check_promotion_rules(item, rules.get('promotions', {})):
            score *= 1.2

        # Apply inventory rules
        if _check_inventory_rules(item, rules.get('inventory', {})):
            score *= 0.8

        # Apply seasonal rules
        if _check_seasonal_rules(item, rules.get('seasonal', {}), current_time):
            score *= 1.1

        # Apply category boost rules
        category_boost = _apply_category_boost(
            item,
            rules.get('category_boost', {})
        )
        score *= category_boost

        return score

    except Exception as e:
        logger.error(f"Error applying business rules: {str(e)}")
        return 1.0


def _check_promotion_rules(item: Dict[str, Any],
                           promotion_rules: Dict[str, Any]) -> bool:
    """Check if item matches promotion rules"""
    try:
        if not promotion_rules:
            return False

        item_id = item.get('item_id')
        if not item_id:
            return False

        # Check active promotions
        active_promotions = promotion_rules.get('active_promotions', {})
        return item_id in active_promotions

    except Exception as e:
        logger.error(f"Error in promotion rules: {str(e)}")
        return False


def _check_inventory_rules(item: Dict[str, Any],
                           inventory_rules: Dict[str, Any]) -> bool:
    """Check if item matches inventory rules"""
    try:
        if not inventory_rules:
            return False

        inventory_level = item.get('inventory_level', 0)
        threshold = inventory_rules.get('low_stock_threshold', 10)

        return inventory_level < threshold

    except Exception as e:
        logger.error(f"Error in inventory rules: {str(e)}")
        return False


def _check_seasonal_rules(item: Dict[str, Any],
                          seasonal_rules: Dict[str, Any],
                          current_time: datetime) -> bool:
    """Check if item matches seasonal rules"""
    try:
        if not seasonal_rules:
            return False

        current_month = current_time.month
        seasonal_items = seasonal_rules.get(str(current_month), [])

        return item.get('item_id') in seasonal_items

    except Exception as e:
        logger.error(f"Error in seasonal rules: {str(e)}")
        return False


def _apply_category_boost(item: Dict[str, Any],
                          category_rules: Dict[str, Any]) -> float:
    """Apply category boost multiplier"""
    try:
        if not category_rules:
            return 1.0

        item_category = item.get('category')
        if not item_category:
            return 1.0

        return category_rules.get(item_category, 1.0)

    except Exception as e:
        logger.error(f"Error in category boost: {str(e)}")
        return 1.0


def _apply_final_ranking(items: List[Dict[str, Any]],
                         rules: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply final ranking combining all scores"""
    try:
        # Get score weights from rules
        weights = rules.get('score_weights', {
            'relevance': 0.3,
            'personalization': 0.3,
            'business': 0.4
        })

        # Calculate final scores
        for item in items:
            item['final_score'] = (
                    item.get('relevance_score', 0) * weights['relevance'] +
                    item.get('personalization_score', 0) * weights['personalization'] +
                    item.get('business_score', 0) * weights['business']
            )

        # Sort by final score
        return sorted(items, key=lambda x: x.get('final_score', 0), reverse=True)

    except Exception as e:
        logger.error(f"Error in final ranking: {str(e)}")
        return items