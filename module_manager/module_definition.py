"""
Module Definition System

Defines the core structures and protocols for Twitch bot modules.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Protocol, Callable, Awaitable, TYPE_CHECKING
from enum import Enum
import asyncio

from feature_flags.feature_flag import FeatureFlag
from feature_flags.permission_types import PermissionLevel
from db.schema_manager import ModuleSchema

if TYPE_CHECKING:
    from feature_flags.feature_flags_manager import FeatureFlagManager
    from db.module_connections import ModuleDatabaseManager


class ModuleStatus(Enum):
    """Status of a module."""
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class CommandDefinition:
    """Defines a Twitch chat command."""
    name: str
    handler: Callable
    description: str = ""
    permission_required: bool = False
    aliases: List[str] = field(default_factory=list)
    cooldown_seconds: float = 0.0


@dataclass
class ModuleConfig:
    """Configuration for a module."""
    enabled_by_default: bool = True
    auto_start: bool = True
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    

class ModuleLifecycle(Protocol):
    """Protocol for module lifecycle management."""
    
    async def on_start(self) -> None:
        """Called when the module is being started."""
        ...
    
    async def on_stop(self) -> None:
        """Called when the module is being stopped."""
        ...
    
    async def on_error(self, error: Exception) -> None:
        """Called when an error occurs in the module."""
        ...


class TwitchModule(ABC):
    """
    Abstract base class for Twitch bot modules.
    
    All bot modules must inherit from this class and implement the required methods.
    """
    
    def __init__(self):
        self.status = ModuleStatus.INACTIVE
        self._error_message: Optional[str] = None
        
        # These will be injected by the module manager during setup
        self.feature_flag_manager: Optional['FeatureFlagManager'] = None
        self.database_manager: Optional['ModuleDatabaseManager'] = None
    
    @property
    @abstractmethod
    def module_name(self) -> str:
        """Return the unique name of this module."""
        pass
    
    @property
    @abstractmethod
    def module_description(self) -> str:
        """Return a description of what this module does."""
        pass
    
    @property
    @abstractmethod
    def module_version(self) -> str:
        """Return the version of this module."""
        pass
    
    @abstractmethod
    def get_feature_flags(self) -> List[tuple[FeatureFlag, PermissionLevel, Any, str]]:
        """Return the feature flags this module declares as (flag, permission, default_value, description)."""
        pass
    
    @abstractmethod
    def get_database_schema(self) -> Optional[ModuleSchema]:
        """Return the database schema this module requires."""
        pass
    
    @abstractmethod
    def get_commands(self) -> List[CommandDefinition]:
        """Return the chat commands this module provides."""
        pass
    
    @abstractmethod
    def get_config(self) -> ModuleConfig:
        """Return the configuration for this module."""
        pass
    
    # Optional lifecycle methods
    async def on_start(self) -> None:
        """Called when the module is being started."""
        pass
    
    async def on_stop(self) -> None:
        """Called when the module is being stopped."""
        pass
    
    async def on_error(self, error: Exception) -> None:
        """Called when an error occurs in the module."""
        self._error_message = str(error)
    
    # Setup methods for dependency injection
    def _inject_managers(self, 
                        feature_flag_manager: 'FeatureFlagManager', 
                        database_manager: 'ModuleDatabaseManager') -> None:
        """
        Inject the feature flag and database managers.
        
        This is called by the module manager during module setup.
        """
        self.feature_flag_manager = feature_flag_manager
        self.database_manager = database_manager
    
    # Status management
    def get_status(self) -> ModuleStatus:
        """Get the current status of the module."""
        return self.status
    
    def get_error_message(self) -> Optional[str]:
        """Get the last error message if the module is in error state."""
        return self._error_message if self.status == ModuleStatus.ERROR else None
    
    def _set_status(self, status: ModuleStatus) -> None:
        """Internal method to set module status."""
        self.status = status
        if status != ModuleStatus.ERROR:
            self._error_message = None


@dataclass
class ModuleDefinition:
    """
    Complete definition of a module including its metadata and runtime instance.
    """
    module: TwitchModule
    feature_flags: List[tuple[FeatureFlag, PermissionLevel]]
    database_schema: Optional[ModuleSchema]
    commands: List[CommandDefinition]
    config: ModuleConfig
    
    @property
    def name(self) -> str:
        """Get the module name."""
        return self.module.module_name
    
    @property
    def description(self) -> str:
        """Get the module description."""
        return self.module.module_description
    
    @property
    def version(self) -> str:
        """Get the module version."""
        return self.module.module_version
    
    @property
    def status(self) -> ModuleStatus:
        """Get the module status."""
        return self.module.get_status()
    
    def get_error_message(self) -> Optional[str]:
        """Get the last error message if the module is in error state."""
        return self.module.get_error_message()
    
    @classmethod
    def from_module(cls, module: TwitchModule) -> 'ModuleDefinition':
        """Create a ModuleDefinition from a TwitchModule instance."""
        return cls(
            module=module,
            feature_flags=module.get_feature_flags(),
            database_schema=module.get_database_schema(),
            commands=module.get_commands(),
            config=module.get_config()
        )
