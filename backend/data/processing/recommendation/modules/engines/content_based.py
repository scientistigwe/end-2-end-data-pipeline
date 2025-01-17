# backend/data_pipeline/recommendation/modules/engines/content_based.py

import logging
from typing import Dict, Any, List
from datetime import datetime

from ...types.recommendation_types import (
    RecommendationType,
    RecommendationCandidate
)

logger = logging.getLogger(__name__)

class ContentBasedEngine:
    """
    Content-based recommendation engine.
    Uses item features and user preferences to generate recommendations.
    """

    type = RecommendationType.CONTENT_BASED

    async def generate_candidates(
            self,
            context: Dict[str, Any]
    ) -> List[RecommendationCandidate]:
        """Generate candidates based on content similarity"""
        try:
            # Extract context data
            user_context = context.get('user_context', {})
            item_features = context.get('item_features', {})
            preferences = user_context.get('preferences', {})

            candidates = []
            seen_items = set(user_context.get('seen_items', []))

            # Generate candidates for each feature match
            for item_id, features in item_features.items():
                if item_id in seen_items:
                    continue

                similarity_scores = self._calculate_feature_similarity(
                    features,
                    preferences
                )

                if self._meets_threshold(similarity_scores):
                    candidate = RecommendationCandidate(
                        item_id=item_id,
                        source=self.type,
                        scores={
                            'feature_similarity': similarity_scores['overall'],
                            'category_match': similarity_scores['category'],
                            'attribute_match': similarity_scores['attributes']
                        },
                        features=features,
                        metadata={
                            'similarity_details': similarity_scores,
                            'matched_preferences': self._get_matched_preferences(
                                features,
                                preferences
                            )
                        }
                    )
                    candidates.append(candidate)

            return candidates

        except Exception as e:
            logger.error(f"Content-based candidate generation failed: {str(e)}")
            return []

    def _calculate_feature_similarity(
            self,
            features: Dict[str, Any],
            preferences: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate similarity between item features and user preferences"""
        try:
            scores = {
                'category': self._calculate_category_similarity(
                    features.get('categories', []),
                    preferences.get('preferred_categories', [])
                ),
                'attributes': self._calculate_attribute_similarity(
                    features.get('attributes', {}),
                    preferences.get('preferred_attributes', {})
                ),
                'tags': self._calculate_tag_similarity(
                    features.get('tags', []),
                    preferences.get('preferred_tags', [])
                )
            }

            # Calculate overall similarity
            scores['overall'] = self._calculate_overall_similarity(scores)
            return scores

        except Exception as e:
            logger.error(f"Feature similarity calculation failed: {str(e)}")
            return {'overall': 0.0, 'category': 0.0, 'attributes': 0.0, 'tags': 0.0}

    def _calculate_category_similarity(
            self,
            item_categories: List[str],
            preferred_categories: List[str]
    ) -> float:
        """Calculate category similarity score"""
        if not item_categories or not preferred_categories:
            return 0.0

        matching_categories = set(item_categories) & set(preferred_categories)
        return len(matching_categories) / max(len(item_categories), len(preferred_categories))

    def _calculate_attribute_similarity(
            self,
            item_attributes: Dict[str, Any],
            preferred_attributes: Dict[str, Any]
    ) -> float:
        """Calculate attribute similarity score"""
        if not item_attributes or not preferred_attributes:
            return 0.0

        matching_score = 0.0
        total_attributes = len(preferred_attributes)

        for attr, pref_value in preferred_attributes.items():
            if attr in item_attributes:
                matching_score += self._compare_attribute_values(
                    item_attributes[attr],
                    pref_value
                )

        return matching_score / total_attributes if total_attributes > 0 else 0.0

    def _calculate_tag_similarity(
            self,
            item_tags: List[str],
            preferred_tags: List[str]
    ) -> float:
        """Calculate tag similarity score"""
        if not item_tags or not preferred_tags:
            return 0.0

        matching_tags = set(item_tags) & set(preferred_tags)
        return len(matching_tags) / max(len(item_tags), len(preferred_tags))

    def _compare_attribute_values(
            self,
            item_value: Any,
            preferred_value: Any
    ) -> float:
        """Compare individual attribute values"""
        if isinstance(item_value, (int, float)) and isinstance(preferred_value, (int, float)):
            return 1.0 - min(abs(item_value - preferred_value) / max(item_value, preferred_value), 1.0)
        return 1.0 if item_value == preferred_value else 0.0

    def _calculate_overall_similarity(
            self,
            scores: Dict[str, float]
    ) -> float:
        """Calculate overall similarity score"""
        weights = {
            'category': 0.4,
            'attributes': 0.4,
            'tags': 0.2
        }

        return sum(
            score * weights[score_type]
            for score_type, score in scores.items()
            if score_type in weights
        )

    def _meets_threshold(
            self,
            similarity_scores: Dict[str, float]
    ) -> bool:
        """Check if similarity scores meet minimum thresholds"""
        return (
            similarity_scores['overall'] >= 0.5 and
            similarity_scores['category'] >= 0.3
        )

    def _get_matched_preferences(
            self,
            features: Dict[str, Any],
            preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get details of matched preferences"""
        matched = {
            'categories': list(
                set(features.get('categories', [])) &
                set(preferences.get('preferred_categories', []))
            ),
            'attributes': {},
            'tags': list(
                set(features.get('tags', [])) &
                set(preferences.get('preferred_tags', []))
            )
        }

        # Match attributes
        for attr, pref_value in preferences.get('preferred_attributes', {}).items():
            if attr in features.get('attributes', {}):
                matched['attributes'][attr] = {
                    'item_value': features['attributes'][attr],
                    'preferred_value': pref_value
                }

        return matched