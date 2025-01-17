import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...types.recommendation_types import RecommendationCandidate

logger = logging.getLogger(__name__)


class BusinessRulesRanker:
    """
    Ranks recommendations based on business rules and constraints.
    Handles promotions, inventory, seasonality, and other business logic.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def rank(
            self,
            candidates: List[RecommendationCandidate],
            context: Dict[str, Any]
    ) -> List[RecommendationCandidate]:
        """Rank candidates based on business rules"""
        try:
            business_config = context.get('business_config', {})
            current_time = datetime.now()

            # Apply business rules and calculate scores
            for candidate in candidates:
                business_score = self._calculate_business_score(
                    candidate,
                    business_config,
                    current_time
                )
                candidate.scores['business'] = business_score

            # Sort by business score
            return sorted(
                candidates,
                key=lambda x: x.scores.get('business', 0),
                reverse=True
            )

        except Exception as e:
            self.logger.error(f"Business rules ranking failed: {str(e)}")
            return candidates

    def _calculate_business_score(
            self,
            candidate: RecommendationCandidate,
            config: Dict[str, Any],
            current_time: datetime
    ) -> float:
        """Calculate business rules score for a candidate"""
        try:
            score_components = {
                'promotion': self._evaluate_promotions(
                    candidate, config.get('promotions', {})
                ),
                'inventory': self._evaluate_inventory(
                    candidate, config.get('inventory', {})
                ),
                'margin': self._evaluate_margin(
                    candidate, config.get('margin', {})
                ),
                'seasonal': self._evaluate_seasonal_rules(
                    candidate, config.get('seasonal', {}), current_time
                ),
                'strategic': self._evaluate_strategic_rules(
                    candidate, config.get('strategic', {})
                )
            }

            # Apply component weights
            weights = config.get('component_weights', {
                'promotion': 0.3,
                'inventory': 0.2,
                'margin': 0.2,
                'seasonal': 0.15,
                'strategic': 0.15
            })

            final_score = sum(
                score * weights.get(component, 0.1)
                for component, score in score_components.items()
            )

            return min(max(final_score, 0.0), 1.0)  # Normalize to [0,1]

        except Exception as e:
            self.logger.error(f"Business score calculation failed: {str(e)}")
            return 0.5  # Default neutral score

    def _evaluate_promotions(
            self,
            candidate: RecommendationCandidate,
            promo_config: Dict[str, Any]
    ) -> float:
        """Evaluate promotion-related rules"""
        try:
            item_id = candidate.item_id
            features = candidate.features

            # Check active promotions
            active_promos = promo_config.get('active_promotions', {})
            if item_id in active_promos:
                promo_data = active_promos[item_id]

                # Calculate promotion score based on priority and discount
                priority = promo_data.get('priority', 1)
                discount = promo_data.get('discount_percentage', 0)

                return min((priority * 0.4 + discount * 0.6) / 100, 1.0)

            # Check category-level promotions
            category = features.get('category')
            if category in promo_config.get('category_promotions', {}):
                return 0.7

            return 0.3  # Base score for non-promoted items

        except Exception as e:
            self.logger.error(f"Promotion evaluation failed: {str(e)}")
            return 0.3

    def _evaluate_inventory(
            self,
            candidate: RecommendationCandidate,
            inventory_config: Dict[str, Any]
    ) -> float:
        """Evaluate inventory-related rules"""
        try:
            features = candidate.features
            inventory_level = features.get('inventory_level', 0)

            # Get thresholds
            low_threshold = inventory_config.get('low_threshold', 10)
            optimal_threshold = inventory_config.get('optimal_threshold', 50)
            high_threshold = inventory_config.get('high_threshold', 100)

            if inventory_level <= low_threshold:
                return 0.3  # Reduce score for low inventory
            elif inventory_level <= optimal_threshold:
                return 1.0  # Optimal inventory level
            elif inventory_level <= high_threshold:
                return 0.8  # Slightly reduce score for higher inventory
            else:
                return 0.6  # Reduce score for excess inventory

        except Exception as e:
            self.logger.error(f"Inventory evaluation failed: {str(e)}")
            return 0.5

    def _evaluate_margin(
            self,
            candidate: RecommendationCandidate,
            margin_config: Dict[str, Any]
    ) -> float:
        """Evaluate margin-related rules"""
        try:
            features = candidate.features
            margin = features.get('margin_percentage', 0)

            # Get margin thresholds
            target_margin = margin_config.get('target_margin', 30)
            min_margin = margin_config.get('min_margin', 10)

            if margin < min_margin:
                return 0.1
            elif margin >= target_margin:
                return 1.0
            else:
                # Linear interpolation between min and target margin
                return 0.1 + 0.9 * (margin - min_margin) / (target_margin - min_margin)

        except Exception as e:
            self.logger.error(f"Margin evaluation failed: {str(e)}")
            return 0.5

    def _evaluate_seasonal_rules(
            self,
            candidate: RecommendationCandidate,
            seasonal_config: Dict[str, Any],
            current_time: datetime
    ) -> float:
        """Evaluate seasonal rules"""
        try:
            features = candidate.features
            category = features.get('category')

            # Get seasonal categories for current month
            current_month = current_time.month
            seasonal_categories = seasonal_config.get(str(current_month), [])

            if category in seasonal_categories:
                return 1.0

            # Check upcoming seasons
            next_month = (current_month % 12) + 1
            upcoming_categories = seasonal_config.get(str(next_month), [])

            if category in upcoming_categories:
                return 0.7

            return 0.4

        except Exception as e:
            self.logger.error(f"Seasonal evaluation failed: {str(e)}")
            return 0.5

    def _evaluate_strategic_rules(
            self,
            candidate: RecommendationCandidate,
            strategic_config: Dict[str, Any]
    ) -> float:
        """Evaluate strategic business rules"""
        try:
            features = candidate.features
            category = features.get('category')
            brand = features.get('brand')

            score = 0.5  # Base score

            # Priority categories
            if category in strategic_config.get('priority_categories', []):
                score += 0.3

            # Strategic brands
            if brand in strategic_config.get('strategic_brands', []):
                score += 0.2

            # New product boost
            if features.get('is_new_product', False):
                score += 0.2

            return min(score, 1.0)

        except Exception as e:
            self.logger.error(f"Strategic rules evaluation failed: {str(e)}")
            return 0.5