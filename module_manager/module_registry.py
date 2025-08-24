"""
Module Registry

Handles discovery, registration, and metadata management of Twitch bot modules.
"""

import json
import importlib
import importlib.util
import pkgutil
from pathlib import Path
from typing import Dict, List, Set, Optional, Type
from dataclasses import asdict
import logging

from .module_definition import ModuleDefinition, TwitchModule, ModuleStatus

logger = logging.getLogger(__name__)


class ModuleRegistry:
    """
    Registry for managing Twitch bot modules.
    
    Handles module discovery, registration, dependency resolution,
    and persistence of module states.
    """
    
    def __init__(self, registry_file: str = "module_registry.json"):
        self.registry_file = Path(registry_file)
        self._modules: Dict[str, ModuleDefinition] = {}
        self._module_states: Dict[str, Dict] = {}
        
        # Load existing registry
        self._load_registry()
    
    def register_module(self, module: TwitchModule) -> None:
        """
        Register a new module with the registry.
        
        Args:
            module: The TwitchModule instance to register
            
        Raises:
            ValueError: If a module with the same name is already registered
        """
        module_def = ModuleDefinition.from_module(module)
        
        if module_def.name in self._modules:
            raise ValueError(f"Module '{module_def.name}' is already registered")
        
        # Validate dependencies
        for dep in module_def.config.dependencies:
            if dep not in self._modules:
                logger.warning(f"Module '{module_def.name}' depends on '{dep}' which is not registered")
        
        self._modules[module_def.name] = module_def
        
        # Initialize state if not exists
        if module_def.name not in self._module_states:
            self._module_states[module_def.name] = {
                'enabled': module_def.config.enabled_by_default,
                'auto_start': module_def.config.auto_start,
                'last_error': None,
                'start_count': 0
            }
        
        logger.info(f"Registered module: {module_def.name} v{module_def.version}")
        self._save_registry()
    
    def unregister_module(self, module_name: str) -> bool:
        """
        Unregister a module from the registry.
        
        Args:
            module_name: Name of the module to unregister
            
        Returns:
            True if module was unregistered, False if not found
        """
        if module_name not in self._modules:
            return False
        
        # Check if any other modules depend on this one
        dependents = self.get_dependents(module_name)
        if dependents:
            raise ValueError(f"Cannot unregister '{module_name}': modules {dependents} depend on it")
        
        del self._modules[module_name]
        logger.info(f"Unregistered module: {module_name}")
        self._save_registry()
        return True
    
    def get_module(self, module_name: str) -> Optional[ModuleDefinition]:
        """Get a module definition by name."""
        return self._modules.get(module_name)
    
    def get_all_modules(self) -> Dict[str, ModuleDefinition]:
        """Get all registered modules."""
        return self._modules.copy()
    
    def get_enabled_modules(self) -> Dict[str, ModuleDefinition]:
        """Get all enabled modules."""
        return {
            name: module for name, module in self._modules.items()
            if self._module_states.get(name, {}).get('enabled', False)
        }
    
    def get_auto_start_modules(self) -> List[str]:
        """Get list of modules that should auto-start."""
        return [
            name for name, state in self._module_states.items()
            if state.get('enabled', False) and state.get('auto_start', False)
            and name in self._modules
        ]
    
    def set_module_enabled(self, module_name: str, enabled: bool) -> bool:
        """
        Enable or disable a module.
        
        Args:
            module_name: Name of the module
            enabled: Whether to enable or disable the module
            
        Returns:
            True if state was changed, False if module not found
        """
        if module_name not in self._modules:
            return False
        
        if module_name not in self._module_states:
            self._module_states[module_name] = {}
        
        self._module_states[module_name]['enabled'] = enabled
        logger.info(f"Module '{module_name}' {'enabled' if enabled else 'disabled'}")
        self._save_registry()
        return True
    
    def set_module_auto_start(self, module_name: str, auto_start: bool) -> bool:
        """
        Set whether a module should auto-start.
        
        Args:
            module_name: Name of the module
            auto_start: Whether the module should auto-start
            
        Returns:
            True if state was changed, False if module not found
        """
        if module_name not in self._modules:
            return False
        
        if module_name not in self._module_states:
            self._module_states[module_name] = {}
        
        self._module_states[module_name]['auto_start'] = auto_start
        self._save_registry()
        return True
    
    def is_module_enabled(self, module_name: str) -> bool:
        """Check if a module is enabled."""
        return self._module_states.get(module_name, {}).get('enabled', False)
    
    def get_dependencies(self, module_name: str) -> List[str]:
        """Get the dependencies of a module."""
        module = self._modules.get(module_name)
        return module.config.dependencies if module else []
    
    def get_dependents(self, module_name: str) -> List[str]:
        """Get modules that depend on the given module."""
        dependents = []
        for name, module in self._modules.items():
            if module_name in module.config.dependencies:
                dependents.append(name)
        return dependents
    
    def resolve_start_order(self, module_names: List[str]) -> List[str]:
        """
        Resolve the order in which modules should be started based on dependencies.
        
        Args:
            module_names: List of module names to start
            
        Returns:
            List of module names in the order they should be started
            
        Raises:
            ValueError: If there are circular dependencies
        """
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(name: str):
            if name in temp_visited:
                raise ValueError(f"Circular dependency detected involving module '{name}'")
            if name in visited:
                return
            
            temp_visited.add(name)
            
            # Visit dependencies first
            if name in self._modules:
                for dep in self._modules[name].config.dependencies:
                    if dep in module_names:  # Only include dependencies that are in our start list
                        visit(dep)
            
            temp_visited.remove(name)
            visited.add(name)
            result.append(name)
        
        for name in module_names:
            if name not in visited:
                visit(name)
        
        return result
    
    def discover_modules(self, search_paths: List[str] = None) -> List[str]:
        """
        Discover modules in specified paths.
        
        Args:
            search_paths: List of paths to search for modules
            
        Returns:
            List of discovered module names
        """
        if search_paths is None:
            search_paths = ['.']
        
        discovered = []
        
        for search_path in search_paths:
            path = Path(search_path)
            if not path.exists():
                continue
            
            # Look for Python packages/modules
            for item in path.iterdir():
                curr_file = item / '__init__.py'
                if item.is_dir() and (curr_file).exists():
                    # Try to import and check for TwitchModule classes
                    try:
                        module_name = item.name
                        spec = importlib.util.spec_from_file_location(
                            module_name, 
                            curr_file
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            
                            # Look for TwitchModule subclasses
                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if (isinstance(attr, type) and 
                                    issubclass(attr, TwitchModule) and 
                                    attr is not TwitchModule):
                                    discovered.append(f"{module_name}.{attr_name}")
                    except Exception as e:
                        logger.warning(f"Failed to discover modules in {item}: {e}")
        
        return discovered
    
    def get_module_info(self, module_name: str) -> Optional[Dict]:
        """Get comprehensive information about a module."""
        module = self._modules.get(module_name)
        if not module:
            return None
        
        state = self._module_states.get(module_name, {})
        
        return {
            'name': module.name,
            'description': module.description,
            'version': module.version,
            'status': module.status.value,
            'enabled': state.get('enabled', False),
            'auto_start': state.get('auto_start', False),
            'dependencies': module.config.dependencies,
            'dependents': self.get_dependents(module_name),
            'feature_flags_count': len(module.feature_flags),
            'commands_count': len(module.commands),
            'has_database_schema': module.database_schema is not None,
            'last_error': module.get_error_message() or state.get('last_error'),
            'start_count': state.get('start_count', 0)
        }
    
    def update_module_stats(self, module_name: str, **stats) -> None:
        """Update statistics for a module."""
        if module_name not in self._module_states:
            self._module_states[module_name] = {}
        
        self._module_states[module_name].update(stats)
        self._save_registry()
    
    def _load_registry(self) -> None:
        """Load registry from file."""
        if not self.registry_file.exists():
            return
        
        try:
            with open(self.registry_file, 'r') as f:
                data = json.load(f)
                self._module_states = data.get('module_states', {})
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
    
    def _save_registry(self) -> None:
        """Save registry to file."""
        try:
            data = {
                'module_states': self._module_states,
                'modules': {
                    name: {
                        'name': module.name,
                        'description': module.description,
                        'version': module.version,
                        'dependencies': module.config.dependencies
                    }
                    for name, module in self._modules.items()
                }
            }
            
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
