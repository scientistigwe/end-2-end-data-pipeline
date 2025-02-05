import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata,
    ProcessingStage,
    ProcessingStatus,
    RecommendationContext,
    RecommendationState,
    RecommendationType,
    RecommendationCandidate
)

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Recommendation Service: Orchestrates recommendation generation process.
    Coordinates between Manager, Handler, and various recommendation engines.
    Supports multiple recommendation strategies and combines their results.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        # Service identification
        self.module_identifier = ModuleIdentifier(
            component_name="recommendation_service",
            component_type=ComponentType.RECOMMENDATION_SERVICE,
            department="recommendation",
            role="service"
        )

        # Active request tracking
        self.active_requests: Dict[str, RecommendationContext] = {}

        # Setup message handlers
        self._setup_message_handlers()

    async def _setup_message_handlers(self) -> None:
        """Setup service message handlers"""
        handlers = {
            # Core Process Flow
            MessageType.RECOMMENDATION_PROCESS_START: self._handle_process_start,
            MessageType.RECOMMENDATION_PROCESS_PROGRESS: self._handle_process_progress,
            MessageType.RECOMMENDATION_PROCESS_COMPLETE: self._handle_process_complete,
            MessageType.RECOMMENDATION_PROCESS_FAILED: self._handle_process_error,

            # Candidate Management
            MessageType.RECOMMENDATION_CANDIDATES_GENERATE_REQUEST: self._handle_candidates_generate_request,
            MessageType.RECOMMENDATION_CANDIDATES_FILTER: self._handle_candidates_filter,
            MessageType.RECOMMENDATION_CANDIDATES_RANK: self._handle_candidates_rank,
            MessageType.RECOMMENDATION_CANDIDATES_MERGE: self._handle_candidates_merge,

            # Engine-specific Messages
            MessageType.RECOMMENDATION_ENGINE_CONTENT: self._handle_engine_content,
            MessageType.RECOMMENDATION_ENGINE_COLLABORATIVE: self._handle_engine_collaborative,
            MessageType.RECOMMENDATION_ENGINE_CONTEXTUAL: self._handle_engine_contextual,
            MessageType.RECOMMENDATION_ENGINE_HYBRID: self._handle_engine_hybrid,

            # Validation and Feedback
            MessageType.RECOMMENDATION_VALIDATE_REQUEST: self._handle_validation_request,
            MessageType.RECOMMENDATION_FEEDBACK_PROCESS: self._handle_feedback_process,

            # System Operations
            MessageType.RECOMMENDATION_METRICS_UPDATE: self._handle_metrics_update,
            MessageType.RECOMMENDATION_CONFIG_UPDATE: self._handle_config_update
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                f"recommendation.{message_type.value}",
                handler
            )

    async def _handle_process_start(self, message: ProcessingMessage) -> None:
        """Handle recommendation process start request"""
        try:
            pipeline_id = message.content['pipeline_id']
            config = message.content.get('config', {})

            # Create context with enabled engines
            context = RecommendationContext(
                pipeline_id=pipeline_id,
                correlation_id=message.metadata.correlation_id,
                state=RecommendationState.INITIALIZING,
                enabled_engines=self._get_enabled_engines(config)
            )
            self.active_requests[pipeline_id] = context

            # Initialize engines
            await self._initialize_engines(pipeline_id, config)

            # Update status
            await self._publish_status_update(
                pipeline_id=pipeline_id,
                state=RecommendationState.INITIALIZING,
                progress=0.0,
                message="Starting recommendation process"
            )

        except Exception as e:
            logger.error(f"Process start failed: {str(e)}")
            await self._handle_error(message, str(e))

    def _get_enabled_engines(self, config: Dict[str, Any]) -> List[RecommendationType]:
        """Get list of enabled recommendation engines from config"""
        default_engines = [
            RecommendationType.CONTENT_BASED,
            RecommendationType.COLLABORATIVE,
            RecommendationType.CONTEXTUAL
        ]

        enabled_engines = config.get('enabled_engines', default_engines)
        return [RecommendationType(engine) for engine in enabled_engines]

    async def _initialize_engines(self, pipeline_id: str, config: Dict[str, Any]) -> None:
        """Initialize enabled recommendation engines"""
        context = self.active_requests.get(pipeline_id)
        if not context:
            return

        for engine_type in context.enabled_engines:
            # Get engine specific config
            engine_config = config.get('engine_configs', {}).get(engine_type.value, {})

            # Initialize engine
            await self._publish_engine_message(
                engine_type=engine_type,
                message_type=self._get_engine_init_message_type(engine_type),
                content={
                    'pipeline_id': pipeline_id,
                    'config': engine_config
                }
            )

    def _get_engine_init_message_type(self, engine_type: RecommendationType) -> MessageType:
        """Get initialization message type for engine"""
        message_types = {
            RecommendationType.CONTENT_BASED: MessageType.RECOMMENDATION_ENGINE_CONTENT,
            RecommendationType.COLLABORATIVE: MessageType.RECOMMENDATION_ENGINE_COLLABORATIVE,
            RecommendationType.CONTEXTUAL: MessageType.RECOMMENDATION_ENGINE_CONTEXTUAL,
            RecommendationType.HYBRID: MessageType.RECOMMENDATION_ENGINE_HYBRID
        }
        return message_types.get(engine_type, MessageType.RECOMMENDATION_ENGINE_CONTENT)

    async def _handle_candidates_generate_request(self, message: ProcessingMessage) -> None:
        """Handle candidate generation request"""
        try:
            pipeline_id = message.content['pipeline_id']
            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Update state
            context.state = RecommendationState.GENERATING

            # Track progress for each engine
            engines_started = 0
            for engine_type in context.enabled_engines:
                # Request candidates from engine
                await self._publish_engine_message(
                    engine_type=engine_type,
                    message_type=MessageType.RECOMMENDATION_CANDIDATES_GENERATE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'parameters': context.engine_configs.get(engine_type.value, {})
                    }
                )
                engines_started += 1

            # Update progress
            await self._publish_status_update(
                pipeline_id=pipeline_id,
                state=RecommendationState.GENERATING,
                progress=20.0,  # Initial progress after starting engines
                message=f"Generating candidates using {engines_started} engines"
            )

        except Exception as e:
            logger.error(f"Candidate generation failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_engine_content(self, message: ProcessingMessage) -> None:
        """Handle content-based engine response"""
        await self._process_engine_response(
            message,
            RecommendationType.CONTENT_BASED
        )

    async def _handle_engine_collaborative(self, message: ProcessingMessage) -> None:
        """Handle collaborative filtering engine response"""
        await self._process_engine_response(
            message,
            RecommendationType.COLLABORATIVE
        )

    async def _process_engine_response(
            self,
            message: ProcessingMessage,
            engine_type: RecommendationType
    ) -> None:
        """Process recommendation engine response"""
        try:
            pipeline_id = message.content['pipeline_id']
            candidates = message.content.get('candidates', [])

            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Store engine results
            context.candidates[engine_type.value] = candidates

            # Check if all engines have responded
            if len(context.candidates) == len(context.enabled_engines):
                await self._merge_candidates(pipeline_id)

        except Exception as e:
            logger.error(f"Engine response processing failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _merge_candidates(self, pipeline_id: str) -> None:
        """Merge and rank candidates from all engines"""
        try:
            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Merge candidates
            await self._publish_handler_message(
                MessageType.RECOMMENDATION_CANDIDATES_MERGE_REQUEST,
                {
                    'pipeline_id': pipeline_id,
                    'candidates': context.candidates,
                    'merge_config': context.engine_configs.get('merge_config', {})
                }
            )

        except Exception as e:
            logger.error(f"Candidate merging failed: {str(e)}")
            await self._handle_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                str(e)
            )

    async def _publish_status_update(
            self,
            pipeline_id: str,
            state: RecommendationState,
            progress: float,
            message: str
    ) -> None:
        """Publish status update"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_STATUS_RESPONSE,
                    content={
                        'pipeline_id': pipeline_id,
                        'state': state.value,
                        'progress': progress,
                        'message': message,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="recommendation_manager",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
                    ),
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            logger.error(f"Status update failed: {str(e)}")

    async def _handle_feedback_process(self, message: ProcessingMessage) -> None:
        """Process recommendation feedback"""
        try:
            pipeline_id = message.content['pipeline_id']
            feedback = message.content.get('feedback', {})

            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Store feedback
            if 'feedback_history' not in context.metrics:
                context.metrics['feedback_history'] = []
            context.metrics['feedback_history'].append(feedback)

            # Update engines with feedback
            for engine_type in context.enabled_engines:
                await self._publish_engine_message(
                    engine_type=engine_type,
                    message_type=MessageType.RECOMMENDATION_FEEDBACK_PROCESS,
                    content={
                        'pipeline_id': pipeline_id,
                        'feedback': feedback
                    }
                )

        except Exception as e:
            logger.error(f"Feedback processing failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _publish_engine_message(
            self,
            engine_type: RecommendationType,
            message_type: MessageType,
            content: Dict[str, Any]
    ) -> None:
        """Publish message to specific recommendation engine"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=message_type,
                    content=content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component=f"recommendation_engine_{engine_type.value}",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
                    ),
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            logger.error(f"Engine message publishing failed: {str(e)}")

    async def _publish_handler_message(
            self,
            message_type: MessageType,
            content: Dict[str, Any]
    ) -> None:
        """Publish message to recommendation handler"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=message_type,
                    content=content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="recommendation_handler",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
                    ),
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            logger.error(f"Handler message publishing failed: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        try:
            # Cleanup active requests
            for pipeline_id in list(self.active_requests.keys()):
                await self._handle_error(
                    ProcessingMessage(content={'pipeline_id': pipeline_id}),
                    "Service cleanup initiated"
                )
                del self.active_requests[pipeline_id]

        except Exception as e:
            logger.error(f"Service cleanup failed: {str(e)}")
            raise

    async def _handle_process_progress(self, message: ProcessingMessage) -> None:
        """Handle process progress updates"""
        try:
            pipeline_id = message.content['pipeline_id']
            progress = message.content.get('progress', 0.0)
            stage = message.content.get('stage', '')

            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Update context metrics
            context.metrics['progress'] = progress
            context.metrics[f'{stage}_progress'] = progress

            # Forward progress update
            await self._publish_status_update(
                pipeline_id=pipeline_id,
                state=context.state,
                progress=progress,
                message=f"Processing {stage}: {progress}% complete"
            )

        except Exception as e:
            logger.error(f"Progress update handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_engine_hybrid(self, message: ProcessingMessage) -> None:
        """Handle hybrid engine response"""
        try:
            pipeline_id = message.content['pipeline_id']
            hybrid_results = message.content.get('results', {})

            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Update context with hybrid results
            context.metrics['hybrid_engine'] = {
                'weight_distribution': hybrid_results.get('weights', {}),
                'blend_method': hybrid_results.get('blend_method', 'weighted_average'),
                'confidence': hybrid_results.get('confidence', 0.0)
            }

            # Process hybrid recommendations
            await self._process_engine_response(
                message,
                RecommendationType.HYBRID
            )

        except Exception as e:
            logger.error(f"Hybrid engine handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_metrics_update(self, message: ProcessingMessage) -> None:
        """Handle metrics update"""
        try:
            pipeline_id = message.content['pipeline_id']
            metrics = message.content.get('metrics', {})

            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Update context metrics
            context.metrics.update(metrics)
            context.updated_at = datetime.utcnow()

            # Check for performance thresholds
            if self._check_performance_thresholds(metrics):
                await self._handle_performance_alert(pipeline_id, metrics)

            # Forward metrics update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_METRICS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': metrics,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="recommendation_manager",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Metrics update handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    def _check_performance_thresholds(self, metrics: Dict[str, Any]) -> bool:
        """Check if metrics exceed performance thresholds"""
        thresholds = {
            'processing_time': 30.0,  # seconds
            'memory_usage': 85.0,  # percent
            'error_rate': 0.1  # 10% error rate
        }

        for metric, threshold in thresholds.items():
            if metrics.get(metric, 0) > threshold:
                return True

        return False

    async def _handle_performance_alert(self, pipeline_id: str, metrics: Dict[str, Any]) -> None:
        """Handle performance threshold alert"""
        try:
            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Create alert
            alert = {
                'type': 'performance_alert',
                'pipeline_id': pipeline_id,
                'metrics': metrics,
                'timestamp': datetime.utcnow().isoformat(),
                'message': "Performance thresholds exceeded"
            }

            # Store alert in context
            if 'alerts' not in context.metrics:
                context.metrics['alerts'] = []
            context.metrics['alerts'].append(alert)

            # Notify about alert
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_METRICS_UPDATE,
                    content=alert,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="recommendation_manager",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Performance alert handling failed: {str(e)}")

    async def _handle_config_update(self, message: ProcessingMessage) -> None:
        """Handle configuration update request"""
        try:
            pipeline_id = message.content['pipeline_id']
            config_updates = message.content.get('config', {})

            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Validate configuration updates
            validated_updates = self._validate_config_updates(config_updates)

            # Apply updates
            if context.engine_configs:
                context.engine_configs.update(validated_updates.get('engine_configs', {}))
            if context.ranking_criteria:
                context.ranking_criteria.update(validated_updates.get('ranking_criteria', {}))
            if context.validation_rules:
                context.validation_rules.update(validated_updates.get('validation_rules', {}))

            # Record update
            context.metrics['config_updates'] = context.metrics.get('config_updates', 0) + 1
            context.metrics['last_config_update'] = datetime.utcnow().isoformat()

            # Notify about config update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_CONFIG_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'updated_config': validated_updates,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="recommendation_manager",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Config update handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_process_complete(self, message: ProcessingMessage) -> None:
        """
        Handle process completion from recommendation processing.

        Args:
            message (ProcessingMessage): Message containing completion details
                Expected content:
                - pipeline_id: str
                - recommendations: List[Dict[str, Any]]
                - engine_metrics: Optional[Dict[str, Any]]
        """
        try:
            pipeline_id = message.content['pipeline_id']
            recommendations = message.content.get('recommendations', [])
            engine_metrics = message.content.get('engine_metrics', {})

            context = self.active_requests.get(pipeline_id)
            if not context:
                logger.warning(f"No active context found for pipeline {pipeline_id}")
                return

            # Update state before processing
            old_state = context.state
            context.state = RecommendationState.COMPLETED
            context.completed_at = datetime.utcnow()

            try:
                # Validate final recommendations
                validation_result = self._validate_recommendations(recommendations, context.validation_rules)
                if not validation_result['passed']:
                    logger.error(f"Final recommendations failed validation: {validation_result}")
                    await self._handle_validation_failure(pipeline_id, validation_result)
                    return

                # Calculate final metrics
                final_metrics = self._calculate_final_metrics(context, recommendations)
                final_metrics.update({
                    'engine_metrics': engine_metrics,
                    'validation_result': validation_result,
                    'processing_stages': {
                        'generation_time': context.metrics.get('generation_time', 0),
                        'ranking_time': context.metrics.get('ranking_time', 0),
                        'filtering_time': context.metrics.get('filtering_time', 0)
                    },
                    'engine_contributions': self._calculate_engine_contributions(context),
                    'quality_metrics': {
                        'diversity_score': validation_result.get('metrics', {}).get('diversity_score', 0),
                        'average_confidence': final_metrics.get('average_confidence', 0),
                        'coverage_rate': len(recommendations) / context.metrics.get('total_candidates', 1)
                    }
                })

                # Record final state in context
                context.metrics.update(final_metrics)
                context.recommendations = recommendations

                # Publish completion notification
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.RECOMMENDATION_PROCESS_COMPLETE,
                        content={
                            'pipeline_id': pipeline_id,
                            'recommendations': recommendations,
                            'metrics': final_metrics,
                            'timestamp': datetime.utcnow().isoformat(),
                            'processing_time': (context.completed_at - context.created_at).total_seconds(),
                            'engine_summary': {
                                'engines_used': len(context.enabled_engines),
                                'engine_contributions': final_metrics.get('engine_contributions', {})
                            }
                        },
                        metadata=MessageMetadata(
                            correlation_id=message.metadata.correlation_id,
                            source_component=self.module_identifier.component_name,
                            target_component="recommendation_manager",
                            domain_type="recommendation",
                            processing_stage=ProcessingStage.RECOMMENDATION,
                            requires_response=False
                        ),
                        source_identifier=self.module_identifier
                    )
                )

                # Log success with key metrics
                logger.info(
                    f"Pipeline {pipeline_id} completed successfully: "
                    f"{len(recommendations)} recommendations, "
                    f"confidence: {final_metrics.get('average_confidence', 0):.2f}, "
                    f"diversity: {final_metrics.get('quality_metrics', {}).get('diversity_score', 0):.2f}"
                )

            except Exception as inner_e:
                # Revert state on failure
                context.state = old_state
                context.completed_at = None
                raise inner_e

            finally:
                # Cleanup context only on successful completion
                if context.state == RecommendationState.COMPLETED:
                    try:
                        # Release resources
                        await self._cleanup_resources(pipeline_id)
                        # Remove from active requests
                        del self.active_requests[pipeline_id]
                    except Exception as cleanup_e:
                        logger.error(f"Error during context cleanup: {cleanup_e}")
                        # Don't raise - main completion was successful

        except Exception as e:
            logger.error(f"Process completion handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    def _calculate_engine_contributions(self, context: RecommendationContext) -> Dict[str, float]:
        """Calculate contribution metrics for each recommendation engine"""
        contributions = {}

        try:
            total_candidates = sum(len(candidates) for candidates in context.candidates.values())
            if total_candidates == 0:
                return {engine.value: 0.0 for engine in context.enabled_engines}

            for engine_type, candidates in context.candidates.items():
                engine_candidates = len(candidates)
                contribution_score = engine_candidates / total_candidates

                # Weight by engine confidence if available
                if engine_metrics := context.metrics.get('engine_metrics', {}).get(engine_type, {}):
                    confidence = engine_metrics.get('confidence', 1.0)
                    contribution_score *= confidence

                contributions[engine_type] = contribution_score

            # Normalize contributions
            total_contribution = sum(contributions.values())
            if total_contribution > 0:
                contributions = {
                    engine: score / total_contribution
                    for engine, score in contributions.items()
                }

        except Exception as e:
            logger.error(f"Error calculating engine contributions: {e}")
            contributions = {engine.value: 0.0 for engine in context.enabled_engines}

        return contributions

    async def _cleanup_resources(self, pipeline_id: str) -> None:
        """Clean up resources used by the recommendation process"""
        context = self.active_requests.get(pipeline_id)
        if not context:
            return

        try:
            # Notify engines to cleanup
            for engine_type in context.enabled_engines:
                await self._publish_engine_message(
                    engine_type=engine_type,
                    message_type=MessageType.RECOMMENDATION_CLEANUP_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                    }
                )

            # Clear cached data
            if hasattr(context, 'candidates'):
                context.candidates.clear()

        except Exception as e:
            logger.error(f"Resource cleanup error for pipeline {pipeline_id}: {e}")
            # Continue with cleanup despite errors

    def _validate_config_updates(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration updates"""
        validated = {}

        # Validate engine configs
        if 'engine_configs' in updates:
            validated['engine_configs'] = {}
            for engine, config in updates['engine_configs'].items():
                if engine in [e.value for e in RecommendationType]:
                    validated['engine_configs'][engine] = self._validate_engine_config(config)

        # Validate ranking criteria
        if 'ranking_criteria' in updates:
            ranking = updates['ranking_criteria']
            if isinstance(ranking, dict):
                # Ensure weights sum to 1.0
                weights = ranking.get('weights', {})
                if weights and abs(sum(weights.values()) - 1.0) < 0.001:
                    validated['ranking_criteria'] = ranking

        # Validate validation rules
        if 'validation_rules' in updates:
            rules = updates['validation_rules']
            if isinstance(rules, dict):
                validated['validation_rules'] = {
                    'min_recommendations': max(1, rules.get('min_recommendations', 1)),
                    'min_confidence': min(1.0, max(0.0, rules.get('min_confidence', 0.5))),
                    'check_diversity': bool(rules.get('check_diversity', False)),
                    'min_diversity': min(1.0, max(0.0, rules.get('min_diversity', 0.3)))
                }

        return validated

    def _validate_engine_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate engine-specific configuration"""
        validated = {}

        # Common parameters
        if 'weight' in config:
            validated['weight'] = min(1.0, max(0.0, config['weight']))
        if 'enabled' in config:
            validated['enabled'] = bool(config['enabled'])
        if 'parameters' in config and isinstance(config['parameters'], dict):
            validated['parameters'] = config['parameters']

        # Engine-specific validation could be added here
        return validated

    async def _handle_process_error(self, message: ProcessingMessage) -> None:
        """Handle process error"""
        try:
            pipeline_id = message.content['pipeline_id']
            error = message.content.get('error', 'Unknown error')

            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Update context
            context.state = RecommendationState.FAILED
            context.errors.append({
                'error': error,
                'timestamp': datetime.utcnow().isoformat(),
                'component': message.metadata.source_component
            })

            # Check for retry possibility
            if self._should_retry(context):
                await self._retry_process(pipeline_id)
            else:
                # Process has failed permanently
                await self._handle_permanent_failure(pipeline_id, error)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    def _should_retry(self, context: RecommendationContext) -> bool:
        """Determine if process should be retried"""
        # Check retry count
        retry_limit = context.engine_configs.get('max_retries', 3)
        current_retries = len([e for e in context.errors if e.get('retried', False)])

        if current_retries >= retry_limit:
            return False

        # Check error types
        latest_error = context.errors[-1] if context.errors else None
        if latest_error:
            # Don't retry certain error types
            non_retryable = ['configuration_error', 'validation_error', 'permanent_failure']
            if latest_error.get('type') in non_retryable:
                return False

        return True

    async def _retry_process(self, pipeline_id: str) -> None:
        """Retry the recommendation process"""
        try:
            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Mark latest error as retried
            if context.errors:
                context.errors[-1]['retried'] = True

            # Reset state
            context.state = RecommendationState.INITIALIZING
            context.candidates = {}

            # Reinitialize engines
            await self._initialize_engines(pipeline_id, context.engine_configs)

            # Update metrics
            context.metrics['retry_count'] = context.metrics.get('retry_count', 0) + 1
            context.metrics['last_retry'] = datetime.utcnow().isoformat()

            # Notify about retry
            await self._publish_status_update(
                pipeline_id=pipeline_id,
                state=RecommendationState.INITIALIZING,
                progress=0.0,
                message=f"Retrying process (attempt {context.metrics['retry_count']})"
            )

        except Exception as e:
            logger.error(f"Process retry failed: {str(e)}")
            await self._handle_permanent_failure(pipeline_id, str(e))

    async def _handle_permanent_failure(self, pipeline_id: str, error: str) -> None:
        """Handle permanent process failure"""
        try:
            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Update final state
            context.state = RecommendationState.FAILED
            context.completed_at = datetime.utcnow()

            # Calculate error metrics
            error_metrics = {
                'total_errors': len(context.errors),
                'error_types': {},
                'retry_count': context.metrics.get('retry_count', 0),
                'final_error': error,
                'processing_time': (context.completed_at - context.created_at).total_seconds()
            }

            # Count error types
            for err in context.errors:
                err_type = err.get('type', 'unknown')
                error_metrics['error_types'][err_type] = error_metrics['error_types'].get(err_type, 0) + 1

            # Send failure notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_PROCESS_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'error_metrics': error_metrics,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="recommendation_manager",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup context
            del self.active_requests[pipeline_id]

        except Exception as e:
            logger.error(f"Permanent failure handling failed: {str(e)}")

    def _calculate_final_metrics(self, context: RecommendationContext, recommendations: List[Dict[str, Any]]) -> Dict[
        str, Any]:
        """Calculate final recommendation metrics"""
        metrics = {
            'total_recommendations': len(recommendations),
            'processing_time': (datetime.utcnow() - context.created_at).total_seconds(),
            'engines_used': len(context.enabled_engines),
            'average_confidence': 0.0,
            'diversity_score': 0.0
        }

        # Calculate average confidence
        if recommendations:
            confidence_sum = sum(rec.get('confidence', 0) for rec in recommendations)
            metrics['average_confidence'] = confidence_sum / len(recommendations)

        # Calculate diversity score (if available)
        if 'diversity_scores' in context.metrics:
            metrics['diversity_score'] = context.metrics['diversity_scores'].get('final', 0.0)

        return metrics


    async def _handle_candidates_filter(self, message: ProcessingMessage) -> None:
        """Handle candidate filtering request"""
        try:
            pipeline_id = message.content['pipeline_id']
            candidates = message.content.get('candidates', [])
            filter_config = message.content.get('filter_config', {})

            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Update state
            context.state = RecommendationState.FILTERING

            # Apply filters
            filtered_candidates = await self._apply_filters(candidates, filter_config)

            # Update context
            context.metrics['filtered_count'] = len(filtered_candidates)

            # Move to ranking
            await self._publish_handler_message(
                MessageType.RECOMMENDATION_CANDIDATES_RANK_REQUEST,
                {
                    'pipeline_id': pipeline_id,
                    'candidates': filtered_candidates,
                    'ranking_config': context.ranking_criteria
                }
            )

            # Update progress
            await self._publish_status_update(
                pipeline_id=pipeline_id,
                state=RecommendationState.FILTERING,
                progress=60.0,
                message=f"Filtered candidates: {len(filtered_candidates)} remaining"
            )

        except Exception as e:
            logger.error(f"Candidate filtering failed: {str(e)}")
            await self._handle_error(message, str(e))


    async def _apply_filters(
            self,
            candidates: List[Dict[str, Any]],
            filter_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filtering rules to candidates"""
        filtered = candidates.copy()

        # Apply minimum confidence threshold
        min_confidence = filter_config.get('min_confidence', 0.5)
        filtered = [c for c in filtered if c.get('confidence', 0) >= min_confidence]

        # Apply diversity filtering if configured
        if filter_config.get('ensure_diversity', False):
            filtered = self._apply_diversity_filter(filtered, filter_config)

        # Apply business rules
        if 'business_rules' in filter_config:
            filtered = self._apply_business_rules(filtered, filter_config['business_rules'])

        return filtered


    def _apply_diversity_filter(
            self,
            candidates: List[Dict[str, Any]],
            config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply diversity filtering to candidates"""
        if not candidates:
            return []

        diversity_config = config.get('diversity_config', {})
        max_similar = diversity_config.get('max_similar_items', 2)
        similarity_threshold = diversity_config.get('similarity_threshold', 0.8)

        diverse_candidates = []
        categories = {}  # Track items by category

        for candidate in candidates:
            category = candidate.get('category', 'default')

            # Check if we've reached maximum for this category
            if category in categories and len(categories[category]) >= max_similar:
                continue

            # Check similarity with already selected items
            if self._is_sufficiently_different(candidate, diverse_candidates, similarity_threshold):
                diverse_candidates.append(candidate)
                categories.setdefault(category, []).append(candidate)

        return diverse_candidates


    def _is_sufficiently_different(
            self,
            candidate: Dict[str, Any],
            selected: List[Dict[str, Any]],
            threshold: float
    ) -> bool:
        """Check if candidate is sufficiently different from selected items"""
        if not selected:
            return True

        for item in selected:
            similarity = self._calculate_similarity(candidate, item)
            if similarity > threshold:
                return False
        return True


    def _calculate_similarity(self, item1: Dict[str, Any], item2: Dict[str, Any]) -> float:
        """Calculate similarity between two items"""
        # Get feature vectors
        features1 = item1.get('features', {})
        features2 = item2.get('features', {})

        # If no features, use category comparison
        if not features1 or not features2:
            return 1.0 if item1.get('category') == item2.get('category') else 0.0

        # Calculate cosine similarity of feature vectors
        common_features = set(features1.keys()) & set(features2.keys())
        if not common_features:
            return 0.0

        dot_product = sum(features1[f] * features2[f] for f in common_features)
        norm1 = sum(v * v for v in features1.values()) ** 0.5
        norm2 = sum(v * v for v in features2.values()) ** 0.5

        return dot_product / (norm1 * norm2) if norm1 * norm2 > 0 else 0.0


    async def _handle_candidates_rank(self, message: ProcessingMessage) -> None:
        """Handle candidate ranking request"""
        try:
            pipeline_id = message.content['pipeline_id']
            candidates = message.content.get('candidates', [])
            ranking_config = message.content.get('ranking_config', {})

            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Update state
            context.state = RecommendationState.RANKING

            # Apply ranking
            ranked_candidates = self._rank_candidates(candidates, ranking_config)

            # Update metrics
            context.metrics['ranking_completed'] = datetime.utcnow().isoformat()
            context.metrics['ranked_count'] = len(ranked_candidates)

            # Move to validation
            await self._publish_handler_message(
                MessageType.RECOMMENDATION_VALIDATE_REQUEST,
                {
                    'pipeline_id': pipeline_id,
                    'candidates': ranked_candidates,
                    'validation_config': context.validation_rules
                }
            )

            # Update progress
            await self._publish_status_update(
                pipeline_id=pipeline_id,
                state=RecommendationState.RANKING,
                progress=80.0,
                message="Candidates ranked and ready for validation"
            )

        except Exception as e:
            logger.error(f"Candidate ranking failed: {str(e)}")
            await self._handle_error(message, str(e))


    def _rank_candidates(
            self,
            candidates: List[Dict[str, Any]],
            ranking_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Rank candidates based on multiple criteria"""
        if not candidates:
            return []

        # Get ranking weights
        weights = ranking_config.get('weights', {
            'confidence': 0.4,
            'relevance': 0.3,
            'diversity': 0.2,
            'recency': 0.1
        })

        # Calculate scores
        ranked = []
        for candidate in candidates:
            score = sum(
                weights[criterion] * self._get_criterion_score(candidate, criterion)
                for criterion in weights.keys()
            )
            ranked.append({**candidate, 'final_score': score})

        # Sort by final score
        return sorted(ranked, key=lambda x: x['final_score'], reverse=True)


    def _get_criterion_score(self, candidate: Dict[str, Any], criterion: str) -> float:
        """Get normalized score for a specific ranking criterion"""
        if criterion == 'confidence':
            return candidate.get('confidence', 0)
        elif criterion == 'relevance':
            return candidate.get('relevance_score', 0)
        elif criterion == 'diversity':
            return candidate.get('diversity_score', 0.5)  # Default medium diversity
        elif criterion == 'recency':
            # Calculate recency score (1.0 for new items, decreasing with age)
            created_at = datetime.fromisoformat(candidate.get('created_at', datetime.utcnow().isoformat()))
            age_days = (datetime.utcnow() - created_at).days
            return max(0, 1 - (age_days / 30))  # Linear decay over 30 days
        return 0


    async def _handle_validation_request(self, message: ProcessingMessage) -> None:
        """Handle recommendation validation request"""
        try:
            pipeline_id = message.content['pipeline_id']
            candidates = message.content.get('candidates', [])
            validation_config = message.content.get('validation_config', {})

            context = self.active_requests.get(pipeline_id)
            if not context:
                return

            # Validate recommendations
            validation_result = self._validate_recommendations(candidates, validation_config)

            if validation_result['passed']:
                # Process completion
                await self._handle_process_complete(
                    ProcessingMessage(
                        message_type=MessageType.RECOMMENDATION_PROCESS_COMPLETE,
                        content={
                            'pipeline_id': pipeline_id,
                            'recommendations': candidates,
                            'validation_result': validation_result
                        },
                        metadata=message.metadata,
                        source_identifier=self.module_identifier
                    )
                )
            else:
                # Handle validation failure
                await self._handle_validation_failure(pipeline_id, validation_result)

        except Exception as e:
            logger.error(f"Validation request handling failed: {str(e)}")
            await self._handle_error(message, str(e))


    def _validate_recommendations(
            self,
            candidates: List[Dict[str, Any]],
            validation_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate final recommendations"""
        validation_result = {
            'passed': True,
            'checks': [],
            'metrics': {}
        }

        # Check minimum recommendations
        min_recommendations = validation_config.get('min_recommendations', 1)
        if len(candidates) < min_recommendations:
            validation_result['passed'] = False
            validation_result['checks'].append({
                'check': 'minimum_recommendations',
                'passed': False,
                'message': f"Not enough recommendations: {len(candidates)} < {min_recommendations}"
            })

        # Check confidence threshold
        min_confidence = validation_config.get('min_confidence', 0.5)
        low_confidence = [c for c in candidates if c.get('confidence', 0) < min_confidence]
        if low_confidence:
            validation_result['checks'].append({
                'check': 'confidence_threshold',
                'passed': False,
                'message': f"{len(low_confidence)} recommendations below confidence threshold"
            })

        # Check diversity
        if validation_config.get('check_diversity', False):
            diversity_score = self._calculate_diversity_score(candidates)
            validation_result['metrics']['diversity_score'] = diversity_score

            min_diversity = validation_config.get('min_diversity', 0.3)
            if diversity_score < min_diversity:
                validation_result['checks'].append({
                    'check': 'diversity_threshold',
                    'passed': False,
                    'message': f"Diversity score {diversity_score} below threshold {min_diversity}"
                })

        return validation_result


    def _calculate_diversity_score(self, candidates: List[Dict[str, Any]]) -> float:
        """Calculate diversity score for recommendations"""
        if not candidates:
            return 0.0

        # Calculate pairwise similarities
        similarities = []
        for i, c1 in enumerate(candidates[:-1]):
            for c2 in candidates[i + 1:]:
                similarities.append(self._calculate_similarity(c1, c2))

        # Average similarity (convert to diversity)
        if not similarities:
            return 1.0
        return 1.0 - (sum(similarities) / len(similarities))

    async def _handle_validation_failure(self, pipeline_id: str, validation_result: Dict[str, Any]) -> None:
        """
        Handle recommendation validation failure.

        Args:
            pipeline_id (str): Pipeline identifier
            validation_result (Dict[str, Any]): Results from validation containing:
                - passed (bool): Overall validation status
                - checks (List[Dict]): List of validation checks performed
                - metrics (Dict): Optional validation metrics
        """
        try:
            context = self.active_requests.get(pipeline_id)
            if not context:
                logger.warning(f"No active context found for pipeline {pipeline_id}")
                return

            # Update context state
            context.state = RecommendationState.VALIDATION_PENDING
            context.metrics['validation_failures'] = context.metrics.get('validation_failures', 0) + 1

            # Store validation details
            failure_details = {
                'timestamp': datetime.utcnow().isoformat(),
                'validation_result': validation_result,
                'retry_count': context.metrics.get('validation_failures', 0)
            }

            if 'validation_history' not in context.metrics:
                context.metrics['validation_history'] = []
            context.metrics['validation_history'].append(failure_details)

            # Check if we should retry
            if self._should_retry_validation(context):
                # Prepare for retry
                await self._prepare_validation_retry(pipeline_id, validation_result)
            else:
                # Create decision point for manual intervention
                await self._create_validation_decision_point(pipeline_id, validation_result)

            # Notify about validation failure
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_VALIDATE_REJECT,
                    content={
                        'pipeline_id': pipeline_id,
                        'validation_result': validation_result,
                        'failure_details': failure_details,
                        'retry_eligible': self._should_retry_validation(context),
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="recommendation_manager",
                        domain_type="recommendation",
                        processing_stage=ProcessingStage.RECOMMENDATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Validation failure handling failed: {str(e)}")
            await self._handle_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                f"Validation failure handling error: {str(e)}"
            )

    def _should_retry_validation(self, context: RecommendationContext) -> bool:
        """
        Determine if validation should be retried.

        Args:
            context (RecommendationContext): Current recommendation context

        Returns:
            bool: True if validation should be retried, False otherwise
        """
        # Check retry count
        max_validation_retries = context.validation_rules.get('max_retries', 3)
        current_retries = context.metrics.get('validation_failures', 0)

        if current_retries >= max_validation_retries:
            return False

        # Check if failures are getting worse
        validation_history = context.metrics.get('validation_history', [])
        if len(validation_history) >= 2:
            last_result = validation_history[-1]['validation_result']
            previous_result = validation_history[-2]['validation_result']

            # Compare validation metrics
            last_metrics = last_result.get('metrics', {})
            prev_metrics = previous_result.get('metrics', {})

            # If metrics are degrading, don't retry
            if all(last_metrics.get(key, 0) <= prev_metrics.get(key, 0)
                   for key in ['diversity_score', 'confidence_score']):
                return False

        return True

    async def _prepare_validation_retry(self, pipeline_id: str, validation_result: Dict[str, Any]) -> None:
        """
        Prepare for validation retry by adjusting parameters.

        Args:
            pipeline_id (str): Pipeline identifier
            validation_result (Dict[str, Any]): Previous validation result
        """
        context = self.active_requests.get(pipeline_id)
        if not context:
            return

        # Adjust parameters based on validation failures
        failed_checks = [check for check in validation_result.get('checks', [])
                         if not check.get('passed', False)]

        for check in failed_checks:
            check_type = check.get('check')
            if check_type == 'diversity_threshold':
                # Increase diversity in ranking
                if 'ranking_criteria' in context.engine_configs:
                    context.engine_configs['ranking_criteria']['diversity_weight'] = \
                        context.engine_configs['ranking_criteria'].get('diversity_weight', 0.2) * 1.2

            elif check_type == 'confidence_threshold':
                # Adjust confidence thresholds
                for engine_type in context.enabled_engines:
                    if engine_config := context.engine_configs.get(engine_type.value):
                        engine_config['min_confidence'] = \
                            engine_config.get('min_confidence', 0.5) * 1.1

        # Schedule retry
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.RECOMMENDATION_VALIDATE_RETRY,
                content={
                    'pipeline_id': pipeline_id,
                    'updated_config': context.engine_configs,
                    'retry_count': context.metrics.get('validation_failures', 0),
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="recommendation_handler",
                    domain_type="recommendation",
                    processing_stage=ProcessingStage.RECOMMENDATION
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _create_validation_decision_point(self, pipeline_id: str, validation_result: Dict[str, Any]) -> None:
        """
        Create a decision point for manual validation handling.

        Args:
            pipeline_id (str): Pipeline identifier
            validation_result (Dict[str, Any]): Validation result that caused the failure
        """
        context = self.active_requests.get(pipeline_id)
        if not context:
            return

        # Update state for decision
        context.state = RecommendationState.AWAITING_DECISION
        context.pending_decision = {
            'type': 'validation_failure',
            'validation_result': validation_result,
            'options': ['force_approve', 'modify_criteria', 'retry_validation', 'abort'],
            'timestamp': datetime.utcnow().isoformat()
        }

        # Notify about required decision
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.RECOMMENDATION_VALIDATE_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'validation_result': validation_result,
                    'requires_decision': True,
                    'decision_options': context.pending_decision['options'],
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="recommendation_manager",
                    domain_type="recommendation",
                    processing_stage=ProcessingStage.RECOMMENDATION
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_candidates_merge(self, message: ProcessingMessage) -> None:
        """
        Handle candidate merging from multiple recommendation engines.

        Args:
            message (ProcessingMessage): Message containing candidates to merge
                Expected content:
                - pipeline_id: str
                - candidates: Dict[str, List[Dict[str, Any]]] (by engine)
                - merge_config: Optional[Dict[str, Any]]
        """
        try:
            pipeline_id = message.content['pipeline_id']
            candidates_by_engine = message.content.get('candidates', {})
            merge_config = message.content.get('merge_config', {})

            context = self.active_requests.get(pipeline_id)
            if not context:
                logger.warning(f"No active context found for pipeline {pipeline_id}")
                return

            # Update state
            context.state = RecommendationState.RANKING
            merge_start_time = datetime.utcnow()

            # Get engine weights
            engine_weights = self._get_engine_weights(context, merge_config)

            # Merge candidates
            merged_candidates = self._merge_engine_candidates(
                candidates_by_engine,
                engine_weights,
                merge_config
            )

            # Track merging metrics
            merge_duration = (datetime.utcnow() - merge_start_time).total_seconds()
            merge_metrics = {
                'merge_duration': merge_duration,
                'candidates_per_engine': {
                    engine: len(candidates)
                    for engine, candidates in candidates_by_engine.items()
                },
                'total_merged': len(merged_candidates),
                'engine_weights': engine_weights
            }

            context.metrics.update({
                'merge_metrics': merge_metrics,
                'merge_timestamp': datetime.utcnow().isoformat()
            })

            # Forward to ranking
            await self._publish_handler_message(
                MessageType.RECOMMENDATION_CANDIDATES_RANK_REQUEST,
                {
                    'pipeline_id': pipeline_id,
                    'candidates': merged_candidates,
                    'merge_metrics': merge_metrics,
                    'ranking_config': context.ranking_criteria,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Candidate merging failed: {str(e)}")
            await self._handle_error(message, str(e))


    def _merge_engine_candidates(
            self,
            candidates_by_engine: Dict[str, List[Dict[str, Any]]],
            engine_weights: Dict[str, float],
            merge_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Merge candidates from multiple engines with weighting.

        Args:
            candidates_by_engine: Candidates grouped by engine
            engine_weights: Weight for each engine's recommendations
            merge_config: Configuration for merging process

        Returns:
            List[Dict[str, Any]]: Merged and normalized candidates
        """
        # Track merged candidates by ID to avoid duplicates
        merged_map = {}

        min_confidence = merge_config.get('min_confidence', 0.5)
        max_candidates = merge_config.get('max_candidates', 100)

        for engine, candidates in candidates_by_engine.items():
            engine_weight = engine_weights.get(engine, 1.0)

            for candidate in candidates:
                candidate_id = candidate.get('id')
                if not candidate_id:
                    continue

                # Skip low confidence candidates
                confidence = candidate.get('confidence', 0)
                if confidence < min_confidence:
                    continue

                if candidate_id in merged_map:
                    # Combine with existing candidate
                    existing = merged_map[candidate_id]
                    merged = self._combine_candidates(
                        existing,
                        candidate,
                        engine_weight
                    )
                    merged_map[candidate_id] = merged
                else:
                    # Add new candidate with weighted confidence
                    candidate['confidence'] *= engine_weight
                    candidate['source_engines'] = [engine]
                    merged_map[candidate_id] = candidate

        # Convert to list and sort by confidence
        merged_candidates = list(merged_map.values())
        merged_candidates.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        # Apply max candidates limit
        return merged_candidates[:max_candidates]


    def _combine_candidates(
            self,
            existing: Dict[str, Any],
            new: Dict[str, Any],
            engine_weight: float
    ) -> Dict[str, Any]:
        """
        Combine two candidates for the same item.

        Args:
            existing: Existing candidate entry
            new: New candidate entry to merge
            engine_weight: Weight of the new candidate's engine

        Returns:
            Dict[str, Any]: Combined candidate entry
        """
        # Weighted confidence combination
        total_weight = sum(1.0 for _ in existing.get('source_engines', []))
        total_weight += engine_weight

        combined_confidence = (
                                      existing.get('confidence', 0) * (total_weight - engine_weight) +
                                      new.get('confidence', 0) * engine_weight
                              ) / total_weight

        # Combine features if present
        combined_features = existing.get('features', {}).copy()
        if new_features := new.get('features'):
            for feature, value in new_features.items():
                if feature in combined_features:
                    combined_features[feature] = (
                                                         combined_features[feature] * (total_weight - engine_weight) +
                                                         value * engine_weight
                                                 ) / total_weight
                else:
                    combined_features[feature] = value

        # Create combined candidate
        combined = existing.copy()
        combined.update({
            'confidence': combined_confidence,
            'features': combined_features,
            'source_engines': existing.get('source_engines', []) + [new.get('source_engines', ['unknown'])[0]]
        })

        return combined


    def _get_engine_weights(
            self,
            context: RecommendationContext,
            merge_config: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Get weights for each recommendation engine.

        Args:
            context: Current recommendation context
            merge_config: Merging configuration

        Returns:
            Dict[str, float]: Weight for each engine
        """
        weights = merge_config.get('engine_weights', {})

        # Use configured weights or default to equal weighting
        if not weights:
            default_weight = 1.0 / len(context.enabled_engines)
            weights = {engine.value: default_weight for engine in context.enabled_engines}

        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        return weights


    async def _handle_engine_contextual(self, message: ProcessingMessage) -> None:
        """
        Handle response from contextual recommendation engine.

        Args:
            message (ProcessingMessage): Message containing contextual engine results
                Expected content:
                - pipeline_id: str
                - candidates: List[Dict[str, Any]]
                - context_factors: Dict[str, Any]
                - confidence_scores: Dict[str, float]
        """
        try:
            pipeline_id = message.content['pipeline_id']
            candidates = message.content.get('candidates', [])
            context_factors = message.content.get('context_factors', {})
            confidence_scores = message.content.get('confidence_scores', {})

            context = self.active_requests.get(pipeline_id)
            if not context:
                logger.warning(f"No active context found for pipeline {pipeline_id}")
                return

            # Process contextual factors
            processed_candidates = self._process_contextual_candidates(
                candidates,
                context_factors,
                confidence_scores
            )

            # Store engine results
            engine_metrics = {
                'candidates_count': len(candidates),
                'context_factors_used': list(context_factors.keys()),
                'average_confidence': sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0,
                'timestamp': datetime.utcnow().isoformat()
            }

            context.candidates[RecommendationType.CONTEXTUAL.value] = processed_candidates
            context.metrics['contextual_engine'] = engine_metrics

            # Check if all engines have responded
            if len(context.candidates) == len(context.enabled_engines):
                await self._handle_candidates_merge(
                    ProcessingMessage(
                        message_type=MessageType.RECOMMENDATION_CANDIDATES_MERGE_REQUEST,
                        content={
                            'pipeline_id': pipeline_id,
                            'candidates': context.candidates,
                            'merge_config': context.engine_configs.get('merge_config', {})
                        },
                        metadata=message.metadata,
                        source_identifier=self.module_identifier
                    )
                )

        except Exception as e:
            logger.error(f"Contextual engine handling failed: {str(e)}")
            await self._handle_error(message, str(e))


    def _process_contextual_candidates(
            self,
            candidates: List[Dict[str, Any]],
            context_factors: Dict[str, Any],
            confidence_scores: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Process and enhance candidates with contextual information.

        Args:
            candidates: Raw candidates from contextual engine
            context_factors: Contextual factors used
            confidence_scores: Confidence scores by factor

        Returns:
            List[Dict[str, Any]]: Processed candidates with enhanced context
        """
        processed = []

        for candidate in candidates:
            # Enhance candidate with contextual information
            enhanced = candidate.copy()

            # Add context factor influence
            if 'features' not in enhanced:
                enhanced['features'] = {}

            for factor, value in context_factors.items():
                if factor_confidence := confidence_scores.get(factor):
                    enhanced['features'][f'context_{factor}'] = value * factor_confidence

            # Calculate overall contextual confidence
            contextual_confidence = sum(
                confidence_scores.get(factor, 0) * value
                for factor, value in context_factors.items()
            ) / len(context_factors) if context_factors else 0

            enhanced['confidence'] = (
                    enhanced.get('confidence', 0) * 0.7 +  # Base confidence
                    contextual_confidence * 0.3  # Contextual boost
            )

            enhanced['context_factors'] = context_factors
            processed.append(enhanced)

        return processed