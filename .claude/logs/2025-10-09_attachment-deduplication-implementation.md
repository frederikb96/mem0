# Attachment Deduplication Implementation Plan

**Date:** 2025-10-09
**Status:** In Progress
**Feature:** LLM-Aware Attachment Handling During Deduplication

---

## Overview

Implement semantic attachment reassignment during deduplication where the LLM decides which memories should have which attachments based on content relationships, rather than simple programmatic merging.

## Problem Statement

**Current Behavior (Before This Feature):**
- When `deduplicate=False`: Attachments from `add()` call are added to ALL created/updated memories
- When `deduplicate=True`: Attachments are NOT passed to LLM, so semantic decisions cannot be made

**Edge Cases:**
1. **NONE event**: LLM says fact already exists → new memory not added → attachment orphaned
2. **Complex reshuffling**: LLM merges/splits/deletes memories → unclear where attachments should go
3. **Semantic drift**: The memory that should have the attachment might be updated/deleted/merged

**Goal:**
Let the LLM make semantic decisions about attachment placement based on content relationships.

---

## Design Decision: Option 1 - LLM-Aware Attachments ⭐

### Why This Approach?

1. **Semantic Understanding**: LLM can see relationships between facts and attachments
2. **Handles All Edge Cases**: Merges, splits, deletes, NONE events
3. **User Intent**: "I attached this to THIS fact" → LLM finds which memory represents that fact
4. **Debuggable**: Clear in LLM output where attachments went

### Core Principle

- Show attachment metadata to LLM in the deduplication prompt
- LLM returns attachment assignments in its response
- Map attachment IDs (A1, A2, A3...) to avoid UUID confusion
- **Backward compatible**: If no attachments present, field is omitted entirely

---

## Implementation Steps

### ✅ Step 1: Update Prompts (COMPLETED)

**File:** `mem0/configs/prompts.py`

**Changes Made:**
- Updated `DEFAULT_UPDATE_MEMORY_PROMPT` with attachment instructions
- Added 4 examples showing attachment handling for ADD, UPDATE, DELETE, NONE
- Specified backward compatibility (omit field if no attachments)

**Key Instructions Added:**
```
- If attachments are not present in input, omit "attachments" field entirely
- If attachments ARE present, MUST include field in EVERY memory item (even if empty [])
- Assign attachments based on semantic relationships
- When deleting memory with attachments, they're simply deleted
- Never lose attachments - every input attachment must appear in output
```

---

### 🔄 Step 2: Modify Deduplication Flow (IN PROGRESS)

**File:** `mem0/memory/main.py`

**Function:** `_add_to_vector_store()` around lines 399-519

**Changes Needed:**

#### A. Extract Attachment Info from Input

When collecting old memories from vector store (lines 406-413):

```python
# Current code:
for mem in existing_memories:
    retrieved_old_memory.append({"id": mem.id, "text": mem.payload["data"]})

# NEW code:
for mem in existing_memories:
    mem_dict = {"id": mem.id, "text": mem.payload["data"]}

    # Extract attachment_ids from metadata
    if "attachment_ids" in mem.payload:
        mem_dict["attachment_ids"] = mem.payload["attachment_ids"]

    retrieved_old_memory.append(mem_dict)
```

#### B. Track Attachment from Current Add Call

The `metadata` parameter contains `attachment_ids` if attachment was provided.

Extract this BEFORE deduplication:

```python
# After line 398, before Phase 2
current_attachment_id = None
if metadata and "attachment_ids" in metadata and metadata["attachment_ids"]:
    current_attachment_id = metadata["attachment_ids"][0]  # Single attachment per add() call
```

#### C. Build Attachment ID Mapping

After line 425 (UUID mapping creation):

