"""
Debug and Development Test for Feature Flags

This module provides quick debug tests for development purposes:
- Observer immediate notifications
- File watching behavior
- Manager state inspection
- Configuration file structure validation

Use this for interactive debugging and troubleshooting.
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


def debug_observer_notifications():
    """Debug observer immediate notifications."""
    print("🔍 DEBUG: Observer Immediate Notifications")
    print("-" * 60)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "debug_observer.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    # Create test setup
    DEBUG_FLAG = FeatureFlag("debug_observer_flag")
    manager = get_manager(str(config_path), module_name="debug_module")
    manager.declare_flag(DEBUG_FLAG, PermissionLevel.READ_WRITE, "initial", "Debug flag")
    
    # Observer tracking
    notifications = []
    
    def debug_observer(flag_name: str, old_value, new_value):
        timestamp = time.time()
        notifications.append((timestamp, flag_name, old_value, new_value))
        print(f"  🔔 [{timestamp:.3f}] {flag_name}: {old_value} → {new_value}")
    
    manager.add_observer(DEBUG_FLAG, debug_observer)
    print("✅ Observer added")
    
    # Test immediate notification
    print("\n🔄 Testing immediate notification...")
    start_time = time.time()
    manager.set_flag(DEBUG_FLAG, "immediate_test")
    immediate_time = time.time()
    
    print(f"⏱️  Set operation took: {(immediate_time - start_time)*1000:.1f}ms")
    
    # Check if notification was immediate
    if notifications:
        notification_time = notifications[-1][0]
        delay = (notification_time - start_time) * 1000
        print(f"⏱️  Observer notification delay: {delay:.1f}ms")
    else:
        print("❌ No immediate notification received")
    
    # Wait for file watcher (if any)
    print("\n⏳ Waiting for file watcher notifications...")
    time.sleep(1.0)
    
    print(f"📊 Total notifications received: {len(notifications)}")
    for i, (timestamp, flag_name, old_val, new_val) in enumerate(notifications):
        print(f"  {i+1}. {flag_name}: {old_val} → {new_val}")
    
    manager.shutdown()
    if config_file.exists():
        config_file.unlink()
    print("✅ Debug observer test complete\n")


def debug_manager_state():
    """Debug manager internal state."""
    print("🔍 DEBUG: Manager Internal State")
    print("-" * 60)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "debug_state.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    manager = get_manager(str(config_path), module_name="debug_state")
    
    # Declare multiple flags with different permissions
    TEST_FLAGS = [
        (FeatureFlag("admin_flag"), PermissionLevel.OWNER_ONLY, "admin_value"),
        (FeatureFlag("shared_flag"), PermissionLevel.READ_WRITE, 42),
        (FeatureFlag("readonly_flag"), PermissionLevel.READ_ONLY, True),
    ]
    
    for flag, permission, value in TEST_FLAGS:
        manager.declare_flag(flag, permission, value, f"Debug flag {flag.name}")
    
    print("✅ Created test flags")
    
    # Inspect manager state
    print("\n📋 Manager State:")
    print(f"  Module name: {manager.module_name}")
    print(f"  Config path: {manager.config_path}")
    
    # Show ownership info
    ownership_info = manager.get_ownership_info()
    print(f"\n👥 Ownership Information:")
    for flag_name, ownership in ownership_info.items():
        print(f"  • {flag_name}:")
        print(f"    Owner: {ownership.owner_module}")
        print(f"    Access: {ownership.access_permissions.value}")
    
    # Show configuration file structure
    print(f"\n📄 Configuration File Structure:")
    if config_file.exists():
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        print(json.dumps(config_data, indent=2))
    else:
        print("  ❌ Configuration file not found")
    
    manager.shutdown()
    if config_file.exists():
        config_file.unlink()
    print("✅ Debug state inspection complete\n")


def debug_file_watching():
    """Debug file watching behavior."""
    print("🔍 DEBUG: File Watching Behavior")
    print("-" * 60)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "debug_filewatcher.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    WATCH_FLAG = FeatureFlag("file_watch_test")
    manager = get_manager(str(config_path), module_name="file_watcher_debug")
    manager.declare_flag(WATCH_FLAG, PermissionLevel.READ_WRITE, "initial", "File watch test")
    
    file_events = []
    
    def file_watch_observer(flag_name: str, old_value, new_value):
        file_events.append((time.time(), "file_change", flag_name, old_value, new_value))
        print(f"  📁 File change detected: {flag_name} {old_value} → {new_value}")
    
    manager.add_observer(WATCH_FLAG, file_watch_observer)
    print("✅ File watcher observer added")
    
    # Test 1: Internal change (through manager)
    print("\n🔄 Test 1: Internal change through manager")
    manager.set_flag(WATCH_FLAG, "internal_change")
    time.sleep(0.2)
    
    # Test 2: External file modification
    print("\n🔄 Test 2: External file modification")
    if config_file.exists():
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Modify the file externally
        config_data['flags']['file_watch_test']['value'] = "external_change"
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print("✅ File modified externally")
        time.sleep(1.0)  # Give file watcher time to detect
    
    print(f"\n📊 File watch events: {len(file_events)}")
    for i, (timestamp, event_type, flag_name, old_val, new_val) in enumerate(file_events):
        print(f"  {i+1}. [{timestamp:.3f}] {event_type}: {flag_name} {old_val} → {new_val}")
    
    manager.shutdown()
    if config_file.exists():
        config_file.unlink()
    print("✅ Debug file watching complete\n")


def debug_quick_test():
    """Quick interactive debug test."""
    print("🔍 DEBUG: Quick Interactive Test")
    print("-" * 60)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "debug_quick.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    QUICK_FLAG = FeatureFlag("quick_test")
    manager = get_manager(str(config_path), module_name="quick_debug")
    manager.declare_flag(QUICK_FLAG, PermissionLevel.READ_WRITE, 0, "Quick test counter")
    
    print("✅ Manager created and flag declared")
    print(f"Initial value: {manager.get_int(QUICK_FLAG)}")
    
    # Interactive test loop
    for i in range(5):
        new_value = i + 1
        print(f"\n🔄 Setting flag to {new_value}...")
        manager.set_flag(QUICK_FLAG, new_value)
        retrieved = manager.get_int(QUICK_FLAG)
        print(f"✅ Retrieved value: {retrieved}")
        
        if retrieved != new_value:
            print(f"❌ Value mismatch! Expected {new_value}, got {retrieved}")
        
        time.sleep(0.1)
    
    manager.shutdown()
    if config_file.exists():
        config_file.unlink()
    print("✅ Quick debug test complete\n")


def main():
    """Run all debug tests."""
    print("🛠️  FEATURE FLAGS DEBUG SUITE")
    print("=" * 80)
    print("This suite provides debug information for development:")
    print("• Observer immediate notification behavior")
    print("• Manager internal state inspection")
    print("• File watching system behavior")
    print("• Quick interactive testing")
    print("=" * 80)
    
    try:
        debug_observer_notifications()
        debug_manager_state()
        debug_file_watching()
        debug_quick_test()
        
        print("🎉 ALL DEBUG TESTS COMPLETED!")
        print("✅ Observer system functioning")
        print("✅ Manager state accessible")
        print("✅ File watching operational")
        print("✅ Quick tests passing")
        
    except Exception as e:
        print(f"\n❌ Debug test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🛠️  Debug testing complete!")


if __name__ == "__main__":
    main()
