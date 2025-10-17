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


async def mcp_add_memory(text):
    """Add memory via MCP"""
    async with sse_client(MCP_SSE_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "add_memories",
                arguments={"text": text}
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

    # Step 2: Add memory
    print("=== STEP 2: Add Memory ===")
    text = "Lenovo supports linux quite well, that is cool. However, docker is somtimes not as nice as podman but is more popular"
    print(f"Input: {text}")
    print()
    result = await mcp_add_memory(text)
    print(f"Result: {result}")
    print()
    time.sleep(3)

    # Step 3: Search
    print("=== STEP 3: Search for Memory ===")
    query = "Lenovo"
    print(f"Query: {query}")
    print()
    result = await mcp_search(query)
    print(f"Result: {result}")
    print()

    print("=" * 80)
    print("TEST COMPLETE - REVIEW OUTPUT ABOVE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
