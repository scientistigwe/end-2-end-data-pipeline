# backend/core/utils/rate_limiter.py

import os
from typing import Dict, Any
import asyncio
from enum import Enum
from datetime import time
from uuid import uuid4
from aiohttp import web
from dataclasses import dataclass, field

class AsyncRateLimiter:
    """Rate limiter for async operations"""

    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self._calls = []

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def acquire(self):
        """Acquire permission to proceed"""
        now = time.time()
        # Remove old calls
        self._calls = [call for call in self._calls if call > now - self.period]
        if len(self._calls) >= self.max_calls:
            sleep_time = self._calls[0] - (now - self.period)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        self._calls.append(now)

