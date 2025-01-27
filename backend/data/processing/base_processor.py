"""
Enhanced Decision and Analytics Processors with comprehensive lifecycle management.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Set
from datetime import datetime

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    DecisionMessageType, AnalyticsMessageType,
    DecisionContext, AnalyticsContext,
    ModuleIdentifier, ComponentType
)
from core.staging.staging_manager import StagingManager


class BaseProcessor:
    """Base processor with shared functionality"""

    def __init__(self, message_broker: MessageBroker, staging_manager: StagingManager):
        self.message_broker = message_broker
        self.staging_manager = staging_manager
        self.active_processes: Dict[str, Any] = {}
        self.health_check_interval = 60
        self.resource_check_interval = 30
        self.cleanup_interval = 300

    async def _check_resource_availability(self, requirements: Dict[str, Any]) -> bool:
        """Verify resource availability before processing"""
        current_usage = await self._get_current_resource_usage()
        return all(
            current_usage.get(resource, 0) + amount <= self._get_resource_limits()[resource]
            for resource, amount in requirements.items()
        )

    async def _allocate_resources(self, context: Any) -> bool:
        """Allocate required resources with locking"""
        try:
            async with self._resource_lock:
                if await self._check_resource_availability(context.resource_requirements):
                    context.allocated_resources = context.resource_requirements.copy()
                    await self._update_resource_usage(context.allocated_resources)
                    return True
                return False
        except Exception as e:
            logger.error(f"Resource allocation failed: {str(e)}")
            return False

    async def _release_resources(self, context: Any) -> None:
        """Release allocated resources safely"""
        try:
            async with self._resource_lock:
                if context.allocated_resources:
                    await self._update_resource_usage(
                        context.allocated_resources,
                        release=True
                    )
                    context.allocated_resources.clear()
        except Exception as e:
            logger.error(f"Resource release failed: {str(e)}")

    async def _monitor_resource_usage(self) -> None:
        """Monitor resource usage and handle overages"""
        while True:
            try:
                usage = await self._get_current_resource_usage()
                limits = self._get_resource_limits()

                for resource, usage_amount in usage.items():
                    if usage_amount > limits[resource] * 0.9:  # 90% threshold
                        await self._handle_resource_pressure(resource)

                await asyncio.sleep(self.resource_check_interval)
            except Exception as e:
                logger.error(f"Resource monitoring failed: {str(e)}")


