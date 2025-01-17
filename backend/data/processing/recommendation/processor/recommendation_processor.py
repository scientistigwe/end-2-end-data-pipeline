# backend/data_pipeline/recommendation/processor/recommendation_processor.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    RecommendationContext
)
from core.staging.staging_manager import StagingManager

from ..types.recommendation_types import (
    RecommendationType,
    RecommendationPhase,
    RecommendationStatus,
    RecommendationCandidate,
    RankedRecommendation,
    RecommendationResult,
    RecommendationState
)

from ..modules.engines import (
    content_based,
    collaborative_filtering,
    contextual_engine,
    hybrid_engine
)

from ..modules.rankers import (
    relevance_ranker,
    personalization_ranker,
    diversity_ranker,
    business_rules_ranker
)

logger = logging.getLogger(__name__)


class RecommendationProcessor:
    """
    Coordinates recommendation generation through different engines,
    ranking, and aggregation phases.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        self.message_broker = message_broker
        self.staging_manager = staging_manager
        self.logger = logging.getLogger(__name__)

        # Active states
        self.active_states: Dict[str, RecommendationState] = {}

        # Initialize engines and rankers
        self._initialize_components()

    def _initialize_components(self) -> None:
        """Initialize recommendation components"""
        # Recommendation engines
        self.engines = {
            RecommendationType.CONTENT_BASED: content_based,
            RecommendationType.COLLABORATIVE: collaborative_filtering,
            RecommendationType.CONTEXTUAL: contextual_engine,
            RecommendationType.HYBRID: hybrid_engine
        }

        # Ranking components
        self.rankers = {
            'relevance': relevance_ranker,
            'personalization': personalization_ranker,
            'diversity': diversity_ranker,
            'business_rules': business_rules_ranker
        }

    async def process_recommendation_request(
            self,
            pipeline_id: str,
            context: RecommendationContext
    ) -> RecommendationState:
        """Process recommendation request through all phases"""
        try:
            # Initialize state
            state = await self._initialize_state(pipeline_id, context)
            self.active_states[pipeline_id] = state

            # Generate candidates
            await self._generate_candidates(state, context)
            if state.status == RecommendationStatus.FAILED:
                return state

            # Filter candidates
            await self._filter_candidates(state, context)
            if state.status == RecommendationStatus.FAILED:
                return state

            # Rank recommendations
            await self._rank_recommendations(state, context)
            if state.status == RecommendationStatus.FAILED:
                return state

            # Finalize recommendations
            await self._finalize_recommendations(state, context)

            return state

        except Exception as e:
            logger.error(f"Failed to process recommendation request: {str(e)}")
            await self._handle_error(pipeline_id, "process", str(e))
            raise

    async def _generate_candidates(
            self,
            state: RecommendationState,
            context: RecommendationContext
    ) -> None:
        """Generate candidates from enabled engines"""
        try:
            state.status = RecommendationStatus.GENERATING
            state.current_phase = RecommendationPhase.CANDIDATE_GENERATION

            candidates = []
            for engine_type in context.enabled_engines:
                if engine_type in self.engines:
                    engine_candidates = await self._get_engine_candidates(
                        self.engines[engine_type],
                        context
                    )
                    candidates.extend(engine_candidates)

            state.candidates = candidates
            await self._notify_phase_complete(
                state.pipeline_id,
                RecommendationPhase.CANDIDATE_GENERATION,
                len(candidates)
            )

        except Exception as e:
            state.status = RecommendationStatus.FAILED
            await self._handle_error(state.pipeline_id, "candidate_generation", str(e))

    async def _filter_candidates(
            self,
            state: RecommendationState,
            context: RecommendationContext
    ) -> None:
        """Filter candidates based on rules"""
        try:
            state.status = RecommendationStatus.FILTERING
            state.current_phase = RecommendationPhase.FILTERING

            filtered_candidates = []
            for candidate in state.candidates:
                if self._meets_filtering_criteria(candidate, context.filtering_rules):
                    filtered_candidates.append(candidate)

            state.candidates = filtered_candidates
            await self._notify_phase_complete(
                state.pipeline_id,
                RecommendationPhase.FILTERING,
                len(filtered_candidates)
            )

        except Exception as e:
            state.status = RecommendationStatus.FAILED
            await self._handle_error(state.pipeline_id, "filtering", str(e))

    async def _rank_recommendations(
            self,
            state: RecommendationState,
            context: RecommendationContext
    ) -> None:
        """Rank filtered candidates"""
        try:
            state.status = RecommendationStatus.RANKING
            state.current_phase = RecommendationPhase.RANKING

            ranked_items = []
            for idx, candidate in enumerate(state.candidates):
                ranking_scores = {}

                # Apply each ranker
                for ranker_name, ranker in self.rankers.items():
                    if ranker_name in context.ranking_criteria:
                        score = await ranker.rank(
                            candidate,
                            context.ranking_criteria[ranker_name]
                        )
                        ranking_scores[ranker_name] = score

                # Calculate final score
                final_score = self._calculate_final_score(
                    ranking_scores,
                    context.engine_weights
                )

                ranked_items.append(
                    RankedRecommendation(
                        candidate=candidate,
                        final_score=final_score,
                        rank=idx + 1,
                        ranking_factors=ranking_scores,
                        confidence=self._calculate_confidence(ranking_scores)
                    )
                )

            # Sort by final score
            state.ranked_items = sorted(
                ranked_items,
                key=lambda x: x.final_score,
                reverse=True
            )

            await self._notify_phase_complete(
                state.pipeline_id,
                RecommendationPhase.RANKING,
                len(state.ranked_items)
            )

        except Exception as e:
            state.status = RecommendationStatus.FAILED
            await self._handle_error(state.pipeline_id, "ranking", str(e))

    async def _finalize_recommendations(
            self,
            state: RecommendationState,
            context: RecommendationContext
    ) -> None:
        """Finalize recommendations applying diversity and limits"""
        try:
            state.current_phase = RecommendationPhase.FINALIZATION

            # Apply diversity rules
            diversified_items = await self.rankers['diversity'].apply_diversity(
                state.ranked_items,
                context.diversity_settings
            )

            # Apply limits
            final_items = diversified_items[:context.max_recommendations]

            # Create final result
            result = RecommendationResult(
                pipeline_id=state.pipeline_id,
                recommendations=final_items,
                metadata=self._create_result_metadata(state, context),
                scores=self._calculate_overall_scores(final_items)
            )

            # Store result
            await self._store_result(state.pipeline_id, result)

            # Update state
            state.status = RecommendationStatus.COMPLETED
            await self._notify_completion(state.pipeline_id, result)

        except Exception as e:
            state.status = RecommendationStatus.FAILED
            await self._handle_error(state.pipeline_id, "finalization", str(e))

    async def _get_engine_candidates(
            self,
            engine: Any,
            context: RecommendationContext
    ) -> List[RecommendationCandidate]:
        """Get candidates from specific engine"""
        try:
            raw_candidates = await engine.generate_candidates(context)
            return [
                RecommendationCandidate(
                    item_id=str(uuid.uuid4()),
                    source=engine.type,
                    scores=candidate.get('scores', {}),
                    features=candidate.get('features', {}),
                    metadata=candidate.get('metadata', {})
                )
                for candidate in raw_candidates
            ]
        except Exception as e:
            logger.error(f"Engine candidate generation failed: {str(e)}")
            return []

    def _meets_filtering_criteria(
            self,
            candidate: RecommendationCandidate,
            rules: Dict[str, Any]
    ) -> bool:
        """Check if candidate meets filtering criteria"""
        # Implement filtering logic
        return True

    def _calculate_final_score(
            self,
            ranking_scores: Dict[str, float],
            weights: Dict[str, float]
    ) -> float:
        """Calculate final score from ranking factors"""
        final_score = 0.0
        for ranker_name, score in ranking_scores.items():
            weight = weights.get(ranker_name, 1.0)
            final_score += score * weight
        return final_score / len(ranking_scores) if ranking_scores else 0.0

    def _calculate_confidence(
            self,
            ranking_scores: Dict[str, float]
    ) -> float:
        """Calculate confidence score"""
        return sum(ranking_scores.values()) / len(ranking_scores) if ranking_scores else 0.0

    async def _store_result(
            self,
            pipeline_id: str,
            result: RecommendationResult
    ) -> None:
        """Store recommendation result"""
        await self.staging_manager.store_staged_data(
            pipeline_id,
            {
                'type': 'recommendation_result',
                'data': result.__dict__,
                'created_at': datetime.now().isoformat()
            }
        )

    async def _notify_completion(
            self,
            pipeline_id: str,
            result: RecommendationResult
    ) -> None:
        """Notify about recommendation completion"""
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'recommendations': [r.__dict__ for r in result.recommendations],
                'metadata': result.metadata,
                'scores': result.scores
            }
        )
        await self.message_broker.publish(message)

    async def _notify_phase_complete(
            self,
            pipeline_id: str,
            phase: RecommendationPhase,
            count: int
    ) -> None:
        """Notify about phase completion"""
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_UPDATE,
            content={
                'pipeline_id': pipeline_id,
                'phase': phase.value,
                'count': count,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    async def _handle_error(
            self,
            pipeline_id: str,
            phase: str,
            error: str
    ) -> None:
        """Handle processing errors"""
        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_ERROR,
            content={
                'pipeline_id': pipeline_id,
                'phase': phase,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    def _create_result_metadata(
            self,
            state: RecommendationState,
            context: RecommendationContext
    ) -> Dict[str, Any]:
        """Create metadata for recommendation result"""
        return {
            'engines_used': context.enabled_engines,
            'candidates_generated': len(state.candidates),
            'candidates_ranked': len(state.ranked_items),
            'processing_time': (datetime.now() - state.created_at).total_seconds(),
            'context_type': context.request_type
        }

    def _calculate_overall_scores(
            self,
            recommendations: List[RankedRecommendation]
    ) -> Dict[str, float]:
        """Calculate overall recommendation scores"""
        return {
            'average_confidence': sum(r.confidence for r in recommendations) / len(recommendations),
            'average_score': sum(r.final_score for r in recommendations) / len(recommendations)
        }