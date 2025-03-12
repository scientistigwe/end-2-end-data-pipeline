"""
Configuration Manager Module

This module provides a centralized configuration management system that combines
YAML defaults with environment variable overrides. It includes validation,
type conversion, and caching mechanisms.

Features:
    - YAML configuration loading
    - Environment variable override
    - Configuration validation
    - Type conversion
    - Performance caching
    - Nested configuration support

Usage:
    from config.config_manager import config_manager

    max_workers = config_manager.get('broker.max_workers')
    config_manager.set('performance.thread_pool_workers', 8)
"""

import os
import yaml
import logging
from typing import Any, Dict, Optional, Union, List
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass


class ConfigurationManager:
    """
    Centralized configuration management system.

    Provides a unified interface for managing application configuration
    from multiple sources with validation and caching.

    Attributes:
        _config (Dict[str, Any]): Internal configuration storage
        _env_prefix (str): Prefix for environment variables
        _path_sep (str): Separator for nested configuration paths
    """

    def __init__(
            self,
            config_path: Optional[str] = None,
            env_prefix: str = 'DATAFLOW_',
            path_sep: str = '.'
    ):
        """
        Initialize configuration manager.

        Args:
            config_path (Optional[str]): Path to YAML configuration file
            env_prefix (str): Prefix for environment variables
            path_sep (str): Separator for nested configuration paths
        """
        self._config: Dict[str, Any] = self._get_default_config()
        self._env_prefix = env_prefix
        self._path_sep = path_sep
        self._type_converters = self._setup_type_converters()

        if config_path:
            self._load_yaml_config(config_path)

        self._load_env_config()
        self._validate_config()

        logger.info("Configuration manager initialized successfully")

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """
        Get default configuration values.

        Returns:
            Dict[str, Any]: Default configuration dictionary
        """
        return {
            'broker': {
                'max_workers': 4,
                'message_retention_hours': 24,
                'retry_delay_seconds': 300,
                'max_retries': 3
            },
            'processing': {
                'max_flows': 10,
                'flow_retention_hours': 24,
                'batch_size': 1000,
                'timeout_seconds': 3600
            },
            'staging': {
                'retention_days': 7,
                'quality_threshold': 0.8,
                'max_file_size_mb': 1024,
                'compression_enabled': True
            },
            'performance': {
                'thread_pool_workers': 4,
                'queue_size_limit': 100,
                'cache_size_mb': 512,
                'enable_monitoring': True
            },
            'security': {
                'enable_encryption': True,
                'key_rotation_days': 30,
                'min_password_length': 12,
                'require_mfa': True
            }
        }

    def _setup_type_converters(self) -> Dict[str, callable]:
        """
        Set up type conversion functions for configuration values.

        Returns:
            Dict[str, callable]: Mapping of types to converter functions
        """
        return {
            'bool': lambda x: str(x).lower() in ('true', '1', 'yes', 'on'),
            'int': int,
            'float': float,
            'list': lambda x: [i.strip() for i in str(x).split(',') if i.strip()],
            'dict': lambda x: dict(item.split(':') for item in str(x).split(','))
        }

    def _load_yaml_config(self, config_path: str) -> None:
        """
        Load configuration from YAML file.

        Args:
            config_path (str): Path to YAML configuration file

        Raises:
            ConfigurationError: If YAML file cannot be loaded
        """
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                raise ConfigurationError(f"Configuration file not found: {config_path}")

            with open(config_path, 'r') as file:
                yaml_config = yaml.safe_load(file)
                if yaml_config:
                    self._merge_config(yaml_config)

            logger.info(f"Loaded YAML configuration from {config_path}")

        except Exception as e:
            raise ConfigurationError(f"Error loading YAML configuration: {str(e)}")

    def _merge_config(self, new_config: Dict[str, Any], base: Dict[str, Any] = None, path: str = '') -> None:
        """
        Recursively merge new configuration into existing config.

        Args:
            new_config (Dict[str, Any]): New configuration to merge.
            base (Dict[str, Any]): Base configuration to merge into
            path (str): Current config path for logging
        """
        if base is None:
            base = self._config

        for key, value in new_config.items():
            current_path = f"{path}{self._path_sep}{key}" if path else key

            if isinstance(value, dict) and key in base:
                self._merge_config(value, base[key], current_path)
            else:
                base[key] = value
                logger.debug(f"Updated configuration: {current_path} = {value}")

    def _load_env_config(self) -> None:
        """
        Load configuration from environment variables.

        Environment variables should be prefixed with self._env_prefix
        and use underscore as separator for nested configs.
        """
        env_configs = {
            key: value for key, value in os.environ.items()
            if key.startswith(self._env_prefix)
        }

        for env_key, value in env_configs.items():
            config_key = env_key[len(self._env_prefix):].lower()
            key_path = config_key.split('_')
            self._set_nested_value(key_path, self._convert_value(value))

        logger.info(f"")

    def _set_nested_value(self, key_path: List[str], value: Any) -> None:
        """
        Set value in nested configuration dictionary.

        Args:
            key_path (List[str]): Path to configuration key
            value (Any): Value to set

        Raises:
            ConfigurationError: If path is invalid
        """
        current = self._config
        for part in key_path[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                raise ConfigurationError(
                    f"Cannot set nested key {'.'.join(key_path)}: "
                    f"{part} is not a dictionary"
                )
            current = current[part]
        current[key_path[-1]] = value

        # Clear cache when updating values
        self.get.cache_clear()
        logger.debug(f"Updated config value: {'.'.join(key_path)} = {value}")

    def _convert_value(self, value: str) -> Any:
        """
        Convert string value to appropriate type.

        Args:
            value (str): Value to convert

        Returns:
            Any: Converted value
        """
        # Try boolean conversion first
        value_lower = value.lower()
        if value_lower in ('true', 'false'):
            return value_lower == 'true'

        # Try numeric conversion
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            # Handle list/dict strings
            if ',' in value:
                if ':' in value:  # Looks like a dict
                    return self._type_converters['dict'](value)
                return self._type_converters['list'](value)
            return value

    def _validate_config(self) -> None:
        """
        Validate configuration values against rules.

        Raises:
            ConfigurationError: If validation fails
        """
        validators = {
            ('broker', 'max_workers'): (
                lambda x: isinstance(x, int) and 1 <= x <= 32,
                "Broker max_workers must be between 1 and 32"
            ),
            ('processing', 'max_flows'): (
                lambda x: isinstance(x, int) and 1 <= x <= 100,
                "Processing max_flows must be between 1 and 100"
            ),
            ('staging', 'quality_threshold'): (
                lambda x: isinstance(x, (int, float)) and 0.0 <= x <= 1.0,
                "Staging quality_threshold must be between 0.0 and 1.0"
            ),
            ('performance', 'thread_pool_workers'): (
                lambda x: isinstance(x, int) and x > 0,
                "Performance thread_pool_workers must be positive"
            )
        }

        for (section, key), (validator, message) in validators.items():
            value = self.get(f"{section}.{key}")
            if value is not None and not validator(value):
                raise ConfigurationError(f"Invalid configuration: {message}")

    @lru_cache(maxsize=128)
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key (str): Configuration key (dot-separated for nested configs)
            default (Any): Default value if key not found

        Returns:
            Any: Configuration value

        Example:
            >>> config_manager.get('broker.max_workers')
            4
            >>> config_manager.get('invalid.key', 'default_value')
            'default_value'
        """
        try:
            value = self._config
            for part in key.split(self._path_sep):
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key (str): Configuration key (dot-separated for nested configs)
            value (Any): Value to set

        Example:
            >>> config_manager.set('broker.max_workers', 8)
        """
        key_path = key.split(self._path_sep)
        self._set_nested_value(key_path, value)

    def has(self, key: str) -> bool:
        """
        Check if configuration key exists.

        Args:
            key (str): Configuration key to check

        Returns:
            bool: True if key exists

        Example:
            >>> config_manager.has('broker.max_workers')
            True
        """
        return self.get(key) is not None

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section.

        Args:
            section (str): Section name

        Returns:
            Dict[str, Any]: Section configuration

        Example:
            >>> config_manager.get_section('broker')
            {'max_workers': 4, 'message_retention_hours': 24, ...}
        """
        return dict(self.get(section, {}))

    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        Update configuration from dictionary.

        Args:
            config_dict (Dict[str, Any]): Configuration updates

        Example:
            >>> config_manager.update_from_dict({'broker': {'max_workers': 8}})
        """
        self._merge_config(config_dict)
        self._validate_config()

    def reset(self) -> None:
        """
        Reset configuration to defaults.

        Example:
            >>> config_manager.reset()
        """
        self._config = self._get_default_config()
        self.get.cache_clear()
        logger.info("Configuration reset to defaults")

    def export_config(self) -> Dict[str, Any]:
        """
        Export current configuration.

        Returns:
            Dict[str, Any]: Current configuration

        Example:
            >>> config = config_manager.export_config()
        """
        return dict(self._config)


# Create singleton instance
config_manager = ConfigurationManager()