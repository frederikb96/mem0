# MCP List Attachments Tool - Implementation Plan

**Date:** 2025-10-09
**Context:** Adding an MCP tool to efficiently list and filter attachments

## Problem Statement

The user needs an MCP tool to list attachments with filtering capabilities. Key requirements:
- Must be efficient for 10,000+ attachments with 100MB+ content
- Support search by UUID and content
- Support date filtering (created_at, updated_at with from/to dates)
- Must be token-efficient (not return full content)
- Must be fast even if not perfectly accurate
- Should be easy to use and follow common patterns

## Proposed Solution

Create a new MCP tool `list_attachments` that mirrors the backend filter endpoint but with MCP-friendly parameters.

### Tool Signature

```python
@mcp.tool(description="List attachments with optional filtering and pagination. Returns content preview (200 chars) for token efficiency. Use get_attachment(id) to retrieve full content.")
async def list_attachments(
    search_query: Annotated[Optional[str], "Search by content or UUID (partial match). Searches both content and attachment ID."] = None,
    from_date: Annotated[Optional[str], "Filter attachments created/updated after this date. Format: YYYY-MM-DD or ISO 8601 datetime."] = None,
    to_date: Annotated[Optional[str], "Filter attachments created/updated before this date. Format: YYYY-MM-DD or ISO 8601 datetime."] = None,
    date_field: Annotated[str, "Which date field to filter on: 'created_at' or 'updated_at'. Default: created_at."] = "created_at",
    sort_column: Annotated[str, "Sort by 'created_at', 'updated_at', or 'size'. Default: created_at."] = "created_at",
    sort_direction: Annotated[str, "Sort direction: 'asc' or 'desc'. Default: desc."] = "desc",
    page: Annotated[int, "Page number for pagination (1-indexed). Default: 1."] = 1,
    size: Annotated[int, "Number of results per page (max 100). Default: 20."] = 20
) -> str:
```

### Implementation Strategy

#### 1. **Performance Optimizations**

**Content Preview (Critical for Token Efficiency):**
```python
# Return only first 200 chars of content
content_preview = attachment.content[:200] if len(attachment.content) > 200 else attachment.content
```

**Database Query Optimization:**
```python
# Use ILIKE for search (case-insensitive, works with indexes)
query = db.query(Attachment)

if search_query:
    query = query.filter(
        or_(
            Attachment.content.ilike(f"%{search_query}%"),
            cast(Attachment.id, String).ilike(f"%{search_query}%")
        )
    )

# Date filtering using provided field
if from_date:
    date_field_column = Attachment.created_at if date_field == "created_at" else Attachment.updated_at
    from_datetime = parse_date(from_date)  # Parse YYYY-MM-DD or ISO 8601
    query = query.filter(date_field_column >= from_datetime)

if to_date:
    date_field_column = Attachment.created_at if date_field == "created_at" else Attachment.updated_at
    to_datetime = parse_date(to_date)
    query = query.filter(date_field_column <= to_datetime)

# Pagination
total = query.count()
attachments = query.offset((page - 1) * size).limit(size).all()
```

**Search Performance:**
- PostgreSQL ILIKE is reasonably fast for prefix searches
- For 10k+ attachments with 100MB content, searching content will be slow
- **Trade-off**: Accept slower search on large content vs complexity of full-text search
- **Mitigation**: Use content preview for search? NO - user may want to search full content
- **Recommendation**: Use ILIKE for now, can add full-text search index later if needed

#### 2. **Date Parsing Helper**

```python
def parse_date(date_str: str) -> datetime:
    """Parse YYYY-MM-DD or ISO 8601 datetime string."""
    try:
        # Try ISO 8601 first (e.g., "2025-10-09T10:30:00Z")
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        # Try YYYY-MM-DD format
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD or ISO 8601.")
```

#### 3. **Response Format**

```json
{
  "results": [
    {
      "id": "uuid-here",
      "content": "First 200 chars of content...",
      "content_length": 125678,
      "created_at": "2025-10-09T10:30:00Z",
      "updated_at": "2025-10-09T11:45:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "size": 20,
    "total": 147,
    "pages": 8
  },
  "filters": {
    "search_query": "kubernetes",
    "from_date": "2025-10-01",
    "to_date": "2025-10-09",
    "date_field": "created_at",
    "sort_column": "created_at",
    "sort_direction": "desc"
  }
}
```

#### 4. **Token Efficiency Analysis**

