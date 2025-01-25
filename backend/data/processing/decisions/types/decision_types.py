# backend/data_pipeline/decision/types/decision_types.py

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

class DecisionSource(Enum):
    """Source of decision request"""
    QUALITY = "quality"            # Quality findings requiring decision
    INSIGHTS = "insights"          # Insight-based decisions
    ANALYTICS = "analytics"        # Advanced analytics decisions
    PIPELINE = "pipeline"          # Pipeline flow decisions
    SYSTEM = "system"             # System-level decisions

class DecisionPhase(Enum):
    """Phases of decision processing"""
    INITIALIZATION = "initialization"
    ANALYSIS = "insight"
    RECOMMENDATION = "recommendation"
    VALIDATION = "validation"
    EXECUTION = "execution"
    REVIEW = "review"

class DecisionStatus(Enum):
    """Status of decision process"""
    INITIALIZING = "initializing"
    ANALYZING = "analyzing"
    AWAITING_INPUT = "awaiting_input"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"

class DecisionPriority(Enum):
    """Priority levels for decisions"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ROUTINE = "routine"

@dataclass
class DecisionRequest:
    """Decision request from a component"""
    request_id: str
    pipeline_id: str
    source: DecisionSource
    options: List[Dict[str, Any]]
    context: Dict[str, Any]
    priority: DecisionPriority
    requires_confirmation: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ComponentDecision:
    """Decision made for a component"""
    decision_id: str
    request_id: str
    pipeline_id: str
    source: DecisionSource
    selected_option: Dict[str, Any]
    impacts: Dict[str, Dict[str, Any]]  # Impact on other components
    user_confirmation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class DecisionImpact:
    """Impact of a decision on components"""
    decision_id: str
    affected_components: Dict[str, Dict[str, Any]]
    cascading_effects: List[Dict[str, Any]]
    requires_updates: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DecisionValidation:
    """Validation results for a decision"""
    decision_id: str
    validation_type: str
    passed: bool
    issues: List[Dict[str, Any]]
    component_validations: Dict[str, bool]  # Validation by each affected component
    metadata: Dict[str, Any] = field(default_factory=dict)
    validated_at: datetime = field(default_factory=datetime.now)

@dataclass
class DecisionState:
    """Current state of decision process"""
    pipeline_id: str
    current_requests: List[DecisionRequest]
    pending_decisions: List[ComponentDecision]
    completed_decisions: List[ComponentDecision]
    status: DecisionStatus
    phase: DecisionPhase
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class ComponentUpdate:
    """Component update about decision impact"""
    component: str
    decision_id: str
    pipeline_id: str
    status: str
    impact_details: Dict[str, Any]
    requires_action: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

# Type aliases for common structures
ComponentImpacts = Dict[str, Dict[str, Any]]
ValidationResults = Dict[str, DecisionValidation]
UpdateResponses = Dict[str, ComponentUpdate]