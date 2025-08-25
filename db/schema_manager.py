"""
Modular Database Schema Manager

Manages database schemas in a modular way, allowing each bot module
to register its own tables, indexes, and migrations dynamically.
"""

import asyncio
import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Protocol
from dataclasses import dataclass
import asyncpg

# Set up logger
logger = logging.getLogger(__name__)
from .config import get_database_config


@dataclass
class TableDefinition:
    """Represents a table definition from a module."""
    name: str
    sql: str
    module: str
    dependencies: List[str] = None  # Tables this depends on
    indexes: List[str] = None


@dataclass
class ModuleSchema:
    """Complete schema definition for a bot module."""
    module_name: str
    tables: List[TableDefinition]
    indexes: List[str] = None
    initial_data: List[str] = None  # SQL for initial data
    
    
class SchemaProvider(Protocol):
    """Protocol that bot modules must implement to provide schema."""
    
    def get_schema(self) -> ModuleSchema:
        """Return the module's schema definition."""
        ...


class SchemaManager:
    """Manages database schemas across all bot modules."""
    
    def __init__(self):
        self.registered_modules: Dict[str, ModuleSchema] = {}
        self.config = get_database_config()
        self._auto_sync = True  # Automatically sync schemas when declared
    
    def declare_schema(self, module_name: str, schema: ModuleSchema) -> None:
        """
        Declare a module's schema (called by modules themselves).
        
        This is the main entry point for modules to register their schemas.
        If auto_sync is enabled, the schema will be created immediately.
        """
        # Validate schema
        if not module_name:
            raise ValueError("Module name cannot be empty")
        if not schema.tables:
            raise ValueError(f"Module {module_name} must define at least one table")
        
        # Register the schema
        self.registered_modules[module_name] = schema
        logger.info(f"Schema declared for module: {module_name}")
        
        # Auto-sync if enabled (handle async context safely)
        if self._auto_sync:
            try:
                # Try to create task if we're in an async context
                loop = asyncio.get_running_loop()
                loop.create_task(self._sync_module_schema(module_name))
            except RuntimeError:
                # No running event loop, schedule for later or sync manually
                logger.info(f"Schema for {module_name} registered. Run sync_all_schemas() to apply changes.")
                # Store for later sync
                if not hasattr(self, '_pending_sync'):
                    self._pending_sync = set()
                self._pending_sync.add(module_name)
    
    async def _sync_module_schema(self, module_name: str) -> bool:
        """Sync a specific module's schema to the database."""
        try:
            schema = self.registered_modules.get(module_name)
            if not schema:
                logger.warning(f"Module {module_name} not found for sync")
                return False
            
            # Check dependencies first
            missing_deps = await self._check_dependencies(schema)
            if missing_deps:
                logger.warning(f"Module {module_name} has missing dependencies: {missing_deps}")
                logger.warning(f"Deferring schema creation until dependencies are available")
                return False
            
            conn = await asyncpg.connect(
                host=self.config.db_host,
                port=self.config.db_port,
                user=self.config.db_user,
                password=self.config.db_password,
                database=self.config.db_name,
            )
            
            logger.info(f"Syncing schema for module: {module_name}")
            
            # Create tables
            for table in schema.tables:
                logger.debug(f"Creating table: {table.name}")
                await conn.execute(table.sql)
            
            # Create indexes
            if schema.indexes:
                logger.debug(f"Creating indexes for {module_name}")
                for index_sql in schema.indexes:
                    await conn.execute(index_sql)
            
            # Insert initial data
            if schema.initial_data:
                logger.debug(f"Inserting initial data for {module_name}")
                for data_sql in schema.initial_data:
                    await conn.execute(data_sql)
            
            await conn.close()
            logger.info(f"Module {module_name} schema synced successfully")
            
            # Try to sync any dependent modules that were waiting
            await self._sync_waiting_modules()
            
            return True
            
        except Exception as e:
            logger.error(f"Schema sync failed for module {module_name}: {e}")
            return False
    
    async def _check_dependencies(self, schema: ModuleSchema) -> List[str]:
        """Check if all table dependencies exist in the database."""
        if not any(table.dependencies for table in schema.tables):
            return []  # No dependencies
        
        try:
            conn = await asyncpg.connect(
                host=self.config.db_host,
                port=self.config.db_port,
                user=self.config.db_user,
                password=self.config.db_password,
                database=self.config.db_name,
            )
            
            # Get existing tables
            existing_tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            existing_table_names = {row['table_name'] for row in existing_tables}
            await conn.close()
            
            # Check dependencies
            missing_deps = []
            for table in schema.tables:
                if table.dependencies:
                    for dep in table.dependencies:
                        if dep not in existing_table_names:
                            missing_deps.append(dep)
            
            return missing_deps
            
        except Exception:
            # If we can't check dependencies, assume they're missing
            all_deps = []
            for table in schema.tables:
                if table.dependencies:
                    all_deps.extend(table.dependencies)
            return all_deps
    
    async def _sync_waiting_modules(self) -> None:
        """Try to sync modules that were waiting for dependencies."""
        for module_name in list(self.registered_modules.keys()):
            schema = self.registered_modules[module_name]
            missing_deps = await self._check_dependencies(schema)
            if not missing_deps:
                # Dependencies now available, try to sync
                await self._sync_module_schema(module_name)
    
    def set_auto_sync(self, enabled: bool) -> None:
        """Enable or disable automatic schema synchronization."""
        self._auto_sync = enabled
        logger.info(f"Auto-sync {'enabled' if enabled else 'disabled'}")
    
    def register_module(self, module_name: str, schema: ModuleSchema) -> None:
        """
        Register a module's schema (legacy method for backwards compatibility).
        
        Prefer using declare_schema() instead.
        """
        logger.warning(f"Using legacy register_module. Consider using declare_schema() instead.")
        self.declare_schema(module_name, schema)
    
    def discover_modules(self, base_path: str = "modules") -> None:
        """Auto-discover modules with schema definitions."""
        base_dir = Path(base_path)
        if not base_dir.exists():
            logger.warning(f"Module directory {base_path} does not exist")
            return
        
        for module_path in base_dir.iterdir():
            if module_path.is_dir() and (module_path / "__init__.py").exists():
                try:
                    module_name = f"{base_path}.{module_path.name}"
                    module = importlib.import_module(module_name)
                    
                    # Look for schema provider
                    if hasattr(module, 'get_schema'):
                        schema = module.get_schema()
                        self.register_module(module_path.name, schema)
                        
                except Exception as e:
                    logger.warning(f"Failed to load module {module_path.name}: {e}")
    
    def get_dependency_order(self) -> List[str]:
        """Calculate proper table creation order based on dependencies."""
        ordered = []
        remaining = list(self.registered_modules.keys())
        
        # Simple dependency resolution (could be enhanced with topological sort)
        while remaining:
            for module_name in remaining[:]:
                schema = self.registered_modules[module_name]
                
                # Check if all dependencies are satisfied
                all_deps_satisfied = True
                for table in schema.tables:
                    if table.dependencies:
                        for dep in table.dependencies:
                            if not any(dep in [t.name for s in self.registered_modules.values() 
                                             for t in s.tables if s.module_name in ordered]):
                                all_deps_satisfied = False
                                break
                
                if all_deps_satisfied:
                    ordered.append(module_name)
                    remaining.remove(module_name)
                    break
            else:
                # If we can't resolve dependencies, add remaining modules anyway
                ordered.extend(remaining)
                break
        
        return ordered
    
    async def create_schemas(self, modules: Optional[List[str]] = None) -> bool:
        """Create database schemas for specified modules (or all if None)."""
        try:
            conn = await asyncpg.connect(
                host=self.config.db_host,
                port=self.config.db_port,
                user=self.config.db_user,
                password=self.config.db_password,
                database=self.config.db_name,
            )
            
            target_modules = modules or self.get_dependency_order()
            
            print(f"🏗️  Creating schemas for modules: {', '.join(target_modules)}")
            
            for module_name in target_modules:
                if module_name not in self.registered_modules:
                    print(f"⚠️  Module {module_name} not registered, skipping")
                    continue
                
                schema = self.registered_modules[module_name]
                print(f"\n📦 Processing module: {module_name}")
                
                # Create tables
                for table in schema.tables:
                    print(f"   🔨 Creating table: {table.name}")
                    await conn.execute(table.sql)
                
                # Create indexes
                if schema.indexes:
                    print(f"   📇 Creating indexes for {module_name}")
                    for index_sql in schema.indexes:
                        await conn.execute(index_sql)
                
                # Insert initial data
                if schema.initial_data:
                    print(f"   📊 Inserting initial data for {module_name}")
                    for data_sql in schema.initial_data:
                        await conn.execute(data_sql)
                
                print(f"   ✅ Module {module_name} schema complete")
            
            await conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Schema creation failed: {e}")
            return False
    
    async def validate_schemas(self) -> Dict[str, List[str]]:
        """Validate that all registered schemas exist in the database."""
        try:
            conn = await asyncpg.connect(
                host=self.config.db_host,
                port=self.config.db_port,
                user=self.config.db_user,
                password=self.config.db_password,
                database=self.config.db_name,
            )
            
            # Get existing tables
            existing_tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            existing_table_names = {row['table_name'] for row in existing_tables}
            
            validation_results = {}
            
            for module_name, schema in self.registered_modules.items():
                missing_tables = []
                for table in schema.tables:
                    if table.name not in existing_table_names:
                        missing_tables.append(table.name)
                
                validation_results[module_name] = missing_tables
            
            await conn.close()
            return validation_results
            
        except Exception as e:
            print(f"❌ Schema validation failed: {e}")
            return {}
    
    def list_modules(self) -> None:
        """List all registered modules and their tables."""
        print("📦 Registered Bot Modules:")
        print("-" * 50)
        
        for module_name, schema in self.registered_modules.items():
            print(f"\n🔧 {module_name}:")
            for table in schema.tables:
                deps = f" (depends on: {', '.join(table.dependencies)})" if table.dependencies else ""
                print(f"   • {table.name}{deps}")


