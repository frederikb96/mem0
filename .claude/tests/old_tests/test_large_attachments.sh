#!/bin/bash
set -euo pipefail

# Test large attachments up to 100MB
# Goal: Verify system handles large attachments without timeouts or 503 errors

API_URL="http://localhost:8765/api/v1"
USER_ID="frederik"
TEST_NAME="Large Attachments"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

# Generate text of specific word count
generate_text() {
    local word_count=$1
    local text=""
    local base="Lorem ipsum dolor sit amet consectetur adipiscing elit"

    for ((i=0; i<word_count; i++)); do
        text="$text ${base} "
    done

    echo "$text"
}

# Test 1: Small attachment (100 words) - baseline
test_small_attachment() {
    echo "Creating memory with 100-word attachment..."
    local attachment_text=$(generate_text 100)
    local size_bytes=${#attachment_text}

    echo "Attachment size: $size_bytes bytes (~100 words)"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d "{
            \"text\": \"Test memory with small attachment\",
            \"user_id\": \"$USER_ID\",
            \"metadata\": {\"agent_id\": \"test_small\", \"size\": \"100_words\"},
            \"attachment_text\": $(echo "$attachment_text" | jq -R -s '.'),
            \"infer\": false
        }")

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        memory_id=$(echo "$body" | jq -r '.id')
        att_id=$(echo "$body" | jq -r '.metadata_.attachment_ids[0]')
        echo -e "${GREEN}✓ Memory created: $memory_id, Attachment: $att_id${NC}"

        # Verify attachment retrieval
        att_response=$(curl -s -w "\n%{http_code}" "$API_URL/attachments/$att_id")
        att_http=$(echo "$att_response" | tail -1)

        if [ "$att_http" = "200" ]; then
            echo -e "${GREEN}✓ Attachment retrieved successfully${NC}"
            return 0
        else
            echo -e "${RED}✗ Failed to retrieve attachment (HTTP $att_http)${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Failed to create memory (HTTP $http_code)${NC}"
        echo "$body" | jq '.'
        return 1
    fi
}

# Test 2: Medium attachment (1000 words) - previously failing
test_medium_attachment() {
    echo "Creating memory with 1000-word attachment..."
    local attachment_text=$(generate_text 1000)
    local size_bytes=${#attachment_text}

    echo "Attachment size: $size_bytes bytes (~1000 words, ~6KB)"

    response=$(curl -s -w "\n%{http_code}" --max-time 30 -X POST "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d "{
            \"text\": \"Test memory with medium attachment\",
            \"user_id\": \"$USER_ID\",
            \"metadata\": {\"agent_id\": \"test_medium\", \"size\": \"1000_words\"},
            \"attachment_text\": $(echo "$attachment_text" | jq -R -s '.'),
            \"infer\": false
        }")

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        memory_id=$(echo "$body" | jq -r '.id')
        att_id=$(echo "$body" | jq -r '.metadata_.attachment_ids[0]')
        echo -e "${GREEN}✓ Memory created: $memory_id, Attachment: $att_id${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to create memory (HTTP $http_code)${NC}"
        echo "$body" | jq '.'
        return 1
    fi
}

# Test 3: Large attachment (10,000 words)
test_large_attachment() {
    echo "Creating memory with 10,000-word attachment..."
    local attachment_text=$(generate_text 10000)
    local size_bytes=${#attachment_text}

    echo "Attachment size: $size_bytes bytes (~10,000 words, ~60KB)"

    # Use temporary file for large payload
    local tmpfile=$(mktemp)
    cat > "$tmpfile" <<EOF
{
    "text": "Test memory with large attachment",
    "user_id": "$USER_ID",
    "metadata": {"agent_id": "test_large", "size": "10000_words"},
    "attachment_text": $(echo "$attachment_text" | jq -R -s '.'),
    "infer": false
}
EOF

    response=$(curl -s -w "\n%{http_code}" --max-time 60 -X POST "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d @"$tmpfile")

    rm -f "$tmpfile"

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        memory_id=$(echo "$body" | jq -r '.id')
        att_id=$(echo "$body" | jq -r '.metadata_.attachment_ids[0]')
        echo -e "${GREEN}✓ Memory created: $memory_id, Attachment: $att_id${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to create memory (HTTP $http_code)${NC}"
        echo "$body" | jq '.' | head -20
        return 1
    fi
}

# Test 4: Very large attachment (100,000 words ~600KB)
test_very_large_attachment() {
    echo "Creating memory with 100,000-word attachment..."
    local attachment_text=$(generate_text 100000)
    local size_bytes=${#attachment_text}
    local size_mb=$(echo "scale=2; $size_bytes / 1024 / 1024" | bc)

    echo "Attachment size: $size_bytes bytes (~100,000 words, ~${size_mb}MB)"

    # Use temporary file for large payload
    local tmpfile=$(mktemp)
    cat > "$tmpfile" <<EOF
{
    "text": "Test memory with very large attachment",
    "user_id": "$USER_ID",
    "metadata": {"agent_id": "test_very_large", "size": "100000_words"},
    "attachment_text": $(echo "$attachment_text" | jq -R -s '.'),
    "infer": false
}
EOF

    response=$(curl -s -w "\n%{http_code}" --max-time 120 -X POST "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d @"$tmpfile")

    rm -f "$tmpfile"

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        memory_id=$(echo "$body" | jq -r '.id')
        att_id=$(echo "$body" | jq -r '.metadata_.attachment_ids[0]')
        echo -e "${GREEN}✓ Memory created: $memory_id, Attachment: $att_id (${size_mb}MB)${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to create memory (HTTP $http_code)${NC}"
        echo "$body" | jq '.' | head -20
        return 1
    fi
}

# Test 5: Multiple large attachments
test_multiple_large_attachments() {
    echo "Creating 5 memories each with 10,000-word attachment..."

    local success_count=0

    for i in {1..5}; do
        echo "  Creating memory $i/5..."
        local attachment_text=$(generate_text 10000)

        # Use temporary file for large payload
        local tmpfile=$(mktemp)
        cat > "$tmpfile" <<EOF
{
    "text": "Multiple large test $i",
    "user_id": "$USER_ID",
    "metadata": {"agent_id": "test_multiple", "iteration": $i},
    "attachment_text": $(echo "$attachment_text" | jq -R -s '.'),
    "infer": false
}
EOF

        response=$(curl -s -w "\n%{http_code}" --max-time 60 -X POST "$API_URL/memories/" \
            -H "Content-Type: application/json" \
            -d @"$tmpfile")

        rm -f "$tmpfile"

        http_code=$(echo "$response" | tail -1)

        if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
            success_count=$((success_count + 1))
            echo -e "  ${GREEN}✓ Memory $i created${NC}"
        else
            echo -e "  ${RED}✗ Memory $i failed (HTTP $http_code)${NC}"
        fi
    done

    if [ $success_count -eq 5 ]; then
        echo -e "${GREEN}✓ All 5 large attachments created successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Only $success_count/5 succeeded${NC}"
        return 1
    fi
}

# ====================
# RUN TESTS
# ====================

echo "========================================="
echo "LARGE ATTACHMENT TESTS"
echo "========================================="

run_test "Test 1: Small attachment (100 words)" test_small_attachment
run_test "Test 2: Medium attachment (1000 words)" test_medium_attachment
run_test "Test 3: Large attachment (10,000 words)" test_large_attachment
run_test "Test 4: Very large attachment (100,000 words ~600KB)" test_very_large_attachment
run_test "Test 5: Multiple large attachments (5x 10,000 words)" test_multiple_large_attachments

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
