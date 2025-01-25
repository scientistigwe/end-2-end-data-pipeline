# backend/config/config_manager.py

import os
import yaml
from typing import Any, Dict, Optional


class ConfigurationManager:
    """Centralized configuration management combining YAML defaults with environment overrides."""

    def __init__(self, config_path: Optional[str] = None):
        self._config: Dict[str, Any] = {
            # Default system settings
            'broker': {
                'max_workers': 4,
                'message_retention_hours': 24
            },
            'processing': {
                'max_flows': 10,
                'flow_retention_hours': 24
            },
            'staging': {
                'retention_days': 7,
                'quality_threshold': 0.8
            },
            'performance': {
                'thread_pool_workers': 4,
                'queue_size_limit': 100
            }
        }

        # Load YAML config if provided (will override defaults)
        if config_path and os.path.exists(config_path):
            self._load_yaml_config(config_path)

        # Load environment variables (highest priority)
        self._load_env_config()

    def _load_yaml_config(self, config_path: str) -> None:
        """Load configuration from YAML file, maintaining structure."""
        try:
            with open(config_path, 'r') as file:
                yaml_config = yaml.safe_load(file)
                if yaml_config:
                    # Map YAML settings to internal configuration structure
                    if 'broker_max_workers' in yaml_config:
                        self._config['broker']['max_workers'] = yaml_config['broker_max_workers']
                    if 'message_retention_hours' in yaml_config:
                        self._config['broker']['message_retention_hours'] = yaml_config['message_retention_hours']
                    if 'max_processing_flows' in yaml_config:
                        self._config['processing']['max_flows'] = yaml_config['max_processing_flows']
                    if 'flow_retention_hours' in yaml_config:
                        self._config['processing']['flow_retention_hours'] = yaml_config['flow_retention_hours']

                    # Handle nested configurations
                    if 'staging_area' in yaml_config:
                        staging = yaml_config['staging_area']
                        self._config['staging']['retention_days'] = staging.get('default_retention_days',
                                                                                self._config['staging'][
                                                                                    'retention_days'])
                        self._config['staging']['quality_threshold'] = staging.get('default_quality_threshold',
                                                                                   self._config['staging'][
                                                                                       'quality_threshold'])

                    if 'thread_pool' in yaml_config:
                        thread_pool = yaml_config['thread_pool']
                        self._config['performance']['thread_pool_workers'] = thread_pool.get('max_workers',
                                                                                             self._config[
                                                                                                 'performance'][
                                                                                                 'thread_pool_workers'])
                        self._config['performance']['queue_size_limit'] = thread_pool.get('queue_size_limit',
                                                                                          self._config['performance'][
                                                                                              'queue_size_limit'])
        except Exception as e:
            raise ValueError(f"Error loading YAML configuration: {str(e)}")

    def _load_env_config(self) -> None:
        """Override configurations with environment variables using structured mapping."""
        env_mapping = {
            'DATAFLOW_BROKER_MAX_WORKERS': ('broker', 'max_workers'),
            'DATAFLOW_MESSAGE_RETENTION_HOURS': ('broker', 'message_retention_hours'),
            'DATAFLOW_MAX_PROCESSING_FLOWS': ('processing', 'max_flows'),
            'DATAFLOW_FLOW_RETENTION_HOURS': ('processing', 'flow_retention_hours'),
            'DATAFLOW_STAGING_RETENTION_DAYS': ('staging', 'retention_days'),
            'DATAFLOW_QUALITY_THRESHOLD': ('staging', 'quality_threshold'),
            'DATAFLOW_THREAD_POOL_WORKERS': ('performance', 'thread_pool_workers'),
            'DATAFLOW_QUEUE_SIZE_LIMIT': ('performance', 'queue_size_limit')
        }

        for env_key, config_path in env_mapping.items():
            if env_key in os.environ:
                value = self._convert_value(os.environ[env_key])
                current = self._config
                for part in config_path[:-1]:
                    current = current[part]
                current[config_path[-1]] = value

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        value = value.lower()
        if value in ('true', 'false'):
            return value == 'true'
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._config[key] = value

    def has(self, key: str) -> bool:
        """Check if configuration key exists."""
        return key in self._config