# Singleton instance
_schema_manager = None

def get_schema_manager() -> SchemaManager:
    """Get the global schema manager instance."""
    global _schema_manager
    if _schema_manager is None:
        _schema_manager = SchemaManager()
    return _schema_manager


# Public API for modules to declare schemas
def declare_schema(module_name: str, schema: ModuleSchema) -> None:
    """
    Declare a module's database schema.
    
    This is the primary function modules should call to register their schemas.
    The schema will be automatically synchronized with the database.
    
    Args:
        module_name: Unique name for the module
        schema: Complete schema definition for the module
    
    Example:
        from db.schema_manager import declare_schema, ModuleSchema, TableDefinition
        
        def setup_module():
            schema = ModuleSchema(
                module_name="my_module",
                tables=[TableDefinition(...)]
            )
            declare_schema("my_module", schema)
    """
    manager = get_schema_manager()
    manager.declare_schema(module_name, schema)


def set_auto_sync(enabled: bool) -> None:
    """
    Enable or disable automatic schema synchronization.
    
    When enabled (default), schemas are automatically created in the database
    when modules declare them. When disabled, schemas must be manually synced.
    """
    manager = get_schema_manager()
    manager.set_auto_sync(enabled)


async def sync_all_schemas() -> bool:
    """
    Manually sync all declared schemas to the database.
    
    Useful when auto_sync is disabled or for batch operations.
    """
    manager = get_schema_manager()
    
    # Sync any pending schemas first
    if hasattr(manager, '_pending_sync') and manager._pending_sync:
        print(f"🔄 Syncing {len(manager._pending_sync)} pending schemas...")
        for module_name in list(manager._pending_sync):
            await manager._sync_module_schema(module_name)
            manager._pending_sync.discard(module_name)
    
    return await manager.create_schemas()


