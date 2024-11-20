import os
import yaml
from typing import Any, Dict, Optional


class ConfigurationManager:
    """
    Centralized configuration management with multiple source support
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager

        Args:
            config_path (str, optional): Path to configuration file
        """
        self._config: Dict[str, Any] = {}
        self._env_prefix = 'DATAFLOW_'

        # Load configurations from multiple sources
        if config_path and os.path.exists(config_path):
            self._load_yaml_config(config_path)

        self._load_env_config()

    def _load_yaml_config(self, config_path: str) -> None:
        """
        Load configuration from YAML file

        Args:
            config_path (str): Path to YAML configuration file
        """
        with open(config_path, 'r') as file:
            yaml_config = yaml.safe_load(file)
            self._config.update(yaml_config or {})

    def _load_env_config(self) -> None:
        """
        Override configurations with environment variables
        """
        for key, value in os.environ.items():
            if key.startswith(self._env_prefix):
                config_key = key[len(self._env_prefix):].lower()
                try:
                    # Try to convert to appropriate type
                    converted_value = self._convert_value(value)
                    self._config[config_key] = converted_value
                except ValueError:
                    self._config[config_key] = value

    def _convert_value(self, value: str) -> Any:
        """
        Convert string value to appropriate type

        Args:
            value (str): Value to convert

        Returns:
            Converted value in appropriate type
        """
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
        """
        Get configuration value

        Args:
            key (str): Configuration key
            default (Any, optional): Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value

        Args:
            key (str): Configuration key
            value (Any): Configuration value
        """
        self._config[key] = value

    def has(self, key: str) -> bool:
        """
        Check if configuration key exists

        Args:
            key (str): Configuration key

        Returns:
            bool: Whether key exists
        """
        return key in self._config