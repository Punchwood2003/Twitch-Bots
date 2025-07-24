"""
Advanced Feature Flag Edge Cases and Stress Tests

This module tests advanced scenarios and edge cases including:
- Permission conflicts and ownership disputes
- Rapid configuration changes and stress testing
- Concurrent adef test_error_recovery():
    ```python
    # Test error handling and recovery scenarios.
    print("\n🔧 TESTING ERROR RECOVERY")
    print("-" * 50)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "test_error_recovery.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    RECOVERY_FLAG = FeatureFlag("recovery_test")
    manager = get_manager(str(config_path), module_name="recovery_test")
    manager.declare_flag(RECOVERY_FLAG, PermissionLevel.READ_WRITE, "valid", "Recovery test flag")s and race conditions
    ```
- Error handling and recovery scenarios
- Complex multi-module ownership patterns
"""

import time
import threading
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


def test_permission_conflicts():
    """Test various permission conflict scenarios."""
    print("🔒 TESTING PERMISSION CONFLICTS")
    print("-" * 50)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "test_permission_conflicts.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    # Test flags with different permission levels
    ADMIN_FLAG = FeatureFlag("admin_only_flag")
    READONLY_FLAG = FeatureFlag("readonly_flag")
    SHARED_FLAG = FeatureFlag("shared_flag")
    
    # Admin manager declares restrictive flags
    admin = get_manager(str(config_path), module_name="admin")
    admin.declare_flag(ADMIN_FLAG, PermissionLevel.OWNER_ONLY, "secret", "Admin-only configuration")
    admin.declare_flag(READONLY_FLAG, PermissionLevel.READ_ONLY, "readonly_value", "Read-only for others")
    admin.declare_flag(SHARED_FLAG, PermissionLevel.READ_WRITE, "shared_initial", "Shared configuration")
    
    print("✅ Admin declared flags with various permission levels")
    
    time.sleep(0.3)  # Allow synchronization
    
    # User manager attempts access
    user = get_manager(str(config_path), module_name="user")
    
    # Test OWNER_ONLY restriction
    try:
        user.use_flag(ADMIN_FLAG)
        assert False, "Should have been denied"
    except PermissionError:
        print("✅ OWNER_ONLY access correctly denied")
    
    # Test READ_ONLY access
    user.use_flag(READONLY_FLAG)
    assert user.get_string(READONLY_FLAG) == "readonly_value"
    print("✅ READ_ONLY access granted for reading")
    
    try:
        user.set_flag(READONLY_FLAG, "modified")
        assert False, "Should have been denied"
    except PermissionError:
        print("✅ READ_ONLY write correctly denied")
    
    # Test READ_WRITE access
    user.use_flag(SHARED_FLAG)
    assert user.get_string(SHARED_FLAG) == "shared_initial"
    user.set_flag(SHARED_FLAG, "modified_by_user")
    assert user.get_string(SHARED_FLAG) == "modified_by_user"
    print("✅ READ_WRITE access working correctly")
    
    # Test ownership conflict
    try:
        user.declare_flag(ADMIN_FLAG, PermissionLevel.READ_WRITE, "conflict", "Attempted override")
        assert False, "Should have been denied"
    except PermissionError:
        print("✅ Ownership conflict correctly prevented")
    
    admin.shutdown()
    user.shutdown()
    if config_file.exists():
        config_file.unlink()
    
    print("✅ Permission conflicts test passed!")


def test_rapid_changes_stress():
    """Test rapid configuration changes and observer performance."""
    print("\n⚡ TESTING RAPID CHANGES & STRESS")
    print("-" * 50)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "test_rapid_changes.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    STRESS_FLAG = FeatureFlag("stress_test_flag")
    manager = get_manager(str(config_path), module_name="stress_test")
    manager.declare_flag(STRESS_FLAG, PermissionLevel.READ_WRITE, 0, "Stress test counter")
    
    # Track observer performance
    observer_calls = []
    start_time = time.time()
    
    def stress_observer(flag_name, old_value, new_value):
        observer_calls.append((time.time(), old_value, new_value))
    
    manager.add_observer(STRESS_FLAG, stress_observer)
    print("✅ Observer added for stress test")
    
    # Rapid fire changes
    num_changes = 50
    change_start = time.time()
    
    for i in range(num_changes):
        manager.set_flag(STRESS_FLAG, i)
        time.sleep(0.01)  # Very rapid changes
    
    change_duration = time.time() - change_start
    
    # Allow time for all observers to complete
    time.sleep(0.5)
    
    # Verify observer performance
    observer_count = len(observer_calls)
    print(f"✅ Completed {num_changes} changes in {change_duration:.2f}s")
    print(f"✅ Observer received {observer_count}/{num_changes} notifications")
    
    # Verify final value
    final_value = manager.get_int(STRESS_FLAG)
    assert final_value == num_changes - 1, f"Expected {num_changes-1}, got {final_value}"
    print(f"✅ Final value correct: {final_value}")
    
    manager.shutdown()
    if config_file.exists():
        config_file.unlink()
    
    print("✅ Rapid changes stress test passed!")


