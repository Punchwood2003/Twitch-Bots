"""
Comprehensive Test Suite Runner

This script runs all tests across the entire project in the correct order:
1. Database infrastructure tests (configuration, connections, schemas)
2. Feature flag tests (basic, advanced, multi-process)

Usage:
    python run_all_tests.py
    python run_all_tests.py --verbose
    python run_all_tests.py --suite database
    python run_all_tests.py --suite feature_flags
    python run_all_tests.py --suite all
"""

import sys
import subprocess
import time
from pathlib import Path
import argparse
import os
from typing import Tuple

# Fix Unicode encoding for Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    os.system('chcp 65001 > nul')


class TestSuite:
    """Represents a test suite with its tests."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.tests = []
    
    def add_test(self, test_name: str, test_path: Path, args: list = None, description: str = ""):
        """Add a test to this suite."""
        self.tests.append({
            'name': test_name,
            'path': test_path,
            'args': args or [],
            'description': description
        })


class ComprehensiveTestRunner:
    """Manages execution of all project test suites."""
    
    def __init__(self):
        self.suites = {}
        self.setup_test_suites()
    
    def setup_test_suites(self):
        """Define all test suites and their tests."""
        base_dir = Path(__file__).parent
        
        # Database Test Suite
        db_suite = TestSuite("database", "Database Infrastructure Tests")
        db_suite.add_test("quick_check", base_dir / "db_tests" / "run_db_tests.py", ["--quick"], "Quick connectivity check")
        db_suite.add_test("full_suite", base_dir / "db_tests" / "run_db_tests.py", [], "Complete database test suite")
        self.suites["database"] = db_suite
        
        # Feature Flags Test Suite  
        ff_suite = TestSuite("feature_flags", "Feature Flags System Tests")
        ff_suite.add_test("basic", base_dir / "feature_flags" / "test_basic_functionality.py", [], "Basic flag operations")
        ff_suite.add_test("advanced", base_dir / "feature_flags" / "test_advanced_feature_flags.py", [], "Advanced features")
        ff_suite.add_test("multiprocess", base_dir / "feature_flags" / "test_multi_process_feature_flags.py", [], "Multi-process simulation")
        self.suites["feature_flags"] = ff_suite
    
    def run_test(self, test_name: str, test_path: Path, args: list = None, verbose: bool = False) -> bool:
        """Run a single test file."""
        print(f"\n{'='*60}")
        print(f"🧪 RUNNING {test_name.upper()}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            cmd = [sys.executable, str(test_path)]
            if args:
                cmd.extend(args)
                
            if verbose:
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                result = subprocess.run(cmd, capture_output=False, text=True, check=True, env=env)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                if result.stdout:
                    print(result.stdout)
            
            duration = time.time() - start_time
            print(f"\n✅ {test_name} completed successfully in {duration:.2f}s")
            return True
            
        except subprocess.CalledProcessError as e:
            duration = time.time() - start_time
            print(f"\n❌ {test_name} failed in {duration:.2f}s")
            if not verbose and e.stdout:
                print("STDOUT:", e.stdout)
            if e.stderr:
                print("STDERR:", e.stderr)
            return False
        except Exception as e:
            duration = time.time() - start_time
            print(f"\n❌ {test_name} error in {duration:.2f}s: {e}")
            return False
    
    def run_suite(self, suite_name: str, verbose: bool = False) -> Tuple[int, int]:
        """Run all tests in a suite."""
        if suite_name not in self.suites:
            print(f"❌ Unknown test suite: {suite_name}")
            return 0, 0
        
        suite = self.suites[suite_name]
        print(f"\n🚀 STARTING {suite.name.upper()} TEST SUITE")
        print(f"📋 {suite.description}")
        print("=" * 80)
        
        passed = 0
        total = len(suite.tests)
        
        for test in suite.tests:
            success = self.run_test(
                test['name'], 
                test['path'], 
                test['args'],
                verbose
            )
            if success:
                passed += 1
        
        print(f"\n📊 {suite.name.upper()} SUITE RESULTS:")
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}")
        
        return passed, total
    
    def run_all_suites(self, verbose: bool = False) -> bool:
        """Run all test suites."""
        print("🧪" * 40)
        print("🧪 COMPREHENSIVE PROJECT TEST SUITE 🧪")
        print("🧪" * 40)
        
        total_passed = 0
        total_tests = 0
        suite_results = {}
        
        # Run test suites in order
        for suite_name in ["database", "feature_flags"]:
            passed, total = self.run_suite(suite_name, verbose)
            suite_results[suite_name] = (passed, total)
            total_passed += passed
            total_tests += total
        
        # Final summary
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 80)
        
        for suite_name, (passed, total) in suite_results.items():
            suite = self.suites[suite_name]
            status = "✅" if passed == total else "❌"
            print(f"{status} {suite.description}: {passed}/{total}")
        
        print(f"\n🔢 Overall Results:")
        print(f"✅ Total Passed: {total_passed}")
        print(f"❌ Total Failed: {total_tests - total_passed}")
        print(f"📈 Success Rate: {(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "No tests run")
        
        if total_passed == total_tests:
            print("\n🎉 ALL TESTS PASSED! Project infrastructure is working correctly.")
            print("📋 Validated systems:")
            print("  • ✅ Database infrastructure (config, connections, schemas)")
            print("  • ✅ Feature flags system (basic, advanced, multi-process)")
            print("  • ✅ Cross-system integration")
            return True
        else:
            print(f"\n⚠️  {total_tests - total_passed} test(s) failed.")
            print("💡 Use --verbose for detailed output")
            print("💡 Run specific suites with --suite <name>")
            return False
    
    def list_suites(self):
        """List all available test suites."""
        print("📋 Available Test Suites:")
        print("-" * 40)
        for suite_name, suite in self.suites.items():
            print(f"\n🔧 {suite_name}:")
            print(f"   📝 {suite.description}")
            for test in suite.tests:
                print(f"   • {test['name']}: {test['description']}")


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Run comprehensive project tests")
    parser.add_argument("--suite", choices=["all", "database", "feature_flags"], 
                       default="all", help="Test suite to run")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--list", action="store_true", help="List available test suites")
    
    args = parser.parse_args()
    
    runner = ComprehensiveTestRunner()
    
    if args.list:
        runner.list_suites()
        return True
    
    start_time = time.time()
    
    try:
        if args.suite == "all":
            success = runner.run_all_suites(args.verbose)
        else:
            passed, total = runner.run_suite(args.suite, args.verbose)
            success = passed == total
        
        total_duration = time.time() - start_time
        print(f"\n⏱️  Total execution time: {total_duration:.2f}s")
        
        return success
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n\n❌ Test runner error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
