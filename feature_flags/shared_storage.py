"""
Shared storage implementation for feature flags.

This module handles file watching, caching, and thread-safe storage
of feature flag data that can be shared across multiple manager instances.
"""

import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Any, Callable, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .permission_types import FlagOwnership


# Set up logger
logger = logging.getLogger(__name__)


class SharedFileHandler(FileSystemEventHandler):
    """File system event handler for feature flag configuration files."""
    
    def __init__(self, storage: 'SharedFlagStorage'):
        self.storage = storage
        self._last_event_time = 0.0
        self._event_count = 0
        self._startup_grace_period = 5.0  # Suppress spam for first 5 seconds
        self._creation_time = time.time()
    
    def _should_handle_event(self, file_path: str) -> bool:
        """Check if we should handle this file event."""
        target_path = str(self.storage.config_path.absolute())
        event_path = str(Path(file_path).absolute())
        return event_path == target_path
    
    def _should_log_event(self) -> bool:
        """Determine if we should log this event or suppress it."""
        current_time = time.time()
        
        # Suppress events during startup grace period if they're rapid
        if current_time - self._creation_time < self._startup_grace_period:
            if current_time - self._last_event_time < 0.1:  # Events within 100ms
                self._event_count += 1
                if self._event_count > 3:  # After 3 rapid events, suppress logging
                    return False
            else:
                self._event_count = 0  # Reset count if gap is larger
        
        self._last_event_time = current_time
        return True
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and self._should_handle_event(event.src_path):
            if self._should_log_event():
                logger.debug(f"Feature flags file modified: {event.src_path}")
            self.storage._reload_config()
    
    def on_created(self, event):
        """Handle file creation events."""
        # Some editors create new files instead of modifying existing ones
        if not event.is_directory and self._should_handle_event(event.src_path):
            if self._should_log_event():
                logger.debug(f"Feature flags file created: {event.src_path}")
            self.storage._reload_config()
    
    def on_moved(self, event):
        """Handle file move events."""
        # Some editors use atomic writes (move temp file to target)
        if not event.is_directory and self._should_handle_event(event.dest_path):
            if self._should_log_event():
                logger.debug(f"Feature flags file moved (atomic write): {event.dest_path}")
            self.storage._reload_config()


