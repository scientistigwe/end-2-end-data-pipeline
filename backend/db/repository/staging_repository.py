from sqlalchemy.orm import Session, joinedload
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID
from sqlalchemy import and_, or_, desc, func

from backend.db.models.staging_model import (
    StagedResource,
    StagingDecision,
    StagingModification,
    StagingEvent
)


class StagingRepository:
    """Repository for staging-related db operations"""

    def __init__(self, db_session: Session):
        """Initialize repository with db session"""
        self.db_session = db_session

    def create_staged_resource(self, data: Dict[str, Any]) -> StagedResource:
        """Create new staged resource"""
        try:
            resource = StagedResource(
                pipeline_id=data['pipeline_id'],
                stage_key=data['stage_key'],
                name=data.get('name'),
                resource_type=data['resource_type'],
                format=data.get('format'),
                storage_location=data['storage_location'],
                size_bytes=data.get('size_bytes'),
                checksum=data.get('checksum'),
                requires_approval=data.get('requires_approval', True),
                control_point_id=data.get('control_point_id'),
                owner_id=data.get('owner_id'),
                metadata=data.get('metadata', {}),
                tags=data.get('tags', []),
                expires_at=data.get('expires_at')
            )
            self.db_session.add(resource)
            self.db_session.commit()
            return resource

        except Exception as e:
            self.db_session.rollback()
            raise

    def update_resource_status(
            self,
            resource_id: UUID,
            status: str,
            metadata_updates: Optional[Dict[str, Any]] = None
    ) -> Optional[StagedResource]:
        """Update status of staged resource"""
        try:
            resource = self.db_session.query(StagedResource).get(resource_id)
            if resource:
                resource.status = status
                resource.updated_at = datetime.utcnow()
                if metadata_updates:
                    resource.metadata.update(metadata_updates)
                self.db_session.commit()
                return resource
            return None

        except Exception as e:
            self.db_session.rollback()
            raise

    def record_decision(
            self,
            resource_id: UUID,
            decision_data: Dict[str, Any]
    ) -> StagingDecision:
        """Record decision for staged resource"""
        try:
            decision = StagingDecision(
                resource_id=resource_id,
                decision_type=decision_data['decision_type'],
                decision_maker=decision_data['decision_maker'],
                reason=decision_data.get('reason'),
                notes=decision_data.get('notes'),
                metadata=decision_data.get('metadata', {}),
                control_point_ref=decision_data.get('control_point_ref')
            )
            self.db_session.add(decision)
            self.db_session.commit()
            return decision

        except Exception as e:
            self.db_session.rollback()
            raise

    def create_modification(
            self,
            resource_id: UUID,
            modification_data: Dict[str, Any]
    ) -> StagingModification:
        """Create modification record for staged resource"""
        try:
            modification = StagingModification(
                resource_id=resource_id,
                modification_type=modification_data['modification_type'],
                changes=modification_data['changes'],
                original_values=modification_data.get('original_values'),
                modified_by=modification_data['modified_by'],
                approved_by=modification_data.get('approved_by'),
                metadata=modification_data.get('metadata', {})
            )
            self.db_session.add(modification)
            self.db_session.commit()
            return modification

        except Exception as e:
            self.db_session.rollback()
            raise

    def record_event(
            self,
            resource_id: UUID,
            event_data: Dict[str, Any]
    ) -> StagingEvent:
        """Record staging event"""
        try:
            event = StagingEvent(
                resource_id=resource_id,
                event_type=event_data['event_type'],
                actor_id=event_data.get('actor_id'),
                details=event_data.get('details', {}),
                metadata=event_data.get('metadata', {}),
                pipeline_id=event_data.get('pipeline_id'),
                stage=event_data.get('stage')
            )
            self.db_session.add(event)
            self.db_session.commit()
            return event

        except Exception as e:
            self.db_session.rollback()
            raise

    def get_resource(self, resource_id: UUID) -> Optional[StagedResource]:
        """Get staged resource by ID with related data"""
        return self.db_session.query(StagedResource) \
            .options(
            joinedload(StagedResource.decisions),
            joinedload(StagedResource.modifications)
        ) \
            .get(resource_id)

    def list_resources(
            self,
            filters: Dict[str, Any],
            page: int = 1,
            page_size: int = 50
    ) -> Tuple[List[StagedResource], int]:
        """List staged resources with filtering and pagination"""
        try:
            query = self.db_session.query(StagedResource)

            # Apply filters
            if filters.get('pipeline_id'):
                query = query.filter(StagedResource.pipeline_id == filters['pipeline_id'])
            if filters.get('status'):
                query = query.filter(StagedResource.status == filters['status'])
            if filters.get('resource_type'):
                query = query.filter(StagedResource.resource_type == filters['resource_type'])
            if filters.get('owner_id'):
                query = query.filter(StagedResource.owner_id == filters['owner_id'])
            if filters.get('requires_approval'):
                query = query.filter(StagedResource.requires_approval == filters['requires_approval'])

            # Get total count
            total = query.count()

            # Apply pagination
            resources = query.order_by(desc(StagedResource.created_at)) \
                .offset((page - 1) * page_size) \
                .limit(page_size) \
                .all()

            return resources, total

        except Exception as e:
            raise

    def get_pipeline_resources(
            self,
            pipeline_id: UUID,
            status: Optional[str] = None
    ) -> List[StagedResource]:
        """Get all resources for a pipeline"""
        query = self.db_session.query(StagedResource) \
            .filter(StagedResource.pipeline_id == pipeline_id)

        if status:
            query = query.filter(StagedResource.status == status)

        return query.order_by(StagedResource.created_at).all()

    def get_resource_modifications(
            self,
            resource_id: UUID
    ) -> List[StagingModification]:
        """Get all modifications for a resource"""
        return self.db_session.query(StagingModification) \
            .filter(StagingModification.resource_id == resource_id) \
            .order_by(StagingModification.executed_at) \
            .all()

    def get_resource_decisions(
            self,
            resource_id: UUID
    ) -> List[StagingDecision]:
        """Get all decisions for a resource"""
        return self.db_session.query(StagingDecision) \
            .filter(StagingDecision.resource_id == resource_id) \
            .order_by(desc(StagingDecision.decision_time)) \
            .all()

        def get_resource_events(
                self,
                resource_id: UUID,
                event_type: Optional[str] = None
        ) -> List[StagingEvent]:
            """Get events for a resource"""
            query = self.db_session.query(StagingEvent) \
                .filter(StagingEvent.resource_id == resource_id)

            if event_type:
                query = query.filter(StagingEvent.event_type == event_type)

            return query.order_by(StagingEvent.event_time).all()

        def cleanup_expired_resources(self) -> List[UUID]:
            """Clean up expired resources"""
            try:
                current_time = datetime.utcnow()
                expired_resources = self.db_session.query(StagedResource) \
                    .filter(
                    StagedResource.expires_at <= current_time,
                    StagedResource.status.in_(['pending', 'awaiting_decision'])
                ) \
                    .all()

                expired_ids = []
                for resource in expired_resources:
                    resource.status = 'expired'
                    expired_ids.append(resource.resource_id)

                    # Record expiration event
                    self.record_event(
                        resource.resource_id,
                        {
                            'event_type': 'resource_expired',
                            'details': {
                                'expiry_time': resource.expires_at.isoformat(),
                                'previous_status': resource.status
                            }
                        }
                    )

                self.db_session.commit()
                return expired_ids

            except Exception as e:
                self.db_session.rollback()
                raise

        def get_pending_approvals(
                self,
                pipeline_id: Optional[UUID] = None
        ) -> List[StagedResource]:
            """Get resources awaiting approval"""
            query = self.db_session.query(StagedResource) \
                .filter(
                StagedResource.status == 'awaiting_decision',
                StagedResource.requires_approval == True
            )

            if pipeline_id:
                query = query.filter(StagedResource.pipeline_id == pipeline_id)

            return query.order_by(StagedResource.created_at).all()

        def update_control_point(
                self,
                resource_id: UUID,
                control_point_id: UUID
        ) -> Optional[StagedResource]:
            """Update control point reference"""
            try:
                resource = self.db_session.query(StagedResource).get(resource_id)
                if resource:
                    resource.control_point_id = control_point_id
                    self.db_session.commit()
                    return resource
                return None

            except Exception as e:
                self.db_session.rollback()
                raise

        def mark_resource_accessed(self, resource_id: UUID) -> None:
            """Update last accessed timestamp"""
            try:
                resource = self.db_session.query(StagedResource).get(resource_id)
                if resource:
                    resource.last_accessed = datetime.utcnow()
                    self.db_session.commit()

            except Exception as e:
                self.db_session.rollback()
                raise

        def get_resource_by_key(
                self,
                pipeline_id: UUID,
                stage_key: str
        ) -> Optional[StagedResource]:
            """Get resource by pipeline ID and stage key"""
            return self.db_session.query(StagedResource) \
                .filter(
                StagedResource.pipeline_id == pipeline_id,
                StagedResource.stage_key == stage_key
            ) \
                .first()

        def update_modification_status(
                self,
                modification_id: UUID,
                status: str,
                error: Optional[str] = None
        ) -> Optional[StagingModification]:
            """Update modification execution status"""
            try:
                modification = self.db_session.query(StagingModification).get(modification_id)
                if modification:
                    modification.status = status
                    modification.executed_at = datetime.utcnow()
                    if error:
                        modification.error = error
                    self.db_session.commit()
                    return modification
                return None

            except Exception as e:
                self.db_session.rollback()
                raise

        def get_pipeline_statistics(self, pipeline_id: UUID) -> Dict[str, Any]:
            """Get statistics for pipeline staging"""
            try:
                stats = {}

                # Resource counts by status
                status_counts = self.db_session.query(
                    StagedResource.status,
                    func.count(StagedResource.resource_id)
                ) \
                    .filter(StagedResource.pipeline_id == pipeline_id) \
                    .group_by(StagedResource.status) \
                    .all()

                stats['status_counts'] = {
                    status: count for status, count in status_counts
                }

                # Decision statistics
                decision_counts = self.db_session.query(
                    StagingDecision.decision_type,
                    func.count(StagingDecision.decision_id)
                ) \
                    .join(StagedResource) \
                    .filter(StagedResource.pipeline_id == pipeline_id) \
                    .group_by(StagingDecision.decision_type) \
                    .all()

                stats['decision_counts'] = {
                    decision_type: count for decision_type, count in decision_counts
                }

                # Modification statistics
                modification_counts = self.db_session.query(
                    StagingModification.status,
                    func.count(StagingModification.modification_id)
                ) \
                    .join(StagedResource) \
                    .filter(StagedResource.pipeline_id == pipeline_id) \
                    .group_by(StagingModification.status) \
                    .all()

                stats['modification_counts'] = {
                    status: count for status, count in modification_counts
                }

                return stats

            except Exception as e:
                raise