# OpenMemory Attachments Feature

## Database Migrations

### Running Migrations in Docker

All Alembic commands must be run inside the Docker container:

```bash
# Apply migrations
docker compose exec openmemory-mcp alembic upgrade head

# Rollback one migration
docker compose exec openmemory-mcp alembic downgrade -1

# Check current version
docker compose exec openmemory-mcp alembic current

# View migration history
docker compose exec openmemory-mcp alembic history

# Stamp database without running migrations (if state is incorrect)
docker compose exec openmemory-mcp alembic stamp head
```

### Attachments Table Schema

**Migration ID:** `80299ea4a74e`
**Created:** 2025-10-04

```sql
CREATE TABLE attachments (
    id UUID PRIMARY KEY,
    content VARCHAR NOT NULL,  -- TEXT in PostgreSQL, unlimited in SQLite
    created_at DATETIME,
    updated_at DATETIME
)
```

**Indexes:**
- `ix_attachments_created_at` on `created_at`
- `idx_attachment_id` on `id`

### Troubleshooting

**Issue:** "table attachments already exists"
**Solution:** Drop table manually then rerun migration:
```bash
docker compose exec openmemory-mcp python3 -c "
import sqlite3
conn = sqlite3.connect('openmemory.db')
cursor = conn.cursor()
cursor.execute('DROP TABLE IF EXISTS attachments')
conn.commit()
conn.close()
"
docker compose exec openmemory-mcp alembic upgrade head
```

**Issue:** Alembic autogenerate creates incorrect migration
**Solution:** Always review and manually fix generated migrations before applying. Check that:
- `upgrade()` creates new tables/columns
- `downgrade()` drops them
- Not dropping/recreating existing tables

## Architecture

```
Memory (summary, <8K tokens) -> metadata.attachment_id -> Attachment (full text, <100MB)
           ↓                                                      ↓
    Qdrant (embedding)                                   PostgreSQL/SQLite TEXT field
```

### Size Limits
- Memory content: ~8K tokens (OpenAI embedding limit: 8,191 tokens)
- Attachment content: 100MB (configurable via `ATTACHMENT_MAX_SIZE_MB` env var)

### Metadata Structure
```json
{
  "attachment_id": "uuid-string"
}
```

## Attachments API

### Endpoints

**POST /api/v1/attachments** - Create attachment
```bash
# Auto-generate ID
curl -X POST http://localhost:8765/api/v1/attachments \
  -H "Content-Type: application/json" \
  -d '{"content":"your text here"}'

# Specify ID
curl -X POST http://localhost:8765/api/v1/attachments \
  -H "Content-Type: application/json" \
  -d '{"content":"your text", "id":"550e8400-e29b-41d4-a716-446655440000"}'
```
- Returns: `201 Created` with attachment object
- Errors: `409 Conflict` if ID exists, `413 Payload Too Large` if exceeds size limit

**GET /api/v1/attachments/{id}** - Retrieve attachment
```bash
curl http://localhost:8765/api/v1/attachments/550e8400-e29b-41d4-a716-446655440000
```
- Returns: `200 OK` with attachment object
- Errors: `404 Not Found` if ID doesn't exist

**PUT /api/v1/attachments/{id}** - Update attachment
```bash
curl -X PUT http://localhost:8765/api/v1/attachments/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{"content":"updated text"}'
```
- Returns: `200 OK` with updated attachment object
- Errors: `404 Not Found` if ID doesn't exist, `413 Payload Too Large` if exceeds size limit

**DELETE /api/v1/attachments/{id}** - Delete attachment
```bash
curl -X DELETE http://localhost:8765/api/v1/attachments/550e8400-e29b-41d4-a716-446655440000
```
- Returns: `204 No Content` (idempotent - returns 204 even if already deleted)

### Response Schema
```json
{
  "id": "uuid",
  "content": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Size Limits
- Default: 100MB per attachment
- Configure via: `ATTACHMENT_MAX_SIZE_MB=100` environment variable
- Error: HTTP 413 if exceeded

## Memory Integration with Attachments

### Create Memory with Attachment

**Option 1: Create memory with attachment text (auto-creates attachment)**
```bash
curl -X POST http://localhost:8765/api/v1/memories \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<your-user-id>",
    "text": "Summary of document",
    "infer": false,
    "attachment_text": "Full document content here..."
  }'
