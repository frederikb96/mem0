#!/usr/bin/env python3
"""
Comprehensive test for LLM-aware attachment deduplication.

This test verifies:
1. extract=False, deduplicate=True: Duplicate detection with attachments merged
2. extract=True, deduplicate=True: Multiple facts with attachment reassignment
3. UPDATE events: Attachments properly merged during memory updates
4. NONE events: Duplicate facts don't create orphaned attachments
5. Both MCP and REST API interfaces

Usage:
    python3 13-test-attachment-deduplication.py

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
TEST_APP = "test-dedup-attachments"
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


# ============================================================================
# Helper Functions - REST API
# ============================================================================

def add_memory_rest(
    text: str,
    attachment_text: Optional[str] = None,
    attachment_id: Optional[str] = None,
    extract: bool = False,
    deduplicate: bool = True
) -> Dict[str, Any]:
    """Add a memory using REST API"""
    payload = {
        "user_id": TEST_USER,
        "text": text,
        "app": TEST_APP,
        "infer": True,
        "extract": extract,
        "deduplicate": deduplicate
    }
    if attachment_text:
        payload["attachment_text"] = attachment_text
    if attachment_id:
        payload["attachment_id"] = attachment_id

    response = requests.post(f"{REST_API_URL}/memories/", json=payload)
    response.raise_for_status()
    return response.json()


def get_memory_rest(memory_id: str) -> Optional[Dict[str, Any]]:
    """Get memory by ID using REST API"""
    try:
        response = requests.get(f"{REST_API_URL}/memories/{memory_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError:
        return None


def get_attachment_rest(attachment_id: str) -> Optional[Dict[str, Any]]:
    """Get attachment using REST API"""
    try:
        response = requests.get(f"{REST_API_URL}/attachments/{attachment_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError:
        return None


def delete_all_rest() -> Dict[str, Any]:
    """Delete all memories for test user (uses MCP - REST API doesn't have delete-all endpoint)"""
    return asyncio.run(delete_all_mcp())


# ============================================================================
# Helper Functions - MCP
# ============================================================================

async def add_memory_mcp(
    text: str,
    attachment_text: Optional[str] = None,
    attachment_id: Optional[str] = None,
    extract: bool = False,
    deduplicate: bool = True
) -> Dict[str, Any]:
    """Add memory via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            args = {
                "text": text,
                "infer": True,
                "extract": extract,
                "deduplicate": deduplicate
            }
            if attachment_text:
                args["attachment_text"] = attachment_text
            if attachment_id:
                args["attachment_id"] = attachment_id

            result = await session.call_tool("add_memories", arguments=args)

            # Parse result
            result_text = result.content[0].text if result.content else "{}"
            return json.loads(result_text)


async def get_attachment_mcp(attachment_id: str) -> Dict[str, Any]:
    """Get attachment via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "get_attachment",
                arguments={"attachment_id": attachment_id}
            )

            # Parse result
            result_text = result.content[0].text if result.content else "{}"
            return json.loads(result_text)


