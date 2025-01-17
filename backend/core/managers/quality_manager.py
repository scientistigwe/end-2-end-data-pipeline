# backend/core/managers/quality_manager.py

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
from ..managers.base.base_manager import BaseManager, ManagerState
from ..handlers.channel.quality_handler import QualityHandler
from data.processing.quality.types.quality_types import (
    QualityCheckConfig,
    QualityCheckType,
    QualityProcessState,
    QualityState,
    QualityMetrics
)



class QualityManager(BaseManager):
    """
    Manager for quality analysis orchestration.
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
            component_name="quality_manager",
            domain_type="quality"
        )

        # Initialize components
        self.staging_manager = staging_manager
        self.quality_handler = QualityHandler(
            message_broker=message_broker,
            staging_manager=staging_manager
        )

        # Active processes tracking
        self.active_processes: Dict[str, QualityProcessState] = {}

        # Setup handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup handlers for quality-related messages"""
        self.register_message_handler(
            MessageType.QUALITY_START,
            self._handle_quality_start
        )
        self.register_message_handler(
            MessageType.QUALITY_RESULTS,
            self._handle_quality_results
        )
        self.register_message_handler(
            MessageType.QUALITY_UPDATE,
            self._handle_quality_update
        )
        self.register_message_handler(
            MessageType.QUALITY_RESOLUTION_COMPLETE,
            self._handle_resolution_complete
        )
        self.register_message_handler(
            MessageType.QUALITY_VALIDATION_COMPLETE,
            self._handle_validation_complete
        )
        self.register_message_handler(
            MessageType.QUALITY_COMPLETE,
            self._handle_quality_complete
        )
        self.register_message_handler(
            MessageType.QUALITY_ERROR,
            self._handle_quality_error
        )

    async def initiate_quality_process(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> str:
        """Start a quality analysis process"""
        try:
            # Create control point with CPM
            control_point_id = await self.control_point_manager.create_control_point(
                stage=ProcessingStage.QUALITY_CHECK,
                metadata={
                    'pipeline_id': pipeline_id,
                    'config': config
                }
            )

            # Create staging area for quality results
            staged_id = await self.staging_manager.create_staging_area(
                source_type='quality',
                source_identifier=pipeline_id,
                metadata={
                    'control_point_id': control_point_id,
                    'config': config
                }
            )

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

            # Send start message to handler
            start_message = ProcessingMessage(
                message_type=MessageType.QUALITY_START,
                content={
                    'pipeline_id': pipeline_id,
                    'staged_id': staged_id,
                    'config': config
                },
                metadata=MessageMetadata(
                    source_component=self.component_name,
                    target_component="quality_handler",
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
            self.logger.error(f"Failed to initiate quality process: {str(e)}")
            await self._handle_error(pipeline_id, e)
            raise

    async def _handle_quality_start(self, message: ProcessingMessage) -> None:
        """Handle start of quality analysis"""
        pipeline_id = message.content.get('pipeline_id')
        try:
            process_state = self.active_processes.get(pipeline_id)
            if process_state:
                process_state.current_state = QualityState.DETECTING
                process_state.updated_at = datetime.now()

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_quality_results(self, message: ProcessingMessage) -> None:
        """Handle quality analysis results"""
        pipeline_id = message.content.get('pipeline_id')
        results = message.content.get('results', {})
        requires_attention = message.content.get('requires_attention', False)

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                return

            # Update process state
            process_state.current_state = (
                QualityState.RESOLVING if requires_attention
                else QualityState.COMPLETED
            )
            process_state.updated_at = datetime.now()

            # Update control point
            control_point_id = await self._get_control_point_id(pipeline_id)
            if control_point_id:
                status = (
                    ProcessingStatus.AWAITING_DECISION if requires_attention
                    else ProcessingStatus.COMPLETED
                )
                await self.control_point_manager.update_control_point(
                    control_point_id,
                    status=status,
                    metadata={
                        'quality_results': results,
                        'requires_attention': requires_attention,
                        'updated_at': datetime.now().isoformat()
                    }
                )

            # If issues require attention, notify CPM
            if requires_attention:
                await self._notify_issues_found(pipeline_id, results)
            else:
                await self._notify_quality_complete(pipeline_id, results)

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_quality_update(self, message: ProcessingMessage) -> None:
        """Handle quality process updates"""
        pipeline_id = message.content.get('pipeline_id')
        update_type = message.content.get('update_type')
        update_data = message.content.get('update_data', {})

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                return

            # Update process state
            if update_type == "metrics":
                process_state.metrics = update_data
            elif update_type == "issues":
                process_state.issues_found = update_data.get('total', process_state.issues_found)
                process_state.issues_resolved = update_data.get('resolved', process_state.issues_resolved)

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

    async def _handle_resolution_complete(self, message: ProcessingMessage) -> None:
        """Handle completion of quality resolutions"""
        pipeline_id = message.content.get('pipeline_id')
        results = message.content.get('results', {})
        remaining_issues = message.content.get('remaining_issues', 0)

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                return

            # Update process state
            process_state.current_state = QualityState.VALIDATING
            process_state.issues_resolved = process_state.issues_found - remaining_issues
            process_state.updated_at = datetime.now()

            # Update control point
            control_point_id = await self._get_control_point_id(pipeline_id)
            if control_point_id:
                await self.control_point_manager.update_control_point(
                    control_point_id,
                    status=ProcessingStatus.IN_PROGRESS,
                    metadata={
                        'resolution_results': results,
                        'remaining_issues': remaining_issues,
                        'updated_at': datetime.now().isoformat()
                    }
                )

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_validation_complete(self, message: ProcessingMessage) -> None:
        """Handle completion of quality validation"""
        pipeline_id = message.content.get('pipeline_id')
        results = message.content.get('results', {})
        requires_resolution = message.content.get('requires_resolution', False)

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                return

            # Update process state
            process_state.current_state = (
                QualityState.RESOLVING if requires_resolution
                else QualityState.COMPLETED
            )
            process_state.updated_at = datetime.now()

            # Update control point
            control_point_id = await self._get_control_point_id(pipeline_id)
            if control_point_id:
                status = (
                    ProcessingStatus.AWAITING_DECISION if requires_resolution
                    else ProcessingStatus.COMPLETED
                )
                await self.control_point_manager.update_control_point(
                    control_point_id,
                    status=status,
                    metadata={
                        'validation_results': results,
                        'requires_resolution': requires_resolution,
                        'updated_at': datetime.now().isoformat()
                    }
                )

            # If more resolutions needed, notify CPM
            if requires_resolution:
                await self._notify_resolution_needed(pipeline_id, results)
            else:
                await self._notify_quality_complete(pipeline_id, results)

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_quality_complete(self, message: ProcessingMessage) -> None:
        """Handle quality process completion"""
        pipeline_id = message.content.get('pipeline_id')
        final_results = message.content.get('final_results', {})
        metrics = message.content.get('metrics', {})

        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                return

            # Update process state
            process_state.current_state = QualityState.COMPLETED
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
            await self._notify_quality_complete(pipeline_id, final_results)

            # Cleanup process tracking
            del self.active_processes[pipeline_id]

            # Update manager state if no more active processes
            if not self.active_processes:
                self.state = ManagerState.ACTIVE

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_quality_error(self, message: ProcessingMessage) -> None:
        """Handle quality process errors"""
        pipeline_id = message.content.get('pipeline_id')
        error = message.content.get('error')
        phase = message.content.get('phase')

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
                    'stage': ProcessingStage.QUALITY_CHECK.value,
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

# backend/core/managers/quality_manager.py (continued)

    async def _notify_issues_found(
        self,
        pipeline_id: str,
        results: Dict[str, Any]
    ) -> None:
        """Notify about quality issues found"""
        message = ProcessingMessage(
            message_type=MessageType.QUALITY_ISSUES_FOUND,
            content={
                'pipeline_id': pipeline_id,
                'issues': results.get('issues', []),
                'requires_attention': True,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_resolution_needed(
        self,
        pipeline_id: str,
        results: Dict[str, Any]
    ) -> None:
        """Notify about needed resolutions"""
        message = ProcessingMessage(
            message_type=MessageType.QUALITY_RESOLUTION_NEEDED,
            content={
                'pipeline_id': pipeline_id,
                'remaining_issues': results.get('remaining_issues', []),
                'requires_attention': True,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_quality_complete(
        self,
        pipeline_id: str,
        results: Dict[str, Any]
    ) -> None:
        """Notify about quality process completion"""
        message = ProcessingMessage(
            message_type=MessageType.STAGE_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.QUALITY_CHECK.value,
                'results': results,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        )
        await self.message_broker.publish(message)

    async def submit_resolutions(
        self,
        pipeline_id: str,
        resolutions: Dict[str, Any]
    ) -> bool:
        """Submit quality issue resolutions"""
        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                raise ValueError(f"No active process found for pipeline: {pipeline_id}")

            # Create resolution message
            resolution_message = ProcessingMessage(
                message_type=MessageType.QUALITY_RESOLUTION,
                content={
                    'pipeline_id': pipeline_id,
                    'staged_id': process_state.staged_id,
                    'resolutions': resolutions,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.component_name,
                    target_component="quality_handler"
                )
            )
            await self.message_broker.publish(resolution_message)

            return True

        except Exception as e:
            self.logger.error(f"Resolution submission failed: {str(e)}")
            await self._handle_error(pipeline_id, e)
            return False

    async def get_quality_status(
        self,
        pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current status of quality process"""
        try:
            process_state = self.active_processes.get(pipeline_id)
            if not process_state:
                return None

            # Get handler status
            handler_status = await self.quality_handler.get_process_status(pipeline_id)

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
                'state': process_state.current_state.value,
                'phase': process_state.current_phase.value,
                'metrics': process_state.metrics.__dict__,
                'issues_found': process_state.issues_found,
                'issues_resolved': process_state.issues_resolved,
                'requires_attention': process_state.requires_attention,
                'handler_status': handler_status,
                'control_point_status': control_point_status.value if control_point_status else None,
                'created_at': process_state.created_at.isoformat(),
                'updated_at': process_state.updated_at.isoformat()
            }

        except Exception as e:
            self.logger.error(f"Failed to get quality status: {str(e)}")
            return None

    async def get_quality_results(
        self,
        pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get quality analysis results"""
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
                'state': process_state.current_state.value,
                'created_at': process_state.created_at.isoformat(),
                'updated_at': process_state.updated_at.isoformat()
            }

        except Exception as e:
            self.logger.error(f"Failed to get quality results: {str(e)}")
            return None

    async def _get_control_point_id(self, pipeline_id: str) -> Optional[str]:
        """Get control point ID for pipeline"""
        try:
            control_points = await self.control_point_manager.get_pipeline_control_points(
                pipeline_id
            )
            if not control_points:
                return None

            # Find active quality control point
            for cp in control_points:
                if (cp.stage == ProcessingStage.QUALITY_CHECK and
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
            await self.quality_handler.cleanup()

            # Cleanup active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self._handle_quality_error(
                    ProcessingMessage(
                        message_type=MessageType.QUALITY_ERROR,
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