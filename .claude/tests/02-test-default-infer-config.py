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

import json
import uuid
import requests

# Configuration
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

# Test data - same as infer=True example from 01-test-mcp-basic.py (Step 8)
TEST_TEXT = "Lenovo supports linux quite well, that is cool. However, docker is sometimes not as nice as podman but is more popular"


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


def run_test():
    print("=" * 80)
    print("MCP Default Infer Config Test")
    print("=" * 80)
    print(f"User ID: {TEST_USER_ID}")
    print(f"MCP URL: {MCP_URL}")
    print(f"Test text: {TEST_TEXT}")
    print()

    # Step 1: Clean slate - delete all memories
    print("Step 1: Cleaning up - delete all memories")
    print("-" * 80)
    try:
        result = call_mcp_tool("delete_all_memories", {})
        print(f"Delete all result: {result}")
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

    result = call_mcp_tool("add_memories", {"text": TEST_TEXT})

    print(f"Add result: {result}")

    # Parse response to get memory ID
    if "results" in result and len(result["results"]) > 0:
        memory_id = result["results"][0]["id"]
        stored_memory = result["results"][0]["memory"]
        print(f"Memory ID: {memory_id}")
        print(f"Stored as: {stored_memory}")
        print()
    else:
        print("ERROR: No memory returned in add response")
        return

    # Step 3: Search to retrieve the memory
    print("Step 3: Search for the memory")
    print("-" * 80)
    search_result = call_mcp_tool("search_memory", {"query": "Lenovo linux"})

    if "results" in search_result and len(search_result["results"]) > 0:
        retrieved_memory = search_result["results"][0]["memory"]
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
    run_test()
