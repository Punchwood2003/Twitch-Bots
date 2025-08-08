"""
Database Infrastructure Package

This package provides database infrastructure for Twitch Bot services including async
connection management, modular schema management, and resource pooling.
"""

from .config import DatabaseConfig
from .module_connections import get_module_database_manager, ModuleDatabaseManager
from .schema_manager import declare_schema, ModuleSchema, TableDefinition

__all__ = [
    "DatabaseConfig",
    "get_module_database_manager",
    "ModuleDatabaseManager", 
    "declare_schema",
    "ModuleSchema",
    "TableDefinition",
]

# Version info
__version__ = "1.0.0"
__author__ = "Matthew Sheldon"
__description__ = "Provides async database management for Twitch Bot services with connection pooling and schema management to Supabase."
