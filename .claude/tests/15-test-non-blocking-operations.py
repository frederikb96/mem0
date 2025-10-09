#!/usr/bin/env python3
"""
Test non-blocking API behavior during heavy memory operations.

This test verifies that:
1. Search queries remain responsive while adding long memories
2. Both REST and MCP APIs are non-blocking
3. Heavy LLM operations (inference + deduplication) run in background threads

Usage:
    python3 15-test-non-blocking-operations.py

Requirements:
    - OpenMemory service running at http://localhost:8765
    - Test user 'frederik' configured
    - OPENAI_API_KEY set in environment
"""

import asyncio
import requests
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from mcp import ClientSession
from mcp.client.sse import sse_client


# Configuration
BASE_URL = "http://localhost:8765"
REST_API_URL = f"{BASE_URL}/api/v1"
TEST_USER = "frederik"
TEST_APP = "test-non-blocking"
MCP_SSE_URL = f"{BASE_URL}/mcp/claude-code/sse/{TEST_USER}"

# Test parameters - generate unique texts for REST and MCP to avoid deduplication
import uuid
REST_UNIQUE_ID = str(uuid.uuid4())[:8]
MCP_UNIQUE_ID = str(uuid.uuid4())[:8]

REST_MEMORY_TEXT = f"""
REST Test {REST_UNIQUE_ID}: Comprehensive overview of artificial intelligence and machine learning systems.
Deep learning has revolutionized computer vision, natural language processing, and speech recognition.
Neural networks with multiple layers can learn hierarchical representations of data through backpropagation.
Convolutional neural networks excel at image recognition tasks by learning local patterns and spatial hierarchies.
Recurrent neural networks and transformers have transformed natural language understanding and generation.
Attention mechanisms allow models to focus on relevant parts of input sequences dynamically.
Transfer learning enables models pre-trained on large datasets to be fine-tuned for specific tasks efficiently.
Reinforcement learning agents learn optimal policies through interaction with environments and reward signals.
Generative adversarial networks create realistic synthetic data through adversarial training processes.
Unsupervised learning methods discover hidden patterns and structures in unlabeled datasets automatically.
"""

MCP_MEMORY_TEXT = f"""
MCP Test {MCP_UNIQUE_ID}: Advanced concepts in distributed systems and cloud computing architecture.
Microservices architecture enables independent deployment and scaling of application components.
Container orchestration platforms like Kubernetes automate deployment, scaling, and management of containerized applications.
Service mesh technologies provide communication infrastructure for microservices with load balancing and service discovery.
Event-driven architectures enable loose coupling between services through asynchronous message passing.
Database sharding strategies distribute data across multiple servers to handle large-scale applications.
CQRS pattern separates read and write operations for improved performance and scalability.
Circuit breaker patterns prevent cascading failures in distributed systems during service outages.
Distributed tracing helps monitor and debug complex interactions across microservices.
Eventual consistency models balance availability and partition tolerance in distributed databases.
API gateway patterns centralize authentication, rate limiting, and request routing for backend services.
"""


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


def create_long_memory_rest() -> Dict[str, Any]:
    """Create a long memory using REST API with full LLM processing"""
    start_time = time.time()
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Colors.OKCYAN}[{timestamp}] 🚀 REST: Starting memory add request...{Colors.ENDC}")

    response = requests.post(
        f"{REST_API_URL}/memories/",
        json={
            "user_id": TEST_USER,
            "text": REST_MEMORY_TEXT,
            "app": TEST_APP,
            "infer": True,  # Enable LLM processing
            "extract": False,  # Don't extract - store as-is (but still process)
            "deduplicate": True  # Deduplicate (slow - this is what we're testing)
        },
        timeout=120  # 2 minute timeout for long operation
    )
    elapsed = time.time() - start_time
    response.raise_for_status()
    result = response.json()
    result["_elapsed_seconds"] = elapsed

    timestamp_end = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Colors.OKCYAN}[{timestamp_end}] ✅ REST: Memory add completed in {elapsed:.2f}s{Colors.ENDC}")

    return result