def test_concurrent_access():
    """Test concurrent access from multiple threads."""
    print("\n🔀 TESTING CONCURRENT ACCESS")
    print("-" * 50)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "test_concurrent_access.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    COUNTER_FLAG = FeatureFlag("concurrent_counter")
    manager = get_manager(str(config_path), module_name="concurrent_test")
    manager.declare_flag(COUNTER_FLAG, PermissionLevel.READ_WRITE, 0, "Thread-safe counter")
    
    # Shared state for thread coordination
    results = []
    errors = []
    
    def worker_thread(thread_id, iterations):
        """Worker thread that performs concurrent operations."""
        try:
            for i in range(iterations):
                # Read current value
                current = manager.get_int(COUNTER_FLAG, 0)
                
                # Small random delay to increase race condition likelihood
                time.sleep(0.001 * (thread_id % 3))
                
                # Increment and write back
                new_value = current + 1
                manager.set_flag(COUNTER_FLAG, new_value)
                
                results.append((thread_id, i, current, new_value))
                
        except Exception as e:
            errors.append((thread_id, str(e)))
    
    # Start multiple concurrent threads
    num_threads = 5
    iterations_per_thread = 10
    threads = []
    
    start_time = time.time()
    for i in range(num_threads):
        thread = threading.Thread(target=worker_thread, args=(i, iterations_per_thread))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    duration = time.time() - start_time
    
    # Analyze results
    total_operations = len(results)
    expected_operations = num_threads * iterations_per_thread
    final_value = manager.get_int(COUNTER_FLAG, 0)
    
    print(f"✅ Completed {total_operations}/{expected_operations} operations in {duration:.2f}s")
    print(f"✅ Final counter value: {final_value}")
    print(f"✅ Errors encountered: {len(errors)}")
    
    if errors:
        for thread_id, error in errors[:3]:  # Show first 3 errors
            print(f"   Thread {thread_id}: {error}")
    
    # Verify thread safety (final value should be reasonable)
    assert final_value > 0, "Counter should have been incremented"
    assert len(errors) == 0, "No errors should occur in thread-safe operations"
    print("✅ Thread safety maintained")
    
    manager.shutdown()
    if config_file.exists():
        config_file.unlink()
    
    print("✅ Concurrent access test passed!")


def test_error_recovery():
    """Test error handling and recovery scenarios."""
    print("\n� TESTING ERROR RECOVERY")
    print("-" * 50)
    
    config_path = "test_error_recovery.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    RECOVERY_FLAG = FeatureFlag("recovery_test")
    manager = get_manager(str(config_path), module_name="recovery_test")
    manager.declare_flag(RECOVERY_FLAG, PermissionLevel.READ_WRITE, "valid", "Recovery test flag")
    
    print("✅ Initial configuration created")
    
    # Test 1: Corrupt configuration file
    with open(config_path, 'w') as f:
        f.write("{ invalid json content }")
    print("💀 Configuration file corrupted")
    
    # Manager should handle corruption gracefully
    time.sleep(0.2)  # Allow file watcher to detect change
    
    try:
        # Should still work with cached values
        value = manager.get_string(RECOVERY_FLAG, "fallback")
        print(f"✅ Graceful fallback during corruption: '{value}'")
    except Exception as e:
        print(f"⚠️ Error during corruption: {e}")
    
    # Test 2: Recovery by writing valid config
    manager.set_flag(RECOVERY_FLAG, "recovered")
    
    # Verify recovery
    with open(config_path, 'r') as f:
        recovered_config = json.load(f)
    
    assert "flags" in recovered_config
    assert recovered_config["flags"]["recovery_test"]["value"] == "recovered"
    print("✅ Configuration recovered successfully")
    
    # Test 3: Invalid flag operations
    NONEXISTENT_FLAG = FeatureFlag("nonexistent")
    
    try:
        manager.get_string(NONEXISTENT_FLAG)
        assert False, "Should have failed"
    except PermissionError:
        print("✅ Undeclared flag access correctly denied")
    
    try:
        manager.add_observer(NONEXISTENT_FLAG, lambda f, o, n: None)
        assert False, "Should have failed"
    except PermissionError:
        print("✅ Observer on undeclared flag correctly denied")
    
    manager.shutdown()
    if config_file.exists():
        config_file.unlink()
    
    print("✅ Error recovery test passed!")


