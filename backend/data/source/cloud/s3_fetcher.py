from __future__ import annotations

import logging
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List
from datetime import datetime
import aioboto3
import pandas as pd
from io import BytesIO
from dataclasses import dataclass, field

from backend.core.monitoring.process import ProcessMonitor
from backend.core.monitoring.collectors import MetricsCollector
from backend.core.utils.rate_limiter import AsyncRateLimiter
from .s3_config import Config

logger = logging.getLogger(__name__)


@dataclass
class TransferContext:
    """Context for S3 data transfers"""
    operation_id: str
    bucket: str
    key: str
    start_time: datetime = field(default_factory=datetime.now)
    bytes_transferred: int = 0
    parts_completed: int = 0
    total_parts: Optional[int] = None
    status: str = "pending"


class S3Fetcher:
    """Enhanced S3 fetcher with comprehensive capabilities"""

    def __init__(
            self,
            config: Optional[Config] = None,
            metrics_collector: Optional[MetricsCollector] = None
    ):
        """Initialize fetcher with configuration"""
        self.config = config or Config()
        self.metrics_collector = metrics_collector or MetricsCollector()

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="s3_fetcher",
            source_id="fetcher"
        )

        # Initialize rate limiter
        self.rate_limiter = AsyncRateLimiter(
            max_calls=100,
            period=1.0
        )

        # Initialize session
        self.session = aioboto3.Session()
        self.s3_client = None

        # Transfer tracking
        self.active_transfers: Dict[str, TransferContext] = {}

        # Chunk size for multipart operations
        self.chunk_size = self.config.CHUNK_SIZE

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup_client()

    async def _ensure_client(self):
        """Ensure S3 client exists"""
        if not self.s3_client:
            self.s3_client = await self.session.client('s3')

    async def _cleanup_client(self):
        """Clean up S3 client"""
        if self.s3_client:
            await self.s3_client.close()
            self.s3_client = None

    async def fetch_object_async(
            self,
            bucket: str,
            key: str,
            **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch object from S3 asynchronously

        Args:
            bucket: S3 bucket name
            key: Object key
            **kwargs: Additional fetch arguments

        Returns:
            Dictionary containing object data and metadata
        """
        try:
            await self._ensure_client()

            # Create transfer context
            context = TransferContext(
                operation_id=key.replace('/', '_'),
                bucket=bucket,
                key=key
            )

            self.active_transfers[context.operation_id] = context

            # Get object metadata first
            head_response = await self.s3_client.head_object(
                Bucket=bucket,
                Key=key
            )

            size = head_response['ContentLength']

            # Record start metrics
            await self.process_monitor.record_metric(
                'object_fetch_start',
                1,
                size=size,
                bucket=bucket,
                key=key
            )

            # Determine fetch method based on size
            if size > self.config.MULTIPART_THRESHOLD:
                data = await self._fetch_large_object(context, size)
            else:
                data = await self._fetch_small_object(context)

            # Process data based on format
            processed_data = await self._process_data(
                data,
                head_response['ContentType']
            )

            # Record completion metrics
            duration = (datetime.now() - context.start_time).total_seconds()
            await self.process_monitor.record_operation_metric(
                'object_fetch',
                success=True,
                duration=duration,
                bytes_transferred=size,
                operation_id=context.operation_id
            )

            return {
                'data': processed_data,
                'metadata': {
                    'content_type': head_response['ContentType'],
                    'size': size,
                    'last_modified': head_response['LastModified'].isoformat(),
                    'etag': head_response['ETag'],
                    'fetch_stats': {
                        'duration': duration,
                        'parts_completed': context.parts_completed,
                        'total_parts': context.total_parts
                    }
                }
            }

        except Exception as e:
            await self.process_monitor.record_error(
                'object_fetch_error',
                error=str(e),
                bucket=bucket,
                key=key
            )
            raise
        finally:
            # Cleanup transfer context
            if context.operation_id in self.active_transfers:
                del self.active_transfers[context.operation_id]

    async def _fetch_small_object(
            self,
            context: TransferContext
    ) -> bytes:
        """Fetch small object in single request"""
        try:
            response = await self.s3_client.get_object(
                Bucket=context.bucket,
                Key=context.key
            )

            async with response['Body'] as stream:
                data = await stream.read()

            context.bytes_transferred = len(data)
            context.parts_completed = 1
            context.total_parts = 1

            return data

        except Exception as e:
            logger.error(f"Small object fetch error: {str(e)}")
            raise

    async def _fetch_large_object(
            self,
            context: TransferContext,
            size: int
    ) -> bytes:
        """Fetch large object in parts"""
        try:
            buffer = BytesIO()
            part_size = self.chunk_size
            total_parts = (size + part_size - 1) // part_size
            context.total_parts = total_parts

            async for chunk in self._fetch_object_parts(context, size, part_size):
                buffer.write(chunk)
                context.parts_completed += 1

                # Record progress metrics
                await self.process_monitor.record_metric(
                    'object_fetch_progress',
                    context.parts_completed / total_parts * 100,
                    operation_id=context.operation_id
                )

            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Large object fetch error: {str(e)}")
            raise

    async def _fetch_object_parts(
            self,
            context: TransferContext,
            size: int,
            part_size: int
    ) -> AsyncGenerator[bytes, None]:
        """Generator to fetch object parts"""
        for start in range(0, size, part_size):
            end = min(start + part_size - 1, size - 1)

            response = await self.s3_client.get_object(
                Bucket=context.bucket,
                Key=context.key,
                Range=f'bytes={start}-{end}'
            )

            async with response['Body'] as stream:
                chunk = await stream.read()
                context.bytes_transferred += len(chunk)
                yield chunk

    async def _process_data(
            self,
            data: bytes,
            content_type: str
    ) -> Any:
        """Process data based on content type"""
        try:
            format_type = content_type.split('/')[-1].lower()

            if format_type == 'csv':
                return pd.read_csv(BytesIO(data))
            elif format_type == 'json':
                return pd.read_json(BytesIO(data))
            elif format_type == 'parquet':
                return pd.read_parquet(BytesIO(data))
            else:
                return data

        except Exception as e:
            logger.error(f"Data processing error: {str(e)}")
            raise

    async def list_objects_async(
            self,
            bucket: str,
            prefix: str = '',
            max_items: Optional[int] = None,
            **kwargs
    ) -> Dict[str, Any]:
        """List objects from S3 bucket asynchronously"""
        try:
            await self._ensure_client()

            list_params = {
                'Bucket': bucket,
                'Prefix': prefix,
                'MaxKeys': max_items or 1000,
                **kwargs
            }

            objects = []
            continuation_token = None

            while True:
                if continuation_token:
                    list_params['ContinuationToken'] = continuation_token

                response = await self.s3_client.list_objects_v2(**list_params)

                objects.extend([{
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag']
                } for obj in response.get('Contents', [])])

                if not response.get('IsTruncated'):
                    break

                continuation_token = response.get('NextContinuationToken')

                # Break if we've reached max_items
                if max_items and len(objects) >= max_items:
                    objects = objects[:max_items]
                    break

            return {
                'objects': objects,
                'count': len(objects),
                'prefix': prefix,
                'continuation_token': continuation_token,
                'is_truncated': bool(continuation_token)
            }

        except Exception as e:
            logger.error(f"List objects error: {str(e)}")
            raise

    async def check_connection(self) -> Dict[str, Any]:
        """Check S3 connection and capabilities"""
        try:
            await self._ensure_client()

            start_time = datetime.now()
            response = await self.s3_client.list_buckets()
            latency = (datetime.now() - start_time).total_seconds()

            buckets = response.get('Buckets', [])

            return {
                'status': 'connected',
                'diagnostics': {
                    'latency': latency,
                    'buckets_accessible': len(buckets),
                    'timestamp': datetime.now().isoformat()
                },
                'capabilities': {
                    'multipart_supported': True,
                    'max_upload_size': '5TB',
                    'max_part_size': '5GB'
                }
            }

        except Exception as e:
            logger.error(f"Connection check error: {str(e)}")
            return {
                'status': 'error',
                'diagnostics': {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
            }

    async def get_transfer_status(
            self,
            operation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get status of active transfer"""
        context = self.active_transfers.get(operation_id)
        if not context:
            return None

        return {
            'operation_id': operation_id,
            'status': context.status,
            'bucket': context.bucket,
            'key': context.key,
            'start_time': context.start_time.isoformat(),
            'bytes_transferred': context.bytes_transferred,
            'parts_completed': context.parts_completed,
            'total_parts': context.total_parts,
            'progress': (
                (context.parts_completed / context.total_parts * 100)
                if context.total_parts
                else 0
            )
        }

    async def list_active_transfers(self) -> List[Dict[str, Any]]:
        """List all active transfers"""
        return [
            await self.get_transfer_status(operation_id)
            for operation_id in self.active_transfers
        ]

    async def cleanup(self):
        """Clean up resources"""
        try:
            # Clean up client
            await self._cleanup_client()

            # Clear tracking
            self.active_transfers.clear()

        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")
            raise