```
- Automatically creates attachment
- Links via `metadata.attachment_id`
- Optionally specify `attachment_id` to use specific UUID

**Option 2: Link to existing attachment**
```bash
curl -X POST http://localhost:8765/api/v1/memories \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<your-user-id>",
    "text": "Memory summary",
    "infer": false,
    "attachment_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```
- Links existing attachment to memory
- Returns 404 if attachment_id doesn't exist

### Delete Memory with Attachments

**Default behavior (keeps attachments):**
```bash
curl -X DELETE http://localhost:8765/api/v1/memories \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<your-user-id>",
    "memory_ids": ["uuid1", "uuid2"]
  }'
```

**Delete attachments too:**
```bash
curl -X DELETE http://localhost:8765/api/v1/memories \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<your-user-id>",
    "memory_ids": ["uuid1", "uuid2"],
    "delete_attachments": true
  }'
```

### Backward Compatibility
- All attachment fields are optional
- Existing memory creation still works without changes
- Metadata structure: `{"attachment_id": "uuid-string"}` (flat, non-breaking)

## MCP Tools with Attachments

### add_memories (extended)
```python
# Add memory with attachment text (auto-creates attachment)
add_memories(
    text="Summary of document",
    attachment_text="Full document content here..."
)

# Add memory with specific attachment ID
add_memories(
    text="Summary",
    attachment_text="Content",
    attachment_id="550e8400-e29b-41d4-a716-446655440000"
)

# Link to existing attachment
add_memories(
    text="Summary",
    attachment_id="550e8400-e29b-41d4-a716-446655440000"
)
```

### get_attachment
```python
get_attachment(attachment_id="550e8400-e29b-41d4-a716-446655440000")
# Returns: {"id": "...", "content": "...", "created_at": "...", "updated_at": "..."}
```

### delete_attachment
```python
delete_attachment(attachment_id="550e8400-e29b-41d4-a716-446655440000")
# Returns: {"success": true, "message": "..."}
# Idempotent - returns success even if not found
```

### delete_all_memories (extended)
```python
# Delete memories, keep attachments (default)
delete_all_memories()

# Delete memories AND their attachments
delete_all_memories(delete_attachments=True)
```

## UI (Web Interface)

### Accessing the UI

The UI is available at http://localhost:3000 when running via Docker Compose.

### Attachments Page (/attachments)

**Features:**
- Create new attachments with optional custom ID
- Search for attachments by ID
- View, edit, and delete attachments
- See content size and timestamps

**Navigation:**
Click "Attachments" in the top navigation bar (Paperclip icon)

### Creating Attachments

**Method 1: Standalone Creation**
1. Go to /attachments page
2. Click "Create Attachment" button
3. Optionally enter a custom ID (or leave blank for auto-generated UUID)
4. Enter content in the textarea
5. Click "Save"
6. Copy the generated ID for use with memories

**Method 2: Via Memory Creation (integrated)**
1. Click "Create Memory" button in navbar
2. Enter memory summary in "Memory (Summary)" field
3. Check "Add extended content (attachment)" checkbox
4. Choose one of two options:
   - **Create new:** Enter content directly (auto-creates attachment)
   - **Link existing:** Check "Link existing attachment" and enter attachment ID
5. Click "Save Memory"

### Viewing/Editing Attachments

1. Go to /attachments page
2. Enter attachment ID in search field
3. Press Enter or click "Search" button
4. Dialog opens with attachment details:
   - ID (with copy button)
   - Content (read-only initially)
   - Created/Updated timestamps
   - Character count and size
5. Click "Edit" to modify content
6. Click "Save" to update
7. Click "Delete" to remove (with confirmation)

### Testing the UI

**Test Case 1: Create standalone attachment**
```
1. Navigate to http://localhost:3000/attachments
2. Click "Create Attachment"
3. Enter test content (e.g., "This is test content for attachment")
4. Click Save
5. ✓ Dialog closes
6. ✓ Toast: "Attachment created successfully"
```

