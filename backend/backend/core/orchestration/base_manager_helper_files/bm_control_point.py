# backend/core/base/base_manager_control_point.py

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.core.messaging.types import (
    ProcessingStage,
    ProcessingMessage,
    MessageType,
    ModuleIdentifier
)
from .bm_constants import ResourceState
from .bm_metrics import ManagerMetadata


@dataclass
class ControlPoint:
    """Control point tracking with enhanced properties"""
    control_point_id: str
    pipeline_id: str
    stage: ProcessingStage
    options: List[str]
    data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: int = 3600
    status: str = "pending"
    decision: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    required_artifacts: Optional[List[str]] = None

    def validate_decision(self, decision: str) -> bool:
        """
        Validate if the decision is allowed for this control point.

        Args:
            decision (str): Decision to validate

        Returns:
            bool: True if decision is valid, False otherwise
        """
        return decision in self.options

    def update_status(self, decision: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Update control point status based on decision.

        Args:
            decision (str): Decision made
            details (Optional[Dict[str, Any]], optional): Additional details. Defaults to None.
        """
        self.status = "decided"
        self.decision = {
            'decision': decision,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }


class ControlPointManager:
    """
    Centralized control point management with advanced tracking and validation.
    """

    def __init__(self,
                 metadata: ManagerMetadata,
                 message_broker=None,
                 logger=None):
        """
        Initialize control point manager.

        Args:
            metadata (ManagerMetadata): Manager metadata for tracking
            message_broker (Optional): Message broker for notifications
            logger (Optional): Logger for tracking events
        """
        self._active_control_points: Dict[str, ControlPoint] = {}
        self._metadata = metadata
        self._message_broker = message_broker
        self._logger = logger

    def create_control_point(
            self,
            pipeline_id: str,
            stage: ProcessingStage,
            data: Dict[str, Any],
            options: List[str],
            validation_rules: Optional[Dict[str, Any]] = None,
            required_artifacts: Optional[List[str]] = None,
            timeout_seconds: int = 3600
    ) -> str:
        """
        Create a new control point with comprehensive validation.

        Args:
            pipeline_id (str): Pipeline identifier
            stage (ProcessingStage): Current pipeline stage
            data (Dict[str, Any]): Stage-specific data
            options (List[str]): Allowed decision options
            validation_rules (Optional[Dict[str, Any]], optional): Additional validation rules
            required_artifacts (Optional[List[str]], optional): Artifacts required for progression
            timeout_seconds (int, optional): Timeout for decision. Defaults to 3600.

        Returns:
            str: Generated control point ID
        """
        control_point_id = f"cp_{pipeline_id}_{stage.value}_{datetime.now().timestamp()}"

        control_point = ControlPoint(
            control_point_id=control_point_id,
            pipeline_id=pipeline_id,
            stage=stage,
            data=data,
            options=options,
            timeout_seconds=timeout_seconds,
            validation_rules=validation_rules,
            required_artifacts=required_artifacts
        )

        # Store control point
        self._active_control_points[control_point_id] = control_point

        # Update metrics
        self._metadata.control_point_metrics.active_control_points += 1
        self._metadata.control_point_metrics.decisions_pending += 1

        # Optional: Notify about control point
        self._notify_control_point(control_point)

        return control_point_id

    def _notify_control_point(self, control_point: ControlPoint) -> None:
        """
        Send notification about a new control point.

        Args:
            control_point (ControlPoint): Control point to notify about
        """
        if not self._message_broker or not self._logger:
            return

        try:
            message = ProcessingMessage(
                source_identifier=ModuleIdentifier("base_manager_helper_files"),
                target_identifier=ModuleIdentifier("ui_handler"),
                message_type=MessageType.CONTROL_POINT_REACHED,
                content={
                    'control_point_id': control_point.control_point_id,
                    'pipeline_id': control_point.pipeline_id,
                    'stage': control_point.stage.value,
                    'data': control_point.data,
                    'options': control_point.options,
                    'timeout_seconds': control_point.timeout_seconds,
                    'validation_rules': control_point.validation_rules,
                    'required_artifacts': control_point.required_artifacts
                }
            )

            self._message_broker.publish(message)
            self._logger.info(f"Control point {control_point.control_point_id} notification sent")

        except Exception as e:
            if self._logger:
                self._logger.error(f"Error notifying control point: {str(e)}")

    def validate_stage_transition(
            self,
            control_point: ControlPoint,
            decision_details: Dict[str, Any]
    ) -> bool:
        """
        Validate stage transition based on control point rules.

        Args:
            control_point (ControlPoint): Control point to validate
            decision_details (Dict[str, Any]): Decision details

        Returns:
            bool: Whether transition is valid
        """
        # Validate against rules if present
        if control_point.validation_rules:
            for rule, condition in control_point.validation_rules.items():
                if rule not in decision_details:
                    return False

                # Basic rule validation (can be expanded)
                if not eval(f"{decision_details.get(rule)} {condition}"):
                    return False

        # Validate artifacts if required
        if control_point.required_artifacts:
            artifacts = decision_details.get('artifacts', [])
            if not all(artifact in artifacts for artifact in control_point.required_artifacts):
                return False

        return True

    def cleanup_expired_control_points(self, current_time: datetime) -> List[str]:
        """
        Clean up expired control points.

        Args:
            current_time (datetime): Current timestamp

        Returns:
            List[str]: List of expired control point IDs
        """
        expired_points = [
            cp_id for cp_id, cp in self._active_control_points.items()
            if (current_time - cp.created_at).total_seconds() > cp.timeout_seconds
        ]

        for cp_id in expired_points:
            self._metadata.control_point_metrics.decisions_timeout += 1
            del self._active_control_points[cp_id]

        return expired_points