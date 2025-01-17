# backend/core/handlers/channel/quality_handler.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    MessageMetadata
)
from ...staging.staging_manager import StagingManager
from ..base.base_handler import BaseChannelHandler, HandlerState
from data.processing.quality.processor.quality_processor import QualityProcessor
from data.processing.quality.types.quality_types import (
    QualityState,
    QualityPhase,
    QualityContext,
    QualityProcessState
)

logger = logging.getLogger(__name__)


class QualityHandler(BaseChannelHandler):
    """
    Handler for quality analysis operations.
    Coordinates between manager, processor, and staging area.
    """

    def __init__(
        self,
        message_broker: MessageBroker,
        staging_manager: StagingManager
    ):
        super().__init__(
            message_broker=message_broker,
            handler_name="quality_handler",
            domain_type="quality"
        )

        # Initialize components
        self.staging_manager = staging_manager
        self.quality_processor = QualityProcessor(
            message_broker=message_broker,
            staging_manager=staging_manager
        )

        # State tracking
        self.active_processes: Dict[str, QualityProcessState] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup handlers for quality-specific messages"""
        self.register_message_handler(
            MessageType.QUALITY_START,
            self._handle_quality_start
        )
        self.register_message_handler(
            MessageType.QUALITY_UPDATE,
            self._handle_quality_update
        )
        self.register_message_handler(
            MessageType.QUALITY_RESOLUTION,
            self._handle_quality_resolution
        )
        self.register_message_handler(
            MessageType.QUALITY_VALIDATE,
            self._handle_quality_validation
        )

    async def _handle_quality_start(self, message: ProcessingMessage) -> None:
        """Handle start of quality analysis process"""
        pipeline_id = message.content.get('pipeline_id')
        staged_id = message.content.get('staged_id')
        config = message.content.get('config', {})

        try:
            # Initialize process state
            process_state = QualityProcessState(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                current_state=QualityState.INITIALIZING,
                current_phase=QualityPhase.DETECTION,
                metrics=QualityMetrics(
                    total_issues=0,
                    issues_by_type={},
                    auto_resolvable=0,
                    manual_required=0,
                    resolution_rate=0.0,
                    average_severity=0.0
                )
            )
            self.active_processes[pipeline_id] = process_state

            # Analyze context
            context = await self.quality_processor.analyze_context(
                data=await self._get_staged_data(staged_id),
                metadata=config
            )

            # Update state
            process_state.current_state = QualityState.DETECTING
            process_state.updated_at = datetime.now()

            # Process quality checks
            results = await self.quality_processor.process_quality_checks(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                context=context
            )

            # Update process state
            self._update_process_state(
                pipeline_id=pipeline_id,
                results=results,
                phase=QualityPhase.DETECTION
            )

            # Notify about completion
            await self._notify_quality_results(
                pipeline_id=pipeline_id,
                results=results,
                state=process_state
            )

        except Exception as e:
            await self._handle_quality_error(
                pipeline_id=pipeline_id,
                phase="initialization",
                error=str(e)
            )

    async def _handle_quality_update(self, message: ProcessingMessage) -> None:
        """Handle quality process updates"""
        pipeline_id = message.content.get('pipeline_id')
        update_type = message.content.get('update_type')
        update_data = message.content.get('update_data', {})

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                raise ValueError(f"No active process found for pipeline: {pipeline_id}")

            # Update process state
            if update_type == "metrics":
                self._update_quality_metrics(process_state, update_data)
            elif update_type == "issues":
                self._update_quality_issues(process_state, update_data)

            # Notify about update
            await self._notify_quality_update(
                pipeline_id=pipeline_id,
                update_type=update_type,
                update_data=update_data
            )

        except Exception as e:
            await self._handle_quality_error(
                pipeline_id=pipeline_id,
                phase="update",
                error=str(e)
            )

    async def _handle_quality_resolution(self, message: ProcessingMessage) -> None:
        """Handle quality issue resolutions"""
        pipeline_id = message.content.get('pipeline_id')
        staged_id = message.content.get('staged_id')
        resolutions = message.content.get('resolutions', {})

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                raise ValueError(f"No active process found for pipeline: {pipeline_id}")

            # Update state
            process_state.current_state = QualityState.RESOLVING
            process_state.current_phase = QualityPhase.RESOLUTION
            process_state.updated_at = datetime.now()

            # Apply resolutions
            resolution_results = await self.quality_processor.apply_resolutions(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                resolutions=resolutions
            )

            # Update process state
            self._update_process_state(
                pipeline_id=pipeline_id,
                results=resolution_results,
                phase=QualityPhase.RESOLUTION
            )

            # Notify about resolution
            await self._notify_resolution_results(
                pipeline_id=pipeline_id,
                results=resolution_results,
                state=process_state
            )

        except Exception as e:
            await self._handle_quality_error(
                pipeline_id=pipeline_id,
                phase="resolution",
                error=str(e)
            )

    async def _handle_quality_validation(self, message: ProcessingMessage) -> None:
        """Handle validation of resolved issues"""
        pipeline_id = message.content.get('pipeline_id')
        staged_id = message.content.get('staged_id')

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                raise ValueError(f"No active process found for pipeline: {pipeline_id}")

            # Update state
            process_state.current_state = QualityState.VALIDATING
            process_state.current_phase = QualityPhase.VALIDATION
            process_state.updated_at = datetime.now()

            # Validate resolutions
            validation_results = await self.quality_processor.validate_resolutions(
                pipeline_id=pipeline_id,
                staged_id=staged_id
            )

            # Update process state
            self._update_process_state(
                pipeline_id=pipeline_id,
                results=validation_results,
                phase=QualityPhase.VALIDATION
            )

            # Check if process is complete
            if self._is_quality_complete(validation_results):
                process_state.current_state = QualityState.COMPLETED
                await self._notify_quality_completion(
                    pipeline_id=pipeline_id,
                    results=validation_results,
                    state=process_state
                )
            else:
                # More resolutions needed
                await self._notify_validation_results(
                    pipeline_id=pipeline_id,
                    results=validation_results,
                    state=process_state
                )

        except Exception as e:
            await self._handle_quality_error(
                pipeline_id=pipeline_id,
                phase="validation",
                error=str(e)
            )

        # backend/core/handlers/channel/quality_handler.py (continued)

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
            phase: QualityPhase
    ) -> None:
        """Update quality process state"""
        process_state = self.active_processes.get(pipeline_id)
        if not process_state:
            return

        if phase == QualityPhase.DETECTION:
            process_state.issues_found = len(results.get('issues', []))
            process_state.requires_attention = any(
                issue.get('requires_manual', False)
                for issue in results.get('issues', [])
            )
        elif phase == QualityPhase.RESOLUTION:
            process_state.issues_resolved = len(results.get('resolved_issues', []))
            process_state.metrics.resolution_rate = (
                process_state.issues_resolved / process_state.issues_found
                if process_state.issues_found > 0 else 0.0
            )

        process_state.current_phase = phase
        process_state.updated_at = datetime.now()

    def _update_quality_metrics(
            self,
            process_state: QualityProcessState,
            metrics_data: Dict[str, Any]
    ) -> None:
        """Update quality metrics"""
        metrics = process_state.metrics
        metrics.total_issues = metrics_data.get('total_issues', metrics.total_issues)
        metrics.auto_resolvable = metrics_data.get('auto_resolvable', metrics.auto_resolvable)
        metrics.manual_required = metrics_data.get('manual_required', metrics.manual_required)
        metrics.average_severity = metrics_data.get('average_severity', metrics.average_severity)

        if 'issues_by_type' in metrics_data:
            metrics.issues_by_type.update(metrics_data['issues_by_type'])

    def _update_quality_issues(
            self,
            process_state: QualityProcessState,
            issues_data: Dict[str, Any]
    ) -> None:
        """Update quality issues tracking"""
        process_state.issues_found = issues_data.get('total', process_state.issues_found)
        process_state.issues_resolved = issues_data.get('resolved', process_state.issues_resolved)
        process_state.requires_attention = issues_data.get('requires_attention', process_state.requires_attention)

    async def _notify_quality_results(
            self,
            pipeline_id: str,
            results: Dict[str, Any],
            state: QualityProcessState
    ) -> None:
        """Notify about quality check results"""
        message = ProcessingMessage(
            message_type=MessageType.QUALITY_RESULTS,
            content={
                'pipeline_id': pipeline_id,
                'results': results,
                'metrics': state.metrics.__dict__,
                'requires_attention': state.requires_attention,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.handler_name,
                target_component="quality_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_quality_update(
            self,
            pipeline_id: str,
            update_type: str,
            update_data: Dict[str, Any]
    ) -> None:
        """Notify about quality process updates"""
        message = ProcessingMessage(
            message_type=MessageType.QUALITY_UPDATE,
            content={
                'pipeline_id': pipeline_id,
                'update_type': update_type,
                'update_data': update_data,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.handler_name,
                target_component="quality_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_resolution_results(
            self,
            pipeline_id: str,
            results: Dict[str, Any],
            state: QualityProcessState
    ) -> None:
        """Notify about resolution results"""
        message = ProcessingMessage(
            message_type=MessageType.QUALITY_RESOLUTION_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'results': results,
                'metrics': state.metrics.__dict__,
                'remaining_issues': state.issues_found - state.issues_resolved,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.handler_name,
                target_component="quality_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_validation_results(
            self,
            pipeline_id: str,
            results: Dict[str, Any],
            state: QualityProcessState
    ) -> None:
        """Notify about validation results"""
        message = ProcessingMessage(
            message_type=MessageType.QUALITY_VALIDATION_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'results': results,
                'requires_resolution': not self._is_quality_complete(results),
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.handler_name,
                target_component="quality_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_quality_completion(
            self,
            pipeline_id: str,
            results: Dict[str, Any],
            state: QualityProcessState
    ) -> None:
        """Notify about quality process completion"""
        message = ProcessingMessage(
            message_type=MessageType.QUALITY_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'final_results': results,
                'metrics': state.metrics.__dict__,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.handler_name,
                target_component="quality_manager"
            )
        )
        await self.message_broker.publish(message)

    def _is_quality_complete(self, validation_results: Dict[str, Any]) -> bool:
        """Check if quality process is complete"""
        # Check validation results to determine if all issues are resolved
        remaining_issues = validation_results.get('remaining_issues', [])
        new_issues = validation_results.get('new_issues', [])
        return len(remaining_issues) == 0 and len(new_issues) == 0

    async def _handle_quality_error(
            self,
            pipeline_id: str,
            phase: str,
            error: str
    ) -> None:
        """Handle quality processing errors"""
        try:
            # Update process state
            process_state = self.active_processes.get(pipeline_id)
            if process_state:
                process_state.current_state = QualityState.FAILED
                process_state.metadata['error'] = {
                    'phase': phase,
                    'message': error,
                    'timestamp': datetime.now().isoformat()
                }

            # Create error message
            error_message = ProcessingMessage(
                message_type=MessageType.QUALITY_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'phase': phase,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.handler_name,
                    target_component="quality_manager"
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
        """Get current status of quality process"""
        process_state = self.active_processes.get(pipeline_id)
        if not process_state:
            return None

        return {
            'pipeline_id': pipeline_id,
            'state': process_state.current_state.value,
            'phase': process_state.current_phase.value,
            'metrics': process_state.metrics.__dict__,
            'issues_found': process_state.issues_found,
            'issues_resolved': process_state.issues_resolved,
            'requires_attention': process_state.requires_attention,
            'created_at': process_state.created_at.isoformat(),
            'updated_at': process_state.updated_at.isoformat()
        }

    async def cleanup(self) -> None:
        """Cleanup handler resources"""
        try:
            # Cleanup processor
            await self.quality_processor.cleanup()

            # Cleanup active processes
            self.active_processes.clear()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise