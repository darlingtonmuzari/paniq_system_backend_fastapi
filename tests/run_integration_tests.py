#!/usr/bin/env python3
"""
Integration Test Runner
Runs all integration tests with proper setup and teardown
"""
import os
import sys
import asyncio
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"ERROR: {description} failed!")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return False
    else:
        print(f"SUCCESS: {description} completed")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True


def setup_test_environment():
    """Set up the test environment"""
    print("Setting up integration test environment...")
    
    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "postgresql://postgres:password@localhost:5432/panic_system_test"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    
    # Create test database if it doesn't exist
    create_db_command = """
    psql -h localhost -U postgres -c "CREATE DATABASE panic_system_test;" || true
    """
    
    if not run_command(create_db_command, "Create test database"):
        print("Warning: Could not create test database (it might already exist)")
    
    return True


def run_integration_tests():
    """Run all integration tests"""
    test_commands = [
        {
            "command": "python -m pytest tests/integration/test_api_integration.py -v --tb=short",
            "description": "API Integration Tests"
        },
        {
            "command": "python -m pytest tests/integration/test_database_integration.py -v --tb=short",
            "description": "Database Integration Tests"
        },
        {
            "command": "python -m pytest tests/integration/test_external_services_integration.py -v --tb=short",
            "description": "External Services Integration Tests"
        },
        {
            "command": "python -m pytest tests/integration/test_end_to_end_workflows.py -v --tb=short",
            "description": "End-to-End Workflow Tests"
        },
        {
            "command": "python -m pytest tests/integration/test_performance_load.py -v --tb=short -m 'not slow'",
            "description": "Performance Tests (Fast)"
        }
    ]
    
    results = []
    
    for test in test_commands:
        success = run_command(test["command"], test["description"])
        results.append((test["description"], success))
    
    return results


def run_performance_tests():
    """Run performance and load tests separately"""
    print("\n" + "="*60)
    print("Running Performance and Load Tests")
    print("="*60)
    
    perf_command = "python -m pytest tests/integration/test_performance_load.py -v --tb=short"
    return run_command(perf_command, "Performance and Load Tests")


def generate_test_report(results):
    """Generate a test report"""
    print("\n" + "="*60)
    print("INTEGRATION TEST RESULTS")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    failed_tests = total_tests - passed_tests
    
    for test_name, success in results:
        status = "PASSED" if success else "FAILED"
        print(f"{test_name:<40} {status}")
    
    print(f"\nSummary:")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    return failed_tests == 0


def cleanup_test_environment():
    """Clean up test environment"""
    print("\nCleaning up test environment...")
    
    # Drop test database
    drop_db_command = """
    psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS panic_system_test;"
    """
    
    run_command(drop_db_command, "Drop test database")


def main():
    """Main test runner function"""
    print("Panic System Platform - Integration Test Runner")
    print("=" * 60)
    
    # Parse command line arguments
    run_perf_tests = "--performance" in sys.argv or "--all" in sys.argv
    run_all_tests = "--all" in sys.argv
    
    try:
        # Setup
        if not setup_test_environment():
            print("Failed to set up test environment")
            return 1
        
        # Run integration tests
        results = run_integration_tests()
        
        # Run performance tests if requested
        if run_perf_tests:
            perf_success = run_performance_tests()
            results.append(("Performance Tests", perf_success))
        
        # Generate report
        all_passed = generate_test_report(results)
        
        # Cleanup
        if "--no-cleanup" not in sys.argv:
            cleanup_test_environment()
        
        return 0 if all_passed else 1
        
    except KeyboardInterrupt:
        print("\nTest run interrupted by user")
        cleanup_test_environment()
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        cleanup_test_environment()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)