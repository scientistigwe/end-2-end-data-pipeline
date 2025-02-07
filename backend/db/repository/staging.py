from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import and_, or_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.staging.base import BaseStagedOutput
from ..models.staging.analytics import (
    StagedAnalyticsOutput,
    StagedInsightOutput,
    StagedDecisionOutput
)
from ..models.staging.processing import (
    StagedMonitoringOutput,
    StagedQualityOutput,
    StagedRecommendationOutput
)
from ..models.staging.reporting import (
    StagedReportOutput,
    StagedMetricsOutput,
    StagedComplianceReport
)

import logging

logger = logging.getLogger(__name__)


class StagingRepository(BaseRepository[BaseStagedOutput]):
    """
    Repository for managing staged outputs and processing across different 
    components with comprehensive tracking and validation.
    """

    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session)

    async def create_staged_output(
        self,
        output_data: Dict[str, Any],
        output_type: str,
        pipeline_id: UUID,
        user_id: Optional[UUID] = None
    ) -> BaseStagedOutput:
        """
        Create a new staged output with proper type handling and validation.

        Args:
            output_data: Output data
            output_type: Type of output
            pipeline_id: Associated pipeline ID
            user_id: Optional user ID for tracking

        Returns:
            Created staged output instance
        """
        try:
            # Select appropriate model class based on type
            model_mapping = {
                'analytics': StagedAnalyticsOutput,
                'insight': StagedInsightOutput,
                'decision': StagedDecisionOutput,
                'monitoring': StagedMonitoringOutput,
                'quality': StagedQualityOutput,
                'recommendation': StagedRecommendationOutput,
                'report': StagedReportOutput,
                'metrics': StagedMetricsOutput,
                'compliance': StagedComplianceReport
            }

            model_class = model_mapping.get(output_type)
            if not model_class:
                raise ValueError(f"Invalid output type: {output_type}")

            # Prepare output data
            output_data.update({
                'pipeline_id': pipeline_id,
                'created_by': user_id,
                'status': 'pending',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })

            # Create the output instance
            output = await self.create(output_data, model_class)
            logger.info(f"Created new staged output of type {output_type}")
            return output

        except Exception as e:
            logger.error(f"Failed to create staged output: {str(e)}")
            raise

    async def get_pipeline_outputs(
        self,
        pipeline_id: UUID,
        output_type: Optional[str] = None,
        status: Optional[str] = None,
        time_range: Optional[timedelta] = None
    ) -> List[BaseStagedOutput]:
        """
        Get staged outputs for a pipeline with filtering.

        Args:
            pipeline_id: Pipeline ID
            output_type: Optional output type filter
            status: Optional status filter
            time_range: Optional time range filter

        Returns:
            List of matching staged outputs
        """
        try:
            query = select(BaseStagedOutput).where(
                BaseStagedOutput.pipeline_id == pipeline_id
            )

            if output_type:
                query = query.where(BaseStagedOutput.component_type == output_type)
            if status:
                query = query.where(BaseStagedOutput.status == status)
            if time_range:
                start_time = datetime.utcnow() - time_range
                query = query.where(BaseStagedOutput.created_at >= start_time)

            query = query.order_by(desc(BaseStagedOutput.created_at))
            result = await self.db_session.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error retrieving pipeline outputs: {str(e)}")
            raise

    async def update_output_status(
        self,
        output_id: UUID,
        status: str,
        metrics: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update staged output status with metrics and error tracking.

        Args:
            output_id: Output ID
            status: New status
            metrics: Optional performance metrics
            error: Optional error message
        """
        try:
            output = await self.get_by_id(output_id, BaseStagedOutput)
            if not output:
                raise ValueError(f"Staged output not found: {output_id}")

            output.status = status
            output.updated_at = datetime.utcnow()

            if status == 'completed':
                output.completed_at = datetime.utcnow()
                if output.started_at:
                    output.processing_time = (
                        output.completed_at - output.started_at
                    ).total_seconds()

            if metrics:
                output.metrics = metrics

            if error:
                output.error = error
                output.error_count += 1

            await self.db_session.commit()
            logger.info(f"Updated staged output {output_id} status to {status}")

        except Exception as e:
            logger.error(f"Failed to update output status: {str(e)}")
            raise

    async def get_output_metrics(
        self,
        pipeline_id: UUID,
        output_type: Optional[str] = None,
        time_range: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive metrics for staged outputs.

        Args:
            pipeline_id: Pipeline ID
            output_type: Optional output type filter
            time_range: Optional time range

        Returns:
            Dictionary of metrics
        """
        try:
            query = select(BaseStagedOutput).where(
                BaseStagedOutput.pipeline_id == pipeline_id
            )

            if output_type:
                query = query.where(BaseStagedOutput.component_type == output_type)
            if time_range:
                start_time = datetime.utcnow() - time_range
                query = query.where(BaseStagedOutput.created_at >= start_time)

                # Execute query
                result = await self.db_session.execute(query)
                outputs = result.scalars().all()

                # Calculate metrics
                total_count = len(outputs)
                status_counts = {}
                total_processing_time = 0
                error_count = 0

                for output in outputs:
                    # Status counts
                    status_counts[output.status] = status_counts.get(output.status, 0) + 1

                    # Processing time
                    if output.processing_time:
                        total_processing_time += output.processing_time

                    # Error tracking
                    if output.error_count:
                        error_count += output.error_count

                return {
                    'total_outputs': total_count,
                    'status_distribution': status_counts,
                    'average_processing_time': (
                        total_processing_time / total_count if total_count > 0 else 0
                    ),
                    'error_rate': (
                        error_count / total_count if total_count > 0 else 0
                    ),
                    'time_period': {
                        'start': start_time.isoformat() if time_range else None,
                        'end': datetime.utcnow().isoformat()
                    }
                }
        except Exception as e:
            logger.error(f"Error getting output metrics: {str(e)}")
            raise

    async def cleanup_expired_outputs(self) -> List[UUID]:
        """
        Clean up expired staged outputs.

        Returns:
            List of expired output IDs
        """
        try:
            current_time = datetime.utcnow()
            query = select(BaseStagedOutput).where(
                and_(
                    BaseStagedOutput.expires_at <= current_time,
                    BaseStagedOutput.status.in_(['pending', 'in_progress'])
                )
            )

            result = await self.db_session.execute(query)
            expired_outputs = result.scalars().all()

            expired_ids = []
            for output in expired_outputs:
                output.status = 'expired'
                output.updated_at = current_time
                expired_ids.append(output.id)

            if expired_ids:
                await self.db_session.commit()
                logger.info(f"Cleaned up {len(expired_ids)} expired outputs")

            return expired_ids

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to cleanup expired outputs: {str(e)}")
            raise


    async def get_component_outputs(
            self,
            pipeline_id: UUID,
            component_type: str,
            include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get outputs for a specific component with optional metadata.

        Args:
            pipeline_id: Pipeline ID
            component_type: Component type to filter
            include_metadata: Whether to include metadata

        Returns:
            List of outputs with their details
        """
        try:
            query = select(BaseStagedOutput).where(
                and_(
                    BaseStagedOutput.pipeline_id == pipeline_id,
                    BaseStagedOutput.component_type == component_type
                )
            )

            if include_metadata:
                query = query.options(selectinload(BaseStagedOutput.metadata))

            result = await self.db_session.execute(query)
            outputs = result.scalars().all()

            return [
                {
                    'id': str(output.id),
                    'status': output.status,
                    'created_at': output.created_at.isoformat(),
                    'processing_time': output.processing_time,
                    'error': output.error,
                    'metrics': output.metrics,
                    'metadata': output.metadata if include_metadata else None
                }
                for output in outputs
            ]

        except Exception as e:
            logger.error(f"Error getting component outputs: {str(e)}")
            raise


    async def get_processing_history(
            self,
            output_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Get processing history for a staged output.

        Args:
            output_id: Output ID

        Returns:
            List of processing history entries
        """
        try:
            output = await self.get_by_id(output_id, BaseStagedOutput)
            if not output:
                raise ValueError(f"Staged output not found: {output_id}")

            history = []

            # Status changes
            history.append({
                'event_type': 'created',
                'timestamp': output.created_at.isoformat(),
                'details': {'initial_status': output.status}
            })

            if output.started_at:
                history.append({
                    'event_type': 'processing_started',
                    'timestamp': output.started_at.isoformat(),
                    'details': {'processing_attempt': 1}
                })

            if output.completed_at:
                history.append({
                    'event_type': 'processing_completed',
                    'timestamp': output.completed_at.isoformat(),
                    'details': {
                        'processing_time': output.processing_time,
                        'final_status': output.status
                    }
                })

            # Error events
            if output.error_count > 0:
                history.append({
                    'event_type': 'errors_occurred',
                    'timestamp': output.updated_at.isoformat(),
                    'details': {
                        'error_count': output.error_count,
                        'last_error': output.error
                    }
                })

            return sorted(
                history,
                key=lambda x: datetime.fromisoformat(x['timestamp'])
            )

        except Exception as e:
            logger.error(f"Error getting processing history: {str(e)}")
            raise


    async def retry_failed_outputs(
            self,
            pipeline_id: UUID,
            max_retries: int = 3
    ) -> List[UUID]:
        """
        Retry failed outputs within retry limit.

        Args:
            pipeline_id: Pipeline ID
            max_retries: Maximum retry attempts

        Returns:
            List of retried output IDs
        """
        try:
            query = select(BaseStagedOutput).where(
                and_(
                    BaseStagedOutput.pipeline_id == pipeline_id,
                    BaseStagedOutput.status == 'failed',
                    BaseStagedOutput.retry_count < max_retries
                )
            )

            result = await self.db_session.execute(query)
            failed_outputs = result.scalars().all()

            retried_ids = []
            for output in failed_outputs:
                output.status = 'pending'
                output.retry_count += 1
                output.updated_at = datetime.utcnow()
                output.error = None
                retried_ids.append(output.id)

            if retried_ids:
                await self.db_session.commit()
                logger.info(f"Retried {len(retried_ids)} failed outputs")

            return retried_ids

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to retry outputs: {str(e)}")
            raise


    async def validate_output(
            self,
            output_id: UUID,
            validation_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a staged output against rules.

        Args:
            output_id: Output ID
            validation_rules: Validation rules to apply

        Returns:
            Validation results
        """
        try:
            output = await self.get_by_id(output_id, BaseStagedOutput)
            if not output:
                raise ValueError(f"Staged output not found: {output_id}")

            # Perform validation
            validation_results = {
                'passed': True,
                'checks': [],
                'timestamp': datetime.utcnow().isoformat()
            }

            for rule in validation_rules.get('rules', []):
                check_result = {
                    'rule': rule['name'],
                    'passed': True,
                    'details': {}
                }

                # Implement rule checking logic here
                # This is a placeholder for actual validation logic
                check_result['passed'] = True

                validation_results['checks'].append(check_result)
                validation_results['passed'] &= check_result['passed']

            # Update output with validation results
            output.metadata = output.metadata or {}
            output.metadata['validation_results'] = validation_results
            output.updated_at = datetime.utcnow()

            await self.db_session.commit()
            return validation_results

        except Exception as e:
            logger.error(f"Error validating output: {str(e)}")
            raise