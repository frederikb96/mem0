#!/usr/bin/env python3
"""
Test script for MCP list_attachments tool (once implemented).

This script verifies that the list_attachments MCP tool works correctly
with various filter combinations.

NOTE: The MCP tool is not yet implemented. This is a test plan/script
that can be used once the tool is added to mcp_server.py.
"""

import requests
import json
import time
from datetime import datetime, timedelta
import uuid

# Configuration
API_URL = "http://localhost:8765"
USER_ID = "test_user"


def create_test_attachment(content: str, custom_id: str = None) -> dict:
    """Create an attachment for testing."""
    url = f"{API_URL}/api/v1/attachments/"
    payload = {"content": content}
    if custom_id:
        payload["id"] = custom_id

    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def filter_attachments(
    page: int = 1,
    size: int = 10,
    search_query: str = None,
    from_date: int = None,
    to_date: int = None,
    sort_column: str = None,
    sort_direction: str = None,
    timeout: int = 5,
) -> dict:
    """Test the filter attachments endpoint (simulates what MCP tool would do)."""
    url = f"{API_URL}/api/v1/attachments/filter"
    payload = {
        "page": page,
        "size": size,
        "timeout": timeout,
    }

    if search_query:
        payload["search_query"] = search_query
    if from_date:
        payload["from_date"] = from_date
    if to_date:
        payload["to_date"] = to_date
    if sort_column:
        payload["sort_column"] = sort_column
    if sort_direction:
        payload["sort_direction"] = sort_direction

    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def delete_attachment(attachment_id: str):
    """Delete an attachment."""
    url = f"{API_URL}/api/v1/attachments/{attachment_id}"
    response = requests.delete(url)
    # Attachment delete returns 204, so don't check for json
    return response.status_code == 204


def test_list_all():
    """Test 1: List all attachments (no filters)."""
    print("Test 1: List all attachments")
    result = filter_attachments(page=1, size=10)

    assert "items" in result, "Response should have 'items'"
    assert "total" in result, "Response should have 'total'"
    assert "page" in result, "Response should have 'page'"
    assert "pages" in result, "Response should have 'pages'"

    print(f"  ✓ Found {result['total']} total attachments")
    print(f"  ✓ Page {result['page']} of {result['pages']}")
    print()


def test_search_by_content():
    """Test 2: Search by content substring."""
    print("Test 2: Search by content")

    # Create test attachment
    test_content = f"Test content for search - kubernetes config - {time.time()}"
    attachment = create_test_attachment(test_content)
    attachment_id = attachment["id"]

    try:
        # Search for it
        result = filter_attachments(search_query="kubernetes")

        found = any(item["id"] == attachment_id for item in result["items"])
        assert found, "Created attachment should be found in search results"

        print(f"  ✓ Search found attachment with 'kubernetes' in content")
    finally:
        delete_attachment(attachment_id)

    print()


def test_search_by_uuid():
    """Test 3: Search by partial UUID."""
    print("Test 3: Search by partial UUID")

    # Create test attachment
    attachment = create_test_attachment(f"UUID search test - {time.time()}")
    attachment_id = attachment["id"]

    try:
        # Search by first 8 chars of UUID
        partial_uuid = attachment_id[:8]
        result = filter_attachments(search_query=partial_uuid)

        found = any(item["id"] == attachment_id for item in result["items"])
        assert found, f"Attachment should be found by partial UUID '{partial_uuid}'"

        print(f"  ✓ Found attachment by partial UUID: {partial_uuid}")
    finally:
        delete_attachment(attachment_id)

    print()


def test_sort_by_created():
    """Test 4: Sort by created_at (desc)."""
    print("Test 4: Sort by created_at (desc)")

    # Create two attachments with small delay
    att1 = create_test_attachment(f"First attachment - {time.time()}")
    time.sleep(1)
    att2 = create_test_attachment(f"Second attachment - {time.time()}")

    try:
        result = filter_attachments(
            sort_column="created_at", sort_direction="desc", size=50
        )

        # Find our attachments in the results
        items = result["items"]
        att1_idx = next(
            (i for i, item in enumerate(items) if item["id"] == att1["id"]), None
        )
        att2_idx = next(
            (i for i, item in enumerate(items) if item["id"] == att2["id"]), None
        )

        if att1_idx is not None and att2_idx is not None:
            assert (
                att2_idx < att1_idx
            ), "Newer attachment should appear before older one (desc)"
            print(
                f"  ✓ Sort order correct: newer attachment (idx {att2_idx}) before older (idx {att1_idx})"
            )
    finally:
        delete_attachment(att1["id"])
        delete_attachment(att2["id"])

    print()


