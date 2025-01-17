# backend/data_pipeline/quality/types/quality_types.py

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

class QualityCheckType(Enum):
    """Types of quality checks"""
    BASIC_VALIDATION = "basic_validation"
    ADDRESS_LOCATION = "address_location"
    CODE_CLASSIFICATION = "code_classification"
    DATETIME_PROCESSING = "datetime_processing"
    DOMAIN_VALIDATION = "domain_validation"
    DUPLICATION_CHECK = "duplication_check"
    IDENTIFIER_CHECK = "identifier_check"
    NUMERIC_CURRENCY = "numeric_currency"
    TEXT_STANDARD = "text_standard"

class QualityIssueType(Enum):
    """Types of quality issues"""
    MISSING_VALUE = "missing_value"
    DATA_TYPE_MISMATCH = "data_type_mismatch"
    FORMAT_ERROR = "format_error"
    RANGE_VIOLATION = "range_violation"
    PATTERN_MISMATCH = "pattern_mismatch"
    DUPLICATE_ENTRY = "duplicate_entry"
    VALIDATION_ERROR = "validation_error"
    REFERENCE_ERROR = "reference_error"
    CONSISTENCY_ERROR = "consistency_error"

class ResolutionType(Enum):
    """Types of issue resolutions"""
    AUTO_FIX = "auto_fix"
    MANUAL_FIX = "manual_fix"
    IGNORE = "ignore"
    REJECT = "reject"
    ESCALATE = "escalate"

class QualityPhase(Enum):
    """Phases of quality processing"""
    DETECTION = "detection"
    ANALYSIS = "analysis"
    RESOLUTION = "resolution"
    VALIDATION = "validation"

@dataclass
class QualityContext:
    """Context for quality processing"""
    pipeline_id: str
    staged_id: str
    current_phase: QualityPhase
    metadata: Dict[str, Any]
    detection_results: Optional[Dict[str, Any]] = None
    analysis_results: Optional[Dict[str, Any]] = None
    resolution_results: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class QualityIssue:
    """Representation of a quality issue"""
    issue_id: str
    issue_type: QualityIssueType
    column_name: str
    description: str
    severity: int
    affected_rows: List[int]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class QualityAnalysis:
    """Analysis of quality issues"""
    issue_id: str
    analysis_type: str
    findings: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ResolutionAction:
    """Action for resolving quality issues"""
    issue_id: str
    resolution_type: ResolutionType
    action_params: Dict[str, Any]
    requires_approval: bool = False
    approved_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ValidationResult:
    """Results of resolution validation"""
    issue_id: str
    validation_status: bool
    checks_performed: List[str]
    remaining_issues: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class QualityCheckConfig:
    """Configuration for quality checks"""
    check_type: QualityCheckType
    parameters: Dict[str, Any]
    thresholds: Dict[str, float]
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QualityRules:
    """Rules for quality validation"""
    rule_id: str
    rule_type: str
    conditions: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    priority: int
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QualityMetrics:
    """Metrics for quality assessment"""
    total_issues: int
    issues_by_type: Dict[QualityIssueType, int]
    auto_resolvable: int
    manual_required: int
    resolution_rate: float
    average_severity: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

# Type aliases for common types
ColumnChecks = Dict[str, List[QualityCheckType]]
IssueMap = Dict[str, QualityIssue]
ResolutionMap = Dict[str, ResolutionAction]
ValidationMap = Dict[str, ValidationResult]

# Quality processing states
class QualityState(Enum):
    """States of quality processing"""
    INITIALIZING = "initializing"
    DETECTING = "detecting"
    ANALYZING = "analyzing"
    RESOLVING = "resolving"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class QualityProcessState:
    """State of quality processing"""
    pipeline_id: str
    staged_id: str
    current_state: QualityState
    current_phase: QualityPhase
    metrics: QualityMetrics
    issues_found: int = 0
    issues_resolved: int = 0
    requires_attention: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)