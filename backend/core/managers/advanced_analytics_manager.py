# backend/core/managers/analytics_manager.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ProcessingStage,
    MessageMetadata
)
from ..control.cpm import ControlPointManager
from ..staging.staging_manager import StagingManager
from .base_manager import BaseManager, ManagerState
from ..handlers.channel.analytics_handler import AdvancedAnalyticsHandler


class AdvancedAnalyticsManager(BaseManager):
    """
    Manager for advanced analytics orchestration.
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
            component_name="advanced_analytics_manager",
            domain_type="analytics"
        )

        # Initialize components
        self.staging_manager = staging_manager
        self.analytics_handler = AdvancedAnalyticsHandler(
            message_broker=message_broker,
            staging_manager=staging_manager
        )

        # Setup handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup handlers for analytics-related messages"""
        self.register_message_handler(
            MessageType.ANALYTICS_START,
            self._handle_analytics_start
        )
        self.register_message_handler(
            MessageType.ANALYTICS_UPDATE,
            self._handle_analytics_update
        )
        self.register_message_handler(
            MessageType.ANALYTICS_COMPLETE,
            self._handle_analytics_complete
        )
        self.register_message_handler(
            MessageType.ANALYTICS_ERROR,
            self._handle_analytics_error
        )

    async def initiate_analytics_process(
        self,
        pipeline_id: str,
        config: Dict[str, Any]
    ) -> str:
        """Start an advanced analytics process"""
        try:
            # Create control point with CPM
            control_point_id = await self.control_point_manager.create_control_point(
                stage=ProcessingStage.ADVANCED_ANALYTICS,
                metadata={
                    'pipeline_id': pipeline_id,
                    'config': config
                }
            )

            # Create staging area for analytics results
            staged_id = await self.staging_manager.create_staging_area(
                source_type='analytics',
                source_identifier=pipeline_id,
                metadata={
                    'control_point_id': control_point_id,
                    'config': config
                }
            )

            # Send start message to handler
            start_message = ProcessingMessage(
                message_type=MessageType.ANALYTICS_START,
                content={
                    'pipeline_id': pipeline_id,
                    'staged_id': staged_id,
                    'config': config
                },
                metadata=MessageMetadata(
                    source_component=self.component_name,
                    target_component="advanced_analytics_handler",
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

            return staged_id

        except Exception as e:
            self.logger.error(f"Failed to initiate analytics process: {str(e)}")
            await self._handle_error(pipeline_id, e)
            raise

    async def _handle_analytics_start(self, message: ProcessingMessage) -> None:
        """Handle start of analytics process"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            staged_id = message.content.get('staged_id')

            # Update state tracking
            self.state = ManagerState.PROCESSING
            self._active_processes[pipeline_id] = {
                'staged_id': staged_id,
                'start_time': datetime.now(),
                'status': ProcessingStatus.IN_PROGRESS
            }

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_analytics_update(self, message: ProcessingMessage) -> None:
        """Handle analytics process updates"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            phase = message.content.get('phase')
            staged_id = message.content.get('staged_id')
            summary = message.content.get('summary', {})

            # Update CPM
            control_point = await self.control_point_manager.get_control_point(
                self._active_processes[pipeline_id].get('control_point_id')
            )
            if control_point:
                await self.control_point_manager.update_control_point(
                    control_point.id,
                    metadata={
                        'current_phase': phase,
                        'phase_summary': summary,
                        'staged_id': staged_id,
                        'updated_at': datetime.now().isoformat()
                    }
                )

            # Update staging area metadata
            await self.staging_manager.update_stage_status(
                staged_id=staged_id,
                stage=phase,
                status=ProcessingStatus.IN_PROGRESS.value,
                metadata=summary
            )

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_analytics_complete(self, message: ProcessingMessage) -> None:
        """Handle completion of analytics process"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            staged_id = message.content.get('staged_id')
            summary = message.content.get('summary', {})

            # Update CPM
            control_point = await self.control_point_manager.get_control_point(
                self._active_processes[pipeline_id].get('control_point_id')
            )
            if control_point:
                await self.control_point_manager.update_control_point(
                    control_point.id,
                    status=ProcessingStatus.COMPLETED,
                    metadata={
                        'completion_summary': summary,
                        'completed_at': datetime.now().isoformat()
                    }
                )

            # Update staging area status
            await self.staging_manager.update_stage_status(
                staged_id=staged_id,
                stage=ProcessingStage.ADVANCED_ANALYTICS.value,
                status=ProcessingStatus.COMPLETED.value,
                metadata={
                    'completion_summary': summary,
                    'completed_at': datetime.now().isoformat()
                }
            )

            # Notify about completion
            complete_message = ProcessingMessage(
                message_type=MessageType.STAGE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.ADVANCED_ANALYTICS.value,
                    'staged_id': staged_id,
                    'summary': summary
                }
            )
            await self.message_broker.publish(complete_message)

            # Cleanup process tracking
            if pipeline_id in self._active_processes:
                del self._active_processes[pipeline_id]

            self.state = ManagerState.ACTIVE

        except Exception as e:
            await self._handle_error(pipeline_id, e)

    async def _handle_analytics_error(self, message: ProcessingMessage) -> None:
        """Handle analytics process errors"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            error = message.content.get('error')
            phase = message.content.get('phase')

            # Update CPM
            control_point = await self.control_point_manager.get_control_point(
                self._active_processes[pipeline_id].get('control_point_id')
            )
            if control_point:
                await self.control_point_manager.update_control_point(
                    control_point.id,
                    status=ProcessingStatus.FAILED,
                    metadata={
                        'error': error,
                        'failed_phase': phase,
                        'failed_at': datetime.now().isoformat()
                    }
                )

            # Update staging area status
            staged_id = self._active_processes[pipeline_id].get('staged_id')
            if staged_id:
                await self.staging_manager.update_stage_status(
                    staged_id=staged_id,
                    stage=phase,
                    status=ProcessingStatus.FAILED.value,
                    metadata={
                        'error': error,
                        'failed_at': datetime.now().isoformat()
                    }
                )

            # Notify about failure
            error_message = ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.ADVANCED_ANALYTICS.value,
                    'error': error,
                    'phase': phase
                }
            )
            await self.message_broker.publish(error_message)

            # Cleanup process tracking
            if pipeline_id in self._active_processes:
                del self._active_processes[pipeline_id]

            self.state = ManagerState.ERROR

        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")

    async def get_analytics_status(
        self,
        pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current status of analytics process"""
        try:
            process_info = self._active_processes.get(pipeline_id)
            if not process_info:
                return None

            # Get status from handler
            handler_status = self.analytics_handler.get_status()

            # Get staging status
            staging_status = await self.staging_manager.get_stage_status(
                process_info['staged_id']
            )

            # Get control point status
            control_point = await self.control_point_manager.get_control_point(
                process_info['control_point_id']
            )

            return {
                'pipeline_id': pipeline_id,
                'staged_id': process_info['staged_id'],
                'start_time': process_info['start_time'].isoformat(),
                'status': process_info['status'].value,
                'handler_status': handler_status,
                'staging_status': staging_status,
                'control_point_status': control_point.status if control_point else None
            }

        except Exception as e:
            self.logger.error(f"Failed to get analytics status: {str(e)}")
            return None

    async def cleanup(self) -> None:
        """Cleanup manager resources"""
        try:
            # Cleanup handler
            await self.analytics_handler.cleanup()

            # Cleanup active processes
            for pipeline_id in list(self._active_processes.keys()):
                await self._handle_analytics_error(
                    ProcessingMessage(
                        message_type=MessageType.ANALYTICS_ERROR,
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