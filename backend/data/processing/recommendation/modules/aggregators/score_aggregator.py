import logging
from typing import Dict, Any, List
import numpy as np

from ...types.recommendation_types import (
    RecommendationCandidate,
    RankedRecommendation
)

logger = logging.getLogger(__name__)


class ScoreAggregator:
    """
    Aggregates scores from different rankers using configurable strategies.
    Supports weighted average, geometric mean, and custom aggregation rules.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.aggregation_strategies = {
            'weighted_average': self._weighted_average_strategy,
            'geometric_mean': self._geometric_mean_strategy,
            'harmonic_mean': self._harmonic_mean_strategy,
            'percentile_based': self._percentile_based_strategy
        }

    async def aggregate_scores(
            self,
            candidates: List[RecommendationCandidate],
            config: Dict[str, Any]
    ) -> List[RankedRecommendation]:
        """Aggregate scores from different rankers"""
        try:
            strategy_name = config.get('aggregation_strategy', 'weighted_average')
            strategy = self.aggregation_strategies.get(
                strategy_name,
                self._weighted_average_strategy
            )

            ranked_items = []
            for idx, candidate in enumerate(candidates):
                final_score = strategy(candidate.scores, config)
                confidence = self._calculate_confidence(
                    candidate.scores,
                    config
                )

                ranked_items.append(
                    RankedRecommendation(
                        candidate=candidate,
                        final_score=final_score,
                        rank=idx + 1,
                        ranking_factors=candidate.scores.copy(),
                        confidence=confidence
                    )
                )

            # Sort by final score
            ranked_items.sort(key=lambda x: x.final_score, reverse=True)

            # Update ranks after sorting
            for idx, item in enumerate(ranked_items):
                item.rank = idx + 1

            return ranked_items

        except Exception as e:
            self.logger.error(f"Score aggregation failed: {str(e)}")
            return []

    def _weighted_average_strategy(
            self,
            scores: Dict[str, float],
            config: Dict[str, Any]
    ) -> float:
        """Calculate weighted average of scores"""
        try:
            weights = config.get('score_weights', {
                'relevance': 0.3,
                'personalization': 0.3,
                'business': 0.2,
                'diversity': 0.2
            })

            weighted_sum = 0
            weight_sum = 0

            for score_type, score in scores.items():
                if score_type in weights:
                    weight = weights[score_type]
                    weighted_sum += score * weight
                    weight_sum += weight

            return weighted_sum / weight_sum if weight_sum > 0 else 0.0

        except Exception as e:
            self.logger.error(f"Weighted average calculation failed: {str(e)}")
            return 0.0

    def _geometric_mean_strategy(
            self,
            scores: Dict[str, float],
            config: Dict[str, Any]
    ) -> float:
        """Calculate geometric mean of scores"""
        try:
            weights = config.get('score_weights', {})
            score_values = []
            score_weights = []

            for score_type, score in scores.items():
                if score_type in weights:
                    score_values.append(max(score, 1e-10))  # Avoid zero
                    score_weights.append(weights[score_type])

            if not score_values:
                return 0.0

            # Calculate weighted geometric mean
            log_scores = np.log(score_values)
            weighted_sum = np.sum(
                [w * s for w, s in zip(score_weights, log_scores)]
            )
            weight_sum = sum(score_weights)

            return np.exp(weighted_sum / weight_sum) if weight_sum > 0 else 0.0

        except Exception as e:
            self.logger.error(f"Geometric mean calculation failed: {str(e)}")
            return 0.0

    def _harmonic_mean_strategy(
            self,
            scores: Dict[str, float],
            config: Dict[str, Any]
    ) -> float:
        """Calculate harmonic mean of scores"""
        try:
            weights = config.get('score_weights', {})
            reciprocal_sum = 0
            weight_sum = 0

            for score_type, score in scores.items():
                if score_type in weights and score > 0:
                    weight = weights[score_type]
                    reciprocal_sum += weight / max(score, 1e-10)
                    weight_sum += weight

            return weight_sum / reciprocal_sum if reciprocal_sum > 0 else 0.0

        except Exception as e:
            self.logger.error(f"Harmonic mean calculation failed: {str(e)}")
            return 0.0

    def _percentile_based_strategy(
            self,
            scores: Dict[str, float],
            config: Dict[str, Any]
    ) -> float:
        """Calculate score using percentile-based aggregation"""
        try:
            thresholds = config.get('score_thresholds', {})
            weights = config.get('score_weights', {})

            score_sum = 0
            weight_sum = 0

            for score_type, score in scores.items():
                if score_type in weights and score_type in thresholds:
                    threshold = thresholds[score_type]
                    weight = weights[score_type]

                    # Apply threshold-based scaling
                    if score >= threshold:
                        scaled_score = 1.0
                    else:
                        scaled_score = score / threshold

                    score_sum += scaled_score * weight
                    weight_sum += weight

            return score_sum / weight_sum if weight_sum > 0 else 0.0

        except Exception as e:
            self.logger.error(f"Percentile-based calculation failed: {str(e)}")
            return 0.0

    # def _calculate_confidence(
    #         self