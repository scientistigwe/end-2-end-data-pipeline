# models/pipeline.py
from sqlalchemy import Column, String, DateTime, JSON, Enum, ForeignKey, Integer, Float, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel
import uuid
# models/pipeline.py
from sqlalchemy import Index, UniqueConstraint, event, DDL
from sqlalchemy.orm import validates
from .base import BaseModel

class Pipeline(BaseModel):
    __tablename__ = 'pipelines'

    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum('idle', 'running', 'paused', 'completed', 'failed', 'cancelled', name='pipeline_status'))
    mode = Column(Enum('development', 'staging', 'production', name='pipeline_mode'))
    source_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'))
    target_id = Column(UUID(as_uuid=True), ForeignKey('data_sources.id'), nullable=True)
    config = Column(JSONB)
    progress = Column(Float, default=0)
    error = Column(Text)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    version = Column(Integer, default=1)
    
    # Stats
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    average_duration = Column(Float)
    
    # Schedule
    schedule_enabled = Column(Boolean, default=False)
    schedule_cron = Column(String(100))
    schedule_timezone = Column(String(50))
    
    # Relationships
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    owner = relationship('User', back_populates='pipelines')
    steps = relationship('PipelineStep', back_populates='pipeline', cascade='all, delete-orphan')
    runs = relationship('PipelineRun', back_populates='pipeline')
    quality_gates = relationship('QualityGate', back_populates='pipeline')

    # Indexes
    __table_args__ = (
        Index('idx_pipeline_status_created', 'status', 'created_at'),
        Index('idx_pipeline_owner_status', 'owner_id', 'status'),
        UniqueConstraint('name', 'owner_id', name='uq_pipeline_name_owner'),
        {'extend_existing': True}
    )

    # Validators
    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) < 3:
            raise ValueError("Pipeline name must be at least 3 characters long")
        return name.strip()

    @validates('progress')
    def validate_progress(self, key, value):
        if not 0 <= value <= 100:
            raise ValueError("Progress must be between 0 and 100")
        return value

    # Properties
    @hybrid_property
    def is_active(self):
        return self.status in ('running', 'paused')

    @hybrid_property
    def duration(self):
        if self.last_run and self.next_run:
            return (self.next_run - self.last_run).total_seconds()
        return None

    # Methods
    def can_start(self):
        return self.status in ('idle', 'failed', 'completed')

    def can_stop(self):
        return self.status in ('running', 'paused')

class PipelineStep(BaseModel):
    __tablename__ = 'pipeline_steps'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id'), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    config = Column(JSONB)
    status = Column(Enum('pending', 'running', 'completed', 'failed', name='step_status'))
    order = Column(Integer)
    enabled = Column(Boolean, default=True)
    timeout = Column(Integer)  # in seconds
    retry_attempts = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    dependencies = Column(JSONB)  # Array of step IDs
    
    pipeline = relationship('Pipeline', back_populates='steps')

class PipelineRun(BaseModel):
    __tablename__ = 'pipeline_runs'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id'), nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(Enum('running', 'completed', 'failed', 'cancelled', name='run_status'))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration = Column(Float)  # in seconds
    error = Column(JSONB)  # {message: string, step?: string, details?: any}
    metrics = Column(JSONB)  # Performance metrics
    
    pipeline = relationship('Pipeline', back_populates='runs')
    step_runs = relationship('PipelineStepRun', back_populates='pipeline_run')

class PipelineStepRun(BaseModel):
    __tablename__ = 'pipeline_step_runs'

    pipeline_run_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_runs.id'), nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey('pipeline_steps.id'), nullable=False)
    status = Column(Enum('pending', 'running', 'completed', 'failed', name='step_run_status'))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration = Column(Float)  # in seconds
    error = Column(JSONB)
    output = Column(JSONB)
    metrics = Column(JSONB)
    
    pipeline_run = relationship('PipelineRun', back_populates='step_runs')
    step = relationship('PipelineStep')

class QualityGate(BaseModel):
    __tablename__ = 'quality_gates'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id'), nullable=False)
    name = Column(String(255), nullable=False)
    rules = Column(JSONB)
    threshold = Column(Float)
    is_active = Column(Boolean, default=True)
    
    pipeline = relationship('Pipeline', back_populates='quality_gates')


# Triggers
def create_pipeline_triggers():
    return [
        DDL(
            """
            CREATE TRIGGER update_pipeline_stats_trigger
            AFTER INSERT OR UPDATE ON pipeline_runs
            FOR EACH ROW
            EXECUTE FUNCTION update_pipeline_stats();
            """
        ),
        DDL(
            """
            CREATE OR REPLACE FUNCTION update_pipeline_stats()
            RETURNS TRIGGER AS $$
            BEGIN
                UPDATE pipelines
                SET total_runs = total_runs + 1,
                    successful_runs = CASE 
                        WHEN NEW.status = 'completed' 
                        THEN successful_runs + 1 
                        ELSE successful_runs 
                    END,
                    last_run = NEW.start_time
                WHERE id = NEW.pipeline_id;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
    ]

event.listen(
    Pipeline.__table__,
    'after_create',
    create_pipeline_triggers()[0].execute_if(dialect='postgresql')
)