**Test Case 2: Search and view attachment**
```
1. Copy attachment ID from previous test
2. Paste in "Attachment ID" search field
3. Press Enter
4. ✓ Dialog opens showing content
5. ✓ ID is displayed with copy button
6. ✓ Timestamps are shown
7. ✓ Content size is displayed
```

**Test Case 3: Edit attachment**
```
1. Open attachment (from Test Case 2)
2. Click "Edit" button
3. Modify content
4. Click "Save"
5. ✓ Toast: "Attachment updated successfully"
6. ✓ Content updated in view
7. ✓ updated_at timestamp changed
```

**Test Case 4: Create memory with new attachment**
```
1. Click "Create Memory" in navbar
2. Enter "Test memory with attachment" in summary field
3. Check "Add extended content (attachment)"
4. Enter "Extended content here..." in Extended Content textarea
5. Click "Save Memory"
6. ✓ Toast: "Memory created successfully"
7. Go to /memories page
8. ✓ New memory appears in list
9. Click on memory to view details
10. ✓ metadata contains attachment_id
```

**Test Case 5: Create memory with existing attachment ID**
```
1. First create an attachment (Test Case 1) and copy its ID
2. Click "Create Memory" in navbar
3. Enter "Memory linked to existing attachment"
4. Check "Add extended content (attachment)"
5. Check "Link existing attachment (by ID)"
6. Paste attachment ID
7. Click "Save Memory"
8. ✓ Toast: "Memory created successfully"
9. ✓ Memory created with metadata.attachment_id set
```

**Test Case 6: Error handling - invalid ID**
```
1. Go to /attachments
2. Enter invalid UUID (e.g., "invalid-id")
3. Click Search
4. ✓ Toast: Error message about invalid ID or not found
```

**Test Case 7: Delete attachment**
```
1. Create test attachment
2. Search for it by ID
3. Click "Delete" button
4. Confirm deletion
5. ✓ Toast: "Attachment deleted successfully"
6. ✓ Dialog closes
7. Try searching for same ID
8. ✓ Shows "not found" error
```

### UI Components

**Files created:**
- `/ui/hooks/useAttachmentsApi.ts` - API hook for CRUD operations
- `/ui/app/attachments/page.tsx` - Main attachments page
- `/ui/app/attachments/components/AttachmentDialog.tsx` - View/Edit/Create dialog
- `/ui/app/memories/components/CreateMemoryDialog.tsx` - Extended with attachment support
- `/ui/components/Navbar.tsx` - Added Attachments navigation link

**Styling:**
- Matches existing OpenMemory dark theme (zinc-900/zinc-950 backgrounds)
- Uses same component library (shadcn/ui)
- Consistent spacing and animations
- Monospace font for IDs and content

### Known Limitations

1. **No attachment listing API** - Can only search by ID, no browse/list functionality
2. **No inline attachment viewing in memory details** - Must manually search for attachment using ID from metadata
3. **No attachment size validation in UI** - Validation happens server-side (100MB limit)
4. **No pagination for content** - Large attachments load entire content at once

### Future UI Enhancements (Optional)

- Add attachment preview in memory detail view (auto-fetch from metadata.attachment_id)
- List all attachments with pagination/filtering
- Rich text editor for attachment content
- File upload support (convert to text)
- Syntax highlighting for code attachments
- Search within attachment content

---

## Integration Testing Results

**Date:** 2025-10-05
**Branch:** main-my
**Environment:** Fresh deployment with clean volumes

### Test Results Summary

✅ **ALL TESTS PASSED** (9/9)

**Test 1: Create Attachment via REST API**
- Endpoint: `POST /api/v1/attachments`
- Result: ✓ Created attachment with auto-generated UUID
- Response: 201 Created with full attachment object

**Test 2: Retrieve Attachment**
- Endpoint: `GET /api/v1/attachments/{id}`
- Result: ✓ Retrieved attachment with all fields
- Response: 200 OK

