import os
from uuid import UUID, uuid4

from app.database import get_db
from app.models import Attachment
from app.schemas import AttachmentCreate, AttachmentResponse, AttachmentUpdate
from fastapi import APIRouter, Depends, HTTPException, Response, status
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
