"""Type definitions and base classes for stream processing."""

from typing import Dict, List, Optional, Any, Union, Callable, TypeVar, Generator

# Type variables for generic type hints
T = TypeVar('T')
StreamData = Union[dict[str, Any], List[dict[str, Any]]]
StreamConfig = Dict[str, Any]
StreamMetadata = Dict[str, Any]


class StreamBase:
    """Base class for stream components with common type definitions."""

    def __init__(self, config: StreamConfig):
        self.config = config
        self.metadata: StreamMetadata = {}

    def validate_config(self, config: StreamConfig) -> bool:
        """Validate stream configuration.

        Args:
            config: Stream configuration dictionary

        Returns:
            bool: True if configuration is valid
        """
        required_keys = ['stream_name', 'batch_size']
        return all(key in config for key in required_keys)


class StreamError(Exception):
    """Base exception for stream-related errors."""
    pass


# Common type aliases
ConfigValidator = Callable[[StreamConfig], bool]
DataTransformer = Callable[[StreamData], StreamData]
BatchProcessor = Callable[[List[StreamData]], Any]