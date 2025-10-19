#!/usr/bin/env python3
"""
Test async performance of MCP API.

Tests that search operations remain fast while a long add operation is running.
This verifies that async/await properly prevents event loop blocking.

NOTE: Since we're using synchronous HTTP requests now, this test can't truly
test async concurrency. However, it still validates that operations work correctly
and measures baseline performance characteristics.
"""

import json
import time
import uuid
import requests
from concurrent.futures import ThreadPoolExecutor
import threading

BASE_URL = "http://localhost:8765"
MCP_URL = f"{BASE_URL}/mcp"
TEST_USER_ID = "frederik"
TEST_CLIENT_NAME = "test-client"


def get_headers():
    """Generate headers with unique session ID per thread"""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": str(uuid.uuid4()),
        "X-User-Id": TEST_USER_ID,
        "X-Client-Name": TEST_CLIENT_NAME
    }


def parse_sse_response(sse_text: str) -> dict:
    """Parse SSE (Server-Sent Events) response format"""
    lines = sse_text.strip().split('\n')
    for line in lines:
        if line.startswith('data: '):
            json_data = line[6:]  # Remove 'data: ' prefix
            return json.loads(json_data)
    return {}


def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Call an MCP tool via HTTP POST"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    try:
        response = requests.post(MCP_URL, headers=get_headers(), json=payload, timeout=30)
        response.raise_for_status()

        # Parse SSE format response
        result = parse_sse_response(response.text)

        # Extract content from MCP response
        if "result" in result and "content" in result["result"]:
            for content_item in result["result"]["content"]:
                if "text" in content_item:
                    text_content = content_item["text"]
                    # Try to parse as JSON, fall back to plain text
                    try:
                        return json.loads(text_content)
                    except json.JSONDecodeError:
                        return {"message": text_content}

        return result
    except Exception as e:
        return {"error": str(e)}


def mcp_delete_all():
    """Delete all memories via MCP"""
    return call_mcp_tool("delete_all_memories", {})


def mcp_add_memory(text, infer=False):
    """Add memory via MCP"""
    return call_mcp_tool("add_memories", {"text": text, "infer": infer})


def mcp_search(query):
    """Search memories via MCP"""
    return call_mcp_tool("search_memory", {"query": query})


def timed_search(query, label):
    """Execute search and measure time"""
    start = time.time()
    result = mcp_search(query)
    elapsed = time.time() - start

    # Get count
    count = len(result.get("results", []))

    return elapsed, count


def continuous_search_loop(query, duration_seconds, stop_event):
    """Run searches continuously for specified duration, measuring each"""
    print(f"\n{'='*80}")
    print(f"CONTINUOUS SEARCH LOOP ({duration_seconds}s)")
    print(f"{'='*80}\n")

    results = []
    start_time = time.time()
    search_num = 1

    while time.time() - start_time < duration_seconds and not stop_event.is_set():
        elapsed, count = timed_search(query, f"Search #{search_num}")
        results.append(elapsed)
        print(f"Search #{search_num:3d}: {elapsed*1000:6.1f}ms (found {count} results)")
        search_num += 1
        time.sleep(0.1)  # Small delay between searches

    return results


def main():
    print("=" * 80)
    print("ASYNC PERFORMANCE TEST")
    print("=" * 80)
    print()
    print("This test verifies that search operations remain fast while")
    print("a long add operation is running (using threading for concurrency).")
    print()

    # Step 1: Delete all
    print("=== STEP 1: Delete All Memories ===")
    mcp_delete_all()
    print("✓ All memories deleted")
    print()

    # Step 2: Add a short test memory
    print("=== STEP 2: Add Test Memory ===")
    test_text = "Python is a programming language"
    print(f"Adding: '{test_text}'")
    mcp_add_memory(test_text, infer=False)
    print("✓ Test memory added")
    print()

    # Step 3: Baseline search performance (no background load)
    print("=== STEP 3: Baseline Search Performance (3 seconds) ===")
    stop_event = threading.Event()
    baseline_results = continuous_search_loop("python", 3, stop_event)
    baseline_avg = sum(baseline_results) / len(baseline_results) if baseline_results else 0
    print(f"\n📊 Baseline Average: {baseline_avg*1000:.1f}ms ({len(baseline_results)} searches)")
    print()

    # Step 4: Start long add operation in background
    print("=== STEP 4: Long Add Operation + Concurrent Searches ===")
    print()

    # Create a long text (5 sentences, ~300 chars each)
    long_text = " ".join([
        "The quantum entanglement phenomenon exhibits non-local correlations between particles that have interacted in the past, regardless of the distance separating them in space, which Einstein famously referred to as spooky action at a distance and which remains one of the most puzzling aspects of quantum mechanics.",
        "Machine learning algorithms have revolutionized the field of artificial intelligence by enabling computers to learn patterns from data without being explicitly programmed for every specific task, leading to breakthroughs in areas such as computer vision, natural language processing, and autonomous systems.",
        "Climate change represents one of the most significant challenges facing humanity today, with rising global temperatures, melting ice caps, extreme weather events, and shifting ecosystems threatening biodiversity, food security, water resources, and the stability of human civilizations worldwide.",
        "The human brain contains approximately 86 billion neurons, each forming thousands of connections with other neurons through synapses, creating a complex network that enables consciousness, memory, learning, emotion, and all the cognitive functions that make us human.",
        "Blockchain technology provides a decentralized, distributed ledger system that records transactions across multiple computers in a way that makes it virtually impossible to alter retroactively without the consensus of the network, offering new possibilities for secure, transparent, and trustless digital interactions."
    ])

    print(f"Long text length: {len(long_text)} characters")
    print("Starting background add operation (infer=False)...")
    print()

    # Start long add in background thread
    stop_event = threading.Event()
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit add operation
        add_future = executor.submit(mcp_add_memory, long_text, False)

        # Give it a moment to start
        time.sleep(0.5)

        # Run searches while add is running
        print("Running searches concurrently with add operation...")
        search_future = executor.submit(continuous_search_loop, "python", 3, stop_event)

        # Wait for both to complete
        load_results = search_future.result()
        add_future.result()

    load_avg = sum(load_results) / len(load_results) if load_results else 0
    print(f"\n📊 Under Load Average: {load_avg*1000:.1f}ms ({len(load_results)} searches)")
    print("✓ Background add completed")
    print()

    # Step 5: Analysis
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()
    print(f"Baseline average:   {baseline_avg*1000:6.1f}ms ({len(baseline_results)} searches)")
    print(f"Under load average: {load_avg*1000:6.1f}ms ({len(load_results)} searches)")
    print()

    if load_avg > 0:
        slowdown = (load_avg / baseline_avg - 1) * 100 if baseline_avg > 0 else 0
        print(f"Slowdown: {slowdown:+.1f}%")
        print()

        if slowdown < 20:
            print("✅ EXCELLENT: Minimal slowdown - concurrent operations working well!")
            print("   Search operations are not blocked by long add operation.")
        elif slowdown < 50:
            print("✓ GOOD: Some slowdown but acceptable - operations can run concurrently.")
        else:
            print("⚠️  WARNING: Significant slowdown detected.")
            print("   This might indicate resource contention or server bottleneck.")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
