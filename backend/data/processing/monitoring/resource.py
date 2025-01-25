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

class ResourceMonitor:
    """System resource monitoring"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.monitoring_task = None

    async def start_monitoring(self, interval: int = 60):
        """Start resource monitoring"""
        self.monitoring_task = asyncio.create_task(
            self._monitor_loop(interval)
        )

    async def stop_monitoring(self):
        """Stop resource monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self, interval: int):
        """Monitoring loop"""
        while True:
            try:
                await self._collect_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {str(e)}", exc_info=True)
                await asyncio.sleep(interval)

    async def _collect_metrics(self):
        """Collect system metrics"""
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        await self.metrics_collector.record_metric(
            'system_cpu_usage',
            cpu_percent,
            'system',
            'resource_monitor',
            metric_type='resource'
        )

        # Memory metrics
        memory = psutil.virtual_memory()
        await self.metrics_collector.record_metric(
            'system_memory_usage',
            memory.percent,
            'system',
            'resource_monitor',
            metric_type='resource'
        )

        # Disk metrics
        disk = psutil.disk_usage('/')
        await self.metrics_collector.record_metric(
            'system_disk_usage',
            disk.percent,
            'system',
            'resource_monitor',
            metric_type='resource'
        )