async def create_long_memory_mcp_async() -> Dict[str, Any]:
    """Create a long memory using MCP with full LLM processing"""
    start_time = time.time()
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Colors.OKCYAN}[{timestamp}] 🚀 MCP: Starting memory add request...{Colors.ENDC}")

    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "add_memories",
                arguments={
                    "text": MCP_MEMORY_TEXT,
                    "infer": True,
                    "extract": False,  # Don't extract - store as-is (but still process)
                    "deduplicate": True  # Deduplicate (slow - this is what we're testing)
                }
            )

            elapsed = time.time() - start_time

            timestamp_end = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"{Colors.OKCYAN}[{timestamp_end}] ✅ MCP: Memory add completed in {elapsed:.2f}s{Colors.ENDC}")

            return {
                "status": "success",
                "result": str(result),
                "_elapsed_seconds": elapsed
            }


def search_memory_rest(query: str) -> tuple[List[Dict], float]:
    """Search memories using REST API and measure response time"""
    start_time = time.time()
    response = requests.get(
        f"{REST_API_URL}/memories/",
        params={
            "user_id": TEST_USER,
            "search_query": query,
            "size": 10
        },
        timeout=5
    )
    elapsed = time.time() - start_time
    response.raise_for_status()
    results = response.json().get("items", [])
    return results, elapsed


async def search_memory_mcp_async(query: str) -> tuple[Dict, float]:
    """Search memories using MCP and measure response time"""
    start_time = time.time()

    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "search_memory",
                arguments={
                    "query": query,
                    "limit": 10
                }
            )

            elapsed = time.time() - start_time
            return json.loads(result.content[0].text), elapsed


def run_parallel_searches_rest(duration_seconds: int = 30, search_query: str = "test") -> List[float]:
    """Run searches in parallel while memory is being added"""
    search_times = []
    end_time = time.time() + duration_seconds

    print(f"{Colors.OKBLUE}Starting parallel REST searches (query every 0.7s)...{Colors.ENDC}")

    while time.time() < end_time:
        try:
            _, elapsed = search_memory_rest(search_query)
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            # Print search time with color coding
            if elapsed < 0.5:
                color = Colors.OKGREEN
            elif elapsed < 1.0:
                color = Colors.WARNING
            else:
                color = Colors.FAIL

            print(f"{color}[{timestamp}] REST search took {elapsed:.3f}s{Colors.ENDC}")
            search_times.append(elapsed)

            time.sleep(0.7)  # Search every 700ms
        except Exception as e:
            print(f"{Colors.FAIL}REST search error: {e}{Colors.ENDC}")

    return search_times


async def run_parallel_searches_mcp_async(duration_seconds: int = 30, search_query: str = "test") -> List[float]:
    """Run MCP searches in parallel while memory is being added"""
    search_times = []
    end_time = time.time() + duration_seconds

    print(f"{Colors.OKBLUE}Starting parallel MCP searches (query every 0.7s)...{Colors.ENDC}")

    while time.time() < end_time:
        try:
            _, elapsed = await search_memory_mcp_async(search_query)
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            # Print search time with color coding
            if elapsed < 0.5:
                color = Colors.OKGREEN
            elif elapsed < 1.0:
                color = Colors.WARNING
            else:
                color = Colors.FAIL

            print(f"{color}[{timestamp}] MCP search took {elapsed:.3f}s{Colors.ENDC}")
            search_times.append(elapsed)

            await asyncio.sleep(0.7)  # Search every 700ms
        except Exception as e:
            print(f"{Colors.FAIL}MCP search error: {e}{Colors.ENDC}")

    return search_times


