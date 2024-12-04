# stream_fetcher.py
import json
from typing import Dict, Any, Generator, Optional, Callable
import logging
from kafka import KafkaConsumer
import pika
from .stream_config import Config

logger = logging.getLogger(__name__)

class StreamFetcher:
    """Handle stream data fetching operations"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize stream fetcher"""
        self.config = config
        self.stream_type = config['stream_type']
        self.consumer = None
        self.connection = None
        self.channel = None
        
    def initialize_consumer(self) -> None:
        """Initialize appropriate stream consumer"""
        try:
            if self.stream_type == 'kafka':
                self._initialize_kafka()
            elif self.stream_type == 'rabbitmq':
                self._initialize_rabbitmq()
            else:
                raise ValueError(f"Unsupported stream type: {self.stream_type}")
                
        except Exception as e:
            logger.error(f"Consumer initialization error: {str(e)}")
            raise

    def _initialize_kafka(self) -> None:
        """Initialize Kafka consumer"""
        try:
            self.consumer = KafkaConsumer(
                *self.config['topics'],
                bootstrap_servers=self.config['bootstrap_servers'],
                group_id=self.config['group_id'],
                auto_offset_reset=self.config.get('auto_offset_reset', 'latest'),
                enable_auto_commit=self.config.get('enable_auto_commit', True),
                max_poll_records=Config.MAX_POLL_RECORDS,
                consumer_timeout_ms=Config.CONSUMER_TIMEOUT_MS
            )
        except Exception as e:
            logger.error(f"Kafka initialization error: {str(e)}")
            raise

    def _initialize_rabbitmq(self) -> None:
        """Initialize RabbitMQ consumer"""
        try:
            credentials = pika.PlainCredentials(
                self.config.get('username', 'guest'),
                self.config.get('password', 'guest')
            )
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.config['host'],
                    port=self.config.get('port', 5672),
                    virtual_host=self.config.get('virtual_host', '/'),
                    credentials=credentials,
                    heartbeat=Config.HEARTBEAT_INTERVAL_MS
                )
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.config['queue'])
            
        except Exception as e:
            logger.error(f"RabbitMQ initialization error: {str(e)}")
            raise

    def consume_stream(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Consume stream data with callback"""
        try:
            if self.stream_type == 'kafka':
                self._consume_kafka(callback)
            elif self.stream_type == 'rabbitmq':
                self._consume_rabbitmq(callback)
                
        except Exception as e:
            logger.error(f"Stream consumption error: {str(e)}")
            raise

    def _consume_kafka(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Consume Kafka messages"""
        try:
            for message in self.consumer:
                try:
                    data = json.loads(message.value.decode('utf-8'))
                    metadata = {
                        'topic': message.topic,
                        'partition': message.partition,
                        'offset': message.offset,
                        'timestamp': message.timestamp
                    }
                    callback({'data': data, 'metadata': metadata})
                except Exception as e:
                    logger.error(f"Kafka message processing error: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Kafka consumption error: {str(e)}")
            raise

    def _consume_rabbitmq(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Consume RabbitMQ messages"""
        def process_message(ch, method, properties, body):
            try:
                data = json.loads(body.decode('utf-8'))
                metadata = {
                    'exchange': method.exchange,
                    'routing_key': method.routing_key,
                    'delivery_tag': method.delivery_tag
                }
                callback({'data': data, 'metadata': metadata})
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            except Exception as e:
                logger.error(f"RabbitMQ message processing error: {str(e)}")
                ch.basic_nack(delivery_tag=method.delivery_tag)

        try:
            self.channel.basic_consume(
                queue=self.config['queue'],
                on_message_callback=process_message
            )
            self.channel.start_consuming()
            
        except Exception as e:
            logger.error(f"RabbitMQ consumption error: {str(e)}")
            raise

    def close(self) -> None:
        """Close stream connections"""
        try:
            if self.stream_type == 'kafka' and self.consumer:
                self.consumer.close()
            elif self.stream_type == 'rabbitmq':
                if self.channel:
                    self.channel.close()
                if self.connection:
                    self.connection.close()
                    
        except Exception as e:
            logger.error(f"Stream closure error: {str(e)}")
            raise