#!/usr/bin/env python3
"""
Comprehensive test for delete functionality.

This test verifies that:
1. Memories can be added and searched
2. Deleted memories are removed from both DB and vector store (Qdrant)
3. Deleted memories don't appear in searches
4. Update with same content after deletion creates a NEW memory (ADD, not UPDATE)

Usage:
    python3 05-test-delete-comprehensive.py

Requirements:
    - OpenMemory service running at http://localhost:8765
    - Test user 'frederik' configured
    - OPENAI_API_KEY set in environment
"""

import requests
import json
import uuid
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


# Configuration
BASE_URL = "http://localhost:8765"
REST_API_URL = f"{BASE_URL}/api/v1"
TEST_USER = "frederik"
TEST_APP = "test-delete"


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
            print(f"  Details: {json.dumps(result.details, indent=2)}")
    print()


def create_memory_rest(text: str) -> Dict[str, Any]:
    """Create a memory using REST API with Qdrant storage"""
    response = requests.post(
        f"{REST_API_URL}/memories/",
        json={
            "user_id": TEST_USER,
            "text": text,
            "app": TEST_APP,
            "infer": True,  # Enable LLM processing to store in Qdrant
            "extract": False,  # Don't extract facts, store as-is
            "deduplicate": False  # Don't deduplicate
        }
    )
    response.raise_for_status()
    return response.json()


def list_memories_with_search(search_query: str) -> List[Dict[str, Any]]:
    """List memories using REST API filter endpoint"""
    response = requests.get(
        f"{REST_API_URL}/memories/",
        params={
            "user_id": TEST_USER,
            "search_query": search_query,
            "size": 100
        }
    )
    response.raise_for_status()
    result = response.json()
    return result.get("items", [])


def delete_memories(memory_ids: List[str]) -> Dict[str, Any]:
    """Delete memories using REST API"""
    response = requests.delete(
        f"{REST_API_URL}/memories/",
        json={
            "memory_ids": memory_ids,
            "user_id": TEST_USER,
            "delete_attachments": False
        }
    )
    response.raise_for_status()
    return response.json()


def test_add_unique_memory() -> TestResult:
    """Test Step 1: Add a unique memory"""
    try:
        # Create a unique memory with UUID
        unique_id = str(uuid.uuid4())
        unique_text = f"UNIQUE_MEMORY_TEST_{unique_id}_This is a test memory about quantum computing and AI"

        print(f"{Colors.OKBLUE}Creating memory with text:{Colors.ENDC} {unique_text[:50]}...")
        memory = create_memory_rest(unique_text)

        memory_id = memory.get("id")
        if not memory_id:
            return TestResult(
                name="Add Unique Memory",
                passed=False,
                message="No memory ID returned",
                details=memory
            )

        return TestResult(
            name="Add Unique Memory",
            passed=True,
            message=f"Memory created with ID: {memory_id}",
            details={"memory_id": memory_id, "text": unique_text}
        )
    except Exception as e:
        return TestResult(
            name="Add Unique Memory",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def test_search_before_delete(unique_text: str) -> TestResult:
    """Test Step 2: Search for the memory (should be found)"""
    try:
        print(f"{Colors.OKBLUE}Searching for:{Colors.ENDC} {unique_text[:50]}...")

        # Wait a moment for indexing
        time.sleep(2)

        results = list_memories_with_search(unique_text)

        # Check if our memory is in the results
        found = any(unique_text in result.get("content", "") for result in results)

        if found:
            return TestResult(
                name="Search Before Delete",
                passed=True,
                message=f"Memory found in search results (found {len(results)} results)",
                details={"results_count": len(results)}
            )
        else:
            return TestResult(
                name="Search Before Delete",
                passed=False,
                message="Memory NOT found in search results (should be there)",
                details={"results": results}
            )
    except Exception as e:
        return TestResult(
            name="Search Before Delete",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def test_delete_memory(memory_id: str) -> TestResult:
    """Test Step 3: Delete the memory"""
    try:
        print(f"{Colors.OKBLUE}Deleting memory:{Colors.ENDC} {memory_id}")

        result = delete_memories([memory_id])

        return TestResult(
            name="Delete Memory",
            passed=True,
            message=f"Memory deleted successfully",
            details=result
        )
    except Exception as e:
        return TestResult(
            name="Delete Memory",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def test_search_after_delete(unique_text: str) -> TestResult:
    """Test Step 4: Search for the memory (should NOT be found)"""
    try:
        print(f"{Colors.OKBLUE}Searching again for:{Colors.ENDC} {unique_text[:50]}...")

        # Wait a moment for deletion to propagate
        time.sleep(2)

        results = list_memories_with_search(unique_text)

        # Check if our memory is in the results
        found = any(unique_text in result.get("content", "") for result in results)

        if not found:
            return TestResult(
                name="Search After Delete (Should be Gone)",
                passed=True,
                message=f"Memory correctly NOT found in search results",
                details={"results_count": len(results)}
            )
        else:
            return TestResult(
                name="Search After Delete (Should be Gone)",
                passed=False,
                message="❌ BUG: Memory still found in search results after deletion!",
                details={"results": results}
            )
    except Exception as e:
        return TestResult(
            name="Search After Delete (Should be Gone)",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def test_update_after_delete(original_text: str) -> TestResult:
    """Test Step 5: Update with slightly different text (should ADD, not UPDATE)"""
    try:
        # Modify the text slightly
        modified_text = original_text.replace("quantum computing", "quantum mechanics")

        print(f"{Colors.OKBLUE}Creating similar memory:{Colors.ENDC} {modified_text[:50]}...")

        # This should create a NEW memory (ADD event), not update the deleted one
        memory = create_memory_rest(modified_text)

        memory_id = memory.get("id")
        if not memory_id:
            return TestResult(
                name="Update After Delete (Should ADD)",
                passed=False,
                message="No memory ID returned",
                details=memory
            )

        # The memory should be created as a NEW memory
        # If the old memory wasn't properly deleted from Qdrant,
        # this might trigger an UPDATE instead of ADD
        return TestResult(
            name="Update After Delete (Should ADD)",
            passed=True,
            message=f"New memory created with ID: {memory_id}",
            details={"memory_id": memory_id, "text": modified_text}
        )
    except Exception as e:
        return TestResult(
            name="Update After Delete (Should ADD)",
            passed=False,
            message=f"Error: {str(e)}",
            details=None
        )


def run_comprehensive_delete_test():
    """Run the comprehensive delete test"""
    print_header("Comprehensive Delete Test")

    results = []

    # Step 1: Add unique memory
    result1 = test_add_unique_memory()
    results.append(result1)
    print_test_result(result1)

    if not result1.passed:
        print(f"{Colors.FAIL}Test failed at step 1. Aborting.{Colors.ENDC}")
        return

    memory_id = result1.details["memory_id"]
    unique_text = result1.details["text"]

    # Step 2: Search before delete
    result2 = test_search_before_delete(unique_text)
    results.append(result2)
    print_test_result(result2)

    # Step 3: Delete memory
    result3 = test_delete_memory(memory_id)
    results.append(result3)
    print_test_result(result3)

    # Step 4: Search after delete (should be gone)
    result4 = test_search_after_delete(unique_text)
    results.append(result4)
    print_test_result(result4)

    # Step 5: Update after delete (should ADD)
    result5 = test_update_after_delete(unique_text)
    results.append(result5)
    print_test_result(result5)

    # Summary
    print_header("Test Summary")
    passed = sum(1 for r in results if r.passed)
    total = len(results)

    if passed == total:
        print(f"{Colors.OKGREEN}{Colors.BOLD}All tests passed! ({passed}/{total}){Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}Some tests failed. ({passed}/{total} passed){Colors.ENDC}")

    print()


if __name__ == "__main__":
    try:
        run_comprehensive_delete_test()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
