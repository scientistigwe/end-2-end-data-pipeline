# models/validators.py
from pydantic import BaseModel, validator, constr
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

class PipelineCreate(BaseModel):
    name: constr(min_length=3, max_length=255)
    description: Optional[str]
    mode: str
    source_id: uuid.UUID
    target_id: Optional[uuid.UUID]
    config: Dict[str, Any]
    schedule_enabled: bool = False
    schedule_cron: Optional[str]
    schedule_timezone: Optional[str]

    @validator('mode')
    def validate_mode(cls, v):
        allowed_modes = {'development', 'staging', 'production'}
        if v not in allowed_modes:
            raise ValueError(f'Mode must be one of {allowed_modes}')
        return v

    @validator('schedule_cron')
    def validate_cron(cls, v, values):
        if values.get('schedule_enabled') and not v:
            raise ValueError('Cron expression required when schedule is enabled')
        return v

class PipelineUpdate(BaseModel):
    name: Optional[constr(min_length=3, max_length=255)]
    description: Optional[str]
    config: Optional[Dict[str, Any]]
    schedule_enabled: Optional[bool]
    schedule_cron: Optional[str]
    schedule_timezone: Optional[str]