```python
# Map attachment UUIDs to simple IDs (A1, A2, A3...)
attachment_id_mapping = {}
reverse_attachment_mapping = {}

# Collect all unique attachment IDs from old memories
all_attachment_ids = set()
for mem in retrieved_old_memory:
    if "attachment_ids" in mem:
        all_attachment_ids.update(mem["attachment_ids"])

# Add current attachment if present
if current_attachment_id:
    all_attachment_ids.add(current_attachment_id)

# Create mapping
for idx, att_id in enumerate(sorted(all_attachment_ids)):
    simple_id = f"A{idx + 1}"
    attachment_id_mapping[att_id] = simple_id
    reverse_attachment_mapping[simple_id] = att_id

# Replace UUIDs in retrieved_old_memory with simple IDs
for mem in retrieved_old_memory:
    if "attachment_ids" in mem:
        mem["attachment_ids"] = [attachment_id_mapping[aid] for aid in mem["attachment_ids"]]
```

#### D. Prepare New Facts with Attachments

Modify `new_retrieved_facts` to include attachment info:

```python
# If current add() call has attachment, tag ALL extracted facts with it
# (since they all come from same add operation)
if current_attachment_id:
    new_facts_with_attachments = [
        {"text": fact, "attachments": [attachment_id_mapping[current_attachment_id]]}
        for fact in new_retrieved_facts
    ]
else:
    # For backward compatibility: if no attachments anywhere, keep as strings
    if not attachment_id_mapping:
        new_facts_with_attachments = new_retrieved_facts  # Keep as simple strings
    else:
        # There are old attachments but no new one
        new_facts_with_attachments = [
            {"text": fact, "attachments": []}
            for fact in new_retrieved_facts
        ]
```

#### E. Modify Prompt Building

Check if we have ANY attachments:

```python
has_attachments = len(attachment_id_mapping) > 0

# Pass flag to get_update_memory_messages
function_calling_prompt = get_update_memory_messages(
    retrieved_old_memory,
    new_facts_with_attachments if has_attachments else new_retrieved_facts,
    self.config.custom_update_memory_prompt,
    has_attachments=has_attachments  # NEW parameter
)
```

---

### 🔄 Step 3: Update Prompt Builder Function

**File:** `mem0/configs/prompts.py`

**Function:** `get_update_memory_messages()` around line 291

**Changes Needed:**

Add `has_attachments` parameter:

```python
def get_update_memory_messages(
    retrieved_old_memory_dict,
    response_content,
    custom_update_memory_prompt=None,
    has_attachments=False  # NEW
):
    # ... existing code ...

    # Format new facts based on whether attachments are present
    if has_attachments:
        # response_content is now list of dicts with "text" and "attachments"
        facts_formatted = json.dumps(response_content, indent=4)
    else:
        # response_content is list of strings (backward compatible)
        facts_formatted = json.dumps(response_content, indent=4)

    return f"""...
    The new retrieved facts are mentioned in the triple backticks:
    ```
    {facts_formatted}
    ```
    ...
    """
```

---

### 🔄 Step 4: Process LLM Output with Attachments

**File:** `mem0/memory/main.py`

**Location:** Lines 464-511 (processing `new_memories_with_actions`)

**Changes Needed:**

#### A. After LLM Response Parsing (line 446)

Extract and validate attachments from LLM response:

```python
# After line 446 (response parsed into new_memories_with_actions)

# If we sent attachments to LLM, reverse-map them back to UUIDs
if has_attachments and "memory" in new_memories_with_actions:
    for mem in new_memories_with_actions["memory"]:
        if "attachments" in mem:
            # Map A1, A2 back to UUIDs
            mem["attachment_ids"] = [
                reverse_attachment_mapping.get(simple_id)
                for simple_id in mem["attachments"]
                if simple_id in reverse_attachment_mapping
            ]
            # Remove the "attachments" field, keep only "attachment_ids"
            del mem["attachments"]
```

#### B. Modify Memory Creation/Update (lines 475-496)

**For ADD events:**

