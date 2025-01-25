# staging_manager.py

import logging
import asyncio
import json
import shutil
import uuid
import random
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    StagingContext,
    StagingState,
    StagingMetrics
)
from core.monitoring.collectors import MetricsCollector

logger = logging.getLogger(__name__)


class StagingError(Exception):
    """Base exception for staging-related errors"""
    pass


@contextmanager
def staging_operation(operation_name: str):
    """Context manager for staging operations with error handling"""
    try:
        logger.debug(f"Starting staging operation: {operation_name}")
        yield
        logger.debug(f"Completed staging operation: {operation_name}")
    except Exception as e:
        logger.error(f"Staging operation '{operation_name}' failed: {str(e)}")
        raise StagingError(f"Operation '{operation_name}' failed: {str(e)}")


class StagingManager:
    """
    Message-based staging manager for data pipeline operations.
    Handles temporary data storage and retrieval through message broker communication.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            base_path: Optional[str] = None,
            cleanup_interval: int = 3600,
            max_age_hours: int = 24,
            max_size_bytes: int = 10_737_418_240,  # 10GB
            metrics_collector: Optional[MetricsCollector] = None
    ):
        self.message_broker = message_broker
        self.base_path = Path(base_path or Path.cwd() / 'staged_data')
        self.metrics_collector = metrics_collector or MetricsCollector()

        # Configuration
        self.cleanup_interval = cleanup_interval
        self.max_age = timedelta(hours=max_age_hours)
        self.max_size_bytes = max_size_bytes

        # State tracking
        self.active_stages: Dict[str, StagingContext] = {}
        self.global_metrics = StagingMetrics()
        self._running = True

        # Component identification
        self.component_name = "staging_manager"

        # Initialize system
        self._ensure_storage_path()
        self._setup_message_handlers()
        self._start_cleanup_task()

        logger.info(f"Staging manager initialized at {self.base_path}")

    def _ensure_storage_path(self) -> None:
        """Ensure base storage path exists"""
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _setup_message_handlers(self) -> None:
        """Initialize message handlers for staging operations"""
        handlers = {
            MessageType.STAGING_STORE_REQUEST: self._handle_store_request,
            MessageType.STAGING_RETRIEVE_REQUEST: self._handle_retrieve_request,
            MessageType.STAGING_ACCESS_REQUEST: self._handle_access_request,
            MessageType.STAGING_DELETE_REQUEST: self._handle_delete_request,
            MessageType.STAGING_ACCESS_GRANT: self._handle_access_grant,
            MessageType.STAGING_METRICS_REQUEST: self._handle_metrics_request
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.component_name,
                f"staging.{message_type.value}.#",
                handler
            )

    async def _handle_store_request(self, message: ProcessingMessage) -> None:
        """Handle data storage requests"""
        stage_id = message.content['stage_id']
        pipeline_id = message.content['pipeline_id']
        data = message.content['data']
        metadata = message.content.get('metadata', {})

        async with staging_operation("store_data"):
            try:
                context = StagingContext(
                    stage_id=stage_id,
                    pipeline_id=pipeline_id,
                    metadata=metadata
                )
                self.active_stages[stage_id] = context

                # Store data
                storage_path = self.base_path / stage_id
                storage_path.mkdir(parents=True, exist_ok=True)
                context.storage_path = storage_path

                data_file = storage_path / 'data.json'
                with open(data_file, 'w') as f:
                    json.dump(data, f)

                context.state = StagingState.STORED
                context.size_bytes = data_file.stat().st_size
                context.update_metrics("store", context.size_bytes)

                await self._notify_store_complete(stage_id, message)

            except Exception as e:
                context.state = StagingState.ERROR
                context.error = str(e)
                await self._notify_error(stage_id, str(e), message)

    async def _handle_retrieve_request(self, message: ProcessingMessage) -> None:
        """Handle data retrieval requests"""
        stage_id = message.content['stage_id']
        requester = message.metadata.source_component

        async with staging_operation("retrieve_data"):
            context = self.active_stages.get(stage_id)
            if not context or not context.has_access(requester):
                await self._notify_access_denied(stage_id, requester, message)
                return

            try:
                data_file = context.storage_path / 'data.json'
                with open(data_file, 'r') as f:
                    data = json.load(f)

                context.update_metrics("retrieve")
                await self._notify_retrieve_complete(stage_id, data, message)

            except Exception as e:
                await self._notify_error(stage_id, str(e), message)

    async def _handle_access_request(self, message: ProcessingMessage) -> None:
        """Handle access request messages"""
        stage_id = message.content['stage_id']
        requester = message.metadata.source_component

        context = self.active_stages.get(stage_id)
        if not context:
            await self._notify_error(stage_id, "Stage not found", message)
            return

        context.grant_access(requester)
        await self._notify_access_granted(stage_id, requester, message)

    async def _handle_access_grant(self, message: ProcessingMessage) -> None:
        """Handle access grant messages"""
        stage_id = message.content['stage_id']
        granted_to = message.content['component_id']

        context = self.active_stages.get(stage_id)
        if context:
            context.grant_access(granted_to)

    async def _handle_delete_request(self, message: ProcessingMessage) -> None:
        """Handle deletion requests"""
        stage_id = message.content['stage_id']

        async with staging_operation("delete_data"):
            context = self.active_stages.get(stage_id)
            if not context:
                await self._notify_error(stage_id, "Stage not found", message)
                return

            try:
                if context.storage_path and context.storage_path.exists():
                    shutil.rmtree(context.storage_path)

                context.state = StagingState.DELETED
                del self.active_stages[stage_id]

                await self._notify_delete_complete(stage_id, message)

            except Exception as e:
                await self._notify_error(stage_id, str(e), message)

    async def _handle_metrics_request(self, message: ProcessingMessage) -> None:
        """Handle metrics request messages"""
        await self._publish_metrics(message.metadata.source_component)

    async def _notify_store_complete(self, stage_id: str, original_message: ProcessingMessage) -> None:
        """Notify about successful storage"""
        context = self.active_stages[stage_id]
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGING_STORE_COMPLETE,
            content={
                'stage_id': stage_id,
                'size_bytes': context.size_bytes,
                'metadata': context.metadata
            },
            metadata=MessageMetadata(
                source_component=self.component_name,
                target_component=original_message.metadata.source_component
            )
        ))

    async def _notify_retrieve_complete(
            self,
            stage_id: str,
            data: Any,
            original_message: ProcessingMessage
    ) -> None:
        """Notify about successful retrieval"""
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGING_RETRIEVE_COMPLETE,
            content={
                'stage_id': stage_id,
                'data': data
            },
            metadata=MessageMetadata(
                source_component=self.component_name,
                target_component=original_message.metadata.source_component
            )
        ))

    async def _notify_delete_complete(self, stage_id: str, original_message: ProcessingMessage) -> None:
        """Notify about successful deletion"""
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGING_DELETE_COMPLETE,
            content={'stage_id': stage_id},
            metadata=MessageMetadata(
                source_component=self.component_name,
                target_component=original_message.metadata.source_component
            )
        ))

    async def _notify_error(
            self,
            stage_id: str,
            error: str,
            original_message: ProcessingMessage
    ) -> None:
        """Notify about operation error"""
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGING_ERROR,
            content={
                'stage_id': stage_id,
                'error': error
            },
            metadata=MessageMetadata(
                source_component=self.component_name,
                target_component=original_message.metadata.source_component
            )
        ))

    async def _notify_access_denied(
            self,
            stage_id: str,
            requester: str,
            original_message: ProcessingMessage
    ) -> None:
        """Notify about access denial"""
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGING_ACCESS_DENIED,
            content={
                'stage_id': stage_id,
                'reason': 'Access not authorized'
            },
            metadata=MessageMetadata(
                source_component=self.component_name,
                target_component=requester
            )
        ))

    async def _notify_access_granted(
            self,
            stage_id: str,
            requester: str,
            original_message: ProcessingMessage
    ) -> None:
        """Notify about access grant"""
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGING_ACCESS_GRANTED,
            content={
                'stage_id': stage_id,
                'granted_to': requester
            },
            metadata=MessageMetadata(
                source_component=self.component_name,
                target_component=requester
            )
        ))

    async def _publish_metrics(self, target_component: str) -> None:
        """Publish current metrics"""
        self.global_metrics.active_stages = len(self.active_stages)
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGING_METRICS_UPDATE,
            content={
                'metrics': self.global_metrics.__dict__,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component=self.component_name,
                target_component=target_component
            )
        ))

    def _start_cleanup_task(self) -> None:
        """Start periodic cleanup task"""
        asyncio.create_task(self._periodic_cleanup())

    async def _periodic_cleanup(self) -> None:
        """Run periodic cleanup with error handling and backoff"""
        base_interval = self.cleanup_interval
        max_interval = base_interval * 10
        current_interval = base_interval

        while self._running:
            try:
                await self._cleanup_expired_stages()
                current_interval = base_interval

            except Exception as e:
                logger.error(f"Cleanup error: {str(e)}")
                current_interval = min(current_interval * 2, max_interval)

            await asyncio.sleep(current_interval)

    async def _cleanup_expired_stages(self) -> None:
        """Clean up expired stages"""
        current_time = datetime.now()

        for stage_id, context in list(self.active_stages.items()):
            age = current_time - context.created_at
            if age > self.max_age:
                await self._handle_delete_request(ProcessingMessage(
                    message_type=MessageType.STAGING_DELETE_REQUEST,
                    content={'stage_id': stage_id},
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component=self.component_name
                    )
                ))

    async def cleanup(self) -> None:
        """Perform complete cleanup"""
        self._running = False

        for stage_id in list(self.active_stages.keys()):
            try:
                await self._handle_delete_request(ProcessingMessage(
                    message_type=MessageType.STAGING_DELETE_REQUEST,
                    content={'stage_id': stage_id},
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component=self.component_name
                    )
                ))
            except Exception as e:
                logger.error(f"Error cleaning up stage {stage_id}: {str(e)}")