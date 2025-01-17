# backend/core/managers/insight_manager.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ProcessingStage,
    MessageMetadata
)
from ..control.cpm import ControlPointManager
from ..staging.staging_manager import StagingManager
from .base.base_manager import BaseManager, ManagerState
from ..handlers.channel.insight_handler import InsightHandler
from data.processing.insights.types.insight_types import (
    InsightType,
    InsightStatus,
    InsightPhase,
    InsightProcessState,
    InsightConfig,
    InsightMetrics
)


class InsightManager(BaseManager):
    """
    Manager for insight generation orchestration.
    Coordinates between CPM, Handler, and Staging Area.
    """

    def __init__(
        self,
        message_broker: MessageBroker,
        control_point_manager: ControlPointManager,
        staging_manager: StagingManager
    ):
        super().__init__(
            message_broker=message_broker,
            control_point_manager=control_point_manager,
            component_name="insight_manager",
            domain_type="insights"
        )

        # Initialize components
        self.staging_manager = staging_manager
        self.insight_handler = InsightHandler(
            message_broker=message_broker,
            staging_manager=staging_manager
        )

        # Active processes tracking
        self.active_processes: Dict[str, InsightProcessState] = {}

        # Setup handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup handlers for insight-related messages"""
        self.register_message_handler(
            MessageType.INSIGHT_START,
            self._handle_insight_start
        )
        self.register_message_handler(
            MessageType.INSIGHT_RESULTS,
            self._handle_insight_results
        )
        self.register_message_handler(
            MessageType.INSIGHT_UPDATE,
            self._handle_insight_update
        )
        self.register_message_handler(
            MessageType.INSIGHT_REVIEW_NEEDED,
            self._handle_review_needed
        )
        self.register_message_handler(
            MessageType.INSIGHT_COMPLETE,
            self._handle_insight_complete
        )
        self.register_message_handler(
            MessageType.INSIGHT_ERROR,
            self._handle_insight_error
        )

    async def initiate_insight_process(
        self,
        pipeline_id: str,
        config: Dict[str, Any]
    ) -> str:
        """Start an insight generation process"""
        try:
            # Create control point with CPM
            control_point_id = await self.control_point_manager.create_control_point(
                stage=ProcessingStage.INSIGHT_GENERATION,
                metadata={
                    'pipeline_id': pipeline_id,
                    'config': config
                }
            )

            # Create staging area for insight results
            staged_id = await self.staging_manager.create_staging_area(
                source_type='insights',
                source_identifier=pipeline_id,
                metadata={
                    'control_point_id': control_point_id,
                    'config': config
                }
            )

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

            # Send start message to handler
            start_message = ProcessingMessage(
                message_type=MessageType.INSIGHT_START,
                content={
                    'pipeline_id': pipeline_id,
                    'staged_id': staged_id,
                    'config': config
                },
                metadata=MessageMetadata(
                    source_component=self.component_name,
                    target_component="insight_handler",
                    correlation_id=str(uuid.uuid4())
                )
            )
            await self.message_broker.publish(start_message)

            # Update control point status
            await self.control_point_manager.update_control_point(
                control_point_id,
                status=ProcessingStatus.IN_PROGRESS,
                metadata={
                    'staged_id': staged_id,
                    'started_at': datetime.now().isoformat()
                }
            )

            # Update manager state
            self.state = ManagerState.PROCESSING

            return staged_id

        except Exception as e:
            self.logger.error(f"Failed to initiate insight process: {str(e)}")
            await self._handle_error(pipeline_id, e)
            raise

    async def _handle_insight_start(self, message: ProcessingMessage) -> None:
        """Handle start of insight generation"""
        pipeline_id = message.content.get('pipeline_id')
        try:
            process_state = self.active_processes.get(pipeline_id)
            if process_state:
                process_state.current_status = InsightStatus.PROCESSING
                process_state.updated_at = datetime.now()

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_insight_results(self, message: ProcessingMessage) -> None:
        """Handle insight generation results"""
        pipeline_id = message.content.get('pipeline_id')
        results = message.content.get('results', {})
        requires_review = message.content.get('requires_review', False)

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                return

            # Update process state
            process_state.current_status = (
                InsightStatus.AWAITING_REVIEW if requires_review
                else InsightStatus.COMPLETED
            )
            process_state.updated_at = datetime.now()

            # Update control point
            control_point_id = await self._get_control_point_id(pipeline_id)
            if control_point_id:
                status = (
                    ProcessingStatus.AWAITING_DECISION if requires_review
                    else ProcessingStatus.COMPLETED
                )
                await self.control_point_manager.update_control_point(
                    control_point_id,
                    status=status,
                    metadata={
                        'insight_results': results,
                        'requires_review': requires_review,
                        'updated_at': datetime.now().isoformat()
                    }
                )

            # If review needed, notify CPM
            if requires_review:
                await self._notify_review_required(pipeline_id, results)
            else:
                await self._notify_insights_complete(pipeline_id, results)

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_insight_update(self, message: ProcessingMessage) -> None:
        """Handle insight process updates"""
        pipeline_id = message.content.get('pipeline_id')
        update_type = message.content.get('update_type')
        update_data = message.content.get('update_data', {})

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                return

            # Update process state
            if update_type == "metrics":
                self._update_metrics(process_state, update_data)
            elif update_type == "insights":
                self._update_insight_counts(process_state, update_data)

            process_state.updated_at = datetime.now()

            # Update control point
            control_point_id = await self._get_control_point_id(pipeline_id)
            if control_point_id:
                await self.control_point_manager.update_control_point(
                    control_point_id,
                    metadata={
                        'update_type': update_type,
                        'update_data': update_data,
                        'updated_at': datetime.now().isoformat()
                    }
                )

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_review_needed(self, message: ProcessingMessage) -> None:
        """Handle insights requiring review"""
        pipeline_id = message.content.get('pipeline_id')
        validation_results = message.content.get('validation_results', {})

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                return

            # Update process state
            process_state.current_status = InsightStatus.AWAITING_REVIEW
            process_state.requires_review = True
            process_state.updated_at = datetime.now()

            # Update control point
            control_point_id = await self._get_control_point_id(pipeline_id)
            if control_point_id:
                await self.control_point_manager.update_control_point(
                    control_point_id,
                    status=ProcessingStatus.AWAITING_DECISION,
                    metadata={
                        'validation_results': validation_results,
                        'requires_review': True,
                        'updated_at': datetime.now().isoformat()
                    }
                )

            # Notify CPM about required review
            await self._notify_review_required(pipeline_id, validation_results)

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_insight_complete(self, message: ProcessingMessage) -> None:
        """Handle insight process completion"""
        pipeline_id = message.content.get('pipeline_id')
        final_results = message.content.get('final_results', {})
        metrics = message.content.get('metrics', {})

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                return

            # Update process state
            process_state.current_status = InsightStatus.COMPLETED
            process_state.metrics = metrics
            process_state.updated_at = datetime.now()

            # Update control point
            control_point_id = await self._get_control_point_id(pipeline_id)
            if control_point_id:
                await self.control_point_manager.update_control_point(
                    control_point_id,
                    status=ProcessingStatus.COMPLETED,
                    metadata={
                        'final_results': final_results,
                        'metrics': metrics,
                        'completed_at': datetime.now().isoformat()
                    }
                )

            # Notify CPM about completion
            await self._notify_insights_complete(pipeline_id, final_results)

            # Cleanup process tracking
            del self.active_processes[pipeline_id]

            # Update manager state if no more active processes
            if not self.active_processes:
                self.state = ManagerState.ACTIVE

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_insight_error(self, message: ProcessingMessage) -> None:
        """Handle insight process errors"""
        pipeline_id = message.content.get('pipeline_id')
        error = message.content.get('error')
        phase = message.content.get('phase')

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

            # Update control point
            control_point_id = await self._get_control_point_id(pipeline_id)
            if control_point_id:
                await self.control_point_manager.update_control_point(
                    control_point_id,
                    status=ProcessingStatus.FAILED,
                    metadata={
                        'error': error,
                        'phase': phase,
                        'failed_at': datetime.now().isoformat()
                    }
                )

            # Notify CPM about error
            error_message = ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.INSIGHT_GENERATION.value,
                    'error': error,
                    'phase': phase
                }
            )
            await self.message_broker.publish(error_message)

            # Cleanup process tracking
            if pipeline_id in self.active_processes:
                del self.active_processes[pipeline_id]

            # Update manager state if no more active processes
            if not self.active_processes:
                self.state = ManagerState.ERROR

        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")

    def _update_metrics(
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

    async def _notify_review_required(
        self,
        pipeline_id: str,
        results: Dict[str, Any]
    ) -> None:
        """Notify that insights require review"""
        message = ProcessingMessage(
            message_type=MessageType.STAGE_AWAITING_DECISION,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.INSIGHT_GENERATION.value,
                'results': results,
                'requires_review': True,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

        # backend/core/managers/insight_manager.py (continued)

        async def _notify_insights_complete(
                self,
                pipeline_id: str,
                results: Dict[str, Any]
        ) -> None:
            """Notify about insight generation completion"""
            message = ProcessingMessage(
                message_type=MessageType.STAGE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.INSIGHT_GENERATION.value,
                    'results': results,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.component_name,
                    target_component="control_point_manager"
                )
            )
            await self.message_broker.publish(message)

        async def submit_review_decisions(
                self,
                pipeline_id: str,
                decisions: Dict[str, Any]
        ) -> bool:
            """Submit review decisions for insights"""
            try:
                process_state = self.active_processes.get(pipeline_id)
                if not process_state:
                    raise ValueError(f"No active process found for pipeline: {pipeline_id}")

                # Create review message
                review_message = ProcessingMessage(
                    message_type=MessageType.INSIGHT_REVIEW,
                    content={
                        'pipeline_id': pipeline_id,
                        'staged_id': process_state.staged_id,
                        'decisions': decisions,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="insight_handler"
                    )
                )
                await self.message_broker.publish(review_message)

                return True

            except Exception as e:
                self.logger.error(f"Review submission failed: {str(e)}")
                await self._handle_error(pipeline_id, e)
                return False

        async def get_insight_status(
                self,
                pipeline_id: str
        ) -> Optional[Dict[str, Any]]:
            """Get current status of insight process"""
            try:
                process_state = self.active_processes.get(pipeline_id)
                if not process_state:
                    return None

                # Get handler status
                handler_status = await self.insight_handler.get_process_status(pipeline_id)

                # Get control point status
                control_point_id = await self._get_control_point_id(pipeline_id)
                control_point_status = None
                if control_point_id:
                    control_point = await self.control_point_manager.get_control_point(
                        control_point_id
                    )
                    if control_point:
                        control_point_status = control_point.status

                return {
                    'pipeline_id': pipeline_id,
                    'staged_id': process_state.staged_id,
                    'status': process_state.current_status.value,
                    'phase': process_state.current_phase.value,
                    'metrics': process_state.metrics.__dict__,
                    'insights_generated': process_state.insights_generated,
                    'insights_validated': process_state.insights_validated,
                    'requires_review': process_state.requires_review,
                    'handler_status': handler_status,
                    'control_point_status': control_point_status.value if control_point_status else None,
                    'created_at': process_state.created_at.isoformat(),
                    'updated_at': process_state.updated_at.isoformat()
                }

            except Exception as e:
                self.logger.error(f"Failed to get insight status: {str(e)}")
                return None

        async def get_insight_results(
                self,
                pipeline_id: str
        ) -> Optional[Dict[str, Any]]:
            """Get insight generation results"""
            try:
                process_state = self.active_processes.get(pipeline_id)
                if not process_state:
                    return None

                # Get results from staging
                staged_data = await self.staging_manager.get_staged_data(
                    process_state.staged_id
                )
                if not staged_data:
                    return None

                return {
                    'pipeline_id': pipeline_id,
                    'results': staged_data.get('data', {}),
                    'metrics': process_state.metrics.__dict__,
                    'status': process_state.current_status.value,
                    'created_at': process_state.created_at.isoformat(),
                    'updated_at': process_state.updated_at.isoformat()
                }

            except Exception as e:
                self.logger.error(f"Failed to get insight results: {str(e)}")
                return None

        async def _get_control_point_id(self, pipeline_id: str) -> Optional[str]:
            """Get control point ID for pipeline"""
            try:
                control_points = await self.control_point_manager.get_pipeline_control_points(
                    pipeline_id
                )
                if not control_points:
                    return None

                # Find active insight control point
                for cp in control_points:
                    if (cp.stage == ProcessingStage.INSIGHT_GENERATION and
                            cp.status != ProcessingStatus.COMPLETED):
                        return cp.id

                return None

            except Exception as e:
                self.logger.error(f"Failed to get control point ID: {str(e)}")
                return None

        async def cleanup(self) -> None:
            """Cleanup manager resources"""
            try:
                # Cleanup handler
                await self.insight_handler.cleanup()

                # Cleanup active processes
                for pipeline_id in list(self.active_processes.keys()):
                    await self._handle_insight_error(
                        ProcessingMessage(
                            message_type=MessageType.INSIGHT_ERROR,
                            content={
                                'pipeline_id': pipeline_id,
                                'error': 'Manager cleanup initiated',
                                'phase': 'cleanup'
                            }
                        )
                    )

                # Call parent cleanup
                await super().cleanup()

            except Exception as e:
                self.logger.error(f"Cleanup failed: {str(e)}")
                raise