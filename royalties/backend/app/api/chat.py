"""Chat proxy — bridges TanStack AI AG-UI protocol to LLM APIs.

Architecture:
  - RAG context: retrieved from AnythingLLM vector search
  - LLM inference: direct calls to OpenAI (primary) or Docker Model Runner (fallback)
  - Both LLM backends use the OpenAI-compatible /v1/chat/completions streaming API
  - Tokens are streamed in real-time to the frontend (no buffering)
"""

import base64
import io
import json
import logging
import os
import uuid
import time
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])
log = logging.getLogger(__name__)

# ── AnythingLLM (RAG context only) ──────────────────────────────────────
ANYTHINGLLM_BASE = "http://anythingllm:3001/api/v1"
ANYTHINGLLM_API_KEY = "27VXB0E-8P34VRP-HZCMC8Y-M8PEJ8Y"
MAX_INLINE_BYTES = 500_000

# ── LLM providers (direct API calls) ───────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE = "https://api.openai.com/v1"
OPENAI_MODEL = "gpt-4o-mini"

# Docker Model Runner exposes an OpenAI-compatible endpoint
# From inside Docker network: model-runner.docker.internal
# The backend container connects via the Docker host gateway
DMR_BASE = os.environ.get(
    "DMR_BASE",
    "http://model-runner.docker.internal/engines/llama.cpp/v1",
)
DMR_MODEL = "docker.io/ai/qwen2.5:3B-Q4_K_M"

SYSTEM_PROMPT = (
    "You are a royalty settlement expert for Schilling ERP, a Danish publishing system. "
    "You help users analyze royalty statements (afregninger), settlement data (afregndata), "
    "and export files (export_schilling). The documents contain Danish financial terms: "
    "TRANSNR (transaction number), TRANSTYPE (transaction type like Salg=Sale), KONTO (account), "
    "AFTALE (agreement), ARTNR (article/ISBN), KANAL (channel), PRISGRUPPE (price group), "
    "VILKAR (terms), BILAGSNR (voucher number), BILAGSDATO (voucher date), ANTAL (quantity), "
    "STKPRIS (unit price), STKAFREGNSATS (settlement rate), BELOEB (amount), VALUTA (currency), "
    "SKAT (tax), AFREGNBATCH (settlement batch). "
    "Always answer based on the actual document data provided in context. "
    "Be specific with numbers, dates, and amounts. Answer in the same language as the question."
)

_workspace_slug: str | None = None


async def _get_workspace_slug() -> str:
    global _workspace_slug
    if _workspace_slug:
        return _workspace_slug
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{ANYTHINGLLM_BASE}/workspaces",
                headers={"Authorization": f"Bearer {ANYTHINGLLM_API_KEY}"},
            )
            if resp.status_code == 200:
                workspaces = resp.json().get("workspaces", [])
                if workspaces:
                    _workspace_slug = workspaces[0].get("slug", "my-workspace")
                    return _workspace_slug
    except Exception:
        pass
    _workspace_slug = "my-workspace"
    return _workspace_slug


# ── RAG context retrieval ───────────────────────────────────────────────

