#!/usr/bin/env python3
"""
Test MCP delete_all_memories endpoint.

This test verifies that:
1. Multiple memories can be added
2. MCP delete_all_memories removes them from both DB and Qdrant
3. Deleted memories don't appear in searches

Usage:
    python3 06-test-mcp-delete-all.py

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
TEST_APP = "test-mcp-delete"
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


def create_memory_rest(text: str) -> Dict[str, Any]:
    """Create a memory using REST API with Qdrant storage"""
    response = requests.post(
        f"{REST_API_URL}/memories/",
        json={
            "user_id": TEST_USER,
            "text": text,
            "app": TEST_APP,
            "infer": True,  # Enable LLM processing to store in Qdrant
            "extract": False,  # Don't extract facts, store as-is
            "deduplicate": False  # Don't deduplicate
        }
    )
    response.raise_for_status()
    return response.json()


def list_memories_with_search(search_query: str) -> List[Dict[str, Any]]:
    """List memories using REST API filter endpoint"""
    response = requests.get(
        f"{REST_API_URL}/memories/",
        params={
            "user_id": TEST_USER,
            "search_query": search_query,
            "size": 100
        }
    )
    response.raise_for_status()
    result = response.json()
    return result.get("items", [])


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
                        "delete_attachments": False
                    }
                )

                print(f"{Colors.OKGREEN}MCP tool called successfully{Colors.ENDC}")
                print(f"{Colors.OKBLUE}Result: {result}{Colors.ENDC}")

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


def test_add_two_memories() -> TestResult:
    """Test Step 1: Add two unique memories"""
    try:
        # Create two unique memories
        unique_id1 = str(uuid.uuid4())
        unique_id2 = str(uuid.uuid4())

        text1 = f"MCP_DELETE_TEST_1_{unique_id1}_Memory about artificial intelligence and neural networks"
        text2 = f"MCP_DELETE_TEST_2_{unique_id2}_Memory about machine learning and deep learning"

        print(f"{Colors.OKBLUE}Creating memory 1:{Colors.ENDC} {text1[:60]}...")
        memory1 = create_memory_rest(text1)

        print(f"{Colors.OKBLUE}Creating memory 2:{Colors.ENDC} {text2[:60]}...")
        memory2 = create_memory_rest(text2)

        memory_id1 = memory1.get("id")
        memory_id2 = memory2.get("id")

        if not memory_id1 or not memory_id2:
            return TestResult(
                name="Add Two Memories",
                passed=False,
                message="Missing memory IDs in response",
                details={"memory1": memory1, "memory2": memory2}
            )

        return TestResult(
            name="Add Two Memories",
            passed=True,
            message=f"Created 2 memories",
            details={
                "memory1_id": memory_id1,
                "memory1_text": text1,
                "memory2_id": memory_id2,
                "memory2_text": text2
            }
        )
    except Exception as e:
        return TestResult(
            name="Add Two Memories",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def test_search_before_delete(text1: str, text2: str) -> TestResult:
    """Test Step 2: Search for both memories (should be found)"""
    try:
        print(f"{Colors.OKBLUE}Searching for memory 1...{Colors.ENDC}")

        # Wait for indexing
        time.sleep(2)

        results1 = list_memories_with_search(text1)
        results2 = list_memories_with_search(text2)

        found1 = any(text1 in result.get("content", "") for result in results1)
        found2 = any(text2 in result.get("content", "") for result in results2)

        if found1 and found2:
            return TestResult(
                name="Search Before Delete",
                passed=True,
                message=f"Both memories found in search",
                details={"memory1_results": len(results1), "memory2_results": len(results2)}
            )
        else:
            return TestResult(
                name="Search Before Delete",
                passed=False,
                message=f"Not all memories found (mem1: {found1}, mem2: {found2})",
                details={"results1": results1, "results2": results2}
            )
    except Exception as e:
        return TestResult(
            name="Search Before Delete",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def test_mcp_delete_all() -> TestResult:
    """Test Step 3: Call MCP delete_all_memories"""
    try:
        print(f"{Colors.OKBLUE}Calling MCP delete_all_memories...{Colors.ENDC}")

        result = call_mcp_delete_all()

        return TestResult(
            name="MCP Delete All",
            passed=True,
            message="MCP delete_all_memories called",
            details=result
        )
    except Exception as e:
        return TestResult(
            name="MCP Delete All",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def test_search_after_delete(text1: str, text2: str) -> TestResult:
    """Test Step 4: Search for both memories (should NOT be found)"""
    try:
        print(f"{Colors.OKBLUE}Searching again for both memories...{Colors.ENDC}")

        # Wait for deletion to propagate
        time.sleep(2)

        results1 = list_memories_with_search(text1)
        results2 = list_memories_with_search(text2)

        found1 = any(text1 in result.get("content", "") for result in results1)
        found2 = any(text2 in result.get("content", "") for result in results2)

        if not found1 and not found2:
            return TestResult(
                name="Search After Delete (Should be Gone)",
                passed=True,
                message="Both memories correctly NOT found",
                details={"memory1_results": len(results1), "memory2_results": len(results2)}
            )
        else:
            return TestResult(
                name="Search After Delete (Should be Gone)",
                passed=False,
                message=f"❌ BUG: Some memories still found! (mem1: {found1}, mem2: {found2})",
                details={"results1": results1, "results2": results2}
            )
    except Exception as e:
        return TestResult(
            name="Search After Delete (Should be Gone)",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def run_mcp_delete_all_test():
    """Run the MCP delete_all test"""
    print_header("MCP delete_all_memories Test")

    results = []

    # Step 1: Add two memories
    result1 = test_add_two_memories()
    results.append(result1)
    print_test_result(result1)

    if not result1.passed:
        print(f"{Colors.FAIL}Test failed at step 1. Aborting.{Colors.ENDC}")
        return

    text1 = result1.details["memory1_text"]
    text2 = result1.details["memory2_text"]

    # Step 2: Search before delete
    result2 = test_search_before_delete(text1, text2)
    results.append(result2)
    print_test_result(result2)

    # Step 3: MCP delete_all
    result3 = test_mcp_delete_all()
    results.append(result3)
    print_test_result(result3)

    # Step 4: Search after delete (should be gone)
    result4 = test_search_after_delete(text1, text2)
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
        run_mcp_delete_all_test()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
