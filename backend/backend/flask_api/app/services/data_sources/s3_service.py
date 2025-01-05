# backend/flask_api/app/services/data_sources/s3_service.py

import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from .base_service import BaseSourceService
from .....database.models.data_source import DataSource, S3SourceConfig

class S3SourceService(BaseSourceService):
    source_type = 's3'

    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self._client_registry: Dict[UUID, Any] = {}
        self._resource_registry: Dict[UUID, Any] = {}

    def connect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create and validate S3 connection."""
        try:
            # Validate configuration
            validation_result = self.validate_config(data)
            if validation_result.status == 'failed':
                raise ValueError(f"Invalid S3 configuration: {validation_result.details}")

            # Test connection before creating records
            session = self._create_session(data)
            s3_client = session.client('s3')
            s3_client.head_bucket(Bucket=data['bucket'])

            # Create source record
            source = DataSource(
                name=data['name'],
                type=self.source_type,
                status='pending',
                config={
                    'bucket': data['bucket'],
                    'region': data['region'],
                    'prefix': data.get('prefix', '')
                }
            )

            # Create S3 config
            s3_config = S3SourceConfig(
                source=source,
                bucket=data['bucket'],
                region=data['region'],
                prefix=data.get('prefix', ''),
                storage_class=data.get('storage_class', 'STANDARD'),
                versioning_enabled=data.get('versioning_enabled', False),
                transfer_config=data.get('transfer_config', {
                    'multipart_threshold': 8 * 1024 * 1024,
                    'multipart_chunksize': 8 * 1024 * 1024,
                    'max_concurrency': 10
                })
            )

            source.status = 'active'
            self.db_session.add(source)
            self.db_session.add(s3_config)
            self.db_session.commit()

            # Store clients in registry
            self._client_registry[source.id] = s3_client
            self._resource_registry[source.id] = session.resource('s3')

            return self._format_source(source)
        except ClientError as e:
            self.logger.error(f"S3 connection error: {str(e)}")
            self.db_session.rollback()
            raise ValueError(f"S3 connection failed: {e.response['Error']['Message']}")
        except Exception as e:
            self.logger.error(f"S3 connection error: {str(e)}")
            self.db_session.rollback()
            raise

    def list_objects(self, source_id: UUID, prefix: Optional[str] = None, max_keys: int = 1000) -> Dict[str, Any]:
        """List objects in S3 bucket with pagination."""
        try:
            source = self._get_source_or_error(source_id)
            s3_client = self._get_client(source)

            list_params = {
                'Bucket': source.config['bucket'],
                'MaxKeys': max_keys
            }

            if prefix:
                list_params['Prefix'] = prefix
            elif source.config.get('prefix'):
                list_params['Prefix'] = source.config['prefix']

            response = s3_client.list_objects_v2(**list_params)

            objects = []
            for obj in response.get('Contents', []):
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'storage_class': obj['StorageClass'],
                    'etag': obj['ETag']
                })

            return {
                'objects': objects,
                'prefix': list_params.get('Prefix', ''),
                'is_truncated': response.get('IsTruncated', False),
                'next_continuation_token': response.get('NextContinuationToken'),
                'total_objects': len(objects)
            }
        except ClientError as e:
            self.logger.error(f"S3 list error: {str(e)}")
            raise ValueError(f"Failed to list objects: {e.response['Error']['Message']}")

    def list_sources(self) -> List[DataSource]:
        """
        List all S3 data sources.
        
        Returns:
            List[DataSource]: List of all S3 data sources
        """
        try:
            return (self.db_session.query(DataSource)
                    .filter(DataSource.type == self.source_type)
                    .all())
        except Exception as exc:
            self.logger.error(f"Error listing S3 sources: {str(exc)}")
            raise
        
    def get_object_info(self, source_id: UUID, key: str) -> Dict[str, Any]:
        """Get detailed information about an S3 object."""
        try:
            source = self._get_source_or_error(source_id)
            s3_client = self._get_client(source)

            response = s3_client.head_object(
                Bucket=source.config['bucket'],
                Key=key
            )

            return {
                'key': key,
                'size': response['ContentLength'],
                'last_modified': response['LastModified'].isoformat(),
                'etag': response['ETag'],
                'storage_class': response['StorageClass'],
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {}),
                'version_id': response.get('VersionId'),
                'server_side_encryption': response.get('ServerSideEncryption')
            }
        except ClientError as e:
            self.logger.error(f"S3 info error: {str(e)}")
            raise ValueError(f"Failed to get object info: {e.response['Error']['Message']}")

    def initiate_download(self, source_id: UUID, key: str) -> Dict[str, Any]:
        """Generate pre-signed URL for object download."""
        try:
            source = self._get_source_or_error(source_id)
            s3_client = self._get_client(source)

            url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': source.config['bucket'],
                    'Key': key
                },
                ExpiresIn=3600  # URL expires in 1 hour
            )

            return {
                'download_url': url,
                'expires_in': 3600
            }
        except ClientError as e:
            self.logger.error(f"S3 download error: {str(e)}")
            raise ValueError(f"S3 download error: {str(e)}")
        
    def _validate_source_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate S3 source configuration."""
        errors = []
        required_fields = ['access_key', 'secret_key', 'region', 'bucket']
        
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        if 'region' in config:
            try:
                session = boto3.Session()
                valid_regions = session.get_available_regions('s3')
                if config['region'] not in valid_regions:
                    errors.append(f"Invalid region. Must be one of: {', '.join(valid_regions)}")
            except Exception as e:
                errors.append(f"Error validating region: {str(e)}")

        if 'storage_class' in config:
            valid_storage_classes = [
                'STANDARD', 'REDUCED_REDUNDANCY', 'STANDARD_IA',
                'ONEZONE_IA', 'INTELLIGENT_TIERING', 'GLACIER',
                'DEEP_ARCHIVE'
            ]
            if config['storage_class'] not in valid_storage_classes:
                errors.append(f"Invalid storage class. Must be one of: {', '.join(valid_storage_classes)}")

        return errors

    def _test_source_connection(self, source: DataSource) -> Dict[str, Any]:
        """Test S3 connection and return bucket metrics."""
        s3_client = self._get_client(source)
        s3_resource = self._get_resource(source)
        bucket = source.config['bucket']
        
        try:
            # Get bucket location
            location = s3_client.get_bucket_location(Bucket=bucket)['LocationConstraint']
            
            # Get bucket versioning status
            versioning = s3_client.get_bucket_versioning(Bucket=bucket)
            
            # Get bucket metrics
            bucket_obj = s3_resource.Bucket(bucket)
            total_objects = sum(1 for _ in bucket_obj.objects.all())
            total_size = sum(obj.size for obj in bucket_obj.objects.all())
            
            return {
                "bucket": bucket,
                "location": location,
                "versioning_enabled": versioning.get('Status') == 'Enabled',
                "total_objects": total_objects,
                "total_size_bytes": total_size
            }
        except ClientError as e:
            raise ValueError(f"Failed to test connection: {e.response['Error']['Message']}")

    def _sync_source_data(self, source: DataSource) -> Dict[str, Any]:
        """Sync S3 bucket metadata and statistics."""
        s3_client = self._get_client(source)
        bucket = source.config['bucket']
        prefix = source.config.get('prefix', '')
        
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            total_objects = 0
            total_bytes = 0
            
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                for obj in page.get('Contents', []):
                    total_objects += 1
                    total_bytes += obj['Size']
            
            return {
                "records_processed": total_objects,
                "bytes_processed": total_bytes
            }
        except ClientError as e:
            raise ValueError(f"Failed to sync data: {e.response['Error']['Message']}")

    def _get_source_preview(self, source: DataSource, limit: int) -> List[Dict[str, Any]]:
        """Get preview of S3 objects."""
        s3_client = self._get_client(source)
        bucket = source.config['bucket']
        prefix = source.config.get('prefix', '')
        
        try:
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=limit
            )
            
            preview_data = []
            for obj in response.get('Contents', [])[:limit]:
                # Get object metadata
                head = s3_client.head_object(Bucket=bucket, Key=obj['Key'])
                
                preview_data.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "content_type": head.get('ContentType'),
                    "metadata": head.get('Metadata', {}),
                    "storage_class": obj['StorageClass']
                })
            
            return preview_data
        except ClientError as e:
            raise ValueError(f"Failed to get preview: {e.response['Error']['Message']}")

    def _disconnect_source(self, source: DataSource) -> None:
        """Clean up S3 connection resources."""
        if source.id in self._client_registry:
            del self._client_registry[source.id]
        if source.id in self._resource_registry:
            del self._resource_registry[source.id]

    def _create_session(self, config: Dict[str, Any]) -> boto3.Session:
        """Create boto3 session with credentials."""
        return boto3.Session(
            aws_access_key_id=config['access_key'],
            aws_secret_access_key=config['secret_key'],
            region_name=config['region']
        )

    def _get_client(self, source: DataSource) -> Any:
        """Get or create S3 client for source."""
        if source.id not in self._client_registry:
            session = self._create_session({
                'access_key': source.config['access_key'],
                'secret_key': source.config['secret_key'],
                'region': source.config['region']
            })
            self._client_registry[source.id] = session.client('s3')
        
        return self._client_registry[source.id]

    def _get_resource(self, source: DataSource) -> Any:
        """Get or create S3 resource for source."""
        if source.id not in self._resource_registry:
            session = self._create_session({
                'access_key': source.config['access_key'],
                'secret_key': source.config['secret_key'],
                'region': source.config['region']
            })
            self._resource_registry[source.id] = session.resource('s3')
        
        return self._resource_registry[source.id]                             