"""
Module Management CLI

Command-line interface for managing Twitch bot modules.
Provides functionality to enable/disable modules, view status, and more.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from feature_flags.feature_flags_manager import FeatureFlagManager
from db.schema_manager import SchemaManager
from module_manager.module_manager import ModuleManager
from modules.charity_gambling import CharityGamblingModule


class ModuleManagerCLI:
    """Command-line interface for module management."""
    
    def __init__(self):
        self.feature_flag_manager = FeatureFlagManager(module_name="cli")
        self.schema_manager = SchemaManager()
        self.module_manager = ModuleManager(
            self.feature_flag_manager,
            self.schema_manager
        )
    
    async def initialize(self):
        """Initialize the module manager."""
        await self.module_manager.initialize()
        
        # Register built-in modules for management
        charity_module = CharityGamblingModule()
        self.module_manager.register_module(charity_module)
    
    def list_modules(self):
        """List all registered modules."""
        modules = self.module_manager.get_all_modules_info()
        
        if not modules:
            print("No modules registered.")
            return
        
        print("\nRegistered Modules:")
        print("-" * 80)
        print(f"{'Name':<20} {'Version':<10} {'Status':<10} {'Enabled':<8} {'Auto-Start':<10}")
        print("-" * 80)
        
        for name, info in modules.items():
            print(f"{name:<20} {info['version']:<10} {info['status']:<10} "
                  f"{'Yes' if info['enabled'] else 'No':<8} "
                  f"{'Yes' if info['auto_start'] else 'No':<10}")
        
        print("-" * 80)
    
    def show_module_info(self, module_name: str):
        """Show detailed information about a module."""
        info = self.module_manager.get_module_info(module_name)
        
        if not info:
            print(f"Module '{module_name}' not found.")
            return
        
        print(f"\nModule Information: {module_name}")
        print("=" * 50)
        print(f"Name: {info['name']}")
        print(f"Description: {info['description']}")
        print(f"Version: {info['version']}")
        print(f"Status: {info['status']}")
        print(f"Enabled: {'Yes' if info['enabled'] else 'No'}")
        print(f"Auto-Start: {'Yes' if info['auto_start'] else 'No'}")
        print(f"Dependencies: {', '.join(info['dependencies']) if info['dependencies'] else 'None'}")
        print(f"Dependents: {', '.join(info['dependents']) if info['dependents'] else 'None'}")
        print(f"Feature Flags: {info['feature_flags_count']}")
        print(f"Commands: {info['commands_count']}")
        print(f"Database Schema: {'Yes' if info['has_database_schema'] else 'No'}")
        print(f"Times Started: {info['start_count']}")
        
        if info['last_error']:
            print(f"\nLast Error: {info['last_error']}")
    
    def enable_module(self, module_name: str):
        """Enable a module."""
        if self.module_manager.enable_module(module_name):
            print(f"Module '{module_name}' enabled.")
        else:
            print(f"Failed to enable module '{module_name}'. Module may not exist.")
    
    def disable_module(self, module_name: str):
        """Disable a module."""
        if self.module_manager.disable_module(module_name):
            print(f"Module '{module_name}' disabled.")
        else:
            print(f"Failed to disable module '{module_name}'. Module may not exist.")
    
    async def start_module(self, module_name: str):
        """Start a module."""
        success = await self.module_manager.start_module(module_name)
        if success:
            print(f"Module '{module_name}' started successfully.")
        else:
            print(f"Failed to start module '{module_name}'.")
    
    async def stop_module(self, module_name: str):
        """Stop a module."""
        success = await self.module_manager.stop_module(module_name)
        if success:
            print(f"Module '{module_name}' stopped successfully.")
        else:
            print(f"Failed to stop module '{module_name}'.")
    
    async def restart_module(self, module_name: str):
        """Restart a module."""
        success = await self.module_manager.restart_module(module_name)
        if success:
            print(f"Module '{module_name}' restarted successfully.")
        else:
            print(f"Failed to restart module '{module_name}'.")
    
    def show_status(self):
        """Show overall system status."""
        modules = self.module_manager.get_all_modules_info()
        running_modules = self.module_manager.get_running_modules()
        commands = self.module_manager.get_registered_commands()
        
        print("\nSystem Status")
        print("=" * 50)
        print(f"Total Modules: {len(modules)}")
        print(f"Running Modules: {len(running_modules)}")
        print(f"Registered Commands: {len(commands)}")
        
        if running_modules:
            print(f"\nRunning Modules: {', '.join(running_modules)}")
        
        enabled_modules = [name for name, info in modules.items() if info['enabled']]
        if enabled_modules:
            print(f"Enabled Modules: {', '.join(enabled_modules)}")
        
        auto_start_modules = [name for name, info in modules.items() if info['auto_start']]
        if auto_start_modules:
            print(f"Auto-Start Modules: {', '.join(auto_start_modules)}")
    
    def set_auto_start(self, module_name: str, auto_start: bool):
        """Set auto-start for a module."""
        if self.module_manager.registry.set_module_auto_start(module_name, auto_start):
            status = "enabled" if auto_start else "disabled"
            print(f"Auto-start {status} for module '{module_name}'.")
        else:
            print(f"Failed to set auto-start for module '{module_name}'. Module may not exist.")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Twitch Bot Module Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    subparsers.add_parser('list', help='List all modules')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show module information')
    info_parser.add_argument('module', help='Module name')
    
    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable a module')
    enable_parser.add_argument('module', help='Module name')
    
    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable a module')
    disable_parser.add_argument('module', help='Module name')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start a module')
    start_parser.add_argument('module', help='Module name')
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop a module')
    stop_parser.add_argument('module', help='Module name')
    
    # Restart command
    restart_parser = subparsers.add_parser('restart', help='Restart a module')
    restart_parser.add_argument('module', help='Module name')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # Auto-start command
    autostart_parser = subparsers.add_parser('autostart', help='Set module auto-start')
    autostart_parser.add_argument('module', help='Module name')
    autostart_parser.add_argument('enabled', choices=['on', 'off'], help='Enable or disable auto-start')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI
    cli = ModuleManagerCLI()
    await cli.initialize()
    
    # Execute command
    try:
        if args.command == 'list':
            cli.list_modules()
        elif args.command == 'info':
            cli.show_module_info(args.module)
        elif args.command == 'enable':
            cli.enable_module(args.module)
        elif args.command == 'disable':
            cli.disable_module(args.module)
        elif args.command == 'start':
            await cli.start_module(args.module)
        elif args.command == 'stop':
            await cli.stop_module(args.module)
        elif args.command == 'restart':
            await cli.restart_module(args.module)
        elif args.command == 'status':
            cli.show_status()
        elif args.command == 'autostart':
            cli.set_auto_start(args.module, args.enabled == 'on')
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    asyncio.run(main())
