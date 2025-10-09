#!/usr/bin/env python3
"""
Comprehensive test for attachment filter endpoint.

This test verifies:
1. Basic pagination (different page sizes)
2. Search by content (substring match)
3. Search by UUID (partial match)
4. Sorting (created_at, updated_at, size - asc/desc)
5. Date range filtering (from_date, to_date)
6. Combined filters (search + sort + pagination)
7. Edge cases (empty results, invalid parameters)

Usage:
    python3 09-test-attachment-filter.py

Requirements:
    - OpenMemory service running at http://localhost:8765
    - OPENAI_API_KEY set in environment
"""

import requests
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


# Configuration
BASE_URL = "http://localhost:8765"
REST_API_URL = f"{BASE_URL}/api/v1"


@dataclass
class TestResult:
    """Result of a single test case"""
    name: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print a colored header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")


def print_test_result(result: TestResult):
    """Print a test result with color"""
    status = f"{Colors.OKGREEN}✓ PASS{Colors.ENDC}" if result.passed else f"{Colors.FAIL}✗ FAIL{Colors.ENDC}"
    print(f"{status} {result.name}")
    if not result.passed or result.details:
        print(f"  → {result.message}")
        if result.details:
            print(f"  Details: {json.dumps(result.details, indent=2)[:500]}...")
    print()


# ============================================================================
# Test Data Setup
# ============================================================================

# Global list to store created attachment IDs for cleanup
CREATED_ATTACHMENTS = []


