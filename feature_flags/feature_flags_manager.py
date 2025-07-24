"""
High-performance feature flag manager with permission-based access control.

This module provides the main FeatureFlagManager class that handles
feature flag declaration, usage, and access control across modules.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from .feature_flag import FeatureFlag
from .permission_types import PermissionLevel, FlagDeclaration, FlagOwnership
from .shared_storage import get_shared_storage


class FeatureFlagManager:
    """
    High-performance feature flag manager with file watching and caching.
    
    Features:
    - File watching for real-time updates
    - In-memory caching for fast reads
    - Thread-safe operations
    - Configurable reload debouncing
    - Type-safe flag retrieval
    - Permission-based access control
    - Module ownership system
    - User-friendly JSON format with integrated ownership
    - Shared storage across instances for the same file
    """
    
    def __init__(self, config_path: str = "feature_flags.json", 
                 debounce_seconds: float = 0.1,
                 module_name: Optional[str] = None):
        self.module_name = module_name or "unknown"
        self.config_path = Path(config_path)
        self.debounce_seconds = debounce_seconds
        
        # Get shared storage for this config file
        self._storage = get_shared_storage(self.config_path, debounce_seconds)
        self._storage.add_manager()
        
        # Module-specific state (not shared)
        self._declared_flags: Dict[str, FlagDeclaration] = {}
        self._my_observers: Dict[str, Callable[[str, Any, Any], None]] = {}  # Track this manager's observers

        # Initialize config file if it doesn't exist
        self._ensure_config_exists()

    def declare_flag(self, flag: FeatureFlag, access_permissions: PermissionLevel, 
                    default_value: Any, description: str) -> 'FeatureFlagManager':
        """
        Declare a feature flag as the owning module and specify the access level for non-owner modules.
        
        Args:
            flag: FeatureFlag instance
            access_permissions: Permission level for non-owner modules
            default_value: Default value if flag doesn't exist
            description: Description of the flag (required)
            
        Returns:
            Self for method chaining
            
        Raises:
            PermissionError: If flag is already owned by another module
        """
        flag_name = flag.name
        
        # Check if flag is already owned by another module
        existing_ownership = self._storage.get_ownership_info(flag_name)
        if existing_ownership and existing_ownership.owner_module != self.module_name:
            raise PermissionError(
                f"Flag '{flag_name}' is already owned by module '{existing_ownership.owner_module}'. "
                f"Module '{self.module_name}' cannot declare this flag."
            )
        
        # Claim ownership (since only owners can declare)
        ownership = FlagOwnership(
            owner_module=self.module_name,
            access_permissions=access_permissions
        )
        self._storage.set_ownership_info(flag_name, ownership)
        
        # Store the declaration (module is always owner when declaring)
        declaration = FlagDeclaration(flag, PermissionLevel.OWNER_ONLY, default_value, description)
        self._declared_flags[flag_name] = declaration
        
        # Ensure flag exists in config with default value
        if self._storage.get_flag_value(flag_name) is None:
            self._storage.set_flag_value(flag_name, default_value)
            self._storage.set_flag_description(flag_name, description)
        
        # Save the updated ownership registry
        self._persist_config()
        
        return self

    def use_flag(self, flag: FeatureFlag) -> 'FeatureFlagManager':
        """
        Declare intent to use a flag owned by another module.
        
        Args:
            flag: FeatureFlag instance to use
            
        Returns:
            Self for method chaining
            
        Raises:
            PermissionError: If flag doesn't exist or access is denied
        """
        flag_name = flag.name
        
        # Check if flag exists and get ownership info
        ownership = self._storage.get_ownership_info(flag_name)
        if not ownership:
            raise PermissionError(
                f"Flag '{flag_name}' does not exist or has not been declared by any module."
            )
        
        # Check if we're the owner
        if ownership.owner_module == self.module_name:
            # We own it, so we have full access
            permission = PermissionLevel.OWNER_ONLY
        else:
            # Check what permission non-owners have
            permission = ownership.access_permissions
            if permission == PermissionLevel.OWNER_ONLY:
                raise PermissionError(
                    f"Flag '{flag_name}' is owned by module '{ownership.owner_module}' with OWNER_ONLY access. "
                    f"Module '{self.module_name}' cannot access this flag."
                )
        
        # Store the usage declaration
        descriptions = self._storage.get_descriptions()
        declaration = FlagDeclaration(flag, permission, None, descriptions.get(flag_name, ""))
        self._declared_flags[flag_name] = declaration
        
        return self
    
    def _ensure_config_exists(self):
        """Create default config file if it doesn't exist."""
        if not self.config_path.exists():
            # Create an empty config with metadata
            self._storage.write_config({}, {}, {})
    
    def _persist_config(self):
        """Persist current storage state to file."""
        cache = self._storage.get_cache()
        descriptions = self._storage.get_descriptions()
        ownership_registry = self._storage.get_ownership_registry()
        self._storage.write_config(cache, descriptions, ownership_registry)

    def get_flag(self, flag: FeatureFlag, default: Any = None) -> Any:
        """
        Get feature flag value with high performance.
        
        Args:
            flag: FeatureFlag instance
            default: Default value if flag not found
            
        Returns:
            Flag value or default
        
        Raises:
            PermissionError: If flag not declared or access denied
        """
        flag_name = flag.name
        
        # Check if flag was declared/used by this module
        if flag_name not in self._declared_flags:
            raise PermissionError(
                f"Flag '{flag_name}' must be declared or used before access in module '{self.module_name}'"
            )
        
        declaration = self._declared_flags[flag_name]
        
        # Get value from shared storage, fallback to declared default, then provided default
        value = self._storage.get_flag_value(flag_name)
        if value is None:
            value = declaration.default_value if default is None else default
        
        return value
    
    def get_flag_description(self, flag: FeatureFlag) -> str:
        """Get the description for a feature flag."""
        flag_name = flag.name
        descriptions = self._storage.get_descriptions()
        return descriptions.get(flag_name) or getattr(self._declared_flags.get(flag_name), 'description', "")
    
    def get_bool(self, flag: FeatureFlag, default: bool = False) -> bool:
        """Get boolean feature flag value."""
        value = self.get_flag(flag, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    
    def get_int(self, flag: FeatureFlag, default: int = 0) -> int:
        """Get integer feature flag value."""
        value = self.get_flag(flag, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_float(self, flag: FeatureFlag, default: float = 0.0) -> float:
        """Get float feature flag value."""
        value = self.get_flag(flag, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_string(self, flag: FeatureFlag, default: str = "") -> str:
        """Get string feature flag value."""
        value = self.get_flag(flag, default)
        return str(value) if value is not None else default
    
    def set_flag(self, flag: FeatureFlag, value: Any):
        """
        Set feature flag value and persist to file.
        
        Args:
            flag: FeatureFlag instance
            value: New value for the flag
        
        Raises:
            PermissionError: If insufficient permissions
        """
        flag_name = flag.name
        
        # Check if flag was declared/used by this module
        if flag_name not in self._declared_flags:
            raise PermissionError(
                f"Flag '{flag_name}' must be declared or used before modification in module '{self.module_name}'"
            )
        
        declaration = self._declared_flags[flag_name]
        
        # Check write permissions
        if declaration.permission == PermissionLevel.READ_ONLY:
            raise PermissionError(
                f"Module '{self.module_name}' has read-only access to flag '{flag_name}'"
            )
        
        # Check ownership
        ownership = self._storage.get_ownership_info(flag_name)
        if ownership and ownership.owner_module != self.module_name:
            if ownership.access_permissions == PermissionLevel.OWNER_ONLY:
                raise PermissionError(
                    f"Flag '{flag_name}' is owned by module '{ownership.owner_module}' with OWNER_ONLY access. "
                    f"Module '{self.module_name}' cannot modify this flag."
                )
            elif ownership.access_permissions == PermissionLevel.READ_ONLY:
                raise PermissionError(
                    f"Module '{self.module_name}' has read-only access to flag '{flag_name}' owned by '{ownership.owner_module}'"
                )
        
        # Update shared storage and persist
        self._storage.set_flag_value(flag_name, value)
        self._persist_config()
    
    def add_observer(self, flag: FeatureFlag, callback: Callable[[str, Any, Any], None]):
        """
        Add observer for flag changes.
        
        Args:
            flag: FeatureFlag to observe
            callback: Function called when flag changes (flag_name, old_value, new_value)
        """
        # Check access first
        flag_name = flag.name
        if flag_name not in self._declared_flags:
            raise PermissionError(
                f"Flag '{flag_name}' must be declared or used before observing in module '{self.module_name}'"
            )
        
        # Store reference to our callback
        self._my_observers[flag_name] = callback
        self._storage.add_observer(flag.name, callback)
    
    def remove_observer(self, flag: FeatureFlag):
        """Remove observer for flag."""
        flag_name = flag.name
        if flag_name in self._my_observers:
            callback = self._my_observers[flag_name]
            self._storage.remove_observer(flag_name, callback)
            del self._my_observers[flag_name]
    
    def reload(self):
        """Manually reload configuration from file."""
        self._storage.reload()
    
    def get_declared_flags(self) -> Dict[str, FlagDeclaration]:
        """Get all flags declared by this module."""
        return self._declared_flags.copy()

    def get_ownership_info(self) -> Dict[str, FlagOwnership]:
        """Get ownership information for all flags."""
        return self._storage.get_ownership_registry()
    
    def get_all_flags(self) -> Dict[str, Any]:
        """Get all feature flags as a dictionary."""
        return self._storage.get_cache()
    
    def get_all_flags_with_descriptions(self) -> Dict[str, Dict[str, Any]]:
        """Get all feature flags with their descriptions."""
        cache = self._storage.get_cache()
        descriptions = self._storage.get_descriptions()
        
        result = {}
        for flag_name, value in cache.items():
            result[flag_name] = {
                "value": value,
                "description": descriptions.get(flag_name, "")
            }
        return result
    
    def shutdown(self):
        """Clean shutdown of the manager."""
        self._storage.remove_manager()


# Global manager instances (support multiple modules)
_manager_instances: Dict[str, FeatureFlagManager] = {}


def get_manager(config_path: str = "feature_flags.json", 
                module_name: Optional[str] = None) -> FeatureFlagManager:
    """
    Get feature flag manager instance for a specific module.
    
    Args:
        config_path: Path to the feature flags JSON file
        module_name: Name of the module requesting the manager
        
    Returns:
        FeatureFlagManager instance for the specified module
    """
    global _manager_instances
    
    key = f"{config_path}:{module_name or 'default'}"
    
    if key not in _manager_instances:
        _manager_instances[key] = FeatureFlagManager(config_path, module_name=module_name)
    
    return _manager_instances[key]
