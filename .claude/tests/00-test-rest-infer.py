#!/usr/bin/env python3
"""
Simple REST API infer parameter test.
Prints API responses for visual verification.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8765/api/v1"
TEST_USER = "frederik"

def cleanup():
    """Delete all test memories"""
    print("=== CLEANUP ===")
    try:
        response = requests.delete(
            f"{BASE_URL}/memories/",
            json={"memory_ids": [], "user_id": TEST_USER}
        )
        print(f"Status: {response.status_code}")
    except Exception as e:
        print(f"Warning: {e}")
    print()

def add_memory(text, infer):
    """Add memory with specified infer mode"""
    response = requests.post(
        f"{BASE_URL}/memories/",
        json={
            "user_id": TEST_USER,
            "text": text,
            "infer": infer
        }
    )
    return response

def search_memories(query):
    """Search memories"""
    response = requests.get(
        f"{BASE_URL}/memories/",
        params={
            "user_id": TEST_USER,
            "search_query": query,
            "size": 10
        }
    )
    return response

print("=" * 80)
print("REST API INFER PARAMETER TEST")
print("=" * 80)
print()

cleanup()
time.sleep(2)

# Test 1: infer=False (raw storage)
print("=" * 80)
print("TEST 1: infer=False (Raw Verbatim Storage)")
print("=" * 80)
text_false = "Freddy and I like hiking in the blabla stuff ok mountains."
print(f"Input: {text_false}")
print()

print("Adding memory...")
response = add_memory(text_false, infer=False)
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
print()

time.sleep(3)

print("Searching...")
response = search_memories("Freddy")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Found {len(result.get('items', []))} memories:")
    for item in result.get('items', []):
        print(f"  - {item.get('content')}")
else:
    print(f"Error: {response.text}")
print()

# Test 2: infer=True (LLM extraction)
print("=" * 80)
print("TEST 2: infer=True (LLM Semantic Extraction)")
print("=" * 80)
text_true = "Lenovo supports linux quite well, that is cool. However, docker is somtimes not as nice as podman but is more popular"
print(f"Input: {text_true}")
print()

print("Adding memory...")
response = add_memory(text_true, infer=True)
print(f"Status: {response.status_code}")
response_json = response.json() if response.status_code == 200 else response.text
print(f"Response: {json.dumps(response_json, indent=2) if isinstance(response_json, (dict, list)) else response_json}")
print()

time.sleep(3)

print("Searching...")
response = search_memories("Lenovo")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Found {len(result.get('items', []))} memories:")
    for item in result.get('items', []):
        print(f"  - {item.get('content')}")
else:
    print(f"Error: {response.text}")
print()

print("=" * 80)
print("TEST COMPLETE - REVIEW OUTPUT ABOVE")
print("=" * 80)
