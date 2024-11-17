"""
stream_validator.py

Validates the streaming source configuration to ensure it is correct and complete.
"""

from .stream_config import StreamConfig


class StreamValidator:
    def __init__(self, config):
        """
        Initializes the validator with a given configuration.

        Args:
            config (StreamConfig): The configuration object for validation.
        """
        self.config = config

    def validate_source(self):
        """Validates the stream source configuration.

        Returns:
            bool: True if the configuration is valid, False otherwise.
        """
        config_data = self.config.get_config()
        required_fields = ['source_type', 'endpoint', 'credentials']

        for field in required_fields:
            if not config_data.get(field):
                raise ValueError(f"Configuration error: Missing {field}")

        return True
