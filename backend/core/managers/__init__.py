"""
Core Managers Initialization Module

This module provides centralized initialization and import management
for various domain-specific managers in the data processing pipeline.

Managers represent high-level orchestration components responsible for
coordinating complex workflows, resource allocation, and cross-component
communication within specific domains.

Modules:
- PipelineManager: Orchestrates overall pipeline processing
- QualityManager: Coordinates data quality management
- InsightManager: Manages insight generation processes
- RecommendationManager: Handles recommendation workflows
- DecisionManager: Coordinates decision-making processes
- MonitoringManager: Manages system monitoring and metrics
- ReportManager: Oversees report generation
- AdvancedAnalyticsManager: Manages complex analytics processing
"""

from .pipeline_manager import PipelineManager
from .quality_manager import QualityManager
from .insight_manager import InsightManager
from .recommendation_manager import RecommendationManager
from .decision_manager import DecisionManager
from .monitoring_manager import MonitoringManager
from .report_manager import ReportManager
from .advanced_analytics_manager import AnalyticsManager

__all__ = [
    'PipelineManager',
    'QualityManager',
    'InsightManager',
    'RecommendationManager',
    'DecisionManager',
    'MonitoringManager',
    'ReportManager',
    'AnalyticsManager'
]