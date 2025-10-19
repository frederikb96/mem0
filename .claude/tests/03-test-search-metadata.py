#!/usr/bin/env python3
"""
Test MCP search_memory with include_metadata parameter.
"""

import json
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


def mcp_add_memory(text, infer=True, metadata=None):
    """Add memory via MCP"""
    args = {"text": text, "infer": infer}
    if metadata:
        args["metadata"] = metadata
    return call_mcp_tool("add_memories", args)


def mcp_search(query, include_metadata=False):
    """Search memories via MCP"""
    return call_mcp_tool("search_memory", {"query": query, "include_metadata": include_metadata})


def main():
    print("=" * 80)
    print("MCP SEARCH METADATA TEST")
    print("=" * 80)
    print()

    # Step 1: Delete all
    print("=== STEP 1: Delete All Memories ===")
    result = mcp_delete_all()
    print(f"Result: {result}")
    print()

    # Step 2: Add memory with infer=False and custom metadata
    print("=== STEP 2: Add Memory with infer=False and custom metadata ===")
    text = "Quantum mechanics describes behavior at microscopic scales."
    custom_metadata = {
        "category": "science",
        "topic": "physics",
        "importance": "high"
    }
    print(f"Input: {text}")
    print(f"Metadata: {custom_metadata}")
    print("infer=False (should store verbatim with role=user + custom metadata)")
    print()
    result = mcp_add_memory(text, infer=False, metadata=custom_metadata)
    print(f"Result: {result}")
    print()

    # Step 3: Search WITHOUT metadata (default behavior)
    print("=== STEP 3: Search WITHOUT metadata (include_metadata=False) ===")
    query = "quantum"
    print(f"Query: {query}")
    print("(Should return only core fields: id, memory, hash, timestamps, score)")
    print()
    result = mcp_search(query, include_metadata=False)
    print(f"Result: {result}")

    # Pretty print
    print("\nParsed results:")
    print(json.dumps(result, indent=2))
    print()

    # Step 4: Search WITH metadata
    print("=== STEP 4: Search WITH metadata (include_metadata=True) ===")
    print(f"Query: {query}")
    print("(Should return core fields + metadata fields)")
    print()
    result = mcp_search(query, include_metadata=True)
    print(f"Result: {result}")

    # Pretty print
    print("\nParsed results:")
    print(json.dumps(result, indent=2))
    print()

    # Compare field counts
    print("=== COMPARISON ===")
    search_without = mcp_search(query, include_metadata=False)
    search_with = mcp_search(query, include_metadata=True)

    if search_without.get("results"):
        without_fields = set(search_without["results"][0].keys())
        print(f"WITHOUT metadata fields: {sorted(without_fields)}")

    if search_with.get("results"):
        with_fields = set(search_with["results"][0].keys())
        print(f"WITH metadata fields: {sorted(with_fields)}")

        # Show difference
        added_fields = with_fields - without_fields
        if added_fields:
            print(f"\nAdded fields with include_metadata=True: {sorted(added_fields)}")
        else:
            print("\n⚠️  No additional fields added (metadata might be empty)")

        # Verify custom metadata is present
        print("\n=== VERIFY CUSTOM METADATA ===")
        first_result = search_with["results"][0]
        metadata_obj = first_result.get("metadata", {})
        print(f"Custom metadata retrieved: {metadata_obj}")

        # Check for expected custom fields
        expected_fields = ["category", "topic", "importance"]
        found_fields = [f for f in expected_fields if f in metadata_obj]

        if found_fields:
            print(f"✅ Custom metadata fields found: {found_fields}")
            for field in found_fields:
                print(f"   {field} = {metadata_obj[field]}")
        else:
            print("❌ No custom metadata fields found!")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
