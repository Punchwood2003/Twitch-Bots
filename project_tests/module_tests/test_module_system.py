"""
Test Module System

Simple test to verify the module system works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from feature_flags.feature_flags_manager import FeatureFlagManager
from db.schema_manager import SchemaManager
from module_manager.module_manager import ModuleManager
from modules.charity_gambling import CharityGamblingModule


async def test_module_system():
    """Test the basic module system functionality."""
    print("Testing Module System...")
    print("=" * 50)
    
    # Initialize core systems
    feature_flag_manager = FeatureFlagManager(module_name="test")
    schema_manager = SchemaManager()
    module_manager = ModuleManager(
        feature_flag_manager,
        schema_manager,
        "test_module_registry.json"
    )
    
    try:
        # Initialize the module manager
        print("1. Initializing module manager...")
        await module_manager.initialize()
        print("   ✓ Module manager initialized")
        
        # Register a test module
        print("\n2. Registering charity gambling module...")
        charity_module = CharityGamblingModule()
        module_manager.register_module(charity_module)
        print("   ✓ Module registered successfully")
        
        # Check module info
        print("\n3. Checking module information...")
        info = module_manager.get_module_info("charity_gambling")
        print(f"   Module: {info['name']}")
        print(f"   Description: {info['description']}")
        print(f"   Version: {info['version']}")
        print(f"   Enabled: {info['enabled']}")
        print(f"   Feature Flags: {info['feature_flags_count']}")
        print(f"   Commands: {info['commands_count']}")
        print(f"   Has DB Schema: {info['has_database_schema']}")
        
        # Test enabling/disabling
        print("\n4. Testing enable/disable functionality...")
        module_manager.enable_module("charity_gambling")
        print("   ✓ Module enabled")
        
        module_manager.disable_module("charity_gambling")
        print("   ✓ Module disabled")
        
        module_manager.enable_module("charity_gambling")
        print("   ✓ Module re-enabled")
        
        # Test starting/stopping (without Twitch context)
        print("\n5. Testing module lifecycle...")
        success = await module_manager.start_module("charity_gambling")
        print(f"   Start result: {'✓ Success' if success else '✗ Failed'}")
        
        if success:
            running_modules = module_manager.get_running_modules()
            print(f"   Running modules: {running_modules}")
            
            success = await module_manager.stop_module("charity_gambling")
            print(f"   Stop result: {'✓ Success' if success else '✗ Failed'}")
        
        # Test command registration
        print("\n6. Testing command registration...")
        await module_manager.start_module("charity_gambling")
        commands = module_manager.get_registered_commands()
        print(f"   Registered commands: {list(commands.keys())}")
        
        # Test module status
        print("\n7. Testing module status...")
        all_modules = module_manager.get_all_modules_info()
        for name, info in all_modules.items():
            print(f"   {name}: {info['status']} (enabled: {info['enabled']})")
        
        print("\n✓ All tests passed successfully!")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        raise
    finally:
        # Cleanup
        await module_manager.shutdown()
        print("\n🧹 Cleanup complete")


if __name__ == '__main__':
    asyncio.run(test_module_system())
