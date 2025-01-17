# backend/db/types/associations.py
from sqlalchemy import Column, ForeignKey, Index, Table
from sqlalchemy.dialects.postgresql import UUID
from .base import base_meta

# Association table for dataset quality checks
dataset_quality_checks = Table(
    'dataset_quality_checks',
    base_meta,
    Column(
        'dataset_id', 
        UUID(as_uuid=True), 
        ForeignKey('datasets.id', ondelete='CASCADE', name='fk_dataset_quality_checks_dataset'),
        primary_key=True
    ),
    Column(
        'quality_check_id', 
        UUID(as_uuid=True), 
        ForeignKey('quality_checks.id', ondelete='CASCADE', name='fk_dataset_quality_checks_quality_check'),
        primary_key=True
    ),
    Index('ix_dataset_quality_checks_dataset', 'dataset_id'),
    Index('ix_dataset_quality_checks_quality_check', 'quality_check_id')
)

# Association table for dataset tags
dataset_tags = Table(
    'dataset_tags', 
    base_meta,
    Column(
        'dataset_id', 
        UUID(as_uuid=True), 
        ForeignKey('datasets.id', ondelete='CASCADE', name='fk_dataset_tags_dataset'),
        primary_key=True
    ),
    Column(
        'tag_id', 
        UUID(as_uuid=True), 
        ForeignKey('tags.id', ondelete='CASCADE', name='fk_dataset_tags_tag'),
        primary_key=True
    ),
    Index('ix_dataset_tags_dataset', 'dataset_id'),
    Index('ix_dataset_tags_tag', 'tag_id')
)

# Association table for pipeline tags
pipeline_tags = Table(
    'pipeline_tags', 
    base_meta,
    Column(
        'pipeline_id', 
        UUID(as_uuid=True), 
        ForeignKey('pipelines.id', ondelete='CASCADE', name='fk_pipeline_tags_pipeline'),
        primary_key=True
    ),
    Column(
        'tag_id', 
        UUID(as_uuid=True), 
        ForeignKey('tags.id', ondelete='CASCADE', name='fk_pipeline_tags_tag'),
        primary_key=True
    ),
    Index('ix_pipeline_tags_pipeline', 'pipeline_id'),
    Index('ix_pipeline_tags_tag', 'tag_id')
)

# Association table for datasource tags
datasource_tags = Table(
    'datasource_tags', 
    base_meta,
    Column(
        'datasource_id', 
        UUID(as_uuid=True), 
        ForeignKey('data_sources.id', ondelete='CASCADE', name='fk_datasource_tags_datasource'),
        primary_key=True
    ),
    Column(
        'tag_id', 
        UUID(as_uuid=True), 
        ForeignKey('tags.id', ondelete='CASCADE', name='fk_datasource_tags_tag'),
        primary_key=True
    ),
    Index('ix_datasource_tags_datasource', 'datasource_id'),
    Index('ix_datasource_tags_tag', 'tag_id')
)