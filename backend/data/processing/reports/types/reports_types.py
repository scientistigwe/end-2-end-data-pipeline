# backend/data_pipeline/reporting/types/report_types.py

from enum import Enum
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass, field
from uuid import UUID


class ReportStage(Enum):
    """Report stages in the pipeline"""
    DATA_QUALITY = "data_quality"
    QUALITY_RESOLUTION = "quality_resolution"
    INSIGHT_ANALYSIS = "insight_analysis"
    ADVANCED_ANALYTICS = "advanced_analytics"
    PIPELINE_SUMMARY = "pipeline_summary"


class ReportStatus(Enum):
    """Status of report generation"""
    PENDING = "pending"
    GENERATING = "generating"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWED = "reviewed"
    ARCHIVED = "archived"
    FAILED = "failed"


class ReportFormat(Enum):
    """Supported report output formats"""
    HTML = "html"
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass
class ReportContent:
    """Base structure for report content"""
    section_id: UUID
    title: str
    content_type: str
    content: Union[str, Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ReportVisualization:
    """Structure for report visualizations"""
    viz_id: UUID
    title: str
    viz_type: str  # e.g., 'chart', 'table', 'metric_card'
    data: Dict[str, Any]
    config: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportSection:
    """Structure for report sections"""
    section_id: UUID
    title: str
    description: str
    content: List[ReportContent]
    visualizations: List[ReportVisualization] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    order: int = 0


@dataclass
class Report:
    """Complete report structure"""
    report_id: UUID
    pipeline_id: str
    stage: ReportStage
    title: str
    description: str
    sections: List[ReportSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ReportStatus = field(default=ReportStatus.PENDING)
    format: ReportFormat = field(default=ReportFormat.HTML)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "system"
    version: str = "1.0"


@dataclass
class QualityReport(Report):
    """Quality insight specific report"""
    quality_score: float = 0.0
    issues_found: int = 0
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    profile_data: Dict[str, Any] = field(default_factory=dict)  # ydata profiling results


@dataclass
class InsightReport(Report):
    """Insight insight specific report"""
    business_goals: List[str] = field(default_factory=list)
    insights_found: int = 0
    goal_alignment_score: float = 0.0
    analytics_recommendations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AnalyticsReport(Report):
    """Advanced analytics specific report"""
    analysis_type: str = "general"
    model_performance: Dict[str, float] = field(default_factory=dict)
    predictions: Dict[str, Any] = field(default_factory=dict)
    feature_importance: Dict[str, float] = field(default_factory=dict)


@dataclass
class PipelineSummaryReport(Report):
    """Overall pipeline summary report"""
    total_duration: float = 0.0
    stages_completed: List[str] = field(default_factory=list)
    key_decisions: List[Dict[str, Any]] = field(default_factory=list)
    final_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    quality_summary: Dict[str, Any] = field(default_factory=dict)
    insight_summary: Dict[str, Any] = field(default_factory=dict)
    analytics_summary: Optional[Dict[str, Any]] = field(default_factory=dict)