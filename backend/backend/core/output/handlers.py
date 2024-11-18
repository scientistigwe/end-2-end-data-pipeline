# backend/backend/core/output/handlers.py

from typing import Dict, Any, Optional
import logging
import json
import os
from datetime import datetime
import requests
from abc import ABC, abstractmethod

# Import database connector (example using SQLAlchemy)
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.exc import SQLAlchemyError

# Import stream processing libraries (example using Kafka)
from kafka import KafkaProducer
from kafka.errors import KafkaError


class OutputHandlerError(Exception):
    """Base exception for output handler errors"""
    pass


class BaseOutputHandler(ABC):
    """Abstract base class for output handlers"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

    @abstractmethod
    def handle_output(self, data: Any, pipeline_state: Dict[str, Any]) -> None:
        """Handle the output data"""
        pass

    def _validate_data(self, data: Any) -> bool:
        """Basic data validation"""
        return data is not None

    def _format_timestamp(self) -> str:
        """Get formatted timestamp for filenames/logging"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")


class DatabaseOutputHandler(BaseOutputHandler):
    """Handler for database outputs"""

    def __init__(self, connection_string: Optional[str] = None):
        super().__init__()
        self.connection_string = connection_string or os.getenv("DATABASE_URL")
        if not self.connection_string:
            raise OutputHandlerError("No database connection string provided")

        try:
            self.engine = create_engine(self.connection_string)
            self.metadata = MetaData()
        except Exception as e:
            raise OutputHandlerError(f"Failed to initialize database connection: {str(e)}")

    def handle_output(self, data: Any, pipeline_state: Dict[str, Any]) -> None:
        """Save data to database"""
        if not self._validate_data(data):
            raise OutputHandlerError("Invalid data provided")

        try:
            # Get target table information from pipeline state
            table_name = pipeline_state.get("output_table", "default_output")

            # Reflect the table if it exists
            table = Table(table_name, self.metadata, autoload_with=self.engine)

            # Insert data
            with self.engine.connect() as connection:
                if isinstance(data, list):
                    connection.execute(table.insert(), data)
                else:
                    connection.execute(table.insert(), [data])
                connection.commit()

            self.logger.info(f"Successfully saved data to table: {table_name}")

        except SQLAlchemyError as e:
            error_msg = f"Database output error: {str(e)}"
            self.logger.error(error_msg)
            raise OutputHandlerError(error_msg)


class FileOutputHandler(BaseOutputHandler):
    """Handler for file outputs"""

    def __init__(self, output_dir: Optional[str] = None):
        super().__init__()
        self.output_dir = output_dir or os.getenv("OUTPUT_DIR", "outputs")
        os.makedirs(self.output_dir, exist_ok=True)

    def handle_output(self, data: Any, pipeline_state: Dict[str, Any]) -> None:
        """Save data to file"""
        if not self._validate_data(data):
            raise OutputHandlerError("Invalid data provided")

        try:
            # Generate filename based on pipeline state and timestamp
            source_type = pipeline_state.get("source_type", "unknown")
            timestamp = self._format_timestamp()
            filename = f"{source_type}_output_{timestamp}.json"
            filepath = os.path.join(self.output_dir, filename)

            # Write data to file
            with open(filepath, 'w') as f:
                if isinstance(data, (dict, list)):
                    json.dump(data, f, indent=2)
                else:
                    f.write(str(data))

            self.logger.info(f"Successfully saved data to file: {filepath}")

        except (IOError, TypeError) as e:
            error_msg = f"File output error: {str(e)}"
            self.logger.error(error_msg)
            raise OutputHandlerError(error_msg)


class APIOutputHandler(BaseOutputHandler):
    """Handler for API outputs"""

    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        super().__init__()
        self.api_url = api_url or os.getenv("API_OUTPUT_URL")
        self.api_key = api_key or os.getenv("API_OUTPUT_KEY")

        if not self.api_url:
            raise OutputHandlerError("No API URL provided")

    def handle_output(self, data: Any, pipeline_state: Dict[str, Any]) -> None:
        """Send data to API endpoint"""
        if not self._validate_data(data):
            raise OutputHandlerError("Invalid data provided")

        try:
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }

            # Prepare payload
            payload = {
                "data": data,
                "metadata": {
                    "pipeline_id": pipeline_state.get("pipeline_id"),
                    "source_type": pipeline_state.get("source_type"),
                    "timestamp": self._format_timestamp()
                }
            }

            # Send POST request
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            response.raise_for_status()
            self.logger.info(f"Successfully sent data to API: {self.api_url}")

        except requests.exceptions.RequestException as e:
            error_msg = f"API output error: {str(e)}"
            self.logger.error(error_msg)
            raise OutputHandlerError(error_msg)


class StreamOutputHandler(BaseOutputHandler):
    """Handler for stream outputs (e.g., Kafka)"""

    def __init__(self, bootstrap_servers: Optional[str] = None):
        super().__init__()
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS")

        if not self.bootstrap_servers:
            raise OutputHandlerError("No Kafka bootstrap servers provided")

        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
        except KafkaError as e:
            raise OutputHandlerError(f"Failed to initialize Kafka producer: {str(e)}")

    def handle_output(self, data: Any, pipeline_state: Dict[str, Any]) -> None:
        """Send data to stream"""
        if not self._validate_data(data):
            raise OutputHandlerError("Invalid data provided")

        try:
            # Get topic from pipeline state or use default
            topic = pipeline_state.get("output_topic", "default_output")

            # Prepare message
            message = {
                "data": data,
                "metadata": {
                    "pipeline_id": pipeline_state.get("pipeline_id"),
                    "source_type": pipeline_state.get("source_type"),
                    "timestamp": self._format_timestamp()
                }
            }

            # Send message to Kafka
            future = self.producer.send(topic, message)
            future.get(timeout=10)  # Wait for sending to complete

            self.logger.info(f"Successfully sent data to topic: {topic}")

        except KafkaError as e:
            error_msg = f"Stream output error: {str(e)}"
            self.logger.error(error_msg)
            raise OutputHandlerError(error_msg)

    def __del__(self):
        """Cleanup Kafka producer"""
        if hasattr(self, 'producer'):
            self.producer.close()