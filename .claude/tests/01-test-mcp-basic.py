#!/usr/bin/env python3
"""
Simple MCP API test using Streamable HTTP transport.
Prints MCP responses for visual verification.

Authentication via custom headers (X-User-Id, X-Client-Name)
set once instead of passed as parameters on every call.
"""

import json
import time
import uuid
import requests

BASE_URL = "http://localhost:8765"
MCP_URL = f"{BASE_URL}/mcp"
SESSION_ID = str(uuid.uuid4())
TEST_USER_ID = "frederik"
TEST_CLIENT_NAME = "test-client"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Mcp-Session-Id": SESSION_ID,
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
        response = requests.post(MCP_URL, headers=HEADERS, json=payload, timeout=30)
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


def mcp_add_memory(text, infer=True):
    """Add memory via MCP"""
    return call_mcp_tool("add_memories", {
        "text": text,
        "infer": infer
    })


def mcp_search(query):
    """Search memories via MCP"""
    return call_mcp_tool("search_memory", {
        "query": query
    })


def mcp_delete_memories(memory_ids):
    """Delete specific memories by ID via MCP"""
    return call_mcp_tool("delete_memories", {
        "memory_ids": memory_ids
    })


def mcp_update_memory(memory_id, text, metadata=None):
    """Update memory content and metadata via MCP"""
    args = {
        "memory_id": memory_id,
        "text": text
    }
    if metadata:
        args["metadata"] = metadata
    return call_mcp_tool("update_memory", args)


def main():
    print("=" * 80)
    print("MCP API BASIC TEST - Streamable HTTP Transport")
    print("=" * 80)
    print(f"Server: {MCP_URL}")
    print(f"Session: {SESSION_ID}")
    print(f"User: {TEST_USER_ID} (via X-User-Id header)")
    print(f"Client: {TEST_CLIENT_NAME} (via X-Client-Name header)")
    print()

    # Test connection
    try:
        requests.get(f"{BASE_URL}/docs", timeout=5)
        print("✓ Server is running")
        print("-" * 80)
    except Exception as e:
        print(f"✗ Server not reachable: {e}")
        return

    # Step 1: Delete all
    print("\n=== STEP 1: Delete All Memories ===")
    result = mcp_delete_all()
    print(f"Result: {result}")
    time.sleep(2)

    # Step 2: Add memory with infer=False (verbatim storage)
    print("\n=== STEP 2: Add Memory with infer=False ===")
    text_false = "The quantum entanglement phenomenon exhibits non-local correlations between particles."
    print(f"Input: {text_false}")
    print("infer=False (should store verbatim)")
    result = mcp_add_memory(text_false, infer=False)
    print(f"Result: {result}")
    time.sleep(2)

    # Step 3: Search for infer=False memory
    print("\n=== STEP 3: Search for infer=False Memory ===")
    query = "quantum"
    print(f"Query: {query}")
    print("(Should find verbatim memory)")
    result = mcp_search(query)
    print(f"Result: {result}")

    # Extract memory ID from search result
    memory_id = result["results"][0]["id"] if result.get("results") else None
    print(f"\nExtracted Memory ID: {memory_id}")
    time.sleep(2)

    if not memory_id:
        print("\n✗ Failed to get memory ID, stopping test")
        return

    # Step 4: Update that memory with new content and metadata
    print("\n=== STEP 4: Update Memory Content and Metadata ===")
    updated_text = "Updated: The quantum entanglement phenomenon demonstrates spooky action at a distance."
    custom_metadata = {"category": "physics", "topic": "quantum", "updated_test": "true"}
    print(f"New text: {updated_text}")
    print(f"Custom metadata: {custom_metadata}")
    result = mcp_update_memory(memory_id, updated_text, custom_metadata)
    print(f"Result: {result}")
    time.sleep(2)

    # Step 5: Search again to verify update
    print("\n=== STEP 5: Search to Verify Update ===")
    query = "spooky action"
    print(f"Query: {query}")
    print("(Should find updated content)")
    result = mcp_search(query)
    print(f"Result: {result}")
    time.sleep(2)

    # Step 6: Delete that specific memory
    print("\n=== STEP 6: Delete Specific Memory ===")
    print(f"Deleting memory: {memory_id}")
    result = mcp_delete_memories([memory_id])
    print(f"Result: {result}")
    time.sleep(2)

    # Step 7: Search again to verify deletion
    print("\n=== STEP 7: Search Again (should be empty) ===")
    query = "quantum"
    print(f"Query: {query}")
    print("(Should find nothing)")
    result = mcp_search(query)
    print(f"Result: {result}")
    time.sleep(2)

    # Step 8: Add memory with infer=True (LLM extraction)
    print("\n=== STEP 8: Add Memory with infer=True ===")
    text_true = "Lenovo supports linux quite well, that is cool. However, docker is sometimes not as nice as podman but is more popular"
    print(f"Input: {text_true}")
    print("infer=True (should extract facts via LLM)")
    result = mcp_add_memory(text_true, infer=True)
    print(f"Result: {result}")
    time.sleep(3)

    # Step 9: Search for infer=True memory
    print("\n=== STEP 9: Search for infer=True Memory ===")
    query = "Lenovo"
    print(f"Query: {query}")
    print("(Should find LLM-extracted facts)")
    result = mcp_search(query)
    print(f"Result: {result}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE - REVIEW OUTPUT ABOVE")
    print("=" * 80)


if __name__ == "__main__":
    main()
