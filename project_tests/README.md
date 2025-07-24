# Testing Suite

## 📋 **Overview**

This directory contains the comprehensive testing suite for the different systems of this project, providing organized test execution and development debugging tools.

## 🗂️ **Directory Structure**

```
project_tests/
├── README.md         # This documentation
├── .temp/            # Temporary test files (gitignored)
│   └── .gitignore    # Automatically ignores *.json files
├── run_all_tests.py  # Main test orchestrator
└── feature_flags/    # Feature flag test suite
```

## 🧪 **Test Files Overview**

### **Core Test Suite**

#### 🔧 **`run_all_tests.py`** - Test Orchestrator
- **Purpose**: Central entry point for all test execution
- **Features**: 
  - Individual test selection (`--test basic`, `--test advanced`)
  - Verbose output mode (`--verbose`)
  - Pass/fail tracking with summary reporting
  - Subprocess management with UTF-8 environment

## 🚀 **Usage Examples**

### **Running Tests**

```bash
# Run all tests from project root
python project_tests/run_all_tests.py

# Run specific test categories
python project_tests/run_all_tests.py --test basic
python project_tests/run_all_tests.py --test advanced
python project_tests/run_all_tests.py --test multiprocess

# Enable verbose output for troubleshooting
python project_tests/run_all_tests.py --verbose

# Run individual test files directly
python project_tests/feature_flags/test_basic_functionality.py
python project_tests/feature_flags/debug_feature_flags.py
```

### **From Different Directories**

```bash
# Works from project root
python project_tests/run_all_tests.py

# Also works from project_tests directory
cd project_tests
python run_all_tests.py --test basic
python feature_flags/debug_feature_flags.py
```

## 🗃️ **File Organization Features**

### **Organized Temporary Files**
- All test configurations stored in `project_tests/.temp/`
- Automatic cleanup after test completion
- Gitignored temporary files