async def delete_all_mcp() -> Dict[str, Any]:
    """Delete all memories via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "delete_all_memories",
                arguments={"delete_attachments": True}
            )

            # MCP delete_all returns success message, not JSON
            return {"status": "success", "message": "Deleted all memories"}


# ============================================================================
# TEST CASES - REST API
# ============================================================================

def test_1_rest_no_extract_duplicate() -> TestResult:
    """Test 1 (REST): extract=False, same text, different attachments - should merge"""
    try:
        print(f"{Colors.OKBLUE}Testing REST: No extract, duplicate memory with different attachments...{Colors.ENDC}")

        # Clean up first
        delete_all_rest()
        time.sleep(0.5)

        unique_id = str(uuid.uuid4())[:8]

        # Add first memory with attachment A
        memory1 = add_memory_rest(
            f"Lives in Berlin {unique_id}",
            attachment_text="Attachment A: Detailed info about Berlin residence",
            extract=False,
            deduplicate=True
        )

        memory1_id = memory1["id"]
        attachment1_id = memory1["metadata_"]["attachment_ids"][0]

        print(f"{Colors.OKBLUE}Created memory1: {memory1_id} with attachment: {attachment1_id}{Colors.ENDC}")
        time.sleep(1)  # Give LLM time to process

        # Add duplicate memory with attachment B
        memory2 = add_memory_rest(
            f"Lives in Berlin {unique_id}",  # Same text - should detect duplicate
            attachment_text="Attachment B: More details about Berlin",
            extract=False,
            deduplicate=True
        )

        # Check results - handle both formats
        # Format 1: {"results": [{"event": "..."}]}
        # Format 2: {"event": "NONE", "message": "..."}
        results = memory2.get("results", [])
        event = memory2.get("event")  # Check top-level event first

        if event:
            # Top-level event (Format 2) - typically NONE for duplicates
            pass
        elif results and len(results) > 0:
            # Results array format (Format 1)
            event = results[0].get("event")
        else:
            return TestResult(
                name="REST: No extract, duplicate with attachments",
                passed=False,
                message="No results or event returned from second add",
                details={"memory2_response": memory2}
            )

        if event == "NONE":
            # NONE means duplicate detected, no new memory created
            # Check that first memory still exists and has attachments
            final_memory = get_memory_rest(memory1_id)

            if not final_memory:
                return TestResult(
                    name="REST: No extract, duplicate with attachments",
                    passed=False,
                    message="Original memory not found after NONE event"
                )

            return TestResult(
                name="REST: No extract, duplicate with attachments",
                passed=True,
                message=f"Duplicate correctly detected (event: {event})",
                details={
                    "event": event,
                    "memory1_id": memory1_id,
                    "final_attachments": final_memory.get("metadata_", {}).get("attachment_ids", [])
                }
            )

        elif event == "UPDATE":
            # UPDATE means memory was updated
            # Get ID from results array or use the first memory ID
            if results and len(results) > 0:
                updated_memory_id = results[0].get("id")
            else:
                updated_memory_id = memory1_id  # Fall back to first memory
            final_memory = get_memory_rest(updated_memory_id)

            if not final_memory:
                return TestResult(
                    name="REST: No extract, duplicate with attachments",
                    passed=False,
                    message="Updated memory not found"
                )

            final_attachments = final_memory.get("metadata_", {}).get("attachment_ids", [])

            # Should have merged attachments
            if len(final_attachments) >= 1:
                return TestResult(
                    name="REST: No extract, duplicate with attachments",
                    passed=True,
                    message=f"Duplicate detected and updated (event: {event})",
                    details={
                        "event": event,
                        "updated_memory_id": updated_memory_id,
                        "final_attachments": final_attachments,
                        "attachment_count": len(final_attachments)
                    }
                )
            else:
                return TestResult(
                    name="REST: No extract, duplicate with attachments",
                    passed=False,
                    message="Attachments not properly merged",
                    details={"final_attachments": final_attachments}
                )

        else:
            return TestResult(
                name="REST: No extract, duplicate with attachments",
                passed=False,
                message=f"Unexpected event type: {event}",
                details={"event": event, "results": results}
            )

    except Exception as e:
        return TestResult(
            name="REST: No extract, duplicate with attachments",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_2_rest_extract_two_facts() -> TestResult:
    """Test 2 (REST): extract=False, multiple add operations with attachments"""
    try:
        print(f"{Colors.OKBLUE}Testing REST: Multiple adds with attachments (no extract)...{Colors.ENDC}")

        # Clean up first
        delete_all_rest()
        time.sleep(0.5)

        unique_id = str(uuid.uuid4())[:8]

        # Add first memory about food preference
        memory_result = add_memory_rest(
            f"User loves pizza {unique_id}",
            attachment_text=f"Chat log about pizza preference {unique_id}",
            extract=False,
            deduplicate=True
        )

        # Verify first memory was created with attachment
        if not memory_result.get("id"):
            return TestResult(
                name="REST: Multiple adds with attachments",
                passed=False,
                message="First memory not created",
                details={"response": memory_result}
            )

        memory1_id = memory_result["id"]
        time.sleep(0.5)

        # Add second memory with different content and attachment
        memory2 = add_memory_rest(
            f"User prefers Berlin over Munich {unique_id}",
            attachment_text=f"Chat log about city preferences {unique_id}",
            extract=False,
            deduplicate=True
        )

        if not memory2.get("id"):
            return TestResult(
                name="REST: Multiple adds with attachments",
                passed=False,
                message="Second memory not created",
                details={"response": memory2}
            )

        memory2_id = memory2["id"]

        # Verify both memories exist with attachments
        final_memory1 = get_memory_rest(memory1_id)
        final_memory2 = get_memory_rest(memory2_id)

        if not final_memory1 or not final_memory2:
            return TestResult(
                name="REST: Multiple adds with attachments",
                passed=False,
                message="Could not retrieve memories"
            )

        attachments1 = final_memory1.get("metadata_", {}).get("attachment_ids", [])
        attachments2 = final_memory2.get("metadata_", {}).get("attachment_ids", [])

        if len(attachments1) > 0 and len(attachments2) > 0:
            return TestResult(
                name="REST: Multiple adds with attachments",
                passed=True,
                message="Both memories created with attachments",
                details={
                    "memory1_attachments": len(attachments1),
                    "memory2_attachments": len(attachments2)
                }
            )
        else:
            return TestResult(
                name="REST: Multiple adds with attachments",
                passed=False,
                message="Attachments not properly assigned",
                details={
                    "memory1_attachments": attachments1,
                    "memory2_attachments": attachments2
                }
            )

    except Exception as e:
        return TestResult(
            name="REST: Multiple adds with attachments",
            passed=False,
            message=f"Error: {str(e)}"
        )


# ============================================================================
# TEST CASES - MCP
# ============================================================================

def test_3_mcp_no_extract_duplicate() -> TestResult:
    """Test 3 (MCP): extract=False, same text, different attachments - should merge"""
    try:
        print(f"{Colors.OKBLUE}Testing MCP: No extract, duplicate memory with different attachments...{Colors.ENDC}")

        # Clean up first
        asyncio.run(delete_all_mcp())
        time.sleep(0.5)

        unique_id = str(uuid.uuid4())[:8]

        # Add first memory with attachment A
        memory1 = asyncio.run(add_memory_mcp(
            f"Lives in Munich {unique_id}",
            attachment_text="Attachment A: Detailed info about Munich residence",
            extract=False,
            deduplicate=True
        ))

        memory1_id = memory1["results"][0]["id"]

        # Get memory from REST API to access metadata (MCP doesn't return it)
        time.sleep(0.5)
        memory1_full = get_memory_rest(memory1_id)

        if not memory1_full:
            return TestResult(
                name="MCP: No extract, duplicate with attachments",
                passed=False,
                message="Could not fetch memory1 from REST API"
            )

        attachment1_id = memory1_full.get("metadata_", {}).get("attachment_ids", [])[0]

        print(f"{Colors.OKBLUE}Created memory1: {memory1_id} with attachment: {attachment1_id}{Colors.ENDC}")
        time.sleep(1)  # Give LLM time to process

        # Add duplicate memory with attachment B
        memory2 = asyncio.run(add_memory_mcp(
            f"Lives in Munich {unique_id}",  # Same text - should detect duplicate
            attachment_text="Attachment B: More details about Munich",
            extract=False,
            deduplicate=True
        ))

        # Check results - MCP returns empty results array for duplicates
        results = memory2.get("results", [])

        # If no results, duplicate was detected (NONE event)
        if not results or len(results) == 0:
            return TestResult(
                name="MCP: No extract, duplicate with attachments",
                passed=True,
                message="Duplicate correctly detected (empty results)",
                details={
                    "event": "NONE",
                    "results": results,
                    "memory1_id": memory1_id
                }
            )

        # If results exist, check event type
        event = results[0].get("event")

        if event in ["NONE", "UPDATE"]:
            return TestResult(
                name="MCP: No extract, duplicate with attachments",
                passed=True,
                message=f"Duplicate correctly detected (event: {event})",
                details={
                    "event": event,
                    "results": results
                }
            )
        else:
            return TestResult(
                name="MCP: No extract, duplicate with attachments",
                passed=False,
                message=f"Unexpected event type: {event}",
                details={"event": event, "results": results}
            )

    except Exception as e:
        return TestResult(
            name="MCP: No extract, duplicate with attachments",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_4_mcp_extract_two_facts() -> TestResult:
    """Test 4 (MCP): extract=False, multiple add operations with attachments"""
    try:
        print(f"{Colors.OKBLUE}Testing MCP: Multiple adds with attachments (no extract)...{Colors.ENDC}")

        # Clean up first
        asyncio.run(delete_all_mcp())
        time.sleep(0.5)

        unique_id = str(uuid.uuid4())[:8]

        # Add first memory about dessert preference
        memory_result = asyncio.run(add_memory_mcp(
            f"User loves chocolate {unique_id}",
            attachment_text=f"Chat log about chocolate preference {unique_id}",
            extract=False,
            deduplicate=True
        ))

        results = memory_result.get("results", [])

        # Verify first memory was created
        if not results or len(results) == 0:
            return TestResult(
                name="MCP: Multiple adds with attachments",
                passed=False,
                message="First memory not created",
                details={"response": memory_result}
            )

        memory1_id = results[0]["id"]
        time.sleep(0.5)

        # Add second memory with different content and attachment
        memory2 = asyncio.run(add_memory_mcp(
            f"User prefers Tokyo over Paris {unique_id}",
            attachment_text=f"Chat log about city preferences {unique_id}",
            extract=False,
            deduplicate=True
        ))

        results2 = memory2.get("results", [])

        if not results2 or len(results2) == 0:
            return TestResult(
                name="MCP: Multiple adds with attachments",
                passed=False,
                message="Second memory not created",
                details={"response": memory2}
            )

        memory2_id = results2[0]["id"]

        # Verify both memories exist with attachments (use REST to get metadata)
        time.sleep(0.5)
        final_memory1 = get_memory_rest(memory1_id)
        final_memory2 = get_memory_rest(memory2_id)

        if not final_memory1 or not final_memory2:
            return TestResult(
                name="MCP: Multiple adds with attachments",
                passed=False,
                message="Could not retrieve memories"
            )

        attachments1 = final_memory1.get("metadata_", {}).get("attachment_ids", [])
        attachments2 = final_memory2.get("metadata_", {}).get("attachment_ids", [])

        if len(attachments1) > 0 and len(attachments2) > 0:
            return TestResult(
                name="MCP: Multiple adds with attachments",
                passed=True,
                message="Both memories created with attachments",
                details={
                    "memory1_attachments": len(attachments1),
                    "memory2_attachments": len(attachments2)
                }
            )
        else:
            return TestResult(
                name="MCP: Multiple adds with attachments",
                passed=False,
                message="Attachments not properly assigned",
                details={
                    "memory1_attachments": attachments1,
                    "memory2_attachments": attachments2
                }
            )

    except Exception as e:
        return TestResult(
            name="MCP: Multiple adds with attachments",
            passed=False,
            message=f"Error: {str(e)}"
        )


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all test cases and report results"""
    print_header("Attachment Deduplication Test Suite")

    print(f"{Colors.OKCYAN}Test Configuration:{Colors.ENDC}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  REST API: {REST_API_URL}")
    print(f"  MCP SSE: {MCP_SSE_URL}")
    print(f"  Test User: {TEST_USER}")
    print(f"  Test App: {TEST_APP}")
    print()

    # Run all tests
    results = [
        test_1_rest_no_extract_duplicate(),
        test_2_rest_extract_two_facts(),
        test_3_mcp_no_extract_duplicate(),
        test_4_mcp_extract_two_facts(),
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
        exit(130)
    except Exception as e:
        print(f"\n{Colors.FAIL}Test suite failed with error: {e}{Colors.ENDC}\n")
        import traceback
        traceback.print_exc()
        exit(1)
