"""
Feature flags package with permission-based access control and high performance.

This package provides a comprehensive feature flag system with:
- File watching for real-time updates
- In-memory caching for fast reads
- Thread-safe operations
- Permission-based access control
- Module ownership system
- Type-safe flag retrieval

Basic usage:
    ```python
    from feature_flags import FeatureFlag, get_manager, PermissionLevel
    
    # Create flags
    DEBUG_MODE = FeatureFlag("debug_mode")
    MAX_CONNECTIONS = FeatureFlag("max_connections")
    
    # Get manager for your module
    manager = get_manager(module_name="my_module")
    
    # Declare flags (as owner)
    manager.declare_flag(DEBUG_MODE, PermissionLevel.READ_WRITE, False, "Enable debug logging")
    manager.declare_flag(MAX_CONNECTIONS, PermissionLevel.READ_ONLY, 100, "Maximum concurrent connections")
    
    # Use flags from other modules
    manager.use_flag(SOME_OTHER_FLAG)
    
    # Get values
    if manager.get_bool(DEBUG_MODE):
        print("Debug mode enabled")
    
    max_conn = manager.get_int(MAX_CONNECTIONS, 50)
    ```
"""

# Core classes
from .feature_flag import FeatureFlag
from .feature_flags_manager import FeatureFlagManager, get_manager
from .permission_types import PermissionLevel, FlagDeclaration, FlagOwnership
from .shared_storage import SharedFlagStorage, get_shared_storage

# Public API
__all__ = [
    # Core classes
    'FeatureFlag',
    'FeatureFlagManager',
    'get_manager',
    
    # Permission system
    'PermissionLevel',
    'FlagDeclaration', 
    'FlagOwnership',
    
    # Storage (advanced usage)
    'SharedFlagStorage',
    'get_shared_storage',
]

# Version info
__version__ = "1.0.0"
__author__ = "Matthew Sheldon"
__description__ = "High-performance feature flags with permission-based access control"
