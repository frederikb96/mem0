#!/usr/bin/env python3
"""
Simple MCP API test.
Prints MCP responses for visual verification.
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


async def mcp_add_memory(text, infer=True):
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


async def mcp_delete_memories(memory_ids):
    """Delete specific memories by ID via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "delete_memories",
                arguments={"memory_ids": memory_ids}
            )
            return result


async def mcp_update_memory(memory_id, text, metadata=None):
    """Update memory content and metadata via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            args = {"memory_id": memory_id, "text": text}
            if metadata:
                args["metadata"] = metadata
            result = await session.call_tool(
                "update_memory",
                arguments=args
            )
            return result


async def main():
    print("=" * 80)
    print("MCP API BASIC TEST")
    print("=" * 80)
    print()

    # Step 1: Delete all
    print("=== STEP 1: Delete All Memories ===")
    result = await mcp_delete_all()
    print(f"Result: {result}")
    print()
    time.sleep(2)

    # Step 2: Add memory with infer=False (verbatim storage)
    print("=== STEP 2: Add Memory with infer=False ===")
    text_false = "The quantum entanglement phenomenon exhibits non-local correlations between particles."
    print(f"Input: {text_false}")
    print(f"infer=False (should store verbatim)")
    print()
    result = await mcp_add_memory(text_false, infer=False)
    print(f"Result: {result}")
    print()
    time.sleep(2)

    # Step 3: Search for infer=False memory
    print("=== STEP 3: Search for infer=False Memory ===")
    query = "quantum"
    print(f"Query: {query}")
    print("(Should find verbatim memory)")
    print()
    result = await mcp_search(query)
    print(f"Result: {result}")

    # Extract memory ID from search result
    search_data = json.loads(result.content[0].text)
    memory_id = search_data["results"][0]["id"] if search_data["results"] else None
    print(f"\nExtracted Memory ID: {memory_id}")
    print()
    time.sleep(2)

    # Step 4: Update that memory with new content and metadata
    print("=== STEP 4: Update Memory Content and Metadata ===")
    updated_text = "Updated: The quantum entanglement phenomenon demonstrates spooky action at a distance."
    custom_metadata = {"category": "physics", "topic": "quantum", "updated_test": "true"}
    print(f"New text: {updated_text}")
    print(f"Custom metadata: {custom_metadata}")
    print()
    result = await mcp_update_memory(memory_id, updated_text, custom_metadata)
    print(f"Result: {result}")
    print()
    time.sleep(2)

    # Step 5: Search again to verify update
    print("=== STEP 5: Search to Verify Update ===")
    query = "spooky action"
    print(f"Query: {query}")
    print("(Should find updated content)")
    print()
    result = await mcp_search(query)
    print(f"Result: {result}")
    print()
    time.sleep(2)

    # Step 6: Delete that specific memory
    print("=== STEP 6: Delete Specific Memory ===")
    print(f"Deleting memory: {memory_id}")
    print()
    result = await mcp_delete_memories([memory_id])
    print(f"Result: {result}")
    print()
    time.sleep(2)

    # Step 7: Search again to verify deletion
    print("=== STEP 7: Search Again (should be empty) ===")
    query = "quantum"
    print(f"Query: {query}")
    print("(Should find nothing)")
    print()
    result = await mcp_search(query)
    print(f"Result: {result}")
    print()
    time.sleep(2)

    # Step 8: Add memory with infer=True (LLM extraction)
    print("=== STEP 8: Add Memory with infer=True ===")
    text_true = "Lenovo supports linux quite well, that is cool. However, docker is sometimes not as nice as podman but is more popular"
    print(f"Input: {text_true}")
    print(f"infer=True (should extract facts via LLM)")
    print()
    result = await mcp_add_memory(text_true, infer=True)
    print(f"Result: {result}")
    print()
    time.sleep(3)

    # Step 9: Search for infer=True memory
    print("=== STEP 9: Search for infer=True Memory ===")
    query = "Lenovo"
    print(f"Query: {query}")
    print("(Should find LLM-extracted facts)")
    print()
    result = await mcp_search(query)
    print(f"Result: {result}")
    print()

    print("=" * 80)
    print("TEST COMPLETE - REVIEW OUTPUT ABOVE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
