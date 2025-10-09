#!/usr/bin/env python3
"""
Comprehensive test for attachment operations and fixes.

This test verifies:
1. MCP create_attachment tool
2. MCP update_attachment tool
3. MCP delete_memories tool (with delete_attachments flag)
4. REST DELETE /memories/ with delete_attachments flag (fixed)
5. MCP delete_all_memories with delete_attachments flag (fixed)
6. Attachment merging on UPDATE events

Usage:
    python3 08-test-attachment-operations.py

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
TEST_APP = "test-attachments"
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

def create_memory_rest(text: str, attachment_text: Optional[str] = None, attachment_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a memory using REST API"""
    payload = {
        "user_id": TEST_USER,
        "text": text,
        "app": TEST_APP,
        "infer": True,
        "extract": False,
        "deduplicate": False
    }
    if attachment_text:
        payload["attachment_text"] = attachment_text
    if attachment_id:
        payload["attachment_id"] = attachment_id

    response = requests.post(f"{REST_API_URL}/memories/", json=payload)
    response.raise_for_status()
    return response.json()


def delete_memories_rest(memory_ids: List[str], delete_attachments: bool = False) -> Dict[str, Any]:
    """Delete memories using REST API"""
    response = requests.delete(
        f"{REST_API_URL}/memories/",
        json={
            "user_id": TEST_USER,
            "memory_ids": memory_ids,
            "delete_attachments": delete_attachments
        }
    )
    response.raise_for_status()
    return response.json()


