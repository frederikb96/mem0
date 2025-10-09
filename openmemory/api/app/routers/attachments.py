import os
from typing import Optional
from uuid import UUID, uuid4

from app.database import get_db
from app.models import Attachment
from app.schemas import AttachmentCreate, AttachmentResponse, AttachmentUpdate
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/attachments", tags=["attachments"])

# Get size limit from environment variable (default: 100MB)
ATTACHMENT_MAX_SIZE_MB = int(os.getenv("ATTACHMENT_MAX_SIZE_MB", "100"))
ATTACHMENT_MAX_SIZE_BYTES = ATTACHMENT_MAX_SIZE_MB * 1024 * 1024


def validate_content_size(content: str) -> None:
    """Validate that content size doesn't exceed the configured limit."""
    content_size = len(content.encode('utf-8'))
    if content_size > ATTACHMENT_MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Content size ({content_size / 1024 / 1024:.2f}MB) exceeds maximum allowed size ({ATTACHMENT_MAX_SIZE_MB}MB)"
        )


# Note: Defined twice to accept both with and without trailing slash
@router.post("", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def create_attachment(
    attachment: AttachmentCreate,
    db: Session = Depends(get_db)
):
    """Create a new attachment with optional ID (auto-generated if not provided)."""
    # Validate content size
    validate_content_size(attachment.content)

    # Generate ID if not provided
    attachment_id = attachment.id if attachment.id else uuid4()

    # Check if ID already exists
    existing = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Attachment with ID {attachment_id} already exists"
        )

    # Create attachment
    db_attachment = Attachment(
        id=attachment_id,
        content=attachment.content
    )
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)

    return db_attachment


@router.get("/{attachment_id}", response_model=AttachmentResponse)
async def get_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db)
):
    """Get an attachment by ID."""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment with ID {attachment_id} not found"
        )

    return attachment


@router.put("/{attachment_id}", response_model=AttachmentResponse)
async def update_attachment(
    attachment_id: UUID,
    attachment_update: AttachmentUpdate,
    db: Session = Depends(get_db)
):
    """Update an attachment's content."""
    # Validate content size
    validate_content_size(attachment_update.content)

    # Find attachment
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment with ID {attachment_id} not found"
        )

    # Update content
    attachment.content = attachment_update.content
    db.commit()
    db.refresh(attachment)

    return attachment


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete an attachment (idempotent - returns 204 even if not found)."""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()

    if attachment:
        db.delete(attachment)
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


class FilterAttachmentsRequest(BaseModel):
    page: int = 1
    size: int = 10
    search_query: Optional[str] = None
    sort_column: Optional[str] = None
    sort_direction: Optional[str] = None
    from_date: Optional[int] = None
    to_date: Optional[int] = None
    timeout: Optional[int] = 5  # Query timeout in seconds (default: 5)


class AttachmentListItem(BaseModel):
    id: str
    content: str  # Preview (first 200 chars)
    content_length: int
    created_at: int  # Unix timestamp
    updated_at: int  # Unix timestamp

    model_config = {"from_attributes": True}


class FilterAttachmentsResponse(BaseModel):
    items: list[AttachmentListItem]
    total: int
    page: int
    size: int
    pages: int


@router.post("/filter", response_model=FilterAttachmentsResponse)
async def filter_attachments(
    request: FilterAttachmentsRequest,
    db: Session = Depends(get_db)
):
    """
    List attachments with pagination, search, and sorting.

    Search query matches:
    - Attachment content (substring, case-insensitive)
    - Attachment ID (exact or partial UUID match)
    """
    from sqlalchemy import or_, cast, String, text
    from datetime import datetime

    # Build base query with timeout (only for PostgreSQL)
    # Note: SQLite doesn't support statement timeout, so this only works with PostgreSQL
    try:
        # Check if we're using PostgreSQL
        if 'postgresql' in str(db.bind.url):
            timeout_ms = request.timeout * 1000 if request.timeout else 5000
            db.execute(text(f"SET LOCAL statement_timeout = {timeout_ms}"))
    except Exception:
        # Silently ignore if timeout setting fails (e.g., with SQLite)
        pass

    query = db.query(Attachment)

    # Apply search filter (content OR UUID)
    if request.search_query:
        query = query.filter(
            or_(
                Attachment.content.ilike(f"%{request.search_query}%"),
                cast(Attachment.id, String).ilike(f"%{request.search_query}%")
            )
        )

    # Apply date filters
    if request.from_date:
        from_datetime = datetime.fromtimestamp(request.from_date)
        query = query.filter(Attachment.created_at >= from_datetime)

    if request.to_date:
        to_datetime = datetime.fromtimestamp(request.to_date)
        query = query.filter(Attachment.created_at <= to_datetime)

    # Get total count before pagination
    total = query.count()

    # Apply sorting
    if request.sort_column and request.sort_direction:
        sort_direction = request.sort_direction.lower()
        if sort_direction not in ['asc', 'desc']:
            raise HTTPException(status_code=400, detail="Invalid sort direction")

        sort_mapping = {
            'created_at': Attachment.created_at,
            'updated_at': Attachment.updated_at,
            'size': Attachment.content  # Will sort by length
        }

        if request.sort_column not in sort_mapping:
            raise HTTPException(status_code=400, detail="Invalid sort column")

        sort_field = sort_mapping[request.sort_column]

        if request.sort_column == 'size':
            # Sort by content length
            from sqlalchemy import func
            if sort_direction == 'desc':
                query = query.order_by(func.length(Attachment.content).desc())
            else:
                query = query.order_by(func.length(Attachment.content).asc())
        else:
            if sort_direction == 'desc':
                query = query.order_by(sort_field.desc())
            else:
                query = query.order_by(sort_field.asc())
    else:
        # Default sorting: newest first
        query = query.order_by(Attachment.created_at.desc())

    # Calculate pages
    pages = (total + request.size - 1) // request.size if total > 0 else 1

    # Apply pagination
    attachments = query.offset((request.page - 1) * request.size).limit(request.size).all()

    # Build response items with preview content
    items = [
        AttachmentListItem(
            id=str(a.id),
            content=a.content[:200] if len(a.content) > 200 else a.content,  # Preview
            content_length=len(a.content),
            created_at=int(a.created_at.timestamp()),
            updated_at=int(a.updated_at.timestamp())
        )
        for a in attachments
    ]

    return FilterAttachmentsResponse(
        items=items,
        total=total,
        page=request.page,
        size=request.size,
        pages=pages
    )
