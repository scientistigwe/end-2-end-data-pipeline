# backend/core/staging/staging_manager.py

import logging
import asyncio
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy import func

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType, ProcessingStage, ProcessingStatus,
    MessageMetadata, ModuleIdentifier, ComponentType, ReportSectionType
)

# Import all staging models
from db.models.staging.base_staging_model import BaseStagedOutput
from db.models.staging.quality_output_model import StagedQualityOutput
from db.models.staging.insight_output_model import StagedInsightOutput
from db.models.staging.advanced_analytics_output_model import StagedAnalyticsOutput
from db.models.staging.report_output_model import StagedReportOutput
from db.models.staging.staging_history_model import StagingProcessingHistory
from db.models.staging.staging_control_model import StagingControlPoint

# Import data source and pipeline models
from db.models.data_source import (
    DataSource, FileSourceInfo, APISourceConfig,
    DatabaseSourceConfig, S3SourceConfig, StreamSourceConfig
)
from db.models.pipeline import (
    Pipeline, PipelineStep, PipelineRun, PipelineStepRun,
    QualityGate, PipelineLog
)

from db.models.auth import (
    User, UserSession, UserActivityLog, TeamMember, ServiceAccount
)

logger = logging.getLogger(__name__)


class StagingManager:
    """
    Comprehensive Staging Manager handling all aspects of data staging
    Including storage, tracking, versioning, and cleanup
    """

    def __init__(self, message_broker: MessageBroker, db_session):
        self.message_broker = message_broker
        self.db_session = db_session

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="staging_manager",
            component_type=ComponentType.MANAGER,
            department="staging",
            role="manager"
        )

        # Model mappings
        self._output_model_map = {
            ComponentType.QUALITY: StagedQualityOutput,
            ComponentType.INSIGHT: StagedInsightOutput,
            ComponentType.ANALYTICS: StagedAnalyticsOutput,
            ComponentType.REPORT: StagedReportOutput
        }

        self._source_config_map = {
            'file': FileSourceInfo,
            'api': APISourceConfig,
            'db': DatabaseSourceConfig,
            's3': S3SourceConfig,
            'stream': StreamSourceConfig
        }

        # Initialize
        self._initialize()

    def _initialize(self):
        """Initialize staging manager and start background tasks"""
        try:
            # Subscribe to messages
            asyncio.create_task(
                self.message_broker.subscribe(
                    self.module_identifier,
                    [
                        "data.storage",
                        "stage.*",
                        "*.complete",
                        "cleanup.request"
                    ],
                    self._handle_staging_message
                )
            )

            # Start cleanup task
            asyncio.create_task(self._periodic_cleanup())

            logger.info("Staging Manager initialized successfully")

        except Exception as e:
            logger.error(f"Staging Manager initialization failed: {str(e)}")
            raise

    # DATA INGESTION AND STORAGE

    async def store_incoming_data(
            self,
            pipeline_id: str,
            data: Any,
            metadata: Dict[str, Any],
            source_type: str,
            user_id: Optional[str] = None
    ) -> str:
        """Store incoming data with complete tracking"""
        try:
            # Validate pipeline and source
            pipeline = await self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")

            if user_id and pipeline.owner_id != user_id:
                raise ValueError("Unauthorized access to pipeline")

            source = await self.db_session.query(DataSource).get(pipeline.source_id)
            if not source:
                raise ValueError(f"Data source not found for pipeline: {pipeline_id}")

            # Create staged output
            output_id = str(uuid.uuid4())
            staged_output = BaseStagedOutput(
                id=output_id,
                pipeline_id=pipeline_id,
                component_type=ComponentType.QUALITY_MANAGER,
                output_type=ReportSectionType.DATA,
                status=ProcessingStatus.PENDING,
                metadata={
                    **metadata,
                    'source_id': str(source.id),
                    'source_type': source.type,
                    'source_name': source.name,
                    'ingestion_time': datetime.utcnow().isoformat()
                },
                storage_path=f"data/{pipeline_id}/{output_id}",
                data_size=len(str(data))
            )

            self.db_session.add(staged_output)

            # Create pipeline run
            pipeline_run = PipelineRun(
                pipeline_id=pipeline_id,
                version=pipeline.version,
                status='running',
                start_time=datetime.utcnow(),
                trigger_type='data_received',
                inputs={
                    'staged_id': output_id,
                    'source_type': source.type
                }
            )
            self.db_session.add(pipeline_run)

            # Track processing history
            history = StagingProcessingHistory(
                staged_output_id=output_id,
                event_type="data_received",
                status=ProcessingStatus.PENDING,
                details={
                    "source_type": source_type,
                    "pipeline_run_id": pipeline_run.id,
                    "user_id": user_id
                }
            )
            self.db_session.add(history)

            # Log pipeline event
            pipeline_log = PipelineLog(
                pipeline_id=pipeline_id,
                event_type='data_staged',
                message=f"Data received from source {source.name}",
                details={
                    'staged_id': output_id,
                    'source_type': source.type,
                    'user_id': user_id
                },
                timestamp=datetime.utcnow()
            )
            self.db_session.add(pipeline_log)

            await self.db_session.commit()

            # Notify CPM
            await self._notify_data_staged(
                output_id,
                staged_output.metadata,
                pipeline_id,
                pipeline_run.id
            )

            return output_id

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Data staging failed: {str(e)}")
            raise

    async def store_component_output(
            self,
            staged_id: str,
            component_type: ComponentType,
            output: Dict[str, Any],
            output_type: ReportSectionType,
            user_id: Optional[str] = None
    ) -> bool:
        """Store processing output from a component"""
        try:
            # Validate access if user_id provided
            if user_id and not await self.check_access_permission(
                    staged_id, user_id, 'write'
            ):
                raise ValueError("Unauthorized access")

            # Get output model
            output_model = self._output_model_map.get(component_type)
            if not output_model:
                raise ValueError(f"Unknown component type: {component_type}")

            # Create component output
            component_output = output_model(
                id=staged_id,
                **output
            )
            self.db_session.add(component_output)

            # Update base output
            base_output = await self.db_session.query(BaseStagedOutput).get(staged_id)
            if base_output:
                base_output.status = ProcessingStatus.COMPLETED
                base_output.updated_at = datetime.utcnow()

            # Add history entry
            history = StagingProcessingHistory(
                staged_output_id=staged_id,
                event_type=f"{component_type.value}_complete",
                status=ProcessingStatus.COMPLETED,
                details={
                    "output_type": output_type.value,
                    "user_id": user_id
                }
            )
            self.db_session.add(history)

            await self.db_session.commit()
            return True

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Output storage failed: {str(e)}")
            return False

    # DATA RETRIEVAL AND ACCESS

    async def retrieve_data(
            self,
            staged_id: str,
            component_type: ComponentType,
            user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve data for component processing with access control"""
        try:
            # Validate access
            if user_id and not await self.check_access_permission(
                    staged_id, user_id, 'read'
            ):
                return None

            # Get base output
            base_output = await self.db_session.query(BaseStagedOutput).get(staged_id)
            if not base_output:
                return None

            # Update status
            base_output.status = ProcessingStatus.PROCESSING
            base_output.updated_at = datetime.utcnow()

            # Add history
            history = StagingProcessingHistory(
                staged_output_id=staged_id,
                event_type="data_retrieved",
                status=ProcessingStatus.IN_PROGRESS,
                details={
                    "component_type": component_type.value,
                    "user_id": user_id
                }
            )
            self.db_session.add(history)

            await self.db_session.commit()

            # Get component-specific output if exists
            component_output = None
            if component_type in self._output_model_map:
                component_output = await self.db_session.query(
                    self._output_model_map[component_type]
                ).get(staged_id)

            return {
                "metadata": base_output.metadata,
                "storage_path": base_output.storage_path,
                "pipeline_id": base_output.pipeline_id,
                "created_at": base_output.created_at.isoformat(),
                "component_output": component_output.__dict__ if component_output else None
            }

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Data retrieval failed: {str(e)}")
            return None

    # VERSION CONTROL AND RECOVERY

    async def create_output_version(
            self,
            staged_id: str,
            version_note: str,
            user_id: Optional[str] = None
    ) -> Optional[str]:
        """Create new version of staged output"""
        try:
            # Validate access
            if user_id and not await self.check_access_permission(
                    staged_id, user_id, 'write'
            ):
                return None

            output = await self.db_session.query(BaseStagedOutput).get(staged_id)
            if not output:
                return None

            # Create new version
            new_version = BaseStagedOutput(
                pipeline_id=output.pipeline_id,
                component_type=output.component_type,
                output_type=output.output_type,
                metadata={
                    **output.metadata,
                    'previous_version': staged_id,
                    'version_note': version_note,
                    'created_by': user_id
                }
            )
            self.db_session.add(new_version)

            # Track versioning in history
            history = StagingProcessingHistory(
                staged_output_id=staged_id,
                event_type="version_created",
                status=output.status,
                details={
                    "new_version_id": new_version.id,
                    "version_note": version_note,
                    "user_id": user_id
                }
            )
            self.db_session.add(history)

            await self.db_session.commit()
            return new_version.id

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Version creation failed: {str(e)}")
            return None

    async def recover_failed_output(
            self,
            staged_id: str,
            user_id: Optional[str] = None
    ) -> Optional[str]:
        """Recover failed staged output"""
        try:
            # Validate access
            if user_id and not await self.check_access_permission(
                    staged_id, user_id, 'write'
            ):
                return None

            output = await self.db_session.query(BaseStagedOutput).get(staged_id)
            if not output or output.status != ProcessingStatus.FAILED:
                return None

            # Create recovery point
            recovery_id = await self.create_output_version(
                staged_id,
                "Recovery point",
                user_id
            )

            if recovery_id:
                # Reset status for retry
                output.status = ProcessingStatus.PENDING
                output.updated_at = datetime.utcnow()

                # Track recovery attempt
                history = StagingProcessingHistory(
                    staged_output_id=staged_id,
                    event_type="recovery_attempted",
                    status=ProcessingStatus.PENDING,
                    details={
                        "recovery_point": recovery_id,
                        "user_id": user_id
                    }
                )
                self.db_session.add(history)

                await self.db_session.commit()

            return recovery_id

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Recovery failed: {str(e)}")
            return None

    # CLEANUP AND MAINTENANCE

    async def _periodic_cleanup(self):
        """Run periodic cleanup tasks"""
        while True:
            try:
                await self.cleanup_expired_data()
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                logger.error(f"Periodic cleanup failed: {str(e)}")
                await asyncio.sleep(300)  # Retry after 5 minutes

    async def cleanup_expired_data(self) -> None:
        """Clean up expired staged data"""
        try:
            # Find expired outputs
            expired_outputs = await self.db_session.query(BaseStagedOutput).filter(
                BaseStagedOutput.expires_at <= datetime.utcnow(),
                BaseStagedOutput.status != ProcessingStatus.ARCHIVED
            ).all()

            for output in expired_outputs:
                await self.archive_output(output.id)

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")

    # MONITORING AND METRICS

    async def get_storage_metrics(self) -> Dict[str, Any]:
        """Get comprehensive storage usage metrics"""
        try:
            # Get total size
            total_size = await self.db_session.query(
                func.sum(BaseStagedOutput.data_size)
            ).scalar()

            # Get status distribution
            status_counts = await self.db_session.query(
                BaseStagedOutput.status,
                func.count(BaseStagedOutput.id)
            ).group_by(BaseStagedOutput.status).all()

            # Get component distribution
            component_counts = await self.db_session.query(
                BaseStagedOutput.component_type,
                func.count(BaseStagedOutput.id)
            ).group_by(BaseStagedOutput.component_type).all()

            # Get pipeline metrics
            pipeline_metrics = await self.db_session.query(
                BaseStagedOutput.pipeline_id,
                func.count(BaseStagedOutput.id).label('output_count'),
                func.sum(BaseStagedOutput.data_size).label('total_size')
            ).group_by(BaseStagedOutput.pipeline_id).all()

            return {
                'total_size_bytes': total_size or 0,
                'status_distribution': dict(status_counts),
                'component_distribution': dict(component_counts),
                'pipeline_metrics': {
                    p[0]: {'count': p[1], 'size': p[2]}
                    for p in pipeline_metrics
                },
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get storage metrics: {str(e)}")
            return {}

    async def get_pipeline_staging_status(
            self,
            pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get staging status for all components in a pipeline"""
        try:
            # Get latest output for each component
            status_by_component = {}
            for comp_type in ComponentType:
                latest = await self.db_session.query(BaseStagedOutput).filter(
                    BaseStagedOutput.pipeline_id == pipeline_id,
                    BaseStagedOutput.component_type == comp_type
                ).order_by(BaseStagedOutput.created_at.desc()).first()

                if latest:
                    status_by_component[comp_type.value] = {
                        'status': latest.status.value,
                        'last_updated': latest.updated_at.isoformat(),
                        'output_id': latest.id,
                        'metadata': latest.metadata
                    }
                else:
                    status_by_component[comp_type.value] = {
                        'status': 'not_started',
                        'last_updated': None,
                        'output_id': None
                    }

            return status_by_component

        except Exception as e:
            logger.error(f"Failed to get pipeline staging status: {str(e)}")
            return None

    # ACCESS CONTROL

    async def check_access_permission(
            self,
            staged_id: str,
            user_id: str,
            action: str
    ) -> bool:
        """Check if user has permission to access staged data"""
        try:
            output = await self.db_session.query(BaseStagedOutput).get(staged_id)
            if not output:
                return False

            pipeline = await self.db_session.query(Pipeline).get(output.pipeline_id)
            if not pipeline:
                return False

            # Direct ownership
            if pipeline.owner_id == user_id:
                return True

            # Team access
            if pipeline.team_id:
                team_member = await self.db_session.query(TeamMember).filter(
                    TeamMember.team_id == pipeline.team_id,
                    TeamMember.user_id == user_id
                ).first()

                if team_member:
                    if action == 'read':
                        return True
                    if action == 'write' and team_member.role in ['admin', 'editor']:
                        return True

            # Service account access
            service_account = await self.db_session.query(ServiceAccount).filter(
                ServiceAccount.user_id == user_id,
                ServiceAccount.scope.contains([f"pipeline:{pipeline.id}:{action}"])
            ).first()

            if service_account:
                return True

            return False

        except Exception as e:
            logger.error(f"Permission check failed: {str(e)}")
            return False

    # MESSAGE HANDLING

    async def _handle_staging_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming staging-related messages"""
        try:
            message_type = message.get('message_type')
            content = message.get('content', {})

            if message_type == MessageType.STAGING_CLEANUP_START:
                await self.cleanup_expired_data()

            elif message_type == MessageType.COMPONENT_OUTPUT_READY:
                await self.store_component_output(
                    content['staged_id'],
                    content['component_type'],
                    content['output'],
                    content['output_type']
                )

            elif message_type == MessageType.DATA_ACCESS_REQUEST:
                data = await self.retrieve_data(
                    content['staged_id'],
                    content['component_type'],
                    content.get('user_id')
                )
                # Send response if required

            # Handle other message types...

        except Exception as e:
            logger.error(f"Message handling failed: {str(e)}")

    # UTILITY METHODS

    async def _notify_data_staged(
            self,
            staged_id: str,
            metadata: Dict[str, Any],
            pipeline_id: str,
            run_id: str
    ) -> None:
        """Notify about newly staged data"""
        try:
            message = {
                'message_type': MessageType.DATA_STORAGE,
                'content': {
                    'staged_id': staged_id,
                    'pipeline_id': pipeline_id,
                    'run_id': run_id,
                    'metadata': metadata
                },
                'source_identifier': self.module_identifier,
                'metadata': MessageMetadata(
                    source_component="staging_manager",
                    target_component="control_point_manager"
                )
            }

            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Notification failed: {str(e)}")