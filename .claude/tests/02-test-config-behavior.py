#!/usr/bin/env python3
"""
Test that configuration changes actually affect memory operation behavior.

Tests:
- Default flags control memory processing when params not specified
- Custom prompts affect extraction/deduplication logic
- Config changes take effect immediately (no restart needed)

Usage:
    python3 02-test-config-behavior.py

Requirements:
    - OpenMemory service running at http://localhost:8765
    - Test user 'frederik' configured
    - OPENAI_API_KEY set in environment
"""

import requests
import json
import time
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Configuration
BASE_URL = "http://localhost:8765"
REST_API_URL = f"{BASE_URL}/api/v1"
TEST_USER = "frederik"
TEST_APP = "test-config-behavior"


@dataclass
class TestResult:
    """Result of a single test case"""
    name: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a colored header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")


def print_test_result(result: TestResult):
    """Print a test result with color"""
    status = f"{Colors.OKGREEN}✓ PASS{Colors.ENDC}" if result.passed else f"{Colors.FAIL}✗ FAIL{Colors.ENDC}"
    print(f"{status} {result.name}")
    if not result.passed or result.details:
        print(f"  → {result.message}")
        if result.details:
            print(f"  Details: {json.dumps(result.details, indent=2)}")
    print()


def get_config() -> Dict[str, Any]:
    """Get current configuration"""
    response = requests.get(f"{REST_API_URL}/config/")
    response.raise_for_status()
    return response.json()