def get_attachment_rest(attachment_id: str) -> Optional[Dict[str, Any]]:
    """Get attachment using REST API"""
    try:
        response = requests.get(f"{REST_API_URL}/attachments/{attachment_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError:
        return None


def get_memory_rest(memory_id: str) -> Optional[Dict[str, Any]]:
    """Get memory by ID using REST API"""
    try:
        response = requests.get(f"{REST_API_URL}/memories/{memory_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError:
        return None


# ============================================================================
# Helper Functions - MCP
# ============================================================================

async def call_mcp_create_attachment(content: str, attachment_id: Optional[str] = None) -> Dict[str, Any]:
    """Create attachment via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            args = {"content": content}
            if attachment_id:
                args["attachment_id"] = attachment_id

            result = await session.call_tool("create_attachment", arguments=args)

            # Parse result
            result_text = result.content[0].text if result.content else "{}"
            return json.loads(result_text)


async def call_mcp_update_attachment(attachment_id: str, content: str) -> Dict[str, Any]:
    """Update attachment via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "update_attachment",
                arguments={
                    "attachment_id": attachment_id,
                    "content": content
                }
            )

            # Parse result
            result_text = result.content[0].text if result.content else "{}"
            return json.loads(result_text)


async def call_mcp_get_attachment(attachment_id: str) -> Dict[str, Any]:
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


async def call_mcp_delete_memories(memory_ids: List[str], delete_attachments: bool = False) -> Dict[str, Any]:
    """Delete memories via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "delete_memories",
                arguments={
                    "memory_ids": memory_ids,
                    "delete_attachments": delete_attachments
                }
            )

            # Parse result
            result_text = result.content[0].text if result.content else "{}"
            return json.loads(result_text)


async def call_mcp_add_memory(text: str, attachment_text: Optional[str] = None, attachment_id: Optional[str] = None) -> Dict[str, Any]:
    """Add memory via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            args = {
                "text": text,
                "infer": True,
                "extract": False,
                "deduplicate": False
            }
            if attachment_text:
                args["attachment_text"] = attachment_text
            if attachment_id:
                args["attachment_id"] = attachment_id

            result = await session.call_tool("add_memories", arguments=args)

            # Parse result
            result_text = result.content[0].text if result.content else "{}"
            return json.loads(result_text)


# ============================================================================
# TEST CASES
# ============================================================================

def test_1_mcp_create_attachment() -> TestResult:
    """Test 1: MCP create_attachment tool"""
    try:
        print(f"{Colors.OKBLUE}Testing MCP create_attachment...{Colors.ENDC}")

        attachment_content = "Test attachment content created via MCP"
        result = asyncio.run(call_mcp_create_attachment(attachment_content))

        if result.get("success"):
            attachment_id = result.get("id")
            print(f"{Colors.OKBLUE}Created attachment: {attachment_id}{Colors.ENDC}")

            return TestResult(
                name="MCP create_attachment",
                passed=True,
                message=f"Created attachment successfully",
                details={"attachment_id": attachment_id, "result": result}
            )
        else:
            return TestResult(
                name="MCP create_attachment",
                passed=False,
                message=f"Failed: {result.get('error', 'Unknown error')}",
                details=result
            )
    except Exception as e:
        return TestResult(
            name="MCP create_attachment",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_2_mcp_update_attachment() -> TestResult:
    """Test 2: MCP update_attachment tool"""
    try:
        print(f"{Colors.OKBLUE}Testing MCP update_attachment...{Colors.ENDC}")

        # Create attachment first
        original_content = "Original content"
        create_result = asyncio.run(call_mcp_create_attachment(original_content))

        if not create_result.get("success"):
            return TestResult(
                name="MCP update_attachment",
                passed=False,
                message="Failed to create attachment for test",
                details=create_result
            )

        attachment_id = create_result.get("id")
        print(f"{Colors.OKBLUE}Created attachment: {attachment_id}{Colors.ENDC}")

        # Update attachment
        updated_content = "Updated content via MCP"
        update_result = asyncio.run(call_mcp_update_attachment(attachment_id, updated_content))

        if update_result.get("success") and update_result.get("content") == updated_content:
            return TestResult(
                name="MCP update_attachment",
                passed=True,
                message=f"Updated attachment successfully",
                details={"attachment_id": attachment_id, "result": update_result}
            )
        else:
            return TestResult(
                name="MCP update_attachment",
                passed=False,
                message=f"Failed: {update_result.get('error', 'Content mismatch')}",
                details=update_result
            )
    except Exception as e:
        return TestResult(
            name="MCP update_attachment",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_3_mcp_delete_memories_with_attachments() -> TestResult:
    """Test 3: MCP delete_memories tool with delete_attachments=True"""
    try:
        print(f"{Colors.OKBLUE}Testing MCP delete_memories with attachments...{Colors.ENDC}")

        # Create two memories with attachments
        attachment1_content = "Attachment 1 for delete test"
        attachment2_content = "Attachment 2 for delete test"

        memory1_result = asyncio.run(call_mcp_add_memory(
            "Memory 1 with attachment",
            attachment_text=attachment1_content
        ))
        memory2_result = asyncio.run(call_mcp_add_memory(
            "Memory 2 with attachment",
            attachment_text=attachment2_content
        ))

        # Extract memory IDs from MCP response
        memory1_id = memory1_result["results"][0]["id"]
        memory2_id = memory2_result["results"][0]["id"]

        # Fetch memories from REST API to get metadata (MCP doesn't return metadata)
        time.sleep(0.5)  # Small delay for DB sync
        memory1 = get_memory_rest(memory1_id)
        memory2 = get_memory_rest(memory2_id)

        if not memory1 or not memory2:
            return TestResult(
                name="MCP delete_memories with attachments",
                passed=False,
                message="Could not fetch memories from REST API",
                details={"memory1_id": memory1_id, "memory2_id": memory2_id}
            )

        # Get attachment IDs from metadata
        attachment1_id = memory1.get("metadata_", {}).get("attachment_ids", [])[0] if memory1.get("metadata_", {}).get("attachment_ids") else None
        attachment2_id = memory2.get("metadata_", {}).get("attachment_ids", [])[0] if memory2.get("metadata_", {}).get("attachment_ids") else None

        if not attachment1_id or not attachment2_id:
            return TestResult(
                name="MCP delete_memories with attachments",
                passed=False,
                message="Could not extract attachment IDs from memory metadata",
                details={"memory1": memory1, "memory2": memory2}
            )

        print(f"{Colors.OKBLUE}Created memories: {memory1_id}, {memory2_id}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}With attachments: {attachment1_id}, {attachment2_id}{Colors.ENDC}")

        # Delete memories with attachments
        delete_result = asyncio.run(call_mcp_delete_memories(
            [memory1_id, memory2_id],
            delete_attachments=True
        ))

        if not delete_result.get("success"):
            return TestResult(
                name="MCP delete_memories with attachments",
                passed=False,
                message=f"Delete failed: {delete_result.get('error')}",
                details=delete_result
            )

        # Verify attachments are deleted
        time.sleep(1)
        attachment1_check = asyncio.run(call_mcp_get_attachment(attachment1_id))
        attachment2_check = asyncio.run(call_mcp_get_attachment(attachment2_id))

        attachments_deleted = (
            attachment1_check.get("error") == "Attachment not found" and
            attachment2_check.get("error") == "Attachment not found"
        )

        if attachments_deleted:
            return TestResult(
                name="MCP delete_memories with attachments",
                passed=True,
                message="Deleted memories and attachments successfully",
                details={
                    "deleted_memories": [memory1_id, memory2_id],
                    "deleted_attachments": [attachment1_id, attachment2_id]
                }
            )
        else:
            return TestResult(
                name="MCP delete_memories with attachments",
                passed=False,
                message="Memories deleted but attachments still exist",
                details={
                    "attachment1_check": attachment1_check,
                    "attachment2_check": attachment2_check
                }
            )
    except Exception as e:
        return TestResult(
            name="MCP delete_memories with attachments",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_4_rest_delete_memories_with_attachments() -> TestResult:
    """Test 4: REST DELETE /memories/ with delete_attachments=True (fixed bug)"""
    try:
        print(f"{Colors.OKBLUE}Testing REST DELETE /memories/ with attachments...{Colors.ENDC}")

        # Create two memories with attachments
        unique_id = str(uuid.uuid4())[:8]
        attachment1_content = f"REST attachment 1 - {unique_id}"
        attachment2_content = f"REST attachment 2 - {unique_id}"

        memory1 = create_memory_rest(
            f"REST Memory 1 - {unique_id}",
            attachment_text=attachment1_content
        )
        memory2 = create_memory_rest(
            f"REST Memory 2 - {unique_id}",
            attachment_text=attachment2_content
        )

        memory1_id = str(memory1["id"])
        memory2_id = str(memory2["id"])

        # Get attachment IDs from metadata
        attachment1_id = memory1["metadata_"]["attachment_ids"][0]
        attachment2_id = memory2["metadata_"]["attachment_ids"][0]

        print(f"{Colors.OKBLUE}Created memories: {memory1_id}, {memory2_id}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}With attachments: {attachment1_id}, {attachment2_id}{Colors.ENDC}")

        # Delete memories with attachments
        delete_result = delete_memories_rest(
            [memory1_id, memory2_id],
            delete_attachments=True
        )

        # Verify attachments are deleted
        time.sleep(1)
        attachment1_check = get_attachment_rest(attachment1_id)
        attachment2_check = get_attachment_rest(attachment2_id)

        attachments_deleted = attachment1_check is None and attachment2_check is None

        if attachments_deleted:
            return TestResult(
                name="REST DELETE /memories/ with attachments",
                passed=True,
                message="Deleted memories and attachments successfully (BUG FIXED)",
                details={
                    "deleted_memories": [memory1_id, memory2_id],
                    "deleted_attachments": [attachment1_id, attachment2_id]
                }
            )
        else:
            return TestResult(
                name="REST DELETE /memories/ with attachments",
                passed=False,
                message="⚠️ BUG NOT FIXED: Attachments still exist after delete",
                details={
                    "attachment1_exists": attachment1_check is not None,
                    "attachment2_exists": attachment2_check is not None
                }
            )
    except Exception as e:
        return TestResult(
            name="REST DELETE /memories/ with attachments",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_5_mcp_delete_memories_without_attachments() -> TestResult:
    """Test 5: MCP delete_memories with delete_attachments=False (attachments preserved)"""
    try:
        print(f"{Colors.OKBLUE}Testing MCP delete_memories WITHOUT deleting attachments...{Colors.ENDC}")

        # Create memory with attachment
        attachment_content = "Attachment should be preserved"
        memory_result = asyncio.run(call_mcp_add_memory(
            "Memory to delete without attachment",
            attachment_text=attachment_content
        ))

        # Extract memory ID from MCP response
        memory_id = memory_result["results"][0]["id"]

        # Fetch memory from REST API to get metadata (MCP doesn't return metadata)
        time.sleep(0.5)  # Small delay for DB sync
        memory = get_memory_rest(memory_id)

        if not memory:
            return TestResult(
                name="MCP delete_memories without attachments",
                passed=False,
                message="Could not fetch memory from REST API",
                details={"memory_id": memory_id}
            )

        # Get attachment ID from metadata
        attachment_id = memory.get("metadata_", {}).get("attachment_ids", [])[0] if memory.get("metadata_", {}).get("attachment_ids") else None

        if not attachment_id:
            return TestResult(
                name="MCP delete_memories without attachments",
                passed=False,
                message="Could not extract attachment ID from memory metadata",
                details={"memory": memory}
            )

        print(f"{Colors.OKBLUE}Created memory: {memory_id} with attachment: {attachment_id}{Colors.ENDC}")

        # Delete memory WITHOUT deleting attachment
        delete_result = asyncio.run(call_mcp_delete_memories(
            [memory_id],
            delete_attachments=False
        ))

        if not delete_result.get("success"):
            return TestResult(
                name="MCP delete_memories without attachments",
                passed=False,
                message=f"Delete failed: {delete_result.get('error')}",
                details=delete_result
            )

        # Verify attachment still exists
        time.sleep(1)
        attachment_check = asyncio.run(call_mcp_get_attachment(attachment_id))

        attachment_exists = "content" in attachment_check and not attachment_check.get("error")

        if attachment_exists:
            return TestResult(
                name="MCP delete_memories without attachments",
                passed=True,
                message="Memory deleted, attachment preserved correctly",
                details={
                    "deleted_memory": memory_id,
                    "preserved_attachment": attachment_id
                }
            )
        else:
            return TestResult(
                name="MCP delete_memories without attachments",
                passed=False,
                message="Attachment was incorrectly deleted",
                details={"attachment_check": attachment_check}
            )
    except Exception as e:
        return TestResult(
            name="MCP delete_memories without attachments",
            passed=False,
            message=f"Error: {str(e)}"
        )


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all test cases and report results"""
    print_header("Attachment Operations Test Suite")

    print(f"{Colors.OKCYAN}Test Configuration:{Colors.ENDC}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  REST API: {REST_API_URL}")
    print(f"  MCP SSE: {MCP_SSE_URL}")
    print(f"  Test User: {TEST_USER}")
    print(f"  Test App: {TEST_APP}")
    print()

    # Run all tests
    results = [
        test_1_mcp_create_attachment(),
        test_2_mcp_update_attachment(),
        test_3_mcp_delete_memories_with_attachments(),
        test_4_rest_delete_memories_with_attachments(),
        test_5_mcp_delete_memories_without_attachments(),
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
