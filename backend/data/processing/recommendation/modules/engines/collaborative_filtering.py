# backend/data_pipeline/recommendation/modules/engines/collaborative_filtering.py

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import numpy as np

from ...types.recommendation_types import (
    RecommendationType,
    RecommendationCandidate
)

logger = logging.getLogger(__name__)


class CollaborativeEngine:
    """
    Collaborative filtering recommendation engine.
    Uses user-item interactions to generate recommendations.
    """

    type = RecommendationType.COLLABORATIVE

    async def generate_candidates(
            self,
            context: Dict[str, Any]
    ) -> List[RecommendationCandidate]:
        """Generate candidates using collaborative filtering"""
        try:
            # Extract context data
            user_id = context['user_context'].get('user_id')
            interaction_data = context.get('interaction_data', {})
            similarity_threshold = context.get('similarity_threshold', 0.3)

            candidates = []

            # Find similar users
            similar_users = self._find_similar_users(
                user_id,
                interaction_data,
                similarity_threshold
            )

            # Get items from similar users
            candidate_items = self._get_candidate_items(
                user_id,
                similar_users,
                interaction_data
            )

            # Create recommendation candidates
            for item_id, item_data in candidate_items.items():
                candidate = RecommendationCandidate(
                    item_id=item_id,
                    source=self.type,
                    scores={
                        'popularity': item_data['popularity'],
                        'similarity': item_data['similarity'],
                        'rating': item_data['avg_rating']
                    },
                    features=item_data.get('features', {}),
                    metadata={
                        'supporting_users': item_data['supporting_users'],
                        'interaction_stats': item_data['interaction_stats']
                    }
                )
                candidates.append(candidate)

            return candidates

        except Exception as e:
            logger.error(f"Collaborative filtering candidate generation failed: {str(e)}")
            return []

    def _find_similar_users(
            self,
            user_id: str,
            interaction_data: Dict[str, Any],
            similarity_threshold: float
    ) -> Dict[str, float]:
        """Find users similar to target user"""
        try:
            user_interactions = interaction_data.get('user_interactions', {})
            target_interactions = set(user_interactions.get(user_id, []))

            if not target_interactions:
                return {}

            similar_users = {}
            for other_id, other_interactions in user_interactions.items():
                if other_id == user_id:
                    continue

                other_interactions_set = set(other_interactions)
                similarity = self._calculate_user_similarity(
                    target_interactions,
                    other_interactions_set
                )

                if similarity >= similarity_threshold:
                    similar_users[other_id] = similarity

            return similar_users

        except Exception as e:
            logger.error(f"Similar users calculation failed: {str(e)}")
            return {}

    def _get_candidate_items(
            self,
            user_id: str,
            similar_users: Dict[str, float],
            interaction_data: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Get candidate items from similar users"""
        try:
            user_interactions = interaction_data.get('user_interactions', {})
            item_ratings = interaction_data.get('item_ratings', {})

            # Items user has already interacted with
            user_items = set(user_interactions.get(user_id, []))

            candidate_items = {}

            for similar_user, similarity in similar_users.items():
                similar_user_items = user_interactions.get(similar_user, [])

                for item_id in similar_user_items:
                    if item_id in user_items:
                        continue

                    if item_id not in candidate_items:
                        candidate_items[item_id] = {
                            'supporting_users': [],
                            'similarity_sum': 0.0,
                            'rating_sum': 0.0,
                            'interaction_count': 0,
                            'interaction_stats': {
                                'views': 0,
                                'ratings': [],
                                'interactions': 0
                            }
                        }

                    # Update item data
                    candidate_items[item_id]['supporting_users'].append(similar_user)
                    candidate_items[item_id]['similarity_sum'] += similarity
                    candidate_items[item_id]['interaction_count'] += 1

                    # Add rating if available
                    if item_id in item_ratings:
                        rating = item_ratings[item_id].get(similar_user)
                        if rating:
                            candidate_items[item_id]['rating_sum'] += rating
                            candidate_items[item_id]['interaction_stats']['ratings'].append(rating)

            # Calculate final scores for each item
            for item_id, item_data in candidate_items.items():
                item_data['popularity'] = item_data['interaction_count'] / len(similar_users)
                item_data['similarity'] = item_data['similarity_sum'] / item_data['interaction_count']
                item_data['avg_rating'] = (
                    sum(item_data['interaction_stats']['ratings']) /
                    len(item_data['interaction_stats']['ratings'])
                    if item_data['interaction_stats']['ratings']
                    else 0.0
                )

            return candidate_items

        except Exception as e:
            logger.error(f"Candidate items calculation failed: {str(e)}")
            return {}

    def _calculate_user_similarity(
            self,
            user1_items: Set[str],
            user2_items: Set[str]
    ) -> float:
        """Calculate similarity between two users using Jaccard similarity"""
        try:
            if not user1_items or not user2_items:
                return 0.0

            intersection = len(user1_items & user2_items)
            union = len(user1_items | user2_items)

            return intersection / union if union > 0 else 0.0

        except Exception as e:
            logger.error(f"User similarity calculation failed: {str(e)}")
            return 0.0

    def _calculate_rating_similarity(
            self,
            ratings1: List[float],
            ratings2: List[float]
    ) -> float:
        """Calculate similarity between rating patterns"""
        try:
            if not ratings1 or not ratings2:
                return 0.0

            # Convert to numpy arrays for efficient calculation
            r1 = np.array(ratings1)
            r2 = np.array(ratings2)

            # Calculate Pearson correlation
            correlation = np.corrcoef(r1, r2)[0, 1]

            # Convert correlation to similarity score [0, 1]
            return (correlation + 1) / 2

        except Exception as e:
            logger.error(f"Rating similarity calculation failed: {str(e)}")
            return 0.0

    def _get_item_features(
            self,
            item_id: str,
            interaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get features for an item from interaction data"""
        try:
            item_features = interaction_data.get('item_features', {})
            return item_features.get(item_id, {})
        except Exception as e:
            logger.error(f"Item features retrieval failed: {str(e)}")
            return {}