def test_rest_non_blocking() -> TestResult:
    """Test REST API non-blocking behavior"""
    try:
        print_header("Testing REST API Non-Blocking Behavior")

        # Start adding long memory in background thread
        memory_result = {}

        def add_memory_thread():
            try:
                result = create_long_memory_rest()
                memory_result["result"] = result
            except Exception as e:
                memory_result["error"] = str(e)
                print(f"{Colors.FAIL}Error adding memory: {e}{Colors.ENDC}")

        add_thread = threading.Thread(target=add_memory_thread)
        add_thread.start()

        # Give it a moment to start processing
        time.sleep(2)

        # Run parallel searches
        search_times = run_parallel_searches_rest(duration_seconds=25, search_query="artificial")

        # Wait for memory to finish
        add_thread.join(timeout=120)

        # Analyze results
        if not search_times:
            return TestResult(
                name="REST Non-Blocking Test",
                passed=False,
                message="No search results collected",
                details=None
            )

        avg_search_time = sum(search_times) / len(search_times)
        max_search_time = max(search_times)
        blocking_searches = sum(1 for t in search_times if t > 2.0)

        # Success criteria: average < 1s, max < 3s, no more than 20% blocking
        passed = (
            avg_search_time < 1.0 and
            max_search_time < 3.0 and
            blocking_searches < len(search_times) * 0.2
        )

        return TestResult(
            name="REST Non-Blocking Test",
            passed=passed,
            message=f"Avg: {avg_search_time:.3f}s, Max: {max_search_time:.3f}s, Blocking: {blocking_searches}/{len(search_times)}",
            details={
                "total_searches": len(search_times),
                "avg_time": f"{avg_search_time:.3f}s",
                "max_time": f"{max_search_time:.3f}s",
                "blocking_count": blocking_searches,
                "memory_result": memory_result.get("result", memory_result.get("error"))
            }
        )
    except Exception as e:
        return TestResult(
            name="REST Non-Blocking Test",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


async def test_mcp_non_blocking_async() -> TestResult:
    """Test MCP API non-blocking behavior"""
    try:
        print_header("Testing MCP API Non-Blocking Behavior")

        # Start adding long memory as background task
        memory_task = asyncio.create_task(create_long_memory_mcp_async())

        # Give it a moment to start processing
        await asyncio.sleep(2)

        # Run parallel searches
        search_times = await run_parallel_searches_mcp_async(duration_seconds=25, search_query="artificial")

        # Wait for memory to finish
        memory_result = await asyncio.wait_for(memory_task, timeout=120)

        # Analyze results
        if not search_times:
            return TestResult(
                name="MCP Non-Blocking Test",
                passed=False,
                message="No search results collected",
                details=None
            )

        avg_search_time = sum(search_times) / len(search_times)
        max_search_time = max(search_times)
        blocking_searches = sum(1 for t in search_times if t > 2.0)

        # Success criteria: average < 1s, max < 3s, no more than 20% blocking
        passed = (
            avg_search_time < 1.0 and
            max_search_time < 3.0 and
            blocking_searches < len(search_times) * 0.2
        )

        return TestResult(
            name="MCP Non-Blocking Test",
            passed=passed,
            message=f"Avg: {avg_search_time:.3f}s, Max: {max_search_time:.3f}s, Blocking: {blocking_searches}/{len(search_times)}",
            details={
                "total_searches": len(search_times),
                "avg_time": f"{avg_search_time:.3f}s",
                "max_time": f"{max_search_time:.3f}s",
                "blocking_count": blocking_searches,
                "memory_result": memory_result
            }
        )
    except Exception as e:
        return TestResult(
            name="MCP Non-Blocking Test",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def test_mcp_non_blocking() -> TestResult:
    """Wrapper to call async MCP test from sync context"""
    return asyncio.run(test_mcp_non_blocking_async())


def run_non_blocking_test():
    """Run the non-blocking behavior test"""
    print_header("Non-Blocking API Test Suite")

    results = []

    # Test 1: REST API
    result1 = test_rest_non_blocking()
    results.append(result1)
    print_test_result(result1)

    # Test 2: MCP API
    result2 = test_mcp_non_blocking()
    results.append(result2)
    print_test_result(result2)

    # Summary
    print_header("Test Summary")
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    if passed == total:
        print(f"{Colors.OKGREEN}{Colors.BOLD}✓ All tests passed! ({passed}/{total}){Colors.ENDC}")
        print(f"{Colors.OKGREEN}APIs are properly non-blocking!{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}✗ Some tests failed. ({passed}/{total} passed){Colors.ENDC}")
        print(f"{Colors.FAIL}API may be blocking during heavy operations.{Colors.ENDC}")

    print()


if __name__ == "__main__":
    try:
        run_non_blocking_test()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
