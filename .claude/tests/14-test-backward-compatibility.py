#!/usr/bin/env python3
"""
Test backward compatibility - verify system works WITHOUT attachments.

This test ensures that the attachment deduplication feature doesn't break
existing behavior when NO attachments are used.

Usage:
    python3 14-test-backward-compatibility.py

Requirements:
    - OpenMemory service running at http://localhost:8765
    - Test user 'frederik' configured
    - OPENAI_API_KEY set in environment
"""

import asyncio
import requests
import json
import uuid
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from mcp import ClientSession
from mcp.client.sse import sse_client


# Configuration
BASE_URL = "http://localhost:8765"
REST_API_URL = f"{BASE_URL}/api/v1"
TEST_USER = "frederik"
TEST_APP = "test-backward-compat"
MCP_SSE_URL = f"{BASE_URL}/mcp/claude-code/sse/{TEST_USER}"


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


# Helper Functions
async def delete_all_mcp() -> Dict[str, Any]:
    """Delete all memories via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "delete_all_memories",
                arguments={"delete_attachments": True}
            )
            return {"status": "success"}


def delete_all_rest() -> Dict[str, Any]:
    """Delete all memories (uses MCP)"""
    return asyncio.run(delete_all_mcp())


def add_memory_rest(text: str, extract: bool = False, deduplicate: bool = True) -> Dict[str, Any]:
    """Add a memory using REST API WITHOUT attachments"""
    payload = {
        "user_id": TEST_USER,
        "text": text,
        "app": TEST_APP,
        "infer": True,
        "extract": extract,
        "deduplicate": deduplicate
    }
    response = requests.post(f"{REST_API_URL}/memories/", json=payload)
    response.raise_for_status()
    return response.json()


def get_memory_rest(memory_id: str) -> Optional[Dict[str, Any]]:
    """Get memory by ID"""
    try:
        response = requests.get(f"{REST_API_URL}/memories/{memory_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError:
        return None


# ============================================================================
# TEST CASES - Backward Compatibility
# ============================================================================

def test_1_simple_add_no_attachments() -> TestResult:
    """Test 1: Simple memory add WITHOUT attachments (backward compat)"""
    try:
        print(f"{Colors.OKBLUE}Testing: Simple add without attachments...{Colors.ENDC}")

        delete_all_rest()
        time.sleep(0.5)

        unique_id = str(uuid.uuid4())[:8]

        # Add memory WITHOUT any attachment
        result = add_memory_rest(
            f"User likes Python {unique_id}",
            extract=False,
            deduplicate=True
        )

        if not result.get("id"):
            return TestResult(
                name="Simple add without attachments",
                passed=False,
                message="No memory ID returned",
                details={"response": result}
            )

        memory_id = result["id"]
        memory = get_memory_rest(memory_id)

        # Verify NO attachment_ids in metadata
        has_attachments = "metadata" in memory and "attachment_ids" in memory.get("metadata", {})

        return TestResult(
            name="Simple add without attachments",
            passed=not has_attachments,
            message="Memory created without attachments" if not has_attachments else "Unexpected attachments found!",
            details={
                "memory_id": memory_id,
                "has_attachments": has_attachments,
                "metadata": memory.get("metadata", {})
            }
        )

    except Exception as e:
        return TestResult(
            name="Simple add without attachments",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_2_duplicate_detection_no_attachments() -> TestResult:
    """Test 2: Duplicate detection WITHOUT attachments (backward compat)"""
    try:
        print(f"{Colors.OKBLUE}Testing: Duplicate detection without attachments...{Colors.ENDC}")

        delete_all_rest()
        time.sleep(0.5)

        unique_id = str(uuid.uuid4())[:8]

        # Add first memory
        memory1 = add_memory_rest(
            f"Prefers dark mode {unique_id}",
            extract=False,
            deduplicate=True
        )

        memory1_id = memory1.get("id")
        time.sleep(1)

        # Add duplicate
        memory2 = add_memory_rest(
            f"Prefers dark mode {unique_id}",  # Same text
            extract=False,
            deduplicate=True
        )

        # Check for NONE or UPDATE event
        results = memory2.get("results", [])
        event = memory2.get("event")

        if event:
            pass  # Top-level event
        elif results and len(results) > 0:
            event = results[0].get("event")
        else:
            event = None

        duplicate_detected = event in ["NONE", "UPDATE"]

        return TestResult(
            name="Duplicate detection without attachments",
            passed=duplicate_detected,
            message=f"Duplicate {'correctly' if duplicate_detected else 'NOT'} detected (event: {event})",
            details={
                "event": event,
                "memory1_id": memory1_id,
                "results": results
            }
        )

    except Exception as e:
        return TestResult(
            name="Duplicate detection without attachments",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_3_multiple_adds_no_attachments() -> TestResult:
    """Test 3: Multiple different memories WITHOUT attachments"""
    try:
        print(f"{Colors.OKBLUE}Testing: Multiple adds without attachments...{Colors.ENDC}")

        delete_all_rest()
        time.sleep(0.5)

        unique_id = str(uuid.uuid4())[:8]

        # Add 3 different memories
        memory1 = add_memory_rest(f"Likes coffee {unique_id}", extract=False)
        memory2 = add_memory_rest(f"Works in Berlin {unique_id}", extract=False)
        memory3 = add_memory_rest(f"Prefers vi over emacs {unique_id}", extract=False)

        # Verify all created
        ids = [m.get("id") for m in [memory1, memory2, memory3]]
        all_created = all(id is not None for id in ids)

        if not all_created:
            return TestResult(
                name="Multiple adds without attachments",
                passed=False,
                message="Not all memories created",
                details={"ids": ids}
            )

        # Verify none have attachments
        time.sleep(0.5)
        memories = [get_memory_rest(id) for id in ids]
        has_any_attachments = any(
            "metadata" in m and "attachment_ids" in m.get("metadata", {})
            for m in memories if m
        )

        return TestResult(
            name="Multiple adds without attachments",
            passed=not has_any_attachments,
            message="All memories created without attachments",
            details={
                "count": len(ids),
                "has_attachments": has_any_attachments
            }
        )

    except Exception as e:
        return TestResult(
            name="Multiple adds without attachments",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_4_extract_without_attachments() -> TestResult:
    """Test 4: Fact extraction WITHOUT attachments (backward compat)"""
    try:
        print(f"{Colors.OKBLUE}Testing: Extraction without attachments...{Colors.ENDC}")

        delete_all_rest()
        time.sleep(0.5)

        unique_id = str(uuid.uuid4())[:8]

        # Add with extraction (should create at least 1 memory)
        result = add_memory_rest(
            f"User loves pizza {unique_id}",
            extract=True,
            deduplicate=True
        )

        # Handle both response formats
        # Format 1: {"results": [...]}
        # Format 2: Direct memory object with "id"
        if "results" in result:
            results = result["results"]
            memory_ids = [r["id"] for r in results]
        elif "id" in result:
            # Direct memory response
            results = [result]
            memory_ids = [result["id"]]
        else:
            return TestResult(
                name="Extract without attachments",
                passed=False,
                message="Unexpected response format",
                details={"response": result}
            )

        # Should have at least 1 memory created
        facts_extracted = len(memory_ids) >= 1

        if not facts_extracted:
            return TestResult(
                name="Extract without attachments",
                passed=False,
                message="No memory created",
                details={"response": result}
            )

        # Verify none have attachments
        time.sleep(0.5)
        has_any_attachments = False
        for memory_id in memory_ids:
            memory = get_memory_rest(memory_id)
            if memory and "metadata" in memory and "attachment_ids" in memory.get("metadata", {}):
                has_any_attachments = True
                break

        return TestResult(
            name="Extract without attachments",
            passed=not has_any_attachments,
            message=f"Created {len(memory_ids)} memories without attachments",
            details={
                "memory_count": len(memory_ids),
                "has_attachments": has_any_attachments
            }
        )

    except Exception as e:
        return TestResult(
            name="Extract without attachments",
            passed=False,
            message=f"Error: {str(e)}"
        )


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all backward compatibility tests"""
    print_header("Backward Compatibility Test Suite")

    print(f"{Colors.OKCYAN}Test Configuration:{Colors.ENDC}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  REST API: {REST_API_URL}")
    print(f"  Test User: {TEST_USER}")
    print(f"  Test App: {TEST_APP}")
    print()

    print(f"{Colors.WARNING}Purpose: Verify system works correctly WITHOUT attachments{Colors.ENDC}\n")

    # Run all tests
    results = [
        test_1_simple_add_no_attachments(),
        test_2_duplicate_detection_no_attachments(),
        test_3_multiple_adds_no_attachments(),
        test_4_extract_without_attachments(),
    ]

    # Print results
    print_header("Test Results")
    for result in results:
        print_test_result(result)

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
        print(f"{Colors.OKGREEN}{Colors.BOLD}✓ ALL BACKWARD COMPATIBILITY TESTS PASSED!{Colors.ENDC}")
        print(f"{Colors.OKGREEN}System works correctly without attachments.{Colors.ENDC}\n")
        return 0
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}✗ BACKWARD COMPATIBILITY BROKEN{Colors.ENDC}\n")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
        exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Tests interrupted by user{Colors.ENDC}\n")
        exit(130)
    except Exception as e:
        print(f"\n{Colors.FAIL}Test suite failed with error: {e}{Colors.ENDC}\n")
        import traceback
        traceback.print_exc()
        exit(1)
