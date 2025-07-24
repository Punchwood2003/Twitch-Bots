"""
Feature Flags Test Suite Runner

This script runs all feature flag tests in the correct order:
1. Basic functionality tests (core operations, observers, permissions)
2. Advanced tests (edge cases, stress testing, concurrent access)
3. Multi-process simulation tests

Usage:
    python run_all_tests.py
    python run_all_tests.py --verbose
    python run_all_tests.py --test basic
    python run_all_tests.py --test advanced
    python run_all_tests.py --test multiprocess
"""

import sys
import subprocess
import time
from pathlib import Path
import argparse
import os

# Fix Unicode encoding for Windows terminal
if sys.platform == "win32":
    # Set UTF-8 encoding for stdout/stderr
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    # Set console code page to UTF-8
    os.system('chcp 65001 > nul')


def run_test(test_name: str, test_path: Path, verbose: bool = False) -> bool:
    """Run a single test file and return success status."""
    print(f"\n{'='*60}")
    print(f"🧪 RUNNING {test_name.upper()} TESTS")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        if verbose:
            # Set UTF-8 environment for subprocess
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            result = subprocess.run([sys.executable, str(test_path)], 
                                    capture_output=False, 
                                    text=True, 
                                    check=True,
                                    env=env)
        else:
            # Set UTF-8 environment for subprocess
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            result = subprocess.run([sys.executable, str(test_path)], 
                                    capture_output=True, 
                                    text=True, 
                                    check=True,
                                    encoding='utf-8',
                                    env=env)
            print(result.stdout)
        
        duration = time.time() - start_time
        print(f"\n✅ {test_name} tests PASSED in {duration:.2f}s")
        return True
        
    except subprocess.CalledProcessError as e:
        duration = time.time() - start_time
        print(f"\n❌ {test_name} tests FAILED in {duration:.2f}s")
        if not verbose:
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n💥 {test_name} tests ERROR in {duration:.2f}s: {e}")
        return False


def main():
    """Run the complete test suite."""
    parser = argparse.ArgumentParser(description="Feature Flags Test Suite Runner")
    parser.add_argument("--verbose", "-v", action="store_true", 
                        help="Show verbose output from tests")
    parser.add_argument("--test", "-t", choices=["basic", "advanced", "multiprocess", "debug"], 
                        help="Run only specific test category")
    
    args = parser.parse_args()
    
    # Define test files
    test_dir = Path(__file__).parent / "feature_flags"
    tests = [
        ("basic", test_dir / "test_basic_functionality.py"),
        ("advanced", test_dir / "test_advanced_feature_flags.py"),
        ("multiprocess", test_dir / "test_multi_process_feature_flags.py"),
        ("debug", test_dir / "debug_feature_flags.py"),
    ]
    
    # Verify test files exist
    missing_tests = []
    for test_name, test_path in tests:
        if not test_path.exists():
            missing_tests.append((test_name, test_path))
    
    if missing_tests:
        print("❌ Missing test files:")
        for test_name, test_path in missing_tests:
            print(f"  • {test_name}: {test_path}")
        return False
    
    print("🚀 FEATURE FLAGS TEST SUITE")
    print("=" * 80)
    print(f"Test directory: {test_dir}")
    print(f"Python executable: {sys.executable}")
    
    if args.test:
        # Run specific test
        for test_name, test_path in tests:
            if test_name == args.test:
                success = run_test(test_name, test_path, args.verbose)
                return success
        
        print(f"❌ Test '{args.test}' not found")
        return False
    
    # Run all tests
    start_time = time.time()
    passed = 0
    failed = 0
    
    for test_name, test_path in tests:
        if test_name == "debug":
            # Skip debug test in full suite unless specifically requested
            continue
            
        success = run_test(test_name, test_path, args.verbose)
        if success:
            passed += 1
        else:
            failed += 1
            # Continue running other tests even if one fails
    
    total_duration = time.time() - start_time
    
    # Final summary
    print(f"\n{'='*80}")
    print("🏁 TEST SUITE SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⏱️  Total time: {total_duration:.2f}s")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Feature flag system is working correctly.")
        print("📋 Tested components:")
        print("  • ✅ Basic flag operations (declare, use, get, set)")
        print("  • ✅ Permission system (read-only, read-write, owner-only)")
        print("  • ✅ Observer pattern (real-time notifications)")
        print("  • ✅ Cross-manager communication")
        print("  • ✅ File persistence and atomic writes")
        print("  • ✅ Stress testing and rapid changes")
        print("  • ✅ Concurrent access and thread safety")
        print("  • ✅ Error handling and recovery")
        print("  • ✅ Complex ownership patterns")
        print("  • ✅ Multi-process simulation")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the output above.")
        print("💡 You can run individual tests with: --test <testname>")
        print("💡 Use --verbose for more detailed output")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
