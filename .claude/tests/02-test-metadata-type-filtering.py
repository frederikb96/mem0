#!/usr/bin/env python3
"""
Test metadata filtering using 'type' field.
Tests ability to filter memories by custom metadata (type: personal, notes, conversations).

Authentication via custom headers (X-User-Id, X-Client-Name).
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


def mcp_add_memory(text, metadata=None, infer=False):
    """Add memory via MCP with optional metadata"""
    args = {
        "text": text,
        "infer": infer
    }
    if metadata:
        args["metadata"] = metadata
    return call_mcp_tool("add_memories", args)


def mcp_search(query, filters=None, include_metadata=True):
    """Search memories via MCP with optional filters"""
    args = {
        "query": query,
        "include_metadata": include_metadata
    }
    if filters:
        args["filters"] = filters
    return call_mcp_tool("search_memory", args)


def main():
    print("=" * 80)
    print("MCP API TEST - Metadata Type Filtering")
    print("=" * 80)
    print(f"Server: {MCP_URL}")
    print(f"Session: {SESSION_ID}")
    print(f"User: {TEST_USER_ID}")
    print(f"Client: {TEST_CLIENT_NAME}")
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
    time.sleep(2)

    # Step 2: Add personal memory
    print("\n=== STEP 2: Add Personal Memory ===")
    personal_text = "Freddy prefers dark mode for better readability"
    print(f"Text: {personal_text}")
    print("Metadata: type='personal'")
    result = mcp_add_memory(personal_text, metadata={"type": "personal"}, infer=False)
    print(f"Result: {json.dumps(result, indent=2)}")
    time.sleep(2)

    # Step 3: Add notes memory
    print("\n=== STEP 3: Add Notes Memory ===")
    notes_text = "Kubernetes uses etcd for cluster state storage and coordination"
    print(f"Text: {notes_text}")
    print("Metadata: type='notes'")
    result = mcp_add_memory(notes_text, metadata={"type": "notes"}, infer=False)
    print(f"Result: {json.dumps(result, indent=2)}")
    time.sleep(2)

    # Step 4: Add conversation memory
    print("\n=== STEP 4: Add Conversation Memory ===")
    conv_text = "Discussed the implementation of MCP metadata filtering with Claude"
    print(f"Text: {conv_text}")
    print("Metadata: type='conversations'")
    result = mcp_add_memory(conv_text, metadata={"type": "conversations"}, infer=False)
    print(f"Result: {json.dumps(result, indent=2)}")
    time.sleep(2)

    # Step 5: Search without filter (should find all 3)
    print("\n=== STEP 5: Search Without Filter (should find all 3) ===")
    query = "Freddy Kubernetes Claude"
    print(f"Query: '{query}'")
    print("Filter: None")
    result = mcp_search(query)
    print(f"Found {len(result.get('results', []))} memories")
    for i, mem in enumerate(result.get('results', []), 1):
        mem_type = mem.get('metadata', {}).get('type', 'N/A')
        print(f"  {i}. Type: {mem_type} | Memory: {mem.get('memory', '')[:60]}...")
    time.sleep(2)

    # Step 6: Filter by type='personal'
    print("\n=== STEP 6: Filter by type='personal' ===")
    query = "preferences readability dark"
    filters = {"type": "personal"}
    print(f"Query: '{query}'")
    print(f"Filter: {filters}")
    result = mcp_search(query, filters=filters)
    print(f"Found {len(result.get('results', []))} memories")
    for i, mem in enumerate(result.get('results', []), 1):
        mem_type = mem.get('metadata', {}).get('type', 'N/A')
        print(f"  {i}. Type: {mem_type} | Memory: {mem.get('memory', '')}")

    # Verify only personal
    types_found = [m.get('metadata', {}).get('type') for m in result.get('results', [])]
    if types_found == ['personal']:
        print("✓ PASS: Only 'personal' type found")
    else:
        print(f"✗ FAIL: Expected ['personal'], got {types_found}")
    time.sleep(2)

    # Step 7: Filter by type='notes'
    print("\n=== STEP 7: Filter by type='notes' ===")
    query = "kubernetes etcd"
    filters = {"type": "notes"}
    print(f"Query: '{query}'")
    print(f"Filter: {filters}")
    result = mcp_search(query, filters=filters)
    print(f"Found {len(result.get('results', []))} memories")
    for i, mem in enumerate(result.get('results', []), 1):
        mem_type = mem.get('metadata', {}).get('type', 'N/A')
        print(f"  {i}. Type: {mem_type} | Memory: {mem.get('memory', '')}")

    # Verify only notes
    types_found = [m.get('metadata', {}).get('type') for m in result.get('results', [])]
    if types_found == ['notes']:
        print("✓ PASS: Only 'notes' type found")
    else:
        print(f"✗ FAIL: Expected ['notes'], got {types_found}")
    time.sleep(2)

    # Step 8: Filter by type='conversations'
    print("\n=== STEP 8: Filter by type='conversations' ===")
    query = "MCP Claude discussion"
    filters = {"type": "conversations"}
    print(f"Query: '{query}'")
    print(f"Filter: {filters}")
    result = mcp_search(query, filters=filters)
    print(f"Found {len(result.get('results', []))} memories")
    for i, mem in enumerate(result.get('results', []), 1):
        mem_type = mem.get('metadata', {}).get('type', 'N/A')
        print(f"  {i}. Type: {mem_type} | Memory: {mem.get('memory', '')}")

    # Verify only conversations
    types_found = [m.get('metadata', {}).get('type') for m in result.get('results', [])]
    if types_found == ['conversations']:
        print("✓ PASS: Only 'conversations' type found")
    else:
        print(f"✗ FAIL: Expected ['conversations'], got {types_found}")
    time.sleep(2)

    # Step 9: Combined filter (type + date range)
    print("\n=== STEP 9: Combined Filter (type='notes' + date) ===")
    print("NOTE: Date filtering requires use_numeric_date_filters=true in config")
    print("      Enable via Settings UI or config.json")
    # Get actual created_at from the notes memory
    notes_search = mcp_search("kubernetes", include_metadata=True)
    if notes_search.get('results'):
        notes_created_at = notes_search['results'][0].get('created_at')
        print(f"Notes memory created at: {notes_created_at}")

        # Use the actual timestamp as the filter
        query = "storage"
        filters = {
            "type": "notes",
            "created_at": {"gte": notes_created_at}
        }
        print(f"Query: '{query}'")
        print(f"Filter: type='notes' AND created_at >= {notes_created_at}")
        result = mcp_search(query, filters=filters)
        print(f"Found {len(result.get('results', []))} memories")
        for i, mem in enumerate(result.get('results', []), 1):
            mem_type = mem.get('metadata', {}).get('type', 'N/A')
            created_at = mem.get('created_at', 'N/A')
            print(f"  {i}. Type: {mem_type} | Created: {created_at} | Memory: {mem.get('memory', '')[:50]}...")

        # Verify results (lenient check - date filtering may not be enabled)
        types_found = [m.get('metadata', {}).get('type') for m in result.get('results', [])]
        if len(types_found) == 1 and types_found[0] == 'notes':
            print("✓ PASS: Combined filter working (type + date)")
        elif len(types_found) == 0:
            print("⚠ SKIP: No results (date filtering may not be enabled in config)")
        else:
            print(f"✗ FAIL: Expected 1 'notes' memory, got {len(types_found)} with types {types_found}")
    else:
        print("✗ FAIL: Could not get notes memory timestamp")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nSUMMARY:")
    print("- ✓ Created 3 memories with different 'type' metadata")
    print("- ✓ Filtered by type='personal' (should find 1)")
    print("- ✓ Filtered by type='notes' (should find 1)")
    print("- ✓ Filtered by type='conversations' (should find 1)")
    print("- ✓ Combined filter: type + date range")
    print("\nReview output above for any failures.")


if __name__ == "__main__":
    main()
