import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    RecommendationContext,
    RecommendationState,
    ManagerState
)
from .base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class RecommendationManager(BaseManager):
    """
    Recommendation Manager: Coordinates high-level recommendation workflow.
    Manages recommendation generation, filtering, and ranking process.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            component_name: str = "recommendation_manager",
            domain_type: str = "recommendation"
    ):
        # Call base class __init__ first to set up context
        super().__init__(
            message_broker=message_broker,
            component_name=component_name,
            domain_type=domain_type
        )

        # Active processes and contexts
        self.active_processes: Dict[str, RecommendationContext] = {}
        self.process_timeouts: Dict[str, datetime] = {}

        # Recommendation configuration
        self.recommendation_thresholds = {
            "minimum_confidence": 0.7,
            "minimum_diversity": 0.3,
            "maximum_processing_time": 1800,  # 30 minutes
            "maximum_candidates": 100
        }

    async def _initialize_manager(self) -> None:
        """Initialize the recommendation manager"""
        try:
            # Initialize base components
            await super()._initialize_manager()

            # Setup message handlers
            await self._setup_domain_handlers()

            # Update state
            self.state = ManagerState.ACTIVE
            # Access component_name through context
            logger.info(f"Recommendation manager initialized successfully: {self.context.component_name}")

        except Exception as e:
            logger.error(f"Failed to initialize recommendation manager: {str(e)}")
            self.state = ManagerState.ERROR
            raise

    async def _setup_domain_handlers(self) -> None:
        """Setup recommendation-specific message handlers"""
        handlers = {
            # Core Process Flow
            MessageType.RECOMMENDATION_GENERATE_REQUEST: self._handle_generate_request,
            MessageType.RECOMMENDATION_GENERATE_COMPLETE: self._handle_generate_complete,
            MessageType.RECOMMENDATION_PROCESS_START: self._handle_process_start,
            MessageType.RECOMMENDATION_PROCESS_PROGRESS: self._handle_process_progress,
            MessageType.RECOMMENDATION_PROCESS_COMPLETE: self._handle_process_complete,
            MessageType.RECOMMENDATION_PROCESS_FAILED: self._handle_process_failed,

            # Candidate Management
            MessageType.RECOMMENDATION_CANDIDATES_GENERATE_REQUEST: self._handle_candidates_generate,
            MessageType.RECOMMENDATION_CANDIDATES_GENERATE_PROGRESS: self._handle_candidates_progress,
            MessageType.RECOMMENDATION_CANDIDATES_GENERATE_COMPLETE: self._handle_candidates_complete,
            MessageType.RECOMMENDATION_MERGE_REQUEST: self._handle_candidates_merge,

            # Filtering and Ranking
            MessageType.RECOMMENDATION_FILTER_REQUEST: self._handle_filter_request,
            MessageType.RECOMMENDATION_FILTER_COMPLETE: self._handle_filter_complete,
            MessageType.RECOMMENDATION_RANK_REQUEST: self._handle_rank_request,
            MessageType.RECOMMENDATION_RANK_COMPLETE: self._handle_rank_complete,

            # Validation
            MessageType.RECOMMENDATION_VALIDATE_REQUEST: self._handle_validate_request,
            MessageType.RECOMMENDATION_VALIDATE_COMPLETE: self._handle_validate_complete,
            MessageType.RECOMMENDATION_VALIDATE_APPROVE: self._handle_validate_approve,
            MessageType.RECOMMENDATION_VALIDATE_REJECT: self._handle_validate_reject,

            # Engine-Specific Processing
            MessageType.RECOMMENDATION_ENGINE_CONTENT: self._handle_content_engine,
            MessageType.RECOMMENDATION_ENGINE_COLLABORATIVE: self._handle_collaborative_engine,
            MessageType.RECOMMENDATION_ENGINE_CONTEXTUAL: self._handle_contextual_engine,
            MessageType.RECOMMENDATION_ENGINE_HYBRID: self._handle_hybrid_engine,

            # Advanced Features
            MessageType.RECOMMENDATION_PERSONALIZE: self._handle_personalize,
            MessageType.RECOMMENDATION_DIVERSITY_ENSURE: self._handle_diversity_ensure,
            MessageType.RECOMMENDATION_FEEDBACK_INCORPORATE: self._handle_feedback_incorporate,
            MessageType.RECOMMENDATION_BUSINESS_RULES: self._handle_business_rules,

            # System Operations
            MessageType.RECOMMENDATION_METRICS_UPDATE: self._handle_metrics_update,
            MessageType.RECOMMENDATION_CONFIG_UPDATE: self._handle_config_update
        }

        for message_type, handler in handlers.items():
            await self.register_message_handler(message_type, handler)

    async def initiate_recommendation_process(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> str:
        """Initiate a new recommendation process"""
        try:
            correlation_id = str(uuid.uuid4())

            # Validate configuration
            if not self._validate_recommendation_config(config):
                raise ValueError("Invalid recommendation configuration")

            # Create recommendation context
            context = RecommendationContext(
                pipeline_id=pipeline_id,
                correlation_id=correlation_id,
                state=RecommendationState.INITIALIZING,
                config=config,
                created_at=datetime.now()
            )

            self.active_processes[pipeline_id] = context

            # Start recommendation process
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_PROCESS_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': config
                    },
                    metadata=MessageMetadata(
                        correlation_id=correlation_id,
                        source_component=self.component_name,
                        target_component="recommendation_service",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
                    )
                )
            )

            logger.info(f"Recommendation process initiated for pipeline: {pipeline_id}")
            return correlation_id

        except Exception as e:
            logger.error(f"Failed to initiate recommendation process: {str(e)}")
            raise

    def _validate_recommendation_config(self, config: Dict[str, Any]) -> bool:
        """Validate recommendation configuration"""
        try:
            required_fields = ['recommendation_type', 'engines', 'filters']
            if not all(field in config for field in required_fields):
                return False

            # Validate engines configuration
            if not self._validate_engines_config(config['engines']):
                return False

            # Validate filters configuration
            if not self._validate_filters_config(config['filters']):
                return False

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False

    def _validate_engines_config(self, engines_config: Dict[str, Any]) -> bool:
        """Validate engines configuration"""
        try:
            required_engine_fields = ['type', 'weight', 'parameters']
            return all(
                all(field in engine for field in required_engine_fields)
                for engine in engines_config.values()
            )
        except Exception as e:
            logger.error(f"Engines configuration validation failed: {str(e)}")
            return False

    def _validate_filters_config(self, filters_config: Dict[str, Any]) -> bool:
        """Validate filters configuration"""
        try:
            required_filter_fields = ['type', 'parameters', 'order']
            return all(
                all(field in filter_config for field in required_filter_fields)
                for filter_config in filters_config.values()
            )
        except Exception as e:
            logger.error(f"Filters configuration validation failed: {str(e)}")
            return False

    async def _handle_process_start(self, message: ProcessingMessage) -> None:
        """Handle recommendation process start"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = RecommendationState.INITIALIZING
            context.updated_at = datetime.now()

            # Start candidate generation
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_CANDIDATES_GENERATE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="recommendation_service",
                        domain_type="recommendation"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Process start failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_candidates_generate(self, message: ProcessingMessage) -> None:
        """Handle candidate generation request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = RecommendationState.GENERATING
            context.updated_at = datetime.now()

            # Start engines based on configuration
            for engine_type in context.config['engines']:
                await self._start_engine(pipeline_id, engine_type)

        except Exception as e:
            logger.error(f"Candidate generation failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _start_engine(self, pipeline_id: str, engine_type: str) -> None:
        """Start recommendation engine"""
        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            engine_config = context.config['engines'][engine_type]

            message_type = self._get_engine_message_type(engine_type)
            if not message_type:
                raise ValueError(f"Invalid engine type: {engine_type}")

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=message_type,
                    content={
                        'pipeline_id': pipeline_id,
                        'engine_config': engine_config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="recommendation_service",
                        domain_type="recommendation"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Engine start failed: {str(e)}")
            raise

    def _get_engine_message_type(self, engine_type: str) -> Optional[MessageType]:
        """Get message type for engine type"""
        engine_types = {
            'content': MessageType.RECOMMENDATION_ENGINE_CONTENT,
            'collaborative': MessageType.RECOMMENDATION_ENGINE_COLLABORATIVE,
            'contextual': MessageType.RECOMMENDATION_ENGINE_CONTEXTUAL,
            'hybrid': MessageType.RECOMMENDATION_ENGINE_HYBRID
        }
        return engine_types.get(engine_type)

    async def _handle_filter_request(self, message: ProcessingMessage) -> None:
        """Handle recommendation filtering request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = RecommendationState.FILTERING
            context.updated_at = datetime.now()

            # Apply filters in order
            filters = sorted(
                context.config['filters'].items(),
                key=lambda x: x[1]['order']
            )

            for filter_name, filter_config in filters:
                await self._apply_filter(pipeline_id, filter_name, filter_config)

        except Exception as e:
            logger.error(f"Filter request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _apply_filter(self, pipeline_id: str, filter_name: str, filter_config: Dict[str, Any]) -> None:
        """Apply recommendation filter"""
        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_FILTER_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'filter_name': filter_name,
                        'filter_config': filter_config,
                        'candidates': context.candidates
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="recommendation_service",
                        domain_type="recommendation"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Filter application failed: {str(e)}")
            raise

    async def _handle_process_complete(self, message: ProcessingMessage) -> None:
        """Handle process completion"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Generate final recommendations
            final_recommendations = self._generate_final_recommendations(context)

            # Update context
            context.state = RecommendationState.COMPLETED
            context.completed_at = datetime.now()

            # Notify completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_PROCESS_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'recommendations': final_recommendations,
                        'metrics': context.metrics.__dict__,
                        'completion_time': context.completed_at.isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="control_point_manager",
                        domain_type="recommendation"
                    )
                )
            )

            # Cleanup
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Process completion failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    def _generate_final_recommendations(self, context: RecommendationContext) -> List[Dict[str, Any]]:
        """Generate final recommendations based on filtered and ranked candidates"""
        try:
            # Apply final scoring
            scored_candidates = [
                {
                    **candidate,
                    'final_score': self._calculate_final_score(candidate, context)
                }
                for candidate in context.candidates
            ]

            # Sort by final score
            sorted_recommendations = sorted(
                scored_candidates,
                key=lambda x: x['final_score'],
                reverse=True
            )

            # Apply diversity if enabled
            if context.config.get('ensure_diversity', False):
                sorted_recommendations = self._ensure_diversity(sorted_recommendations)

            # Return top N recommendations
            max_recommendations = context.config.get('max_recommendations', 10)
            return sorted_recommendations[:max_recommendations]

        except Exception as e:
            logger.error(f"Final recommendations generation failed: {str(e)}")

    async def _handle_generate_request(self, message: ProcessingMessage) -> None:
        """
        Handle request to generate recommendations
        """
        pipeline_id = message.content.get('pipeline_id')
        try:
            # Create new context for this generation request
            context = RecommendationContext(
                pipeline_id=pipeline_id,
                correlation_id=message.metadata.correlation_id,
                state=RecommendationState.INITIALIZING,
                config=message.content.get('config', {})
            )

            self.active_processes[pipeline_id] = context

            # Start the generation process
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_PROCESS_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="recommendation_processor",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
                    )
                )
            )

            logger.info(f"Initiated recommendation generation for pipeline: {pipeline_id}")

        except Exception as e:
            logger.error(f"Failed to handle validation rejection: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_content_engine(self, message: ProcessingMessage) -> None:
        """
        Handle content-based recommendation engine processing
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Get engine configuration
            engine_config = context.config['engines'].get('content', {})

            # Process content-based recommendations
            await self._process_content_recommendations(
                pipeline_id,
                engine_config,
                message.content.get('data', {})
            )

        except Exception as e:
            logger.error(f"Failed to handle content engine: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_collaborative_engine(self, message: ProcessingMessage) -> None:
        """
        Handle collaborative filtering recommendation engine
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Get engine configuration
            engine_config = context.config['engines'].get('collaborative', {})

            # Process collaborative filtering recommendations
            await self._process_collaborative_recommendations(
                pipeline_id,
                engine_config,
                message.content.get('user_data', {}),
                message.content.get('item_data', {})
            )

        except Exception as e:
            logger.error(f"Failed to handle collaborative engine: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_contextual_engine(self, message: ProcessingMessage) -> None:
        """
        Handle contextual recommendation engine
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Get engine configuration
            engine_config = context.config['engines'].get('contextual', {})

            # Process contextual recommendations
            await self._process_contextual_recommendations(
                pipeline_id,
                engine_config,
                message.content.get('context_data', {})
            )

        except Exception as e:
            logger.error(f"Failed to handle contextual engine: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_hybrid_engine(self, message: ProcessingMessage) -> None:
        """
        Handle hybrid recommendation engine combining multiple approaches
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Get engine configuration
            engine_config = context.config['engines'].get('hybrid', {})

            # Process hybrid recommendations
            await self._process_hybrid_recommendations(
                pipeline_id,
                engine_config,
                message.content.get('engine_results', {})
            )

        except Exception as e:
            logger.error(f"Failed to handle hybrid engine: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_personalize(self, message: ProcessingMessage) -> None:
        """
        Handle personalization of recommendations
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Apply personalization
            personalization_config = context.config.get('personalization', {})
            user_profile = message.content.get('user_profile', {})

            personalized_recommendations = await self._apply_personalization(
                context.ranked_recommendations,
                personalization_config,
                user_profile
            )

            context.ranked_recommendations = personalized_recommendations

            # Proceed to next phase
            await self._start_diversity_check(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle personalization: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_diversity_ensure(self, message: ProcessingMessage) -> None:
        """
        Handle diversity enforcement in recommendations
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Apply diversity rules
            diversity_config = context.config.get('diversity', {})
            diverse_recommendations = await self._ensure_diversity(
                context.ranked_recommendations,
                diversity_config
            )

            context.ranked_recommendations = diverse_recommendations

            # Proceed to next phase
            await self._start_validation(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle diversity enforcement: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_feedback_incorporate(self, message: ProcessingMessage) -> None:
        """
        Handle incorporation of user feedback
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Process feedback
            feedback_data = message.content.get('feedback', {})
            await self._incorporate_feedback(
                pipeline_id,
                feedback_data
            )

            # Update recommendations based on feedback
            await self._update_recommendations_with_feedback(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle feedback incorporation: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_business_rules(self, message: ProcessingMessage) -> None:
        """
        Handle application of business rules to recommendations
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Apply business rules
            rules_config = context.config.get('business_rules', {})
            filtered_recommendations = await self._apply_business_rules(
                context.ranked_recommendations,
                rules_config
            )

            context.ranked_recommendations = filtered_recommendations

            # Proceed to next phase
            await self._start_personalization(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle business rules: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_metrics_update(self, message: ProcessingMessage) -> None:
        """
        Handle updates to recommendation metrics
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update metrics
            metrics_update = message.content.get('metrics', {})
            self._update_metrics(context, metrics_update)

            # Publish metrics update
            await self._publish_metrics_update(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle metrics update: {str(e)}")

    async def _handle_config_update(self, message: ProcessingMessage) -> None:
        """
        Handle updates to recommendation configuration
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update configuration
            config_update = message.content.get('config', {})
            await self._update_configuration(context, config_update)

            # Restart processing if needed
            if message.content.get('restart_required', False):
                await self._restart_processing(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle config update: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _process_content_recommendations(
            self,
            pipeline_id: str,
            engine_config: Dict[str, Any],
            data: Dict[str, Any]
    ) -> None:
        """
        Process content-based recommendations
        """
        try:
            # Extract features from items
            features = await self._extract_content_features(data)

            # Generate similarity scores
            similarity_scores = await self._calculate_content_similarity(features)

            # Generate recommendations
            recommendations = await self._generate_content_recommendations(
                similarity_scores,
                engine_config
            )

            # Store results
            context = self.active_processes[pipeline_id]
            context.candidates['content'] = recommendations

            # Check if all engines completed
            await self._check_engines_completion(pipeline_id)

        except Exception as e:
            logger.error(f"Content recommendation processing failed: {str(e)}")
            raise


    async def _process_collaborative_recommendations(
            self,
            pipeline_id: str,
            engine_config: Dict[str, Any],
            user_data: Dict[str, Any],
            item_data: Dict[str, Any]
    ) -> None:
        """
        Process collaborative filtering recommendations
        """
        try:
            # Build user-item interaction matrix
            interaction_matrix = await self._build_interaction_matrix(
                user_data,
                item_data
            )

            # Calculate user similarities
            user_similarities = await self._calculate_user_similarities(
                interaction_matrix
            )

            # Generate recommendations
            recommendations = await self._generate_collaborative_recommendations(
                user_similarities,
                engine_config
            )

            # Store results
            context = self.active_processes[pipeline_id]
            context.candidates['collaborative'] = recommendations

            # Check if all engines completed
            await self._check_engines_completion(pipeline_id)

        except Exception as e:
            logger.error(f"Collaborative recommendation processing failed: {str(e)}")
            raise


    async def _process_contextual_recommendations(
            self,
            pipeline_id: str,
            engine_config: Dict[str, Any],
            context_data: Dict[str, Any]
    ) -> None:
        """
        Process contextual recommendations
        """
        try:
            # Extract contextual features
            context_features = await self._extract_contextual_features(context_data)

            # Apply contextual rules
            filtered_items = await self._apply_contextual_rules(
                context_features,
                engine_config
            )

            # Generate recommendations
            recommendations = await self._generate_contextual_recommendations(
                filtered_items,
                engine_config
            )

            # Store results
            context = self.active_processes[pipeline_id]
            context.candidates['contextual'] = recommendations

            # Check if all engines completed
            await self._check_engines_completion(pipeline_id)

        except Exception as e:
            logger.error(f"Contextual recommendation processing failed: {str(e)}")
            raise


    async def _handle_generate_complete(self, message: ProcessingMessage) -> None:
        """
        Handle completion of recommendation generation
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            logger.warning(f"No context found for pipeline: {pipeline_id}")
            return

        try:
            # Update context with results
            context.state = RecommendationState.COMPLETION
            context.completed_at = datetime.now()

            # Notify completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_PROCESS_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'recommendations': message.content.get('recommendations', []),
                        'metrics': context.metrics.__dict__,
                        'completion_time': context.completed_at.isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="control_point_manager",
                        domain_type="recommendation"
                    )
                )
            )

            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle generation completion: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_process_progress(self, message: ProcessingMessage) -> None:
        """
        Handle progress updates during recommendation processing
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update progress in context
            progress = message.content.get('progress', 0)
            stage = message.content.get('stage', '')

            context.progress[stage] = progress
            context.updated_at = datetime.now()

            # Forward progress update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_PROCESS_PROGRESS,
                    content={
                        'pipeline_id': pipeline_id,
                        'progress': progress,
                        'stage': stage,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=message.metadata
                )
            )

        except Exception as e:
            logger.error(f"Failed to handle progress update: {str(e)}")


    async def _handle_process_failed(self, message: ProcessingMessage) -> None:
        """
        Handle recommendation process failure
        """
        pipeline_id = message.content.get('pipeline_id')
        error = message.content.get('error', 'Unknown error')

        try:
            context = self.active_processes.get(pipeline_id)
            if context:
                context.state = RecommendationState.FAILED
                context.error = error

                # Notify about failure
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.RECOMMENDATION_PROCESS_FAILED,
                        content={
                            'pipeline_id': pipeline_id,
                            'error': error,
                            'timestamp': datetime.now().isoformat()
                        },
                        metadata=MessageMetadata(
                            correlation_id=context.correlation_id,
                            source_component=self.component_name,
                            target_component="control_point_manager",
                            domain_type="recommendation"
                        )
                    )
                )

                await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Error handling process failure: {str(e)}")

    async def _handle_candidates_progress(self, message: ProcessingMessage) -> None:
        """
        Handle progress updates for candidate generation
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update candidate generation progress
            engine_type = message.content.get('engine_type')
            progress = message.content.get('progress', 0)

            if engine_type:
                context.engine_metrics[engine_type] = {
                    'progress': progress,
                    'updated_at': datetime.now().isoformat()
                }

            # Forward progress update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_CANDIDATES_GENERATE_PROGRESS,
                    content={
                        'pipeline_id': pipeline_id,
                        'engine_type': engine_type,
                        'progress': progress,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=message.metadata
                )
            )

        except Exception as e:
            logger.error(f"Failed to handle candidates progress: {str(e)}")


    async def _handle_candidates_complete(self, message: ProcessingMessage) -> None:
        """
        Handle completion of candidate generation
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Store generated candidates
            engine_type = message.content.get('engine_type')
            candidates = message.content.get('candidates', [])

            if engine_type:
                context.candidates[engine_type] = candidates

            # Check if all engines completed
            if len(context.candidates) == len(context.config['engines']):
                # Proceed to filtering
                await self._start_filtering(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle candidates completion: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_candidates_merge(self, message: ProcessingMessage) -> None:
        """
        Handle request to merge candidates from different engines
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Merge candidates from all engines
            merged_candidates = []

            for engine_type, candidates in context.candidates.items():
                weight = context.config['engines'][engine_type].get('weight', 1.0)

                for candidate in candidates:
                    candidate['source_engine'] = engine_type
                    candidate['engine_weight'] = weight
                    merged_candidates.append(candidate)

            # Store merged candidates
            context.merged_candidates = merged_candidates

            # Proceed to next phase
            await self._start_ranking(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to merge candidates: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_filter_complete(self, message: ProcessingMessage) -> None:
        """
        Handle completion of recommendation filtering
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Store filtered candidates
            filtered_candidates = message.content.get('filtered_candidates', [])
            context.filtered_candidates = filtered_candidates

            # Proceed to ranking
            await self._start_ranking(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle filter completion: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_rank_request(self, message: ProcessingMessage) -> None:
        """
        Handle request to rank recommendations
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = RecommendationState.RANKING

            # Apply ranking criteria
            ranking_config = context.config.get('ranking', {})
            await self._apply_ranking(pipeline_id, ranking_config)

        except Exception as e:
            logger.error(f"Failed to handle rank request: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_rank_complete(self, message: ProcessingMessage) -> None:
        """
        Handle completion of recommendation ranking
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Store ranked recommendations
            ranked_recommendations = message.content.get('ranked_recommendations', [])
            context.ranked_recommendations = ranked_recommendations

            # Proceed to validation
            await self._start_validation(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle rank completion: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_validate_request(self, message: ProcessingMessage) -> None:
        """
        Handle request to validate recommendations
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = RecommendationState.VALIDATION

            # Apply validation rules
            validation_config = context.config.get('validation', {})
            await self._validate_recommendations(pipeline_id, validation_config)

        except Exception as e:
            logger.error(f"Failed to handle validate request: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_validate_complete(self, message: ProcessingMessage) -> None:
        """
        Handle completion of recommendation validation
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Store validation results
            validation_results = message.content.get('validation_results', {})
            context.validation_results = validation_results

            if validation_results.get('passed', False):
                # Proceed to completion
                await self._complete_process(pipeline_id)
            else:
                # Handle validation failure
                await self._handle_validation_failure(pipeline_id, validation_results)

        except Exception as e:
            logger.error(f"Failed to handle validation completion: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_validate_approve(self, message: ProcessingMessage) -> None:
        """
        Handle approval of recommendations after validation
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Mark recommendations as approved
            context.validation_results['approved'] = True

            # Proceed to completion
            await self._complete_process(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle validation approval: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _process_hybrid_recommendations(
            self,
            pipeline_id: str,
            engine_config: Dict[str, Any],
            engine_results: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """
        Process hybrid recommendations combining multiple approaches
        """
        try:
            # Combine results from different engines
            combined_scores = await self._combine_engine_scores(
                engine_results,
                engine_config
            )

            # Apply hybrid ranking
            ranked_recommendations = await self._apply_hybrid_ranking(
                combined_scores,
                engine_config
            )

            # Store results
            context = self.active_processes[pipeline_id]
            context.candidates['hybrid'] = ranked_recommendations

            # Check if all engines completed
            await self._check_engines_completion(pipeline_id)

        except Exception as e:
            logger.error(f"Hybrid recommendation processing failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))


    async def _handle_validate_reject(self, message: ProcessingMessage) -> None:
        """
        Handle rejection of recommendations after validation
        """
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Store rejection reason
            rejection_reason = message.content.get('reason', 'No reason provided')
            context.validation_results['rejected'] = True
            context.validation_results['rejection_reason'] = rejection_reason

            # Handle rejection
            await self._handle_validation_rejection(pipeline_id, rejection_reason)

        except Exception as e:
            logger.error(f"Failed to handle validation rejection: {str(e)}")
            await self._handle_error(pipeline_id, str(e))