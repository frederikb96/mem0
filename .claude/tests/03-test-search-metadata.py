#!/usr/bin/env python3
"""
Test MCP search_memory with include_metadata parameter.
"""

import asyncio
import json
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


async def mcp_search(query, include_metadata=False):
    """Search memories via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "search_memory",
                arguments={"query": query, "include_metadata": include_metadata}
            )
            return result


async def main():
    print("=" * 80)
    print("MCP SEARCH METADATA TEST")
    print("=" * 80)
    print()

    # Step 1: Delete all
    print("=== STEP 1: Delete All Memories ===")
    result = await mcp_delete_all()
    print(f"Result: {result}")
    print()

    # Step 2: Add memory with infer=False (verbatim)
    print("=== STEP 2: Add Memory with infer=False ===")
    text = "Quantum mechanics describes behavior at microscopic scales."
    print(f"Input: {text}")
    print("infer=False (should store verbatim with role=user metadata)")
    print()
    result = await mcp_add_memory(text, infer=False)
    print(f"Result: {result}")
    print()

    # Step 3: Search WITHOUT metadata (default behavior)
    print("=== STEP 3: Search WITHOUT metadata (include_metadata=False) ===")
    query = "quantum"
    print(f"Query: {query}")
    print("(Should return only core fields: id, memory, hash, timestamps, score)")
    print()
    result = await mcp_search(query, include_metadata=False)
    print(f"Result: {result}")

    # Parse and pretty print
    search_data = json.loads(result.content[0].text)
    print("\nParsed results:")
    print(json.dumps(search_data, indent=2))
    print()

    # Step 4: Search WITH metadata
    print("=== STEP 4: Search WITH metadata (include_metadata=True) ===")
    print(f"Query: {query}")
    print("(Should return core fields + metadata fields)")
    print()
    result = await mcp_search(query, include_metadata=True)
    print(f"Result: {result}")

    # Parse and pretty print
    search_data = json.loads(result.content[0].text)
    print("\nParsed results:")
    print(json.dumps(search_data, indent=2))
    print()

    # Compare field counts
    print("=== COMPARISON ===")
    search_without = json.loads((await mcp_search(query, include_metadata=False)).content[0].text)
    search_with = json.loads((await mcp_search(query, include_metadata=True)).content[0].text)

    if search_without["results"]:
        without_fields = set(search_without["results"][0].keys())
        print(f"WITHOUT metadata fields: {sorted(without_fields)}")

    if search_with["results"]:
        with_fields = set(search_with["results"][0].keys())
        print(f"WITH metadata fields: {sorted(with_fields)}")

        # Show difference
        added_fields = with_fields - without_fields
        if added_fields:
            print(f"\nAdded fields with include_metadata=True: {sorted(added_fields)}")
        else:
            print("\n⚠️  No additional fields added (metadata might be empty)")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
