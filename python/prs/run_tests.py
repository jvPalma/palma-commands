#!/usr/bin/env python3
"""
Test runner for PRS unit tests.

This script runs all unit tests and provides a summary of results.
It can be used for continuous integration or local development.
"""

import sys
import subprocess
import os
from pathlib import Path

def run_tests():
    """Run all unit tests and return success status."""
    # Change to the project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Test files to run
    test_files = [
        # Core module tests
        'prs/core/__tests__/test_models.py',
        'prs/core/__tests__/test_printPullRequests.py',
        'prs/core/__tests__/test_helpers.py',
        'prs/core/__tests__/test_user_filtering.py',
        
        # Core submodule tests
        'prs/core/author/__tests__/test_helpers.py',
        'prs/core/display/__tests__/test_display_config.py',
        'prs/core/display/__tests__/test_feature_renderers.py',
        'prs/core/display/__tests__/test_panel_renderer.py',
        
        # Main module tests
        'prs/__tests__/test_config.py',
        'prs/__tests__/test_cli.py',
        
        # VC Tools tests
        'prs/vc_tools/github/__tests__/test_adapter.py',
        'prs/vc_tools/github/__tests__/test_client.py'
    ]
    
    print("Running PRS Unit Tests")
    print("=" * 50)
    
    all_passed = True
    results = {}
    
    for test_file in test_files:
        print(f"\nRunning tests in {test_file}...")
        print("-" * 40)
        
        try:
            # Run pytest on the specific file
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                test_file, 
                '-v',  # Verbose output
                '--tb=short',  # Short traceback format
                '--no-header',  # No header info
                '--no-summary'  # No summary at end of each file
            ], capture_output=True, text=True, cwd=project_root)
            
            if result.returncode == 0:
                print(f"✓ PASSED: {test_file}")
                results[test_file] = "PASSED"
            else:
                print(f"✗ FAILED: {test_file}")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                results[test_file] = "FAILED"
                all_passed = False
                
        except Exception as e:
            print(f"✗ ERROR running {test_file}: {e}")
            results[test_file] = f"ERROR: {e}"
            all_passed = False
    
    # Print summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed_count = 0
    failed_count = 0
    
    for test_file, status in results.items():
        status_symbol = "✓" if status == "PASSED" else "✗"
        print(f"{status_symbol} {test_file}: {status}")
        
        if status == "PASSED":
            passed_count += 1
        else:
            failed_count += 1
    
    print(f"\nResults: {passed_count} passed, {failed_count} failed")
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return True
    else:
        print(f"\n❌ {failed_count} test file(s) failed")
        return False

def install_dependencies():
    """Install required test dependencies."""
    print("Installing test dependencies...")
    try:
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', 'pytest', 'pytest-mock'
        ], check=True)
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False

def main():
    """Main entry point."""
    print("PRS Unit Test Runner")
    print("=" * 50)
    
    # Check if pytest is available
    try:
        import pytest
        print("✓ pytest is available")
    except ImportError:
        print("pytest not found, attempting to install...")
        if not install_dependencies():
            print("Failed to install dependencies. Exiting.")
            sys.exit(1)
    
    # Run the tests
    success = run_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()