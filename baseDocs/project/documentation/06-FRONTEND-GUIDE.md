# 06 — Frontend Guide

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 19 | UI framework |
| TypeScript | 5.9 | Type safety |
| Vite | 8 | Build tool & dev server |
| React Router | 7 | Client-side routing |
| Tailwind CSS | 3 | Utility-first styling |
| shadcn/ui | 4 | Component library (Radix primitives) |
| TanStack AI | — | Chat SSE streaming (AG-UI protocol) |
| Motion (Framer Motion) | 12 | Animations |
| Lucide React | 0.577 | Icon library |
| react-markdown | 10 | Markdown rendering |
| react-pdf | 10 | PDF preview |
| react-dropzone | 15 | Drag-and-drop file input |

---

## Application Structure

```
src/
├── main.tsx                    # React root mount
├── App.tsx                     # BrowserRouter + Routes
├── App.css                     # App-level styles
├── index.css                   # Global CSS tokens (OKLCH), fonts
├── api.ts                      # Centralized HTTP client
├── types.ts                    # Shared TypeScript interfaces
├── lib/
│   └── utils.ts                # cn() — clsx + tailwind-merge
├── components/                 # Shared components
│   ├── AuthContext.tsx          # Auth state (Context + Provider + hook)
│   ├── AuthBackground.tsx      # Animated auth page background
│   ├── DocumentChat.tsx        # Document-scoped AI chat (sidebar)
│   ├── DocumentPreview.tsx     # File preview (table/raw/PDF)
│   ├── HistorySheet.tsx        # Upload history slide-out panel
│   ├── Layout.tsx              # App shell (header + navigation + outlet)
│   ├── ProtectedRoute.tsx      # Auth guard wrapper
│   ├── ThemeProvider.tsx       # Dark/light/system theme context
│   ├── ThemeToggle.tsx         # Theme cycling button
│   └── ui/                     # shadcn/ui primitives (12 components)
├── pages/
│   ├── LoginPage.tsx           # Login form
│   ├── RegisterPage.tsx        # Registration with password strength
│   ├── UploadPage.tsx          # Batch drag-and-drop upload
│   ├── ResultsPage.tsx         # Validation results dashboard
│   └── HelpPage.tsx            # Full-page AI assistant
└── features/
    ├── ai-chat/                # Reusable chat building blocks
    │   ├── index.ts            # Public exports
    │   ├── types.ts            # Chat-specific types
    │   ├── hooks/
    │   │   └── useChatKeyboard.ts
    │   └── components/         # 14 chat components
    └── uploads/                # Batch upload system
        ├── index.ts
        ├── types.ts
        ├── constants.ts
        ├── api/
        │   └── upload-api.ts
        ├── hooks/              # 3 upload hooks
        ├── utils/
        │   └── file-helpers.ts
        └── components/         # 8 upload components
```

---

## Routing

Defined in `App.tsx` using React Router v7:

| Route | Component | Auth | Description |
|-------|-----------|------|-------------|
| `/login` | `LoginPage` | Public | Login form |
| `/register` | `RegisterPage` | Public | Registration form |
| `/upload` | `UploadPage` | Protected | Batch file upload |
| `/results/:validationId` | `ResultsPage` | Protected | Validation results |
| `/help` | `HelpPage` | Protected | AI assistant |
| `/` or `*` | — | — | Redirects to `/login` |

Protected routes are wrapped in `<ProtectedRoute>`, which:
1. Shows `<Spinner>` while verifying the token
2. Redirects to `/login` if the user is not authenticated
3. Renders the child route if authenticated

---

## State Management

No global store is used. State is managed through React Context and local hooks:

### AuthContext

```typescript
interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  login: (nickname: string, password: string) => Promise<void>
  register: (nickname: string, password: string) => Promise<void>
  logout: () => void
}
```

- Token stored in `localStorage` under key `rsv_token`
- Nickname cached in `rsv_nickname`
- On mount: reads token from localStorage → calls `GET /api/auth/me` → sets user or clears token

### ThemeProvider

```typescript
type Theme = 'light' | 'dark' | 'system'
```

- Stored in `localStorage` under key `rv-theme`
- Default: `dark`
- Applies `.dark` or `.light` class to `<html>` element
- `ThemeToggle` cycles through: dark → light → system

---

## API Client (`api.ts`)

Centralized HTTP client with automatic auth header injection:

```typescript
const BASE = '/api'

function getToken(): string | null {
  return localStorage.getItem('rsv_token')
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...init?.headers }
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
```

**Exported functions**:

| Function | Method | Endpoint |
|----------|--------|----------|
| `register(nickname, password)` | POST | `/auth/register` |
| `login(nickname, password)` | POST | `/auth/login` |
| `getMe()` | GET | `/auth/me` |
| `uploadFile(file)` | POST | `/uploads/` |
| `listUploads()` | GET | `/uploads/` |
| `getUpload(id)` | GET | `/uploads/:id` |
| `getUploadContent(id)` | GET | `/uploads/:id/content` |
| `triggerValidation(uploadId)` | POST | `/validations/:id/run` |
| `getValidation(id)` | GET | `/validations/:id` |
| `getValidationIssues(id, params)` | GET | `/validations/:id/issues` |
| `downloadValidationPdf(id)` | GET | `/validations/:id/pdf` |
| `downloadAnnotatedPdf(id)` | GET | `/validations/:id/annotated-pdf` |

---

## Pages

### LoginPage

- Cinematic design with `AuthBackground` (animated mesh gradient)
- Nickname + password form
- Link to Register
- On success: stores token, redirects to `/upload`

### RegisterPage

- Same cinematic design as Login
- Nickname + password + confirm password
- Password strength meter
- On success: auto-login, redirects to `/upload`

