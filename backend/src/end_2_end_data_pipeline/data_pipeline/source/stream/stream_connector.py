# data_pipeline/source/cloud/stream_connector.py
import confluent_kafka
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_config import StreamConfig
from backend.src.end_2_end_data_pipeline.data_pipeline.exceptions import StreamingConnectionError, StreamingDataLoadingError


class StreamConnector:
    """Manages connections and message reading from Kafka streams"""

    def __init__(self, config: StreamConfig):
        self.config = config
        self.consumer = None
        self.metrics = {
            'connection_attempts': 0,
            'connection_drops': 0,
            'messages_processed': 0,
            'last_poll_timestamp': None,
            'batch_sizes': []
        }
        self._initialize_consumer()

    def _initialize_consumer(self):
        """Initialize the Kafka consumer with retry logic"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                self.consumer = confluent_kafka.Consumer(self.config.get_consumer_config())
                self.consumer.subscribe([self.config.topic])
                logging.info(f"Successfully connected to Kafka topic: {self.config.topic}")
                break
            except confluent_kafka.KafkaException as e:
                retry_count += 1
                self.metrics['connection_attempts'] += 1
                if retry_count == max_retries:
                    raise StreamingConnectionError(f"Failed to connect to Kafka after {max_retries} attempts: {e}")
                logging.warning(f"Connection attempt {retry_count} failed, retrying...")

    def read_messages(self, batch_size: Optional[int] = None) -> List[str]:
        """Read messages from Kafka with monitoring and error handling"""
        if not self.consumer:
            raise StreamingConnectionError("Consumer not initialized")

        messages = []
        start_time = datetime.now()
        batch_size = batch_size or self.config.batch_size

        try:
            while len(messages) < batch_size:
                msg = self.consumer.poll(timeout=self.config.poll_timeout)

                if msg is None:
                    break

                if msg.error():
                    if msg.error().code() == confluent_kafka.KafkaError._PARTITION_EOF:
                        logging.info("Reached end of partition")
                        break
                    else:
                        raise StreamingDataLoadingError(f"Error reading message: {msg.error()}")

                messages.append(msg.value().decode('utf-8'))

            # Update metrics
            self.metrics['messages_processed'] += len(messages)
            self.metrics['last_poll_timestamp'] = datetime.now()
            self.metrics['batch_sizes'].append(len(messages))

            # Commit offsets
            self.consumer.commit(asynchronous=False)

            return messages

        except confluent_kafka.KafkaException as e:
            self.metrics['connection_drops'] += 1
            raise StreamingDataLoadingError(f"Error reading messages from Kafka: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get current connector metrics"""
        return {
            **self.metrics,
            'messages_per_second': self._calculate_throughput(),
            'average_batch_size': sum(self.metrics['batch_sizes']) / len(self.metrics['batch_sizes'])
            if self.metrics['batch_sizes'] else 0
        }

    def _calculate_throughput(self) -> float:
        """Calculate current messages per second throughput"""
        if not self.metrics['last_poll_timestamp']:
            return 0.0

        time_diff = (datetime.now() - self.metrics['last_poll_timestamp']).total_seconds()
        return self.metrics['messages_processed'] / max(time_diff, 1)

    def close(self):
        """Clean up consumer resources"""
        if self.consumer:
            self.consumer.close()
