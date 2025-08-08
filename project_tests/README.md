# Project Tests

## 📋 **Overview**

This directory contains the comprehensive testing suite for the different systems of this project, providing organized test execution and development debugging tools.

## 🗂️ **Directory Structure**

```
project_tests/
├── README.md                   # This documentation
├── run_all_tests.py            # Comprehensive test runner
├── db_tests/                   # Database infrastructure tests
└── feature_flags/              # Feature flags system tests
```

## 🏃‍♂️ **Quick Start**

```bash
# Run all tests
python run_all_tests.py

# Run specific test suite
python run_all_tests.py --suite database
python run_all_tests.py --suite feature_flags

# List available test suites
python run_all_tests.py --list

# Verbose output for debugging
python run_all_tests.py --verbose
```

## 🧪 **Test Suites**

### Database Infrastructure Tests (`--suite database`)
- **Quick Check**: Fast connectivity verification
- **Full Suite**: Comprehensive database infrastructure validation
  - Configuration loading and validation
  - Connection lifecycle management  
  - Schema manager functionality
  - Module integration testing

### Feature Flags System Tests (`--suite feature_flags`)
- **Basic**: Core feature flag operations
- **Advanced**: Complex scenarios and edge cases
- **Multi-process**: Concurrent access simulation

## 📃 **Test Runner Features**

- 🧪 **Unified Interface**: Single command to run all project tests
- 📊 **Detailed Reports**: Success rates, timing, and failure analysis
- 🎯 **Selective Testing**: Run individual suites or all tests
- 🔍 **Debug Support**: Verbose mode for troubleshooting
- ⏱️ **Performance Tracking**: Execution time monitoring

## 🏗️ **Architecture**

The comprehensive test runner (`run_all_tests.py`) manages test execution across:

1. **Database Infrastructure** (`db_tests/`)
   - Configuration validation
   - Connection management
   - Schema operations
   - Integration testing

2. **Feature Flags System** (`feature_flags/`)
   - Basic functionality
   - Advanced features
   - Multi-process scenarios

## 🚀 **Usage Examples**

### Running All Tests
```bash
# Run complete test suite
python run_all_tests.py

# Expected output:
# 🧪 COMPREHENSIVE PROJECT TEST SUITE 🧪
# 🚀 STARTING DATABASE TEST SUITE
# 🚀 STARTING FEATURE_FLAGS TEST SUITE
# ...
# 🎉 ALL TESTS PASSED! Project infrastructure is working correctly.
```

### Running Specific Test Suites
```bash
# Database tests only
python run_all_tests.py --suite database

# Feature flags tests only
python run_all_tests.py --suite feature_flags
```

### Debugging Failed Tests
```bash
# Verbose output for troubleshooting
python run_all_tests.py --verbose

# List all available test suites
python run_all_tests.py --list
```

### Running Individual Tests
```bash
# Direct test execution
cd db_tests
python run_db_tests.py --quick

cd ../feature_flags
python test_basic_functionality.py
```