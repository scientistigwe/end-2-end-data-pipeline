from __future__ import annotations

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
from collections import defaultdict
import psutil
import json

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric measurement"""
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Centralized metrics collection for all data sources"""

    def __init__(self):
        self.metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._start_time = time.time()

    async def record_metric(
            self,
            name: str,
            value: float,
            source_type: str,
            source_id: str,
            **labels
    ):
        """Record a metric with source information"""
        labels.update({
            'source_type': source_type,
            'source_id': source_id
        })

        self.metrics[name].append(MetricPoint(
            value=value,
            labels=labels
        ))

    async def get_metrics(
            self,
            source_type: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get metrics, optionally filtered by source type"""
        if source_type:
            return {
                name: [
                    {
                        'value': point.value,
                        'timestamp': point.timestamp.isoformat(),
                        'labels': point.labels
                    }
                    for point in points
                    if point.labels.get('source_type') == source_type
                ]
                for name, points in self.metrics.items()
            }
        return {
            name: [
                {
                    'value': point.value,
                    'timestamp': point.timestamp.isoformat(),
                    'labels': point.labels
                }
                for point in points
            ]
            for name, points in self.metrics.items()
        }
