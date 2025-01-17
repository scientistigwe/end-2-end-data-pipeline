# backend/core/handlers/channel/insight_handler.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    MessageMetadata
)
from backend.core.staging.staging_manager import StagingManager
from backend.core.handlers.base.base_handler import BaseChannelHandler, HandlerState
from backend.data.processing.insights.processor.insight_processor import InsightProcessor
from backend.data.processing.insights.types.insight_types import (
    InsightType,
    InsightStatus,
    InsightPhase,
    InsightContext,
    InsightConfig,
    InsightProcessState,
    InsightMetrics
)

logger = logging.getLogger(__name__)


class InsightHandler(BaseChannelHandler):
    """
    Handler for insight generation operations.
    Coordinates between manager, processor, and staging area.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        super().__init__(
            message_broker=message_broker,
            handler_name="insight_handler",
            domain_type="insights"
        )

        # Initialize components
        self.staging_manager = staging_manager
        self.insight_processor = InsightProcessor(
            message_broker=message_broker,
            staging_manager=staging_manager
        )

        # State tracking
        self.active_processes: Dict[str, InsightProcessState] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup handlers for insight-specific messages"""
        self.register_message_handler(
            MessageType.INSIGHT_START,
            self._handle_insight_start
        )
        self.register_message_handler(
            MessageType.INSIGHT_UPDATE,
            self._handle_insight_update
        )
        self.register_message_handler(
            MessageType.INSIGHT_VALIDATE,
            self._handle_insight_validation
        )
        self.register_message_handler(
            MessageType.INSIGHT_REVIEW,
            self._handle_insight_review
        )

    async def _handle_insight_start(self, message: ProcessingMessage) -> None:
        """Handle start of insight generation process"""
        pipeline_id = message.content.get('pipeline_id')
        staged_id = message.content.get('staged_id')
        config = message.content.get('config', {})

        try:
            # Initialize process state
            process_state = InsightProcessState(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                current_status=InsightStatus.INITIALIZING,
                current_phase=InsightPhase.INITIALIZATION,
                metrics=InsightMetrics(
                    total_insights=0,
                    insights_by_type={},
                    insights_by_priority={},
                    average_confidence=0.0,
                    validation_rate=0.0
                )
            )
            self.active_processes[pipeline_id] = process_state

            # Create insight config
            insight_config = InsightConfig(
                enabled_types=config.get('enabled_types', list(InsightType)),
                priority_threshold=config.get('priority_threshold', 0.5),
                confidence_threshold=config.get('confidence_threshold', 0.7),
                time_window=config.get('time_window'),
                max_insights=config.get('max_insights'),
                custom_rules=config.get('custom_rules', {})
            )

            # Analyze context
            context = await self.insight_processor.analyze_context(
                data=await self._get_staged_data(staged_id),
                metadata={
                    'pipeline_id': pipeline_id,
                    'staged_id': staged_id,
                    'quality_check_passed': config.get('quality_check_passed', True),
                    'domain_type': config.get('domain_type')
                }
            )

            # Update state
            process_state.current_status = InsightStatus.PROCESSING
            process_state.current_phase = InsightPhase.PATTERN_DETECTION
            process_state.updated_at = datetime.now()

            # Generate insights
            results = await self.insight_processor.generate_insights(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                context=context,
                config=insight_config
            )

            # Update process state
            self._update_process_state(
                pipeline_id=pipeline_id,
                results=results,
                phase=InsightPhase.INSIGHT_GENERATION
            )

            # Notify about completion
            await self._notify_insight_results(
                pipeline_id=pipeline_id,
                results=results,
                state=process_state
            )

        except Exception as e:
            await self._handle_insight_error(
                pipeline_id=pipeline_id,
                phase="initialization",
                error=str(e)
            )

    async def _handle_insight_update(self, message: ProcessingMessage) -> None:
        """Handle insight process updates"""
        pipeline_id = message.content.get('pipeline_id')
        update_type = message.content.get('update_type')
        update_data = message.content.get('update_data', {})

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                raise ValueError(f"No active process found for pipeline: {pipeline_id}")

            # Update process state
            if update_type == "metrics":
                self._update_insight_metrics(process_state, update_data)
            elif update_type == "insights":
                self._update_insight_counts(process_state, update_data)

            # Notify about update
            await self._notify_insight_update(
                pipeline_id=pipeline_id,
                update_type=update_type,
                update_data=update_data
            )

        except Exception as e:
            await self._handle_insight_error(
                pipeline_id=pipeline_id,
                phase="update",
                error=str(e)
            )

    async def _handle_insight_validation(self, message: ProcessingMessage) -> None:
        """Handle validation of generated insights"""
        pipeline_id = message.content.get('pipeline_id')
        staged_id = message.content.get('staged_id')
        insights = message.content.get('insights', {})

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                raise ValueError(f"No active process found for pipeline: {pipeline_id}")

            # Update state
            process_state.current_status = InsightStatus.VALIDATING
            process_state.current_phase = InsightPhase.VALIDATION
            process_state.updated_at = datetime.now()

            # Validate insights
            validation_results = await self.insight_processor.validate_insights(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                insights=insights
            )

            # Update process state
            self._update_process_state(
                pipeline_id=pipeline_id,
                results=validation_results,
                phase=InsightPhase.VALIDATION
            )

            # Check if review needed
            requires_review = self._check_requires_review(validation_results)
            if requires_review:
                process_state.current_status = InsightStatus.AWAITING_REVIEW
                process_state.requires_review = True
                await self._notify_review_needed(
                    pipeline_id=pipeline_id,
                    validation_results=validation_results
                )
            else:
                # Complete process
                await self._complete_insight_process(
                    pipeline_id=pipeline_id,
                    results=validation_results
                )

        except Exception as e:
            await self._handle_insight_error(
                pipeline_id=pipeline_id,
                phase="validation",
                error=str(e)
            )

    async def _handle_insight_review(self, message: ProcessingMessage) -> None:
        """Handle insight review decisions"""
        pipeline_id = message.content.get('pipeline_id')
        staged_id = message.content.get('staged_id')
        review_decisions = message.content.get('decisions', {})

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                raise ValueError(f"No active process found for pipeline: {pipeline_id}")

            # Apply review decisions
            final_results = await self._apply_review_decisions(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                decisions=review_decisions
            )

            # Complete process
            await self._complete_insight_process(
                pipeline_id=pipeline_id,
                results=final_results
            )

        except Exception as e:
            await self._handle_insight_error(
                pipeline_id=pipeline_id,
                phase="review",
                error=str(e)
            )

    async def _get_staged_data(self, staged_id: str) -> Any:
        """Get data from staging area"""
        staged_data = await self.staging_manager.get_staged_data(staged_id)
        if not staged_data:
            raise ValueError(f"No data found in staging for ID: {staged_id}")
        return staged_data.get('data')

    def _update_process_state(
            self,
            pipeline_id: str,
            results: Dict[str, Any],
            phase: InsightPhase
    ) -> None:
        """Update insight process state"""
        process_state = self.active_processes.get(pipeline_id)
        if not process_state:
            return

        if phase == InsightPhase.INSIGHT_GENERATION:
            insights = results.get('insights', {})
            process_state.insights_generated = sum(
                len(type_insights.get('insights', []))
                for type_insights in insights.values()
            )

        elif phase == InsightPhase.VALIDATION:
            validations = results.get('validations', {})
            process_state.insights_validated = sum(
                val['summary']['passed']
                for val in validations.values()
            )

        process_state.current_phase = phase
        process_state.updated_at = datetime.now()

    def _update_insight_metrics(
            self,
            process_state: InsightProcessState,
            metrics_data: Dict[str, Any]
    ) -> None:
        """Update insight metrics"""
        metrics = process_state.metrics
        metrics.total_insights = metrics_data.get('total_insights', metrics.total_insights)
        metrics.average_confidence = metrics_data.get('average_confidence', metrics.average_confidence)
        metrics.validation_rate = metrics_data.get('validation_rate', metrics.validation_rate)

        if 'insights_by_type' in metrics_data:
            metrics.insights_by_type.update(metrics_data['insights_by_type'])
        if 'insights_by_priority' in metrics_data:
            metrics.insights_by_priority.update(metrics_data['insights_by_priority'])

    def _update_insight_counts(
            self,
            process_state: InsightProcessState,
            count_data: Dict[str, Any]
    ) -> None:
        """Update insight counts"""
        process_state.insights_generated = count_data.get(
            'generated',
            process_state.insights_generated
        )
        process_state.insights_validated = count_data.get(
            'validated',
            process_state.insights_validated
        )

    def _check_requires_review(
            self,
            validation_results: Dict[str, Any]
    ) -> bool:
        """Check if insights require review"""
        validations = validation_results.get('validations', {})
        for type_validations in validations.values():
            summary = type_validations['summary']
            if summary['failed'] > 0:
                return True
            if any(v['validation_score'] < 0.8 for v in type_validations['validations']):
                return True
        return False

    async def _apply_review_decisions(
            self,
            pipeline_id: str,
            staged_id: str,
            decisions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply review decisions to insights"""
        try:
            # Get current insights
            staged_data = await self.staging_manager.get_staged_data(staged_id)
            if not staged_data:
                raise ValueError(f"No insight data found for ID: {staged_id}")

            insights = staged_data.get('data', {})
            final_insights = {}

            # Apply decisions
            for insight_type, type_insights in insights.items():
                type_decisions = decisions.get(insight_type, {})
                approved_insights = []

                for insight in type_insights.get('insights', []):
                    decision = type_decisions.get(insight['insight_id'])
                    if decision and decision.get('approved', False):
                        insight['reviewed_by'] = decision.get('reviewer')
                        insight['review_notes'] = decision.get('notes')
                        approved_insights.append(insight)

                if approved_insights:
                    final_insights[insight_type] = {
                        'insights': approved_insights,
                        'metadata': type_insights.get('metadata', {})
                    }

            # Store final results
            final_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=final_insights,
                metadata={
                    'pipeline_id': pipeline_id,
                    'review_summary': {
                        'total_reviewed': len(decisions),
                        'total_approved': sum(
                            1 for d in decisions.values()
                            if d.get('approved', False)
                        )
                    }
                }
            )

            return {
                'staged_id': final_staged_id,
                'insights': final_insights
            }

        except Exception as e:
            self.logger.error(f"Failed to apply review decisions: {str(e)}")
            raise

    async def _complete_insight_process(
            self,
            pipeline_id: str,
            results: Dict[str, Any]
    ) -> None:
        """Complete insight process"""
        try:
            process_state = self.active_processes[pipeline_id]
            process_state.current_status = InsightStatus.COMPLETED
            process_state.updated_at = datetime.now()

            # Notify about completion
            await self._notify_insight_completion(
                pipeline_id=pipeline_id,
                results=results,
                state=process_state
            )

            # Cleanup
            del self.active_processes[pipeline_id]

        except Exception as e:
            await self._handle_insight_error(
                pipeline_id=pipeline_id,
                phase="completion",
                error=str(e)
            )

    # backend/core/handlers/channel/insight_handler.py (continued)

    async def _notify_insight_results(
            self,
            pipeline_id: str,
            results: Dict[str, Any],
            state: InsightProcessState
    ) -> None:
        """Notify about insight generation results"""
        message = ProcessingMessage(
            message_type=MessageType.INSIGHT_RESULTS,
            content={
                'pipeline_id': pipeline_id,
                'results': results,
                'metrics': state.metrics.__dict__,
                'requires_review': state.requires_review,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.handler_name,
                target_component="insight_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_insight_update(
            self,
            pipeline_id: str,
            update_type: str,
            update_data: Dict[str, Any]
    ) -> None:
        """Notify about insight process updates"""
        message = ProcessingMessage(
            message_type=MessageType.INSIGHT_UPDATE,
            content={
                'pipeline_id': pipeline_id,
                'update_type': update_type,
                'update_data': update_data,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.handler_name,
                target_component="insight_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_review_needed(
            self,
            pipeline_id: str,
            validation_results: Dict[str, Any]
    ) -> None:
        """Notify that insights require review"""
        message = ProcessingMessage(
            message_type=MessageType.INSIGHT_REVIEW_NEEDED,
            content={
                'pipeline_id': pipeline_id,
                'validation_results': validation_results,
                'requires_review': True,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.handler_name,
                target_component="insight_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_insight_completion(
            self,
            pipeline_id: str,
            results: Dict[str, Any],
            state: InsightProcessState
    ) -> None:
        """Notify about insight process completion"""
        message = ProcessingMessage(
            message_type=MessageType.INSIGHT_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'final_results': results,
                'metrics': state.metrics.__dict__,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.handler_name,
                target_component="insight_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _handle_insight_error(
            self,
            pipeline_id: str,
            phase: str,
            error: str
    ) -> None:
        """Handle insight processing errors"""
        try:
            # Update process state
            process_state = self.active_processes.get(pipeline_id)
            if process_state:
                process_state.current_status = InsightStatus.FAILED
                process_state.metadata['error'] = {
                    'phase': phase,
                    'message': error,
                    'timestamp': datetime.now().isoformat()
                }

            # Create error message
            error_message = ProcessingMessage(
                message_type=MessageType.INSIGHT_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'phase': phase,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.handler_name,
                    target_component="insight_manager"
                )
            )

            # Publish error
            await self.message_broker.publish(error_message)

        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")

    async def get_process_status(
            self,
            pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current status of insight process"""
        process_state = self.active_processes.get(pipeline_id)
        if not process_state:
            return None

        return {
            'pipeline_id': pipeline_id,
            'staged_id': process_state.staged_id,
            'status': process_state.current_status.value,
            'phase': process_state.current_phase.value,
            'metrics': process_state.metrics.__dict__,
            'insights_generated': process_state.insights_generated,
            'insights_validated': process_state.insights_validated,
            'requires_review': process_state.requires_review,
            'created_at': process_state.created_at.isoformat(),
            'updated_at': process_state.updated_at.isoformat()
        }

    async def cleanup(self) -> None:
        """Cleanup handler resources"""
        try:
            # Cleanup processor
            await self.insight_processor.cleanup()

            # Cleanup active processes
            self.active_processes.clear()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise