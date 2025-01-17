from __future__ import annotations

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class DatabaseSourceConfig:
    """
    Configuration for db data source
    
    Responsible for storing and managing db connection configuration
    """
    
    # Supported db types with their default ports
    SUPPORTED_SOURCES: Dict[str, Dict[str, Optional[int]]] = field(default_factory=lambda: {
        'postgresql': {'default_port': 5432},
        'mysql': {'default_port': 3306},
        'mssql': {'default_port': 1433},
        'oracle': {'default_port': 1521},
        'sqlite': {'default_port': None}
    })

    # Core connection parameters
    source_type: str = 'postgresql'  # Default to postgresql
    host: str = 'localhost'
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    
    # Optional additional connection parameters
    additional_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """
        Post-initialization setup
        - Normalize source type
        - Set default port if not specified
        """
        # Normalize source type to lowercase
        self.source_type = self.source_type.lower()
        
        # Validate source type
        if self.source_type not in self.SUPPORTED_SOURCES:
            raise ValueError(f"Unsupported db type: {self.source_type}")
        
        # Set default port if not specified
        if self.port is None:
            self.port = self.SUPPORTED_SOURCES[self.source_type]['default_port']

    def get_connection_parameters(self) -> Dict[str, Any]:
        """
        Prepare connection parameters for db connection
        
        Returns:
            Dictionary of connection parameters
        """
        # Basic connection parameters
        connection_params = {
            'source_type': self.source_type,
            'host': self.host,
            'port': self.port,
            'db': self.database,
            'username': self.username
        }
        
        # Add any additional connection parameters
        connection_params.update(self.additional_params)
        
        return connection_params

    def mask_sensitive_info(self) -> Dict[str, Any]:
        """
        Create a safe representation of connection info for logging/debugging
        
        Returns:
            Dictionary with sensitive info masked
        """
        return {
            'source_type': self.source_type,
            'host': self.host,
            'port': self.port,
            'db': self.database,
            'username': self.username
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> DatabaseSourceConfig:
        """
        Create a DatabaseSourceConfig instance from a dictionary
        
        Args:
            config_dict: Configuration dictionary
        
        Returns:
            DatabaseSourceConfig instance
        """
        # Extract core parameters
        source_type = config_dict.get('source_type', 
            config_dict.get('type', 'postgresql'))
        
        # Remove core parameters to use as additional params
        core_params = ['source_type', 'type', 'host', 'port', 'db', 'username']
        additional_params = {
            k: v for k, v in config_dict.items() 
            if k not in core_params
        }

        return cls(
            source_type=source_type,
            host=config_dict.get('host', 'localhost'),
            port=config_dict.get('port'),
            database=config_dict.get('db'),
            username=config_dict.get('username'),
            additional_params=additional_params
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to a dictionary
        
        Returns:
            Dictionary representation of the configuration
        """
        config_dict = {
            'source_type': self.source_type,
            'host': self.host,
            'port': self.port,
            'db': self.database,
            'username': self.username
        }
        
        # Add additional parameters
        config_dict.update(self.additional_params)
        
        return config_dict

    def update(self, **kwargs):
        """
        Update configuration parameters
        
        Args:
            **kwargs: Keyword arguments to update
        """
        # Update core parameters
        core_params = ['source_type', 'host', 'port', 'db', 'username']
        for param in core_params:
            if param in kwargs:
                setattr(self, param, kwargs[param])
        
        # Update additional parameters
        self.additional_params.update({
            k: v for k, v in kwargs.items() 
            if k not in core_params
        })