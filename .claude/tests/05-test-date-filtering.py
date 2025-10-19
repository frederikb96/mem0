#!/usr/bin/env python3
"""
Test date filtering in Qdrant using numeric timestamps.
Tests that created_at filters work correctly with gte operator.
"""

import json
import time
import uuid
import requests
from datetime import datetime

BASE_URL = "http://localhost:8765"
MCP_URL = f"{BASE_URL}/mcp"
SESSION_ID = str(uuid.uuid4())
TEST_USER_ID = "frederik"
TEST_CLIENT_NAME = "test-date-filter"

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


def mcp_add_memory(text, infer=False):
    """Add memory via MCP"""
    return call_mcp_tool("add_memories", {
        "text": text,
        "infer": infer
    })


def mcp_search(query, filters=None):
    """Search memories via MCP with optional filters"""
    args = {"query": query}
    if filters:
        args["filters"] = filters
    return call_mcp_tool("search_memory", args)


def main():
    print("=" * 80)
    print("DATE FILTERING TEST - Qdrant Numeric Timestamps")
    print("=" * 80)
    print(f"Server: {MCP_URL}")
    print(f"Session: {SESSION_ID}")
    print(f"User: {TEST_USER_ID}")
    print()

    # Test connection
    try:
        requests.get(f"{BASE_URL}/docs", timeout=5)
        print("✓ Server is running")
        print("-" * 80)
    except Exception as e:
        print(f"✗ Server not reachable: {e}")
        return

    # Step 1: Clean slate
    print("\n=== STEP 1: Delete All Memories ===")
    result = mcp_delete_all()
    print(f"Result: {result}")
    time.sleep(1)

    # Step 2: Add first memory with infer=False
    print("\n=== STEP 2: Add First Memory (infer=False) ===")
    text1 = "This is the first test memory for date filtering"
    print(f"Text: {text1}")
    result1 = mcp_add_memory(text1, infer=False)
    print(f"Result: {json.dumps(result1, indent=2)}")
    time.sleep(1)

    # Step 3: Wait 2 seconds
    print("\n=== STEP 3: Waiting 2 seconds... ===")
    time.sleep(2)

    # Step 4: Add second memory with infer=False
    print("\n=== STEP 4: Add Second Memory (infer=False) ===")
    text2 = "This is the second test memory for date filtering"
    print(f"Text: {text2}")
    result2 = mcp_add_memory(text2, infer=False)
    print(f"Result: {json.dumps(result2, indent=2)}")
    time.sleep(1)

    # Step 5: Search for both memories (no filter)
    print("\n=== STEP 5: Search All Memories (no filter) ===")
    query = "test memory"
    print(f"Query: {query}")
    search_all = mcp_search(query)
    print(f"Found {len(search_all.get('results', []))} memories")
    print(f"Results: {json.dumps(search_all, indent=2)}")

    if not search_all.get("results") or len(search_all["results"]) < 2:
        print("\n✗ Expected 2 memories, got less. Stopping test.")
        return

    # Step 6: Extract timestamp from first memory
    first_memory = search_all["results"][0]
    second_memory = search_all["results"][1]
    first_created_at = first_memory.get("created_at")
    second_created_at = second_memory.get("created_at")
    print(f"\nFirst memory created_at: {first_created_at}")
    print(f"Second memory created_at: {second_created_at}")

    if not first_created_at:
        print("\n✗ No created_at field found. Stopping test.")
        return

    # Parse the ISO timestamp and add 1 second to filter between first and second memory
    try:
        dt = datetime.fromisoformat(first_created_at)
        # Add 1 second to filter threshold - keep the same timezone
        filter_timestamp_seconds = dt.timestamp() + 1
        filter_dt = datetime.fromtimestamp(filter_timestamp_seconds, tz=dt.tzinfo)
        filter_timestamp = filter_dt.isoformat()
        print(f"Filter timestamp (first + 1s): {filter_timestamp}")
        print(f"This should exclude first memory ({first_created_at})")
        print(f"This should include second memory ({second_created_at})")
    except Exception as e:
        print(f"\n✗ Failed to parse timestamp: {e}")
        return

    # Step 7: Search with gte date filter
    print("\n=== STEP 6: Search with created_at gte Filter ===")
    filters = {"created_at": {"gte": filter_timestamp}}
    print(f"Query: {query}")
    print(f"Filters: {filters}")
    filtered_results = mcp_search(query, filters=filters)
    print(f"Found {len(filtered_results.get('results', []))} memories")
    print(f"Results: {json.dumps(filtered_results, indent=2)}")

    # Step 8: Verify only second memory returned
    print("\n=== STEP 7: Verify Results ===")
    if not filtered_results.get("results"):
        print("✗ FAIL: No results returned with date filter")
        return

    if len(filtered_results["results"]) != 1:
        print(f"✗ FAIL: Expected 1 memory, got {len(filtered_results['results'])}")
        return

    returned_memory = filtered_results["results"][0]
    returned_text = returned_memory.get("memory", "")

    if "second" in returned_text.lower():
        print("✓ PASS: Correct memory returned (second memory)")
        print(f"  Memory text: {returned_text}")
        print(f"  Memory created_at: {returned_memory.get('created_at')}")
    else:
        print("✗ FAIL: Wrong memory returned")
        print(f"  Expected 'second' in text, got: {returned_text}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
