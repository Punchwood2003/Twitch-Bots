"""
Module Manager System

This package provides a modular system for declaring and managing Twitch bot modules.
Each module can declare its own feature flags, database schema, commands, and lifecycle hooks.
"""

from .module_definition import ModuleDefinition, ModuleStatus
from .module_manager import ModuleManager
from .module_registry import ModuleRegistry

__all__ = [
    'ModuleDefinition',
    'ModuleStatus', 
    'ModuleManager',
    'ModuleRegistry'
]
