"""Chat proxy — bridges TanStack AI AG-UI protocol to AnythingLLM streaming API."""

import json
import uuid
import time
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])

ANYTHINGLLM_BASE = "http://anythingllm:3001/api/v1"
ANYTHINGLLM_API_KEY = "27VXB0E-8P34VRP-HZCMC8Y-M8PEJ8Y"

# Default workspace slug — auto-detected on first request
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

        # No workspace found — create one
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


async def _stream_sse(messages: list[dict]) -> AsyncGenerator[str, None]:
    """Call AnythingLLM stream-chat and yield AG-UI protocol SSE chunks."""
    slug = await _get_workspace_slug()
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    msg_id = f"msg-{uuid.uuid4().hex[:12]}"
    ts = int(time.time() * 1000)

    # Extract the last user message content
    user_message = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            # TanStack AI sends parts array
            parts = m.get("parts", [])
            for p in parts:
                if p.get("type") == "text":
                    user_message = p.get("content", "")
                    break
            # Fallback: plain content field
            if not user_message:
                user_message = m.get("content", "")
            if user_message:
                break

    if not user_message:
        chunk = json.dumps({
            "type": "RUN_ERROR",
            "runId": run_id,
            "timestamp": ts,
            "error": {"message": "No user message found"},
        })
        yield f"data: {chunk}\n\n"
        return

    # Emit RUN_STARTED
    yield f"data: {json.dumps({'type': 'RUN_STARTED', 'runId': run_id, 'timestamp': ts})}\n\n"

    # Emit TEXT_MESSAGE_START
    yield f"data: {json.dumps({'type': 'TEXT_MESSAGE_START', 'messageId': msg_id, 'role': 'assistant', 'timestamp': ts})}\n\n"

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            async with client.stream(
                "POST",
                f"{ANYTHINGLLM_BASE}/workspace/{slug}/stream-chat",
                headers={
                    "Authorization": f"Bearer {ANYTHINGLLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"message": user_message, "mode": "chat"},
            ) as resp:
                if resp.status_code != 200:
                    chunk = json.dumps({
                        "type": "RUN_ERROR",
                        "runId": run_id,
                        "timestamp": int(time.time() * 1000),
                        "error": {"message": f"AnythingLLM returned {resp.status_code}"},
                    })
                    yield f"data: {chunk}\n\n"
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
                            yield f"data: {json.dumps({'type': 'RUN_ERROR', 'runId': run_id, 'timestamp': int(time.time() * 1000), 'error': {'message': is_error}})}\n\n"
                            return

                        if text:
                            chunk = json.dumps({
                                "type": "TEXT_MESSAGE_CONTENT",
                                "messageId": msg_id,
                                "delta": text,
                            })
                            yield f"data: {chunk}\n\n"

                        if is_close:
                            break

        except httpx.ConnectError:
            yield f"data: {json.dumps({'type': 'RUN_ERROR', 'runId': run_id, 'timestamp': int(time.time() * 1000), 'error': {'message': 'Cannot connect to AnythingLLM service'}})}\n\n"
            return

    # Emit TEXT_MESSAGE_END + RUN_FINISHED
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
