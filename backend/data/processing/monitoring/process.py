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
from .collectors.metric_collector import MetricsCollector


logger = logging.getLogger(__name__)

class ProcessMonitor:
    """Process-specific monitoring"""

    def __init__(
            self,
            metrics_collector: MetricsCollector,
            source_type: str,
            source_id: str
    ):
        self.metrics_collector = metrics_collector
        self.source_type = source_type
        self.source_id = source_id
        self.start_time = time.time()

    async def record_operation_metric(
            self,
            operation: str,
            success: bool,
            duration: float,
            **labels
    ):
        """Record operation metrics"""
        # Record success/failure
        await self.metrics_collector.record_metric(
            f'{operation}_success',
            1 if success else 0,
            self.source_type,
            self.source_id,
            operation=operation,
            **labels
        )

        # Record duration
        await self.metrics_collector.record_metric(
            f'{operation}_duration',
            duration,
            self.source_type,
            self.source_id,
            operation=operation,
            **labels
        )

    async def record_data_metric(
            self,
            metric_name: str,
            value: float,
            **labels
    ):
        """Record data-related metrics"""
        await self.metrics_collector.record_metric(
            metric_name,
            value,
            self.source_type,
            self.source_id,
            metric_type='data',
            **labels
        )

    async def record_error(
            self,
            error_type: str,
            **labels
    ):
        """Record error occurrences"""
        await self.metrics_collector.record_metric(
            'error_count',
            1,
            self.source_type,
            self.source_id,
            error_type=error_type,
            **labels
        )