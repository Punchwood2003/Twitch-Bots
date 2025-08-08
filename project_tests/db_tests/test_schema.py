"""
Test Schema Management

Comprehensive test schema management for database testing.
Creates isolated test tables, validates schema operations, and provides
utilities for other tests. Combines schema utilities and validation tests.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Fix Unicode encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add the parent directory to the path so we can import db modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from db.config import get_database_config
import asyncpg


# Test table schemas - isolated from production
TEST_TABLES = {
    'test_users': """
        CREATE TABLE IF NOT EXISTS test_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100),
            points INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """,
    
    'test_transactions': """
        CREATE TABLE IF NOT EXISTS test_transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES test_users(id) ON DELETE CASCADE,
            amount INTEGER NOT NULL,
            transaction_type VARCHAR(50) NOT NULL,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """,
    
    'test_logs': """
        CREATE TABLE IF NOT EXISTS test_logs (
            id SERIAL PRIMARY KEY,
            level VARCHAR(20) NOT NULL,
            message TEXT NOT NULL,
            module VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """,
    
    'test_config': """
        CREATE TABLE IF NOT EXISTS test_config (
            id SERIAL PRIMARY KEY,
            config_key VARCHAR(100) NOT NULL UNIQUE,
            config_value TEXT,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """
}

# Test indexes for performance
TEST_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_test_users_username ON test_users(username)",
    "CREATE INDEX IF NOT EXISTS idx_test_users_active ON test_users(is_active)",
    "CREATE INDEX IF NOT EXISTS idx_test_transactions_user_id ON test_transactions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_test_transactions_type ON test_transactions(transaction_type)",
    "CREATE INDEX IF NOT EXISTS idx_test_logs_level ON test_logs(level)",
    "CREATE INDEX IF NOT EXISTS idx_test_config_key ON test_config(config_key)"
]

# Sample test data
TEST_DATA = [
    "INSERT INTO test_users (username, email, points) VALUES ('testuser1', 'test1@example.com', 100) ON CONFLICT (username) DO NOTHING",
    "INSERT INTO test_users (username, email, points) VALUES ('testuser2', 'test2@example.com', 250) ON CONFLICT (username) DO NOTHING",
    "INSERT INTO test_config (config_key, config_value) VALUES ('test_setting_1', 'value1') ON CONFLICT (config_key) DO NOTHING"
]


async def create_test_schema(conn: asyncpg.Connection) -> bool:
    """Create all test tables, indexes, and sample data."""
    try:
        print("🏗️  Creating test schema...")
        
        # Create tables
        for table_name, schema_sql in TEST_TABLES.items():
            await conn.execute(schema_sql)
        
        # Create indexes
        for index_sql in TEST_INDEXES:
            await conn.execute(index_sql)
        
        # Insert sample data
        for query in TEST_DATA:
            await conn.execute(query)
        
        print(f"   ✅ Created {len(TEST_TABLES)} tables, {len(TEST_INDEXES)} indexes")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test schema: {e}")
        return False


async def cleanup_test_schema(conn: asyncpg.Connection) -> bool:
    """Clean up test tables."""
    try:
        print("🧹 Cleaning up test schema...")
        
        # Drop in reverse dependency order
        for table_name in ['test_transactions', 'test_logs', 'test_config', 'test_users']:
            await conn.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
        
        print("   ✅ Test schema cleaned up")
        return True
        
    except Exception as e:
        print(f"❌ Failed to cleanup test schema: {e}")
        return False


async def validate_test_schema(conn: asyncpg.Connection) -> bool:
    """Validate test schema exists and is functional."""
    try:
        # Check tables exist
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name LIKE 'test_%'
        """)
        
        existing_tables = {t['table_name'] for t in tables}
        expected_tables = set(TEST_TABLES.keys())
        
        if not expected_tables.issubset(existing_tables):
            missing = expected_tables - existing_tables
            print(f"❌ Missing test tables: {missing}")
            return False
        
        # Quick data validation
        user_count = await conn.fetchval("SELECT COUNT(*) FROM test_users")
        print(f"   ✅ Schema validated - {len(existing_tables)} tables, {user_count} test users")
        return True
        
    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False


async def test_crud_operations(conn: asyncpg.Connection) -> bool:
    """Test CRUD operations on test tables."""
    try:
        # CREATE
        user_id = await conn.fetchval("""
            INSERT INTO test_users (username, email, points) 
            VALUES ('crud_test_user', 'crud@test.com', 500) 
            RETURNING id
        """)
        
        # READ
        user = await conn.fetchrow("SELECT * FROM test_users WHERE id = $1", user_id)
        assert user['points'] == 500
        
        # UPDATE  
        await conn.execute("UPDATE test_users SET points = $1 WHERE id = $2", 750, user_id)
        updated_points = await conn.fetchval("SELECT points FROM test_users WHERE id = $1", user_id)
        assert updated_points == 750
        
        # Test foreign key relationship
        await conn.fetchval("""
            INSERT INTO test_transactions (user_id, amount, transaction_type, description)
            VALUES ($1, $2, $3, $4) RETURNING id
        """, user_id, 100, 'test_transaction', 'CRUD test')
        
        # DELETE (tests cascade)
        await conn.execute("DELETE FROM test_users WHERE id = $1", user_id)
        
        # Verify cascade worked
        remaining = await conn.fetchval("SELECT COUNT(*) FROM test_transactions WHERE user_id = $1", user_id)
        assert remaining == 0
        
        print("   ✅ CRUD operations validated")
        return True
        
    except Exception as e:
        print(f"❌ CRUD operations failed: {e}")
        return False


async def setup_test_environment():
    """Set up complete test environment."""
    try:
        config = get_database_config()
        conn = await asyncpg.connect(**config.get_connection_params())
        
        # Clean and recreate
        await cleanup_test_schema(conn)
        success = await create_test_schema(conn)
        
        await conn.close()
        return success
        
    except Exception as e:
        print(f"❌ Test environment setup failed: {e}")
        return False


async def teardown_test_environment():
    """Clean up test environment."""
    try:
        config = get_database_config()
        conn = await asyncpg.connect(**config.get_connection_params())
        
        await cleanup_test_schema(conn)
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Test environment teardown failed: {e}")
        return False


async def run_schema_tests() -> bool:
    """Run comprehensive schema validation tests."""
    print("🧪 Test Schema Validation Suite")
    print("=" * 50)
    
    try:
        # Setup
        if not await setup_test_environment():
            return False
        
        config = get_database_config()
        conn = await asyncpg.connect(**config.get_connection_params())
        
        # Run validation tests
        tests = [
            ("Schema Structure", validate_test_schema),
            ("CRUD Operations", test_crud_operations),
        ]
        
        passed = 0
        for test_name, test_func in tests:
            print(f"\n🔍 Testing {test_name}...")
            if await test_func(conn):
                passed += 1
                print(f"   ✅ {test_name} passed")
            else:
                print(f"   ❌ {test_name} failed")
        
        await conn.close()
        await teardown_test_environment()
        
        print(f"\n📊 Schema tests: {passed}/{len(tests)} passed")
        return passed == len(tests)
        
    except Exception as e:
        print(f"❌ Schema tests failed: {e}")
        await teardown_test_environment()
        return False


if __name__ == "__main__":
    async def main():
        print("🧪 Test Schema Management")
        print("=" * 40)
        
        success = await run_schema_tests()
        
        if success:
            print("\n✅ Test schema system working correctly!")
        else:
            print("\n❌ Test schema system has issues!")
    
    asyncio.run(main())