**Test 3: Update Attachment**
- Endpoint: `PUT /api/v1/attachments/{id}`
- Result: ✓ Content updated, `updated_at` timestamp changed
- Response: 200 OK

**Test 4: Create Memory with attachment_text (auto-create)**
- Endpoint: `POST /api/v1/memories` with `attachment_text`
- Result: ✓ Attachment auto-created, `metadata.attachment_id` set
- Verified: Attachment exists in database with correct content

**Test 5: Create Memory with attachment_id (link existing)**
- Endpoint: `POST /api/v1/memories` with `attachment_id`
- Result: ✓ Memory linked to existing attachment
- Verified: `metadata.attachment_id` matches provided ID

**Test 6: Delete Memory (default - keep attachment)**
- Endpoint: `DELETE /api/v1/memories` without `delete_attachments`
- Result: ✓ Memory deleted, attachment preserved
- Verified: Attachment still exists after memory deletion

**Test 7: Delete Memory with delete_attachments=true**
- Endpoint: `DELETE /api/v1/memories` with `delete_attachments: true`
- Result: ✓ Both memory and attachment deleted
- Verified: Attachment returns 404 after deletion

**Test 8: Error Handling - Non-existent Attachment**
- Endpoint: `POST /api/v1/memories` with invalid `attachment_id`
- Result: ✓ Returns 404 with clear error message
- Error: "Attachment with ID {id} not found"

**Test 9: Error Handling - Duplicate ID**
- Endpoint: `POST /api/v1/attachments` with existing ID
- Result: ✓ Returns 409 Conflict
- Error: "Attachment with ID {id} already exists"

### System Verification

✅ **Database Migration:** Attachments table created successfully
- Columns: id (UUID PK), content (VARCHAR), created_at, updated_at
- Indexes: ix_attachments_created_at, idx_attachment_id

✅ **API Server:** Running without errors
- Only Pydantic deprecation warnings (non-blocking)
- All endpoints responding correctly

✅ **UI Server:** Running and accessible
- Homepage: http://localhost:3000 ✓
- Attachments page: http://localhost:3000/attachments ✓
- No JavaScript errors

✅ **Vector Store (Qdrant):** Running
- Port 6333 accessible
- Ready for vector operations

### Backward Compatibility Verified

✅ Memory creation without attachments works unchanged
✅ All attachment fields optional with safe defaults
✅ Metadata structure flat and non-breaking
✅ Existing memories not affected

### Performance Notes

- Attachment creation: <100ms
- Memory creation with attachment: <150ms
- Retrieval operations: <50ms
- No database locking issues observed

### Known Issues

None identified during testing.

### Ready for Production

The attachments feature is fully functional and ready for use:
- REST API: ✅ All endpoints working
- Memory Integration: ✅ Create/delete flows working
- MCP Tools: ✅ Implemented (not tested in this session)
- UI: ✅ Accessible and responsive
- Documentation: ✅ Complete with examples

**Containers Running:**
```
openmemory-mem0_store-1       Up (Qdrant)
openmemory-openmemory-mcp-1   Up (API + MCP)
openmemory-openmemory-ui-1    Up (Next.js UI)
```

**Access Points:**
- API: http://localhost:8765
- UI: http://localhost:3000
- Qdrant: http://localhost:6333

---

## Environment Setup and Running

### Prerequisites

- Docker and Docker Compose
- OpenAI API Key

### Environment Files

The project requires environment variables in three locations:

**1. Root `.env` (for docker-compose):**
```env
USER=<your-user-id>
NEXT_PUBLIC_API_URL=http://localhost:8765
NEXT_PUBLIC_USER_ID=<your-user-id>
```

**2. `api/.env` (for API service):**
```env
OPENAI_API_KEY=<your-openai-api-key>
USER=<your-user-id>
```

**3. `ui/.env` (for UI service):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8765
NEXT_PUBLIC_USER_ID=<your-user-id>
```

**Note:** All `.env` files are gitignored. Use `.env.example` as templates.

### Starting the Services

**Recommended: Use Makefile commands**

```bash
# From openmemory/ directory

# 1. Create .env files from examples (first time only)
make env

