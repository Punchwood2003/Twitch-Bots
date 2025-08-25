"""
Module Manager

Main orchestrator for managing Twitch bot modules lifecycle, dependencies,
and integration with feature flags and database systems.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from contextlib import asynccontextmanager

from feature_flags.feature_flags_manager import FeatureFlagManager
from db.schema_manager import SchemaManager
from db.module_connections import ModuleDatabaseManager
from .module_definition import ModuleDefinition, ModuleStatus, TwitchModule, CommandDefinition
from .module_registry import ModuleRegistry

logger = logging.getLogger(__name__)


class ModuleManager:
    """
    Main manager for Twitch bot modules.
    
    Handles module lifecycle, dependency management, feature flag integration,
    database schema management, and command registration.
    """
    
    def __init__(self, 
                 feature_flag_manager: FeatureFlagManager,
                 schema_manager: SchemaManager,
                 registry_file: str = "module_registry.json"):
        self.feature_flag_manager = feature_flag_manager
        self.schema_manager = schema_manager
        self.registry = ModuleRegistry(registry_file)
        
        # Runtime state
        self._running_modules: Set[str] = set()
        self._module_tasks: Dict[str, asyncio.Task] = {}
        self._registered_commands: Dict[str, CommandDefinition] = {}
        self._startup_complete = False
        
        # Module managers (one per module)
        self._module_feature_managers: Dict[str, FeatureFlagManager] = {}
        self._module_database_managers: Dict[str, ModuleDatabaseManager] = {}
        
        # Event callbacks
        self._on_module_started_callbacks = []
        self._on_module_stopped_callbacks = []
        self._on_module_error_callbacks = []
    
    async def initialize(self) -> None:
        """Initialize the module manager and prepare systems."""
        logger.info("Initializing Module Manager...")
        
        # Initialize database schemas for all registered modules
        await self._initialize_database_schemas()
        
        # Initialize feature flags for all registered modules
        self._initialize_feature_flags()
        
        logger.info("Module Manager initialized successfully")
    
    def register_module(self, module: TwitchModule) -> None:
        """
        Register a new module.
        
        Args:
            module: The TwitchModule instance to register
        """
        try:
            # Create dedicated managers for this module
            module_feature_manager = FeatureFlagManager(
                config_path="feature_flags.json",
                module_name=module.module_name
            )
            module_database_manager = ModuleDatabaseManager(module.module_name)
            
            # Store the managers
            self._module_feature_managers[module.module_name] = module_feature_manager
            self._module_database_managers[module.module_name] = module_database_manager
            
            # Inject managers into the module
            module._inject_managers(module_feature_manager, module_database_manager)
            
            # Register with registry
            self.registry.register_module(module)
            
            # Always set up feature flags immediately when module is registered
            self._setup_module_feature_flags(module.module_name)
            
            # Always set up database schema immediately when module is registered
            asyncio.create_task(self._setup_module_database_schema(module.module_name))
            
            logger.info(f"Successfully registered module: {module.module_name}")
        except Exception as e:
            logger.error(f"Failed to register module {module.module_name}: {e}")
            raise
    
    def unregister_module(self, module_name: str) -> bool:
        """
        Unregister a module.
        
        Args:
            module_name: Name of the module to unregister
            
        Returns:
            True if successful, False if module not found
        """
        try:
            # Stop the module if it's running
            if module_name in self._running_modules:
                asyncio.create_task(self.stop_module(module_name))
            
            # Unregister commands
            self._unregister_module_commands(module_name)
            
            # Clean up module managers
            if module_name in self._module_database_managers:
                db_manager = self._module_database_managers[module_name]
                asyncio.create_task(db_manager.cleanup())
                del self._module_database_managers[module_name]
            
            if module_name in self._module_feature_managers:
                del self._module_feature_managers[module_name]
            
            # Unregister from registry
            result = self.registry.unregister_module(module_name)
            
            if result:
                logger.info(f"Successfully unregistered module: {module_name}")
            
            return result
        except Exception as e:
            logger.error(f"Failed to unregister module {module_name}: {e}")
            return False
    
    async def start_module(self, module_name: str, force: bool = False) -> bool:
        """
        Start a specific module.
        
        Args:
            module_name: Name of the module to start
            force: Whether to force start even if dependencies aren't running
            
        Returns:
            True if started successfully, False otherwise
        """
        module_def = self.registry.get_module(module_name)
        if not module_def:
            logger.error(f"Module '{module_name}' not found")
            return False
        
        if not self.registry.is_module_enabled(module_name):
            logger.warning(f"Module '{module_name}' is disabled")
            return False
        
        if module_name in self._running_modules:
            logger.info(f"Module '{module_name}' is already running")
            return True
        
        try:
            # Check dependencies
            if not force:
                for dep in module_def.config.dependencies:
                    if dep not in self._running_modules:
                        if not await self.start_module(dep):
                            logger.error(f"Failed to start dependency '{dep}' for module '{module_name}'")
                            return False
            
            # Set status to starting
            module_def.module._set_status(ModuleStatus.STARTING)
            
            # Setup database connection for the module
            if module_name in self._module_database_managers:
                await self._module_database_managers[module_name].setup()
            
            # Register commands
            self._register_module_commands(module_def)
            
            # Start the module
            await module_def.module.on_start()
            
            # Set status to active
            module_def.module._set_status(ModuleStatus.ACTIVE)
            self._running_modules.add(module_name)
            
            # Update stats
            stats = self.registry._module_states.get(module_name, {})
            stats['start_count'] = stats.get('start_count', 0) + 1
            self.registry.update_module_stats(module_name, **stats)
            
            # Notify callbacks
            for callback in self._on_module_started_callbacks:
                try:
                    await callback(module_name, module_def)
                except Exception as e:
                    logger.error(f"Error in module started callback: {e}")
            
            logger.info(f"Successfully started module: {module_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start module '{module_name}': {e}")
            module_def.module._set_status(ModuleStatus.ERROR)
            await module_def.module.on_error(e)
            
            # Update error stats
            self.registry.update_module_stats(module_name, last_error=str(e))
            
            # Notify error callbacks
            for callback in self._on_module_error_callbacks:
                try:
                    await callback(module_name, module_def, e)
                except Exception as callback_error:
                    logger.error(f"Error in module error callback: {callback_error}")
            
            return False
    
    async def stop_module(self, module_name: str, force: bool = False) -> bool:
        """
        Stop a specific module.
        
        Args:
            module_name: Name of the module to stop
            force: Whether to force stop even if other modules depend on it
            
        Returns:
            True if stopped successfully, False otherwise
        """
        module_def = self.registry.get_module(module_name)
        if not module_def:
            logger.error(f"Module '{module_name}' not found")
            return False
        
        if module_name not in self._running_modules:
            logger.info(f"Module '{module_name}' is not running")
            return True
        
        try:
            # Check dependents
            if not force:
                dependents = [dep for dep in self.registry.get_dependents(module_name) 
                             if dep in self._running_modules]
                if dependents:
                    logger.warning(f"Cannot stop '{module_name}': modules {dependents} depend on it")
                    return False
            
            # Set status to stopping
            module_def.module._set_status(ModuleStatus.STOPPING)
            
            # Stop the module
            await module_def.module.on_stop()
            
            # Clean up database connection
            if module_name in self._module_database_managers:
                await self._module_database_managers[module_name].cleanup()
            
            # Unregister commands
            self._unregister_module_commands(module_name)
            
            # Cancel module task if exists
            if module_name in self._module_tasks:
                self._module_tasks[module_name].cancel()
                del self._module_tasks[module_name]
            
            # Set status to inactive
            module_def.module._set_status(ModuleStatus.INACTIVE)
            self._running_modules.discard(module_name)
            
            # Notify callbacks
            for callback in self._on_module_stopped_callbacks:
                try:
                    await callback(module_name, module_def)
                except Exception as e:
                    logger.error(f"Error in module stopped callback: {e}")
            
            logger.info(f"Successfully stopped module: {module_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop module '{module_name}': {e}")
            module_def.module._set_status(ModuleStatus.ERROR)
            await module_def.module.on_error(e)
            return False
    
    async def restart_module(self, module_name: str) -> bool:
        """
        Restart a specific module.
        
        Args:
            module_name: Name of the module to restart
            
        Returns:
            True if restarted successfully, False otherwise
        """
        if await self.stop_module(module_name):
            return await self.start_module(module_name)
        return False
    
    async def start_auto_start_modules(self) -> List[str]:
        """
        Start all modules that are configured to auto-start.
        
        Returns:
            List of modules that were successfully started
        """
        auto_start_modules = self.registry.get_auto_start_modules()
        
        # Resolve start order based on dependencies
        try:
            start_order = self.registry.resolve_start_order(auto_start_modules)
        except ValueError as e:
            logger.error(f"Failed to resolve module start order: {e}")
            return []
        
        started_modules = []
        
        for module_name in start_order:
            if await self.start_module(module_name):
                started_modules.append(module_name)
            else:
                logger.warning(f"Failed to auto-start module: {module_name}")
        
        self._startup_complete = True
        logger.info(f"Auto-started modules: {started_modules}")
        return started_modules
    
    async def stop_all_modules(self) -> None:
        """Stop all running modules."""
        # Stop in reverse dependency order
        running_modules = list(self._running_modules)
        try:
            stop_order = list(reversed(self.registry.resolve_start_order(running_modules)))
        except ValueError:
            # If there are circular dependencies, just stop in reverse order
            stop_order = list(reversed(running_modules))
        
        for module_name in stop_order:
            await self.stop_module(module_name, force=True)
    
    def enable_module(self, module_name: str) -> bool:
        """Enable a module."""
        return self.registry.set_module_enabled(module_name, True)
    
    def disable_module(self, module_name: str) -> bool:
        """Disable a module."""
        # Stop the module if it's running
        if module_name in self._running_modules:
            asyncio.create_task(self.stop_module(module_name))
        
        return self.registry.set_module_enabled(module_name, False)
    
    def get_module_info(self, module_name: str) -> Optional[Dict]:
        """Get comprehensive information about a module."""
        return self.registry.get_module_info(module_name)
    
    def get_all_modules_info(self) -> Dict[str, Dict]:
        """Get information about all registered modules."""
        return {
            name: self.registry.get_module_info(name)
            for name in self.registry.get_all_modules().keys()
        }
    
    def get_running_modules(self) -> List[str]:
        """Get list of currently running modules."""
        return list(self._running_modules)
    
    def get_registered_commands(self) -> Dict[str, CommandDefinition]:
        """Get all registered commands from running modules."""
        return self._registered_commands.copy()
    
    def is_module_running(self, module_name: str) -> bool:
        """Check if a module is currently running."""
        return module_name in self._running_modules
    
    # Event callbacks
    def on_module_started(self, callback):
        """Register a callback for when a module starts."""
        self._on_module_started_callbacks.append(callback)
    
    def on_module_stopped(self, callback):
        """Register a callback for when a module stops."""
        self._on_module_stopped_callbacks.append(callback)
    
    def on_module_error(self, callback):
        """Register a callback for when a module encounters an error."""
        self._on_module_error_callbacks.append(callback)
    
    # Private methods
    async def _initialize_database_schemas(self) -> None:
        """Initialize database schemas for all registered modules."""
        for module_name, module_def in self.registry.get_all_modules().items():
            await self._setup_module_database_schema(module_name)
    
    async def _setup_module_database_schema(self, module_name: str) -> None:
        """Set up database schema for a specific module."""
        module_def = self.registry.get_module(module_name)
        if not module_def:
            return
        
        # Check if module has a database schema - it's optional
        schema = module_def.database_schema
        if schema is None or (hasattr(schema, '__len__') and len(schema) == 0):
            logger.debug(f"Module '{module_name}' has no database schema - skipping database setup")
            return
        
        try:
            self.schema_manager.declare_schema(module_name, schema)
            logger.debug(f"Set up database schema for module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to set up database schema for module '{module_name}': {e}")
    
    def _initialize_feature_flags(self) -> None:
        """Initialize feature flags for all registered modules."""
        for module_name in self.registry.get_all_modules().keys():
            self._setup_module_feature_flags(module_name)
    
    def _setup_module_feature_flags(self, module_name: str) -> None:
        """Set up feature flags for a specific module."""
        module_def = self.registry.get_module(module_name)
        if not module_def:
            return
        
        # Get the module's dedicated feature flag manager
        module_flag_manager = self._module_feature_managers.get(module_name)
        if not module_flag_manager:
            logger.error(f"No feature flag manager found for module: {module_name}")
            return
        
        try:
            for flag, permission, default_value, description in module_def.feature_flags:
                module_flag_manager.declare_flag(flag, permission, default_value, description)
            logger.debug(f"Set up feature flags for module: {module_name}")
        except Exception as e:
            logger.error(f"Failed to set up feature flags for module '{module_name}': {e}")
    
    def _register_module_commands(self, module_def: ModuleDefinition) -> None:
        """Register commands for a module."""
        for command in module_def.commands:
            # Check for command name conflicts
            if command.name in self._registered_commands:
                logger.warning(f"Command '{command.name}' already registered, skipping")
                continue
            
            self._registered_commands[command.name] = command
            
            # Register aliases too
            for alias in command.aliases:
                if alias not in self._registered_commands:
                    self._registered_commands[alias] = command
        
        logger.debug(f"Registered {len(module_def.commands)} commands for module: {module_def.name}")
    
    def _unregister_module_commands(self, module_name: str) -> None:
        """Unregister commands for a module."""
        module_def = self.registry.get_module(module_name)
        if not module_def:
            return
        
        commands_to_remove = []
        for command_name, command_def in self._registered_commands.items():
            # Find commands that belong to this module
            for module_command in module_def.commands:
                if (command_def.name == module_command.name or 
                    command_name in module_command.aliases):
                    commands_to_remove.append(command_name)
                    break
        
        for command_name in commands_to_remove:
            del self._registered_commands[command_name]
        
        logger.debug(f"Unregistered {len(commands_to_remove)} commands for module: {module_name}")
    
    async def shutdown(self) -> None:
        """Shutdown the module manager and all modules."""
        logger.info("Shutting down Module Manager...")
        await self.stop_all_modules()
        
        # Clean up all module database managers
        for module_name, db_manager in self._module_database_managers.items():
            try:
                await db_manager.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up database manager for {module_name}: {e}")
        
        self._module_database_managers.clear()
        self._module_feature_managers.clear()
        
        logger.info("Module Manager shutdown complete")