async def _get_rag_context(query: str) -> str:
    """Retrieve relevant document chunks from AnythingLLM vector store."""
    slug = await _get_workspace_slug()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Use the non-streaming chat endpoint in "query" mode with a
            # dummy model — we only care about the context sources returned.
            # AnythingLLM's /workspace/:slug/chat returns sources.
            resp = await client.post(
                f"{ANYTHINGLLM_BASE}/workspace/{slug}/chat",
                headers={
                    "Authorization": f"Bearer {ANYTHINGLLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"message": query, "mode": "query"},
                timeout=30.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                sources = data.get("sources", [])
                if sources:
                    context_parts = []
                    for src in sources[:8]:
                        title = src.get("title", "")
                        text = src.get("text", "")
                        if text:
                            context_parts.append(f"[{title}]\n{text}")
                    if context_parts:
                        return "\n\n---\n\n".join(context_parts)

                # If model also generated text, that means AnythingLLM already
                # sent the query to its LLM. We only want the sources.
                # Fall through and return the textResponse if sources are empty
                text_resp = data.get("textResponse", "")
                if text_resp and "no relevant information" not in text_resp.lower():
                    return f"[AnythingLLM response]\n{text_resp}"
    except Exception as e:
        log.warning("RAG context retrieval failed: %s", e)

    return ""


# ── file content extraction ─────────────────────────────────────────────

def _extract_text(filename: str, raw: bytes) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in {".csv", ".tsv", ".txt", ".md", ".xml"}:
        return raw.decode("utf-8", errors="replace")[:MAX_INLINE_BYTES]
    if ext == ".json":
        try:
            obj = json.loads(raw)
            text = json.dumps(obj, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            text = raw.decode("utf-8", errors="replace")
        return text[:MAX_INLINE_BYTES]
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


# ── Direct LLM streaming (OpenAI-compatible API) ───────────────────────

async def _stream_openai_compatible(
    base_url: str,
    api_key: str | None,
    model: str,
    messages: list[dict],
    msg_id: str,
    timeout: float = 60.0,
) -> AsyncGenerator[tuple[str | None, str | None], None]:
    """Stream from any OpenAI-compatible endpoint.

    Yields (delta_text, error) tuples.
    - On success: yields (chunk_text, None) for each token
    - On error: yields (None, error_message) once
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=15.0, read=timeout, write=15.0, pool=15.0)
        ) as client:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    try:
                        err = json.loads(body)
                        err_msg = err.get("error", {}).get("message", "") or str(err)
                    except Exception:
                        err_msg = body.decode("utf-8", errors="replace")[:200]
                    yield (None, f"HTTP {resp.status_code}: {err_msg}")
                    return

                buffer = ""
                async for raw in resp.aiter_text():
                    buffer += raw
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            return
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        choices = data.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            text = delta.get("content", "")
                            if text:
                                yield (text, None)

    except httpx.ConnectError:
        yield (None, "Cannot connect to LLM service")
    except httpx.ReadTimeout:
        yield (None, "LLM service timed out")
    except Exception as e:
        yield (None, f"LLM error: {e}")


# ── Main SSE streaming ─────────────────────────────────────────────────

async def _stream_sse(messages: list[dict], mode: str = "query") -> AsyncGenerator[str, None]:
    """Stream chat with OpenAI (primary) + Docker Model Runner (fallback).

    Uses AnythingLLM only for RAG context retrieval, then calls LLMs directly.
    """
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    msg_id = f"msg-{uuid.uuid4().hex[:12]}"
    ts = int(time.time() * 1000)

    # Extract user message from TanStack AI format
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

    # ── Build LLM messages with RAG context ──
    rag_context = ""
    if mode == "query":
        rag_context = await _get_rag_context(user_message)

    llm_messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if rag_context:
        llm_messages.append({
            "role": "system",
            "content": f"Relevant document context:\n\n{rag_context}",
        })
    llm_messages.append({"role": "user", "content": user_message})

    # ── Try primary: OpenAI ──
    primary_error: str | None = None
    got_content = False

    async for delta, error in _stream_openai_compatible(
        OPENAI_BASE, OPENAI_API_KEY, OPENAI_MODEL, llm_messages, msg_id, timeout=60.0
    ):
        if error:
            primary_error = error
            break
        if delta:
            got_content = True
            yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_CONTENT', 'messageId': msg_id, 'delta': delta})}\n\n"

    # ── Fallback: Docker Model Runner ──
    if not got_content:
        log.warning("Primary (OpenAI) failed: %s — trying local fallback", primary_error)

        yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_CONTENT', 'messageId': msg_id, 'delta': '\n\n---\n\n> _Using local model (OpenAI unavailable)_\n\n'})}\n\n"

        fb_got_content = False
        fb_error: str | None = None

        async for delta, error in _stream_openai_compatible(
            DMR_BASE, None, DMR_MODEL, llm_messages, msg_id, timeout=180.0
        ):
            if error:
                fb_error = error
                break
            if delta:
                fb_got_content = True
                yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_CONTENT', 'messageId': msg_id, 'delta': delta})}\n\n"

        if not fb_got_content:
            err_text = f"⚠️ Both AI providers failed.\n- **OpenAI**: {primary_error}\n- **Local model**: {fb_error}"
            yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_CONTENT', 'messageId': msg_id, 'delta': err_text})}\n\n"

    # Close message and run
    end_ts = int(time.time() * 1000)
    yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_END', 'messageId': msg_id, 'timestamp': end_ts})}\n\n"
    yield f"data: {json.dumps({'type': 'RUN_FINISHED', 'runId': run_id, 'timestamp': end_ts, 'finishReason': 'stop'})}\n\n"


@router.post("/stream")
async def chat_stream(request: Request) -> StreamingResponse:
    """TanStack AI AG-UI compatible chat endpoint.

    Accepts optional ``mode``: "query" (default, RAG), "chat", or "agent".
    Mode can be passed as a query param (?mode=agent) or in the JSON body.
    """
    body = await request.json()
    messages = body.get("messages", [])
    mode = request.query_params.get("mode") or body.get("mode", "query")
    if mode not in ("query", "chat", "agent"):
        mode = "query"

    return StreamingResponse(
        _stream_sse(messages, mode=mode),
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
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}


@router.post("/upload")
async def chat_upload(request: Request):
    """Upload a file: extract text and return it for inline chat injection.
    Also uploads to AnythingLLM for future RAG retrieval."""
    form = await request.form()
    file = form.get("file")
    if file is None:
        return {"success": False, "error": "No file provided"}

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {"success": False, "error": f"Unsupported file type: {ext}"}

    content = await file.read()
    is_image = ext in IMAGE_EXTENSIONS

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

    extracted_text = _extract_text(file.filename, content)

    # Best-effort embed into AnythingLLM
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
        pass

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