def test_pagination():
    """Test 5: Pagination works correctly."""
    print("Test 5: Pagination (page 1, size 2)")

    # Create 3 test attachments
    attachments = [
        create_test_attachment(f"Pagination test {i} - {time.time()}")
        for i in range(3)
    ]

    try:
        # Get first page with size 2
        result = filter_attachments(page=1, size=2)

        assert len(result["items"]) <= 2, "Page size should be respected"
        assert result["size"] == 2, "Response should show size=2"
        assert result["page"] == 1, "Response should show page=1"

        print(f"  ✓ Page 1: {len(result['items'])} items (max 2)")
        print(f"  ✓ Total pages: {result['pages']}")
    finally:
        for att in attachments:
            delete_attachment(att["id"])

    print()


def test_content_preview():
    """Test 6: Content preview (200 chars max)."""
    print("Test 6: Content preview (200 chars)")

    # Create attachment with >200 chars
    long_content = "A" * 500
    attachment = create_test_attachment(long_content)

    try:
        result = filter_attachments(search_query=attachment["id"][:8])

        item = next(
            (item for item in result["items"] if item["id"] == attachment["id"]), None
        )
        assert item, "Attachment should be found"

        assert len(item["content"]) == 200, "Content should be truncated to 200 chars"
        assert (
            item["content_length"] == 500
        ), "content_length should show full length"

        print(f"  ✓ Content preview length: {len(item['content'])} chars")
        print(f"  ✓ Full content length: {item['content_length']} chars")
    finally:
        delete_attachment(attachment["id"])

    print()


def test_empty_search():
    """Test 7: Empty search results."""
    print("Test 7: Empty search results")

    # Search for something that doesn't exist
    result = filter_attachments(search_query="xyznonexistent12345")

    assert len(result["items"]) == 0, "Should return empty list for no matches"
    assert result["total"] == 0, "Total should be 0"

    print(f"  ✓ Empty search returns 0 results")
    print()


def test_timeout_parameter():
    """Test 8: Timeout parameter is accepted."""
    print("Test 8: Timeout parameter")

    # Test with different timeout values
    for timeout in [1, 5, 10]:
        result = filter_attachments(timeout=timeout, size=5)
        assert "items" in result, f"Should work with timeout={timeout}"

    print(f"  ✓ Timeout parameter accepted (1s, 5s, 10s)")
    print()


def test_sort_by_size():
    """Test 9: Sort by size."""
    print("Test 9: Sort by size (desc)")

    # Create attachments of different sizes
    small = create_test_attachment("Small")
    large = create_test_attachment("A" * 1000)

    try:
        result = filter_attachments(sort_column="size", sort_direction="desc", size=50)

        items = result["items"]
        small_idx = next(
            (i for i, item in enumerate(items) if item["id"] == small["id"]), None
        )
        large_idx = next(
            (i for i, item in enumerate(items) if item["id"] == large["id"]), None
        )

        if small_idx is not None and large_idx is not None:
            assert (
                large_idx < small_idx
            ), "Larger attachment should appear first (desc)"
            print(f"  ✓ Sort by size works: large (idx {large_idx}) before small (idx {small_idx})")
    finally:
        delete_attachment(small["id"])
        delete_attachment(large["id"])

    print()


def test_combined_filters():
    """Test 10: Combined search + date filter."""
    print("Test 10: Combined filters (search + date)")

    # Create test attachment
    test_content = f"Combined filter test - elasticsearch - {time.time()}"
    attachment = create_test_attachment(test_content)

    try:
        # Get current timestamp
        now = int(time.time())
        hour_ago = now - 3600

        # Search with date filter
        result = filter_attachments(
            search_query="elasticsearch", from_date=hour_ago, to_date=now + 3600
        )

        found = any(item["id"] == attachment["id"] for item in result["items"])
        assert found, "Should find attachment with combined filters"

        print(f"  ✓ Combined search + date filter works")
    finally:
        delete_attachment(attachment["id"])

    print()


def run_all_tests():
    """Run all test cases."""
    print("=" * 60)
    print("MCP list_attachments Tool - Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_list_all,
        test_search_by_content,
        test_search_by_uuid,
        test_sort_by_created,
        test_pagination,
        test_content_preview,
        test_empty_search,
        test_timeout_parameter,
        test_sort_by_size,
        test_combined_filters,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
            print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed (out of {len(tests)} total)")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
