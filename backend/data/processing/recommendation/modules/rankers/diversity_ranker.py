# backend/data_pipeline/recommendation/modules/rankers/diversity_ranker.py

import logging
from typing import Dict, Any, List, Set, Optional
import numpy as np
from collections import defaultdict

from ...types.recommendation_types import RecommendationCandidate

logger = logging.getLogger(__name__)


class DiversityRanker:
    """
    Ensures diversity in recommendations by re-ranking based on
    multiple diversity dimensions (category, attribute, feature diversity).
    """

    async def rank(
            self,
            candidates: List[RecommendationCandidate],
            context: Dict[str, Any]
    ) -> List[RecommendationCandidate]:
        """Rank candidates ensuring diversity"""
        try:
            diversity_config = context.get('diversity_config', {
                'category_weight': 0.4,
                'attribute_weight': 0.3,
                'feature_weight': 0.3,
                'min_diversity_score': 0.3,
                'max_similar_items': 2
            })

            # First, calculate diversity scores
            candidates_with_diversity = self._calculate_diversity_scores(
                candidates,
                diversity_config
            )

            # Then re-rank based on diversity
            reranked_candidates = self._rerank_candidates(
                candidates_with_diversity,
                diversity_config
            )

            return reranked_candidates

        except Exception as e:
            logger.error(f"Diversity ranking failed: {str(e)}")
            return candidates

    def _calculate_diversity_scores(
            self,
            candidates: List[RecommendationCandidate],
            config: Dict[str, Any]
    ) -> List[RecommendationCandidate]:
        """Calculate diversity scores for candidates"""
        try:
            # Group candidates by dimensions
            categories = defaultdict(list)
            attributes = defaultdict(list)
            features = defaultdict(list)

            for candidate in candidates:
                # Group by category
                category = self._get_category(candidate)
                categories[category].append(candidate)

                # Group by attributes
                for attr, value in self._get_attributes(candidate).items():
                    attributes[f"{attr}:{value}"].append(candidate)

                # Group by feature vectors
                feature_key = self._get_feature_key(candidate)
                features[feature_key].append(candidate)

            # Calculate diversity scores
            for candidate in candidates:
                diversity_score = self._compute_diversity_score(
                    candidate,
                    categories,
                    attributes,
                    features,
                    config
                )
                candidate.scores['diversity'] = diversity_score

            return candidates

        except Exception as e:
            logger.error(f"Diversity score calculation failed: {str(e)}")
            return candidates

    def _rerank_candidates(
            self,
            candidates: List[RecommendationCandidate],
            config: Dict[str, Any]
    ) -> List[RecommendationCandidate]:
        """Re-rank candidates based on diversity"""
        try:
            if not candidates:
                return []

            # Initialize selected and remaining candidates
            selected = []
            remaining = candidates.copy()
            min_score = config.get('min_diversity_score', 0.3)
            max_similar = config.get('max_similar_items', 2)

            # Track dimensions for diversity
            selected_categories: Set[str] = set()
            selected_attributes: Dict[str, int] = defaultdict(int)
            selected_features: Dict[str, int] = defaultdict(int)

            while remaining and len(selected) < len(candidates):
                # Find most diverse candidate
                next_candidate = self._select_next_diverse_candidate(
                    remaining,
                    selected_categories,
                    selected_attributes,
                    selected_features,
                    max_similar,
                    min_score
                )

                if not next_candidate:
                    break

                # Update selected dimensions
                category = self._get_category(next_candidate)
                selected_categories.add(category)

                for attr, value in self._get_attributes(next_candidate).items():
                    key = f"{attr}:{value}"
                    selected_attributes[key] += 1

                feature_key = self._get_feature_key(next_candidate)
                selected_features[feature_key] += 1

                # Update candidate lists
                selected.append(next_candidate)
                remaining.remove(next_candidate)

            return selected + remaining  # Add any remaining candidates at the end

        except Exception as e:
            logger.error(f"Candidate re-ranking failed: {str(e)}")
            return candidates

    def _compute_diversity_score(
            self,
            candidate: RecommendationCandidate,
            categories: Dict[str, List[RecommendationCandidate]],
            attributes: Dict[str, List[RecommendationCandidate]],
            features: Dict[str, List[RecommendationCandidate]],
            config: Dict[str, Any]
    ) -> float:
        """Compute diversity score for a candidate"""
        try:
            category_score = self._calculate_category_diversity(
                candidate,
                categories,
                config
            )

            attribute_score = self._calculate_attribute_diversity(
                candidate,
                attributes,
                config
            )

            feature_score = self._calculate_feature_diversity(
                candidate,
                features,
                config
            )

            # Weighted combination
            weights = {
                'category': config.get('category_weight', 0.4),
                'attribute': config.get('attribute_weight', 0.3),
                'feature': config.get('feature_weight', 0.3)
            }

            return (
                    category_score * weights['category'] +
                    attribute_score * weights['attribute'] +
                    feature_score * weights['feature']
            )

        except Exception as e:
            logger.error(f"Diversity score computation failed: {str(e)}")
            return 0.0

    def _select_next_diverse_candidate(
            self,
            candidates: List[RecommendationCandidate],
            selected_categories: Set[str],
            selected_attributes: Dict[str, int],
            selected_features: Dict[str, int],
            max_similar: int,
            min_score: float
    ) -> Optional[RecommendationCandidate]:
        """Select next most diverse candidate"""
        try:
            best_candidate = None
            best_score = -1

            for candidate in candidates:
                # Skip if doesn't meet minimum diversity score
                if candidate.scores.get('diversity', 0) < min_score:
                    continue

                # Check category diversity
                category = self._get_category(candidate)
                if len(selected_categories) < max_similar or category not in selected_categories:
                    # Check attribute diversity
                    attributes_ok = True
                    for attr, value in self._get_attributes(candidate).items():
                        key = f"{attr}:{value}"
                        if selected_attributes[key] >= max_similar:
                            attributes_ok = False
                            break

                    if attributes_ok:
                        # Check feature diversity
                        feature_key = self._get_feature_key(candidate)
                        if selected_features[feature_key] < max_similar:
                            # Calculate combined score
                            score = candidate.scores.get('diversity', 0)
                            if score > best_score:
                                best_score = score
                                best_candidate = candidate

            return best_candidate

        except Exception as e:
            logger.error(f"Candidate selection failed: {str(e)}")
            return None

    def _get_category(self, candidate: RecommendationCandidate) -> str:
        """Get category from candidate"""
        return str(candidate.features.get('category', 'unknown'))

    def _get_attributes(self, candidate: RecommendationCandidate) -> Dict[str, Any]:
        """Get relevant attributes from candidate"""
        return candidate.features.get('attributes', {})

    def _get_feature_key(self, candidate: RecommendationCandidate) -> str:
        """Create feature key for candidate"""
        try:
            features = candidate.features.get('feature_vector', [])
            if isinstance(features, list):
                return '_'.join(map(str, features))
            return str(features)
        except Exception:
            return 'unknown'

    def _calculate_category_diversity(
            self,
            candidate: RecommendationCandidate,
            categories: Dict[str, List[RecommendationCandidate]],
            config: Dict[str, Any]
    ) -> float:
        """Calculate category-based diversity"""
        try:
            category = self._get_category(candidate)
            total_candidates = sum(len(cats) for cats in categories.values())
            category_count = len(categories[category])

            return 1 - (category_count / total_candidates)

        except Exception as e:
            logger.error(f"Category diversity calculation failed: {str(e)}")
            return 0.0

    def _calculate_attribute_diversity(
            self,
            candidate: RecommendationCandidate,
            attributes: Dict[str, List[RecommendationCandidate]],
            config: Dict[str, Any]
    ) -> float:
        """Calculate attribute-based diversity"""
        try:
            candidate_attrs = self._get_attributes(candidate)
            if not candidate_attrs:
                return 0.0

            diversity_scores = []
            total_candidates = sum(len(attrs) for attrs in attributes.values())

            for attr, value in candidate_attrs.items():
                key = f"{attr}:{value}"
                attr_count = len(attributes[key])
                diversity_scores.append(1 - (attr_count / total_candidates))

            return np.mean(diversity_scores)

        except Exception as e:
            logger.error(f"Attribute diversity calculation failed: {str(e)}")
            return 0.0

    def _calculate_feature_diversity(
            self,
            candidate: RecommendationCandidate,
            features: Dict[str, List[RecommendationCandidate]],
            config: Dict[str, Any]
    ) -> float:
        """Calculate feature-based diversity"""
        try:
            feature_key = self._get_feature_key(candidate)
            total_candidates = sum(len(feats) for feats in features.values())
            feature_count = len(features[feature_key])

            return 1 - (feature_count / total_candidates)

        except Exception as e:
            logger.error(f"Feature diversity calculation failed: {str(e)}")
            return 0.0