### UploadPage

Three-phase state machine managed by `useBatchUpload`:

1. **Idle Phase**: `DropZone` accepts files via drag-and-drop or click. Shows file queue with format badges, sizes, remove buttons.
2. **Processing Phase**: Progress bars per file. SSE events show real-time status (uploading → parsing → validating → complete/error).
3. **Completed Phase**: `BatchSummary` shows results cards per file with error/warning/info counts and links to results.

Archive files (ZIP/TAR/RAR) are automatically extracted; the batch expands to show individual files.

### ResultsPage

Two-panel layout:
- **Left panel**: Summary cards (passed, warnings, errors, info) + severity-filtered, paginated issue table
- **Right panel**: Tabbed view — Document Preview (table/raw/PDF) + Document Chat (AI sidebar)

Features:
- Download PDF report (styled summary)
- Download annotated PDF (color-coded source data)
- Actions dropdown: re-run validation, view upload details
- `HistorySheet` slide-out panel for quick access to past uploads

### HelpPage

Full-page AI assistant with:
- Two modes toggled by user: `query` (RAG-powered) and `agent` (SQL agent)
- File upload support (drag-and-drop onto chat area)
- Suggestion chips for common questions
- Full markdown rendering with syntax highlighting
- Keyboard shortcuts (Ctrl+/ to focus, Escape to stop, ArrowUp to edit last message)

---

## Feature Modules

### `features/ai-chat/`

Reusable chat building blocks used by both `DocumentChat` (compact sidebar) and `HelpPage` (full page).

**Components** (14 total):

| Component | Purpose |
|-----------|---------|
| `ChatConversation` | Scrollable message container with auto-scroll + follow-ups |
| `ChatMessage` | Single message bubble with avatar and status |
| `ChatMarkdown` | Markdown renderer (GFM, syntax highlighting) |
| `ChatPromptInput` | Textarea with file attach, mode toggle, keyboard shortcuts |
| `ChatEmptyState` | Initial empty state with suggestion chips |
| `ChatErrorState` | Error display with retry button |
| `ChatFileChip` | Attached file badge (removable) |
| `ChatMessageActions` | Hover actions: copy, regenerate |
| `ChatScrollButton` | Floating "scroll to bottom" button |
| `ChatShimmer` | Skeleton shimmer while awaiting first token |
| `ChatSources` | RAG source citation display |
| `ChatSuggestionChips` | Pre-canned question buttons |
| `ChatThinking` | Collapsible reasoning/thinking block |
| `ChatTypingIndicator` | Animated typing dots during stream |

**Hooks**:
- `useChatKeyboard`: Keyboard shortcut handler (focus, stop, edit last)

**Variants**: `'compact'` (sidebar) and `'full'` (page)

### `features/uploads/`

Self-contained batch upload system.

**Types**:
```typescript
type BatchPhase = 'idle' | 'processing' | 'completed'
type FileStatus = 'queued' | 'uploading' | 'parsing' | 'validating' | 'complete' | 'error'

interface BatchFile {
  id: string
  file: File
  status: FileStatus
  progress: number
  uploadId?: string
  validationId?: string
  errorCount?: number
  warningCount?: number
  infoCount?: number
  error?: string
}
```

**Hooks**:
- `useFileQueue`: File queue state machine (add, remove, update, clear)
- `useBatchUpload`: Upload + validation orchestrator (phases, file management)
- `useUploadProgress`: SSE subscription for batch progress events

**Components** (8 total):

| Component | Purpose |
|-----------|---------|
| `DropZone` | react-dropzone drag-and-drop area |
| `FormatBadge` | File format pill badge |
| `FileQueueItem` | Single file row in queue |
| `FileQueueList` | All queued files list |
| `FileProgressRow` | Per-file progress bar |
| `UploadProgress` | Phase 2 overall progress view |
| `UploadProgressSteps` | Step indicators (upload → parse → validate) |
| `BatchSummary` | Phase 3 completed results cards |

---

## Design System

### Color System

OKLCH color space defined as CSS variables in `index.css`:

```css
:root {
  --background: 0.98 0.005 285;    /* Light mode */
  --foreground: 0.15 0.01 285;
  --primary: 0.65 0.18 45;         /* Warm amber brand */
  --destructive: 0.55 0.22 25;     /* Red */
  /* ... more tokens */
}

.dark {
  --background: 0.12 0.01 285;     /* Dark mode */
  --foreground: 0.92 0.01 285;
  /* ... */
}
```

### Typography

| Font | Usage | Source |
|------|-------|--------|
| Inter Variable | Body text (primary) | @fontsource-variable |
| Plus Jakarta Sans | Body text (secondary) | Google Fonts |
| Outfit | Display headings | Google Fonts |
| JetBrains Mono | Code blocks, monospace | Google Fonts |

### Custom Utilities

```css
.text-gradient    /* Gradient text effect */
.surface-elevated /* Subtle elevated surface with shadow */
.noise-overlay    /* Texture noise overlay */
```

---

## Build Configuration

### Vite (`vite.config.ts`)

```typescript
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') }
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/docs': 'http://localhost:8000',
      '/redoc': 'http://localhost:8000',
      '/openapi.json': 'http://localhost:8000'
    }
  }
})
```

### Tailwind (`tailwind.config.js`)

- `darkMode: ['class']` — toggled by `.dark` class on `<html>`
- Custom font families: `display`, `body`, `mono`
- Custom color palettes: `brand` (warm amber), `ink` (neutral grays)
- shadcn/ui semantic tokens via CSS variables

### TypeScript

- Target: ES2020
- Strict mode enabled
- Path alias: `@/*` → `src/*`
- Bundler module resolution
