# Bug Fix: parse_messages Adding Role Prefixes with extract=False

**Date:** 2025-10-08
**Type:** Bug Fix
**Scope:** mem0 core library

## Problem

When `extract=False` was used, the system was still modifying the text by adding role prefixes like "user: ", "assistant: ", "system: " through the `parse_messages()` function.

**Expected Behavior:**
When `extract=False`, the text should be stored **exactly as provided** without any modifications.

**Actual Behavior:**
- Input: `"This is a test message"`
- Stored: `"user: This is a test message"`

## Root Cause

In `/home/frederik/Programming/mem0/mem0/memory/main.py`, when `extract=False`, the code used `parsed_messages` which had already been formatted with role prefixes by the `parse_messages()` utility function.

```python
# Before (line 392):
new_retrieved_facts = [parsed_messages]  # Contains "user: " prefix
```

The `parse_messages()` function in `mem0/memory/utils.py` was designed for LLM consumption (formatting conversation history for prompts), but was being used as the content to store.

## Solution

Modified the code to extract raw message content without role prefixes when `extract=False`:

```python
# After (lines 391-397):
# No extraction: Use raw message content without role prefixes
raw_content = ""
for msg in messages:
    if msg["role"] in ["user", "assistant", "system"]:
        raw_content += msg["content"] + "\n"
new_retrieved_facts = [raw_content.strip()]
logger.debug("Extraction disabled. Using raw message content as memory.")
```

## Files Changed

- `/home/frederik/Programming/mem0/mem0/memory/main.py` (lines 390-397)

## Testing

**Test Case:**
```bash
curl -X POST "http://localhost:8765/api/v1/memories/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "frederik",
    "text": "UNIQUE_TEST_12345: This is a test",
    "app": "test-no-prefix",
    "infer": true,
    "extract": false,
    "deduplicate": true
  }'
```

**Result:**
```json
{
  "text": "UNIQUE_TEST_12345: This is a test"
}
```

✓ No "user: " prefix - text stored exactly as provided!

## Impact

- **Users:** When using `extract=False`, text is now stored exactly as provided
- **Deduplication:** Still works correctly, but uses clean text without role prefixes
- **Backward Compatibility:** Existing memories with prefixes remain unchanged; only new memories created with `extract=False` will have clean text

## Related Work

This fix was discovered while testing custom extraction and deduplication prompts. The test script `04-test-custom-prompts.py` validates that the fix works correctly.

## Notes

- The `parse_messages()` function itself was not changed - it's still used for extraction prompts
- Only the non-extraction path was modified to use raw content
- The fix aligns with user expectations: `extract=False` means "don't modify my text"