```python
if event_type == "ADD":
    # Build metadata with attachments
    add_metadata = deepcopy(metadata)

    # Override attachment_ids with what LLM decided
    if has_attachments and "attachment_ids" in resp:
        add_metadata["attachment_ids"] = resp["attachment_ids"]

    memory_id = self._create_memory(
        data=action_text,
        existing_embeddings=new_message_embeddings,
        metadata=add_metadata,
    )
    returned_memories.append({"id": memory_id, "memory": action_text, "event": event_type})
```

**For UPDATE events:**

```python
elif event_type == "UPDATE":
    # Get existing memory to preserve non-attachment metadata
    existing_memory = self.vector_store.get(vector_id=temp_uuid_mapping[resp.get("id")])

    # Build updated metadata
    update_metadata = deepcopy(metadata)

    # Override attachment_ids with what LLM decided
    if has_attachments and "attachment_ids" in resp:
        update_metadata["attachment_ids"] = resp["attachment_ids"]
    elif "attachment_ids" in existing_memory.payload:
        # Preserve existing attachments if LLM didn't change them
        update_metadata["attachment_ids"] = existing_memory.payload["attachment_ids"]

    self._update_memory(
        memory_id=temp_uuid_mapping[resp.get("id")],
        data=action_text,
        existing_embeddings=new_message_embeddings,
        metadata=update_metadata,
    )
    returned_memories.append({
        "id": temp_uuid_mapping[resp.get("id")],
        "memory": action_text,
        "event": event_type,
        "previous_memory": resp.get("old_memory"),
    })
```

**For DELETE events:**
No changes needed - attachments deleted with memory.

**For NONE events:**
No action needed.

---

### 📝 Step 5: Handle No-Deduplication Path

**File:** `mem0/memory/main.py`

**Location:** Lines 450-462 (when `deduplicate=False`)

**Changes Needed:**

When deduplication is disabled, keep current behavior (all facts get the attachment):

```python
# No deduplication: Prepare to ADD all facts directly
logger.debug("Deduplication disabled. Adding all facts directly.")
new_message_embeddings = {}
for new_mem in new_retrieved_facts:
    messages_embeddings = self.embedding_model.embed(new_mem, "add")
    new_message_embeddings[new_mem] = messages_embeddings

# Create simple ADD actions for all facts
# Keep current behavior: all facts get the same attachment (if any)
new_memories_with_actions = {
    "memory": [{"text": fact, "event": "ADD"} for fact in new_retrieved_facts]
}
temp_uuid_mapping = {}
```

Then in processing (line 475), the existing metadata (with attachment_ids) will be used for all.

---

### ✅ Step 6: Implement AsyncMemory Support

**File:** `mem0/memory/main.py`

**Location:** Lines 807-1023 (`AsyncMemory._add_to_vector_store`)

**Changes Needed:**

Apply the same logic as synchronous version, but with `await asyncio.to_thread()` calls.

---

## Testing Strategy

### Test 1: No Extract + Dedup + Attachments

**File:** `.claude/tests/10-test-dedup-attachments-no-extract.py`

**Scenario:**
1. Add memory with attachment: "Lives in Berlin" (attachment A)
2. Add memory with attachment: "Lives in Berlin" (attachment B)
3. Expected: LLM recognizes duplicate, event=NONE or UPDATE with both attachments merged

**Verification:**
- Check final memory has correct attachment(s)
- No orphaned attachments
- Memory content correct

---

### Test 2: Extract + Dedup + Attachments (2 Facts)

**File:** `.claude/tests/11-test-dedup-attachments-with-extract.py`

**Scenario:**
1. Add initial memory with attachment: "I love pizza and hate pineapple" (attachment A)
   - Extracts to: ["Loves pizza", "Hates pineapple"]
2. Add second memory with attachment: "Actually I love pineapple pizza now!" (attachment B)
   - Extracts to: ["Loves pineapple pizza"]
3. Expected:
   - LLM UPDATEs the pineapple fact
   - Keeps the pizza fact
   - Attachment B goes to the updated pineapple fact
   - Attachment A stays with pizza fact OR moves to updated fact (LLM decides semantically)

