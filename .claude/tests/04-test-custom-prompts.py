#!/usr/bin/env python3
"""
Test script to validate custom extraction and deduplication prompts.

Tests three scenarios:
1. Technical issue memory (no extract, with dedup, agent_id="general")
2. Personal memory about bicycle tour (no extract, with dedup, agent_id="personal")
3. Full conversation extraction (with extraction enabled)

For each test, outputs detailed LLM decisions and events.

Usage:
    python3 04-test-custom-prompts.py

Requirements:
    - OpenMemory service running at http://localhost:8765
    - Test user 'frederik' configured
    - OPENAI_API_KEY set in environment
    - Custom prompts configured in Settings UI
"""

import requests
import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Configuration
BASE_URL = "http://localhost:8765"
REST_API_URL = f"{BASE_URL}/api/v1"
TEST_USER = "frederik"


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


def print_subheader(text: str):
    """Print a colored subheader"""
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}{'-'*80}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{Colors.BOLD}{'-'*80}{Colors.ENDC}\n")


def print_detail(label: str, value: Any, indent: int = 2):
    """Print a labeled detail"""
    spaces = " " * indent
    if isinstance(value, (dict, list)):
        print(f"{spaces}{Colors.BOLD}{label}:{Colors.ENDC}")
        print(f"{spaces}{json.dumps(value, indent=2)}")
    else:
        print(f"{spaces}{Colors.BOLD}{label}:{Colors.ENDC} {value}")


