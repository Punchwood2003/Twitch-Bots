"""
Basic Feature Flags Functionality Tests

This module tests core feature flag functionality including:
- Flag declaration and usage
- Basic observers and notifications
- Cross-manager communication
- Permission validation
- Configuration persistence
"""

import time
import json
import sys
import os
from pathlib import Path

# Fix Unicode encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add the parent directory to the path so we can import feature_flags
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from feature_flags import FeatureFlag, get_manager, PermissionLevel


def test_basic_flag_operations():
    """Test basic flag declaration, setting, and getting."""
    print("🔍 TESTING BASIC FLAG OPERATIONS")
    print("-" * 50)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "test_basic_operations.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    # Test flags
    BOOL_FLAG = FeatureFlag("bool_test")
    INT_FLAG = FeatureFlag("int_test")
    STRING_FLAG = FeatureFlag("string_test")
    
    # Create manager
    manager = get_manager(str(config_path), module_name="basic_test")
    
    # Declare flags
    manager.declare_flag(BOOL_FLAG, PermissionLevel.READ_WRITE, True, "Boolean test flag")
    manager.declare_flag(INT_FLAG, PermissionLevel.READ_WRITE, 42, "Integer test flag")
    manager.declare_flag(STRING_FLAG, PermissionLevel.READ_WRITE, "hello", "String test flag")
    
    print("✅ Flags declared successfully")
    
    # Test getting initial values
    assert manager.get_bool(BOOL_FLAG) == True
    assert manager.get_int(INT_FLAG) == 42
    assert manager.get_string(STRING_FLAG) == "hello"
    
    print("✅ Initial values retrieved correctly")
    
    # Test setting new values
    manager.set_flag(BOOL_FLAG, False)
    manager.set_flag(INT_FLAG, 100)
    manager.set_flag(STRING_FLAG, "world")
    
    # Test getting updated values
    assert manager.get_bool(BOOL_FLAG) == False
    assert manager.get_int(INT_FLAG) == 100
    assert manager.get_string(STRING_FLAG) == "world"
    
    print("✅ Values updated and retrieved correctly")
    
    # Test persistence
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    assert config_data['flags']['bool_test']['value'] == False
    assert config_data['flags']['int_test']['value'] == 100
    assert config_data['flags']['string_test']['value'] == "world"
    
    print("✅ Values persisted to configuration file")
    
    manager.shutdown()
    if config_file.exists():
        config_file.unlink()
    
    print("✅ Basic flag operations test passed!")


def test_observers():
    """Test observer functionality."""
    print("\n🔔 TESTING OBSERVER FUNCTIONALITY")
    print("-" * 50)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "test_observers.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    TEST_FLAG = FeatureFlag("observer_test")
    manager = get_manager(str(config_path), module_name="observer_test")
    manager.declare_flag(TEST_FLAG, PermissionLevel.READ_WRITE, "initial", "Observer test flag")
    
    # Track observer calls
    observer_calls = []
    
    def test_observer(flag_name: str, old_value, new_value):
        observer_calls.append((flag_name, old_value, new_value))
        print(f"  🔔 Observer notified: {flag_name} {old_value} → {new_value}")
    
    manager.add_observer(TEST_FLAG, test_observer)
    print("✅ Observer added")
    
    # Test observer notifications
    manager.set_flag(TEST_FLAG, "change1")
    manager.set_flag(TEST_FLAG, "change2")
    
    # Allow time for notifications
    time.sleep(0.2)
    
    assert len(observer_calls) >= 2, f"Expected at least 2 notifications, got {len(observer_calls)}"
    assert observer_calls[0] == ("observer_test", "initial", "change1")
    assert observer_calls[1] == ("observer_test", "change1", "change2")
    
    print(f"✅ Received {len(observer_calls)} observer notifications")
    
    manager.shutdown()
    if config_file.exists():
        config_file.unlink()
    
    print("✅ Observer functionality test passed!")


def test_cross_manager_communication():
    """Test cross-manager communication."""
    print("\n🔗 TESTING CROSS-MANAGER COMMUNICATION")
    print("-" * 50)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "test_cross_manager.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    SHARED_FLAG = FeatureFlag("shared_flag")
    
    # Manager A declares flag
    manager_a = get_manager(str(config_path), module_name="manager_a")
    manager_a.declare_flag(SHARED_FLAG, PermissionLevel.READ_WRITE, "initial", "Shared flag")
    
    print("✅ Manager A declared shared flag")
    
    # Manager B uses the same flag
    manager_b = get_manager(str(config_path), module_name="manager_b")
    manager_b.use_flag(SHARED_FLAG)
    
    print("✅ Manager B connected to shared flag")
    
    # Test communication A -> B
    manager_a.set_flag(SHARED_FLAG, "from_a")
    time.sleep(0.3)  # Allow synchronization
    
    value_b = manager_b.get_string(SHARED_FLAG)
    assert value_b == "from_a", f"Expected 'from_a', got '{value_b}'"
    print("✅ Manager B sees changes from Manager A")
    
    # Test communication B -> A
    manager_b.set_flag(SHARED_FLAG, "from_b")
    time.sleep(0.3)  # Allow synchronization
    
    value_a = manager_a.get_string(SHARED_FLAG)
    assert value_a == "from_b", f"Expected 'from_b', got '{value_a}'"
    print("✅ Manager A sees changes from Manager B")
    
    # Test cross-manager observers
    a_notifications = []
    b_notifications = []
    
    def observer_a(flag_name: str, old_value, new_value):
        a_notifications.append((flag_name, old_value, new_value))
    
    def observer_b(flag_name: str, old_value, new_value):
        b_notifications.append((flag_name, old_value, new_value))
    
    manager_a.add_observer(SHARED_FLAG, observer_a)
    manager_b.add_observer(SHARED_FLAG, observer_b)
    
    # Make change through Manager A
    manager_a.set_flag(SHARED_FLAG, "cross_test")
    time.sleep(0.3)
    
    assert len(a_notifications) > 0, "Manager A should receive notifications"
    assert len(b_notifications) > 0, "Manager B should receive cross-manager notifications"
    
    print(f"✅ Cross-manager observers working (A: {len(a_notifications)}, B: {len(b_notifications)})")
    
    manager_a.shutdown()
    manager_b.shutdown()
    if config_file.exists():
        config_file.unlink()
    
    print("✅ Cross-manager communication test passed!")