class SharedFlagStorage:
    """Shared storage and file watching for a specific config file."""
    
    def __init__(self, config_path: Path, debounce_seconds: float = 0.2):
        self.config_path = config_path
        self.debounce_seconds = debounce_seconds
        self._cache: Dict[str, Any] = {}
        self._descriptions: Dict[str, str] = {}
        self._ownership_registry: Dict[str, 'FlagOwnership'] = {}  # Shared ownership info
        self._last_reload = 0.0
        self._lock = threading.RLock()
        self._observers: Dict[str, List[Callable[[str, Any, Any], None]]] = {}
        self._manager_count = 0  # Track how many managers are using this storage
        
        # File watching
        self.observer = None
        
        # Load initial configuration
        self._reload_config()
        
        # Set up file watching
        self._setup_file_watcher()
    
    def add_manager(self) -> None:
        """Register a new manager using this storage."""
        with self._lock:
            self._manager_count += 1
    
    def remove_manager(self) -> None:
        """Unregister a manager from this storage."""
        with self._lock:
            self._manager_count -= 1
            if self._manager_count <= 0:
                self._shutdown()
    
    def _setup_file_watcher(self):
        """Set up file system watcher for real-time updates."""
        try:
            self.observer = Observer()
            handler = SharedFileHandler(self)
            watch_directory = str(self.config_path.parent)
            self.observer.schedule(handler, watch_directory, recursive=False)
            self.observer.start()
            logger.debug(f"File watcher started for {self.config_path}")
        except Exception as e:
            logger.warning(f"Could not set up file watcher for {self.config_path}: {e}")
            self.observer = None
    
    def _reload_config(self):
        """Reload configuration from file with debouncing."""
        current_time = time.time()
        
        # More aggressive debouncing to handle rapid editor events
        if current_time - self._last_reload < self.debounce_seconds:
            # Only log debounced events occasionally to reduce log spam
            if current_time - self._last_reload > 0.05:  # Only log if gap > 50ms
                logger.debug(f"Config reload debounced ({current_time - self._last_reload:.2f}s since last reload)")
            return
        
        logger.debug(f"Reloading feature flags from {self.config_path}")
        
        with self._lock:
            self._last_reload = current_time  # Update timestamp before processing
            try:
                if not self.config_path.exists():
                    return
                
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                old_cache = self._cache.copy()
                
                if "flags" in config_data:
                    # Current structured format
                    self._cache = {}
                    self._descriptions = {}
                    self._ownership_registry = {}
                    for flag_name, flag_data in config_data["flags"].items():
                        if isinstance(flag_data, dict) and "value" in flag_data:
                            self._cache[flag_name] = flag_data["value"]
                            if "description" in flag_data:
                                self._descriptions[flag_name] = flag_data["description"]
                            # Load ownership information
                            if "owner_module" in flag_data and "access_permissions" in flag_data:
                                from .permission_types import PermissionLevel
                                self._ownership_registry[flag_name] = FlagOwnership(
                                    owner_module=flag_data["owner_module"],
                                    access_permissions=PermissionLevel(flag_data["access_permissions"])
                                )
                        else:
                            # Fallback for malformed entries
                            self._cache[flag_name] = flag_data
                else:
                    # Empty or invalid config
                    self._cache = {}
                    self._descriptions = {}
                    self._ownership_registry = {}
                
                # Call observers for changed values
                self._notify_observers(old_cache, self._cache)
                
                logger.info(f"Feature flags reloaded successfully, {len(self._cache)} flags in cache")
                
            except Exception as e:
                logger.error(f"Error reloading config from {self.config_path}: {e}")
    
    def _notify_observers(self, old_config: Dict[str, Any], new_config: Dict[str, Any]):
        """Notify observers of configuration changes."""
        for flag_name, callbacks in self._observers.items():
            old_value = old_config.get(flag_name)
            new_value = new_config.get(flag_name)
            
            if old_value != new_value:
                for callback in callbacks:
                    try:
                        callback(flag_name, old_value, new_value)
                    except Exception as e:
                        logger.error(f"Error in observer callback for {flag_name}: {e}")
    
    def write_config(self, flags: Dict[str, Any], descriptions: Dict[str, str], ownership_info: Dict[str, FlagOwnership]):
        """Write configuration with consolidated ownership info in user-friendly format."""
        with self._lock:
            structured_config = {
                "_metadata": {
                    "description": "Feature flags configuration with integrated ownership information",
                    "format_version": "1.0",
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "flags": {}
            }
            
            # Consolidate flags with their values, descriptions, and ownership info
            for flag_name, value in flags.items():
                flag_entry = {"value": value}
                
                # Add description if available
                if flag_name in descriptions and descriptions[flag_name]:
                    flag_entry["description"] = descriptions[flag_name]
                
                # Add ownership information if available
                if flag_name in ownership_info:
                    ownership = ownership_info[flag_name]
                    flag_entry["owner_module"] = ownership.owner_module
                    flag_entry["access_permissions"] = ownership.access_permissions.value
                
                structured_config["flags"][flag_name] = flag_entry
            
            self._write_config_atomic(structured_config)
    
    def _write_config_atomic(self, config: Dict[str, Any]):
        """Write configuration to file atomically."""
        temp_path = self.config_path.with_suffix('.tmp')
        try:
            # Create directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Atomic move
            temp_path.replace(self.config_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to write config to {self.config_path}: {e}")
    
    def get_cache(self) -> Dict[str, Any]:
        """Get the current cache (thread-safe)."""
        with self._lock:
            return self._cache.copy()
    
    def get_descriptions(self) -> Dict[str, str]:
        """Get the current descriptions (thread-safe)."""
        with self._lock:
            return self._descriptions.copy()
    
    def get_flag_value(self, flag_name: str) -> Any:
        """Get a specific flag value (thread-safe)."""
        with self._lock:
            return self._cache.get(flag_name)
    
    def set_flag_value(self, flag_name: str, value: Any):
        """Set a specific flag value (thread-safe)."""
        with self._lock:
            old_value = self._cache.get(flag_name)
            self._cache[flag_name] = value
            
            # Call observers immediately when value changes
            if old_value != value:
                self._notify_observer(flag_name, old_value, value)
    
    def _notify_observer(self, flag_name: str, old_value: Any, new_value: Any):
        """Notify all observers for a specific flag (must be called within lock)."""
        if flag_name in self._observers:
            for callback in self._observers[flag_name]:
                try:
                    callback(flag_name, old_value, new_value)
                except Exception as e:
                    logger.error(f"Error in observer callback for {flag_name}: {e}")
    
    def set_flag_description(self, flag_name: str, description: str):
        """Set a specific flag description (thread-safe)."""
        with self._lock:
            self._descriptions[flag_name] = description
    
    def get_ownership_registry(self) -> Dict[str, 'FlagOwnership']:
        """Get the current ownership registry (thread-safe)."""
        with self._lock:
            return self._ownership_registry.copy()
    
    def set_ownership_info(self, flag_name: str, ownership: 'FlagOwnership'):
        """Set ownership info for a flag (thread-safe)."""
        with self._lock:
            self._ownership_registry[flag_name] = ownership
    
    def get_ownership_info(self, flag_name: str) -> 'FlagOwnership':
        """Get ownership info for a specific flag (thread-safe)."""
        with self._lock:
            return self._ownership_registry.get(flag_name)
    
    def add_observer(self, flag_name: str, callback: Callable[[str, Any, Any], None]):
        """Add observer for flag changes."""
        with self._lock:
            if flag_name not in self._observers:
                self._observers[flag_name] = []
            self._observers[flag_name].append(callback)
    
    def remove_observer(self, flag_name: str, callback: Callable[[str, Any, Any], None] = None):
        """Remove observer for flag."""
        with self._lock:
            if flag_name in self._observers:
                if callback:
                    # Remove specific callback
                    try:
                        self._observers[flag_name].remove(callback)
                        if not self._observers[flag_name]:  # Remove empty list
                            del self._observers[flag_name]
                    except ValueError:
                        pass  # Callback not found
                else:
                    # Remove all observers for this flag
                    del self._observers[flag_name]
    
    def reload(self):
        """Manually reload configuration from file."""
        self._reload_config()
    
    def _shutdown(self):
        """Clean shutdown of shared storage."""
        if self.observer:
            self.observer.stop()
            self.observer.join()


# Global shared storage instances
_shared_storages: Dict[str, SharedFlagStorage] = {}
_storage_lock = threading.Lock()


def get_shared_storage(config_path: Path, debounce_seconds: float) -> SharedFlagStorage:
    """Get or create shared storage for a config file."""
    global _shared_storages, _storage_lock
    
    path_str = str(config_path.resolve())
    
    with _storage_lock:
        if path_str not in _shared_storages:
            _shared_storages[path_str] = SharedFlagStorage(config_path, debounce_seconds)
        return _shared_storages[path_str]
