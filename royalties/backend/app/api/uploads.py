"""File upload endpoints."""

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.models.upload import Upload
from app.models.user import User
from app.schemas.upload import UploadResponse
from app.services.upload_service import process_upload

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

ALLOWED = set(settings.allowed_extensions.split(","))
MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.post("/", response_model=UploadResponse, status_code=201)
async def upload_file(
    file: UploadFile,
    user_id: Annotated[uuid.UUID, Form()],
    db: DbSession,
) -> Upload:
    """Upload a royalty statement file for validation."""
    # Validate user exists
    result = await db.execute(select(User).where(User.id == user_id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="User not found")

    # Validate file is present
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Validate extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Accepted: {', '.join(sorted(ALLOWED))}",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb}MB",
        )

    # Save to disk
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    stored_name = f"{file_id}.{ext}"
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(content)

    # Parse to count rows
    row_count = await process_upload(stored_path, ext)

    # Record in database
    upload = Upload(
        id=file_id,
        user_id=user_id,
        filename=file.filename,
        file_path=str(stored_path),
        file_format=ext,
        row_count=row_count,
    )
    db.add(upload)
    await db.flush()
    await db.refresh(upload)
    return upload


@router.get("/{upload_id}", response_model=UploadResponse)
async def get_upload(upload_id: uuid.UUID, db: DbSession) -> Upload:
    """Get details of a previously uploaded file."""
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalars().first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload
