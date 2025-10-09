# Attachments List View Implementation Plan

**Date:** 2025-10-09
**Status:** Planning Phase
**Feasibility:** ✅ **HIGHLY FEASIBLE** with minimal refactoring

---

## Executive Summary

After analyzing the codebase, implementing a memory-style list view for attachments is **very straightforward** and requires **minimal refactoring**. The existing architecture is clean, modular, and perfectly suited for code reuse.

### Key Findings

✅ **Clean Architecture** - Next.js 15 + React 19 + Redux Toolkit + Radix UI
✅ **Modular Components** - Easy to extract and reuse patterns
✅ **Type Safety** - Full TypeScript support throughout
✅ **Consistent Patterns** - All features follow same structure
✅ **API Parity** - Backend already supports all needed operations

**Recommendation:** Proceed with implementation - no architectural changes needed.

---

## Current Architecture Analysis

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | Next.js 15 (App Router) | Server-side rendering, routing |
| **UI Library** | Radix UI (shadcn/ui) | Accessible, unstyled components |
| **State Management** | Redux Toolkit | Global state, selections |
| **Styling** | TailwindCSS | Utility-first CSS |
| **HTTP Client** | Axios | REST API communication |
| **Type System** | TypeScript | Type safety |

### Current Memories View Structure

```
/memories (page)
├── MemoryFilters (search + actions + filters)
│   ├── Search input with debounce
│   ├── FilterComponent (apps, categories)
│   ├── Clear Filters button
│   └── Bulk Actions dropdown (archive, pause, delete)
├── MemoriesSection (data fetching + layout)
│   ├── useMemoriesApi hook
│   ├── URL params management (page, size, search)
│   ├── MemoryTable (table display)
│   │   ├── Checkbox column (selection)
│   │   ├── Memory content column
│   │   ├── Categories column
│   │   ├── Source App column
│   │   ├── Created On column
│   │   └── Actions column (dropdown menu)
│   ├── PageSizeSelector (10, 25, 50, 100)
│   ├── Results counter
│   └── MemoryPagination (page navigation)
└── UpdateMemory Dialog (edit modal)
```

### Backend API Support

#### Current Attachments REST API

| Endpoint | Method | Pagination | Filtering | Sorting | Status |
|----------|--------|-----------|-----------|---------|--------|
| `/api/v1/attachments` | POST | - | - | - | ✅ Create |
| `/api/v1/attachments/{id}` | GET | - | - | - | ✅ Get single |
| `/api/v1/attachments/{id}` | PUT | - | - | - | ✅ Update |
| `/api/v1/attachments/{id}` | DELETE | - | - | - | ✅ Delete |
| `/api/v1/attachments/filter` | POST | ❌ No | ❌ No | ❌ No | **❌ MISSING** |

**Missing:** List/filter endpoint similar to `/api/v1/memories/filter`

---

## Proposed Solution

### Overview

Reuse the memory view pattern with attachment-specific adaptations:
- **Table view** instead of dialog-based
- **Search by content AND UUID** instead of ID-only search
- **Pagination + sorting** like memories
- **Bulk actions** (delete selected)
- **Create button** in filter bar

### Architecture Decision: Shared vs Specialized Components

**Option A: Generic Components (Higher Refactoring)**
- Create `<GenericTable>`, `<GenericFilters>`, etc.
- Pass configuration objects
- Single component handles both memories and attachments

**Option B: Specialized Components (Minimal Refactoring)** ⭐ **RECOMMENDED**
- Copy memory components → rename to attachment equivalents
- Adapt only where needed (columns, actions, API calls)
- Keep specific logic in each component

**Recommendation:** **Option B** - Less coupling, faster development, easier maintenance

### Why Option B is Better

1. **Faster Development** - Copy, rename, adapt (1-2 days vs 3-5 days for generics)
2. **Simpler Code** - No complex configuration objects or conditional rendering
3. **Easier Maintenance** - Changes to memories don't affect attachments
4. **Type Safety** - Specific types for each domain (Memory vs Attachment)
5. **Future Flexibility** - Easy to diverge features later

---

## Implementation Plan

### Phase 1: Backend API (Required First)

#### 1. New REST Endpoint: `/api/v1/attachments/filter`

**File:** `openmemory/api/app/routers/attachments.py`

**Functionality:**
```python
@router.post("/filter")
async def filter_attachments(
    page: int = 1,
    size: int = 10,
    search_query: Optional[str] = None,  # Search content OR UUID
    sort_column: Optional[str] = "created_at",
    sort_direction: Optional[str] = "desc",
    from_date: Optional[int] = None,
    to_date: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List attachments with pagination, search, and sorting.

    Search query matches:
    - Attachment content (substring, case-insensitive)
    - Attachment ID (exact or partial UUID match)
    """
    query = db.query(Attachment)

    # Search filter
    if search_query:
        query = query.filter(
            or_(
                Attachment.content.ilike(f"%{search_query}%"),
                Attachment.id.cast(String).ilike(f"%{search_query}%")
            )
        )

    # Date range filters
    if from_date:
        query = query.filter(Attachment.created_at >= datetime.fromtimestamp(from_date))
    if to_date:
        query = query.filter(Attachment.created_at <= datetime.fromtimestamp(to_date))

    # Total count
    total = query.count()

    # Sorting
    sort_field = getattr(Attachment, sort_column, Attachment.created_at)
    if sort_direction == "desc":
        query = query.order_by(sort_field.desc())
    else:
        query = query.order_by(sort_field.asc())

    # Pagination
    attachments = query.offset((page - 1) * size).limit(size).all()

    return {
        "items": [
            {
                "id": str(a.id),
                "content": a.content[:200],  # Preview only (first 200 chars)
                "content_length": len(a.content),
                "created_at": a.created_at.isoformat(),
                "updated_at": a.updated_at.isoformat(),
            }
            for a in attachments
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size
    }
```

**Response Schema:**
```typescript
interface AttachmentListItem {
  id: string;
  content: string;           // First 200 chars (preview)
  content_length: number;    // Full length in bytes
  created_at: string;        // ISO format
  updated_at: string;        // ISO format
}

interface AttachmentFilterResponse {
  items: AttachmentListItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
```

---

### Phase 2: Frontend Components

#### File Structure

```
ui/app/attachments/
├── page.tsx                          # Main page (routing + layout)
├── components/
│   ├── AttachmentFilters.tsx        # Search + Create button + bulk actions
│   ├── AttachmentsSection.tsx       # Data fetching + pagination controls
│   ├── AttachmentTable.tsx          # Table display with columns
│   ├── AttachmentPagination.tsx     # Page navigation (reuse from memories)
│   ├── PageSizeSelector.tsx         # Reuse from memories
│   └── AttachmentDialog.tsx         # Existing (view/edit/create)
```

#### Redux Store

**File:** `ui/store/attachmentsSlice.ts` (new)

```typescript
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface AttachmentListItem {
  id: string;
  content: string;           // Preview (200 chars)
  content_length: number;
  created_at: string;
  updated_at: string;
}

interface AttachmentsState {
  attachments: AttachmentListItem[];
  selectedAttachmentIds: string[];
  status: 'idle' | 'loading' | 'succeeded' | 'failed';
  error: string | null;
}

const initialState: AttachmentsState = {
  attachments: [],
  selectedAttachmentIds: [],
  status: 'idle',
  error: null,
};

const attachmentsSlice = createSlice({
  name: 'attachments',
  initialState,
  reducers: {
    setAttachmentsSuccess: (state, action: PayloadAction<AttachmentListItem[]>) => {
      state.status = 'succeeded';
      state.attachments = action.payload;
      state.error = null;
    },
    selectAttachment: (state, action: PayloadAction<string>) => {
      if (!state.selectedAttachmentIds.includes(action.payload)) {
        state.selectedAttachmentIds.push(action.payload);
      }
    },
    deselectAttachment: (state, action: PayloadAction<string>) => {
      state.selectedAttachmentIds = state.selectedAttachmentIds.filter(
        id => id !== action.payload
      );
    },
    selectAllAttachments: (state) => {
      state.selectedAttachmentIds = state.attachments.map(a => a.id);
    },
    clearSelection: (state) => {
      state.selectedAttachmentIds = [];
    },
  },
});

export const {
  setAttachmentsSuccess,
  selectAttachment,
  deselectAttachment,
  selectAllAttachments,
  clearSelection,
} = attachmentsSlice.actions;

export default attachmentsSlice.reducer;
```

#### Custom Hook Updates

**File:** `ui/hooks/useAttachmentsApi.ts` (extend existing)

```typescript
// Add new function to existing hook
const fetchAttachments = useCallback(async (
  query?: string,
  page: number = 1,
  size: number = 10,
  sortColumn: string = "created_at",
  sortDirection: "asc" | "desc" = "desc"
): Promise<{ attachments: AttachmentListItem[], total: number, pages: number }> => {
  setIsLoading(true);
  setError(null);
  try {
    const response = await axios.post<AttachmentFilterResponse>(
      `${URL}/api/v1/attachments/filter`,
      {
        page,
        size,
        search_query: query,
        sort_column: sortColumn,
        sort_direction: sortDirection,
      }
    );
    setIsLoading(false);
    return {
      attachments: response.data.items,
      total: response.data.total,
      pages: response.data.pages
    };
  } catch (err: any) {
    const errorMessage = err.message || 'Failed to fetch attachments';
    setError(errorMessage);
    setIsLoading(false);
    throw new Error(errorMessage);
  }
}, [URL]);

// Add to return object
return {
  fetchAttachment,
  fetchAttachments,  // NEW
  createAttachment,
  updateAttachment,
  deleteAttachment,
  isLoading,
  error,
};
```

#### Component: AttachmentTable

**File:** `ui/app/attachments/components/AttachmentTable.tsx`

```typescript
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { MoreHorizontal, Eye, Edit, Trash2 } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "@/store/store";
import { selectAttachment, deselectAttachment, selectAllAttachments, clearSelection } from "@/store/attachmentsSlice";
import { formatDate } from "@/lib/helpers";

export function AttachmentTable() {
  const dispatch = useDispatch();
  const attachments = useSelector((state: RootState) => state.attachments.attachments);
  const selectedIds = useSelector((state: RootState) => state.attachments.selectedAttachmentIds);

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      dispatch(selectAllAttachments());
    } else {
      dispatch(clearSelection());
    }
  };

  const handleSelectAttachment = (id: string, checked: boolean) => {
    if (checked) {
      dispatch(selectAttachment(id));
    } else {
      dispatch(deselectAttachment(id));
    }
  };

  const isAllSelected = attachments.length > 0 && selectedIds.length === attachments.length;

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow className="bg-zinc-800 hover:bg-zinc-800">
            <TableHead className="w-[50px] pl-4">
              <Checkbox
                checked={isAllSelected}
                onCheckedChange={handleSelectAll}
              />
            </TableHead>
            <TableHead className="border-zinc-700 w-[300px]">ID</TableHead>
            <TableHead className="border-zinc-700">Content Preview</TableHead>
            <TableHead className="border-zinc-700 w-[120px]">Size</TableHead>
            <TableHead className="border-zinc-700 w-[140px]">Created</TableHead>
            <TableHead className="border-zinc-700 w-[140px]">Updated</TableHead>
            <TableHead className="text-right border-zinc-700">
              <MoreHorizontal className="h-4 w-4 mr-2" />
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {attachments.map((attachment) => (
            <TableRow key={attachment.id} className="hover:bg-zinc-900/50">
              <TableCell className="pl-4">
                <Checkbox
                  checked={selectedIds.includes(attachment.id)}
                  onCheckedChange={(checked) =>
                    handleSelectAttachment(attachment.id, checked as boolean)
                  }
                />
              </TableCell>
              <TableCell className="font-mono text-xs text-zinc-400">
                {attachment.id.substring(0, 8)}...
              </TableCell>
              <TableCell className="max-w-[400px] truncate">
                {attachment.content}
              </TableCell>
              <TableCell className="text-center">
                {(attachment.content_length / 1024).toFixed(1)} KB
              </TableCell>
              <TableCell className="text-center">
                {formatDate(attachment.created_at)}
              </TableCell>
              <TableCell className="text-center">
                {formatDate(attachment.updated_at)}
              </TableCell>
              <TableCell className="text-right">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="bg-zinc-900 border-zinc-800">
                    <DropdownMenuItem onClick={() => handleView(attachment.id)}>
                      <Eye className="mr-2 h-4 w-4" />
                      View
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleEdit(attachment.id)}>
                      <Edit className="mr-2 h-4 w-4" />
                      Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleDelete(attachment.id)}
                      className="text-red-500"
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

#### Component: AttachmentFilters

**File:** `ui/app/attachments/components/AttachmentFilters.tsx`

```typescript
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { FiTrash2 } from "react-icons/fi";
import { GoPlus } from "react-icons/go";
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "@/store/store";
import { clearSelection } from "@/store/attachmentsSlice";
import { useAttachmentsApi } from "@/hooks/useAttachmentsApi";
import { useRouter, useSearchParams } from "next/navigation";
import { debounce } from "lodash";
import { useRef } from "react";

