"""Chat proxy — bridges TanStack AI AG-UI protocol to AnythingLLM streaming API.

Strategy: uploaded files are read server-side so their text content is injected
directly into the LLM prompt.  This avoids relying on slow AnythingLLM embedding
and guarantees the model can "see" the document immediately.
"""

import base64
import csv
import io
import json
import os
import uuid
import time
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])

ANYTHINGLLM_BASE = "http://anythingllm:3001/api/v1"
ANYTHINGLLM_API_KEY = "27VXB0E-8P34VRP-HZCMC8Y-M8PEJ8Y"
MAX_INLINE_BYTES = 500_000  # ~500 KB text content inline limit

_workspace_slug: str | None = None


async def _get_workspace_slug() -> str:
    """Get the first available workspace slug, or create one."""
    global _workspace_slug
    if _workspace_slug:
        return _workspace_slug

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{ANYTHINGLLM_BASE}/workspaces",
            headers={"Authorization": f"Bearer {ANYTHINGLLM_API_KEY}"},
        )
        if resp.status_code == 200:
            data = resp.json()
            workspaces = data.get("workspaces", [])
            if workspaces:
                _workspace_slug = workspaces[0].get("slug")
                if _workspace_slug:
                    return _workspace_slug

        resp = await client.post(
            f"{ANYTHINGLLM_BASE}/workspace/new",
            headers={
                "Authorization": f"Bearer {ANYTHINGLLM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"name": "Royalty Settlements"},
        )
        if resp.status_code == 200:
            ws = resp.json().get("workspace", {})
            _workspace_slug = ws.get("slug", "royalty-settlements")
        else:
            _workspace_slug = "royalty-settlements"

    return _workspace_slug


# ── file content extraction ─────────────────────────────────────────────

def _extract_text(filename: str, raw: bytes) -> str:
    """Best-effort text extraction from common file types."""
    ext = os.path.splitext(filename)[1].lower()

    # Plain text formats
    if ext in {".csv", ".tsv", ".txt", ".md", ".xml"}:
        return raw.decode("utf-8", errors="replace")[:MAX_INLINE_BYTES]

    # JSON
    if ext == ".json":
        try:
            obj = json.loads(raw)
            text = json.dumps(obj, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            text = raw.decode("utf-8", errors="replace")
        return text[:MAX_INLINE_BYTES]

    # Excel
    if ext in {".xlsx", ".xls"}:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            rows: list[str] = []
            for ws in wb.worksheets:
                rows.append(f"## Sheet: {ws.title}")
                for row in ws.iter_rows(values_only=True):
                    rows.append(",".join(str(c) if c is not None else "" for c in row))
                if len("\n".join(rows)) > MAX_INLINE_BYTES:
                    break
            wb.close()
            return "\n".join(rows)[:MAX_INLINE_BYTES]
        except Exception:
            return "(Could not read Excel file)"

    # PDF
    if ext == ".pdf":
        try:
            import pdfplumber
            pages: list[str] = []
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        pages.append(t)
                    if len("\n".join(pages)) > MAX_INLINE_BYTES:
                        break
            return "\n".join(pages)[:MAX_INLINE_BYTES] or "(PDF contained no extractable text)"
        except Exception:
            return "(Could not read PDF file)"

    return "(Binary file — content not extractable as text)"


# ── streaming ───────────────────────────────────────────────────────────

async def _stream_sse(messages: list[dict]) -> AsyncGenerator[str, None]:
    """Call AnythingLLM stream-chat and yield AG-UI protocol SSE chunks."""
    slug = await _get_workspace_slug()
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    msg_id = f"msg-{uuid.uuid4().hex[:12]}"
    ts = int(time.time() * 1000)

    # Build user message from the last user turn
    user_message = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            parts = m.get("parts", [])
            for p in parts:
                if p.get("type") == "text":
                    user_message = p.get("content", "")
                    break
            if not user_message:
                user_message = m.get("content", "")
            if user_message:
                break

    if not user_message:
        yield f"data: {json.dumps({'type': 'RUN_ERROR', 'runId': run_id, 'timestamp': ts, 'error': {'message': 'No user message found'}})}\n\n"
        return

    yield f"data: {json.dumps({'type': 'RUN_STARTED', 'runId': run_id, 'timestamp': ts})}\n\n"
    yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_START', 'messageId': msg_id, 'role': 'assistant', 'timestamp': ts})}\n\n"

    timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
    got_content = False
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream(
                "POST",
                f"{ANYTHINGLLM_BASE}/workspace/{slug}/stream-chat",
                headers={
                    "Authorization": f"Bearer {ANYTHINGLLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"message": user_message, "mode": "query"},
            ) as resp:
                if resp.status_code != 200:
                    yield f"data: {json.dumps({'type': 'RUN_ERROR', 'runId': run_id, 'timestamp': int(time.time() * 1000), 'error': {'message': f'AnythingLLM returned {resp.status_code}'}})}\n\n"
                    return

                buffer = ""
                async for raw in resp.aiter_text():
                    buffer += raw
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("data: "):
                            line = line[6:]
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        text = data.get("textResponse", "")
                        is_close = data.get("close", False)
                        is_error = data.get("error")

                        if is_error and isinstance(is_error, str):
                            yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_CONTENT', 'messageId': msg_id, 'delta': f'\\n\\n⚠️ Error: {is_error}'})}\n\n"
                            break

                        if text:
                            got_content = True
                            yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_CONTENT', 'messageId': msg_id, 'delta': text})}\n\n"

                        if is_close:
                            break

        except httpx.ConnectError:
            yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_CONTENT', 'messageId': msg_id, 'delta': '⚠️ Cannot connect to the AI service. Please try again later.'})}\n\n"
        except (httpx.RemoteProtocolError, httpx.ReadTimeout) as exc:
            if not got_content:
                yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_CONTENT', 'messageId': msg_id, 'delta': f'⚠️ The AI service timed out or dropped the connection. Please try again.'})}\n\n"
        except Exception:
            if not got_content:
                yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_CONTENT', 'messageId': msg_id, 'delta': '⚠️ An unexpected error occurred. Please try again.'})}\n\n"

    # Always close the message and run so the frontend exits loading state
    end_ts = int(time.time() * 1000)
    yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_END', 'messageId': msg_id, 'timestamp': end_ts})}\n\n"
    yield f"data: {json.dumps({'type': 'RUN_FINISHED', 'runId': run_id, 'timestamp': end_ts, 'finishReason': 'stop'})}\n\n"


@router.post("/stream")
async def chat_stream(request: Request) -> StreamingResponse:
    """TanStack AI AG-UI compatible chat endpoint proxying to AnythingLLM."""
    body = await request.json()
    messages = body.get("messages", [])

    return StreamingResponse(
        _stream_sse(messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── file upload ─────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {
    ".csv", ".xlsx", ".xls", ".json", ".pdf", ".txt",
    ".doc", ".docx", ".md", ".tsv", ".xml",
    # Images (for future vision model support)
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}


@router.post("/upload")
async def chat_upload(request: Request):
    """Upload a file: extract its text content and return it so the frontend
    can inject it directly into the chat message.  Also upload+embed into
    AnythingLLM asynchronously for future RAG retrieval."""
    form = await request.form()
    file = form.get("file")
    if file is None:
        return {"success": False, "error": "No file provided"}

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {"success": False, "error": f"Unsupported file type: {ext}"}

    content = await file.read()
    is_image = ext in IMAGE_EXTENSIONS

    # For images: return base64 preview (for future vision model use)
    if is_image:
        b64 = base64.b64encode(content).decode("ascii")
        mime = file.content_type or "image/png"
        return {
            "success": True,
            "document": {
                "title": file.filename,
                "type": "image",
                "mimeType": mime,
                "sizeBytes": len(content),
                "contentPreview": f"(Image: {file.filename}, {len(content):,} bytes)",
                "dataUri": f"data:{mime};base64,{b64}",
            },
        }

    # For documents: extract text content
    extracted_text = _extract_text(file.filename, content)

    # Also upload to AnythingLLM in the background (best-effort, non-blocking)
    slug = await _get_workspace_slug()
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{ANYTHINGLLM_BASE}/document/upload",
                headers={"Authorization": f"Bearer {ANYTHINGLLM_API_KEY}"},
                files={"file": (file.filename, content, file.content_type or "application/octet-stream")},
            )
            if resp.status_code == 200:
                upload_data = resp.json()
                documents = upload_data.get("documents", [])
                doc_locations = [d["location"] for d in documents if d.get("location")]
                if doc_locations:
                    await client.post(
                        f"{ANYTHINGLLM_BASE}/workspace/{slug}/update-embeddings",
                        headers={
                            "Authorization": f"Bearer {ANYTHINGLLM_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={"adds": doc_locations},
                    )
    except Exception:
        pass  # embedding is best-effort; the text content is the primary mechanism

    # Truncate preview for response (keep full text for contentFull)
    preview = extracted_text[:500]
    if len(extracted_text) > 500:
        preview += "…"

    return {
        "success": True,
        "document": {
            "title": file.filename,
            "type": "document",
            "sizeBytes": len(content),
            "contentPreview": preview,
            "contentFull": extracted_text,
        },
    }
