# 09 — AI Chat System

## Overview

The application includes an AI-powered assistant for explaining validation results, Danish royalty terminology, and Schilling ERP business rules. The chat system uses:

- **AnythingLLM** for RAG (Retrieval-Augmented Generation) context
- **OpenAI GPT-4o-mini** as the primary LLM
- **Docker Model Runner (Qwen 2.5 3B)** as a local fallback
- **Server-Sent Events (SSE)** for real-time streaming
- **AG-UI protocol** for structured event delivery
- **TanStack AI React** on the frontend for state management

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (Browser)                                      │
│                                                          │
│  ┌──────────────┐      ┌──────────────────┐             │
│  │ DocumentChat │      │    HelpPage      │             │
│  │  (sidebar)   │      │  (full page)     │             │
│  └──────┬───────┘      └────────┬─────────┘             │
│         │                       │                        │
│         └───────────┬───────────┘                        │
│                     │                                    │
│         ┌───────────▼───────────┐                        │
│         │  useChat (TanStack)   │                        │
│         │  + fetchServerSentEvents │                     │
│         └───────────┬───────────┘                        │
└─────────────────────┼────────────────────────────────────┘
                      │ POST /api/chat/stream?mode=query|agent
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Backend (FastAPI)                                       │
│                                                          │
│  ┌────────────────────────────────────┐                  │
│  │  chat.py — chat_stream()          │                  │
│  │                                    │                  │
│  │  1. Parse request messages         │                  │
│  │  2. Fetch RAG context ────────────┼──┐               │
│  │  3. Build system prompt            │  │               │
│  │  4. Stream LLM response ──────────┼──┼──┐            │
│  │  5. Emit SSE events (AG-UI)       │  │  │            │
│  └────────────────────────────────────┘  │  │            │
│                                          │  │            │
└──────────────────────────────────────────┼──┼────────────┘
                                           │  │
                          ┌────────────────┘  │
                          ▼                   ▼
                ┌──────────────────┐  ┌──────────────────┐
                │  AnythingLLM     │  │  OpenAI API      │
                │  (RAG vectors)   │  │  gpt-4o-mini     │
                │  :3001           │  │                  │
                └──────────────────┘  │  -- fallback --  │
                                      │  Docker Model    │
                                      │  Runner          │
                                      │  (Qwen 2.5 3B)  │
                                      └──────────────────┘
```

---

## Chat Modes

| Mode | Query Param | Behavior |
|------|-------------|----------|
| `query` | `?mode=query` | Default. Fetches RAG context from AnythingLLM, then sends to LLM with context. Best for domain questions. |
| `chat` | `?mode=chat` | Direct LLM conversation without RAG context. General-purpose chat. |
| `agent` | `?mode=agent` | SQL agent mode. Can query the database directly (via AnythingLLM SQL agent). |

---

## RAG Pipeline

### Context Retrieval

When `mode=query`, the backend fetches relevant context from AnythingLLM:

```python
# Fetch RAG context
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{ANYTHINGLLM_BASE}/api/v1/workspace/{workspace_slug}/chat",
        headers={"Authorization": f"Bearer {ANYTHINGLLM_API_KEY}"},
        json={"message": user_message, "mode": "query"}
    )
    rag_context = response.json()["textResponse"]