export function AttachmentFilters() {
  const dispatch = useDispatch();
  const selectedIds = useSelector((state: RootState) => state.attachments.selectedAttachmentIds);
  const { deleteAttachment } = useAttachmentsApi();
  const router = useRouter();
  const searchParams = useSearchParams();
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDeleteSelected = async () => {
    if (!confirm(`Delete ${selectedIds.length} selected attachments?`)) return;

    try {
      await Promise.all(selectedIds.map(id => deleteAttachment(id)));
      dispatch(clearSelection());
      // Refresh list
      router.refresh();
    } catch (error) {
      console.error("Failed to delete attachments:", error);
    }
  };

  const handleSearch = debounce(async (query: string) => {
    router.push(`/attachments?search=${query}`);
  }, 500);

  const handleCreate = () => {
    // Open create dialog (implementation depends on dialog management)
    router.push("/attachments?create=true");
  };

  return (
    <div className="flex flex-col md:flex-row gap-4 mb-4">
      <div className="relative flex-1">
        <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
        <Input
          ref={inputRef}
          placeholder="Search by content or UUID..."
          className="pl-8 bg-zinc-950 border-zinc-800 max-w-[500px]"
          onChange={(e) => handleSearch(e.target.value)}
        />
      </div>
      <div className="flex gap-2">
        <Button
          onClick={handleCreate}
          className="bg-primary hover:bg-primary/90"
        >
          <GoPlus className="mr-2" />
          Create Attachment
        </Button>
        {selectedIds.length > 0 && (
          <Button
            variant="destructive"
            onClick={handleDeleteSelected}
          >
            <FiTrash2 className="mr-2 h-4 w-4" />
            Delete Selected ({selectedIds.length})
          </Button>
        )}
      </div>
    </div>
  );
}
```

---

## Implementation Checklist

### Backend (Required First)

- [ ] **1.1** Add `/api/v1/attachments/filter` endpoint in `attachments.py`
- [ ] **1.2** Support search by content (substring) AND UUID (partial match)
- [ ] **1.3** Support pagination (page, size)
- [ ] **1.4** Support sorting (created_at, updated_at, size)
- [ ] **1.5** Support date range filters (from_date, to_date)
- [ ] **1.6** Return preview content (first 200 chars) + full length
- [ ] **1.7** Write backend test for filter endpoint

### Frontend Redux

- [ ] **2.1** Create `attachmentsSlice.ts` in `ui/store/`
- [ ] **2.2** Add slice to root store configuration
- [ ] **2.3** Implement selection actions (select, deselect, selectAll, clear)
- [ ] **2.4** Implement data loading actions

### Frontend API Hook

- [ ] **3.1** Extend `useAttachmentsApi.ts` with `fetchAttachments` function
- [ ] **3.2** Add bulk delete function (delete multiple IDs)
- [ ] **3.3** Integrate with Redux dispatch for state updates

### Frontend Components

- [ ] **4.1** Create `AttachmentTable.tsx` (table display)
- [ ] **4.2** Create `AttachmentFilters.tsx` (search + create + bulk actions)
- [ ] **4.3** Create `AttachmentsSection.tsx` (data fetching + layout)
- [ ] **4.4** Reuse `MemoryPagination.tsx` (no changes needed)
- [ ] **4.5** Reuse `PageSizeSelector.tsx` (no changes needed)
- [ ] **4.6** Update `AttachmentDialog.tsx` to work with new page layout

### Page Integration

- [ ] **5.1** Update `page.tsx` to use new table layout
- [ ] **5.2** Implement URL parameter management (page, size, search)
- [ ] **5.3** Add dialog state management (view/edit/create modes)
- [ ] **5.4** Handle navigation between list and detail views

### Testing

- [ ] **6.1** Test pagination (10, 25, 50, 100 per page)
- [ ] **6.2** Test search (content substring)
- [ ] **6.3** Test search (UUID partial match)
- [ ] **6.4** Test sorting (created_at, updated_at)
- [ ] **6.5** Test bulk selection + delete
- [ ] **6.6** Test create attachment flow
- [ ] **6.7** Test view/edit attachment from list
- [ ] **6.8** Test mobile responsive layout

---

## Estimated Effort

| Phase | Complexity | Time Estimate |
|-------|-----------|---------------|
| **Backend API** | Low | 2-3 hours |
| **Redux Store** | Low | 1 hour |
| **API Hook** | Low | 1 hour |
| **Components** | Medium | 4-5 hours |
| **Integration** | Low | 1-2 hours |
| **Testing** | Medium | 2-3 hours |
| **Total** | - | **11-15 hours** (1-2 days) |

---

## Risks and Mitigations

### Risk 1: Content Preview Performance
**Issue:** Large attachments (100MB) could slow down list queries
**Mitigation:** Only return first 200 chars + content length, not full content

### Risk 2: Search Performance on Large Datasets
**Issue:** ILIKE search on content could be slow with many attachments
**Mitigation:** Add database index on content column (GIN index for PostgreSQL)

### Risk 3: Mobile Layout
**Issue:** Table with many columns may not fit on mobile
**Mitigation:** Use responsive design with horizontal scroll or card layout on mobile

### Risk 4: Bulk Delete Performance
**Issue:** Deleting many attachments in parallel could timeout
**Mitigation:** Implement backend batch delete endpoint (future enhancement)

---

## Future Enhancements (Out of Scope)

- **Advanced Filters:** Filter by size range, date modified
- **Bulk Edit:** Update multiple attachments at once
- **Export:** Download attachments as files
- **Preview Modes:** Syntax highlighting for code, markdown rendering
- **References:** Show which memories reference each attachment
- **Usage Analytics:** Track attachment access patterns

---

## Conclusion

**Recommendation:** ✅ **PROCEED WITH IMPLEMENTATION**

The proposed solution is:
- ✅ **Feasible** - No architectural changes needed
- ✅ **Low Risk** - Reuses proven patterns
- ✅ **Fast Development** - 1-2 days estimated
- ✅ **Maintainable** - Clean separation of concerns
- ✅ **Scalable** - Pagination handles large datasets

Next step: Get approval and start with Phase 1 (Backend API endpoint).