# 2. Edit the .env files with your values
#    - Edit api/.env: set OPENAI_API_KEY
#    - Edit ui/.env: set NEXT_PUBLIC_USER_ID
#    - Edit root .env: set USER and NEXT_PUBLIC_USER_ID

# 3. Build images
make build

# 4. Start services
make up

# View logs
make logs

# Stop services
make down
```

**Alternative: Direct docker-compose commands**

```bash
# Docker Compose auto-loads .env from the same directory
docker compose up -d --build

# Check containers
docker ps

# View logs
docker compose logs -f

# Stop services
docker compose down -v
```

**Important:** Docker Compose automatically loads variables from the root `.env` file. The `docker-compose.yml` uses `${NEXT_PUBLIC_API_URL}` and `${USER}` which are populated from the `.env` file.

### Verifying Setup

```bash
# Check API is responding
curl http://localhost:8765/api/v1/memories/filter \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"user_id":"<your-user-id>"}'

# Check UI (open in browser)
open http://localhost:3000
# Or visit: http://localhost:3000

# Check Qdrant
curl http://localhost:6333/readyz
# Should return: "all shards are ready"

# Check all containers are running
docker ps
```

### Troubleshooting

**UI shows 404 errors or can't connect to API:**
- Verify `NEXT_PUBLIC_API_URL` in both `ui/.env` AND `docker-compose.yml` match
- Rebuild UI: `docker compose build --no-cache openmemory-ui`
- Restart: `docker compose down && docker compose up -d`

**API errors about missing OPENAI_API_KEY:**
- Verify `api/.env` has valid OpenAI API key
- Restart API: `docker compose restart openmemory-mcp`

**No memories showing:**
- Verify `USER` in `api/.env` matches `NEXT_PUBLIC_USER_ID` in `ui/.env`
- Both should be set to the same user ID value

---

## Multi-Attachment Support

### Overview

Memories support multiple attachments via the `attachment_ids` array in metadata. This enables preserving old attachments when memory updates occur through mem0's smart deduplication.

### Data Model

**Metadata Structure:**
```json
{
  "attachment_ids": ["uuid1", "uuid2", "uuid3"],
  "agent_id": "general",
  ...
}
```

### UPDATE Event Handling

When mem0 triggers an UPDATE event (duplicate memory detected), the system:
1. Extracts existing `attachment_ids` from memory metadata
2. Creates new attachment if `attachment_text` provided
3. Merges old and new attachment IDs (deduplicates)
4. Updates both PostgreSQL metadata and Qdrant vector store

**Implementation locations:**
- MCP Server: `api/app/mcp_server.py` (lines 171-199)
- REST API: `api/app/routers/memories.py` (lines 414-448)

### Creating Memories with Multiple Attachments

**Via REST API:**
```bash
# Create memory with new attachment (auto-adds to attachment_ids array)
curl -X POST http://localhost:8765/api/v1/memories/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Memory summary",
    "user_id": "frederik",
    "metadata": {"agent_id": "general"},
    "attachment_text": "Detailed context..."
  }'

# Link to existing attachment (adds to attachment_ids array)
curl -X POST http://localhost:8765/api/v1/memories/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Memory summary",
    "user_id": "frederik",
    "metadata": {"agent_id": "general"},
    "attachment_ids": ["existing-uuid"]
  }'
```

**Via MCP:**
```python
# Create memory with attachment
add_memories(
    text="Summary",
    attachment_text="Full content...",
    metadata={"agent_id": "general"}
)
```

### Getting Multiple Attachments

```bash
# Search returns metadata with attachment_ids array
curl -X POST http://localhost:8765/api/v1/memories/filter \
  -H "Content-Type: application/json" \
  -d '{"user_id": "frederik", "search_query": "python"}'

# Response includes:
{
  "items": [{
    "id": "...",
    "content": "...",
    "metadata_": {
      "attachment_ids": ["uuid1", "uuid2"],
      ...
    }
  }]
}

# Fetch each attachment individually
curl http://localhost:8765/api/v1/attachments/uuid1
curl http://localhost:8765/api/v1/attachments/uuid2
```
