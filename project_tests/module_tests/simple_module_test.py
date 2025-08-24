"""
Simple Module System Test

Test the module system without database connections.
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


async def simple_test():
    """Test basic module functionality without database."""
    print("Simple Module System Test")
    print("=" * 50)
    
    # Initialize core systems
    feature_flag_manager = FeatureFlagManager(module_name="test")
    schema_manager = SchemaManager()
    module_manager = ModuleManager(
        feature_flag_manager,
        schema_manager,
        "simple_test_registry.json"
    )
    
    try:
        print("1. Creating charity gambling module...")
        charity_module = CharityGamblingModule()
        print(f"   Module name: {charity_module.module_name}")
        print(f"   Module description: {charity_module.module_description}")
        print(f"   Module version: {charity_module.module_version}")
        
        print("\n2. Checking feature flags...")
        feature_flags = charity_module.get_feature_flags()
        print(f"   Feature flags count: {len(feature_flags)}")
        for flag, permission, default_value, description in feature_flags:
            print(f"   - {flag.name}: {description} (default: {default_value})")
        
        print("\n3. Checking database schema...")
        db_schema = charity_module.get_database_schema()
        if db_schema:
            print(f"   Tables: {len(db_schema.tables)}")
            for table in db_schema.tables:
                print(f"   - {table.name}")
        
        print("\n4. Checking commands...")
        commands = charity_module.get_commands()
        print(f"   Commands count: {len(commands)}")
        for command in commands:
            print(f"   - {command.name}: {command.description}")
        
        print("\n5. Checking module config...")
        config = charity_module.get_config()
        print(f"   Enabled by default: {config.enabled_by_default}")
        print(f"   Auto start: {config.auto_start}")
        print(f"   Dependencies: {config.dependencies}")
        
        print("\n6. Testing manager injection...")
        # Check if managers are None initially
        print(f"   Feature manager before injection: {charity_module.feature_flag_manager is not None}")
        print(f"   Database manager before injection: {charity_module.database_manager is not None}")
        
        # Test the injection method
        from feature_flags.feature_flags_manager import FeatureFlagManager as TestFeatureFlagManager
        from db.module_connections import ModuleDatabaseManager as TestModuleDatabaseManager
        
        test_flag_manager = TestFeatureFlagManager(module_name="test_charity")
        test_db_manager = TestModuleDatabaseManager("test_charity")
        
        charity_module._inject_managers(test_flag_manager, test_db_manager)
        
        print(f"   Feature manager after injection: {charity_module.feature_flag_manager is not None}")
        print(f"   Database manager after injection: {charity_module.database_manager is not None}")
        
        print("\n✓ All basic tests passed!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(simple_test())