```

### Knowledge Base Seeding

The knowledge base is populated by running `seed_royalty_docs.sh`, which copies sample royalty files from `baseDocs/royaltyBase/` into AnythingLLM's watched directory.

AnythingLLM indexes these documents automatically and makes them available for vector similarity search.

---

## LLM Configuration

### Primary: OpenAI

```python
OPENAI_MODEL = "gpt-4o-mini"
# API key from environment: OPENAI_API_KEY
```

### Fallback: Docker Model Runner

```python
DMR_MODEL = "docker.io/ai/qwen2.5:3B-Q4_K_M"
DMR_BASE = "http://model-runner.docker.internal/engines/llama.cpp/v1"
```

The fallback is used when:
- `OPENAI_API_KEY` is not set
- OpenAI API returns an error
- Network issues prevent reaching OpenAI

---

## System Prompt

The AI assistant receives a detailed system prompt that establishes:

1. **Expert persona**: Specialist in Schilling ERP royalty settlement system
2. **Language support**: Responds in the same language as the user (Danish/English)
3. **Field name knowledge**: All 17+ Danish column names with explanations:

| Field | Danish | English |
|-------|--------|---------|
| `TRANSNR` | Transaktionsnummer | Transaction number |
| `TRANSTYPE` | Transaktionstype | Transaction type |
| `KONTO` | Konto | Account (recipient) |
| `AFTALE` | Aftale | Agreement number |
| `ARTNR` | Artikelnummer | Product/ISBN |
| `KANAL` | Salgskanal | Sales channel |
| `PRISGRUPPE` | Prisgruppe | Price group |
| `VILKAR` | Vilkår | Terms |
| `BILAGSNR` | Bilagsnummer | Voucher number |
| `BILAGSDATO` | Bilagsdato | Voucher date |
| `ANTAL` | Antal | Quantity |
| `STKPRIS` | Stykpris | Unit price |
| `STKAFREGNSATS` | Stykafregningssats | Settlement unit rate |
| `BELOEB` | Beløb | Amount |
| `VALUTA` | Valuta | Currency |
| `SKAT` | Skat | Tax withholding |
| `AFREGNBATCH` | Afregningsbatch | Settlement batch |

---

## SSE Event Protocol (AG-UI)

The chat stream follows the AG-UI (Agent-UI) protocol:

### Event Sequence

```
1. RUN_STARTED          → Chat run begins
2. TEXT_MESSAGE_START    → Message container opened
3. TEXT_MESSAGE_CONTENT  → Token-by-token content (repeated)
4. TEXT_MESSAGE_END      → Message complete
5. RUN_FINISHED          → Chat run ends
```

### Event Payloads

```json
// 1. Run started
{"type": "RUN_STARTED", "threadId": "uuid", "runId": "uuid"}

// 2. Message start
{"type": "TEXT_MESSAGE_START", "messageId": "uuid", "role": "assistant"}

// 3. Content chunk (repeated per token)
{"type": "TEXT_MESSAGE_CONTENT", "messageId": "uuid", "delta": "The "}

// 4. Message end
{"type": "TEXT_MESSAGE_END", "messageId": "uuid"}

// 5. Run finished
{"type": "RUN_FINISHED", "threadId": "uuid", "runId": "uuid"}
```

---

## Frontend Integration

### TanStack AI React

Both chat surfaces use `@tanstack/ai-react`:

```typescript
import { useChat, fetchServerSentEvents } from '@tanstack/ai-react'

const connection = useMemo(
  () => fetchServerSentEvents('/api/chat/stream?mode=query'),
  []
)

const { messages, sendMessage, isLoading, stop, clear } = useChat({
  connection,
})
```

### Document Chat (Sidebar)

Used on the Results page. Injects the full document content (up to 400,000 chars) as context in the first message:

```typescript
const contextPrefix = `[Document Context - ${filename}]\n${content}\n\n[User Question]\n`
sendMessage(contextPrefix + userQuestion)
```

Subsequent messages are sent without the document prefix.

### Help Page (Full Page)

Features:
- Mode toggle between `query` (RAG) and `agent` (SQL)
- File upload via drag-and-drop or click
- Uploaded files are sent to `/api/chat/upload` and injected as context
- Suggestion chips for common questions
- Keyboard shortcuts:
  - `Ctrl+/` or `Cmd+/`: Focus input
  - `Escape`: Stop generation
  - `ArrowUp` (empty input): Edit last message

---

## Chat File Upload

### Flow

```
1. User drops/selects a file in the chat input
2. Frontend: POST /api/chat/upload (multipart/form-data)
3. Backend: Extract content based on type:
   - Images → base64 data URI
   - CSV/JSON/text → text extraction
   - Excel → text extraction via openpyxl
   - PDF → text extraction via pdfplumber
4. Response: {success, document: {title, type, content/dataUri}}
5. Frontend: Injects the extracted content into the next user message
```

### Size Limits

- **Max inline content**: 500,000 bytes (`MAX_INLINE_BYTES`)
- Larger files are truncated with a warning

---

## Chat Message Rendering

Messages are rendered using a custom `ChatMarkdown` component:

- **Library**: `react-markdown` with `remark-gfm` and `rehype-highlight`
- **Features**: GFM tables, code blocks with syntax highlighting, links, lists
- **Thinking blocks**: `type === 'thinking'` messages shown in collapsible `ChatThinking` component
- **Source citations**: RAG sources displayed via `ChatSources` component

---

## Conversation Persistence

**Conversations are NOT persisted on the server.** The frontend stores message history in React state (via TanStack AI `useChat`). Each request to `/api/chat/stream` includes the full conversation history in the `messages` array.

This means:
- Refreshing the page clears chat history
- Each API call includes all previous messages (growing context window)
- No conversation database table exists
