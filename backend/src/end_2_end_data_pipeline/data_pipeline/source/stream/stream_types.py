# stream_types.py
from typing import Dict, List, Optional, Any, Union, Callable, TypeVar, Generator
from dataclasses import dataclass

# Type variables for generic type hints
T = TypeVar('T')
StreamData = Union[dict[str, Any], List[dict[str, Any]]]

@dataclass
class StreamConfig:
    """Configuration class for stream components"""
    bootstrap_servers: str
    group_id: str
    topic: str
    validation_config: dict[str, Any]

class StreamBase:
    """Base class for stream components with common type definitions."""

    def __init__(self, config: StreamConfig):
        self.config = config
        self.metadata: dict[str, Any] = {}

    def validate_config(self, config: StreamConfig) -> bool:
        """Validate stream configuration."""
        required_keys = ['stream_name', 'batch_size']
        return all(key in vars(config) for key in required_keys)

# Common type aliases
ConfigValidator = Callable[[StreamConfig], bool]
DataTransformer = Callable[[StreamData], StreamData]
BatchProcessor = Callable[[List[StreamData]], Any]

