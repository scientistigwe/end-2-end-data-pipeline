# models/events.py
from sqlalchemy import event
from .audit_log import AuditLog
from .pipeline import Pipeline

def log_model_changes(mapper, connection, target):
    """Log model changes to audit log"""
    if hasattr(target, '__table__'):
        AuditLog.create(
            action='update',
            entity_type=target.__table__.name,
            entity_id=target.id,
            changes=target.get_changes()
        )

def setup_event_listeners():
    """Setup event listeners for all models"""
    for model in [Pipeline, DataSource, Report]:
        event.listen(model, 'after_update', log_model_changes)

def track_pipeline_state(session, instance, **kw):
    """Track pipeline state changes"""
    if isinstance(instance, Pipeline):
        if instance.status != getattr(instance, '_previous_status', None):
            session.add(PipelineStateChange(
                pipeline_id=instance.id,
                previous_status=instance._previous_status,
                new_status=instance.status
            ))

event.listen(Pipeline, 'before_update', track_pipeline_state)