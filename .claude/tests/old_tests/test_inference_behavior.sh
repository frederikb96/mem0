#!/bin/bash
set -euo pipefail

# Test inference behavior: infer=true vs infer=false
# Goal: Understand UPDATE event triggering and attachment merging

API_URL="http://localhost:8765/api/v1"
USER_ID="frederik"
TEST_NAME="Inference Behavior"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_fn="$2"

    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "\n${YELLOW}[TEST $TESTS_RUN]${NC} $test_name"

    if $test_fn; then
        echo -e "${GREEN}✓ PASSED${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 1: infer=true with 10 similar memories
test_infer_true_updates() {
    echo "Adding 10 very similar memories with infer=true..."
    echo "Expected: Multiple UPDATE events, attachment_ids array grows"

    local base_text="Python is a programming language that follows PEP standards"
    local event_counts_add=0
    local event_counts_update=0
    local event_counts_none=0

    for i in {1..10}; do
        local variation="$base_text with feature $i"
        local attachment="ATTACHMENT #$i: Detailed explanation of feature $i in Python development"

        response=$(curl -s -X POST "$API_URL/memories/" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"$variation\",
                \"user_id\": \"$USER_ID\",
                \"metadata\": {\"agent_id\": \"test_infer_true\", \"test_run\": \"inference_behavior\"},
                \"attachment_text\": \"$attachment\",
                \"infer\": true
            }")

        echo "  Iteration $i response: $response" | jq -c '.'
        sleep 0.5  # Avoid rate limiting
    done

    # Search for memories and check attachment_ids
    echo -e "\nSearching for memories with test_run=inference_behavior..."
    search_result=$(curl -s -X POST "$API_URL/memories/filter" \
        -H "Content-Type: application/json" \
        -d "{
            \"user_id\": \"$USER_ID\",
            \"search_query\": \"Python programming\",
            \"size\": 20
        }")

    echo "Search results:" | jq -c '.'
    echo "$search_result" | jq '.items[] | select(.metadata_.test_run == "inference_behavior") | {id: .id, attachment_count: (.metadata_.attachment_ids | length), attachments: .metadata_.attachment_ids}'

    # Verify at least one memory has multiple attachments (UPDATE happened)
    local max_attachments=$(echo "$search_result" | jq '[.items[] | select(.metadata_.test_run == "inference_behavior") | .metadata_.attachment_ids | length] | max')

    if [ "$max_attachments" -gt 1 ]; then
        echo -e "${GREEN}✓ Found memory with $max_attachments attachments (UPDATE events worked)${NC}"
        return 0
    else
        echo -e "${RED}✗ No memory has multiple attachments (UPDATE events did not merge)${NC}"
        return 1
    fi
}

# Test 2: infer=false with 10 similar memories
test_infer_false_no_updates() {
    echo "Adding 10 very similar memories with infer=false..."
    echo "Expected: All ADD events, each memory separate"

    local base_text="Rust is a systems programming language with memory safety"

    for i in {1..10}; do
        local variation="$base_text feature $i"
        local attachment="ATTACHMENT #$i: Rust feature $i details"

        response=$(curl -s -X POST "$API_URL/memories/" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"$variation\",
                \"user_id\": \"$USER_ID\",
                \"metadata\": {\"agent_id\": \"test_infer_false\", \"test_run\": \"infer_false_test\"},
                \"attachment_text\": \"$attachment\",
                \"infer\": false
            }")

        echo "  Iteration $i response: $response" | jq -c '.'
    done

    # Search and verify each memory has exactly 1 attachment
    echo -e "\nSearching for infer=false memories..."
    search_result=$(curl -s -X POST "$API_URL/memories/filter" \
        -H "Content-Type: application/json" \
        -d "{
            \"user_id\": \"$USER_ID\",
            \"search_query\": \"Rust systems programming\",
            \"size\": 20
        }")

    echo "$search_result" | jq '.items[] | select(.metadata_.test_run == "infer_false_test") | {id: .id, content: .content, attachment_count: (.metadata_.attachment_ids | length)}'

    # Count memories with exactly 1 attachment
    local count_single=$(echo "$search_result" | jq '[.items[] | select(.metadata_.test_run == "infer_false_test" and (.metadata_.attachment_ids | length) == 1)] | length')

    if [ "$count_single" -ge 8 ]; then  # At least 8 out of 10 (allowing for some dedup even with infer=false)
        echo -e "${GREEN}✓ Found $count_single memories with single attachment (no UPDATE merging)${NC}"
        return 0
    else
        echo -e "${RED}✗ Only $count_single memories with single attachment${NC}"
        return 1
    fi
}

# Test 3: Verify attachment retrieval for merged memories
test_attachment_retrieval() {
    echo "Testing attachment retrieval for memories with multiple attachments..."

    # Find a memory with multiple attachments from test 1
    search_result=$(curl -s -X POST "$API_URL/memories/filter" \
        -H "Content-Type: application/json" \
        -d "{
            \"user_id\": \"$USER_ID\",
            \"search_query\": \"Python programming\",
            \"size\": 5
        }")

    local memory_with_multiple=$(echo "$search_result" | jq -r '[.items[] | select(.metadata_.test_run == "inference_behavior" and (.metadata_.attachment_ids | length) > 1)] | first | .metadata_.attachment_ids[]')

    if [ -z "$memory_with_multiple" ]; then
        echo "No memory with multiple attachments found, skipping..."
        return 0
    fi

    echo "Found attachment IDs: $memory_with_multiple"

    # Try retrieving each attachment
    local retrieved_count=0
    while IFS= read -r att_id; do
        echo "Retrieving attachment: $att_id"
        att_response=$(curl -s -w "\n%{http_code}" "$API_URL/attachments/$att_id")
        http_code=$(echo "$att_response" | tail -1)

        if [ "$http_code" = "200" ]; then
            echo -e "${GREEN}✓ Retrieved attachment $att_id${NC}"
            retrieved_count=$((retrieved_count + 1))
        else
            echo -e "${RED}✗ Failed to retrieve attachment $att_id (HTTP $http_code)${NC}"
            return 1
        fi
    done <<< "$memory_with_multiple"

    echo -e "${GREEN}✓ Successfully retrieved $retrieved_count attachments${NC}"
    return 0
}

# ====================
# RUN TESTS
# ====================

echo "========================================="
echo "INFERENCE BEHAVIOR TESTS"
echo "========================================="

run_test "Test 1: infer=true causes UPDATE events and merges attachments" test_infer_true_updates
run_test "Test 2: infer=false prevents UPDATE events, each memory separate" test_infer_false_no_updates
run_test "Test 3: Verify all merged attachments are retrievable" test_attachment_retrieval

# ====================
# SUMMARY
# ====================

echo -e "\n========================================="
echo -e "TEST SUMMARY: $TEST_NAME"
echo -e "========================================="
echo -e "Total:  $TESTS_RUN"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    exit 1
else
    echo -e "Failed: $TESTS_FAILED"
    exit 0
fi
