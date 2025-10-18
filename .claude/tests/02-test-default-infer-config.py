#!/usr/bin/env python3
"""
Test default_infer configuration setting via MCP.

This test verifies that the default_infer config value is properly applied
when no infer parameter is explicitly passed to add_memories.

Usage:
1. Make sure OpenMemory is running (docker-compose up)
2. Toggle default_infer in GUI settings (http://localhost:3000/settings)
3. Run this test: python 02-test-default-infer-config.py
4. Check if behavior matches the config setting:
   - default_infer=True: Content is transformed by LLM (semantic extraction)
   - default_infer=False: Content is stored verbatim (exact text)
"""

import asyncio
import json
from mcp import ClientSession
from mcp.client.sse import sse_client

# Configuration
BASE_URL = "http://localhost:8765"
TEST_USER = "frederik"
MCP_SSE_URL = f"{BASE_URL}/mcp/claude-code/sse/{TEST_USER}"

# Test data - same as infer=True example from 01-test-mcp-basic.py (Step 8)
TEST_TEXT = "Lenovo supports linux quite well, that is cool. However, docker is sometimes not as nice as podman but is more popular"

async def run_test():
    print("=" * 80)
    print("MCP Default Infer Config Test")
    print("=" * 80)
    print(f"User ID: {TEST_USER}")
    print(f"MCP URL: {MCP_SSE_URL}")
    print(f"Test text: {TEST_TEXT}")
    print()

    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()
            print("✓ MCP session initialized")
            print()

            # Step 1: Clean slate - delete all memories
            print("Step 1: Cleaning up - delete all memories")
            print("-" * 80)
            try:
                result = await session.call_tool("delete_all_memories", arguments={})
                print(f"Delete all result: {result.content[0].text}")
                print()
            except Exception as e:
                print(f"Warning: delete_all_memories failed (might be empty): {e}")
                print()

            # Step 2: Add memory WITHOUT specifying infer parameter
            # This should use the default_infer value from config
            print("Step 2: Add memory (infer parameter NOT specified)")
            print("-" * 80)
            print(f"Input: {TEST_TEXT}")
            print("Note: infer parameter is NOT passed - will use default_infer from config")
            print()

            result = await session.call_tool(
                "add_memories",
                arguments={
                    "text": TEST_TEXT,
                    # NOTE: No "infer" parameter - relies on default_infer config
                }
            )

            response_text = result.content[0].text
            print(f"Add result: {response_text}")

            # Parse response to get memory ID
            response_data = json.loads(response_text)
            if "results" in response_data and len(response_data["results"]) > 0:
                memory_id = response_data["results"][0]["id"]
                stored_memory = response_data["results"][0]["memory"]
                print(f"Memory ID: {memory_id}")
                print(f"Stored as: {stored_memory}")
                print()
            else:
                print("ERROR: No memory returned in add response")
                return

            # Step 3: Search to retrieve the memory
            print("Step 3: Search for the memory")
            print("-" * 80)
            result = await session.call_tool(
                "search_memory",
                arguments={"query": "Lenovo linux"}
            )

            search_text = result.content[0].text
            search_data = json.loads(search_text)

            if "results" in search_data and len(search_data["results"]) > 0:
                retrieved_memory = search_data["results"][0]["memory"]
                print(f"Retrieved: {retrieved_memory}")
                print()
            else:
                print("ERROR: Memory not found in search")
                return

            # Step 4: Analyze behavior - did infer happen?
            print("Step 4: Behavior Analysis")
            print("=" * 80)

            # Compare input vs stored content
            input_text = TEST_TEXT
            output_text = retrieved_memory

            # Check if content was transformed (infer=True) or verbatim (infer=False)
            is_verbatim = (input_text.lower() == output_text.lower())
            is_transformed = not is_verbatim

            print(f"Input text:     '{input_text}'")
            print(f"Retrieved text: '{output_text}'")
            print()

            if is_verbatim:
                print("✓ Result: VERBATIM STORAGE (infer=False behavior)")
                print("  → Content stored exactly as provided")
                print("  → This means default_infer config is set to FALSE")
                print()
                print("  If you expected transformation, check GUI settings:")
                print("  http://localhost:3000/settings")
                print("  Make sure 'Default Infer' toggle is ON")
            else:
                print("✓ Result: TRANSFORMED CONTENT (infer=True behavior)")
                print("  → LLM extracted semantic facts and transformed content")
                print("  → This means default_infer config is set to TRUE")
                print()
                print("  If you expected verbatim storage, check GUI settings:")
                print("  http://localhost:3000/settings")
                print("  Make sure 'Default Infer' toggle is OFF")

            print()
            print("=" * 80)
            print("Test completed successfully!")
            print()
            print("To test the opposite behavior:")
            print("1. Go to http://localhost:3000/settings")
            print("2. Toggle 'Default Infer' setting")
            print("3. Run this test again")
            print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_test())
