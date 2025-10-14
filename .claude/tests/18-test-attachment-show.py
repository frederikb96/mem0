#!/usr/bin/env python3
"""
Test MCP search_memory with attachment_show flag.

This test verifies that:
1. Memories can be added with complex attachments (strange chars, unicode, etc.)
2. MCP search_memory with attachment_show=True returns both attachment IDs and content
3. The attachment content matches what was originally stored

Usage:
    python3 18-test-attachment-show.py

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
TEST_APP = "test-attachment-show"
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


async def call_mcp_delete_all_async() -> Dict[str, Any]:
    """Call MCP delete_all_memories using proper MCP SSE client"""
    try:
        print(f"{Colors.OKBLUE}Connecting to MCP server at {MCP_SSE_URL}...{Colors.ENDC}")

        # Create SSE client connection
        async with sse_client(MCP_SSE_URL) as (read, write):
            async with ClientSession(read, write) as session:
                print(f"{Colors.OKBLUE}Initializing MCP session...{Colors.ENDC}")

                # Initialize the session
                await session.initialize()

                print(f"{Colors.OKBLUE}Calling delete_all_memories tool...{Colors.ENDC}")

                # Call the delete_all_memories tool
                result = await session.call_tool(
                    "delete_all_memories",
                    arguments={
                        "delete_attachments": True  # Also delete attachments
                    }
                )

                print(f"{Colors.OKGREEN}MCP tool called successfully{Colors.ENDC}")

                return {
                    "status": "success",
                    "message": "MCP delete_all completed",
                    "result": str(result)
                }

    except Exception as e:
        print(f"{Colors.FAIL}Error calling MCP: {str(e)}{Colors.ENDC}")
        return {
            "status": "error",
            "message": f"Error: {str(e)}"
        }


def call_mcp_delete_all() -> Dict[str, Any]:
    """Wrapper to call async MCP function from sync context"""
    return asyncio.run(call_mcp_delete_all_async())


async def call_mcp_add_memory_async(text: str, attachment_text: str) -> Dict[str, Any]:
    """Call MCP add_memories with attachment using proper MCP SSE client"""
    try:
        # Create SSE client connection
        async with sse_client(MCP_SSE_URL) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()

                # Call the add_memories tool
                result = await session.call_tool(
                    "add_memories",
                    arguments={
                        "text": text,
                        "attachment_text": attachment_text,
                        "infer": False,  # Don't use LLM processing
                        "extract": False,
                        "deduplicate": False
                    }
                )

                return {
                    "status": "success",
                    "result": result
                }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error: {str(e)}"
        }


def call_mcp_add_memory(text: str, attachment_text: str) -> Dict[str, Any]:
    """Wrapper to call async MCP function from sync context"""
    return asyncio.run(call_mcp_add_memory_async(text, attachment_text))


async def call_mcp_search_memory_async(query: str, attachment_show: bool = False) -> Dict[str, Any]:
    """Call MCP search_memory with optional attachment_show flag"""
    try:
        # Create SSE client connection
        async with sse_client(MCP_SSE_URL) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()

                # Call the search_memory tool
                result = await session.call_tool(
                    "search_memory",
                    arguments={
                        "query": query,
                        "limit": 10,
                        "attachment_show": attachment_show
                    }
                )

                return {
                    "status": "success",
                    "result": result
                }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error: {str(e)}"
        }


def call_mcp_search_memory(query: str, attachment_show: bool = False) -> Dict[str, Any]:
    """Wrapper to call async MCP function from sync context"""
    return asyncio.run(call_mcp_search_memory_async(query, attachment_show))


def test_delete_all() -> TestResult:
    """Test Step 1: Delete all existing memories"""
    try:
        print(f"{Colors.OKBLUE}Deleting all existing memories...{Colors.ENDC}")
        result = call_mcp_delete_all()

        if result["status"] == "success":
            return TestResult(
                name="Delete All Memories",
                passed=True,
                message="All memories deleted successfully",
                details=result
            )
        else:
            return TestResult(
                name="Delete All Memories",
                passed=False,
                message=f"Failed to delete memories: {result.get('message', 'Unknown error')}",
                details=result
            )
    except Exception as e:
        return TestResult(
            name="Delete All Memories",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def test_add_memories_with_complex_attachments() -> TestResult:
    """Test Step 2: Add memories with complex attachments containing special characters"""
    try:
        # Create unique test data with complex attachments
        unique_id1 = str(uuid.uuid4())
        unique_id2 = str(uuid.uuid4())

        text1 = f"ATTACHMENT_TEST_1_{unique_id1}_Memory about AI"
        attachment1 = f"""Complex attachment with special chars:
        - Unicode: 🚀 🎉 ❤️ 中文 日本語 한국어
        - Newlines and tabs:\n\tIndented content
        - Quotes: "double" and 'single'
        - Backslashes: \\ \n \t
        - JSON-like: {{"key": "value", "nested": {{"a": 1}}}}
        - XML-like: <tag attr="value">content</tag>
        - SQL-like: SELECT * FROM table WHERE id='123'; -- comment
        - Special symbols: @#$%^&*()[]{{}}|\\:;"'<>,.?/~`
        - Long text: {'x' * 1000}
        Unique ID: {unique_id1}
        """

        text2 = f"ATTACHMENT_TEST_2_{unique_id2}_Memory about ML"
        attachment2 = f"""Another complex attachment:
        - Math symbols: ∑ ∫ ∂ √ π ∞ ≈ ≠ ≤ ≥
        - Currency: $ € £ ¥ ₹ ₿
        - Arrows: → ← ↑ ↓ ⇒ ⇐
        - Bullets: • ◦ ▪ ▫ ○ ●
        - Zero-width chars: ​‌‍ (invisible)
        - RTL: مرحبا עברית
        - Emoji sequences: 👨‍👩‍👧‍👦 🏳️‍🌈
        - Control chars: \x00 \x01 \x02
        - Multi-line\n\n\nwith\n\n\nempty\n\n\nlines
        Unique ID: {unique_id2}
        """

        print(f"{Colors.OKBLUE}Adding memory 1 with complex attachment...{Colors.ENDC}")
        result1 = call_mcp_add_memory(text1, attachment1)

        print(f"{Colors.OKBLUE}Adding memory 2 with complex attachment...{Colors.ENDC}")
        result2 = call_mcp_add_memory(text2, attachment2)

        if result1["status"] == "success" and result2["status"] == "success":
            # Parse memory IDs from results
            try:
                result1_json = json.loads(result1["result"].content[0].text)
                result2_json = json.loads(result2["result"].content[0].text)

                memory_id1 = result1_json["results"][0]["id"]
                memory_id2 = result2_json["results"][0]["id"]

                return TestResult(
                    name="Add Memories with Complex Attachments",
                    passed=True,
                    message="Created 2 memories with complex attachments",
                    details={
                        "memory1_id": memory_id1,
                        "memory1_text": text1,
                        "memory1_attachment": attachment1[:100] + "...",
                        "memory2_id": memory_id2,
                        "memory2_text": text2,
                        "memory2_attachment": attachment2[:100] + "...",
                        "unique_id1": unique_id1,
                        "unique_id2": unique_id2
                    }
                )
            except Exception as parse_error:
                return TestResult(
                    name="Add Memories with Complex Attachments",
                    passed=False,
                    message=f"Failed to parse memory IDs: {str(parse_error)}",
                    details={"result1": str(result1), "result2": str(result2)}
                )
        else:
            return TestResult(
                name="Add Memories with Complex Attachments",
                passed=False,
                message="Failed to add one or both memories",
                details={"result1": result1, "result2": result2}
            )

    except Exception as e:
        return TestResult(
            name="Add Memories with Complex Attachments",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def test_search_with_attachment_show(text1: str, text2: str, attachment1: str, attachment2: str, unique_id1: str, unique_id2: str) -> TestResult:
    """Test Step 3: Search with attachment_show=True and verify attachment content"""
    try:
        print(f"{Colors.OKBLUE}Waiting for indexing...{Colors.ENDC}")
        time.sleep(3)

        print(f"{Colors.OKBLUE}Searching with attachment_show=True...{Colors.ENDC}")

        # Search for first memory
        result1 = call_mcp_search_memory(text1, attachment_show=True)

        if result1["status"] != "success":
            return TestResult(
                name="Search with attachment_show=True",
                passed=False,
                message=f"Search failed: {result1.get('message', 'Unknown error')}",
                details=result1
            )

        # Parse search results
        try:
            search_result_json = json.loads(result1["result"].content[0].text)
            results = search_result_json.get("results", [])

            if not results:
                return TestResult(
                    name="Search with attachment_show=True",
                    passed=False,
                    message="No results found in search",
                    details=search_result_json
                )

            first_result = results[0]

            # Check if attachments array is present
            if "attachments" not in first_result:
                return TestResult(
                    name="Search with attachment_show=True",
                    passed=False,
                    message="'attachments' array missing from result",
                    details=first_result
                )

            attachments = first_result["attachments"]

            if not attachments:
                return TestResult(
                    name="Search with attachment_show=True",
                    passed=False,
                    message="'attachments' array is empty",
                    details=first_result
                )

            # Check if attachment content matches
            retrieved_content = attachments[0]["content"]

            # Verify the unique ID is in the retrieved content
            if unique_id1 not in retrieved_content:
                return TestResult(
                    name="Search with attachment_show=True",
                    passed=False,
                    message=f"Attachment content doesn't match (unique_id {unique_id1} not found)",
                    details={
                        "expected_contains": unique_id1,
                        "retrieved_content": retrieved_content[:200] + "..."
                    }
                )

            # Verify complex characters are preserved
            checks = [
                ("Unicode emoji", "🚀"),
                ("Chinese", "中文"),
                ("Special symbols", "@#$%^&*"),
                ("JSON-like", '{"key": "value"'),
                ("Unique ID", unique_id1)
            ]

            failed_checks = []
            for check_name, check_str in checks:
                if check_str not in retrieved_content:
                    failed_checks.append(check_name)

            if failed_checks:
                return TestResult(
                    name="Search with attachment_show=True",
                    passed=False,
                    message=f"Some content checks failed: {', '.join(failed_checks)}",
                    details={
                        "failed_checks": failed_checks,
                        "retrieved_content": retrieved_content[:300] + "..."
                    }
                )

            # Check metadata contains attachment_ids
            if "metadata" not in first_result:
                return TestResult(
                    name="Search with attachment_show=True",
                    passed=False,
                    message="'metadata' missing from result",
                    details=first_result
                )

            metadata = first_result["metadata"]
            if "attachment_ids" not in metadata:
                return TestResult(
                    name="Search with attachment_show=True",
                    passed=False,
                    message="'attachment_ids' missing from metadata",
                    details=metadata
                )

            # All checks passed
            return TestResult(
                name="Search with attachment_show=True",
                passed=True,
                message="Attachment content retrieved successfully and all checks passed",
                details={
                    "attachment_id": attachments[0]["id"],
                    "attachment_size": len(retrieved_content),
                    "checks_passed": [c[0] for c in checks],
                    "metadata_attachment_ids": metadata["attachment_ids"]
                }
            )

        except Exception as parse_error:
            return TestResult(
                name="Search with attachment_show=True",
                passed=False,
                message=f"Failed to parse search results: {str(parse_error)}",
                details={"result": str(result1)}
            )

    except Exception as e:
        return TestResult(
            name="Search with attachment_show=True",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def test_search_without_attachment_show(text1: str) -> TestResult:
    """Test Step 4: Search with attachment_show=False to verify it doesn't return attachments"""
    try:
        print(f"{Colors.OKBLUE}Searching with attachment_show=False (default)...{Colors.ENDC}")

        # Search without attachment_show
        result = call_mcp_search_memory(text1, attachment_show=False)

        if result["status"] != "success":
            return TestResult(
                name="Search with attachment_show=False",
                passed=False,
                message=f"Search failed: {result.get('message', 'Unknown error')}",
                details=result
            )

        # Parse search results
        try:
            search_result_json = json.loads(result["result"].content[0].text)
            results = search_result_json.get("results", [])

            if not results:
                return TestResult(
                    name="Search with attachment_show=False",
                    passed=False,
                    message="No results found in search",
                    details=search_result_json
                )

            first_result = results[0]

            # Check that attachments array is NOT present
            if "attachments" in first_result:
                return TestResult(
                    name="Search with attachment_show=False",
                    passed=False,
                    message="'attachments' array should NOT be present when attachment_show=False",
                    details=first_result
                )

            return TestResult(
                name="Search with attachment_show=False",
                passed=True,
                message="Correctly did not return attachments when attachment_show=False",
                details=first_result
            )

        except Exception as parse_error:
            return TestResult(
                name="Search with attachment_show=False",
                passed=False,
                message=f"Failed to parse search results: {str(parse_error)}",
                details={"result": str(result)}
            )

    except Exception as e:
        return TestResult(
            name="Search with attachment_show=False",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def run_attachment_show_test():
    """Run the attachment_show test suite"""
    print_header("MCP search_memory attachment_show Test")

    results = []

    # Step 1: Delete all memories
    result1 = test_delete_all()
    results.append(result1)
    print_test_result(result1)

    if not result1.passed:
        print(f"{Colors.FAIL}Test failed at step 1. Aborting.{Colors.ENDC}")
        return

    # Step 2: Add memories with complex attachments
    result2 = test_add_memories_with_complex_attachments()
    results.append(result2)
    print_test_result(result2)

    if not result2.passed:
        print(f"{Colors.FAIL}Test failed at step 2. Aborting.{Colors.ENDC}")
        return

    text1 = result2.details["memory1_text"]
    text2 = result2.details["memory2_text"]
    unique_id1 = result2.details["unique_id1"]
    unique_id2 = result2.details["unique_id2"]

    # Reconstruct full attachments (we only stored truncated versions in details)
    attachment1 = f"""Complex attachment with special chars:
        - Unicode: 🚀 🎉 ❤️ 中文 日本語 한국어
        - Newlines and tabs:\n\tIndented content
        - Quotes: "double" and 'single'
        - Backslashes: \\ \n \t
        - JSON-like: {{"key": "value", "nested": {{"a": 1}}}}
        - XML-like: <tag attr="value">content</tag>
        - SQL-like: SELECT * FROM table WHERE id='123'; -- comment
        - Special symbols: @#$%^&*()[]{{}}|\\:;"'<>,.?/~`
        - Long text: {'x' * 1000}
        Unique ID: {unique_id1}
        """

    attachment2 = f"""Another complex attachment:
        - Math symbols: ∑ ∫ ∂ √ π ∞ ≈ ≠ ≤ ≥
        - Currency: $ € £ ¥ ₹ ₿
        - Arrows: → ← ↑ ↓ ⇒ ⇐
        - Bullets: • ◦ ▪ ▫ ○ ●
        - Zero-width chars: ​‌‍ (invisible)
        - RTL: مرحبا עברית
        - Emoji sequences: 👨‍👩‍👧‍👦 🏳️‍🌈
        - Control chars: \x00 \x01 \x02
        - Multi-line\n\n\nwith\n\n\nempty\n\n\nlines
        Unique ID: {unique_id2}
        """

    # Step 3: Search with attachment_show=True
    result3 = test_search_with_attachment_show(text1, text2, attachment1, attachment2, unique_id1, unique_id2)
    results.append(result3)
    print_test_result(result3)

    # Step 4: Search with attachment_show=False
    result4 = test_search_without_attachment_show(text1)
    results.append(result4)
    print_test_result(result4)

    # Summary
    print_header("Test Summary")
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    if passed == total:
        print(f"{Colors.OKGREEN}{Colors.BOLD}All tests passed! ({passed}/{total}){Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}Some tests failed. ({passed}/{total} passed){Colors.ENDC}")

    print()


if __name__ == "__main__":
    try:
        run_attachment_show_test()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