**Verification:**
- Check which memory has which attachment
- Verify semantic correctness of attachment placement
- No lost attachments

---

### Test 3: Backward Compatibility

**File:** Existing tests should still pass

**Verification:**
- Run existing test suite
- All tests without attachments pass unchanged
- No regressions

---

### Test 4: Edge Case - NONE Event

**Scenario:**
1. Add memory: "Loves pizza" (no attachment)
2. Add memory: "Loves pizza" (with attachment A)
3. Expected: LLM returns NONE, but attachment A should still associate

**Implementation Note:**
This edge case needs special handling - if event is NONE but new fact has attachment, we need to ADD the attachment to the existing memory. May need post-processing step.

---

## Backward Compatibility

### For Users Without Attachments

- If no `attachment_ids` in metadata AND no old memories have attachments:
  - `has_attachments = False`
  - Old format used (facts as simple strings)
  - LLM doesn't see "attachments" field
  - Fully backward compatible

### For Custom Prompts

- Users with `custom_update_memory_prompt` won't break
- Their prompts will see attachment data if present
- Can choose to ignore it or handle it
- Default prompt handles both cases

---

## Files to Modify

1. ✅ `mem0/configs/prompts.py` - Updated with attachment examples
2. 🔄 `mem0/configs/prompts.py` - Add `has_attachments` param to `get_update_memory_messages()`
3. 🔄 `mem0/memory/main.py` - Sync `_add_to_vector_store()` method
4. 🔄 `mem0/memory/main.py` - Async `_add_to_vector_store()` method
5. ✅ `.claude/tests/10-test-dedup-attachments-no-extract.py` - New test
6. ✅ `.claude/tests/11-test-dedup-attachments-with-extract.py` - New test

---

## Testing Checklist

- [ ] Test 1: No extract + dedup + attachments passes
- [ ] Test 2: Extract + dedup + attachments passes
- [ ] Test 3: Backward compatibility (existing tests pass)
- [ ] Test 4: Edge case NONE event handled
- [ ] Test 5: No attachments anywhere (pure backward compat)
- [ ] Test 6: Old memories have attachments, new fact doesn't
- [ ] Test 7: Multiple attachments on same memory
- [ ] Test 8: Attachment moves during UPDATE
- [ ] Test 9: Attachment deleted during DELETE
- [ ] Test 10: AsyncMemory version works

---

## Implementation Order

1. ✅ Update prompt with examples
2. Modify `get_update_memory_messages()` to accept `has_attachments`
3. Update sync `_add_to_vector_store()` deduplication logic
4. Update sync `_add_to_vector_store()` action processing
5. Update async version (mirror changes)
6. Write Test 1 (no extract)
7. Write Test 2 (with extract)
8. Run tests and debug
9. Handle edge cases
10. Final validation with all tests

---

## Known Limitations

1. **No Validation**: We don't validate that LLM returned all input attachments
   - Risk: LLM could "forget" an attachment
   - Mitigation: Clear prompt instructions
   - Future: Add validation layer if needed

2. **Single Attachment Per Add**: Current implementation assumes one attachment per `add()` call
   - This matches current API design
   - Multiple attachments would need array handling

3. **NONE Edge Case**: Needs special handling to avoid orphaning
   - May need post-processing if NONE event but new attachment present

---

## Success Criteria

- [x] Prompts updated with clear attachment instructions
- [ ] LLM receives attachment data when present
- [ ] LLM output parsed correctly with attachments
- [ ] Attachments reassigned based on LLM decisions
- [ ] Backward compatible (no regressions)
- [ ] Tests pass for common scenarios
- [ ] Documentation updated

---

## Notes

- This design allows LLM to make semantic decisions about attachment placement
- User intent ("I attached this to THIS fact") is preserved through semantic matching
- Handles all edge cases: merge, split, delete, NONE
- Fully backward compatible
- No validation layer initially (trust LLM output)
