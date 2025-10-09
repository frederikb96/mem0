# OpenMemory Multi-Attachment Testing Plan

## Test Categories

### 1. Inference Behavior Tests (`test_inference_behavior.sh`)
**Goal:** Understand how `infer=true` vs `infer=false` affects memory creation and updates

**Test Cases:**
1. **infer=true (default)**: Add 10 very similar memories with different attachments
   - Expected: Triggers UPDATE events, preserves all attachments
2. **infer=false**: Add 10 very similar memories with different attachments
   - Expected: All ADD events, each memory gets its own attachment
3. **Mixed scenario**: Add with infer=true, then infer=false
   - Expected: Understand interaction between modes

### 2. Large Attachment Tests (`test_large_attachments.sh`)
**Goal:** Verify 100MB attachments work without errors

**Test Cases:**
1. **Small attachment** (100 words): Baseline
2. **Medium attachment** (1000 words): Previously failing
3. **Large attachment** (10,000 words): Stress test
4. **Very large attachment** (100,000 words ~500KB): Near limit
5. **Multiple large attachments**: 10 memories each with 10,000 word attachments

### 3. Special Characters Tests (`test_special_characters.sh`)
**Goal:** Ensure emojis and special characters don't cause 503 errors

**Test Cases:**
1. **Emojis in summary**: 🎉 🚀 💡 etc.
2. **Emojis in attachment**: Full emoji story
3. **Unicode characters**: Chinese, Arabic, Russian text
4. **Special chars**: <, >, &, quotes, backslashes
5. **Mixed**: All of the above combined

### 4. Multi-Attachment Merging Tests (`test_attachment_merging.sh`)
**Goal:** Verify UPDATE events properly merge attachment_ids arrays

**Test Cases:**
1. **Sequential updates**: Add memory, trigger 5 UPDATE events with new attachments
   - Expected: attachment_ids grows: [uuid1] → [uuid1, uuid2] → [uuid1, uuid2, uuid3]
2. **Duplicate prevention**: Try adding same attachment_id twice
   - Expected: No duplicates in array
3. **Empty attachment updates**: UPDATE without new attachment
   - Expected: Preserves existing attachments
4. **Search and verify**: Confirm all attachments retrievable

### 5. MCP API Tests (`test_mcp_features.sh`)
**Goal:** Test new MCP parameters (infer flag, attachment_ids filtering)

**Test Cases:**
1. **MCP add with infer=true**: Default behavior
2. **MCP add with infer=false**: No deduplication
3. **MCP search with include_metadata=false**: Minimal response
4. **MCP search with include_metadata=true, attachment_ids_show=true**: Only attachment_ids in metadata
5. **MCP search with include_metadata=true, attachment_ids_show=false**: Full metadata

### 6. Stress & Edge Case Tests (`test_edge_cases.sh`)
**Goal:** Break things to find limits

**Test Cases:**
1. **100 rapid concurrent adds**: Same summary, different attachments
2. **Empty attachment_text**: Should fail gracefully
3. **Invalid attachment_id**: Should return 404
4. **Malformed UTF-8**: How does system handle it?
5. **Attachment with only whitespace**: Valid or error?
6. **Memory with no summary but with attachment**: Edge case
7. **10MB single-line attachment**: No newlines

## Test Script Structure

Each test script follows this pattern:
```bash
#!/bin/bash
set -euo pipefail

# Configuration
API_URL="http://localhost:8765/api/v1"
USER_ID="frederik"
TEST_NAME="<test_category>"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
run_test() {
    local test_name="$1"
    local test_command="$2"

    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "\n[TEST $TESTS_RUN] $test_name"

    if eval "$test_command"; then
        echo -e "${GREEN}✓ PASSED${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Cleanup before tests
cleanup() {
    echo "Cleaning up test data..."
    # Delete all test memories
}

# Run cleanup
trap cleanup EXIT

# ====================
# TESTS START HERE
# ====================

run_test "Test Name" "curl command here | jq validation"

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
else
    echo -e "Failed: $TESTS_FAILED"
fi
echo -e "=========================================\n"

# Exit with error if any tests failed
[ $TESTS_FAILED -eq 0 ] || exit 1
```

## Expected Outcomes

### Before Fixes:
- Large attachments (>1000 words): ❌ FAIL (timeout/503)
- Special characters: ❌ FAIL (503 error)
- MCP infer flag: ❌ NOT AVAILABLE
- MCP attachment_ids filter: ❌ NOT AVAILABLE
- Backward compat code: ⚠️ PRESENT (should be removed)

### After Fixes:
- Large attachments up to 100MB: ✅ PASS
- Special characters/emojis: ✅ PASS
- MCP infer flag: ✅ AVAILABLE
- MCP attachment_ids filter: ✅ AVAILABLE
- Backward compat code: ✅ REMOVED