**Scenario: 10,000 attachments with 100MB average content**

Without preview (returning full content):
- 20 results × 100MB = ~2GB of text → IMPOSSIBLE
- Would exceed all token limits

With 200-char preview:
- 20 results × 200 chars = ~4,000 chars
- Plus metadata: ~500 chars
- Total: ~4,500 chars per page
- **Token cost**: ~1,125 tokens per page (assuming 4 chars/token)

**Result**: Preview strategy makes this viable for MCP usage.

#### 5. **Usage Examples**

```python
# Example 1: List recent attachments
await list_attachments(
    sort_column="created_at",
    sort_direction="desc",
    size=10
)

# Example 2: Search for specific content
await list_attachments(
    search_query="kubernetes config",
    size=20
)

# Example 3: Find attachments by partial UUID
await list_attachments(
    search_query="a1b2c3",  # Partial UUID
    size=5
)

# Example 4: Date range filter
await list_attachments(
    from_date="2025-10-01",
    to_date="2025-10-09",
    date_field="created_at",
    size=50
)

# Example 5: Find large recent attachments
await list_attachments(
    sort_column="size",
    sort_direction="desc",
    size=10
)
```

## Implementation Checklist

- [ ] Add `parse_date()` helper function to mcp_server.py
- [ ] Implement `list_attachments` MCP tool following the signature above
- [ ] Reuse filter logic from `POST /api/v1/attachments/filter` endpoint
- [ ] Return content preview (200 chars) for token efficiency
- [ ] Include pagination metadata in response
- [ ] Include applied filters in response for transparency
- [ ] Add error handling for invalid date formats
- [ ] Add validation: max page size = 100
- [ ] Test with various filter combinations
- [ ] Create test script to verify functionality
- [ ] Document in MCP tool description how to get full content (use get_attachment)

## Testing Strategy

Create test script `/home/frederik/Programming/mem0/.claude/tests/11-test-mcp-list-attachments.py`:

```python
# Test cases:
1. List all attachments (no filters)
2. Search by content substring
3. Search by partial UUID
4. Filter by date range (created_at)
5. Filter by date range (updated_at)
6. Combined search + date filter
7. Sort by size (desc)
8. Pagination (page 2, size 5)
9. Invalid date format (should error)
10. Large page size (should cap at 100)
11. Empty results
12. Verify content preview is exactly 200 chars for large attachments
```

## Performance Considerations

### Current Limitations

1. **Content Search Speed**: ILIKE on large text columns can be slow
   - **Impact**: Search queries may take 1-5 seconds for 10k+ attachments with large content
   - **Acceptable**: Yes for MCP usage (not high-frequency)
   - **Future Optimization**: Add PostgreSQL full-text search index if needed

2. **Memory Usage**: Loading 20-100 results with 200-char previews
   - **Impact**: Minimal (~4-20KB per request)
   - **Acceptable**: Yes

3. **Database Load**: Count + fetch queries per request
   - **Impact**: Low (indexed queries)
   - **Acceptable**: Yes

### When to Optimize Further

If users report slow searches (>5 seconds), consider:
1. Add PostgreSQL full-text search index (GIN index on content)
2. Add dedicated search column with preprocessed/normalized content
3. Add Redis caching for common searches
4. Add Elasticsearch for advanced search (overkill for now)

**Recommendation**: Implement basic version first, optimize only if needed.

## Alternative Approaches Considered

### Option 1: Full-text Search with PostgreSQL GIN Index
**Pros**: Faster search on large content
**Cons**: More complex, requires migration, heavier database
**Decision**: DEFER - implement if ILIKE proves too slow

### Option 2: Return Only Attachment IDs (No Preview)
**Pros**: Minimal token usage
**Cons**: User can't see what they're getting, poor UX
**Decision**: REJECT - preview is essential for usability

### Option 3: Elasticsearch Integration
**Pros**: Lightning-fast search, advanced features
**Cons**: Adds infrastructure complexity, overkill for current scale
**Decision**: REJECT - too complex for current needs

## Conclusion

The proposed `list_attachments` MCP tool provides:
- ✅ Efficient token usage (200-char preview)
- ✅ Fast enough for 10k+ attachments (with acceptable trade-offs)
- ✅ Flexible filtering (search, dates, sorting)
- ✅ Easy to use (follows common patterns)
- ✅ Pagination support
- ✅ Room for future optimization if needed

**Recommendation**: Implement this solution and gather user feedback before considering more complex optimizations.
