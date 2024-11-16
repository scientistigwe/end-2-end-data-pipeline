"""
stream_config.py

Handles the configuration for stream sources, including user inputs from the UI.
"""


class StreamConfig:
    def __init__(self, source_type, endpoint, credentials):
        """
        Initializes the configuration for a streaming source.

        Args:
            source_type (str): Type of the stream source (e.g., Kafka, Kinesis, HTTP).
            endpoint (str): Endpoint URL or connection string for the stream.
            credentials (dict): Credentials needed for secure access.
        """
        self.source_type = source_type
        self.endpoint = endpoint
        self.credentials = credentials

    def get_config(self):
        """Returns the configuration details as a dictionary."""
        return {
            'source_type': self.source_type,
            'endpoint': self.endpoint,
            'credentials': self.credentials
        }
