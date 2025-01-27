# backend/core/processors/recommendation_processor.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata,
    ProcessingStage,
    ProcessingStatus,
    RecommendationState,
    RecommendationContext,
    RecommendationMetrics
)
from data.processing.recommendations.engines import (
    content_based,
    collaborative_filtering,
    contextual_engine,
    hybrid_engine
)
from data.processing.recommendations.rankers import (
    relevance_ranker,
    diversity_ranker,
    business_rules_ranker
)

logger = logging.getLogger(__name__)

class RecommendationProcessor:
    """
    Recommendation Processor: Handles actual recommendation generation.
    - Direct module access
    - Core processing logic
    - Message-based coordination
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        # Processor identification
        self.module_identifier = ModuleIdentifier(
            component_name="recommendation_processor",
            component_type=ComponentType.RECOMMENDATION_PROCESSOR,
            department="recommendation",
            role="processor"
        )

        # Active processing contexts
        self.active_contexts: Dict[str, RecommendationContext] = {}

        # Initialize components
        self._initialize_components()

        # Setup message handlers
        self._setup_message_handlers()

    def _initialize_components(self) -> None:
        """Initialize recommendation engines and rankers"""
        self.engines = {
            'content_based': content_based,
            'collaborative': collaborative_filtering,
            'contextual': contextual_engine,
            'hybrid': hybrid_engine
        }

        self.rankers = {
            'relevance': relevance_ranker,
            'diversity': diversity_ranker,
            'business_rules': business_rules_ranker
        }

    def _setup_message_handlers(self) -> None:
        """Setup processor message handlers"""
        handlers = {
            # Core Processing
            MessageType.RECOMMENDATION_PROCESSOR_START: self._handle_processor_start,
            MessageType.RECOMMENDATION_PROCESSOR_UPDATE: self._handle_processor_update,

            # Engine Processing
            MessageType.RECOMMENDATION_ENGINE_START: self._handle_engine_start,
            MessageType.RECOMMENDATION_ENGINE_RESPONSE: self._handle_engine_response,

            # Ranking and Filtering
            MessageType.RECOMMENDATION_FILTER_REQUEST: self._handle_filter_request,
            MessageType.RECOMMENDATION_RANK_REQUEST: self._handle_rank_request,

            # Control Messages
            MessageType.RECOMMENDATION_PROCESSOR_CANCEL: self._handle_cancellation
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"recommendation.{message_type.value}.#",
                handler
            )

    async def _handle_processor_start(self, message: ProcessingMessage) -> None:
        """Handle start of recommendation generation"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            config = message.content.get('config', {})

            # Initialize context
            context = RecommendationContext(
                pipeline_id=pipeline_id,
                state=RecommendationState.INITIALIZING,
                config=config
            )
            self.active_contexts[pipeline_id] = context

            # Update status
            await self._publish_status_update(
                pipeline_id,
                "Initializing recommendation generation",
                0.0
            )

            # Start engine processing
            await self._start_engine_processing(pipeline_id, config)

        except Exception as e:
            logger.error(f"Processor start failed: {str(e)}")
            await self._handle_processing_error(message, str(e))

    async def _start_engine_processing(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> None:
        """Start processing with recommendation engines"""
        try:
            context = self.active_contexts[pipeline_id]
            context.state = RecommendationState.ENGINE_SELECTION

            enabled_engines = config.get('enabled_engines', list(self.engines.keys()))

            # Process with each enabled engine
            for engine_name in enabled_engines:
                if engine_name not in self.engines:
                    continue

                engine = self.engines[engine_name]

                try:
                    # Generate recommendations
                    recommendations = await engine.generate_recommendations(
                        config.get('data'),
                        config.get(f'{engine_name}_config', {})
                    )

                    # Process engine results
                    await self._handle_engine_results(
                        pipeline_id,
                        engine_name,
                        recommendations
                    )

                except Exception as engine_error:
                    logger.error(f"Engine {engine_name} failed: {str(engine_error)}")
                    await self._publish_engine_error(
                        pipeline_id,
                        engine_name,
                        str(engine_error)
                    )

            # Check if we should proceed to filtering
            if context.has_recommendations():
                await self._start_filtering(pipeline_id)
            else:
                raise ValueError("No recommendations generated from any engine")

        except Exception as e:
            logger.error(f"Engine processing failed: {str(e)}")
            await self._handle_processing_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                str(e)
            )

    async def _handle_engine_results(
            self,
            pipeline_id: str,
            engine_name: str,
            recommendations: List[Dict[str, Any]]
    ) -> None:
        """Process results from recommendation engine"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        # Add engine recommendations to context
        context.add_engine_results(engine_name, recommendations)

        # Update metrics
        context.update_metrics({
            'engine_metrics': {
                engine_name: {
                    'recommendations_count': len(recommendations),
                    'average_confidence': sum(r.get('confidence', 0) for r in recommendations) / len(recommendations)
                }
            }
        })

        # Update status
        await self._publish_status_update(
            pipeline_id,
            f"Completed {engine_name} engine processing",
            context.calculate_progress()
        )

    async def _start_filtering(self, pipeline_id: str) -> None:
        """Start recommendation filtering process"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        try:
            context.state = RecommendationState.FILTERING

            # Apply filtering rules
            filtered_recommendations = []
            for recommendations in context.engine_results.values():
                for rec in recommendations:
                    if await self._apply_filtering_rules(rec, context.config.get('filtering_rules', {})):
                        filtered_recommendations.append(rec)

            context.filtered_recommendations = filtered_recommendations

            # Update metrics
            context.update_metrics({
                'filtering_metrics': {
                    'total_filtered': len(filtered_recommendations),
                    'filter_rate': len(filtered_recommendations) / context.total_recommendations
                }
            })

            # Move to ranking if we have filtered recommendations
            if filtered_recommendations:
                await self._start_ranking(pipeline_id)
            else:
                raise ValueError("No recommendations passed filtering")

        except Exception as e:
            logger.error(f"Filtering failed: {str(e)}")
            await self._handle_processing_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                str(e)
            )

    async def _start_ranking(self, pipeline_id: str) -> None:
        """Start recommendation ranking process"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        try:
            context.state = RecommendationState.RANKING

            # Rank recommendations
            ranked_recommendations = []
            for rec in context.filtered_recommendations:
                ranking_scores = {}

                # Apply each ranker
                for ranker_name, ranker in self.rankers.items():
                    if ranker_name in context.config.get('ranking_criteria', {}):
                        score = await ranker.calculate_score(
                            rec,
                            context.config['ranking_criteria'][ranker_name]
                        )
                        ranking_scores[ranker_name] = score

                # Calculate final score
                final_score = self._calculate_final_score(ranking_scores)
                ranked_recommendations.append({
                    'recommendation': rec,
                    'ranking_scores': ranking_scores,
                    'final_score': final_score
                })

            # Sort by final score
            ranked_recommendations.sort(key=lambda x: x['final_score'], reverse=True)

            # Store results
            context.final_recommendations = ranked_recommendations[:context.config.get('max_recommendations', 10)]

            # Complete processing
            await self._complete_processing(pipeline_id)

        except Exception as e:
            logger.error(f"Ranking failed: {str(e)}")
            await self._handle_processing_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                str(e)
            )

    async def _complete_processing(self, pipeline_id: str) -> None:
        """Complete recommendation processing"""
        try:
            context = self.active_contexts[pipeline_id]
            context.state = RecommendationState.COMPLETED

            # Calculate final metrics
            final_metrics = self._calculate_final_metrics(context)

            # Publish completion
            await self._publish_completion(
                pipeline_id,
                context.final_recommendations,
                final_metrics
            )

            # Cleanup
            del self.active_contexts[pipeline_id]

        except Exception as e:
            logger.error(f"Completion failed: {str(e)}")
            await self._handle_processing_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                str(e)
            )

    async def _publish_completion(
            self,
            pipeline_id: str,
            recommendations: List[Dict[str, Any]],
            metrics: RecommendationMetrics
    ) -> None:
        """Publish completion message"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.RECOMMENDATION_PROCESSOR_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'recommendations': recommendations,
                    'metrics': metrics.__dict__,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="recommendation_handler",
                    domain_type="recommendation",
                    processing_stage=ProcessingStage.RECOMMENDATION
                ),
                source_identifier=self.module_identifier
            )
        )

    async def cleanup(self) -> None:
        """Cleanup processor resources"""
        try:
            # Calculate final metrics for each active process
            for pipeline_id, context in self.active_contexts.items():
                metrics = self._calculate_final_metrics(context)
                await self._publish_metrics(pipeline_id, metrics)

            # Clear active processes
            self.active_contexts.clear()

        except Exception as e:
            logger.error(f"Processor cleanup failed: {str(e)}")
            raise