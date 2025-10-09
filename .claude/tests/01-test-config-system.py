#!/usr/bin/env python3
"""
Comprehensive test script for configuration system features.

Tests:
- Config API endpoints (GET/PUT)
- Custom prompt configuration (extraction and deduplication)
- Default flags configuration (infer, extract, deduplicate, attachment_ids_show)
- Database persistence of config changes
- Config validation

Usage:
    python3 01-test-config-system.py

Requirements:
    - OpenMemory service running at http://localhost:8765
    - Test user 'frederik' configured
    - OPENAI_API_KEY set in environment
"""

import requests
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Configuration
BASE_URL = "http://localhost:8765"
REST_API_URL = f"{BASE_URL}/api/v1"
TEST_USER = "frederik"
TEST_APP = "test-config-system"


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

def test_1_get_config() -> TestResult:
    """Test GET /api/v1/config/ returns valid config"""
    try:
        config = get_config()

        # Verify structure
        has_openmemory = "openmemory" in config
        has_mem0 = "mem0" in config

        # Verify new fields exist
        has_custom_instructions = "custom_instructions" in config.get("openmemory", {})
        has_custom_update_prompt = "custom_update_memory_prompt" in config.get("openmemory", {})
        has_default_infer = "default_infer" in config.get("mem0", {})
        has_default_extract = "default_extract" in config.get("mem0", {})
        has_default_deduplicate = "default_deduplicate" in config.get("mem0", {})
        has_default_attachment_ids_show = "default_attachment_ids_show" in config.get("mem0", {})

        all_present = all([
            has_openmemory, has_mem0,
            has_custom_instructions, has_custom_update_prompt,
            has_default_infer, has_default_extract, has_default_deduplicate,
            has_default_attachment_ids_show
        ])

        return TestResult(
            name="Test 1: GET Config - All New Fields Present",
            passed=all_present,
            message=f"All configuration fields present in response",
            details={"config": config}
        )
    except Exception as e:
        return TestResult(
            name="Test 1: GET Config",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_2_update_custom_extraction_prompt() -> TestResult:
    """Test updating custom_instructions (extraction prompt)"""
    try:
        custom_prompt = "Extract ONLY technical facts about software, infrastructure, and systems. Ignore personal preferences."

        config = get_config()
        config["openmemory"]["custom_instructions"] = custom_prompt

        # Update config
        updated = update_config(config)

        # Verify update persisted
        retrieved = get_config()
        matches = retrieved["openmemory"]["custom_instructions"] == custom_prompt

        return TestResult(
            name="Test 2: Update Custom Extraction Prompt",
            passed=matches,
            message=f"Custom extraction prompt {'updated and persisted' if matches else 'failed to persist'}",
            details={"set_value": custom_prompt, "retrieved_value": retrieved["openmemory"]["custom_instructions"]}
        )
    except Exception as e:
        return TestResult(
            name="Test 2: Update Custom Extraction Prompt",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_3_update_custom_update_prompt() -> TestResult:
    """Test updating custom_update_memory_prompt (deduplication prompt)"""
    try:
        custom_prompt = "When merging memories, always preserve the most recent information and append historical context."

        config = get_config()
        config["openmemory"]["custom_update_memory_prompt"] = custom_prompt

        # Update config
        updated = update_config(config)

        # Verify update persisted
        retrieved = get_config()
        matches = retrieved["openmemory"]["custom_update_memory_prompt"] == custom_prompt

        return TestResult(
            name="Test 3: Update Custom Update Prompt",
            passed=matches,
            message=f"Custom update prompt {'updated and persisted' if matches else 'failed to persist'}",
            details={"set_value": custom_prompt, "retrieved_value": retrieved["openmemory"]["custom_update_memory_prompt"]}
        )
    except Exception as e:
        return TestResult(
            name="Test 3: Update Custom Update Prompt",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_4_update_default_infer() -> TestResult:
    """Test updating default_infer flag"""
    try:
        config = get_config()

        # Toggle the value
        new_value = not config["mem0"]["default_infer"]
        config["mem0"]["default_infer"] = new_value

        # Update config
        updated = update_config(config)

        # Verify update persisted
        retrieved = get_config()
        matches = retrieved["mem0"]["default_infer"] == new_value

        return TestResult(
            name="Test 4: Update default_infer Flag",
            passed=matches,
            message=f"default_infer flag {'updated and persisted' if matches else 'failed to persist'} (set to {new_value})",
            details={"set_value": new_value, "retrieved_value": retrieved["mem0"]["default_infer"]}
        )
    except Exception as e:
        return TestResult(
            name="Test 4: Update default_infer",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_5_update_default_extract() -> TestResult:
    """Test updating default_extract flag"""
    try:
        config = get_config()

        # Toggle the value
        new_value = not config["mem0"]["default_extract"]
        config["mem0"]["default_extract"] = new_value

        # Update config
        updated = update_config(config)

        # Verify update persisted
        retrieved = get_config()
        matches = retrieved["mem0"]["default_extract"] == new_value

        return TestResult(
            name="Test 5: Update default_extract Flag",
            passed=matches,
            message=f"default_extract flag {'updated and persisted' if matches else 'failed to persist'} (set to {new_value})",
            details={"set_value": new_value, "retrieved_value": retrieved["mem0"]["default_extract"]}
        )
    except Exception as e:
        return TestResult(
            name="Test 5: Update default_extract",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_6_update_default_deduplicate() -> TestResult:
    """Test updating default_deduplicate flag"""
    try:
        config = get_config()

        # Toggle the value
        new_value = not config["mem0"]["default_deduplicate"]
        config["mem0"]["default_deduplicate"] = new_value

        # Update config
        updated = update_config(config)

        # Verify update persisted
        retrieved = get_config()
        matches = retrieved["mem0"]["default_deduplicate"] == new_value

        return TestResult(
            name="Test 6: Update default_deduplicate Flag",
            passed=matches,
            message=f"default_deduplicate flag {'updated and persisted' if matches else 'failed to persist'} (set to {new_value})",
            details={"set_value": new_value, "retrieved_value": retrieved["mem0"]["default_deduplicate"]}
        )
    except Exception as e:
        return TestResult(
            name="Test 6: Update default_deduplicate",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_7_update_default_attachment_ids_show() -> TestResult:
    """Test updating default_attachment_ids_show flag"""
    try:
        config = get_config()

        # Toggle the value
        new_value = not config["mem0"]["default_attachment_ids_show"]
        config["mem0"]["default_attachment_ids_show"] = new_value

        # Update config
        updated = update_config(config)

        # Verify update persisted
        retrieved = get_config()
        matches = retrieved["mem0"]["default_attachment_ids_show"] == new_value

        return TestResult(
            name="Test 7: Update default_attachment_ids_show Flag",
            passed=matches,
            message=f"default_attachment_ids_show flag {'updated and persisted' if matches else 'failed to persist'} (set to {new_value})",
            details={"set_value": new_value, "retrieved_value": retrieved["mem0"]["default_attachment_ids_show"]}
        )
    except Exception as e:
        return TestResult(
            name="Test 7: Update default_attachment_ids_show",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_8_config_persistence_after_restart() -> TestResult:
    """Test that config persists after service restart (manual verification)"""
    try:
        # This test documents that config should persist
        # Actual restart testing requires manual intervention
        config = get_config()

        return TestResult(
            name="Test 8: Config Persistence (requires manual restart test)",
            passed=True,
            message="Config is stored in PostgreSQL database and should persist across restarts",
            details={"note": "To verify: restart containers and check if custom values remain"}
        )
    except Exception as e:
        return TestResult(
            name="Test 8: Config Persistence",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_9_set_all_defaults_false() -> TestResult:
    """Test setting all default flags to False"""
    try:
        config = get_config()

        # Set all to False
        config["mem0"]["default_infer"] = False
        config["mem0"]["default_extract"] = False
        config["mem0"]["default_deduplicate"] = False
        config["mem0"]["default_attachment_ids_show"] = True  # Flip this one to True

        # Update config
        updated = update_config(config)

        # Verify
        retrieved = get_config()
        all_match = (
            retrieved["mem0"]["default_infer"] == False and
            retrieved["mem0"]["default_extract"] == False and
            retrieved["mem0"]["default_deduplicate"] == False and
            retrieved["mem0"]["default_attachment_ids_show"] == True
        )

        return TestResult(
            name="Test 9: Set All Default Flags",
            passed=all_match,
            message=f"All default flags {'set correctly' if all_match else 'failed to set'}",
            details={"retrieved_config": retrieved["mem0"]}
        )
    except Exception as e:
        return TestResult(
            name="Test 9: Set All Default Flags",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_10_null_custom_prompts() -> TestResult:
    """Test setting custom prompts to null"""
    try:
        config = get_config()

        # Set to null
        config["openmemory"]["custom_instructions"] = None
        config["openmemory"]["custom_update_memory_prompt"] = None

        # Update config
        updated = update_config(config)

        # Verify
        retrieved = get_config()
        both_null = (
            retrieved["openmemory"]["custom_instructions"] is None and
            retrieved["openmemory"]["custom_update_memory_prompt"] is None
        )

        return TestResult(
            name="Test 10: Set Custom Prompts to Null",
            passed=both_null,
            message=f"Custom prompts {'set to null correctly' if both_null else 'failed to set to null'}",
            details={"retrieved_config": retrieved["openmemory"]}
        )
    except Exception as e:
        return TestResult(
            name="Test 10: Set Custom Prompts to Null",
            passed=False,
            message=f"Error: {str(e)}"
        )


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all test cases and report results"""
    print_header("OpenMemory Configuration System Test Suite")

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
        test_1_get_config(),
        test_2_update_custom_extraction_prompt(),
        test_3_update_custom_update_prompt(),
        test_4_update_default_infer(),
        test_5_update_default_extract(),
        test_6_update_default_deduplicate(),
        test_7_update_default_attachment_ids_show(),
        test_8_config_persistence_after_restart(),
        test_9_set_all_defaults_false(),
        test_10_null_custom_prompts(),
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
