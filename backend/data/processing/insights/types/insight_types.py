# backend/data_pipeline/insights/types/insight_types.py

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

class InsightType(Enum):
    """Types of insights"""
    PATTERN = "pattern"          # Recurring patterns in data
    TREND = "trend"             # Time-based trends
    CORRELATION = "correlation"  # Relationships between variables
    ANOMALY = "anomaly"         # Unusual patterns/outliers
    DISTRIBUTION = "distribution"  # Data distribution insights
    CLUSTER = "cluster"         # Natural groupings
    FORECAST = "forecast"       # Future predictions
    COMPARATIVE = "comparative"  # Comparative insight
    BUSINESS_GOAL = "business_goal"

class InsightCategory(Enum):
    """Categories of insights"""
    STATISTICAL = "statistical"  # Statistical findings
    BUSINESS = "business"       # Business-related insights
    OPERATIONAL = "operational" # Operational findings
    TEMPORAL = "temporal"       # Time-based insights
    BEHAVIORAL = "behavioral"   # Behavior patterns
    TECHNICAL = "technical"     # Technical findings

class InsightPriority(Enum):
    """Priority levels for insights"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"

class InsightPhase(Enum):
    """Phases of insight processing"""
    INITIALIZATION = "initialization"
    PATTERN_DETECTION = "pattern_detection"
    TREND_ANALYSIS = "trend_analysis"
    RELATIONSHIP_ANALYSIS = "relationship_analysis"
    ANOMALY_DETECTION = "anomaly_detection"
    INSIGHT_GENERATION = "insight_generation"
    VALIDATION = "validation"

class InsightStatus(Enum):
    """Status of insight processing"""
    INITIALIZING = "initializing"
    PROCESSING = "processing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_REVIEW = "awaiting_review"

@dataclass
class InsightContext:
    """Context for insight processing"""
    pipeline_id: str
    staged_id: str
    current_phase: InsightPhase
    metadata: Dict[str, Any]
    quality_check_passed: bool
    domain_type: Optional[str] = None
    phase_results: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class InsightConfig:
    """Configuration for insight generation"""
    enabled_types: List[InsightType]
    priority_threshold: InsightPriority
    confidence_threshold: float
    time_window: Optional[str] = None
    max_insights: Optional[int] = None
    custom_rules: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PatternInsight:
    """Pattern-based insight"""
    pattern_id: str
    pattern_type: str
    description: str
    frequency: int
    confidence: float
    supporting_data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TrendInsight:
    """Trend-based insight"""
    trend_id: str
    trend_type: str
    direction: str
    magnitude: float
    time_range: Dict[str, datetime]
    confidence: float
    supporting_data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RelationshipInsight:
    """Relationship-based insight"""
    relationship_id: str
    variables: List[str]
    relationship_type: str
    strength: float
    description: str
    confidence: float
    supporting_data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AnomalyInsight:
    """Anomaly-based insight"""
    anomaly_id: str
    anomaly_type: str
    severity: float
    affected_data: List[Any]
    detection_method: str
    confidence: float
    supporting_data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class InsightResult:
    """Combined insight result"""
    insight_id: str
    insight_type: InsightType
    category: InsightCategory
    priority: InsightPriority
    title: str
    description: str
    confidence: float
    supporting_data: Dict[str, Any]
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class InsightValidation:
    """Validation results for insights"""
    insight_id: str
    validation_status: bool
    validation_method: str
    confidence_score: float
    validation_details: Dict[str, Any]
    reviewer: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    validated_at: datetime = field(default_factory=datetime.now)

@dataclass
class InsightMetrics:
    """Metrics for insight assessment"""
    total_insights: int
    insights_by_type: Dict[InsightType, int]
    insights_by_priority: Dict[InsightPriority, int]
    average_confidence: float
    validation_rate: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

# Custom types for insight generation
DataPattern = Dict[str, Union[str, float, List[Any]]]
TrendData = Dict[str, Union[datetime, float, str]]
RelationshipData = Dict[str, Union[List[str], float, str]]
AnomalyData = Dict[str, Union[List[Any], float, str]]

@dataclass
class InsightProcessState:
    """State of insight processing"""
    pipeline_id: str
    staged_id: str
    current_status: InsightStatus
    current_phase: InsightPhase
    metrics: InsightMetrics
    insights_generated: int = 0
    insights_validated: int = 0
    requires_review: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)