def create_test_attachments() -> List[str]:
    """Create test attachments with various content and timestamps"""
    global CREATED_ATTACHMENTS

    print(f"{Colors.OKBLUE}Creating test attachments...{Colors.ENDC}")

    attachments_data = [
        # Various sizes and content types
        {"content": "Short attachment content for testing search functionality", "description": "Short text"},
        {"content": "Medium size attachment with some Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 5, "description": "Medium text"},
        {"content": "Large attachment content repeated many times to test size sorting and pagination. " * 50, "description": "Large text"},
        # Code-like content
        {"content": "def hello_world():\n    print('Hello, World!')\n    return True", "description": "Python code"},
        {"content": "SELECT * FROM users WHERE email LIKE '%@example.com';", "description": "SQL query"},
        # JSON-like content
        {"content": '{"name": "test", "value": 123, "nested": {"key": "value"}}', "description": "JSON data"},
        # Special characters
        {"content": "Test with special chars: @#$%^&*()_+-=[]{}|;:',.<>?/~`", "description": "Special chars"},
        # Numbers
        {"content": "12345 67890 Numbers: 42, 100, 999, 1000, 9999", "description": "Numbers"},
        # Repeated keyword for search testing
        {"content": "SEARCHABLE keyword appears here multiple times SEARCHABLE and SEARCHABLE again", "description": "Searchable keyword"},
        {"content": "Another SEARCHABLE content with different context", "description": "Searchable keyword 2"},
    ]

    created_ids = []
    for i, data in enumerate(attachments_data):
        try:
            response = requests.post(
                f"{REST_API_URL}/attachments",
                json={"content": data["content"]}
            )
            response.raise_for_status()
            attachment_id = response.json()["id"]
            created_ids.append(attachment_id)
            CREATED_ATTACHMENTS.append(attachment_id)
            print(f"  {Colors.OKGREEN}✓{Colors.ENDC} Created #{i+1}: {data['description']} (ID: {attachment_id[:8]}...)")

            # Small delay to ensure different timestamps
            time.sleep(0.1)
        except Exception as e:
            print(f"  {Colors.FAIL}✗{Colors.ENDC} Failed to create attachment: {str(e)}")

    print(f"{Colors.OKGREEN}Created {len(created_ids)} test attachments{Colors.ENDC}\n")
    return created_ids


def cleanup_test_attachments():
    """Clean up all test attachments"""
    global CREATED_ATTACHMENTS

    if not CREATED_ATTACHMENTS:
        return

    print(f"\n{Colors.OKBLUE}Cleaning up {len(CREATED_ATTACHMENTS)} test attachments...{Colors.ENDC}")
    for attachment_id in CREATED_ATTACHMENTS:
        try:
            requests.delete(f"{REST_API_URL}/attachments/{attachment_id}")
        except Exception as e:
            print(f"  {Colors.WARNING}Warning: Failed to delete {attachment_id}: {e}{Colors.ENDC}")

    CREATED_ATTACHMENTS = []
    print(f"{Colors.OKGREEN}Cleanup complete{Colors.ENDC}\n")


# ============================================================================
# Helper Functions
# ============================================================================

def filter_attachments(
    page: int = 1,
    size: int = 10,
    search_query: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_direction: Optional[str] = None,
    from_date: Optional[int] = None,
    to_date: Optional[int] = None
) -> Dict[str, Any]:
    """Call the filter attachments endpoint"""
    payload = {
        "page": page,
        "size": size
    }
    if search_query is not None:
        payload["search_query"] = search_query
    if sort_column is not None:
        payload["sort_column"] = sort_column
    if sort_direction is not None:
        payload["sort_direction"] = sort_direction
    if from_date is not None:
        payload["from_date"] = from_date
    if to_date is not None:
        payload["to_date"] = to_date

    response = requests.post(
        f"{REST_API_URL}/attachments/filter",
        json=payload
    )
    response.raise_for_status()
    return response.json()


# ============================================================================
# TEST CASES
# ============================================================================

def test_1_basic_pagination() -> TestResult:
    """Test 1: Basic pagination without filters"""
    try:
        print(f"{Colors.OKBLUE}Testing basic pagination...{Colors.ENDC}")

        # Default page size (10)
        result = filter_attachments(page=1, size=10)

        has_items = len(result["items"]) > 0
        has_total = result["total"] >= len(result["items"])
        has_pagination = "page" in result and "pages" in result
        correct_page = result["page"] == 1
        correct_size = result["size"] == 10

        passed = all([has_items, has_total, has_pagination, correct_page, correct_size])

        return TestResult(
            name="Basic pagination",
            passed=passed,
            message=f"Retrieved {len(result['items'])} items, total={result['total']}, page={result['page']}, pages={result['pages']}",
            details={"first_item": result["items"][0] if result["items"] else None}
        )
    except Exception as e:
        return TestResult(
            name="Basic pagination",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_2_different_page_sizes() -> TestResult:
    """Test 2: Different page sizes (5, 10, 25)"""
    try:
        print(f"{Colors.OKBLUE}Testing different page sizes...{Colors.ENDC}")

        sizes = [5, 10, 25]
        results = {}

        for size in sizes:
            result = filter_attachments(page=1, size=size)
            results[size] = {
                "returned": len(result["items"]),
                "requested": size,
                "total": result["total"]
            }

        # Verify each size returns the correct number or fewer (if total < size)
        all_correct = all(
            results[size]["returned"] <= size and
            (results[size]["returned"] == size or results[size]["returned"] == results[size]["total"])
            for size in sizes
        )

        return TestResult(
            name="Different page sizes",
            passed=all_correct,
            message=f"Tested sizes: {sizes}",
            details=results
        )
    except Exception as e:
        return TestResult(
            name="Different page sizes",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_3_search_by_content() -> TestResult:
    """Test 3: Search by content substring"""
    try:
        print(f"{Colors.OKBLUE}Testing search by content...{Colors.ENDC}")

        # Search for keyword that appears in test data
        result = filter_attachments(search_query="SEARCHABLE")

        found_items = len(result["items"])
        has_matches = found_items >= 2  # We created 2 attachments with "SEARCHABLE"

        # Verify all returned items contain the search term
        all_contain_keyword = all(
            "SEARCHABLE" in item["content"].upper()
            for item in result["items"]
        )

        passed = has_matches and all_contain_keyword

        return TestResult(
            name="Search by content substring",
            passed=passed,
            message=f"Found {found_items} items containing 'SEARCHABLE'",
            details={"items": [item["id"][:8] + "..." for item in result["items"]]}
        )
    except Exception as e:
        return TestResult(
            name="Search by content substring",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_4_search_by_uuid() -> TestResult:
    """Test 4: Search by partial UUID"""
    try:
        print(f"{Colors.OKBLUE}Testing search by UUID...{Colors.ENDC}")

        # Get first attachment ID
        all_attachments = filter_attachments(page=1, size=1)
        if not all_attachments["items"]:
            return TestResult(
                name="Search by partial UUID",
                passed=False,
                message="No attachments available for UUID search test"
            )

        full_uuid = all_attachments["items"][0]["id"]
        partial_uuid = full_uuid[:8]  # First 8 characters

        # Search by partial UUID
        result = filter_attachments(search_query=partial_uuid)

        found_items = len(result["items"])
        correct_match = any(item["id"] == full_uuid for item in result["items"])

        passed = found_items >= 1 and correct_match

        return TestResult(
            name="Search by partial UUID",
            passed=passed,
            message=f"Searched '{partial_uuid}', found {found_items} match(es)",
            details={"searched": partial_uuid, "found": full_uuid[:8] + "..."}
        )
    except Exception as e:
        return TestResult(
            name="Search by partial UUID",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_5_sort_by_created_asc() -> TestResult:
    """Test 5: Sort by created_at ascending (oldest first)"""
    try:
        print(f"{Colors.OKBLUE}Testing sort by created_at (asc)...{Colors.ENDC}")

        result = filter_attachments(
            page=1,
            size=5,
            sort_column="created_at",
            sort_direction="asc"
        )

        # Verify items are sorted (oldest to newest)
        dates = [item["created_at"] for item in result["items"]]
        is_sorted = dates == sorted(dates)

        return TestResult(
            name="Sort by created_at ascending",
            passed=is_sorted,
            message=f"Retrieved {len(result['items'])} items in ascending order",
            details={"dates": dates}
        )
    except Exception as e:
        return TestResult(
            name="Sort by created_at ascending",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_6_sort_by_created_desc() -> TestResult:
    """Test 6: Sort by created_at descending (newest first - default)"""
    try:
        print(f"{Colors.OKBLUE}Testing sort by created_at (desc)...{Colors.ENDC}")

        result = filter_attachments(
            page=1,
            size=5,
            sort_column="created_at",
            sort_direction="desc"
        )

        # Verify items are sorted (newest to oldest)
        dates = [item["created_at"] for item in result["items"]]
        is_sorted = dates == sorted(dates, reverse=True)

        return TestResult(
            name="Sort by created_at descending",
            passed=is_sorted,
            message=f"Retrieved {len(result['items'])} items in descending order",
            details={"dates": dates}
        )
    except Exception as e:
        return TestResult(
            name="Sort by created_at descending",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_7_sort_by_size() -> TestResult:
    """Test 7: Sort by content size"""
    try:
        print(f"{Colors.OKBLUE}Testing sort by size...{Colors.ENDC}")

        # Ascending (smallest first)
        result_asc = filter_attachments(
            page=1,
            size=5,
            sort_column="size",
            sort_direction="asc"
        )

        sizes_asc = [item["content_length"] for item in result_asc["items"]]
        is_sorted_asc = sizes_asc == sorted(sizes_asc)

        # Descending (largest first)
        result_desc = filter_attachments(
            page=1,
            size=5,
            sort_column="size",
            sort_direction="desc"
        )

        sizes_desc = [item["content_length"] for item in result_desc["items"]]
        is_sorted_desc = sizes_desc == sorted(sizes_desc, reverse=True)

        passed = is_sorted_asc and is_sorted_desc

        return TestResult(
            name="Sort by content size",
            passed=passed,
            message=f"Asc: {is_sorted_asc}, Desc: {is_sorted_desc}",
            details={
                "sizes_asc": sizes_asc,
                "sizes_desc": sizes_desc
            }
        )
    except Exception as e:
        return TestResult(
            name="Sort by content size",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_8_date_range_filter() -> TestResult:
    """Test 8: Date range filtering (from_date, to_date)"""
    try:
        print(f"{Colors.OKBLUE}Testing date range filtering...{Colors.ENDC}")

        # Get all attachments to find date range
        all_result = filter_attachments(page=1, size=100)

        if len(all_result["items"]) < 2:
            return TestResult(
                name="Date range filtering",
                passed=False,
                message="Not enough attachments for date range test"
            )

        # Get timestamps
        timestamps = [
            datetime.fromisoformat(item["created_at"].replace('Z', '+00:00')).timestamp()
            for item in all_result["items"]
        ]
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        mid_ts = (min_ts + max_ts) / 2

        # Test: only items after midpoint
        result_after = filter_attachments(from_date=int(mid_ts))
        after_count = len(result_after["items"])

        # Test: only items before midpoint
        result_before = filter_attachments(to_date=int(mid_ts))
        before_count = len(result_before["items"])

        # Verify we got some filtering
        total_count = len(all_result["items"])
        has_filtering = after_count < total_count and before_count < total_count

        return TestResult(
            name="Date range filtering",
            passed=has_filtering,
            message=f"Total: {total_count}, After mid: {after_count}, Before mid: {before_count}",
            details={
                "min_timestamp": min_ts,
                "mid_timestamp": mid_ts,
                "max_timestamp": max_ts
            }
        )
    except Exception as e:
        return TestResult(
            name="Date range filtering",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_9_combined_filters() -> TestResult:
    """Test 9: Combined filters (search + sort + pagination)"""
    try:
        print(f"{Colors.OKBLUE}Testing combined filters...{Colors.ENDC}")

        # Combine search, sort, and pagination
        result = filter_attachments(
            search_query="test",
            page=1,
            size=3,
            sort_column="created_at",
            sort_direction="desc"
        )

        has_results = len(result["items"]) > 0
        respects_page_size = len(result["items"]) <= 3

        # Verify search filter worked
        all_match_search = all(
            "test" in item["content"].lower()
            for item in result["items"]
        )

        # Verify sorting worked
        dates = [item["created_at"] for item in result["items"]]
        is_sorted = dates == sorted(dates, reverse=True)

        passed = has_results and respects_page_size and all_match_search and is_sorted

        return TestResult(
            name="Combined filters (search + sort + pagination)",
            passed=passed,
            message=f"Found {len(result['items'])} results with all filters applied",
            details={"returned_ids": [item["id"][:8] + "..." for item in result["items"]]}
        )
    except Exception as e:
        return TestResult(
            name="Combined filters",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_10_empty_search_results() -> TestResult:
    """Test 10: Search with no matching results"""
    try:
        print(f"{Colors.OKBLUE}Testing empty search results...{Colors.ENDC}")

        # Search for something that definitely doesn't exist
        result = filter_attachments(search_query="NONEXISTENT_KEYWORD_12345")

        no_results = len(result["items"]) == 0
        correct_total = result["total"] == 0
        correct_structure = "items" in result and "pages" in result

        passed = no_results and correct_total and correct_structure

        return TestResult(
            name="Empty search results",
            passed=passed,
            message="Correctly returns empty results for non-matching search",
            details=result
        )
    except Exception as e:
        return TestResult(
            name="Empty search results",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_11_pagination_beyond_last_page() -> TestResult:
    """Test 11: Request page beyond last page"""
    try:
        print(f"{Colors.OKBLUE}Testing pagination beyond last page...{Colors.ENDC}")

        # Get total pages
        first_page = filter_attachments(page=1, size=5)
        total_pages = first_page["pages"]

        # Request page way beyond
        result = filter_attachments(page=total_pages + 10, size=5)

        no_results = len(result["items"]) == 0
        correct_structure = "items" in result and isinstance(result["items"], list)

        passed = no_results and correct_structure

        return TestResult(
            name="Pagination beyond last page",
            passed=passed,
            message=f"Requested page {total_pages + 10}, got empty results (total pages: {total_pages})",
            details={"requested_page": total_pages + 10, "total_pages": total_pages}
        )
    except Exception as e:
        return TestResult(
            name="Pagination beyond last page",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_12_content_preview() -> TestResult:
    """Test 12: Verify content preview (200 chars max)"""
    try:
        print(f"{Colors.OKBLUE}Testing content preview truncation...{Colors.ENDC}")

        result = filter_attachments(page=1, size=10)

        if not result["items"]:
            return TestResult(
                name="Content preview truncation",
                passed=False,
                message="No items to test preview"
            )

        # Check that preview content is <= 200 chars
        all_correct_length = all(
            len(item["content"]) <= 200
            for item in result["items"]
        )

        # Check that content_length field exists and is accurate
        has_length_field = all(
            "content_length" in item and item["content_length"] > 0
            for item in result["items"]
        )

        # Find an item with content longer than 200 chars
        long_items = [
            item for item in result["items"]
            if item["content_length"] > 200
        ]

        if long_items:
            # Verify preview is actually truncated
            is_truncated = all(
                len(item["content"]) < item["content_length"]
                for item in long_items
            )
        else:
            is_truncated = True  # No long items to test

        passed = all_correct_length and has_length_field and is_truncated

        return TestResult(
            name="Content preview truncation",
            passed=passed,
            message=f"All previews <= 200 chars, {len(long_items)} items truncated",
            details={
                "sample_preview_length": len(result["items"][0]["content"]),
                "sample_full_length": result["items"][0]["content_length"]
            }
        )
    except Exception as e:
        return TestResult(
            name="Content preview truncation",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_13_invalid_sort_parameters() -> TestResult:
    """Test 13: Invalid sort parameters (should fail gracefully)"""
    try:
        print(f"{Colors.OKBLUE}Testing invalid sort parameters...{Colors.ENDC}")

        # Invalid sort column
        try:
            filter_attachments(sort_column="invalid_column", sort_direction="asc")
            invalid_column_handled = False
        except requests.exceptions.HTTPError as e:
            invalid_column_handled = e.response.status_code == 400

        # Invalid sort direction
        try:
            filter_attachments(sort_column="created_at", sort_direction="invalid")
            invalid_direction_handled = False
        except requests.exceptions.HTTPError as e:
            invalid_direction_handled = e.response.status_code == 400

        passed = invalid_column_handled and invalid_direction_handled

        return TestResult(
            name="Invalid sort parameters",
            passed=passed,
            message="API correctly rejects invalid sort parameters with 400 error",
            details={
                "invalid_column": invalid_column_handled,
                "invalid_direction": invalid_direction_handled
            }
        )
    except Exception as e:
        return TestResult(
            name="Invalid sort parameters",
            passed=False,
            message=f"Unexpected error: {str(e)}"
        )


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all test cases and report results"""
    print_header("Attachment Filter Endpoint Test Suite")

    print(f"{Colors.OKCYAN}Test Configuration:{Colors.ENDC}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  REST API: {REST_API_URL}")
    print()

    # Setup: Create test attachments
    test_attachments = create_test_attachments()

    if not test_attachments:
        print(f"{Colors.FAIL}Failed to create test attachments. Aborting tests.{Colors.ENDC}")
        return 1

    try:
        # Run all tests
        results = [
            test_1_basic_pagination(),
            test_2_different_page_sizes(),
            test_3_search_by_content(),
            test_4_search_by_uuid(),
            test_5_sort_by_created_asc(),
            test_6_sort_by_created_desc(),
            test_7_sort_by_size(),
            test_8_date_range_filter(),
            test_9_combined_filters(),
            test_10_empty_search_results(),
            test_11_pagination_beyond_last_page(),
            test_12_content_preview(),
            test_13_invalid_sort_parameters(),
        ]

        # Print results
        print_header("Test Results")
        for result in results:
            print_test_result(result)

        # Summary
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        total = len(results)

        print_header("Test Summary")
        print(f"  Total Tests: {total}")
        print(f"  {Colors.OKGREEN}Passed: {passed}{Colors.ENDC}")
        print(f"  {Colors.FAIL}Failed: {failed}{Colors.ENDC}")
        print(f"  Success Rate: {passed/total*100:.1f}%")
        print()

        if failed == 0:
            print(f"{Colors.OKGREEN}{Colors.BOLD}✓ ALL TESTS PASSED!{Colors.ENDC}\n")
            return 0
        else:
            print(f"{Colors.FAIL}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.ENDC}\n")
            return 1

    finally:
        # Cleanup
        cleanup_test_attachments()


if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
        exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Tests interrupted by user{Colors.ENDC}\n")
        cleanup_test_attachments()
        exit(130)
    except Exception as e:
        print(f"\n{Colors.FAIL}Test suite failed with error: {e}{Colors.ENDC}\n")
        import traceback
        traceback.print_exc()
        cleanup_test_attachments()
        exit(1)
