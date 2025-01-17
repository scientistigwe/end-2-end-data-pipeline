# backend/data_pipeline/recommendation/modules/rankers/relevance_ranker.py

import logging
from typing import Dict, Any, List

from ...types.recommendation_types import RecommendationCandidate

logger = logging.getLogger(__name__)


class RelevanceRanker:
    """
    Ranks recommendations based on relevance to user query/context.
    """

    async def rank(
            self,
            candidates: List[RecommendationCandidate],
            context: Dict[str, Any]
    ) -> List[RecommendationCandidate]:
        """Rank candidates based on relevance criteria"""
        try:
            relevance_weights = context.get('relevance_weights', {
                'semantic_similarity': 0.4,
                'feature_match': 0.3,
                'freshness': 0.2,
                'popularity': 0.1
            })

            # Calculate relevance scores
            scored_candidates = []
            for candidate in candidates:
                relevance_score = self._calculate_relevance_score(
                    candidate,
                    context,
                    relevance_weights
                )

                # Add relevance score to candidate
                candidate.scores['relevance'] = relevance_score
                scored_candidates.append(candidate)

            # Sort by relevance score
            return sorted(
                scored_candidates,
                key=lambda x: x.scores['relevance'],
                reverse=True
            )

        except Exception as e:
            logger.error(f"Relevance ranking failed: {str(e)}")
            return candidates

    def _calculate_relevance_score(
            self,
            candidate: RecommendationCandidate,
            context: Dict[str, Any],
            weights: Dict[str, float]
    ) -> float:
        """Calculate overall relevance score"""
        try:
            scores = {
                'semantic_similarity': self._calculate_semantic_similarity(
                    candidate, context
                ),
                'feature_match': self._calculate_feature_match(
                    candidate, context
                ),
                'freshness': self._calculate_freshness(
                    candidate, context
                ),
                'popularity': self._calculate_popularity(
                    candidate, context
                )
            }

            weighted_score = sum(
                score * weights.get(score_type, 0)
                for score_type, score in scores.items()
            )

            return weighted_score

        except Exception as e:
            logger.error(f"Relevance score calculation failed: {str(e)}")
            return 0.0

    def _calculate_semantic_similarity(
            self,
            candidate: RecommendationCandidate,
            context: Dict[str, Any]
    ) -> float:
        """Calculate semantic similarity score"""
        try:
            query_terms = set(context.get('query_terms', []))
            item_terms = set(
                term.lower()
                for term in candidate.features.get('terms', [])
            )

            if not query_terms or not item_terms:
                return 0.0

            # Calculate Jaccard similarity
            intersection = len(query_terms & item_terms)
            union = len(query_terms | item_terms)

            return intersection / union if union > 0 else 0.0

        except Exception as e:
            logger.error(f"Semantic similarity calculation failed: {str(e)}")
            return 0.0

    def _calculate_feature_match(
            self,
            candidate: RecommendationCandidate,
            context: Dict[str, Any]
    ) -> float:
        """Calculate feature match score"""
        try:
            required_features = context.get('required_features', {})
            if not required_features:
                return 1.0

            matching_features = 0
            for feature, value in required_features.items():
                if (
                        feature in candidate.features and
                        candidate.features[feature] == value
                ):
                    matching_features += 1

            return matching_features / len(required_features)

        except Exception as e:
            logger.error(f"Feature match calculation failed: {str(e)}")
            return 0.0

    def _calculate_freshness(
            self,
            candidate: RecommendationCandidate,
            context: Dict[str, Any]
    ) -> float:
        """Calculate freshness score"""
        try:
            if 'timestamp' not in candidate.features:
                return 0.0

            current_time = context.get('current_time', datetime.now())
            item_time = candidate.features['timestamp']

            # Convert to hours difference
            time_diff = (current_time - item_time).total_seconds() / 3600

            # Exponential decay
            decay_rate = context.get('freshness_decay_rate', 0.1)
            return math.exp(-decay_rate * time_diff)

        except Exception as e:
            logger.error(f"Freshness calculation failed: {str(e)}")
            return 0.0

    def _calculate_popularity(
            self,
            candidate: RecommendationCandidate,
            context: Dict[str, Any]
    ) -> float:
        """Calculate popularity score"""
        try:
            views = candidate.features.get('views', 0)
            interactions = candidate.features.get('interactions', 0)

            if views == 0 and interactions == 0:
                return 0.0

            # Calculate engagement rate
            engagement_rate = interactions / views if views > 0 else 0

            # Normalize using log scale
            normalized_views = math.log(1 + views) / math.log(1 + context.get('max_views', 1000))

            return (normalized_views + engagement_rate) / 2

        except Exception as e:
            logger.error(f"Popularity calculation failed: {str(e)}")
            return 0.0