#!/usr/bin/env python3
"""
Frontend Integration Test Script

This test verifies the attachment list view UI by testing:
1. API endpoints used by the UI (filter, pagination, search)
2. Data flow (create → list → filter → delete)
3. Edge cases (empty lists, pagination, search)

Since we can't test the actual React components programmatically,
this script tests the complete API integration that the UI relies on.

Usage:
    python3 10-test-ui-integration.py

Requirements:
    - OpenMemory API running at http://localhost:8765
"""

import requests
import json
import time
from typing import Dict, List, Any
from dataclasses import dataclass


# Configuration
BASE_URL = "http://localhost:8765"
REST_API_URL = f"{BASE_URL}/api/v1"


@dataclass
class TestResult:
    """Result of a single test case"""
    name: str
    passed: bool
    message: str
    details: Any = None


class Colors:
    """ANSI color codes"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print colored header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")


def print_test_result(result: TestResult):
    """Print test result"""
    status = f"{Colors.OKGREEN}✓ PASS{Colors.ENDC}" if result.passed else f"{Colors.FAIL}✗ FAIL{Colors.ENDC}"
    print(f"{status} {result.name}")
    print(f"  → {result.message}")
    if result.details and not result.passed:
        print(f"  Details: {json.dumps(result.details, indent=2)[:300]}...")
    print()


# Test data
CREATED_ATTACHMENTS = []


def cleanup():
    """Clean up test attachments"""
    global CREATED_ATTACHMENTS
    if not CREATED_ATTACHMENTS:
        return

    print(f"\n{Colors.OKBLUE}Cleaning up {len(CREATED_ATTACHMENTS)} test attachments...{Colors.ENDC}")
    for attachment_id in CREATED_ATTACHMENTS:
        try:
            requests.delete(f"{REST_API_URL}/attachments/{attachment_id}")
        except:
            pass
    CREATED_ATTACHMENTS = []


# ============================================================================
# TEST CASES
# ============================================================================

def test_1_create_attachments_for_ui() -> TestResult:
    """Test 1: Create sample attachments for UI testing"""
    global CREATED_ATTACHMENTS

    try:
        print(f"{Colors.OKBLUE}Creating sample attachments...{Colors.ENDC}")

        attachments = [
            "First attachment for UI testing with some content",
            "Second attachment with different text to test search",
            "Third attachment to test pagination",
            "Fourth attachment with more content",
            "Fifth attachment for complete testing",
        ]

        for content in attachments:
            response = requests.post(
                f"{REST_API_URL}/attachments",
                json={"content": content}
            )
            response.raise_for_status()
            CREATED_ATTACHMENTS.append(response.json()["id"])
            time.sleep(0.1)

        return TestResult(
            name="Create sample attachments",
            passed=len(CREATED_ATTACHMENTS) == 5,
            message=f"Created {len(CREATED_ATTACHMENTS)} attachments"
        )
    except Exception as e:
        return TestResult(
            name="Create sample attachments",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_2_list_view_default() -> TestResult:
    """Test 2: Test default list view (page 1, size 10)"""
    try:
        response = requests.post(
            f"{REST_API_URL}/attachments/filter",
            json={"page": 1, "size": 10}
        )
        response.raise_for_status()
        data = response.json()

        has_items = len(data["items"]) >= 5
        has_pagination = "total" in data and "pages" in data
        correct_format = all("id" in item and "content" in item for item in data["items"])

        passed = has_items and has_pagination and correct_format

        return TestResult(
            name="Default list view",
            passed=passed,
            message=f"Retrieved {len(data['items'])} items, total={data['total']}",
            details={"first_item": data["items"][0] if data["items"] else None}
        )
    except Exception as e:
        return TestResult(
            name="Default list view",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_3_search_functionality() -> TestResult:
    """Test 3: Test search functionality (used by search bar)"""
    try:
        # Search for "First"
        response = requests.post(
            f"{REST_API_URL}/attachments/filter",
            json={"page": 1, "size": 10, "search_query": "First"}
        )
        response.raise_for_status()
        data = response.json()

        found_first = any("First" in item["content"] for item in data["items"])
        only_matching = all("First" in item["content"] or "First" in item["id"] for item in data["items"])

        passed = found_first and (len(data["items"]) <= 5)

        return TestResult(
            name="Search functionality",
            passed=passed,
            message=f"Found {len(data['items'])} items matching 'First'",
            details={"matches": [item["id"][:8] for item in data["items"]]}
        )
    except Exception as e:
        return TestResult(
            name="Search functionality",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_4_pagination_page_2() -> TestResult:
    """Test 4: Test pagination (page 2 with size 3)"""
    try:
        response = requests.post(
            f"{REST_API_URL}/attachments/filter",
            json={"page": 2, "size": 3}
        )
        response.raise_for_status()
        data = response.json()

        correct_page = data["page"] == 2
        correct_size = len(data["items"]) <= 3
        has_pagination_info = data["total"] >= 5

        passed = correct_page and correct_size and has_pagination_info

        return TestResult(
            name="Pagination (page 2)",
            passed=passed,
            message=f"Page {data['page']}, showing {len(data['items'])} items of {data['total']} total"
        )
    except Exception as e:
        return TestResult(
            name="Pagination (page 2)",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_5_page_size_selector() -> TestResult:
    """Test 5: Test different page sizes (like UI selector)"""
    try:
        sizes = [5, 10, 25]
        results = {}

        for size in sizes:
            response = requests.post(
                f"{REST_API_URL}/attachments/filter",
                json={"page": 1, "size": size}
            )
            response.raise_for_status()
            data = response.json()
            results[size] = len(data["items"])

        all_correct = all(results[size] <= size for size in sizes)

        return TestResult(
            name="Page size selector",
            passed=all_correct,
            message=f"Tested page sizes: {sizes}",
            details=results
        )
    except Exception as e:
        return TestResult(
            name="Page size selector",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_6_empty_search() -> TestResult:
    """Test 6: Test empty search results (no matches)"""
    try:
        response = requests.post(
            f"{REST_API_URL}/attachments/filter",
            json={"page": 1, "size": 10, "search_query": "NONEXISTENT_SEARCH_TERM"}
        )
        response.raise_for_status()
        data = response.json()

        no_results = len(data["items"]) == 0
        correct_total = data["total"] == 0
        correct_structure = "items" in data and isinstance(data["items"], list)

        passed = no_results and correct_total and correct_structure

        return TestResult(
            name="Empty search results",
            passed=passed,
            message="Correctly handles empty search results"
        )
    except Exception as e:
        return TestResult(
            name="Empty search results",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_7_content_preview() -> TestResult:
    """Test 7: Verify content preview (200 chars max)"""
    try:
        response = requests.post(
            f"{REST_API_URL}/attachments/filter",
            json={"page": 1, "size": 10}
        )
        response.raise_for_status()
        data = response.json()

        if not data["items"]:
            return TestResult(
                name="Content preview",
                passed=False,
                message="No items to test"
            )

        all_short_previews = all(len(item["content"]) <= 200 for item in data["items"])
        has_length_field = all("content_length" in item for item in data["items"])

        passed = all_short_previews and has_length_field

        return TestResult(
            name="Content preview",
            passed=passed,
            message="All content previews <= 200 chars with length field"
        )
    except Exception as e:
        return TestResult(
            name="Content preview",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_8_delete_functionality() -> TestResult:
    """Test 8: Test delete functionality (used by delete button)"""
    global CREATED_ATTACHMENTS

    try:
        if not CREATED_ATTACHMENTS:
            return TestResult(
                name="Delete functionality",
                passed=False,
                message="No attachments to delete"
            )

        # Delete first attachment
        attachment_to_delete = CREATED_ATTACHMENTS[0]

        response = requests.delete(f"{REST_API_URL}/attachments/{attachment_to_delete}")
        success = response.status_code == 204

        # Verify it's deleted
        list_response = requests.post(
            f"{REST_API_URL}/attachments/filter",
            json={"page": 1, "size": 100, "search_query": attachment_to_delete[:8]}
        )
        list_response.raise_for_status()
        data = list_response.json()

        not_in_list = not any(item["id"] == attachment_to_delete for item in data["items"])

        passed = success and not_in_list

        # Remove from tracking
        if passed:
            CREATED_ATTACHMENTS.remove(attachment_to_delete)

        return TestResult(
            name="Delete functionality",
            passed=passed,
            message=f"Deleted attachment and verified removal"
        )
    except Exception as e:
        return TestResult(
            name="Delete functionality",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_9_sort_by_created_desc() -> TestResult:
    """Test 9: Test sort by created_at descending (newest first - default)"""
    try:
        response = requests.post(
            f"{REST_API_URL}/attachments/filter",
            json={
                "page": 1,
                "size": 5,
                "sort_column": "created_at",
                "sort_direction": "desc"
            }
        )
        response.raise_for_status()
        data = response.json()

        dates = [item["created_at"] for item in data["items"]]
        is_sorted = dates == sorted(dates, reverse=True)

        return TestResult(
            name="Sort by created_at (desc)",
            passed=is_sorted,
            message=f"Retrieved {len(data['items'])} items in correct order"
        )
    except Exception as e:
        return TestResult(
            name="Sort by created_at (desc)",
            passed=False,
            message=f"Error: {str(e)}"
        )


def test_10_ui_data_flow() -> TestResult:
    """Test 10: Complete UI data flow (create → list → search → delete)"""
    try:
        # Create
        response = requests.post(
            f"{REST_API_URL}/attachments",
            json={"content": "TEST_FLOW_ATTACHMENT for data flow testing"}
        )
        response.raise_for_status()
        new_id = response.json()["id"]
        CREATED_ATTACHMENTS.append(new_id)

        # List
        time.sleep(0.5)
        list_response = requests.post(
            f"{REST_API_URL}/attachments/filter",
            json={"page": 1, "size": 100}
        )
        list_response.raise_for_status()
        in_list = any(item["id"] == new_id for item in list_response.json()["items"])

        # Search
        search_response = requests.post(
            f"{REST_API_URL}/attachments/filter",
            json={"page": 1, "size": 10, "search_query": "TEST_FLOW"}
        )
        search_response.raise_for_status()
        in_search = any(item["id"] == new_id for item in search_response.json()["items"])

        # Delete
        delete_response = requests.delete(f"{REST_API_URL}/attachments/{new_id}")
        deleted = delete_response.status_code == 204

        # Verify deletion
        time.sleep(0.5)
        verify_response = requests.post(
            f"{REST_API_URL}/attachments/filter",
            json={"page": 1, "size": 100}
        )
        verify_response.raise_for_status()
        not_in_list_after = not any(item["id"] == new_id for item in verify_response.json()["items"])

        passed = in_list and in_search and deleted and not_in_list_after

        if passed:
            CREATED_ATTACHMENTS.remove(new_id)

        return TestResult(
            name="Complete UI data flow",
            passed=passed,
            message="Create → List → Search → Delete flow works correctly",
            details={
                "in_list": in_list,
                "in_search": in_search,
                "deleted": deleted,
                "verified_gone": not_in_list_after
            }
        )
    except Exception as e:
        return TestResult(
            name="Complete UI data flow",
            passed=False,
            message=f"Error: {str(e)}"
        )


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all tests"""
    print_header("Frontend Integration Test Suite")

    print(f"{Colors.OKBLUE}Testing API endpoints used by the UI{Colors.ENDC}")
    print(f"Base URL: {BASE_URL}\n")

    try:
        results = [
            test_1_create_attachments_for_ui(),
            test_2_list_view_default(),
            test_3_search_functionality(),
            test_4_pagination_page_2(),
            test_5_page_size_selector(),
            test_6_empty_search(),
            test_7_content_preview(),
            test_8_delete_functionality(),
            test_9_sort_by_created_desc(),
            test_10_ui_data_flow(),
        ]

        print_header("Test Results")
        for result in results:
            print_test_result(result)

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
            print(f"{Colors.OKGREEN}{Colors.BOLD}✓ ALL INTEGRATION TESTS PASSED!{Colors.ENDC}\n")
            print(f"{Colors.OKBLUE}The UI should now be working correctly. Test it in your browser at:{Colors.ENDC}")
            print(f"{Colors.BOLD}  http://localhost:3000/attachments{Colors.ENDC}\n")
            return 0
        else:
            print(f"{Colors.FAIL}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.ENDC}\n")
            return 1

    finally:
        cleanup()


if __name__ == "__main__":
    try:
        exit(run_all_tests())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Tests interrupted{Colors.ENDC}\n")
        cleanup()
        exit(130)
    except Exception as e:
        print(f"\n{Colors.FAIL}Test suite failed: {e}{Colors.ENDC}\n")
        import traceback
        traceback.print_exc()
        cleanup()
        exit(1)
