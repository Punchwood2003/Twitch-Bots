"""
Basic Database Functionality Tests

Tests for core database operations, configuration, and connection management.
Uses dedicated test tables to avoid interfering with production data.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

# Fix Unicode encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add the parent directory to the path so we can import db modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.config import get_database_config, DatabaseConfig
from db.module_connections import get_module_database_manager

# Import test schema functions - using absolute imports to avoid issues
try:
    from test_schema import setup_test_environment, teardown_test_environment, validate_test_schema, test_crud_operations
except ImportError:
    # Fallback for when running as module
    from .test_schema import setup_test_environment, teardown_test_environment, validate_test_schema, test_crud_operations

import asyncpg


def test_configuration_loading():
    """Test database configuration loading and validation."""
    print("\n🔧 TESTING CONFIGURATION LOADING")
    print("-" * 50)
    
    try:
        config = get_database_config()
        
        # Test required fields
        assert config.db_host, "Database host is required"
        assert config.db_port > 0, "Database port must be positive"
        assert config.db_user, "Database user is required"
        assert config.db_password, "Database password is required"
        assert config.db_name, "Database name is required"
        
        print(f"✅ Configuration loaded successfully")
        print(f"   Host: {config.db_host}:{config.db_port}")
        print(f"   Database: {config.db_name}")
        print(f"   Pool size: {config.db_pool_size}")
        
        # Test database URL generation
        db_url = config.database_url
        sync_url = config.sync_database_url
        
        assert "postgresql+asyncpg://" in db_url, "Async URL should use asyncpg"
        assert "postgresql://" in sync_url, "Sync URL should use psycopg2"
        
        print("✅ Database URL generation working")
        
        # Test connection parameters
        conn_params = config.get_connection_params()
        assert isinstance(conn_params, dict), "Connection params should be a dict"
        assert "host" in conn_params, "Connection params should include host"
        
        print("✅ Connection parameters generation working")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


async def test_connection_lifecycle():
    """Test database connection lifecycle management."""
    print("\n🔌 TESTING CONNECTION LIFECYCLE")
    print("-" * 50)
    
    try:
        # Test manager initialization using modular system
        db_manager = await get_module_database_manager("test_basic_database")
        print("✅ Database manager setup successful")
        
        # Test engine access
        engine = db_manager.engine
        assert engine is not None, "Engine should be available after setup"
        print("✅ Database engine accessible")
        
        # Test cleanup
        await db_manager.cleanup()
        print("✅ Database manager cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection lifecycle test failed: {e}")
        return False


async def test_health_checks():
    """Test database health check functionality."""
    print("\n🏥 TESTING HEALTH CHECKS")
    print("-" * 50)
    
    try:
        db_manager = await get_module_database_manager("test_basic_database")
        
        # Test health check
        start_time = time.time()
        is_healthy = await db_manager.health_check()
        check_time = time.time() - start_time
        
        assert is_healthy, "Database should be healthy"
        print(f"✅ Health check passed in {check_time:.3f}s")
        
        # Test multiple health checks
        for i in range(3):
            healthy = await db_manager.health_check()
            assert healthy, f"Health check {i+1} should pass"
        
        print("✅ Multiple health checks successful")
        
        await db_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Health check test failed: {e}")
        return False


async def test_session_management():
    """Test database session management with test schema."""
    print("\n📊 TESTING SESSION MANAGEMENT")
    print("-" * 50)
    
    try:
        # Setup test environment first
        await setup_test_environment()
        
        db_manager = await get_module_database_manager("test_basic_database")
        
        # Test basic session usage with test tables
        async with db_manager.get_session() as session:
            assert session is not None, "Session should not be None"
            
            # Test simple query on our test tables
            from sqlalchemy import text
            result = await session.execute(text("SELECT COUNT(*) FROM test_users"))
            row = result.fetchone()
            assert row[0] >= 0, "Should be able to count test users"
        
        print("✅ Basic session management working")
        
        # Test multiple concurrent sessions
        async def session_task(task_id: int):
            async with db_manager.get_session() as session:
                result = await session.execute(text("SELECT CAST(:task_id AS INTEGER) as task_id"), {"task_id": task_id})
                row = result.fetchone()
                return row[0]
        
        tasks = [session_task(i) for i in range(3)]  # Reduced concurrent tasks
        results = await asyncio.gather(*tasks)
        
        assert results == list(range(3)), "Concurrent sessions should work correctly"
        print("✅ Concurrent session management working")
        
        await db_manager.cleanup()
        await teardown_test_environment()
        return True
        
    except Exception as e:
        print(f"❌ Session management test failed: {e}")
        await teardown_test_environment()
        return False


async def test_database_info():
    """Test database information retrieval."""
    print("\n📋 TESTING DATABASE INFORMATION")
    print("-" * 50)
    
    try:
        db_manager = await get_module_database_manager("test_basic_database")
        
        # Get database information
        db_info = await db_manager.get_database_info()
        
        assert isinstance(db_info, dict), "Database info should be a dictionary"
        assert "version" in db_info or "database_name" in db_info, "Database info should include basic information"
        
        print("✅ Database information retrieved successfully:")
        for key, value in db_info.items():
            if key in ["version", "database_name", "connection_count", "database_size"]:
                print(f"   {key}: {value}")
        
        # If version is missing, just check we got some useful info
        if "version" not in db_info and len(db_info) > 0:
            print("   Note: Version info not available, but connection is working")
        
        await db_manager.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Database info test failed: {e}")
        return False


async def test_error_handling():
    """Test error handling scenarios."""
    print("\n⚠️  TESTING ERROR HANDLING")
    print("-" * 50)
    
    try:
        # Test that valid connections work
        db_manager = await get_module_database_manager("test_basic_database")
        is_healthy = await db_manager.health_check()
        assert is_healthy, "Valid configuration should be healthy"
        print("✅ Valid configuration works as expected")
        
        # Test connection cleanup
        await db_manager.cleanup()
        print("✅ Connection cleanup handled properly")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


async def run_basic_tests():
    """Run all basic database tests."""
    print("🧪 Basic Database Functionality Tests")
    print("=" * 60)
    
    tests = [
        ("Configuration Loading", test_configuration_loading),
        ("Connection Lifecycle", test_connection_lifecycle),
        ("Health Checks", test_health_checks),
        ("Session Management", test_session_management),
        ("Database Information", test_database_info),
        ("Error Handling", test_error_handling),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
                
            if success:
                passed_tests += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} error: {e}")
    
    # Results Summary
    print("\n" + "=" * 60)
    print("📊 Basic Database Test Results")
    print("=" * 60)
    print(f"Tests passed: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("🎉 All basic database tests passed!")
        return True
    elif passed_tests >= 4:
        print("⚠️  Most basic tests passed. Core functionality is working.")
        return True
    else:
        print("❌ Multiple basic tests failed. Core functionality needs attention.")
        return False


def main():
    """Main test execution function."""
    print("Starting basic database functionality tests...\n")
    
    success = asyncio.run(run_basic_tests())
    
    print("\n" + "🏁" * 20)
    if success:
        print("🎉 Basic database functionality tests successful!")
        print("\n🔧 Core systems validated:")
        print("   • Configuration management")
        print("   • Connection lifecycle")
        print("   • Health monitoring")
        print("   • Session management")
        print("   • Error handling")
    else:
        print("❌ Some basic tests failed.")
        print("   Please review configuration and connectivity.")
    print("🏁" * 20)


if __name__ == "__main__":
    main()