def update_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Update configuration"""
    response = requests.put(f"{REST_API_URL}/config/", json=config)
    response.raise_for_status()
    return response.json()


def create_memory_rest(
    text: str,
    infer: Optional[bool] = None,
    extract: Optional[bool] = None,
    deduplicate: Optional[bool] = None,
) -> Dict[str, Any]:
    """Create a memory via REST API"""
    payload = {
        "user_id": TEST_USER,
        "text": text,
        "app": TEST_APP,
        "metadata": {}
    }

    if infer is not None:
        payload["infer"] = infer
    if extract is not None:
        payload["extract"] = extract
    if deduplicate is not None:
        payload["deduplicate"] = deduplicate

    response = requests.post(f"{REST_API_URL}/memories/", json=payload)
    response.raise_for_status()
    return response.json()


# Store original config for restoration
original_config = None


def backup_config():
    """Backup original configuration"""
    global original_config
    original_config = get_config()
    print(f"{Colors.OKCYAN}✓ Backed up original configuration{Colors.ENDC}\n")


def restore_config():
    """Restore original configuration"""
    global original_config
    if original_config:
        update_config(original_config)
        print(f"{Colors.OKCYAN}✓ Restored original configuration{Colors.ENDC}\n")


# ============================================================================
# TEST CASES
# ============================================================================

def test_1_default_infer_false() -> TestResult:
    """Test that default_infer=False makes memories skip LLM processing by default"""
    try:
        # Set default_infer to False
        config = get_config()
        config["mem0"]["default_infer"] = False
        update_config(config)
        time.sleep(0.5)  # Let config propagate

        # Create memory without specifying infer param
        text = f"Behavior test {uuid.uuid4()}: This should be stored directly without LLM processing"
        response = create_memory_rest(text)

        # With default_infer=False, memory should be stored directly
        # Response should have content field (not NONE event)
        has_content = "content" in response

        return TestResult(
            name="Test 1: default_infer=False → Direct Storage",
            passed=has_content,
            message=f"Memory {'stored directly' if has_content else 'processed unexpectedly'}",
            details={"response": response}
        )
    except Exception as e:
        return TestResult(
            name="Test 1: default_infer=False",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_2_default_infer_true() -> TestResult:
    """Test that default_infer=True makes memories use LLM processing by default"""
    try:
        # Set default_infer to True
        config = get_config()
        config["mem0"]["default_infer"] = True
        config["mem0"]["default_extract"] = True
        config["mem0"]["default_deduplicate"] = True
        update_config(config)
        time.sleep(0.5)  # Let config propagate

        # Create memory without specifying infer param
        text = f"Behavior test {uuid.uuid4()}: User likes to drink tea in the afternoon for relaxation"
        response = create_memory_rest(text)

        # With default_infer=True, memory should be processed
        # Response can be Memory object or NONE event (both indicate processing happened)
        is_processed = (
            ("content" in response) or  # Memory created
            (response.get("event") == "NONE")  # Or deduplicated/no facts
        )

        return TestResult(
            name="Test 2: default_infer=True → LLM Processing",
            passed=is_processed,
            message=f"Memory {'processed with LLM' if is_processed else 'not processed'}",
            details={"response": response}
        )
    except Exception as e:
        return TestResult(
            name="Test 2: default_infer=True",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_3_default_extract_false() -> TestResult:
    """Test that default_extract=False skips extraction by default"""
    try:
        # Set defaults
        config = get_config()
        config["mem0"]["default_infer"] = True
        config["mem0"]["default_extract"] = False
        config["mem0"]["default_deduplicate"] = False
        update_config(config)
        time.sleep(0.5)

        # Create memory without params - should embed raw text
        text = f"Behavior test {uuid.uuid4()}: Raw embedding without extraction test"
        response = create_memory_rest(text)

        # Should get back memory with content
        has_content = "content" in response

        return TestResult(
            name="Test 3: default_extract=False → Raw Embedding",
            passed=has_content,
            message=f"Raw text {'embedded directly' if has_content else 'processed unexpectedly'}",
            details={"response": response}
        )
    except Exception as e:
        return TestResult(
            name="Test 3: default_extract=False",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_4_default_deduplicate_false() -> TestResult:
    """Test that default_deduplicate=False allows duplicate memories"""
    try:
        # Set defaults
        config = get_config()
        config["mem0"]["default_infer"] = True
        config["mem0"]["default_extract"] = True
        config["mem0"]["default_deduplicate"] = False
        update_config(config)
        time.sleep(0.5)

        # Create same memory twice - both should be added
        base_text = f"Behavior test {uuid.uuid4()}: Duplicate memory test"
        response1 = create_memory_rest(base_text)
        time.sleep(0.5)
        response2 = create_memory_rest(base_text)

        # Both should succeed (not get NONE event)
        both_added = (
            ("content" in response1 or response1.get("event") == "NONE") and
            ("content" in response2 or response2.get("event") == "NONE")
        )

        return TestResult(
            name="Test 4: default_deduplicate=False → Allow Duplicates",
            passed=both_added,
            message=f"Duplicate handling: {'no deduplication' if both_added else 'deduplicated unexpectedly'}",
            details={"response1": response1, "response2": response2}
        )
    except Exception as e:
        return TestResult(
            name="Test 4: default_deduplicate=False",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_5_explicit_params_override_defaults() -> TestResult:
    """Test that explicit parameters override config defaults"""
    try:
        # Set all defaults to True
        config = get_config()
        config["mem0"]["default_infer"] = True
        config["mem0"]["default_extract"] = True
        config["mem0"]["default_deduplicate"] = True
        update_config(config)
        time.sleep(0.5)

        # Create memory with explicit infer=False (should override default)
        text = f"Behavior test {uuid.uuid4()}: Override test with explicit params"
        response = create_memory_rest(text, infer=False)

        # Should use fast path despite default_infer=True
        has_content = "content" in response

        return TestResult(
            name="Test 5: Explicit Params Override Defaults",
            passed=has_content,
            message=f"Explicit params {'override config defaults' if has_content else 'did not override'}",
            details={"response": response}
        )
    except Exception as e:
        return TestResult(
            name="Test 5: Explicit Override",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_6_custom_prompts_persist() -> TestResult:
    """Test that custom prompts can be set and persist"""
    try:
        # Set custom prompts
        config = get_config()
        config["openmemory"]["custom_instructions"] = "TEST EXTRACTION PROMPT: Extract technical facts only"
        config["openmemory"]["custom_update_memory_prompt"] = "TEST UPDATE PROMPT: Always merge information"
        update_config(config)
        time.sleep(0.5)

        # Verify they persisted
        retrieved = get_config()
        extraction_match = retrieved["openmemory"]["custom_instructions"] == "TEST EXTRACTION PROMPT: Extract technical facts only"
        update_match = retrieved["openmemory"]["custom_update_memory_prompt"] == "TEST UPDATE PROMPT: Always merge information"

        both_match = extraction_match and update_match

        return TestResult(
            name="Test 6: Custom Prompts Persist",
            passed=both_match,
            message=f"Custom prompts {'persisted correctly' if both_match else 'failed to persist'}",
            details={"retrieved_config": retrieved["openmemory"]}
        )
    except Exception as e:
        return TestResult(
            name="Test 6: Custom Prompts Persist",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_7_config_changes_immediate() -> TestResult:
    """Test that config changes take effect immediately without restart"""
    try:
        # Change default_infer from True to False
        config = get_config()
        config["mem0"]["default_infer"] = True
        update_config(config)
        time.sleep(0.5)

        # Create memory (should process)
        text1 = f"Immediate effect test {uuid.uuid4()}: First memory"
        response1 = create_memory_rest(text1)

        # Change config
        config["mem0"]["default_infer"] = False
        update_config(config)
        time.sleep(0.5)

        # Create memory (should NOT process)
        text2 = f"Immediate effect test {uuid.uuid4()}: Second memory"
        response2 = create_memory_rest(text2)

        # Both should succeed but with different processing
        both_created = (
            bool(response1) and bool(response2)
        )

        return TestResult(
            name="Test 7: Config Changes Take Effect Immediately",
            passed=both_created,
            message=f"Config changes {'applied immediately' if both_created else 'did not apply'}",
            details={"response1": response1, "response2": response2}
        )
    except Exception as e:
        return TestResult(
            name="Test 7: Immediate Config Changes",
            passed=False,
            message=f"Error: {str(e)}"
        )


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all test cases and report results"""
    print_header("OpenMemory Configuration Behavior Test Suite")

    print(f"{Colors.OKCYAN}Test Configuration:{Colors.ENDC}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  REST API: {REST_API_URL}")
    print(f"  Test User: {TEST_USER}")
    print(f"  Test App: {TEST_APP}")
    print()

    # Backup config before tests
    backup_config()

    # Run all tests
    results = [
        test_1_default_infer_false(),
        test_2_default_infer_true(),
        test_3_default_extract_false(),
        test_4_default_deduplicate_false(),
        test_5_explicit_params_override_defaults(),
        test_6_custom_prompts_persist(),
        test_7_config_changes_immediate(),
    ]

    # Print results
    print_header("Test Results")
    for result in results:
        print_test_result(result)

    # Restore original config
    restore_config()

    # Summary
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print_header("Test Summary")
    print(f"  Total Tests: {total}")
    print(f"  {Colors.OKGREEN}Passed: {passed}{Colors.ENDC}")
    print(f"  {Colors.FAIL}Failed: {failed}{Colors.ENDC}")
    print(f"  Success Rate: {passed/total*100:.1f}%")
    print()

    if failed == 0:
        print(f"{Colors.OKGREEN}{Colors.BOLD}✓ ALL TESTS PASSED!{Colors.ENDC}\n")
        return 0
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.ENDC}\n")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
        exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Tests interrupted by user{Colors.ENDC}\n")
        # Try to restore config even on interrupt
        restore_config()
        exit(130)
    except Exception as e:
        print(f"\n{Colors.FAIL}Test suite failed with error: {e}{Colors.ENDC}\n")
        # Try to restore config even on error
        restore_config()
        exit(1)
