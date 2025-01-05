# backend/flask_api/app/services/data_sources/stream_service.py

from confluent_kafka import Consumer, Producer, KafkaError, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic
from typing import Dict, Any, List, Optional
from uuid import UUID
import json
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .base_service import BaseSourceService
from .....database.models.data_source import DataSource, StreamSourceConfig

class StreamSourceService(BaseSourceService):
    source_type = 'stream'

    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self._producer_registry: Dict[UUID, Producer] = {}
        self._consumer_registry: Dict[UUID, Consumer] = {}
        self._admin_registry: Dict[UUID, AdminClient] = {}

    def list_sources(self) -> List[DataSource]:
        """
        List all stream data sources.
        
        Returns:
            List[DataSource]: List of all stream data sources
        """
        try:
            return (self.db_session.query(DataSource)
                    .filter(DataSource.type == self.source_type)
                    .all())
        except Exception as exc:
            self.logger.error(f"Error listing stream sources: {str(exc)}")
            raise
        
    def connect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create and validate stream connection."""
        try:
            # Validate configuration
            validation_result = self.validate_config(data)
            if validation_result.status == 'failed':
                raise ValueError(f"Invalid stream configuration: {validation_result.details}")

            # Test connection before creating records
            admin_client = self._create_admin_client(data)
            metadata = admin_client.list_topics(timeout=10)

            # Create source record
            source = DataSource(
                name=data['name'],
                type=self.source_type,
                status='pending',
                config={
                    'stream_type': data['stream_type'],
                    'bootstrap_servers': data['bootstrap_servers'],
                    'topics': data.get('topics', [])
                }
            )

            # Create stream config
            stream_config = StreamSourceConfig(
                source=source,
                stream_type=data['stream_type'],
                partitions=data.get('partitions'),
                batch_size=data.get('batch_size', 100),
                processing_config=data.get('processing_config', {
                    'auto_offset_reset': 'latest',
                    'enable_auto_commit': True,
                    'max_poll_records': 500
                }),
                error_handling=data.get('error_handling', {
                    'dead_letter_queue': True,
                    'retry_count': 3
                }),
                scaling_config=data.get('scaling_config', {
                    'min_partitions': 1,
                    'max_partitions': 10
                })
            )

            source.status = 'active'
            self.db_session.add(source)
            self.db_session.add(stream_config)
            self.db_session.commit()

            # Store clients in registry
            self._admin_registry[source.id] = admin_client

            return self._format_source(source)
        except KafkaException as e:
            self.logger.error(f"Stream connection error: {str(e)}")
            self.db_session.rollback()
            raise ValueError(f"Failed to connect to stream: {str(e)}")
        except Exception as e:
            self.logger.error(f"Stream connection error: {str(e)}")
            self.db_session.rollback()
            raise

    def get_metrics(self, source_id: UUID) -> Dict[str, Any]:
        """Get stream metrics and statistics."""
        try:
            source = self._get_source_or_error(source_id)
            admin_client = self._get_admin_client(source)
            
            # Get topic metadata
            metadata = admin_client.list_topics(timeout=10)
            topics = source.config.get('topics', [])
            
            metrics = {
                'topics': {},
                'total_partitions': 0,
                'total_messages': 0
            }
            
            for topic in topics:
                topic_metrics = self._get_topic_metrics(source, topic)
                metrics['topics'][topic] = topic_metrics
                metrics['total_partitions'] += topic_metrics['partitions']
                metrics['total_messages'] += topic_metrics['messages']
            
            return metrics
        except Exception as e:
            self.logger.error(f"Failed to get metrics: {str(e)}")
            raise

    def start_consumer(self, source_id: UUID, consumer_group: str) -> Dict[str, Any]:
        """Start a new consumer in the specified consumer group."""
        try:
            source = self._get_source_or_error(source_id)
            
            if source.id in self._consumer_registry:
                raise ValueError("Consumer already running for this source")
            
            consumer_config = {
                'bootstrap.servers': source.config['bootstrap_servers'],
                'group.id': consumer_group,
                'auto.offset.reset': source.stream_config.processing_config['auto_offset_reset'],
                'enable.auto.commit': source.stream_config.processing_config['enable_auto_commit'],
                'max.poll.records': source.stream_config.processing_config['max_poll_records']
            }
            
            consumer = Consumer(consumer_config)
            consumer.subscribe(source.config['topics'])
            self._consumer_registry[source.id] = consumer
            
            return {
                'status': 'started',
                'consumer_group': consumer_group,
                'topics': source.config['topics']
            }
        except Exception as e:
            self.logger.error(f"Failed to start consumer: {str(e)}")
            raise

    def stop_consumer(self, source_id: UUID) -> Dict[str, Any]:
        """Stop the consumer for this source."""
        try:
            if source_id in self._consumer_registry:
                consumer = self._consumer_registry[source_id]
                consumer.close()
                del self._consumer_registry[source_id]
                
                return {
                    'status': 'stopped',
                    'message': 'Consumer successfully stopped'
                }
            raise ValueError("No active consumer found for this source")
        except Exception as e:
            self.logger.error(f"Failed to stop consumer: {str(e)}")
            raise

    def _validate_source_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate stream source configuration."""
        errors = []
        required_fields = ['stream_type', 'bootstrap_servers']
        
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        valid_stream_types = ['kafka', 'kinesis', 'pubsub']
        if 'stream_type' in config and config['stream_type'] not in valid_stream_types:
            errors.append(f"Invalid stream type. Must be one of: {', '.join(valid_stream_types)}")

        if 'bootstrap_servers' in config:
            if not isinstance(config['bootstrap_servers'], str) or not config['bootstrap_servers']:
                errors.append("bootstrap_servers must be a non-empty string")

        return errors

    def _test_source_connection(self, source: DataSource) -> Dict[str, Any]:
        """Test stream connection and return metrics."""
        admin_client = self._get_admin_client(source)
        
        try:
            metadata = admin_client.list_topics(timeout=10)
            broker_metadata = metadata.brokers
            
            return {
                "brokers_connected": len(broker_metadata),
                "topics_available": len(metadata.topics),
                "cluster_id": metadata.cluster_id
            }
        except KafkaException as e:
            raise ValueError(f"Failed to test connection: {str(e)}")

    def _sync_source_data(self, source: DataSource) -> Dict[str, Any]:
        """Sync stream metadata and statistics."""
        total_messages = 0
        total_bytes = 0
        
        for topic in source.config.get('topics', []):
            topic_metrics = self._get_topic_metrics(source, topic)
            total_messages += topic_metrics['messages']
            total_bytes += topic_metrics['size_bytes']
        
        return {
            "records_processed": total_messages,
            "bytes_processed": total_bytes
        }

    def _get_source_preview(self, source: DataSource, limit: int) -> List[Dict[str, Any]]:
        """Get preview of stream messages."""
        preview_data = []
        consumer = self._create_preview_consumer(source)
        
        try:
            start_time = datetime.utcnow()
            timeout = timedelta(seconds=5)
            
            while len(preview_data) < limit and datetime.utcnow() - start_time < timeout:
                msg = consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    raise KafkaException(msg.error())
                
                try:
                    value = json.loads(msg.value().decode('utf-8'))
                except json.JSONDecodeError:
                    value = msg.value().decode('utf-8')
                
                preview_data.append({
                    'topic': msg.topic(),
                    'partition': msg.partition(),
                    'offset': msg.offset(),
                    'timestamp': msg.timestamp()[1],
                    'key': msg.key().decode('utf-8') if msg.key() else None,
                    'value': value
                })
            
            return preview_data
        finally:
            consumer.close()

    def _disconnect_source(self, source: DataSource) -> None:
        """Clean up stream connection resources."""
        for registry in [self._producer_registry, self._consumer_registry, self._admin_registry]:
            if source.id in registry:
                client = registry[source.id]
                if hasattr(client, 'close'):
                    client.close()
                del registry[source.id]

    def _create_preview_consumer(self, source: DataSource) -> Consumer:
        """Create a temporary consumer for preview purposes."""
        consumer_config = {
            'bootstrap.servers': source.config['bootstrap_servers'],
            'group.id': f'preview_consumer_{source.id}_{datetime.utcnow().timestamp()}',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
            'max.poll.records': 100
        }
        
        consumer = Consumer(consumer_config)
        consumer.subscribe(source.config['topics'])
        return consumer

    def _create_admin_client(self, config: Dict[str, Any]) -> AdminClient:
        """Create Kafka admin client."""
        admin_config = {
            'bootstrap.servers': config['bootstrap_servers']
        }
        return AdminClient(admin_config)

    def _get_admin_client(self, source: DataSource) -> AdminClient:
        """Get or create admin client for source."""
        if source.id not in self._admin_registry:
            self._admin_registry[source.id] = self._create_admin_client({
                'bootstrap.servers': source.config['bootstrap_servers']
            })
        return self._admin_registry[source.id]

    def _get_topic_metrics(self, source: DataSource, topic: str) -> Dict[str, Any]:
        """Get metrics for a specific topic."""
        admin_client = self._get_admin_client(source)
        
        try:
            metadata = admin_client.list_topics(topic, timeout=10)
            topic_metadata = metadata.topics[topic]
            
            # Calculate messages per partition
            messages = 0
            size_bytes = 0
            
            for partition in topic_metadata.partitions.values():
                consumer = self._create_preview_consumer(source)
                try:
                    # Get end offsets
                    end_offsets = consumer.get_watermark_offsets(
                        TopicPartition(topic, partition.id)
                    )
                    messages += end_offsets[1] - end_offsets[0]
                    
                    # Estimate size based on sample messages
                    sample_msgs = consumer.consume(num_messages=10, timeout=1.0)
                    if sample_msgs:
                        avg_msg_size = sum(len(msg.value()) for msg in sample_msgs) / len(sample_msgs)
                        size_bytes += avg_msg_size * messages
                finally:
                    consumer.close()
            
            return {
                'partitions': len(topic_metadata.partitions),
                'messages': messages,
                'size_bytes': size_bytes,
                'replication_factor': len(topic_metadata.replicas),
                'is_internal': topic_metadata.is_internal
            }
        except KafkaException as e:
            self.logger.error(f"Failed to get topic metrics: {str(e)}")
            return {
                'partitions': 0,
                'messages': 0,
                'size_bytes': 0,
                'replication_factor': 0,
                'is_internal': False,
                'error': str(e)
            }

    def create_topic(self, source_id: UUID, topic_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new topic in the stream."""
        try:
            source = self._get_source_or_error(source_id)
            admin_client = self._get_admin_client(source)
            
            new_topic = NewTopic(
                topic_config['name'],
                num_partitions=topic_config.get('partitions', 1),
                replication_factor=topic_config.get('replication_factor', 1),
                config=topic_config.get('config', {})
            )
            
            result = admin_client.create_topics([new_topic])
            
            for topic, future in result.items():
                try:
                    future.result()
                except Exception as e:
                    raise ValueError(f"Failed to create topic {topic}: {str(e)}")
            
            # Update source config with new topic
            if 'topics' not in source.config:
                source.config['topics'] = []
            source.config['topics'].append(topic_config['name'])
            self.db_session.commit()
            
            return {
                'name': topic_config['name'],
                'partitions': topic_config.get('partitions', 1),
                'replication_factor': topic_config.get('replication_factor', 1),
                'config': topic_config.get('config', {})
            }
        except Exception as e:
            self.logger.error(f"Failed to create topic: {str(e)}")
            raise

    def delete_topic(self, source_id: UUID, topic_name: str) -> Dict[str, Any]:
        """Delete a topic from the stream."""
        try:
            source = self._get_source_or_error(source_id)
            admin_client = self._get_admin_client(source)
            
            result = admin_client.delete_topics([topic_name])
            
            for topic, future in result.items():
                try:
                    future.result()
                except Exception as e:
                    raise ValueError(f"Failed to delete topic {topic}: {str(e)}")
            
            # Update source config
            if 'topics' in source.config:
                source.config['topics'].remove(topic_name)
                self.db_session.commit()
            
            return {
                'status': 'deleted',
                'topic': topic_name
            }
        except Exception as e:
            self.logger.error(f"Failed to delete topic: {str(e)}")
            raise

    def get_consumer_groups(self, source_id: UUID) -> List[Dict[str, Any]]:
        """Get information about consumer groups."""
        try:
            source = self._get_source_or_error(source_id)
            admin_client = self._get_admin_client(source)
            
            groups = admin_client.list_groups()
            
            return [{
                'group_id': group.id,
                'state': group.state,
                'protocol_type': group.protocol_type,
                'protocol': group.protocol,
                'members': [{
                    'id': member.id,
                    'client_id': member.client_id,
                    'client_host': member.client_host
                } for member in group.members]
            } for group in groups]
        except Exception as e:
            self.logger.error(f"Failed to get consumer groups: {str(e)}")
            raise