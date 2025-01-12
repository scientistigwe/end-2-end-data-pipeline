# backend/core/orchestration/pipeline_manager_helper.py

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID

from backend.core.messaging.types import (
    ProcessingStage,
    ProcessingStatus
)


@dataclass
class StageTransition:
    """
    Defines rules and requirements for transitioning between pipeline stages.

    Attributes:
        from_stage (ProcessingStage): The starting stage of the transition
        to_stage (ProcessingStage): The target stage for the transition
        required_artifacts (List[str]): Artifacts that must be present to transition
        validation_rules (Dict[str, Any]): Rules that must be satisfied to proceed
    """
    from_stage: ProcessingStage
    to_stage: Optional[ProcessingStage]
    required_artifacts: List[str] = field(default_factory=list)
    validation_rules: Dict[str, Any] = field(default_factory=dict)


class PipelineStateManager:
    """
    Manages the state of multiple pipeline instances.

    Provides methods to add, retrieve, and manage pipeline states.
    """

    def __init__(self):
        """
        Initialize the state manager with an empty dictionary of pipeline states.
        """
        self._pipeline_states: Dict[str, 'PipelineState'] = {}

    def add_pipeline(self, state: 'PipelineState') -> None:
        """
        Add a new pipeline state to the manager.

        Args:
            state (PipelineState): The pipeline state to add

        Raises:
            ValueError: If a pipeline with the same ID already exists
        """
        if state.pipeline_id in self._pipeline_states:
            raise ValueError(f"Pipeline {state.pipeline_id} already exists")

        self._pipeline_states[state.pipeline_id] = state

    def get_pipeline_state(self, pipeline_id: str) -> Optional['PipelineState']:
        """
        Retrieve the state of a specific pipeline.

        Args:
            pipeline_id (str): The unique identifier of the pipeline

        Returns:
            Optional[PipelineState]: The pipeline state if found, None otherwise
        """
        return self._pipeline_states.get(pipeline_id)

    def update_pipeline_state(self, pipeline_id: str, state: 'PipelineState') -> None:
        """
        Update the state of an existing pipeline.

        Args:
            pipeline_id (str): The unique identifier of the pipeline
            state (PipelineState): The updated pipeline state

        Raises:
            ValueError: If the pipeline does not exist
        """
        if pipeline_id not in self._pipeline_states:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        self._pipeline_states[pipeline_id] = state

    def remove_pipeline(self, pipeline_id: str) -> None:
        """
        Remove a pipeline from the manager.

        Args:
            pipeline_id (str): The unique identifier of the pipeline to remove
        """
        if pipeline_id in self._pipeline_states:
            del self._pipeline_states[pipeline_id]

    def get_active_pipelines(self) -> List[str]:
        """
        Get a list of active pipeline IDs.

        Returns:
            List[str]: List of pipeline IDs with active status
        """
        return [
            pid for pid, state in self._pipeline_states.items()
            if state.status in [
                ProcessingStatus.PENDING,
                ProcessingStatus.RUNNING,
                ProcessingStatus.AWAITING_DECISION
            ]
        ]


@dataclass
class PipelineState:
    """
    Represents the complete state of a pipeline instance.

    Attributes:
        pipeline_id (str): Unique identifier for the pipeline
        current_stage (ProcessingStage): Current processing stage
        status (ProcessingStatus): Current processing status
        metadata (Dict[str, Any]): Additional metadata about the pipeline
        config (Dict[str, Any]): Configuration for the pipeline
        start_time (Optional[datetime]): Time the pipeline started
        end_time (Optional[datetime]): Time the pipeline ended
        current_progress (float): Progress of the current stage (0.0 to 1.0)
        stages_completed (List[str]): List of completed stage names
        error_history (List[str]): List of errors encountered
    """
    pipeline_id: str
    current_stage: ProcessingStage
    status: ProcessingStatus
    metadata: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    current_progress: float = 0.0
    stages_completed: List[str] = field(default_factory=list)
    error_history: List[str] = field(default_factory=list)

    def record_stage_completion(self, stage_name: str) -> None:
        """
        Record the completion of a stage.

        Args:
            stage_name (str): Name of the completed stage
        """
        if stage_name not in self.stages_completed:
            self.stages_completed.append(stage_name)

        # Reset progress for new stage
        self.current_progress = 0.0

    def update_progress(self, progress: float) -> None:
        """
        Update the progress of the current stage.

        Args:
            progress (float): Progress percentage (0.0 to 1.0)

        Raises:
            ValueError: If progress is not between 0.0 and 1.0
        """
        if not 0.0 <= progress <= 1.0:
            raise ValueError("Progress must be between 0.0 and 1.0")

        self.current_progress = progress

    def add_error(self, error_message: str) -> None:
        """
        Add an error to the error history.

        Args:
            error_message (str): Description of the error
        """
        self.error_history.append(error_message)

        # Optionally update status to failed if not already in a final state
        if self.status not in [
            ProcessingStatus.COMPLETED,
            ProcessingStatus.CANCELLED,
            ProcessingStatus.FAILED
        ]:
            self.status = ProcessingStatus.FAILED