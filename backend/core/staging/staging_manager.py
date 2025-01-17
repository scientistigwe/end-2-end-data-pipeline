# backend/core/staging/staging_manager.py

from datetime import datetime, timedelta
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from uuid import uuid4
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage
from backend.db.models.staging_model import StagedData, SourceStageMetadata, StagingState, StagingControlPoint
from backend.core.monitoring.process import ProcessMonitor

logger = logging.getLogger(__name__)


class StagingManager:
    """Manages staging area for all data sources"""

    def __init__(
            self,
            db_session: AsyncSession,
            message_broker: MessageBroker,
            base_path: str = "staging"
    ):
        self.db_session = db_session
        self.message_broker = message_broker
        self.base_path = Path(base_path)
        self.process_monitor = ProcessMonitor()

        # Create staging directories
        self._create_staging_directories()

    def _create_staging_directories(self):
        """Create required staging directories"""
        for dir_name in ['temp', 'active', 'archive']:
            dir_path = self.base_path / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)

    async def create_staging_area(
            self,
            source_type: str,
            source_identifier: str,
            metadata: Dict[str, Any]
    ) -> str:
        """Create a new staging area for data"""
        try:
            # Create staged data record
            staged_data = StagedData(
                id=str(uuid4()),
                source_type=source_type,
                source_identifier=source_identifier,
                source_metadata=metadata,
                status='initializing'
            )

            self.db_session.add(staged_data)
            await self.db_session.commit()

            # Create source-specific metadata
            source_metadata = SourceStageMetadata(
                staged_data_id=staged_data.id,
                source_type=source_type,
                metadata=self._get_source_metadata(source_type, metadata)
            )

            self.db_session.add(source_metadata)
            await self.db_session.commit()

            # Create initial state
            state = StagingState(
                staged_data_id=staged_data.id,
                stage='initialization',
                status='pending'
            )

            self.db_session.add(state)
            await self.db_session.commit()

            # Create storage directory for file-based sources
            if source_type in ['file', 'cloud']:
                storage_path = self._create_storage_path(staged_data.id)
                staged_data.storage_path = str(storage_path)
                await self.db_session.commit()

            await self._notify_staging_created(staged_data.id, source_type)
            return staged_data.id

        except Exception as e:
            logger.error(f"Error creating staging area: {str(e)}")
            raise

    def _get_source_metadata(
            self,
            source_type: str,
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract source-specific metadata"""
        if source_type == 'file':
            return {
                'file_original_name': metadata.get('filename'),
                'file_mime_type': metadata.get('mime_type')
            }
        elif source_type == 'api':
            return {
                'api_endpoint': metadata.get('endpoint'),
                'api_method': metadata.get('method')
            }
        elif source_type == 'cloud':
            return {
                'cloud_provider': metadata.get('provider'),
                'cloud_region': metadata.get('region'),
                'cloud_path': metadata.get('path')
            }
        elif source_type == 'stream':
            return {
                'stream_checkpoint': metadata.get('checkpoint'),
                'stream_position': metadata.get('position', 0)
            }
        elif source_type == 'db':
            return {
                'db_query': metadata.get('query'),
                'db_table_name': metadata.get('table_name')
            }
        return {}

    def _create_storage_path(self, staged_id: str) -> Path:
        """Create storage path for staged data"""
        today = datetime.now().strftime('%Y-%m-%d')
        storage_path = self.base_path / 'active' / today / staged_id
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path

    async def store_staged_data(
            self,
            staged_id: str,
            data: Any,
            metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store data in staging area"""
        try:
            # Get staged data record
            staged_data = await self._get_staged_data(staged_id)
            if not staged_data:
                raise ValueError(f"No staging area found for ID: {staged_id}")

            # Store based on source type
            if staged_data.source_type == 'file':
                await self._store_file_data(staged_data, data)
            elif staged_data.source_type == 'api':
                await self._store_api_data(staged_data, data)
            elif staged_data.source_type == 'cloud':
                await self._store_cloud_data(staged_data, data)
            elif staged_data.source_type == 'stream':
                await self._store_stream_data(staged_data, data)
            elif staged_data.source_type == 'db':
                await self._store_db_data(staged_data, data)

            # Update metadata if provided
            if metadata:
                staged_data.source_metadata.update(metadata)
                await self.db_session.commit()

            await self._notify_data_stored(staged_id)
            return True

        except Exception as e:
            logger.error(f"Error storing staged data: {str(e)}")
            raise

    async def get_staged_data(
            self,
            staged_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve staged data"""
        try:
            staged_data = await self._get_staged_data(staged_id)
            if not staged_data:
                return None

            # Get data based on source type
            if staged_data.source_type == 'file':
                data = await self._get_file_data(staged_data)
            elif staged_data.source_type == 'api':
                data = await self._get_api_data(staged_data)
            elif staged_data.source_type == 'cloud':
                data = await self._get_cloud_data(staged_data)
            elif staged_data.source_type == 'stream':
                data = await self._get_stream_data(staged_data)
            elif staged_data.source_type == 'db':
                data = await self._get_db_data(staged_data)
            else:
                data = None

            return {
                'id': staged_data.id,
                'source_type': staged_data.source_type,
                'source_identifier': staged_data.source_identifier,
                'metadata': staged_data.source_metadata,
                'data': data,
                'status': staged_data.status,
                'created_at': staged_data.created_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Error retrieving staged data: {str(e)}")
            raise

    async def update_stage_status(
            self,
            staged_id: str,
            stage: str,
            status: str,
            metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update staging state"""
        try:
            state = await self._get_or_create_state(staged_id, stage)
            state.status = status

            if metadata:
                state.processing_metadata = metadata

            if status in ['completed', 'failed']:
                state.completed_at = datetime.now()

            await self.db_session.commit()
            await self._notify_status_update(staged_id, stage, status)
            return True

        except Exception as e:
            logger.error(f"Error updating stage status: {str(e)}")
            raise

    async def create_control_point(
            self,
            staged_id: str,
            control_point_type: str,
            metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create control point for staging area"""
        try:
            control_point = StagingControlPoint(
                id=str(uuid4()),
                staged_data_id=staged_id,
                control_point_type=control_point_type,
                status='pending'
            )

            if metadata:
                control_point.metadata = metadata

            self.db_session.add(control_point)
            await self.db_session.commit()

            await self._notify_control_point_created(control_point.id)
            return control_point.id

        except Exception as e:
            logger.error(f"Error creating control point: {str(e)}")
            raise

    async def archive_staged_data(
            self,
            staged_id: str,
            ttl_days: int = 30
    ) -> bool:
        """Archive staged data"""
        try:
            staged_data = await self._get_staged_data(staged_id)
            if not staged_data:
                return False

            # Move file-based data to archive
            if staged_data.storage_path:
                archive_path = self._create_archive_path(staged_id)
                shutil.move(staged_data.storage_path, str(archive_path))
                staged_data.storage_path = str(archive_path)

            # Update status and expiry
            staged_data.status = 'archived'
            staged_data.expires_at = datetime.now() + timedelta(days=ttl_days)
            await self.db_session.commit()

            await self._notify_data_archived(staged_id)
            return True

        except Exception as e:
            logger.error(f"Error archiving staged data: {str(e)}")
            raise

    def _create_archive_path(self, staged_id: str) -> Path:
        """Create archive path for staged data"""
        today = datetime.now().strftime('%Y-%m-%d')
        archive_path = self.base_path / 'archive' / today / staged_id
        archive_path.mkdir(parents=True, exist_ok=True)
        return archive_path

    async def cleanup_expired_data(self) -> int:
        """Clean up expired staged data"""
        try:
            # Find expired records
            query = select(StagedData).where(
                StagedData.expires_at < datetime.now(),
                StagedData.status == 'archived'
            )
            result = await self.db_session.execute(query)
            expired_data = result.scalars().all()

            cleaned_count = 0
            for data in expired_data:
                # Remove files if exist
                if data.storage_path:
                    path = Path(data.storage_path)
                    if path.exists():
                        if path.is_file():
                            path.unlink()
                        else:
                            shutil.rmtree(path)

                # Remove db records
                await self.db_session.delete(data)
                cleaned_count += 1

            await self.db_session.commit()
            return cleaned_count

        except Exception as e:
            logger.error(f"Error cleaning up expired data: {str(e)}")
            raise

    async def _notify_staging_created(self, staged_id: str, source_type: str):
        """Notify about staging area creation"""
        message = ProcessingMessage(
            message_type=MessageType.STAGE_STORE,
            content={
                'staged_id': staged_id,
                'source_type': source_type,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    async def _notify_data_stored(self, staged_id: str):
        """Notify about data being stored"""
        message = ProcessingMessage(
            message_type=MessageType.STAGE_SUCCESS,
            content={
                'staged_id': staged_id,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    async def _notify_status_update(self, staged_id: str, stage: str, status: str):
        """Notify about status update"""
        message = ProcessingMessage(
            message_type=MessageType.STAGE_UPDATE,
            content={
                'staged_id': staged_id,
                'stage': stage,
                'status': status,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    async def _notify_control_point_created(self, control_point_id: str):
        """Notify about control point creation"""
        message = ProcessingMessage(
            message_type=MessageType.CONTROL_POINT_REACHED,
            content={
                'control_point_id': control_point_id,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    async def _notify_data_archived(self, staged_id: str):
        """Notify about data being archived"""
        message = ProcessingMessage(
            message_type=MessageType.STAGE_COMPLETE,
            content={
                'staged_id': staged_id,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    # Helper methods for source-specific storage
    async def _store_file_data(self, staged_data: StagedData, data: bytes):
        """Store file data"""
        file_path = Path(staged_data.storage_path) / "data"
        file_path.write_bytes(data)
        staged_data.data_size = len(data)
        await self.db_session.commit()

    async def _store_api_data(self, staged_data: StagedData, data: Dict):
        """Store API response data"""
        file_path = Path(staged_data.storage_path) / "response.json"
        file_path.write_text(json.dumps(data))
        staged_data.data_size = len(json.dumps(data))
        await self.db_session.commit()

    async def _store_cloud_data(self, staged_data: StagedData, data: bytes):
        """Store cloud data"""
        file_path = Path(staged_data.storage_path) / "data"
        file_path.write_bytes(data)
        staged_data.data_size = len(data)
        await self.db_session.commit()

    async def _store_stream_data(self, staged_data: StagedData, data: bytes):
        """Store stream data"""
        file_path = Path(staged_data.storage_path) / "stream_data"
        file_path.write_bytes(data)
        staged_data.data_size = len(data)
        await self.db_session.commit()



        async def _store_db_data(self, staged_data: StagedData, data: List[Dict]):
            """Store db query results"""
            file_path = Path(staged_data.storage_path) / "query_results.json"
            file_path.write_text(json.dumps(data))
            staged_data.data_size = len(json.dumps(data))

            # Update metadata with row count
            source_metadata = await self._get_source_metadata_record(staged_data.id)
            if source_metadata:
                source_metadata.db_row_count = len(data)

            await self.db_session.commit()

        async def _get_file_data(self, staged_data: StagedData) -> Optional[bytes]:
            """Retrieve file data"""
            file_path = Path(staged_data.storage_path) / "data"
            if file_path.exists():
                return file_path.read_bytes()
            return None

        async def _get_api_data(self, staged_data: StagedData) -> Optional[Dict]:
            """Retrieve API response data"""
            file_path = Path(staged_data.storage_path) / "response.json"
            if file_path.exists():
                return json.loads(file_path.read_text())
            return None

        async def _get_cloud_data(self, staged_data: StagedData) -> Optional[bytes]:
            """Retrieve cloud data"""
            file_path = Path(staged_data.storage_path) / "data"
            if file_path.exists():
                return file_path.read_bytes()
            return None

        async def _get_stream_data(self, staged_data: StagedData) -> Optional[bytes]:
            """Retrieve stream data"""
            file_path = Path(staged_data.storage_path) / "stream_data"
            if file_path.exists():
                return file_path.read_bytes()
            return None

        async def _get_db_data(self, staged_data: StagedData) -> Optional[List[Dict]]:
            """Retrieve db query results"""
            file_path = Path(staged_data.storage_path) / "query_results.json"
            if file_path.exists():
                return json.loads(file_path.read_text())
            return None

        async def _get_staged_data(self, staged_id: str) -> Optional[StagedData]:
            """Get staged data record"""
            query = select(StagedData).where(StagedData.id == staged_id)
            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()

        async def _get_source_metadata_record(self, staged_id: str) -> Optional[SourceStageMetadata]:
            """Get source metadata record"""
            query = select(SourceStageMetadata).where(
                SourceStageMetadata.staged_data_id == staged_id
            )
            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()

        async def _get_or_create_state(
                self,
                staged_id: str,
                stage: str
        ) -> StagingState:
            """Get or create staging state record"""
            query = select(StagingState).where(
                StagingState.staged_data_id == staged_id,
                StagingState.stage == stage
            )
            result = await self.db_session.execute(query)
            state = result.scalar_one_or_none()

            if not state:
                state = StagingState(
                    staged_data_id=staged_id,
                    stage=stage,
                    status='pending'
                )
                self.db_session.add(state)

            return state

        async def get_staging_metrics(self) -> Dict[str, Any]:
            """Get staging area metrics"""
            try:
                # Get counts by status
                status_counts = {}
                for status in ['active', 'archived', 'failed']:
                    query = select(func.count(StagedData.id)).where(
                        StagedData.status == status
                    )
                    result = await self.db_session.execute(query)
                    status_counts[status] = result.scalar()

                # Get counts by source type
                source_type_counts = {}
                query = select(
                    StagedData.source_type,
                    func.count(StagedData.id)
                ).group_by(StagedData.source_type)
                result = await self.db_session.execute(query)
                source_type_counts = dict(result.all())

                # Get storage metrics
                storage_metrics = await self._get_storage_metrics()

                return {
                    'status_counts': status_counts,
                    'source_type_counts': source_type_counts,
                    'storage_metrics': storage_metrics,
                    'timestamp': datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Error getting staging metrics: {str(e)}")
                raise

        async def _get_storage_metrics(self) -> Dict[str, int]:
            """Calculate storage metrics"""
            metrics = {
                'total_size': 0,
                'active_size': 0,
                'archived_size': 0
            }

            # Sum data sizes
            query = select(
                StagedData.status,
                func.sum(StagedData.data_size)
            ).group_by(StagedData.status)
            result = await self.db_session.execute(query)

            for status, size in result:
                if status == 'active':
                    metrics['active_size'] = size or 0
                elif status == 'archived':
                    metrics['archived_size'] = size or 0

            metrics['total_size'] = metrics['active_size'] + metrics['archived_size']
            return metrics

        async def vacuum_staging(self, older_than_days: int = 7) -> int:
            """Remove old archived data"""
            try:
                cutoff_date = datetime.now() - timedelta(days=older_than_days)

                # Find old archived data
                query = select(StagedData).where(
                    StagedData.status == 'archived',
                    StagedData.created_at < cutoff_date
                )
                result = await self.db_session.execute(query)
                old_data = result.scalars().all()

                removed_count = 0
                for data in old_data:
                    # Remove files
                    if data.storage_path:
                        path = Path(data.storage_path)
                        if path.exists():
                            if path.is_file():
                                path.unlink()
                            else:
                                shutil.rmtree(path)

                    # Remove db record
                    await self.db_session.delete(data)
                    removed_count += 1

                await self.db_session.commit()

                await self._notify_vacuum_complete(removed_count)
                return removed_count

            except Exception as e:
                logger.error(f"Error vacuuming staging area: {str(e)}")
                raise

        async def _notify_vacuum_complete(self, removed_count: int):
            """Notify about vacuum completion"""
            message = ProcessingMessage(
                message_type=MessageType.STAGE_VALIDATE,
                content={
                    'operation': 'vacuum',
                    'removed_count': removed_count,
                    'timestamp': datetime.now().isoformat()
                }
            )
            await self.message_broker.publish(message)

        async def get_stage_history(self, staged_id: str) -> List[Dict[str, Any]]:
            """Get complete history of a staged item"""
            try:
                # Get all states
                query = select(StagingState).where(
                    StagingState.staged_data_id == staged_id
                ).order_by(StagingState.created_at)
                result = await self.db_session.execute(query)
                states = result.scalars().all()

                # Get all control points
                query = select(StagingControlPoint).where(
                    StagingControlPoint.staged_data_id == staged_id
                ).order_by(StagingControlPoint.created_at)
                result = await self.db_session.execute(query)
                control_points = result.scalars().all()

                # Combine and sort by timestamp
                history = []

                for state in states:
                    history.append({
                        'type': 'state',
                        'stage': state.stage,
                        'status': state.status,
                        'timestamp': state.created_at.isoformat(),
                        'metadata': state.processing_metadata
                    })

                for cp in control_points:
                    history.append({
                        'type': 'control_point',
                        'control_type': cp.control_point_type,
                        'status': cp.status,
                        'timestamp': cp.created_at.isoformat(),
                        'decision': cp.decision
                    })

                return sorted(history, key=lambda x: x['timestamp'])

            except Exception as e:
                logger.error(f"Error getting stage history: {str(e)}")
                raise