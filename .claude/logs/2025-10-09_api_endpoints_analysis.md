# API Endpoints Analysis - Memory and Attachment Operations

**Date:** 2025-10-09
**Status:** Current State Analysis (before fixes)

This document provides a comprehensive overview of all REST API and MCP endpoints related to memory and attachment operations in OpenMemory.

---

## 📋 Table of Contents

1. [REST API Endpoints](#rest-api-endpoints)
2. [MCP Tools](#mcp-tools)
3. [Attachment Handling Analysis](#attachment-handling-analysis)
4. [Issues Identified](#issues-identified)
5. [Recommendations](#recommendations)

---

## REST API Endpoints

### Memory Operations

#### 1. **GET /api/v1/memories/**
**Purpose:** List all memories with filtering and pagination

**Parameters:**
- `user_id` (required): String - User identifier
- `app_id` (optional): UUID - Filter by app
- `from_date` (optional): Int - Unix timestamp filter
- `to_date` (optional): Int - Unix timestamp filter
- `categories` (optional): String - Comma-separated category names
- `search_query` (optional): String - Text search filter
- `sort_column` (optional): String - Column to sort by
- `sort_direction` (optional): String - "asc" or "desc"
- `params`: Pagination parameters

**Attachment Handling:**
- Returns memories with `metadata_` which may contain `attachment_ids` array
- No special attachment handling

---

#### 2. **POST /api/v1/memories/**
**Purpose:** Create new memory with optional LLM processing

**Parameters:**
```python
{
  "user_id": str,              # Required
  "text": str,                 # Required - memory content
  "app": str,                  # Default: "openmemory"
  "metadata": dict,            # Default: {}
  "infer": bool,               # Optional - enables LLM processing
  "extract": bool,             # Optional - enables fact extraction
  "deduplicate": bool,         # Optional - enables deduplication
  "attachment_text": str,      # Optional - attachment content
  "attachment_id": UUID        # Optional - attachment UUID
}
```

**Attachment Handling:**
- **IF** `attachment_text` provided:
  - Creates new attachment in database
  - Uses provided `attachment_id` or generates new UUID
  - Adds attachment ID to metadata as `attachment_ids` array
- **IF** only `attachment_id` provided (no text):
  - Verifies attachment exists
  - Links existing attachment to memory
  - Adds to `attachment_ids` array

**Deduplication Behavior:**
- **ADD event:** New attachment IDs added to `attachment_ids` array in metadata
- **UPDATE event:**
  - ✅ **CORRECT:** Merges existing attachment IDs with new ones
  - Preserves old attachments and adds new ones
  - Uses `list(set(...))` to avoid duplicates
- **NONE event:** No action taken
- **DELETE event:** (handled by mem0 LLM) - Not applicable for attachments

**Current Implementation:**
```python
# Lines 430-446 in memories.py
elif result['event'] == 'UPDATE':
    memory_id = UUID(result['id'])
    existing_memory = db.query(Memory).filter(Memory.id == memory_id).first()

    if existing_memory:
        # Get existing attachment IDs
        existing_attachment_ids = []
        if existing_memory.metadata_ and 'attachment_ids' in existing_memory.metadata_:
            existing_attachment_ids = existing_memory.metadata_['attachment_ids']

        # Merge old and new attachment IDs
        if metadata.get('attachment_ids'):
            merged_attachment_ids = list(set(existing_attachment_ids + metadata['attachment_ids']))
            metadata['attachment_ids'] = merged_attachment_ids
        elif existing_attachment_ids:
            metadata['attachment_ids'] = existing_attachment_ids
```

---

#### 3. **GET /api/v1/memories/{memory_id}**
**Purpose:** Get single memory by ID

**Parameters:**
- `memory_id` (path): UUID - Memory identifier

**Returns:**
```python
{
  "id": UUID,
  "text": str,
  "created_at": int,
  "state": str,
  "app_id": UUID,
  "app_name": str,
  "categories": List[str],
  "metadata_": dict  # Contains attachment_ids if present
}
```

**Attachment Handling:**
- Returns `metadata_` which may contain `attachment_ids` array

---

#### 4. **DELETE /api/v1/memories/**
**Purpose:** Delete multiple memories

**Parameters:**
```python
{
  "memory_ids": List[UUID],      # Required
  "user_id": str,                # Required
  "delete_attachments": bool     # Default: False
}
```

**Attachment Handling:**
- **IF** `delete_attachments=True`:
  - ⚠️ **ISSUE:** Only looks for `attachment_id` (singular) in metadata
  - ⚠️ **ISSUE:** Does NOT handle `attachment_ids` (array) properly
  - Current code: `attachment_id_str = memory.metadata_.get("attachment_id")`
  - Should check: `attachment_ids` array

**Current Implementation:**
```python
# Lines 546-558 in memories.py
if request.delete_attachments:
    for memory_id in request.memory_ids:
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if memory and memory.metadata_:
            attachment_id_str = memory.metadata_.get("attachment_id")  # ⚠️ WRONG KEY
            if attachment_id_str:
                try:
                    attachment_id = UUID(attachment_id_str)
                    db.query(Attachment).filter(Attachment.id == attachment_id).delete()
                except (ValueError, AttributeError):
                    pass
```

**Vector Store Deletion:**
- ✅ **FIXED:** Calls `memory_client.delete(str(memory_id))` to delete from Qdrant
- ✅ **FIXED:** Marks memory as deleted in database

---

#### 5. **PUT /api/v1/memories/{memory_id}**
**Purpose:** Update memory content directly (bypasses LLM)

**Parameters:**
```python
{
  "memory_content": str,  # Required - new content
  "user_id": str          # Required
}
```

**Attachment Handling:**
- ❌ **NO ATTACHMENT SUPPORT** - Cannot add/modify attachments via this endpoint
- Only updates memory content

---

#### 6. **POST /api/v1/memories/actions/archive**
**Purpose:** Archive memories

**Parameters:**
- `memory_ids`: List[UUID]
- `user_id`: UUID

**Attachment Handling:**
- No attachment handling - only changes memory state

---

#### 7. **POST /api/v1/memories/actions/pause**
**Purpose:** Pause access to memories

**Parameters:**
```python
{
  "user_id": str,
  "memory_ids": List[UUID],      # Optional
  "category_ids": List[UUID],    # Optional
  "app_id": UUID,                # Optional
  "all_for_app": bool,           # Default: False
  "global_pause": bool,          # Default: False
  "state": MemoryState           # Optional - target state
}
```

**Attachment Handling:**
- No attachment handling - only changes memory state

---

#### 8. **GET /api/v1/memories/{memory_id}/access-log**
**Purpose:** Get access logs for a memory

**Parameters:**
- `memory_id` (path): UUID
- `page`: int (default: 1)
- `page_size`: int (default: 10, max: 100)

**Attachment Handling:**
- No attachment handling

---

#### 9. **POST /api/v1/memories/filter**
**Purpose:** Advanced memory filtering

**Parameters:**
```python
{
  "user_id": str,
  "page": int,                    # Default: 1
  "size": int,                    # Default: 10
  "search_query": str,            # Optional
  "app_ids": List[UUID],          # Optional
  "category_ids": List[UUID],     # Optional
  "sort_column": str,             # Optional
  "sort_direction": str,          # Optional
  "from_date": int,               # Optional
  "to_date": int,                 # Optional
  "show_archived": bool           # Default: False
}
```

**Attachment Handling:**
- Returns memories with `metadata_` containing `attachment_ids`

---

#### 10. **GET /api/v1/memories/{memory_id}/related**
**Purpose:** Get related memories by category

**Parameters:**
- `memory_id` (path): UUID
- `user_id`: str
- `params`: Pagination parameters

**Attachment Handling:**
- Returns memories with `metadata_` containing `attachment_ids`

---

### Attachment Operations

#### 11. **POST /api/v1/attachments/**
**Purpose:** Create standalone attachment

**Parameters:**
```python
{
  "id": UUID,        # Optional - auto-generated if not provided
  "content": str     # Required - attachment content (max 100MB)
}
```

**Notes:**
- Creates attachment in database
- Does NOT link to any memory
- Must be linked via memory operations

---

#### 12. **GET /api/v1/attachments/{attachment_id}**
**Purpose:** Get attachment by ID

**Parameters:**
- `attachment_id` (path): UUID

**Returns:**
```python
{
  "id": UUID,
  "content": str,
  "created_at": datetime,
  "updated_at": datetime
}
```

---

#### 13. **PUT /api/v1/attachments/{attachment_id}**
**Purpose:** Update attachment content

**Parameters:**
- `attachment_id` (path): UUID
- Body: `{"content": str}`

**Notes:**
- Updates existing attachment
- Size limit: 100MB (configurable via `ATTACHMENT_MAX_SIZE_MB`)

---

#### 14. **DELETE /api/v1/attachments/{attachment_id}**
**Purpose:** Delete attachment by ID

**Parameters:**
- `attachment_id` (path): UUID

**Returns:**
- HTTP 204 No Content (idempotent - succeeds even if not found)

**Safety:**
- ⚠️ **NO REFERENCE CHECK** - Can delete attachments still referenced by memories
- Should check if attachment is referenced before deletion

---

## MCP Tools

### Memory Operations

#### 1. **add_memories**
**Purpose:** Add new memory with optional LLM processing

**Parameters:**
```python
{
  "text": str,                   # Required - memory content
  "metadata": dict,              # Optional - custom metadata
  "attachment_text": str,        # Optional - attachment content
  "attachment_id": str,          # Optional - attachment UUID (as string)
  "infer": bool,                 # Optional - enables LLM processing
  "extract": bool,               # Optional - enables fact extraction
  "deduplicate": bool            # Optional - enables deduplication
}
```

**Context Variables:**
- `user_id`: Extracted from SSE session
- `client_name`: Extracted from SSE session path

**Attachment Handling:**
- **IF** `attachment_text` provided:
  - Creates new attachment in database
  - Uses provided `attachment_id` or generates new UUID
  - Adds to `new_attachment_ids` array
- **IF** only `attachment_id` provided:
  - Verifies attachment exists
  - Links existing attachment
  - Adds to `new_attachment_ids` array
- Stores in metadata as `attachment_ids` array

**Deduplication Behavior:**
- **ADD event:**
  - Creates new memory with `attachment_ids` in metadata
- **UPDATE event:**
  - ✅ **CORRECT:** Merges existing attachment IDs with new ones
  - Uses `list(set(...))` to avoid duplicates
- **NONE event:** No action
- **DELETE event:** Memory marked as deleted

**Current Implementation:**
```python
# Lines 188-200 in mcp_server.py
elif result['event'] == 'UPDATE':
    if memory:
        # Preserve existing attachments and merge with new ones
        existing_attachment_ids = []
        if memory.metadata_ and 'attachment_ids' in memory.metadata_:
            existing_attachment_ids = memory.metadata_['attachment_ids']

        # Merge old and new attachment IDs (avoid duplicates)
        merged_attachment_ids = list(set(existing_attachment_ids + new_attachment_ids))

        # Update combined_metadata with merged attachments
        if merged_attachment_ids:
            combined_metadata["attachment_ids"] = merged_attachment_ids
```

---

#### 2. **search_memory**
**Purpose:** Semantic search through memories

**Parameters:**
```python
{
  "query": str,                      # Required - search query
  "limit": int,                      # Default: 10
  "agent_id": str,                   # Optional - filter by agent_id in metadata
  "include_metadata": bool,          # Default: False - return full metadata
  "attachment_ids_show": bool        # Optional - return attachment_ids
}
```

**Metadata Behavior:**
- **IF** `include_metadata=True`: Returns full metadata (overrides attachment_ids_show)
- **ELSE IF** `attachment_ids_show=True` (or config default): Returns `attachment_ids` in metadata
- **ELSE**: No metadata returned

---

#### 3. **list_memories**
**Purpose:** List all memories for user

**Parameters:** None (uses context variables from SSE session)

**Returns:**
- Array of memory objects with full data
- Filtered by access permissions

**Attachment Handling:**
- Returns memories as-is from vector store
- No special attachment filtering

---

#### 4. **delete_all_memories**
**Purpose:** Delete all accessible memories for user

**Parameters:**
```python
{
  "delete_attachments": bool  # Default: False
}
```

**Attachment Handling:**
- **IF** `delete_attachments=True`:
  - ⚠️ **ISSUE:** Only looks for `attachment_id` (singular) in metadata
  - ⚠️ **ISSUE:** Does NOT handle `attachment_ids` (array) properly
  - Current code: `attachment_id_str = memory.metadata_.get("attachment_id")`
  - Should check: `attachment_ids` array

**Current Implementation:**
```python
# Lines 450-462 in mcp_server.py
if delete_attachments:
    for memory_id in accessible_memory_ids:
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if memory and memory.metadata_:
            attachment_id_str = memory.metadata_.get("attachment_id")  # ⚠️ WRONG KEY
            if attachment_id_str:
                try:
                    attachment_id = uuid.UUID(attachment_id_str)
                    db.query(Attachment).filter(Attachment.id == attachment_id).delete()
                except (ValueError, AttributeError):
                    pass
```

**Vector Store Deletion:**
- ✅ **FIXED:** Calls `memory_client.delete(str(memory_id))` for each memory
- ✅ **FIXED:** Marks memories as deleted in database

---

#### 5. **get_attachment**
**Purpose:** Retrieve attachment content by UUID

**Parameters:**
```python
{
  "attachment_id": str  # Required - UUID as string
}
```

**Returns:**
```python
{
  "id": str,
  "content": str,
  "created_at": str,  # ISO format
  "updated_at": str   # ISO format
}
```

---

#### 6. **delete_attachment**
**Purpose:** Delete attachment by UUID

**Parameters:**
```python
{
  "attachment_id": str  # Required - UUID as string
}
```

**Returns:**
```python
{
  "success": bool,
  "message": str
}
```

**Safety:**
- ⚠️ **NO REFERENCE CHECK** - Can delete attachments still referenced by memories
- Idempotent operation (succeeds even if attachment doesn't exist)

---

## Attachment Handling Analysis

### Current Behavior

#### ✅ What Works Correctly

1. **Creating memories with attachments (REST & MCP)**
   - Both APIs support `attachment_text` and `attachment_id` parameters
   - Properly stores attachment IDs in `attachment_ids` array in metadata
   - Handles both new attachment creation and linking existing attachments

2. **Attachment merging on UPDATE events**
   - Both REST API and MCP correctly merge old and new attachment IDs
   - Uses `list(set(...))` to avoid duplicates
   - Preserves existing attachments when adding new ones

3. **Standalone attachment CRUD (REST API)**
   - Can create, read, update, delete attachments independently
   - Proper size validation (100MB default limit)
   - Idempotent delete operation

4. **MCP attachment retrieval**
   - `get_attachment` tool works correctly
   - Returns full attachment content with metadata

### ⚠️ Issues Identified

#### 1. **Critical: Wrong metadata key in delete operations**

**Both REST DELETE and MCP delete_all_memories use wrong key:**

```python
# Current (WRONG):
attachment_id_str = memory.metadata_.get("attachment_id")  # Singular - doesn't exist!

# Should be:
attachment_ids = memory.metadata_.get("attachment_ids", [])  # Array - the actual key
```

**Impact:**
- Attachments are NEVER deleted when `delete_attachments=True`
- Code silently fails (no error, just doesn't find the key)
- Orphaned attachments accumulate in database

**Files affected:**
- `openmemory/api/app/routers/memories.py` - Line 551
- `openmemory/api/app/mcp_server.py` - Line 455

---

#### 2. **Medium: No attachment reference checking**

**Problem:**
- REST API endpoint `DELETE /api/v1/attachments/{attachment_id}` doesn't check if attachment is referenced
- MCP tool `delete_attachment` doesn't check if attachment is referenced
- Can orphan memories by deleting their attachments

**Risk:**
- Memories reference attachments that no longer exist
- No cascading delete or reference count

**Recommendation:**
- Add reference counting before allowing direct attachment deletion
- OR: Only allow attachment deletion via memory deletion
- OR: Make direct attachment deletion a soft delete with cleanup job

---

#### 3. **Low: REST DELETE doesn't support `delete_attachments` parameter**

**Problem:**
- Only REST `DELETE /api/v1/memories/` endpoint supports `delete_attachments`
- Individual memory deletion doesn't have this option
- Inconsistent with MCP `delete_all_memories` which has the parameter

**Note:** Per user's requirements, individual delete should NOT support this parameter (to avoid deleting attachments referenced by other memories). This is actually correct behavior, but the docs/comments should clarify this.

---

#### 4. **Documentation: Metadata key migration**

**Old format** (no longer used):
```python
metadata = {
  "attachment_id": "uuid-string"  # Single attachment (OLD)
}
```

**Current format:**
```python
metadata = {
  "attachment_ids": ["uuid-string-1", "uuid-string-2"]  # Array (NEW)
}
```

**Problem:**
- Code references old format in delete operations
- May have legacy data with old format in database

**Recommendation:**
- Migration script to convert old `attachment_id` to `attachment_ids` array
- Update delete operations to handle both formats during transition

---

## Recommendations

### 1. **Fix delete_attachments parameter handling**

**Priority:** 🔴 Critical

**Changes needed:**

```python
# In both memories.py (line 546-558) and mcp_server.py (line 450-462):

if request.delete_attachments:  # or delete_attachments parameter
    for memory_id in memory_ids:
        memory = db.query(Memory).filter(Memory.id == memory_id).first()
        if memory and memory.metadata_:
            # NEW: Handle attachment_ids array
            attachment_ids = memory.metadata_.get("attachment_ids", [])

            # Also handle legacy attachment_id (singular) if present
            legacy_attachment_id = memory.metadata_.get("attachment_id")
            if legacy_attachment_id and legacy_attachment_id not in attachment_ids:
                attachment_ids.append(legacy_attachment_id)

            # Delete all attachments
            for attachment_id_str in attachment_ids:
                try:
                    attachment_id = uuid.UUID(attachment_id_str)
                    db.query(Attachment).filter(Attachment.id == attachment_id).delete()
                except (ValueError, AttributeError):
                    logging.warning(f"Invalid attachment ID: {attachment_id_str}")
                    pass
```

---

### 2. **Add attachment reference safety**

**Priority:** 🟡 Medium

**Option A: Reference counting before deletion**

```python
# In attachments.py delete endpoint and MCP delete_attachment tool:

# Check if attachment is referenced by any memory
memories_referencing = db.query(Memory).filter(
    Memory.state != MemoryState.deleted,
    Memory.metadata_.contains({"attachment_ids": [str(attachment_id)]})
).count()

if memories_referencing > 0:
    raise HTTPException(
        status_code=409,
        detail=f"Attachment is referenced by {memories_referencing} active memories. Delete those memories first."
    )
```

**Option B: Soft delete with cleanup**
- Add `deleted_at` field to Attachment model
- Soft delete attachments when requested
- Cleanup job removes attachments not referenced by any active memory

---

### 3. **Clarify individual memory delete behavior**

**Priority:** 🟢 Low (documentation)

**Per user's requirements:**
- Individual memory delete (`DELETE /api/v1/memories/`) should NOT support `delete_attachments`
- This prevents accidentally deleting attachments referenced by other memories
- Only bulk delete (`delete_all_memories`) should support this parameter

**Action:**
- Update API documentation to clarify this design decision
- Add code comments explaining the rationale

---

### 4. **Data migration for legacy format**

**Priority:** 🟡 Medium

**Create migration script:**

```python
# Migration: Convert attachment_id to attachment_ids array
memories_to_migrate = db.query(Memory).filter(
    Memory.metadata_.contains({"attachment_id": ...})
).all()

for memory in memories_to_migrate:
    old_id = memory.metadata_.get("attachment_id")
    if old_id:
        # Convert to array format
        memory.metadata_["attachment_ids"] = [old_id]
        # Remove old key
        del memory.metadata_["attachment_id"]

db.commit()
```

---

### 5. **Add MCP "delete memory" tool (singular)**

**Priority:** 🟢 Low (enhancement)

**Currently missing:**
- MCP has `delete_all_memories` (bulk)
- MCP does NOT have single memory delete
- REST API has both

**Recommendation:**
Add MCP tool for consistency:

```python
@mcp.tool(description="Delete a single memory by ID")
async def delete_memory(
    memory_id: Annotated[str, "The UUID of the memory to delete."]
) -> str:
    # Implementation similar to REST DELETE /memories/
    # WITHOUT delete_attachments parameter (per user's requirements)
```

---

## Summary Table

| Operation | REST API | MCP | delete_attachments param | Attachment handling status |
|-----------|----------|-----|--------------------------|----------------------------|
| **Create memory** | ✅ POST /memories/ | ✅ add_memories | N/A | ✅ Correct |
| **Create memory with attachment** | ✅ POST /memories/ | ✅ add_memories | N/A | ✅ Correct |
| **Update (dedup merge)** | ✅ POST /memories/ | ✅ add_memories | N/A | ✅ Correct (merges attachments) |
| **Delete single memory** | ✅ DELETE /memories/ | ❌ Missing | ✅ Yes | ⚠️ BROKEN (wrong key) |
| **Delete all memories** | ❌ Missing | ✅ delete_all_memories | ✅ Yes | ⚠️ BROKEN (wrong key) |
| **Get attachment** | ✅ GET /attachments/{id} | ✅ get_attachment | N/A | ✅ Correct |
| **Delete attachment** | ✅ DELETE /attachments/{id} | ✅ delete_attachment | N/A | ⚠️ No reference check |
| **Create standalone attachment** | ✅ POST /attachments/ | ❌ Missing | N/A | ✅ Correct |
| **Update attachment** | ✅ PUT /attachments/{id} | ❌ Missing | N/A | ✅ Correct |

---

## Next Steps

1. Fix critical bug in delete operations (wrong metadata key)
2. Decide on attachment deletion safety approach (reference counting vs soft delete)
3. Create data migration script for legacy format
4. Update documentation to clarify design decisions
5. Consider adding missing MCP tools for API parity

---

**End of Analysis**
