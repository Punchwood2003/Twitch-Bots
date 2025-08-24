# Module System Tests

This directory contains tests for the modular Twitch bot system.

## Test Files

### `simple_module_test.py`
Basic functionality test that verifies:
- Module creation and initialization
- Feature flag declaration and configuration
- Database schema definition
- Command registration
- Manager injection (FeatureFlagManager and ModuleDatabaseManager)

### `test_module_system.py`
Comprehensive test that verifies:
- Module registration with the module manager
- Module lifecycle (start/stop/restart)
- Enable/disable functionality
- Command registration and management
- Module status tracking
- Feature flag integration
- Database schema integration

## Running Tests

From the project root directory:

```bash
# Run simple functionality test
python project_tests/module_tests/simple_module_test.py

# Run comprehensive system test
python project_tests/module_tests/test_module_system.py
```

Or from the project_tests directory:

```bash
# Run simple functionality test
python module_tests/simple_module_test.py

# Run comprehensive system test
python module_tests/test_module_system.py
```

## Test Requirements

- Python virtual environment activated
- All project dependencies installed
- Database connection available (for comprehensive tests)

## Expected Output

Both tests should complete successfully with all checkmarks (✓) showing passed tests.
The comprehensive test includes async operations that may take a few seconds to complete.

## Test Coverage

These tests verify:
- ✅ Module registration and discovery
- ✅ Feature flag system integration
- ✅ Database schema management
- ✅ Command system functionality
- ✅ Module lifecycle management
- ✅ Dependency injection
- ✅ Enable/disable capabilities
- ✅ Status tracking and reporting
