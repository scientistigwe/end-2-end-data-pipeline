# backend/flask_api/app/services/data_sources/stream_service.py

from typing import Dict, Any
from confluent_kafka import Producer, Consumer
from .....database.models.data_source import DataSource, StreamSourceConfig
from .base_service import BaseSourceService


class StreamSourceService(BaseSourceService):
    source_type = 'stream'

    def connect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create stream connection and source."""
        try:
            # Validate connection
            if data['stream_type'] == 'kafka':
                self._test_kafka_connection(data)
            
            # Create source record
            source = DataSource(
                name=data['name'],
                type=self.source_type,
                status='active',
                config={
                    'stream_type': data['stream_type'],
                    'endpoint': data['endpoint']
                }
            )
            
            # Create stream config
            stream_config = StreamSourceConfig(
                source=source,
                stream_type=data['stream_type'],
                partitions=data.get('partitions'),
                batch_size=data.get('batch_size'),
                processing_config=data.get('processing_config', {})
            )
            
            self.db_session.add(source)
            self.db_session.add(stream_config)
            self.db_session.commit()
            
            return self._format_source(source)
        except Exception as e:
            self.logger.error(f"Stream connection error: {str(e)}")
            self.db_session.rollback()
            raise

    def get_status(self, connection_id: str) -> Dict[str, Any]:
        """Get stream connection status."""
        try:
            source = self.db_session.query(DataSource).get(connection_id)
            if not source:
                raise ValueError("Stream source not found")

            if source.config['stream_type'] == 'kafka':
                return self._get_kafka_status(source)
            
            raise ValueError(f"Unsupported stream type: {source.config['stream_type']}")
        except Exception as e:
            self.logger.error(f"Stream status error: {str(e)}")
            raise

    def _test_kafka_connection(self, data: Dict[str, Any]) -> None:
        """Test Kafka connection."""
        try:
            producer = Producer({
                'bootstrap.servers': data['endpoint']
            })
            producer.list_topics(timeout=10)
        except Exception as e:
            raise ValueError(f"Failed to connect to Kafka: {str(e)}")

    def _get_kafka_status(self, source: DataSource) -> Dict[str, Any]:
        """Get Kafka connection status."""
        try:
            producer = Producer({
                'bootstrap.servers': source.config['endpoint']
            })
            cluster_metadata = producer.list_topics(timeout=10)
            
            return {
                'status': 'connected',
                'topics': len(cluster_metadata.topics),
                'brokers': len(cluster_metadata.brokers)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }