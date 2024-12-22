# backend/flask_api/app/services/data_sources/s3_service.py

import boto3
from typing import Dict, Any, List
from .....database.models.data_source import DataSource, S3SourceConfig
from .base_service import BaseSourceService


class S3SourceService(BaseSourceService):
    source_type = 's3'

    def connect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create S3 connection and source."""
        try:
            # Validate credentials
            session = boto3.Session(
                aws_access_key_id=data['access_key'],
                aws_secret_access_key=data['secret_key'],
                region_name=data['region']
            )
            s3 = session.client('s3')
            s3.list_buckets()
            
            # Create source record
            source = DataSource(
                name=data['name'],
                type=self.source_type,
                status='active',
                config={
                    'bucket': data['bucket'],
                    'region': data['region']
                }
            )
            
            # Create S3 config
            s3_config = S3SourceConfig(
                source=source,
                bucket=data['bucket'],
                region=data['region'],
                prefix=data.get('prefix', ''),
                versioning_enabled=data.get('versioning_enabled', False)
            )
            
            self.db_session.add(source)
            self.db_session.add(s3_config)
            self.db_session.commit()
            
            return self._format_source(source)
        except Exception as e:
            self.logger.error(f"S3 connection error: {str(e)}")
            self.db_session.rollback()
            raise

    def list_objects(self, connection_id: str, prefix: str = '') -> List[Dict[str, Any]]:
        """List objects in S3 bucket."""
        try:
            source = self.db_session.query(DataSource).get(connection_id)
            if not source:
                raise ValueError("S3 source not found")
                
            s3_config = source.s3_config
            session = self._get_session(source)
            s3 = session.client('s3')
            
            response = s3.list_objects_v2(
                Bucket=s3_config.bucket,
                Prefix=prefix
            )
            
            return [
                {
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag']
                }
                for obj in response.get('Contents', [])
            ]
        except Exception as e:
            self.logger.error(f"S3 list error: {str(e)}")
            raise