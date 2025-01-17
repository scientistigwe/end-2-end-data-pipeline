# backend/data_pipeline/recommendation/modules/rankers/personalization_ranker.py

import logging
from typing import Dict, Any, List
import numpy as np
from datetime import datetime

from ...types.recommendation_types import RecommendationCandidate

logger = logging.getLogger(__name__)


class PersonalizationRanker:
    """
    Ranks recommendations based on user preferences and behavior patterns.
    """

    async def rank(
            self,
            candidates: List[RecommendationCandidate],
            context: Dict[str, Any]
    ) -> List[RecommendationCandidate]:
        """Rank candidates based on personalization factors"""
        try:
            user_profile = context.get('user_profile', {})
            user_history = context.get('user_history', [])
            personalization_config = context.get('personalization_config', {})

            # Calculate personalization scores
            scored_candidates = []
            for candidate in candidates:
                personalization_score = self._calculate_personalization_score(
                    candidate,
                    user_profile,
                    user_history,
                    personalization_config
                )

                # Add personalization score
                candidate.scores['personalization'] = personalization_score
                scored_candidates.append(candidate)

            # Sort by personalization score
            return sorted(
                scored_candidates,
                key=lambda x: x.scores['personalization'],
                reverse=True
            )

        except Exception as e:
            logger.error(f"Personalization ranking failed: {str(e)}")
            return candidates

    def _calculate_personalization_score(
            self,
            candidate: RecommendationCandidate,
            user_profile: Dict[str, Any],
            user_history: List[Dict[str, Any]],
            config: Dict[str, Any]
    ) -> float:
        """Calculate overall personalization score"""
        try:
            # Calculate individual components
            preference_score = self._calculate_preference_match(
                candidate, user_profile, config
            )
            behavior_score = self._calculate_behavior_match(
                candidate, user_history, config
            )
            affinity_score = self._calculate_category_affinity(
                candidate, user_history, config
            )
            trend_score = self._calculate_trend_alignment(
                candidate, user_history, config
            )

            # Weight components
            weights = config.get('score_weights', {
                'preference': 0.4,
                'behavior': 0.3,
                'affinity': 0.2,
                'trend': 0.1
            })

            # Calculate weighted sum
            weighted_score = (
                    preference_score * weights['preference'] +
                    behavior_score * weights['behavior'] +
                    affinity_score * weights['affinity'] +
                    trend_score * weights['trend']
            )

            return weighted_score

        except Exception as e:
            logger.error(f"Personalization score calculation failed: {str(e)}")
            return 0.0

    def _calculate_preference_match(
            self,
            candidate: RecommendationCandidate,
            user_profile: Dict[str, Any],
            config: Dict[str, Any]
    ) -> float:
        """Calculate match with user preferences"""
        try:
            preferences = user_profile.get('preferences', {})
            if not preferences:
                return 0.5  # Neutral score if no preferences

            matches = 0
            total_prefs = 0

            # Check each preference type
            for pref_type, pref_value in preferences.items():
                if pref_type in candidate.features:
                    total_prefs += 1
                    if isinstance(pref_value, list):
                        # List preferences (e.g., categories)
                        item_value = candidate.features[pref_type]
                        if isinstance(item_value, list):
                            overlap = set(pref_value) & set(item_value)
                            matches += len(overlap) / max(len(pref_value), len(item_value))
                        else:
                            matches += 1 if item_value in pref_value else 0
                    else:
                        # Single value preferences
                        matches += 1 if candidate.features[pref_type] == pref_value else 0

            return matches / total_prefs if total_prefs > 0 else 0.5

        except Exception as e:
            logger.error(f"Preference match calculation failed: {str(e)}")
            return 0.0

    def _calculate_behavior_match(
            self,
            candidate: RecommendationCandidate,
            user_history: List[Dict[str, Any]],
            config: Dict[str, Any]
    ) -> float:
        """Calculate match with user behavior patterns"""
        try:
            if not user_history:
                return 0.5  # Neutral score if no history

            # Extract feature patterns from history
            historical_patterns = self._extract_behavior_patterns(user_history)

            # Compare candidate features with patterns
            pattern_matches = 0
            total_patterns = len(historical_patterns)

            for feature, pattern in historical_patterns.items():
                if feature in candidate.features:
                    similarity = self._calculate_pattern_similarity(
                        candidate.features[feature],
                        pattern
                    )
                    pattern_matches += similarity

            return pattern_matches / total_patterns if total_patterns > 0 else 0.5

        except Exception as e:
            logger.error(f"Behavior match calculation failed: {str(e)}")
            return 0.0

    def _calculate_category_affinity(
            self,
            candidate: RecommendationCandidate,
            user_history: List[Dict[str, Any]],
            config: Dict[str, Any]
    ) -> float:
        """Calculate affinity with item categories"""
        try:
            if not user_history:
                return 0.5

            # Calculate category frequencies
            category_counts = {}
            total_interactions = 0

            for interaction in user_history:
                category = interaction.get('category')
                if category:
                    category_counts[category] = category_counts.get(category, 0) + 1
                    total_interactions += 1

            if total_interactions == 0:
                return 0.5

            # Calculate affinity score
            candidate_category = candidate.features.get('category')
            if not candidate_category:
                return 0.5

            category_frequency = category_counts.get(candidate_category, 0) / total_interactions

            # Apply softmax to avoid extreme scores
            return 1 / (1 + np.exp(-category_frequency))

        except Exception as e:
            logger.error(f"Category affinity calculation failed: {str(e)}")
            return 0.0

    def _calculate_trend_alignment(
            self,
            candidate: RecommendationCandidate,
            user_history: List[Dict[str, Any]],
            config: Dict[str, Any]
    ) -> float:
        """Calculate alignment with user's recent trends"""
        try:
            if not user_history:
                return 0.5

            # Get recent history
            recent_window = config.get('trend_window', 10)
            recent_history = sorted(
                user_history,
                key=lambda x: x.get('timestamp', datetime.min),
                reverse=True
            )[:recent_window]

            if not recent_history:
                return 0.5

            # Extract recent trends
            recent_trends = self._extract_recent_trends(recent_history)

            # Compare candidate with trends
            trend_alignment = self._compare_with_trends(
                candidate.features,
                recent_trends
            )

            return trend_alignment

        except Exception as e:
            logger.error(f"Trend alignment calculation failed: {str(e)}")
            return 0.0

    def _extract_behavior_patterns(
            self,
            history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract behavior patterns from user history"""
        patterns = {}
        try:
            # Group by feature
            for interaction in history:
                for feature, value in interaction.items():
                    if feature not in patterns:
                        patterns[feature] = []
                    patterns[feature].append(value)

            # Calculate pattern representations
            for feature, values in patterns.items():
                if isinstance(values[0], (int, float)):
                    # Numerical features - calculate mean and std
                    patterns[feature] = {
                        'mean': np.mean(values),
                        'std': np.std(values)
                    }
                else:
                    # Categorical features - calculate frequencies
                    value_counts = {}
                    for value in values:
                        value_counts[value] = value_counts.get(value, 0) + 1
                    patterns[feature] = value_counts

        except Exception as e:
            logger.error(f"Pattern extraction failed: {str(e)}")

        return patterns

    def _calculate_pattern_similarity(
            self,
            value: Any,
            pattern: Any
    ) -> float:
        """Calculate similarity between value and pattern"""
        try:
            if isinstance(pattern, dict):
                if 'mean' in pattern:
                    # Numerical pattern
                    z_score = abs(value - pattern['mean']) / max(pattern['std'], 1e-6)
                    return 1 / (1 + z_score)
                else:
                    # Categorical pattern
                    total = sum(pattern.values())
                    frequency = pattern.get(value, 0) / total
                    return frequency
            return 0.0

        except Exception as e:
            logger.error(f"Pattern similarity calculation failed: {str(e)}")
            return 0.0

    def _extract_recent_trends(
            self,
            recent_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract trends from recent history"""
        try:
            trends = {
                'feature_trends': {},
                'category_trends': {},
                'interaction_patterns': {}
            }

            # Extract sequential patterns
            for i in range(len(recent_history) - 1):
                current = recent_history[i]
                previous = recent_history[i + 1]

                # Feature changes
                for feature in current:
                    if feature in previous:
                        if feature not in trends['feature_trends']:
                            trends['feature_trends'][feature] = []
                        trends['feature_trends'][feature].append(
                            current[feature] - previous[feature]
                            if isinstance(current[feature], (int, float))
                            else 0
                        )

            # Calculate trend metrics
            for feature, changes in trends['feature_trends'].items():
                if changes:
                    trends['feature_trends'][feature] = {
                        'mean_change': np.mean(changes),
                        'trend_direction': np.sign(np.mean(changes))
                    }

            return trends

        except Exception as e:
            logger.error(f"Trend extraction failed: {str(e)}")
            return {}

    def _compare_with_trends(
            self,
            features: Dict[str, Any],
            trends: Dict[str, Any]
    ) -> float:
        """Compare candidate features with recent trends"""
        try:
            trend_scores = []

            # Compare feature trends
            for feature, trend in trends['feature_trends'].items():
                if feature in features:
                    if isinstance(trend, dict) and 'trend_direction' in trend:
                        # Score based on trend alignment
                        trend_scores.append(
                            1 if features[feature] * trend['trend_direction'] > 0 else 0
                        )

            return np.mean(trend_scores) if trend_scores else 0.5

        except Exception as e:
            logger.error(f"Trend comparison failed: {str(e)}")
            return 0.0