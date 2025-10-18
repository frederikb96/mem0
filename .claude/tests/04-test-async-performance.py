#!/usr/bin/env python3
"""
Test async performance of MCP API.

Tests that search operations remain fast while a long add operation is running.
This verifies that async/await properly prevents event loop blocking.
"""

import asyncio
import json
import time
from mcp import ClientSession
from mcp.client.sse import sse_client

BASE_URL = "http://localhost:8765"
TEST_USER = "frederik"
MCP_SSE_URL = f"{BASE_URL}/mcp/claude-code/sse/{TEST_USER}"


async def mcp_delete_all():
    """Delete all memories via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "delete_all_memories",
                arguments={"delete_attachments": False}
            )
            return result


async def mcp_add_memory(text, infer=False):
    """Add memory via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "add_memories",
                arguments={"text": text, "infer": infer}
            )
            return result


async def mcp_search(query):
    """Search memories via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "search_memory",
                arguments={"query": query}
            )
            return result


async def timed_search(query, label):
    """Execute search and measure time"""
    start = time.time()
    result = await mcp_search(query)
    elapsed = time.time() - start

    # Parse result to get count
    search_data = json.loads(result.content[0].text)
    count = len(search_data.get("results", []))

    return elapsed, count


async def continuous_search_loop(query, duration_seconds):
    """Run searches continuously for specified duration, measuring each"""
    print(f"\n{'='*80}")
    print(f"CONTINUOUS SEARCH LOOP ({duration_seconds}s)")
    print(f"{'='*80}\n")

    results = []
    start_time = time.time()
    search_num = 1

    while time.time() - start_time < duration_seconds:
        elapsed, count = await timed_search(query, f"Search #{search_num}")
        results.append(elapsed)
        print(f"Search #{search_num:3d}: {elapsed*1000:6.1f}ms (found {count} results)")
        search_num += 1
        await asyncio.sleep(0.1)  # Small delay between searches

    return results


async def main():
    print("=" * 80)
    print("ASYNC PERFORMANCE TEST")
    print("=" * 80)
    print()
    print("This test verifies that search operations remain fast while")
    print("a long add operation is running (proof of non-blocking async).")
    print()

    # Step 1: Delete all
    print("=== STEP 1: Delete All Memories ===")
    await mcp_delete_all()
    print("✓ All memories deleted")
    print()

    # Step 2: Add a short test memory
    print("=== STEP 2: Add Test Memory ===")
    test_text = "Python is a programming language"
    print(f"Adding: '{test_text}'")
    await mcp_add_memory(test_text, infer=False)
    print("✓ Test memory added")
    print()

    # Step 3: Baseline search performance (no background load)
    print("=== STEP 3: Baseline Search Performance (3 seconds) ===")
    baseline_results = await continuous_search_loop("python", 3)
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

    # Start long add in background
    add_task = asyncio.create_task(mcp_add_memory(long_text, infer=False))

    # Give it a moment to start
    await asyncio.sleep(0.5)

    # Run searches while add is running
    print("Running searches concurrently with add operation...")
    load_results = await continuous_search_loop("python", 3)
    load_avg = sum(load_results) / len(load_results) if load_results else 0
    print(f"\n📊 Under Load Average: {load_avg*1000:.1f}ms ({len(load_results)} searches)")

    # Wait for add to complete
    print("\nWaiting for background add to complete...")
    await add_task
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
            print("✅ EXCELLENT: Minimal slowdown - async is working perfectly!")
            print("   Search operations are not blocked by long add operation.")
        elif slowdown < 50:
            print("✓ GOOD: Some slowdown but acceptable - async is working.")
            print("  Search operations can run concurrently with add.")
        else:
            print("⚠️  WARNING: Significant slowdown detected.")
            print("   This might indicate event loop blocking or resource contention.")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
