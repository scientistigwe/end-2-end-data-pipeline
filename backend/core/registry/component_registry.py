# backend/core/registry/component_registry.py

import logging
import uuid
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from ..messaging.event_types import ComponentType, MessageType
from ..messaging.broker import MessageBroker

logger = logging.getLogger(__name__)


@dataclass
class ComponentMetadata:
    """Metadata for registered components"""
    component_type: ComponentType
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    status: str = "active"
    dependencies: Set[str] = field(default_factory=set)
    capabilities: Set[str] = field(default_factory=set)
    config: Dict[str, Any] = field(default_factory=dict)


class ComponentRegistry:
    """Enhanced centralized component registry"""

    _instance = None

    def __new__(cls, message_broker: Optional[MessageBroker] = None):
        if cls._instance is None:
            cls._instance = super(ComponentRegistry, cls).__new__(cls)
            cls._instance.initialize(message_broker)
        elif message_broker is not None:
            cls._instance.message_broker = message_broker
        return cls._instance

    def initialize(self, message_broker: Optional[MessageBroker]):
        """Initialize the registry with enhanced tracking"""
        # Core storage
        self.registered_components: Dict[str, ComponentMetadata] = {}
        self.component_relationships: Dict[str, Set[str]] = {}
        self.component_uuids: Dict[str, str] = {}

        # Message broker integration
        self.message_broker = message_broker

        # System tracking
        self.registry_id = str(uuid.uuid4())
        self.startup_time = datetime.now()

        # Performance monitoring
        self.stats = {
            'components_registered': 0,
            'components_active': 0,
            'registration_errors': 0
        }

        logger.info(f"Initialized ComponentRegistry with ID: {self.registry_id}")

    async def register_component(
            self,
            component_name: str,
            component_type: ComponentType,
            dependencies: Optional[List[str]] = None,
            capabilities: Optional[List[str]] = None,
            config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a component with enhanced metadata"""
        try:
            # Generate or retrieve UUID
            component_uuid = self.component_uuids.get(
                component_name,
                str(uuid.uuid4())
            )

            # Create metadata
            metadata = ComponentMetadata(
                component_type=component_type,
                dependencies=set(dependencies or []),
                capabilities=set(capabilities or []),
                config=config or {}
            )

            # Store component information
            self.registered_components[component_name] = metadata
            self.component_uuids[component_name] = component_uuid

            # Update relationships
            if dependencies:
                for dep in dependencies:
                    if dep not in self.component_relationships:
                        self.component_relationships[dep] = set()
                    self.component_relationships[dep].add(component_name)

            # Update stats
            self.stats['components_registered'] += 1
            self.stats['components_active'] += 1

            # Notify about registration
            if self.message_broker:
                await self._notify_component_registration(
                    component_name,
                    component_uuid,
                    metadata
                )

            logger.info(
                f"Registered component {component_name} "
                f"({component_type.value}) with UUID {component_uuid}"
            )
            return component_uuid

        except Exception as e:
            self.stats['registration_errors'] += 1
            logger.error(f"Component registration failed: {str(e)}")
            raise

    async def deregister_component(self, component_name: str) -> bool:
        """Deregister a component and clean up relationships"""
        try:
            if component_name not in self.registered_components:
                return False

            # Update metadata
            metadata = self.registered_components[component_name]
            metadata.status = "inactive"
            metadata.last_active = datetime.now()

            # Clean up relationships
            for deps in self.component_relationships.values():
                deps.discard(component_name)

            # Update stats
            self.stats['components_active'] -= 1

            # Notify about deregistration
            if self.message_broker:
                await self._notify_component_deregistration(
                    component_name,
                    self.component_uuids[component_name]
                )

            logger.info(f"Deregistered component {component_name}")
            return True

        except Exception as e:
            logger.error(f"Component deregistration failed: {str(e)}")
            return False

    async def update_component_status(
            self,
            component_name: str,
            status: str,
            metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update component status and metadata"""
        try:
            if component_name not in self.registered_components:
                return False

            component_meta = self.registered_components[component_name]
            component_meta.status = status
            component_meta.last_active = datetime.now()

            if metadata:
                component_meta.config.update(metadata)

            # Notify about status update
            if self.message_broker:
                await self._notify_component_update(
                    component_name,
                    self.component_uuids[component_name],
                    status,
                    metadata
                )

            return True

        except Exception as e:
            logger.error(f"Status update failed: {str(e)}")
            return False

    def get_component_info(
            self,
            component_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get comprehensive component information"""
        if component_name not in self.registered_components:
            return None

        metadata = self.registered_components[component_name]
        dependencies = self.get_component_dependencies(component_name)
        dependents = self.get_component_dependents(component_name)

        return {
            'name': component_name,
            'uuid': self.component_uuids[component_name],
            'type': metadata.component_type.value,
            'status': metadata.status,
            'created_at': metadata.created_at.isoformat(),
            'last_active': metadata.last_active.isoformat(),
            'dependencies': list(dependencies),
            'dependents': list(dependents),
            'capabilities': list(metadata.capabilities),
            'config': metadata.config
        }

    def get_component_dependencies(
            self,
            component_name: str
    ) -> Set[str]:
        """Get component's dependencies"""
        if component_name not in self.registered_components:
            return set()
        return self.registered_components[component_name].dependencies

    def get_component_dependents(
            self,
            component_name: str
    ) -> Set[str]:
        """Get components that depend on this component"""
        return self.component_relationships.get(component_name, set())

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get comprehensive registry statistics"""
        return {
            'registry_id': self.registry_id,
            'uptime': (datetime.now() - self.startup_time).total_seconds(),
            'total_components': len(self.registered_components),
            'active_components': self.stats['components_active'],
            'registration_errors': self.stats['registration_errors'],
            'component_types': self._get_component_type_counts(),
            'relationship_stats': self._get_relationship_stats()
        }

    def _get_component_type_counts(self) -> Dict[str, int]:
        """Get count of components by type"""
        type_counts = {}
        for metadata in self.registered_components.values():
            type_name = metadata.component_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        return type_counts

    def _get_relationship_stats(self) -> Dict[str, int]:
        """Get relationship statistics"""
        return {
            'total_relationships': sum(
                len(deps) for deps in self.component_relationships.values()
            ),
            'independent_components': len([
                name for name, metadata in self.registered_components.items()
                if not metadata.dependencies and name not in self.component_relationships
            ])
        }

    async def _notify_component_registration(
            self,
            component_name: str,
            component_uuid: str,
            metadata: ComponentMetadata
    ) -> None:
        """Notify about component registration"""
        if not self.message_broker:
            return

        await self.message_broker.publish({
            'type': MessageType.COMPONENT_REGISTERED,
            'component_name': component_name,
            'component_uuid': component_uuid,
            'component_type': metadata.component_type.value,
            'timestamp': datetime.now().isoformat()
        })

    async def _notify_component_deregistration(
            self,
            component_name: str,
            component_uuid: str
    ) -> None:
        """Notify about component deregistration"""
        if not self.message_broker:
            return

        await self.message_broker.publish({
            'type': MessageType.COMPONENT_DEREGISTERED,
            'component_name': component_name,
            'component_uuid': component_uuid,
            'timestamp': datetime.now().isoformat()
        })

    async def _notify_component_update(
            self,
            component_name: str,
            component_uuid: str,
            status: str,
            metadata: Optional[Dict[str, Any]]
    ) -> None:
        """Notify about component status update"""
        if not self.message_broker:
            return

        await self.message_broker.publish({
            'type': MessageType.COMPONENT_UPDATED,
            'component_name': component_name,
            'component_uuid': component_uuid,
            'status': status,
            'metadata': metadata,
            'timestamp': datetime.now().isoformat()
        })