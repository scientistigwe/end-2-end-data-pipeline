import json
from typing import Dict, Any, Generator, Optional, Callable, List
import logging
from confluent_kafka import Consumer, KafkaError, Message
import pika
from dataclasses import dataclass
from .stream_config import Config

logger = logging.getLogger(__name__)

@dataclass
class StreamMessage:
    """Standardized message format across different stream types"""
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    raw_message: Any  # Original message object

class StreamFetcher:
    """Enhanced stream data fetching operations with improved error handling"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize stream fetcher
        
        Args:
            config: Stream configuration dictionary
        """
        self.config = config
        self.stream_type = config['stream_type'].lower()
        self.consumer = None
        self.connection = None
        self.channel = None
        self._running = False
        
    def initialize_consumer(self) -> None:
        """Initialize appropriate stream consumer with error handling"""
        try:
            if self.stream_type == 'kafka':
                self._initialize_kafka()
            elif self.stream_type == 'rabbitmq':
                self._initialize_rabbitmq()
            else:
                raise ValueError(f"Unsupported stream type: {self.stream_type}")
                
        except Exception as e:
            logger.error(f"Consumer initialization error: {str(e)}")
            self.close()  # Ensure cleanup on initialization failure
            raise

    def _initialize_kafka(self) -> None:
        """Initialize Kafka consumer with confluent-kafka"""
        try:
            # Convert configuration to confluent-kafka format
            kafka_config = {
                'bootstrap.servers': self.config['bootstrap_servers'],
                'group.id': self.config['group_id'],
                'auto.offset.reset': self.config.get('auto_offset_reset', 'latest'),
                'enable.auto.commit': str(self.config.get('enable_auto_commit', True)).lower(),
                'max.poll.records': str(Config.MAX_POLL_RECORDS),
                'session.timeout.ms': '45000',
                'heartbeat.interval.ms': '15000',
                'metadata.max.age.ms': '300000'
            }
            
            self.consumer = Consumer(kafka_config)
            
            # Subscribe to topics
            topics = self.config['topics']
            if isinstance(topics, str):
                topics = [topics]
            self.consumer.subscribe(topics)
            
        except Exception as e:
            logger.error(f"Kafka initialization error: {str(e)}")
            raise

    def _initialize_rabbitmq(self) -> None:
        """Initialize RabbitMQ consumer with improved error handling"""
        try:
            credentials = pika.PlainCredentials(
                self.config.get('username', 'guest'),
                self.config.get('password', 'guest')
            )
            
            # Enhanced connection parameters
            parameters = pika.ConnectionParameters(
                host=self.config['host'],
                port=self.config.get('port', 5672),
                virtual_host=self.config.get('virtual_host', '/'),
                credentials=credentials,
                heartbeat=Config.HEARTBEAT_INTERVAL_MS,
                connection_attempts=3,
                retry_delay=5,
                socket_timeout=10
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare queue with additional parameters
            queue_name = self.config['queue']
            self.channel.queue_declare(
                queue=queue_name,
                durable=self.config.get('durable', True),
                auto_delete=self.config.get('auto_delete', False)
            )
            
            # Set QoS if specified
            prefetch_count = self.config.get('prefetch_count')
            if prefetch_count:
                self.channel.basic_qos(prefetch_count=prefetch_count)
            
        except Exception as e:
            logger.error(f"RabbitMQ initialization error: {str(e)}")
            self.close()  # Ensure cleanup
            raise

    def consume_stream(self, callback: Callable[[StreamMessage], None], 
                      batch_size: int = None, 
                      timeout: float = None) -> None:
        """
        Consume stream data with callback
        
        Args:
            callback: Function to process received messages
            batch_size: Optional batch size for processing multiple messages
            timeout: Optional timeout in seconds
        """
        try:
            self._running = True
            if self.stream_type == 'kafka':
                self._consume_kafka(callback, batch_size, timeout)
            elif self.stream_type == 'rabbitmq':
                self._consume_rabbitmq(callback)
                
        except Exception as e:
            logger.error(f"Stream consumption error: {str(e)}")
            raise
        finally:
            self._running = False

    def _consume_kafka(self, callback: Callable[[StreamMessage], None],
                      batch_size: int = None,
                      timeout: float = None) -> None:
        """
        Consume Kafka messages with batching support
        
        Args:
            callback: Function to process messages
            batch_size: Optional batch size for processing
            timeout: Optional timeout in seconds
        """
        try:
            messages = []
            while self._running:
                try:
                    msg = self.consumer.poll(timeout=1.0 if timeout is None else timeout)
                    
                    if msg is None:
                        continue
                        
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            logger.debug("Reached end of partition")
                            continue
                        else:
                            logger.error(f"Kafka error: {msg.error()}")
                            continue
                    
                    # Process message
                    try:
                        data = json.loads(msg.value().decode('utf-8'))
                        stream_message = StreamMessage(
                            data=data,
                            metadata={
                                'topic': msg.topic(),
                                'partition': msg.partition(),
                                'offset': msg.offset(),
                                'timestamp': msg.timestamp()[1]
                            },
                            raw_message=msg
                        )
                        
                        if batch_size:
                            messages.append(stream_message)
                            if len(messages) >= batch_size:
                                callback(messages)
                                messages = []
                        else:
                            callback(stream_message)
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON parsing error: {str(e)}")
                    except Exception as e:
                        logger.error(f"Message processing error: {str(e)}")
                        
                except Exception as e:
                    logger.error(f"Kafka consumption error: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Fatal Kafka consumption error: {str(e)}")
            raise
        finally:
            # Process any remaining messages in batch
            if messages:
                try:
                    callback(messages)
                except Exception as e:
                    logger.error(f"Final batch processing error: {str(e)}")

    def _consume_rabbitmq(self, callback: Callable[[StreamMessage], None]) -> None:
        """Consume RabbitMQ messages with enhanced error handling"""
        def process_message(ch, method, properties, body):
            try:
                data = json.loads(body.decode('utf-8'))
                stream_message = StreamMessage(
                    data=data,
                    metadata={
                        'exchange': method.exchange,
                        'routing_key': method.routing_key,
                        'delivery_tag': method.delivery_tag,
                        'redelivered': method.redelivered,
                        'properties': {
                            'content_type': properties.content_type,
                            'delivery_mode': properties.delivery_mode,
                            'headers': properties.headers
                        }
                    },
                    raw_message={'method': method, 'properties': properties, 'body': body}
                )
                
                callback(stream_message)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {str(e)}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except Exception as e:
                logger.error(f"RabbitMQ message processing error: {str(e)}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        try:
            self.channel.basic_consume(
                queue=self.config['queue'],
                on_message_callback=process_message
            )
            self._running = True
            self.channel.start_consuming()
            
        except Exception as e:
            logger.error(f"RabbitMQ consumption error: {str(e)}")
            raise

    def stop(self) -> None:
        """Gracefully stop consumption"""
        self._running = False
        self.close()

    def close(self) -> None:
        """Close stream connections with error handling"""
        try:
            if self.stream_type == 'kafka' and self.consumer:
                try:
                    self.consumer.close()
                except Exception as e:
                    logger.error(f"Error closing Kafka consumer: {str(e)}")
                    
            elif self.stream_type == 'rabbitmq':
                if self.channel:
                    try:
                        self.channel.close()
                    except Exception as e:
                        logger.error(f"Error closing RabbitMQ channel: {str(e)}")
                        
                if self.connection:
                    try:
                        self.connection.close()
                    except Exception as e:
                        logger.error(f"Error closing RabbitMQ connection: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Stream closure error: {str(e)}")
            raise