def test_permissions():
    """Test permission system."""
    print("\n🔒 TESTING PERMISSION SYSTEM")
    print("-" * 50)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "test_permissions.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    # Permission test flags
    OWNER_FLAG = FeatureFlag("owner_only")
    READONLY_FLAG = FeatureFlag("readonly")
    READWRITE_FLAG = FeatureFlag("readwrite")
    
    # Owner manager
    owner = get_manager(str(config_path), module_name="owner")
    owner.declare_flag(OWNER_FLAG, PermissionLevel.OWNER_ONLY, "secret", "Owner only")
    owner.declare_flag(READONLY_FLAG, PermissionLevel.READ_ONLY, "readonly", "Read only")
    owner.declare_flag(READWRITE_FLAG, PermissionLevel.READ_WRITE, "readwrite", "Read write")
    
    print("✅ Owner declared flags with different permission levels")
    
    # User manager
    user = get_manager(str(config_path), module_name="user")
    
    # Test OWNER_ONLY (should fail)
    try:
        user.use_flag(OWNER_FLAG)
        assert False, "Should have been denied"
    except PermissionError:
        print("✅ OWNER_ONLY access correctly denied")
    
    # Test READ_ONLY
    user.use_flag(READONLY_FLAG)
    assert user.get_string(READONLY_FLAG) == "readonly"
    print("✅ READ_ONLY access granted for reading")
    
    try:
        user.set_flag(READONLY_FLAG, "modified")
        assert False, "Should have been denied"
    except PermissionError:
        print("✅ READ_ONLY write correctly denied")
    
    # Test READ_WRITE
    user.use_flag(READWRITE_FLAG)
    assert user.get_string(READWRITE_FLAG) == "readwrite"
    user.set_flag(READWRITE_FLAG, "user_modified")
    assert user.get_string(READWRITE_FLAG) == "user_modified"
    print("✅ READ_WRITE access working correctly")
    
    owner.shutdown()
    user.shutdown()
    if config_file.exists():
        config_file.unlink()
    
    print("✅ Permission system test passed!")


def test_persistence():
    """Test configuration persistence."""
    print("\n💾 TESTING CONFIGURATION PERSISTENCE")
    print("-" * 50)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "test_persistence.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    PERSIST_FLAG = FeatureFlag("persist_test")
    
    # Create manager and set value
    manager1 = get_manager(str(config_path), module_name="persist_test1")
    manager1.declare_flag(PERSIST_FLAG, PermissionLevel.READ_WRITE, "original", "Persistence test")
    manager1.set_flag(PERSIST_FLAG, "modified")
    
    # Verify file exists
    assert config_file.exists(), "Configuration file should exist"
    print("✅ Configuration file created")
    
    # Verify file content
    with open(config_path, 'r') as f:
        config_data = json.load(f)
    
    assert "flags" in config_data
    assert config_data["flags"]["persist_test"]["value"] == "modified"
    print("✅ Configuration contains correct data")
    
    manager1.shutdown()
    
    # Create new manager with same config
    manager2 = get_manager(str(config_path), module_name="persist_test2")
    manager2.use_flag(PERSIST_FLAG)
    
    # Verify persistence
    reloaded_value = manager2.get_string(PERSIST_FLAG)
    assert reloaded_value == "modified", f"Expected 'modified', got '{reloaded_value}'"
    print("✅ Value correctly reloaded from file")
    
    manager2.shutdown()
    if config_file.exists():
        config_file.unlink()
    
    print("✅ Configuration persistence test passed!")


def main():
    """Run all basic functionality tests."""
    print("🧪 BASIC FEATURE FLAGS FUNCTIONALITY TESTS")
    print("="*70)
    print("Testing core feature flag operations and functionality\n")
    
    try:
        test_basic_flag_operations()
        test_observers()
        test_cross_manager_communication()
        test_permissions()
        test_persistence()
        
        print("\n🎉 ALL BASIC TESTS PASSED!")
        print("✅ Basic flag operations working")
        print("✅ Observer notifications functional")
        print("✅ Cross-manager communication operational")
        print("✅ Permission system enforced")
        print("✅ Configuration persistence working")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🧪 Basic functionality testing complete!")


if __name__ == "__main__":
    main()
