# backend/core/orchestration/pipeline_manager.py

from typing import Dict, Any, Optional, List, Callable
import logging
from uuid import UUID
from datetime import datetime

from backend.core.orchestration.base_manager import BaseManager
from backend.core.orchestration.pipeline_manager_helper import (
    PipelineState,
    PipelineStateManager,
    StageTransition
)
from backend.core.messaging.types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ProcessingStage,
    ComponentType,
    ModuleIdentifier
)
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.orchestration.staging_manager import StagingManager
from backend.core.messaging.broker import MessageBroker
from backend.database.repository.pipeline_repository import PipelineRepository

logger = logging.getLogger(__name__)


class PipelineManager(BaseManager):
    """
    Pipeline manager orchestrating data processing pipeline operations.
    Handles pipeline lifecycle, state management, and stage transitions.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            repository: Optional[PipelineRepository] = None,
            control_point_manager: Optional[ControlPointManager] = None,
            staging_manager: Optional[StagingManager] = None,
            component_name: str = "PipelineManager"
    ):
        """
        Initialize the Pipeline Manager with comprehensive components.

        Args:
            message_broker (MessageBroker): Message communication system
            repository (Optional[PipelineRepository], optional): Database repository for pipeline operations
            control_point_manager (Optional[ControlPointManager], optional): Manages control points and decisions
            staging_manager (Optional[StagingManager], optional): Manages data staging across pipeline
            component_name (str, optional): Name of the component. Defaults to "PipelineManager".
        """
        # Initialize base manager
        super().__init__(
            message_broker=message_broker,
            component_name=component_name
        )

        # Dependency injection
        self.repository = repository
        self.control_point_manager = control_point_manager
        self.staging_manager = staging_manager

        # State management
        self.state_manager = PipelineStateManager()

        # Initialize stage transitions
        self._initialize_stage_transitions()

        # Add basic logging of initialization
        logger.info(f"PipelineManager initialized with repository: {repository}")

    def _initialize_stage_transitions(self) -> None:
        """
        Define comprehensive stage transition rules with
        validation and control point requirements.
        """
        self.stage_transitions = {
            ProcessingStage.INITIAL_VALIDATION: StageTransition(
                from_stage=ProcessingStage.INITIAL_VALIDATION,
                to_stage=ProcessingStage.DATA_EXTRACTION,
                required_artifacts=["validation_report"],
                validation_rules={
                    "validation_passed": True,
                    "error_count": "== 0"
                }
            ),
            ProcessingStage.DATA_EXTRACTION: StageTransition(
                from_stage=ProcessingStage.DATA_EXTRACTION,
                to_stage=ProcessingStage.QUALITY_CHECK,
                required_artifacts=["extracted_data", "data_profile"],
                validation_rules={
                    "data_loaded": True,
                    "data_size": "> 0"
                }
            ),
            ProcessingStage.QUALITY_CHECK: StageTransition(
                from_stage=ProcessingStage.QUALITY_CHECK,
                to_stage=ProcessingStage.ANALYSIS_PREP,
                required_artifacts=["quality_report"],
                validation_rules={
                    "quality_score": ">= 0.8",
                    "anomalies_count": "<= 5"
                }
            ),
            ProcessingStage.ANALYSIS_PREP: StageTransition(
                from_stage=ProcessingStage.ANALYSIS_PREP,
                to_stage=ProcessingStage.ANALYSIS_EXECUTION,
                required_artifacts=["prepared_data"],
                validation_rules={
                    "prep_complete": True,
                    "data_consistency": True
                }
            ),
            ProcessingStage.ANALYSIS_EXECUTION: StageTransition(
                from_stage=ProcessingStage.ANALYSIS_EXECUTION,
                to_stage=ProcessingStage.RESULTS_VALIDATION,
                required_artifacts=["analysis_results"],
                validation_rules={
                    "analysis_complete": True,
                    "statistical_significance": True
                }
            ),
            ProcessingStage.RESULTS_VALIDATION: StageTransition(
                from_stage=ProcessingStage.RESULTS_VALIDATION,
                to_stage=ProcessingStage.FINAL_APPROVAL,
                required_artifacts=["validation_report"],
                validation_rules={
                    "validation_passed": True,
                    "result_confidence": ">= 0.9"
                }
            )
        }

    async def initialize_pipeline(
            self,
            pipeline_id: UUID,
            config: Dict[str, Any]
    ) -> None:
        """
        Initialize a new pipeline instance with comprehensive setup.

        Args:
            pipeline_id (UUID): Unique identifier for the pipeline
            config (Dict[str, Any]): Configuration for the pipeline
        """
        try:
            # Create initial pipeline state
            state = PipelineState(
                pipeline_id=str(pipeline_id),
                current_stage=ProcessingStage.INITIAL_VALIDATION,
                status=ProcessingStatus.PENDING,
                metadata={},
                config=config
            )
            self.state_manager.add_pipeline(state)

            # Create initial control point
            await self._create_control_point(
                pipeline_id=str(pipeline_id),
                stage=ProcessingStage.INITIAL_VALIDATION,
                data={
                    'config': config,
                    'initialization_timestamp': datetime.now().isoformat()
                }
            )

            # Log initialization
            logger.info(f"Pipeline {pipeline_id} initialized successfully")

            # Notify about pipeline initialization
            await self._notify_pipeline_status(
                pipeline_id=str(pipeline_id),
                status="initialized",
                details={
                    'config': config,
                    'initial_stage': ProcessingStage.INITIAL_VALIDATION.value
                }
            )

        except Exception as e:
            logger.error(f"Error initializing pipeline {pipeline_id}: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def start_pipeline(self, pipeline_id: UUID) -> None:
        """
        Start the pipeline execution with comprehensive error handling.

        Args:
            pipeline_id (UUID): Unique identifier for the pipeline
        """
        try:
            # Retrieve pipeline state
            state = self.state_manager.get_pipeline_state(str(pipeline_id))
            if not state:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            # Update pipeline status
            state.status = ProcessingStatus.RUNNING
            state.start_time = datetime.now()

            # Notify pipeline start
            await self._notify_pipeline_status(
                pipeline_id=str(pipeline_id),
                status="started",
                details={
                    'stage': state.current_stage.value,
                    'start_time': state.start_time.isoformat()
                }
            )

            # Begin initial stage processing
            await self._process_stage(str(pipeline_id))

        except Exception as e:
            logger.error(f"Error starting pipeline {pipeline_id}: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _process_stage(self, pipeline_id: str) -> None:
        """
        Process the current stage of the pipeline with comprehensive
        configuration and staging.

        Args:
            pipeline_id (str): Unique identifier for the pipeline
        """
        try:
            # Retrieve pipeline state
            state = self.state_manager.get_pipeline_state(pipeline_id)
            if not state:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            # Get stage-specific configuration
            stage_config = state.config.get('stages', {}).get(state.current_stage.value, {})
            if not stage_config:
                raise ValueError(f"No configuration for stage {state.current_stage}")

            # Stage the configuration for processors
            await self.staging_manager.stage_data(
                pipeline_id=pipeline_id,
                key=f"stage_config_{state.current_stage.value}",
                data=stage_config
            )

            # Prepare processing message
            message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier("processor_manager"),
                message_type=MessageType.STAGE_INIT,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': state.current_stage.value,
                    'config_key': f"stage_config_{state.current_stage.value}"
                }
            )

            # Publish message via broker
            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Error processing stage for pipeline {pipeline_id}: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_stage_completion(
            self,
            pipeline_id: str,
            stage_results: Dict[str, Any]
    ) -> None:
        """
        Handle stage completion with validation and control point decision.

        Args:
            pipeline_id (str): Unique identifier for the pipeline
            stage_results (Dict[str, Any]): Results from the completed stage
        """
        try:
            # Retrieve pipeline state
            state = self.state_manager.get_pipeline_state(pipeline_id)
            if not state:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            # Get current stage and transition
            current_stage = state.current_stage
            transition = self.stage_transitions.get(current_stage)
            if not transition:
                raise ValueError(f"No transition defined for {current_stage}")

            # Stage stage results
            await self.staging_manager.stage_data(
                pipeline_id=pipeline_id,
                key=f"results_{current_stage.value}",
                data=stage_results
            )

            # Create completion control point
            await self._create_control_point(
                pipeline_id=pipeline_id,
                stage=current_stage,
                data={
                    'results': stage_results,
                    'validation_rules': transition.validation_rules
                }
            )

            # Wait for control point decision
            decision = await self.control_point_manager.wait_for_decision(pipeline_id)

            # Process decision
            if decision.get('decision') == 'proceed':
                await self._advance_stage(pipeline_id, stage_results)
            else:
                await self._handle_stage_rejection(
                    pipeline_id,
                    current_stage,
                    decision.get('reason', 'Stage rejected')
                )

        except Exception as e:
            logger.error(f"Error handling stage completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _advance_stage(
            self,
            pipeline_id: str,
            stage_results: Dict[str, Any]
    ) -> None:
        """Advance pipeline to next stage"""
        try:
            state = self.state_manager.get_pipeline_state(pipeline_id)
            current_stage = state.current_stage
            transition = self.stage_transitions[current_stage]

            # Record completion
            state.record_stage_completion(current_stage.value)

            # Get next stage
            next_stage = transition.to_stage
            if next_stage:
                # Create transition control point
                await self._create_control_point(
                    pipeline_id=pipeline_id,
                    stage=next_stage,
                    data={
                        'from_stage': current_stage.value,
                        'to_stage': next_stage.value,
                        'results': stage_results
                    }
                )

                # Update state
                state.current_stage = next_stage
                await self._process_stage(pipeline_id)
            else:
                # Pipeline complete
                await self._complete_pipeline(pipeline_id)

        except Exception as e:
            logger.error(f"Error advancing stage: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _create_control_point(
            self,
            pipeline_id: str,
            stage: ProcessingStage,
            data: Dict[str, Any]
    ) -> None:
        """Create control point via CPM"""
        try:
            # Get transition for stage
            transition = self.stage_transitions.get(stage)

            # Create control point via CPM
            await self.control_point_manager.create_control_point(
                pipeline_id=pipeline_id,
                stage=stage,
                data={
                    'stage_data': data,
                    'required_artifacts': transition.required_artifacts if transition else [],
                    'validation_rules': transition.validation_rules if transition else {}
                },
                options=['proceed', 'retry', 'reject']
            )

        except Exception as e:
            logger.error(f"Error creating control point: {str(e)}")
            raise

    async def _complete_pipeline(self, pipeline_id: str) -> None:
        """Handle pipeline completion"""
        try:
            state = self.state_manager.get_pipeline_state(pipeline_id)

            # Update state
            state.status = ProcessingStatus.COMPLETED
            state.end_time = datetime.now()

            # Create completion control point
            await self._create_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.FINAL_APPROVAL,
                data={
                    'stages_completed': state.stages_completed,
                    'execution_time': (state.end_time - state.start_time).total_seconds(),
                    'error_count': len(state.error_history)
                }
            )

            # Wait for final approval
            result = await self.control_point_manager.wait_for_decision(pipeline_id)

            if result.get('decision') == 'approve':
                await self._notify_pipeline_status(
                    pipeline_id=pipeline_id,
                    status="completed",
                    details={
                        'success': True,
                        'stages_completed': state.stages_completed
                    }
                )
            else:
                await self._handle_error(
                    pipeline_id,
                    Exception(result.get('reason', 'Final approval rejected'))
                )

        except Exception as e:
            logger.error(f"Error completing pipeline: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _handle_error(self, pipeline_id: UUID, error: Exception) -> None:
        """Handle pipeline errors"""
        try:
            state = self.state_manager.get_pipeline_state(str(pipeline_id))
            if state:
                # Update state
                state.status = ProcessingStatus.FAILED
                state.add_error(str(error))

                # Create error control point
                await self._create_control_point(
                    pipeline_id=str(pipeline_id),
                    stage=state.current_stage,
                    data={
                        'error': str(error),
                        'stage': state.current_stage.value,
                        'error_count': len(state.error_history)
                    }
                )

                # Notify error
                await self._notify_pipeline_status(
                    pipeline_id=str(pipeline_id),
                    status="failed",
                    details={
                        'error': str(error),
                        'stage': state.current_stage.value
                    }
                )

        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}")

    async def _notify_pipeline_status(
            self,
            pipeline_id: str,
            status: str,
            details: Dict[str, Any]
    ) -> None:
        """Notify pipeline status via CPM"""
        try:
            # Create status message
            message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier("control_point_manager"),
                message_type=MessageType.STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'status': status,
                    'details': details,
                    'timestamp': datetime.now().isoformat()
                }
            )

            # Send via Message Broker
            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Error notifying status: {str(e)}")

    def get_pipeline_status(self, pipeline_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve comprehensive pipeline status.

        Args:
            pipeline_id (UUID): Unique identifier for the pipeline

        Returns:
            Optional[Dict[str, Any]]: Detailed pipeline status
        """
        try:
            state = self.state_manager.get_pipeline_state(str(pipeline_id))
            if not state:
                return None

            return {
                'pipeline_id': str(pipeline_id),
                'status': state.status.value,
                'current_stage': state.current_stage.value,
                'progress': state.current_progress,
                'stages_completed': state.stages_completed,
                'error_count': len(state.error_history),
                'start_time': state.start_time.isoformat() if state.start_time else None,
                'end_time': state.end_time.isoformat() if state.end_time else None,
                'metadata': state.metadata
            }

        except Exception as e:
            logger.error(f"Error getting pipeline status: {str(e)}")
            return None

    async def _log_pipeline_event(
            self,
            pipeline_id: UUID,
            event_type: str,
            message: str,
            details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log pipeline events using the repository if available.

        Args:
            pipeline_id (UUID): Unique identifier for the pipeline
            event_type (str): Type of event
            message (str): Event message
            details (Optional[Dict[str, Any]], optional): Additional event details
        """
        if self.repository:
            try:
                event = {
                    'type': event_type,
                    'message': message,
                    'details': details or {}
                }
                self.repository.log_pipeline_event(pipeline_id, event)
            except Exception as e:
                logger.error(f"Error logging pipeline event: {str(e)}")

    async def save_pipeline_state(
            self,
            pipeline_id: UUID,
            state: Dict[str, Any]
    ) -> None:
        """
        Save pipeline state to repository if available.

        Args:
            pipeline_id (UUID): Unique identifier for the pipeline
            state (Dict[str, Any]): State information to save
        """
        if self.repository:
            try:
                self.repository.save_pipeline_state(pipeline_id, state)
            except Exception as e:
                logger.error(f"Error saving pipeline state: {str(e)}")

    async def get_pipeline_metrics(
            self,
            pipeline_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve pipeline metrics from repository.

        Args:
            pipeline_id (UUID): Unique identifier for the pipeline

        Returns:
            Optional[Dict[str, Any]]: Pipeline metrics if available
        """
        if self.repository:
            try:
                return self.repository.get_pipeline_metrics(pipeline_id)
            except Exception as e:
                logger.error(f"Error retrieving pipeline metrics: {str(e)}")
                return None

        return None

    async def cleanup(self) -> None:
        """
        Comprehensive cleanup of active pipelines and resources.
        Extends parent cleanup with repository-specific cleanup.
        """
        try:
            # Cancel all active pipelines
            for pipeline_id in self.state_manager.get_active_pipelines():
                state = self.state_manager.get_pipeline_state(pipeline_id)
                if state and state.status == ProcessingStatus.RUNNING:
                    state.status = ProcessingStatus.CANCELLED

                    # Optionally log cancellation
                    await self._log_pipeline_event(
                        UUID(pipeline_id),
                        'system_cleanup',
                        'Pipeline cancelled during system cleanup'
                    )

                    # Notify pipeline status
                    await self._notify_pipeline_status(
                        pipeline_id=pipeline_id,
                        status="cancelled",
                        details={"reason": "System cleanup"}
                    )

            # Reset state manager
            self.state_manager = PipelineStateManager()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during pipeline manager cleanup: {str(e)}")