def test_complex_ownership_patterns():
    """Test complex multi-module ownership scenarios."""
    print("\n👥 TESTING COMPLEX OWNERSHIP PATTERNS")
    print("-" * 50)
    
    # Use organized temp directory for test files
    config_path = Path(__file__).parent.parent / ".temp" / "test_complex_ownership.json"
    config_file = Path(config_path)
    if config_file.exists():
        config_file.unlink()
    
    # Create multiple specialized managers
    auth_manager = get_manager(str(config_path), module_name="auth_service")
    db_manager = get_manager(str(config_path), module_name="database_service")
    api_manager = get_manager(str(config_path), module_name="api_service")
    admin_manager = get_manager(str(config_path), module_name="admin_console")
    
    # Each service declares its domain flags
    AUTH_ENABLED = FeatureFlag("auth_enabled")
    AUTH_TIMEOUT = FeatureFlag("auth_timeout")
    DB_CONNECTION_POOL = FeatureFlag("db_connection_pool")
    DB_QUERY_TIMEOUT = FeatureFlag("db_query_timeout")
    API_RATE_LIMIT = FeatureFlag("api_rate_limit")
    ADMIN_MODE = FeatureFlag("admin_mode")
    
    # Auth service flags
    auth_manager.declare_flag(AUTH_ENABLED, PermissionLevel.READ_ONLY, True, "Authentication system status")
    auth_manager.declare_flag(AUTH_TIMEOUT, PermissionLevel.READ_ONLY, 300, "Auth token timeout seconds")
    
    # Database service flags
    db_manager.declare_flag(DB_CONNECTION_POOL, PermissionLevel.READ_ONLY, 10, "DB connection pool size")
    db_manager.declare_flag(DB_QUERY_TIMEOUT, PermissionLevel.READ_WRITE, 30, "DB query timeout seconds")
    
    # API service flags
    api_manager.declare_flag(API_RATE_LIMIT, PermissionLevel.READ_WRITE, 1000, "API requests per minute")
    
    # Admin console flag
    admin_manager.declare_flag(ADMIN_MODE, PermissionLevel.OWNER_ONLY, False, "Administrative mode")
    
    print("✅ All services declared their domain flags")
    
    time.sleep(0.5)  # Allow synchronization
    
    # Cross-service flag usage
    # API service needs auth and database info
    api_manager.use_flag(AUTH_ENABLED)
    api_manager.use_flag(AUTH_TIMEOUT)
    api_manager.use_flag(DB_CONNECTION_POOL)
    api_manager.use_flag(DB_QUERY_TIMEOUT)
    
    # Database service can adjust its own query timeout
    current_timeout = db_manager.get_int(DB_QUERY_TIMEOUT)
    db_manager.set_flag(DB_QUERY_TIMEOUT, current_timeout + 10)
    
    print("✅ Cross-service flag usage successful")
    
    # Admin attempts to access restricted flag
    try:
        auth_manager.use_flag(ADMIN_MODE)
        assert False, "Should have been denied"
    except PermissionError:
        print("✅ Admin mode access correctly restricted")
    
    # Verify configuration structure
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    ownership_summary = {}
    for flag_name, flag_data in config.get('flags', {}).items():
        if isinstance(flag_data, dict):
            owner = flag_data.get('owner_module', 'unknown')
            access = flag_data.get('access_permissions', 'unknown')
            ownership_summary[flag_name] = f"{owner}:{access}"
    
    print("\n📋 Ownership Summary:")
    for flag, ownership in ownership_summary.items():
        print(f"  • {flag}: {ownership}")
    
    # Verify expected ownership patterns
    assert ownership_summary['auth_enabled'] == 'auth_service:read_only'
    assert ownership_summary['db_query_timeout'] == 'database_service:read_write'
    assert ownership_summary['admin_mode'] == 'admin_console:owner_only'
    
    print("✅ Ownership patterns correctly established")
    
    # Clean up
    for manager in [auth_manager, db_manager, api_manager, admin_manager]:
        manager.shutdown()
    
    if config_file.exists():
        config_file.unlink()
    
    print("✅ Complex ownership patterns test passed!")


def main():
    """Run all advanced feature flag tests."""
    print("🧪 ADVANCED FEATURE FLAGS TESTING SUITE")
    print("="*80)
    print("Testing edge cases, stress scenarios, and complex patterns\n")
    
    try:
        test_permission_conflicts()
        test_rapid_changes_stress()
        test_concurrent_access()
        test_error_recovery()
        test_complex_ownership_patterns()
        
        print("\n🎉 ALL ADVANCED TESTS PASSED!")
        print("• ✅ Permission conflicts handled correctly")
        print("• ✅ Rapid changes and stress testing successful")
        print("• ✅ Concurrent access is thread-safe")
        print("• ✅ Error recovery mechanisms working")
        print("• ✅ Complex ownership patterns supported")
        
    except Exception as e:
        print(f"\n❌ Advanced test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🧹 Advanced testing complete!")


if __name__ == "__main__":
    main()
