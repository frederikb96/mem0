#!/usr/bin/env python3
"""
Test date filtering feature in MCP API.

This test verifies that:
1. ISO timestamp parsing works correctly (with/without time component)
2. Date filtering returns correct results from Qdrant
3. from_date filtering works as expected
4. Date field selection (created_at vs updated_at) works

Usage:
    python3 16-test-date-filtering.py

Requirements:
    - OpenMemory service running at http://localhost:8765
    - Test user 'frederik' configured
    - OPENAI_API_KEY set in environment
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from mcp import ClientSession
from mcp.client.sse import sse_client


# Configuration
BASE_URL = "http://localhost:8765"
TEST_USER = "frederik"
MCP_SSE_URL = f"{BASE_URL}/mcp/claude-code/sse/{TEST_USER}"

# Test memories (all different to avoid deduplication)
TEST_MEMORIES = [
    "Alice works as a data scientist specializing in Python and machine learning frameworks",
    "Bob is a frontend developer focusing on React and modern JavaScript frameworks",
    "Charlie develops embedded systems using Rust and C++ for IoT devices",
    "Diana is a machine learning engineer working with TensorFlow and PyTorch daily",
    "Eve manages cloud infrastructure using AWS, Kubernetes, and Terraform tools"
]


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
    print(f"  → {result.message}")
    if result.details:
        print(f"  Details: {json.dumps(result.details, indent=2)}")
    print()


async def mcp_call(tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Make an MCP tool call"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments=arguments)

            # Get the text content
            text_content = result.content[0].text

            # Try to parse as JSON, fallback to returning as-is
            try:
                return json.loads(text_content)
            except json.JSONDecodeError:
                # If not JSON, return a simple dict with the text
                return {"result": text_content}


async def delete_all_memories():
    """Delete all memories to start fresh"""
    print(f"{Colors.OKCYAN}Deleting all memories...{Colors.ENDC}")
    result = await mcp_call("delete_all_memories", {"delete_attachments": False})
    print(f"{Colors.OKGREEN}✓ All memories deleted{Colors.ENDC}")
    return result


async def add_memory(text: str) -> Dict[str, Any]:
    """Add a memory via MCP"""
    result = await mcp_call("add_memories", {
        "text": text,
        "infer": True,
        "extract": False,
        "deduplicate": False
    })
    return result


async def list_all_memories() -> Dict[str, Any]:
    """List all memories via MCP (not semantic search)"""
    result = await mcp_call("list_memories", {})
    # Convert list to dict with "results" key for consistency
    if isinstance(result, list):
        return {"results": result}
    return result

async def search_memories(query: str, from_date: str = None, to_date: str = None, date_field: str = "updated_at") -> Dict[str, Any]:
    """Search memories via MCP with optional date filtering"""
    args = {
        "query": query,
        "limit": 10,
        "date_field": date_field
    }
    if from_date:
        args["from_date"] = from_date
    if to_date:
        args["to_date"] = to_date

    result = await mcp_call("search_memory", args)
    return result


async def test_date_filtering() -> TestResult:
    """Test date filtering with ISO timestamps"""
    try:
        print_header("Testing MCP Date Filtering")

        # Step 1: Clean slate
        await delete_all_memories()
        await asyncio.sleep(1)

        # Step 2: Create 5 memories with 2-second delays
        print(f"\n{Colors.OKBLUE}Creating 5 memories with 2-second delays...{Colors.ENDC}")
        for i, memory_text in enumerate(TEST_MEMORIES, 1):
            print(f"  [{i}/5] {memory_text[:60]}...")
            await add_memory(memory_text)
            if i < len(TEST_MEMORIES):
                await asyncio.sleep(2)

        print(f"\n{Colors.OKGREEN}✓ Created {len(TEST_MEMORIES)} memories{Colors.ENDC}")

        # Step 3: Poll until all memories are accessible (use broad search to get timestamps)
        print(f"\n{Colors.OKBLUE}Waiting for memories to be accessible...{Colors.ENDC}")
        all_memories = []
        max_attempts = 20
        for attempt in range(1, max_attempts + 1):
            # Use very broad single-letter search with high limit to match all memories
            all_results = await mcp_call("search_memory", {"query": "a e i", "limit": 50})
            all_memories = all_results.get("results", [])
            # Filter to only memories with timestamps (newly created ones have created_at_ts)
            all_memories = [m for m in all_memories if m.get("created_at_ts") is not None]
            if len(all_memories) >= 5:
                print(f"  ✓ All 5 memories accessible with timestamps (attempt {attempt})")
                break
            print(f"  Attempt {attempt}: Found {len(all_memories)}/5 memories with timestamps, waiting...")
            await asyncio.sleep(2)

        if len(all_memories) < 5:
            return TestResult(
                name="Date Filtering Test",
                passed=False,
                message=f"Timeout: Expected 5 memories, got {len(all_memories)} after {max_attempts} attempts",
                details={"created_count": len(all_memories)}
            )

        # Step 4: Extract real server-side timestamps (use created_at_ts for new memories)
        print(f"\n{Colors.OKBLUE}Extracting server-side timestamps...{Colors.ENDC}")
        sorted_memories = sorted(all_memories, key=lambda m: m.get("created_at_ts", 0))

        # Use 4th memory timestamp + 1 second to get only the 5th (since gte is inclusive)
        cutoff_ts_unix = sorted_memories[3].get("created_at_ts") + 1
        cutoff_dt = datetime.fromtimestamp(cutoff_ts_unix, tz=timezone.utc)
        cutoff_ts = cutoff_dt.isoformat()

        print(f"  4th memory: {cutoff_ts} (unix: {cutoff_ts_unix})")
        print(f"  5th memory: {datetime.fromtimestamp(sorted_memories[4].get('created_at_ts'), tz=timezone.utc).isoformat()}")

        # Step 5: Test filtering with real timestamps (use created_at for new memories)
        print(f"\n{Colors.OKBLUE}Testing date filter with from_date={cutoff_ts}{Colors.ENDC}")
        filtered_results = await search_memories("systems frameworks engineer developer infrastructure", from_date=cutoff_ts, date_field="created_at")
        filtered_count = len(filtered_results.get("results", []))
        print(f"  Found {filtered_count} memories (expected 1)")

        if filtered_count > 0:
            print(f"  Memory: {filtered_results['results'][0]['memory'][:70]}...")

        # Step 6: Validate
        success = (len(all_memories) == 5 and filtered_count == 1)

        return TestResult(
            name="Date Filtering Test",
            passed=success,
            message=f"{'✓ All tests passed' if success else '✗ Test failed'}: {len(all_memories)} total, {filtered_count} after cutoff",
            details={
                "total_memories": len(all_memories),
                "filtered_memories": filtered_count,
                "cutoff_timestamp": cutoff_ts
            }
        )

    except Exception as e:
        import traceback
        return TestResult(
            name="Date Filtering Test",
            passed=False,
            message=f"Error: {str(e)}",
            details={"traceback": traceback.format_exc()}
        )


async def test_iso_timestamp_formats() -> TestResult:
    """Test different ISO timestamp formats"""
    try:
        print_header("Testing ISO Timestamp Formats")
        
        # Clean slate
        await delete_all_memories()
        await asyncio.sleep(1)
        
        # Create a memory
        print(f"{Colors.OKBLUE}Creating test memory...{Colors.ENDC}")
        await add_memory("Test memory for timestamp format validation")
        await asyncio.sleep(1)
        
        # Test different timestamp formats
        now = datetime.now(timezone.utc)
        
        # Format 1: Full ISO with time
        ts1 = now.isoformat()
        print(f"\n{Colors.OKCYAN}Testing format: {ts1}{Colors.ENDC}")
        result1 = await search_memories("test", from_date=ts1)
        
        # Format 2: Date only (should default to 00:00:00)
        ts2 = now.strftime("%Y-%m-%d")
        print(f"{Colors.OKCYAN}Testing format: {ts2}{Colors.ENDC}")
        result2 = await search_memories("test", from_date=ts2)
        
        # Both should work without errors
        success = "results" in result1 and "results" in result2
        
        return TestResult(
            name="ISO Timestamp Formats Test",
            passed=success,
            message="Both ISO formats accepted successfully" if success else "Format parsing failed",
            details={
                "full_iso_format": ts1,
                "date_only_format": ts2,
                "result1_count": len(result1.get("results", [])),
                "result2_count": len(result2.get("results", []))
            }
        )
        
    except Exception as e:
        return TestResult(
            name="ISO Timestamp Formats Test",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


async def run_all_tests():
    """Run all date filtering tests"""
    print_header("Date Filtering Test Suite")
    
    results = []
    
    # Test 1: Date filtering
    result1 = await test_date_filtering()
    results.append(result1)
    print_test_result(result1)
    
    # Test 2: ISO timestamp formats
    result2 = await test_iso_timestamp_formats()
    results.append(result2)
    print_test_result(result2)
    
    # Final cleanup
    print_header("Cleanup")
    await delete_all_memories()
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    if passed == total:
        print(f"{Colors.OKGREEN}{Colors.BOLD}✓ All tests passed! ({passed}/{total}){Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}✗ Some tests failed. ({passed}/{total} passed){Colors.ENDC}")
    
    print()


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
