# backend/core/registry/component_registry.py

import logging
import uuid
from typing import Dict

logger = logging.getLogger(__name__)


class ComponentRegistry:
    """
    Centralized component registry to ensure consistent module identification
    across the system.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """Initialize the registry"""
        self.registered_components: Dict[str, str] = {}
        self.component_uuid = str(uuid.uuid4())
        logger.info(f"Initialized ComponentRegistry with UUID: {self.component_uuid}")

    def register_component(self, component_name: str) -> str:
        """Register a component and return its UUID"""
        if component_name not in self.registered_components:
            self.registered_components[component_name] = self.component_uuid
            logger.info(f"Registered component {component_name} with UUID {self.component_uuid}")
        return self.registered_components[component_name]

    def get_component_uuid(self, component_name: str) -> str:
        """Get UUID for a component, registering it if necessary"""
        return self.register_component(component_name)