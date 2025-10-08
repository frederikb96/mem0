#!/bin/bash
set -euo pipefail

# Test special characters and emojis
# Goal: Ensure no 503 errors with Unicode, emojis, special chars

API_URL="http://localhost:8765/api/v1"
USER_ID="frederik"
TEST_NAME="Special Characters & Emojis"

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

# Test 1: Emojis in summary
test_emojis_in_summary() {
    echo "Creating memory with emojis in summary..."

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d '{
            "text": "Python is awesome 🎉 🚀 💡 and very popular 🔥",
            "user_id": "'"$USER_ID"'",
            "metadata": {"agent_id": "test_emoji", "location": "summary"},
            "infer": false
        }')

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ Created with emojis in summary${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed (HTTP $http_code)${NC}"
        echo "$body" | jq '.'
        return 1
    fi
}

# Test 2: Emojis in attachment
test_emojis_in_attachment() {
    echo "Creating memory with emojis in attachment..."

    local emoji_story="🌟 Once upon a time, there was a 🦄 unicorn who loved 🍕 pizza and ☕ coffee. Every day, it would 🚴 cycle to the 🏔️ mountains and enjoy the 🌅 sunrise. The end! 🎬"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d '{
            "text": "Story about a unicorn",
            "user_id": "'"$USER_ID"'",
            "metadata": {"agent_id": "test_emoji", "location": "attachment"},
            "attachment_text": "'"$emoji_story"'",
            "infer": false
        }')

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        att_id=$(echo "$body" | jq -r '.metadata_.attachment_ids[0]')
        echo -e "${GREEN}✓ Created with emojis in attachment: $att_id${NC}"

        # Verify retrieval
        att_response=$(curl -s "$API_URL/attachments/$att_id")
        att_content=$(echo "$att_response" | jq -r '.content')

        if echo "$att_content" | grep -q "🦄"; then
            echo -e "${GREEN}✓ Emoji preserved in attachment${NC}"
            return 0
        else
            echo -e "${RED}✗ Emoji not found in retrieved attachment${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Failed (HTTP $http_code)${NC}"
        echo "$body" | jq '.'
        return 1
    fi
}

# Test 3: Unicode characters (Chinese, Arabic, Russian)
test_unicode_characters() {
    echo "Creating memory with Unicode characters..."

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d '{
            "text": "Multilingual: 你好 مرحبا Привет",
            "user_id": "'"$USER_ID"'",
            "metadata": {"agent_id": "test_unicode"},
            "attachment_text": "Chinese: 这是一个测试\nArabic: هذا اختبار\nRussian: Это тест\nJapanese: これはテストです",
            "infer": false
        }')

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ Created with Unicode characters${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed (HTTP $http_code)${NC}"
        echo "$body" | jq '.'
        return 1
    fi
}

# Test 4: Special characters (<, >, &, quotes, backslashes)
test_special_characters() {
    echo "Creating memory with special characters..."

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d '{
            "text": "HTML tags: <div> & </div>",
            "user_id": "'"$USER_ID"'",
            "metadata": {"agent_id": "test_special"},
            "attachment_text": "Special chars: < > & \" '\'' \\ \n Backslash: C:\\\\path\\\\to\\\\file.txt",
            "infer": false
        }')

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ Created with special characters${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed (HTTP $http_code)${NC}"
        echo "$body" | jq '.'
        return 1
    fi
}

# Test 5: Mixed (all of the above)
test_mixed_characters() {
    echo "Creating memory with ALL character types mixed..."

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d '{
            "text": "🎉 Mixed test: <div> & 你好 Привет",
            "user_id": "'"$USER_ID"'",
            "metadata": {"agent_id": "test_mixed"},
            "attachment_text": "🌟 Unicode test:\n- Chinese: 测试\n- Arabic: اختبار\n- Emoji: 🚀\n- HTML: <tag>\n- Quotes: \"double\" '\''single'\''\n- Path: C:\\\\Users\\\\Test",
            "infer": false
        }')

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ Created with mixed characters${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed (HTTP $http_code)${NC}"
        echo "$body" | jq '.'
        return 1
    fi
}

# Test 6: Null bytes and control characters (edge case)
test_control_characters() {
    echo "Creating memory with control characters..."

    # Using jq to properly escape control characters
    local text_with_controls="Line 1\nLine 2\tTabbed\rCarriage return"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d "{
            \"text\": \"Control character test\",
            \"user_id\": \"$USER_ID\",
            \"metadata\": {\"agent_id\": \"test_control\"},
            \"attachment_text\": $(echo -e "$text_with_controls" | jq -R -s '.'),
            \"infer\": false
        }")

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ Created with control characters${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed (HTTP $http_code)${NC}"
        echo "$body" | jq '.'
        return 1
    fi
}

# ====================
# RUN TESTS
# ====================

echo "========================================="
echo "SPECIAL CHARACTERS & EMOJI TESTS"
echo "========================================="

run_test "Test 1: Emojis in summary" test_emojis_in_summary
run_test "Test 2: Emojis in attachment" test_emojis_in_attachment
run_test "Test 3: Unicode characters (Chinese, Arabic, Russian)" test_unicode_characters
run_test "Test 4: Special characters (<, >, &, quotes, backslashes)" test_special_characters
run_test "Test 5: Mixed (all character types)" test_mixed_characters
run_test "Test 6: Control characters (\\n, \\t, \\r)" test_control_characters

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
