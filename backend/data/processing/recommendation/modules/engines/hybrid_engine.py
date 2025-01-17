# backend/data_pipeline/recommendation/modules/engines/hybrid_engine.py

import logging
from typing import Dict, Any, List, Tuple
from collections import defaultdict

from ...types.recommendation_types import (
    RecommendationType,
    RecommendationCandidate
)

logger = logging.getLogger(__name__)


class HybridEngine:
    """
    Hybrid recommendation engine.
    Combines and synthesizes results from multiple recommendation engines.
    """

    type = RecommendationType.HYBRID

    def __init__(self):
        self.engines = {
            RecommendationType.CONTENT_BASED: None,  # Will be injected
            RecommendationType.COLLABORATIVE: None,  # Will be injected
            RecommendationType.CONTEXTUAL: None  # Will be injected
        }

    async def generate_candidates(
            self,
            context: Dict[str, Any]
    ) -> List[RecommendationCandidate]:
        """Generate candidates using hybrid approach"""
        try:
            # Get engine weights from context
            engine_weights = context.get('engine_weights', {
                RecommendationType.CONTENT_BASED: 0.4,
                RecommendationType.COLLABORATIVE: 0.4,
                RecommendationType.CONTEXTUAL: 0.2
            })

            # Collect candidates from each engine
            engine_candidates = {}
            for engine_type, engine in self.engines.items():
                if engine and engine_type in engine_weights:
                    candidates = await engine.generate_candidates(context)
                    engine_candidates[engine_type] = candidates

            # Merge and synthesize results
            merged_candidates = await self._merge_candidates(
                engine_candidates,
                engine_weights,
                context
            )

            return merged_candidates

        except Exception as e:
            logger.error(f"Hybrid candidate generation failed: {str(e)}")
            return []

    async def _merge_candidates(
            self,
            engine_candidates: Dict[RecommendationType, List[RecommendationCandidate]],
            engine_weights: Dict[RecommendationType, float],
            context: Dict[str, Any]
    ) -> List[RecommendationCandidate]:
        """Merge candidates from different engines"""
        try:
            merged_items = defaultdict(lambda: {
                'sources': [],
                'scores': defaultdict(list),
                'features': defaultdict(dict),
                'metadata': defaultdict(dict)
            })

            # Collect all candidates
            for engine_type, candidates in engine_candidates.items():
                for candidate in candidates:
                    item_data = merged_items[candidate.item_id]
                    item_data['sources'].append(engine_type)

                    # Collect scores
                    for score_type, score in candidate.scores.items():
                        item_data['scores'][score_type].append(
                            (score, engine_weights[engine_type])
                        )

                    # Merge features
                    self._merge_features(
                        item_data['features'],
                        candidate.features,
                        engine_type
                    )

                    # Merge metadata
                    item_data['metadata'][engine_type] = candidate.metadata

            # Create final candidates
            final_candidates = []
            for item_id, item_data in merged_items.items():
                if self._validate_hybrid_candidate(item_data, context):
                    candidate = self._create_hybrid_candidate(
                        item_id,
                        item_data,
                        engine_weights
                    )
                    final_candidates.append(candidate)

            # Sort by hybrid score
            final_candidates.sort(
                key=lambda x: x.scores.get('hybrid_score', 0),
                reverse=True
            )

            return final_candidates

        except Exception as e:
            logger.error(f"Candidate merging failed: {str(e)}")
            return []

    def _merge_features(
            self,
            existing_features: Dict[str, Any],
            new_features: Dict[str, Any],
            source: RecommendationType
    ) -> None:
        """Merge features from different sources"""
        try:
            for feature_name, feature_value in new_features.items():
                if feature_name not in existing_features:
                    existing_features[feature_name] = {
                        'value': feature_value,
                        'sources': [source]
                    }
                else:
                    if source not in existing_features[feature_name]['sources']:
                        existing_features[feature_name]['sources'].append(source)

                        # Handle conflicting values
                        if existing_features[feature_name]['value'] != feature_value:
                            existing_features[feature_name]['conflicts'] = True

        except Exception as e:
            logger.error(f"Feature merging failed: {str(e)}")

    def _validate_hybrid_candidate(
            self,
            item_data: Dict[str, Any],
            context: Dict[str, Any]
    ) -> bool:
        """Validate merged candidate against criteria"""
        try:
            min_sources = context.get('min_sources', 1)
            required_sources = set(context.get('required_sources', []))

            # Check number of sources
            if len(item_data['sources']) < min_sources:
                return False

            # Check required sources
            if required_sources and not required_sources.issubset(set(item_data['sources'])):
                return False

            # Check score thresholds
            return self._check_score_thresholds(
                item_data['scores'],
                context.get('score_thresholds', {})
            )

        except Exception as e:
            logger.error(f"Candidate validation failed: {str(e)}")
            return False

    def _calculate_hybrid_scores(
            self,
            scores: Dict[str, List[Tuple[float, float]]]
    ) -> Dict[str, float]:
        """Calculate final scores from multiple sources"""
        try:
            final_scores = {}

            # Calculate weighted average for each score type
            for score_type, score_weights in scores.items():
                if not score_weights:
                    continue

                weighted_sum = sum(score * weight for score, weight in score_weights)
                total_weight = sum(weight for _, weight in score_weights)

                final_scores[score_type] = weighted_sum / total_weight if total_weight > 0 else 0

            # Calculate overall hybrid score
            if final_scores:
                final_scores['hybrid_score'] = sum(final_scores.values()) / len(final_scores)

            return final_scores

        except Exception as e:
            logger.error(f"Score calculation failed: {str(e)}")
            return {'hybrid_score': 0.0}

    def _create_hybrid_candidate(
            self,
            item_id: str,
            item_data: Dict[str, Any],
            engine_weights: Dict[RecommendationType, float]
    ) -> RecommendationCandidate:
        """Create hybrid recommendation candidate"""
        try:
            return RecommendationCandidate(
                item_id=item_id,
                source=self.type,
                scores=self._calculate_hybrid_scores(item_data['scores']),
                features=self._consolidate_features(item_data['features']),
                metadata={
                    'sources': item_data['sources'],
                    'source_metadata': item_data['metadata'],
                    'engine_weights': engine_weights,
                    'feature_confidence': self._calculate_feature_confidence(
                        item_data['features']
                    )
                }
            )

        except Exception as e:
            logger.error(f"Hybrid candidate creation failed: {str(e)}")
            return None

    def _consolidate_features(
            self,
            feature_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Consolidate features from multiple sources"""
        consolidated = {}
        for feature_name, data in feature_data.items():
            if not data.get('conflicts', False):
                consolidated[feature_name] = data['value']
        return consolidated

    def _calculate_feature_confidence(
            self,
            feature_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate confidence scores for features"""
        confidence_scores = {}
        for feature_name, data in feature_data.items():
            # Higher confidence if multiple sources agree
            sources_count = len(data.get('sources', []))
            has_conflicts = data.get('conflicts', False)

            confidence_scores[feature_name] = (
                sources_count / len(self.engines) if not has_conflicts
                else (sources_count / len(self.engines)) * 0.5
            )

        return confidence_scores

    def _check_score_thresholds(
            self,
            scores: Dict[str, List[Tuple[float, float]]],
            thresholds: Dict[str, float]
    ) -> bool:
        """Check if scores meet minimum thresholds"""
        for score_type, threshold in thresholds.items():
            if score_type in scores:
                avg_score = sum(score for score, _ in scores[score_type]) / len(scores[score_type])
                if avg_score < threshold:
                    return False
        return True