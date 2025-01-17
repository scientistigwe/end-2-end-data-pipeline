# backend/data_pipeline/recommendation/types/recommendation_types.py

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

class RecommendationType(Enum):
    """Types of recommendations"""
    CONTENT_BASED = "content_based"
    COLLABORATIVE = "collaborative"
    CONTEXTUAL = "contextual"
    HYBRID = "hybrid"

class RecommendationPhase(Enum):
    """Phases of recommendation processing"""
    CANDIDATE_GENERATION = "candidate_generation"
    FILTERING = "filtering"
    RANKING = "ranking"
    AGGREGATION = "aggregation"
    FINALIZATION = "finalization"

class RecommendationStatus(Enum):
    """Status of recommendation process"""
    INITIALIZING = "initializing"
    GENERATING = "generating"
    FILTERING = "filtering"
    RANKING = "ranking"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class RecommendationContext:
    """Context for recommendation processing"""
    pipeline_id: str
    source_component: str
    request_type: str
    current_phase: RecommendationPhase
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class RecommendationCandidate:
    """Represents a recommendation candidate"""
    item_id: str
    source: RecommendationType
    scores: Dict[str, float]
    features: Dict[str, Any]
    metadata: Dict[str, Any]

@dataclass
class RankedRecommendation:
    """Represents a ranked recommendation"""
    candidate: RecommendationCandidate
    final_score: float
    rank: int
    ranking_factors: Dict[str, float]
    confidence: float

@dataclass
class RecommendationResult:
    """Result of recommendation process"""
    pipeline_id: str
    recommendations: List[RankedRecommendation]
    metadata: Dict[str, Any]
    scores: Dict[str, float]
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class RecommendationState:
    """State of recommendation process"""
    pipeline_id: str
    current_phase: RecommendationPhase
    status: RecommendationStatus
    candidates: List[RecommendationCandidate]
    ranked_items: List[RankedRecommendation]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)