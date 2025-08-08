# Database Testing Suite

Comprehensive testing framework for the Twitch Bot modular database infrastructure.

## 📋 **Overview**

This testing suite validates the modular database system including:
- Configuration management
- Modular connection lifecycle
- Test schema management (isolated from production)
- CRUD operations on test tables
- Integration testing for the modular system
- Error handling and resource cleanup

## 🗂️ **Test Structure**

```
project_tests/db_tests/
├── __init__.py                # Package initialization
├── README.md                  # This documentation
├── run_db_tests.py            # Main test runner
├── test_basic_database.py     # Core functionality tests
├── test_schema.py             # Schema management & validation
└── test_integration.py        # Modular system integration tests
```

## 🏃‍♂️ **Quick Start**

### Run All Tests
```bash
python project_tests/db_tests/run_db_tests.py
```

### Quick Connectivity Check
```bash
python project_tests/db_tests/run_db_tests.py --quick
```

### Run Individual Test Files
```bash
# Basic functionality tests
python project_tests/db_tests/test_basic_database.py

# Test schema management
python project_tests/db_tests/test_schema.py

# Schema validation tests
python project_tests/db_tests/test_schema.py

# Modular system integration tests
python project_tests/db_tests/test_integration.py
```

## 📑 **Performance Benchmarks**

The tests include basic performance validation:
- Health checks should complete within 1 second
- Basic CRUD operations should complete within 2 seconds
- Modular integration tests should complete within 30 seconds

## 📈 **Environment Setup**

### Required Environment Variables
```env
# Database Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=sb_publishable_...
SUPABASE_SERVICE_ROLE_KEY=sb_secret_... 

# These are automatically derived from Supabase URL
DB_HOST=aws-0-us-east-2.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.your-project-id
DB_PASSWORD=your-database-password
```

### Dependencies
Ensure these packages are installed:
```bash
pip install requirements.txt
```

## 🧪 **Test Categories**

### 1. Basic Database Tests (`test_basic_database.py`)

Tests core modular database functionality:

- **Configuration Loading**: Validates environment variable loading and database URL generation
- **Connection Lifecycle**: Tests modular database manager setup, connection, and cleanup
- **Health Checks**: Validates database health monitoring functionality
- **Session Management**: Tests async session creation and concurrent access
- **Database Information**: Retrieves and validates database metadata
- **Error Handling**: Tests behavior with invalid configurations

### 2. Test Schema Management (`test_schema.py`)

Manages isolated test tables (separate from production):

- **Test Table Creation**: Creates isolated test tables for safe testing
- **Test Data Insertion**: Populates test tables with sample data
- **CRUD Operations**: Tests Create, Read, Update, Delete operations on test tables
- **Schema Cleanup**: Removes test tables after testing
- **Data Integrity**: Tests constraints and validation on test tables

### 3. Schema Management Tests (`test_schema.py`)

Comprehensive schema testing with utilities and validation:

- **Schema Creation**: Creates isolated test tables and indexes
- **CRUD Operations**: Tests Create, Read, Update, Delete functionality
- **Schema Validation**: Validates table structure and relationships
- **Test Environment**: Setup/teardown utilities for clean testing
- **Data Integrity**: Tests constraints and foreign key relationships
- **Consolidated**: Previously split across multiple files, now unified

### 4. Modular System Integration Tests (`test_integration.py`)

Tests the complete modular database system:

- **Configuration Integration**: Tests configuration loading for modules
- **Modular Connection Management**: Tests per-module database managers
- **Schema System Integration**: Tests schema querying without production dependencies
- **Resource Cleanup**: Validates proper cleanup of modular resources

## 🛠️ **Common Issues and Solutions**

### Configuration Issues
```
❌ Configuration test failed: Missing environment variable

Solution:
1. Ensure .env file exists in project root
2. Verify all required variables are set:
   - SUPABASE_URL
   - SUPABASE_ANON_KEY  
   - SUPABASE_SERVICE_ROLE_KEY
```

### Connection Issues
```
❌ Connection lifecycle test failed: Connection timeout

Solutions:
1. Check internet connectivity
2. Verify Supabase project is active
3. Confirm database URL is correct
4. Check firewall settings
```

### Schema Issues
```
❌ Schema validation failed: Test tables not found

Solutions:
1. Tests create their own isolated test tables
2. Check database permissions
3. Verify modular database manager is working
```