def create_memory_rest(
    text: str,
    infer: Optional[bool] = None,
    extract: Optional[bool] = None,
    deduplicate: Optional[bool] = None,
    agent_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a memory via REST API"""
    payload = {
        "user_id": TEST_USER,
        "text": text,
        "app": agent_id or "test-custom-prompts",
        "metadata": metadata or {}
    }

    if infer is not None:
        payload["infer"] = infer
    if extract is not None:
        payload["extract"] = extract
    if deduplicate is not None:
        payload["deduplicate"] = deduplicate

    response = requests.post(f"{REST_API_URL}/memories/", json=payload)
    response.raise_for_status()
    return response.json()


def analyze_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze and extract key information from response"""
    analysis = {
        "event": response.get("event", "ADD"),
        "has_id": "id" in response,
        "has_content": "content" in response or "text" in response,
        "content": response.get("content") or response.get("text", ""),
        "metadata": response.get("metadata_", {}),
        "response_type": "Memory Object" if "id" in response else "Event Response"
    }

    return analysis


def print_response_analysis(response: Dict[str, Any], analysis: Dict[str, Any]):
    """Print detailed analysis of response"""
    print_detail("Event Type", analysis["event"])
    print_detail("Response Type", analysis["response_type"])

    if analysis["has_id"]:
        print_detail("Memory ID", response.get("id"))

    if analysis["has_content"]:
        print_detail("Content", analysis["content"])

    if analysis["metadata"]:
        print_detail("Metadata", analysis["metadata"])

    # Print additional response fields
    interesting_fields = ["old_memory", "new_memory", "message"]
    for field in interesting_fields:
        if field in response:
            print_detail(field.replace("_", " ").title(), response[field])


# ============================================================================
# TEST SCENARIOS
# ============================================================================

def test_scenario_1_technical_issue():
    """
    Test Scenario 1: Technical Issue Memory
    - No extraction (extract=False)
    - With deduplication (deduplicate=True)
    - agent_id="general"
    """
    print_header("Test Scenario 1: Technical Issue Memory")

    print(f"{Colors.OKCYAN}Configuration:{Colors.ENDC}")
    print_detail("Extract", False)
    print_detail("Deduplicate", True)
    print_detail("Agent ID", "general")
    print()

    # Test memory
    text = """
    User experienced a mutter crash on Ubuntu laptop, but it seems to have resolved itself
    """

    print(f"{Colors.OKCYAN}Input Text:{Colors.ENDC}")
    print(f"  {text.strip()}")
    print()

    # Create memory
    print(f"{Colors.OKCYAN}Creating memory...{Colors.ENDC}")
    response = create_memory_rest(
        text=text,
        infer=True,
        extract=False,
        deduplicate=True,
        agent_id="general"
    )

    print()
    print_subheader("Response Analysis")
    analysis = analyze_response(response)
    print_response_analysis(response, analysis)

    # Interpretation
    print()
    print_subheader("Interpretation")
    if analysis["event"] == "ADD":
        print(f"  {Colors.OKGREEN}✓{Colors.ENDC} New memory created (no duplicates found)")
        print(f"  → Raw text was embedded without extraction")
        print(f"  → Deduplication checked existing memories")
    elif analysis["event"] == "UPDATE":
        print(f"  {Colors.OKBLUE}↻{Colors.ENDC} Memory updated (duplicate found)")
        print(f"  → Custom update prompt was used for deduplication")
    elif analysis["event"] == "NONE":
        print(f"  {Colors.WARNING}○{Colors.ENDC} No action taken (exact duplicate)")
        print(f"  → Memory already exists with same content")

    return response


def test_scenario_2_personal_memory():
    """
    Test Scenario 2: Personal Memory
    - No extraction (extract=False)
    - With deduplication (deduplicate=True)
    - agent_id="personal"
    """
    print_header("Test Scenario 2: Personal Memory")

    print(f"{Colors.OKCYAN}Configuration:{Colors.ENDC}")
    print_detail("Extract", False)
    print_detail("Deduplicate", True)
    print_detail("Agent ID", "personal")
    print()

    # Test memory
    text = """
    User went on a bicycle tour in September 2025 - great experience with nice weather.
    """

    print(f"{Colors.OKCYAN}Input Text:{Colors.ENDC}")
    print(f"  {text.strip()}")
    print()

    # Create memory
    print(f"{Colors.OKCYAN}Creating memory...{Colors.ENDC}")
    response = create_memory_rest(
        text=text,
        infer=True,
        extract=False,
        deduplicate=True,
        agent_id="personal"
    )

    print()
    print_subheader("Response Analysis")
    analysis = analyze_response(response)
    print_response_analysis(response, analysis)

    # Interpretation
    print()
    print_subheader("Interpretation")
    if analysis["event"] == "ADD":
        print(f"  {Colors.OKGREEN}✓{Colors.ENDC} New personal memory created")
        print(f"  → Raw text was embedded without extraction")
        print(f"  → Deduplication checked existing personal memories")
    elif analysis["event"] == "UPDATE":
        print(f"  {Colors.OKBLUE}↻{Colors.ENDC} Personal memory updated")
        print(f"  → Custom update prompt merged with existing memory")
    elif analysis["event"] == "NONE":
        print(f"  {Colors.WARNING}○{Colors.ENDC} No action taken")
        print(f"  → Similar personal memory already exists")

    return response


def test_scenario_3_conversation_extraction():
    """
    Test Scenario 3: Full Conversation Extraction
    - With extraction (extract=True)
    - With deduplication (deduplicate=True)
    - Contains both technical and personal topics
    """
    print_header("Test Scenario 3: Full Conversation Extraction")

    print(f"{Colors.OKCYAN}Configuration:{Colors.ENDC}")
    print_detail("Extract", True)
    print_detail("Deduplicate", True)
    print_detail("Agent ID", "test-custom-prompts")
    print()

    # Test memory - conversation containing both topics
    text = """
    User: Yesterday I went on a bicycle tour and had a great time.
    But when I came back home and started my laptop, GNOME shell logged an error.

    System: What error did you see?

    User: In journalctl I saw: mutter-x11-frames crashed with SIGSEGV in g_hash_table_lookup()
    It happened right after boot. I think it might be related to the recent system update.

    System: That's a known issue with mutter on some systems. You should check if there's
    a pending update or file a bug report.

    User: Thanks! By the way, the bicycle tour was nice. The weather was perfect.
    """

    print(f"{Colors.OKCYAN}Input Text:{Colors.ENDC}")
    print(f"  {text.strip()[:200]}...")
    print()

    # Create memory with extraction
    print(f"{Colors.OKCYAN}Creating memory with extraction enabled...{Colors.ENDC}")
    print(f"  → Custom extraction prompt will extract facts from conversation")
    print(f"  → Custom deduplication prompt will check for existing similar facts")
    print()

    response = create_memory_rest(
        text=text,
        infer=True,
        extract=True,
        deduplicate=True,
        agent_id="test-custom-prompts"
    )

    print()
    print_subheader("Response Analysis")
    analysis = analyze_response(response)
    print_response_analysis(response, analysis)

    # Interpretation
    print()
    print_subheader("Interpretation")
    print(f"  {Colors.BOLD}Extraction Phase:{Colors.ENDC}")
    if analysis["has_content"]:
        print(f"  {Colors.OKGREEN}✓{Colors.ENDC} Custom extraction prompt extracted facts")
        print(f"  → Check content to see what facts were extracted")
        print(f"  → Should contain both technical (mutter crash) and personal (bicycle) facts")
    else:
        print(f"  {Colors.WARNING}○{Colors.ENDC} No facts extracted or empty result")

    print()
    print(f"  {Colors.BOLD}Deduplication Phase:{Colors.ENDC}")
    if analysis["event"] == "ADD":
        print(f"  {Colors.OKGREEN}✓{Colors.ENDC} New facts added to memory")
        print(f"  → No similar existing facts found")
    elif analysis["event"] == "UPDATE":
        print(f"  {Colors.OKBLUE}↻{Colors.ENDC} Existing memory updated")
        print(f"  → Custom update prompt merged facts")
        print(f"  → Check old_memory and new_memory fields for comparison")
    elif analysis["event"] == "NONE":
        print(f"  {Colors.WARNING}○{Colors.ENDC} No changes made")
        print(f"  → Facts already exist in memory")

    return response


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all test scenarios"""
    print_header("Custom Prompts Validation Test Suite")

    print(f"{Colors.OKCYAN}Test Configuration:{Colors.ENDC}")
    print(f"  Base URL: {BASE_URL}")
    print(f"  REST API: {REST_API_URL}")
    print(f"  Test User: {TEST_USER}")
    print()

    print(f"{Colors.WARNING}Note: This test validates your custom extraction and deduplication prompts.{Colors.ENDC}")
    print(f"{Colors.WARNING}Make sure you have configured custom prompts in Settings UI.{Colors.ENDC}")
    print()

    # Run test scenarios
    results = []

    try:
        # Scenario 1: Technical issue
        response1 = test_scenario_1_technical_issue()
        results.append(("Technical Issue Memory", response1))
        time.sleep(2)  # Delay between tests

        # Scenario 2: Personal memory
        response2 = test_scenario_2_personal_memory()
        results.append(("Personal Memory", response2))
        time.sleep(2)

        # Scenario 3: Conversation extraction
        response3 = test_scenario_3_conversation_extraction()
        results.append(("Conversation Extraction", response3))

    except Exception as e:
        print(f"\n{Colors.FAIL}Error during test execution: {e}{Colors.ENDC}\n")
        import traceback
        traceback.print_exc()
        return 1

    # Summary
    print_header("Test Summary")

    print(f"{Colors.BOLD}Results:{Colors.ENDC}\n")
    for i, (name, response) in enumerate(results, 1):
        analysis = analyze_response(response)
        event_color = {
            "ADD": Colors.OKGREEN,
            "UPDATE": Colors.OKBLUE,
            "NONE": Colors.WARNING,
            "DELETE": Colors.FAIL
        }.get(analysis["event"], Colors.ENDC)

        print(f"  {i}. {name}")
        print(f"     Event: {event_color}{analysis['event']}{Colors.ENDC}")
        print()

    print(f"{Colors.OKGREEN}{Colors.BOLD}✓ All tests completed successfully!{Colors.ENDC}")
    print()
    print(f"{Colors.OKCYAN}Review the detailed outputs above to verify:{Colors.ENDC}")
    print(f"  • Extraction prompt correctly extracts facts from text")
    print(f"  • Deduplication prompt properly merges similar memories")
    print(f"  • Raw text embedding works when extraction is disabled")
    print(f"  • agent_id is correctly set for different memory types")
    print()

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Tests interrupted by user{Colors.ENDC}\n")
        exit(130)
    except Exception as e:
        print(f"\n{Colors.FAIL}Test suite failed with error: {e}{Colors.ENDC}\n")
        import traceback
        traceback.print_exc()
        exit(1)