async def sync_module_schema(module_name: str) -> bool:
    """
    Manually sync a specific module's schema to the database.
    
    Args:
        module_name: Name of the module to sync
        
    Returns:
        True if sync was successful, False otherwise
    """
    manager = get_schema_manager()
    return await manager._sync_module_schema(module_name)


async def main():
    """CLI interface for schema management."""
    import sys
    
    manager = get_schema_manager()
    
    if len(sys.argv) < 2:
        print("Usage: python -m db.schema_manager <command>")
        print("Commands:")
        print("  discover    - Auto-discover module schemas")
        print("  create      - Create all schemas")
        print("  validate    - Validate existing schemas")
        print("  list        - List registered modules")
        return
    
    command = sys.argv[1]
    
    if command == "discover":
        manager.discover_modules()
        manager.list_modules()
    
    elif command == "create":
        manager.discover_modules()
        success = await manager.create_schemas()
        if success:
            print("\n🎉 All schemas created successfully!")
        else:
            print("\n💥 Schema creation failed!")
    
    elif command == "validate":
        manager.discover_modules()
        results = await manager.validate_schemas()
        
        print("\n📋 Schema Validation Results:")
        for module_name, missing_tables in results.items():
            if missing_tables:
                print(f"❌ {module_name}: Missing tables: {', '.join(missing_tables)}")
            else:
                print(f"✅ {module_name}: All tables present")
    
    elif command == "list":
        manager.discover_modules()
        manager.list_modules()
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())
