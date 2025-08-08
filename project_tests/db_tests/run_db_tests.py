"""
Database Test Runner

Comprehensive test runner for all database-related tests.
Runs tests in order from basic functionality to advanced integration.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

# Fix Unicode encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add the parent directory to the path so we can import all modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestResult:
    """Represents the result of a test execution."""
    
    def __init__(self, name: str, passed: bool, duration: float, message: str = ""):
        self.name = name
        self.passed = passed
        self.duration = duration
        self.message = message


class DatabaseTestRunner:
    """Manages execution of all database tests."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.total_duration = 0.0
    
    async def run_test_module(self, module_name: str, test_function: str) -> TestResult:
        """Run a specific test module and function."""
        start_time = time.time()
        
        try:
            # Dynamically import the test module
            module = __import__(f"project_tests.db_tests.{module_name}", fromlist=[test_function])
            test_func = getattr(module, test_function)
            
            # Run the test
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            
            duration = time.time() - start_time
            
            if success:
                return TestResult(module_name, True, duration, "✅ Passed")
            else:
                return TestResult(module_name, False, duration, "❌ Failed")
                
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(module_name, False, duration, f"❌ Error: {str(e)}")
    
    def print_header(self):
        """Print the test runner header."""
        print("🧪" * 30)
        print("🧪 COMPREHENSIVE DATABASE TEST SUITE 🧪")
        print("🧪" * 30)
        print("\n📋 Test Execution Plan:")
        print("   1. Basic Database Functionality")
        print("   2. Schema Setup and Validation")
        print("   3. Full Integration Testing")
        print("\n🚀 Starting test execution...\n")
    
    def print_test_start(self, test_name: str):
        """Print test start message."""
        print(f"🔄 Running {test_name}...")
    
    def print_test_result(self, result: TestResult):
        """Print individual test result."""
        status = "✅ PASSED" if result.passed else "❌ FAILED"
        print(f"   {status} - {result.name} ({result.duration:.2f}s)")
        if result.message and not result.passed:
            print(f"   Message: {result.message}")
    
    def print_summary(self):
        """Print comprehensive test summary."""
        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        success_rate = (passed_count / total_count * 100) if total_count > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 60)
        
        # Overall statistics
        print(f"🔢 Total Tests: {total_count}")
        print(f"✅ Passed: {passed_count}")
        print(f"❌ Failed: {total_count - passed_count}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"⏱️  Total Duration: {self.total_duration:.2f}s")
        
        # Individual test results
        print("\n📋 Individual Test Results:")
        for result in self.results:
            status_icon = "✅" if result.passed else "❌"
            print(f"   {status_icon} {result.name:<25} ({result.duration:.2f}s)")
        
        # Final assessment
        print("\n🎯 ASSESSMENT:")
        if success_rate == 100:
            print("🎉 EXCELLENT! All database systems are fully operational!")
            print("   • Database infrastructure is ready for production")
            print("   • All core functionality validated")
            print("   • Integration tests successful")
        elif success_rate >= 80:
            print("⚠️  GOOD! Most database systems are working correctly.")
            print("   • Core functionality is operational")
            print("   • Minor issues may need attention")
            print("   • Database is usable for development")
        elif success_rate >= 60:
            print("⚠️  PARTIAL! Some database systems need attention.")
            print("   • Basic functionality may be working")
            print("   • Several components need fixes")
            print("   • Review failed tests before proceeding")
        else:
            print("❌ CRITICAL! Major database issues detected.")
            print("   • Core functionality is compromised")
            print("   • Immediate attention required")
            print("   • Review configuration and connectivity")
        
        print("=" * 60)
    
    async def run_all_tests(self):
        """Run all database tests in the proper sequence."""
        self.print_header()
        
        # Define test sequence - streamlined for modular system
        test_sequence = [
            ("test_basic_database", "run_basic_tests", "Basic Database Functionality"),
            ("test_schema", "run_schema_tests", "Test Schema Management"),
            ("test_integration", "run_integration_tests", "Modular System Integration"),
        ]
        
        start_time = time.time()
        
        # Run tests in sequence
        for module_name, function_name, display_name in test_sequence:
            self.print_test_start(display_name)
            result = await self.run_test_module(module_name, function_name)
            self.results.append(result)
            self.print_test_result(result)
            print()  # Add spacing between tests
        
        self.total_duration = time.time() - start_time
        self.print_summary()
        
        # Return overall success
        return all(result.passed for result in self.results)


async def main():
    """Main test runner function."""
    print("Initializing comprehensive database test suite...\n")
    
    runner = DatabaseTestRunner()
    
    try:
        success = await runner.run_all_tests()
        
        # Exit with appropriate code
        exit_code = 0 if success else 1
        
        if success:
            print("\n🎉 All database tests completed successfully!")
            print("   Database infrastructure is ready for use.")
        else:
            print("\n⚠️  Some tests failed. Please review the results above.")
            print("   Check configuration, connectivity, and failed test details.")
        
        return exit_code
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR in test runner: {e}")
        print("   Test execution could not complete.")
        return 1


def run_quick_check():
    """Run a quick connectivity check without full tests."""
    print("🔍 Quick Database Connectivity Check")
    print("-" * 40)
    
    try:
        # Import and test basic config loading
        from db.config import get_database_config
        config = get_database_config()
        print(f"✅ Configuration loaded: {config.db_host}:{config.db_port}")
        return True
    except Exception as e:
        print(f"❌ Quick check failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Quick check mode
        success = run_quick_check()
        sys.exit(0 if success else 1)
    else:
        # Full test suite
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
