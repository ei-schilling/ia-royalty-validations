"""File upload endpoints."""

import csv
import io
import json
import uuid
from pathlib import Path
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import CurrentUser
from app.config import settings
from app.db.database import get_db
from app.models.upload import Upload
from app.schemas.upload import UploadHistoryItem, UploadResponse
from app.services.upload_service import process_upload
from app.services.archive_service import is_archive, extract_archive

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

ALLOWED = set(settings.allowed_extensions.split(","))
MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.post("/", response_model=UploadResponse, status_code=201)
async def upload_file(
    file: UploadFile,
    current_user: CurrentUser,
    db: DbSession,
) -> Upload:
    """Upload a royalty statement file for validation."""
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
        user_id=current_user.id,
        filename=file.filename,
        file_path=str(stored_path),
        file_format=ext,
        row_count=row_count,
    )
    db.add(upload)
    await db.flush()
    await db.refresh(upload)
    return upload


@router.get("/", response_model=list[UploadHistoryItem])
async def list_uploads(
    current_user: CurrentUser,
    db: DbSession,
) -> list[Upload]:
    """List all uploads for the current user, newest first, with validation runs."""
    result = await db.execute(
        select(Upload)
        .where(Upload.user_id == current_user.id)
        .options(selectinload(Upload.validation_runs))
        .order_by(Upload.uploaded_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


@router.get("/{upload_id}", response_model=UploadResponse)
async def get_upload(
    upload_id: uuid.UUID, _current_user: CurrentUser, db: DbSession
) -> Upload:
    """Get details of a previously uploaded file."""
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalars().first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    return upload


MAX_PREVIEW_ROWS = 50_000


@router.get("/{upload_id}/content")
async def get_upload_content(
    upload_id: uuid.UUID, _current_user: CurrentUser, db: DbSession
) -> JSONResponse:
    """Return the parsed content of an uploaded file for preview purposes.

    Returns JSON with ``format``, ``headers`` (for tabular), ``rows`` (list of
    list[str]), and ``raw`` (first 500 KB of text) fields.
    """
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalars().first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    file_path = Path(upload.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File no longer exists on disk")

    raw_bytes = file_path.read_bytes()
    ext = upload.file_format.lower()

    headers: list[str] = []
    rows: list[list[str]] = []
    raw_text = ""

    if ext == "csv":
        text = raw_bytes.decode("utf-8", errors="replace")
        raw_text = text[:500_000]
        reader = csv.reader(io.StringIO(text))
        for i, row in enumerate(reader):
            if i == 0:
                headers = row
            else:
                rows.append(row)
            if i >= MAX_PREVIEW_ROWS:
                break

    elif ext == "json":
        text = raw_bytes.decode("utf-8", errors="replace")
        raw_text = text[:500_000]
        try:
            obj = json.loads(text)
            if isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict):
                headers = list(obj[0].keys())
                for item in obj[:MAX_PREVIEW_ROWS]:
                    rows.append([str(item.get(h, "")) for h in headers])
            elif isinstance(obj, dict):
                # Flat dict — display as key/value
                headers = ["Key", "Value"]
                for k, v in list(obj.items())[:MAX_PREVIEW_ROWS]:
                    rows.append([str(k), str(v)])
        except json.JSONDecodeError:
            pass

    elif ext in ("xlsx", "xls"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
            ws = wb.active
            if ws is not None:
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    str_row = [str(c) if c is not None else "" for c in row]
                    if i == 0:
                        headers = str_row
                    else:
                        rows.append(str_row)
                    if i >= MAX_PREVIEW_ROWS:
                        break
            wb.close()
        except Exception:
            pass
        # Generate text representation
        lines = [",".join(headers)] + [",".join(r) for r in rows[:50]]
        raw_text = "\n".join(lines)

    elif ext == "xml":
        try:
            import xml.etree.ElementTree as ET
            # Detect encoding from XML declaration first, fall back to UTF-8
            for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1", "iso-8859-1"):
                try:
                    text = raw_bytes.decode(enc)
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            else:
                text = raw_bytes.decode("latin-1", errors="replace")
            root = ET.fromstring(text)
            # Pretty-print using ET.indent (Python 3.9+)
            try:
                ET.indent(root, space="  ")
            except AttributeError:
                pass  # Python < 3.9 fallback — use raw text
            pretty = ET.tostring(root, encoding="unicode", xml_declaration=False)
            raw_text = pretty[:500_000]
        except Exception:
            raw_text = raw_bytes.decode("utf-8", errors="replace")[:500_000]

    elif ext == "pdf":
        try:
            import pdfplumber
            pages: list[str] = []
            with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        pages.append(t)
                    if len("\n".join(pages)) > 500_000:
                        break
            raw_text = "\n".join(pages)[:500_000]
        except Exception:
            raw_text = "(Could not extract text from PDF)"
    else:
        raw_text = raw_bytes.decode("utf-8", errors="replace")[:500_000]

    return JSONResponse({
        "format": ext,
        "filename": upload.filename,
        "headers": headers,
        "rows": rows,
        "raw": raw_text,
        "total_rows": upload.row_count,
    })


@router.get("/{upload_id}/file")
async def get_upload_file(
    upload_id: uuid.UUID,
    db: DbSession,
    token: str | None = None,
):
    """Serve the raw uploaded file (used for PDF preview in iframe).

    Accepts a ``?token=`` query param for iframe/embed use (iframes can't send
    Authorization headers).
    """
    from fastapi.responses import Response
    from jose import JWTError, jwt as jose_jwt

    if not token:
        raise HTTPException(status_code=401, detail="Token query parameter required")

    try:
        payload = jose_jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalars().first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    file_path = Path(upload.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File no longer exists on disk")

    media_types = {
        "pdf": "application/pdf",
        "csv": "text/csv",
        "json": "application/json",
        "xml": "application/xml",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
    }
    media_type = media_types.get(upload.file_format.lower(), "application/octet-stream")

    content = file_path.read_bytes()
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": "inline",
            "Content-Length": str(len(content)),
        },
    )


@router.post("/batch", status_code=201)
async def upload_batch(
    files: List[UploadFile],
    current_user: CurrentUser,
    db: DbSession,
) -> JSONResponse:
    """Upload multiple files in a single batch request.

    Supports compressed archives (zip, tar, tar.gz, rar). Each archive is
    extracted and its inner files are processed individually.
    Returns a batch_id and the list of created Upload records.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Increase max size for archives (200 MB)
    archive_max = 200 * 1024 * 1024

    batch_id = str(uuid.uuid4())
    uploads: list[dict] = []
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        if not file.filename:
            continue

        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

        # Handle .tar.gz — detect double extension
        if ext == "gz" and file.filename.lower().endswith((".tar.gz", ".tgz")):
            ext = "gz"  # archive_service handles tar.gz via the gz extension

        if ext not in ALLOWED:
            uploads.append({
                "upload_id": None,
                "filename": file.filename,
                "file_format": ext,
                "row_count": None,
                "status": "rejected",
                "uploaded_at": None,
                "error": f"File type '{ext}' not allowed",
            })
            continue

        file_content = await file.read()
        size_limit = archive_max if is_archive(ext) else MAX_BYTES
        if len(file_content) > size_limit:
            limit_mb = size_limit // (1024 * 1024)
            uploads.append({
                "upload_id": None,
                "filename": file.filename,
                "file_format": ext,
                "row_count": None,
                "status": "rejected",
                "uploaded_at": None,
                "error": f"File exceeds {limit_mb}MB limit",
            })
            continue

        if is_archive(ext):
            # Save archive to a temp location, extract, process each inner file
            archive_id = uuid.uuid4()
            archive_stored = upload_dir / f"{archive_id}.{ext}"
            archive_stored.write_bytes(file_content)

            try:
                extracted = extract_archive(archive_stored, ext, upload_dir)
            except Exception as exc:
                uploads.append({
                    "upload_id": None,
                    "filename": file.filename,
                    "file_format": ext,
                    "row_count": None,
                    "status": "rejected",
                    "uploaded_at": None,
                    "error": f"Failed to extract archive: {exc}",
                })
                # Clean up archive file
                archive_stored.unlink(missing_ok=True)
                continue

            # Clean up archive file after extraction
            archive_stored.unlink(missing_ok=True)

            if not extracted:
                uploads.append({
                    "upload_id": None,
                    "filename": file.filename,
                    "file_format": ext,
                    "row_count": None,
                    "status": "rejected",
                    "uploaded_at": None,
                    "error": "Archive contains no supported files (csv, xlsx, json, pdf)",
                })
                continue

            # Create an Upload record for each extracted file
            for item in extracted:
                inner_path = Path(item["stored_path"])
                inner_ext = item["file_format"]
                inner_id = item["file_id"]
                original_name = item["original_name"]

                row_count = await process_upload(inner_path, inner_ext)

                upload_record = Upload(
                    id=inner_id,
                    user_id=current_user.id,
                    filename=original_name,
                    file_path=str(inner_path),
                    file_format=inner_ext,
                    row_count=row_count,
                )
                db.add(upload_record)
                await db.flush()
                await db.refresh(upload_record)

                uploads.append({
                    "upload_id": str(upload_record.id),
                    "filename": upload_record.filename,
                    "file_format": upload_record.file_format,
                    "row_count": upload_record.row_count,
                    "status": "uploaded",
                    "uploaded_at": upload_record.uploaded_at.isoformat(),
                })
        else:
            # Normal file — same as before
            file_id = uuid.uuid4()
            stored_name = f"{file_id}.{ext}"
            stored_path = upload_dir / stored_name
            stored_path.write_bytes(file_content)

            row_count = await process_upload(stored_path, ext)

            upload_record = Upload(
                id=file_id,
                user_id=current_user.id,
                filename=file.filename,
                file_path=str(stored_path),
                file_format=ext,
                row_count=row_count,
            )
            db.add(upload_record)
            await db.flush()
            await db.refresh(upload_record)

            uploads.append({
                "upload_id": str(upload_record.id),
                "filename": upload_record.filename,
                "file_format": upload_record.file_format,
                "row_count": upload_record.row_count,
                "status": "uploaded",
                "uploaded_at": upload_record.uploaded_at.isoformat(),
            })

    return JSONResponse({"batch_id": batch_id, "uploads": uploads})
