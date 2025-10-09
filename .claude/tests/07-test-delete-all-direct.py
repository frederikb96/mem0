#!/usr/bin/env python3
"""
Direct test of delete_all functionality using mem0 client.

This bypasses HTTP/MCP and directly tests the mem0 delete_all() method
that is used by both REST API and MCP endpoints.

Usage:
    python3 07-test-delete-all-direct.py

Requirements:
    - OpenMemory service running at http://localhost:8765 (Qdrant at port 6333)
    - OPENAI_API_KEY set in environment
"""

import uuid
import time
import os


# Configuration
TEST_USER = "frederik"


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a colored header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")


def run_test():
    """Run direct mem0 delete_all test"""
    print_header("Direct mem0 delete_all() Test")

    # Import mem0
    import sys
    sys.path.insert(0, '/usr/local/lib/python3.11/site-packages')
    from mem0 import Memory

    # Create mem0 client
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": "localhost",
                "port": 6333,
            }
        }
    }

    print(f"{Colors.OKGREEN}→{Colors.ENDC} Creating mem0 client...")
    client = Memory.from_config(config)

    # Step 1: Add two memories
    unique_id1 = str(uuid.uuid4())
    unique_id2 = str(uuid.uuid4())

    text1 = f"DELETE_ALL_TEST_1_{unique_id1}_About Python programming"
    text2 = f"DELETE_ALL_TEST_2_{unique_id2}_About JavaScript development"

    print(f"{Colors.OKGREEN}→{Colors.ENDC} Adding memory 1: {text1[:60]}...")
    result1 = client.add(text1, user_id=TEST_USER)
    print(f"  Added: {result1}")

    print(f"{Colors.OKGREEN}→{Colors.ENDC} Adding memory 2: {text2[:60]}...")
    result2 = client.add(text2, user_id=TEST_USER)
    print(f"  Added: {result2}")

    # Step 2: Search to verify they exist
    print(f"\n{Colors.OKGREEN}→{Colors.ENDC} Searching for memories...")
    time.sleep(2)  # Wait for indexing

    search_results = client.search(text1, user_id=TEST_USER, limit=10)
    found_before = any(text1 in str(r) for r in search_results)

    print(f"  Memory 1 found before delete: {found_before}")

    # Step 3: Delete all memories for this user
    print(f"\n{Colors.OKGREEN}→{Colors.ENDC} Calling delete_all() for user {TEST_USER}...")
    delete_result = client.delete_all(user_id=TEST_USER)
    print(f"  Result: {delete_result}")

    # Step 4: Search again to verify they're gone
    print(f"\n{Colors.OKGREEN}→{Colors.ENDC} Searching again after delete_all...")
    time.sleep(2)  # Wait for deletion to propagate

    search_results_after = client.search(text1, user_id=TEST_USER, limit=10)
    found_after = any(text1 in str(r) for r in search_results_after)

    print(f"  Memory 1 found after delete: {found_after}")

    # Summary
    print_header("Test Summary")

    if found_before and not found_after:
        print(f"{Colors.OKGREEN}{Colors.BOLD}✓ TEST PASSED{Colors.ENDC}")
        print(f"  - Memories existed before delete_all: ✓")
        print(f"  - Memories gone after delete_all: ✓")
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}✗ TEST FAILED{Colors.ENDC}")
        print(f"  - Memories existed before delete_all: {'✓' if found_before else '✗'}")
        print(f"  - Memories gone after delete_all: {'✓' if not found_after else '✗ (BUG: still found!)'}")

    print()


if __name__ == "__main__":
    try:
        run_test()
    except KeyboardInterrupt:
        print(f"\n{Colors.FAIL}Test interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
