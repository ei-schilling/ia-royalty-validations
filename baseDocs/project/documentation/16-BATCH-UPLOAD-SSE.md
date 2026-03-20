# 16 — Batch Upload & SSE Progress

## Overview

The batch upload system allows users to upload multiple files at once (including archives) and receive real-time validation progress via Server-Sent Events.

---

## Upload Flow

### Three-Phase State Machine

```
Phase 1: IDLE          Phase 2: PROCESSING       Phase 3: COMPLETED
┌──────────────┐      ┌───────────────────┐      ┌───────────────────┐
│              │      │                   │      │                   │
│  DropZone    │─────▶│  Upload files     │─────▶│  BatchSummary     │
│  FileQueue   │      │  Trigger batch    │      │  Per-file results │
│              │      │  SSE progress     │      │  Links to results │
└──────────────┘      └───────────────────┘      └───────────────────┘
```

### Phase 1: Idle

Users drag files onto the `DropZone` or click to select. The file queue displays:
- Filename with format badge (CSV, XLSX, JSON, PDF, ZIP, etc.)
- File size
- Remove button

**Constraints**:
- Regular files: max 50 MB
- Archives: max 200 MB
- Deduplication by `name:size` (prevents adding the same file twice)

**Accepted formats**: CSV, XLSX, JSON, PDF, ZIP, TAR, GZ, RAR

### Phase 2: Processing

1. **Upload**: Each file is uploaded individually via `POST /api/uploads/` (multipart/form-data)
2. **Batch trigger**: All upload IDs are sent to `POST /api/validations/batch`
3. **SSE subscription**: Frontend subscribes to `GET /api/validations/batch/{batchId}/progress?token=<jwt>`

During processing, each file shows a progress bar with status indicators:
- Uploading → Parsing → Validating → Complete / Error

### Phase 3: Completed

`BatchSummary` displays:
- Per-file result cards showing error/warning/info counts
- Color-coded severity indicators
- Links to individual `ResultsPage` for each file

---

## Archive Handling

When an archive (ZIP, TAR, RAR) is uploaded:

1. Backend extracts the archive
2. Creates individual upload records for each extracted file
3. Returns expanded upload IDs (more than originally submitted)
4. Frontend synthesizes `BatchFile` entries for newly discovered files

```
User uploads: report.zip (contains 3 files)
                │
                ▼
Backend extracts: statement_jan.csv, statement_feb.csv, statement_mar.csv
                │
                ▼
3 upload records created (3 upload IDs returned)
                │
                ▼
Frontend shows 3 files in progress (not the zip)
```

---

## SSE Event Protocol

### Endpoint

```
GET /api/validations/batch/{batch_id}/progress?token=<jwt>
Content-Type: text/event-stream
```

### Event Types

#### `file_start`

Emitted when a file begins validation.

```
event: file_start
data: {"upload_id": "uuid", "filename": "statement.csv"}
```

#### `file_complete`

Emitted when a file finishes validation successfully.

```
event: file_complete
data: {
  "upload_id": "uuid",
  "validation_id": "uuid",
  "filename": "statement.csv",
  "error_count": 2,
  "warning_count": 5,
  "info_count": 3
}
```

#### `file_error`

Emitted when a file fails validation (parse error, etc.).

```
event: file_error
data: {
  "upload_id": "uuid",
  "filename": "corrupt.csv",
  "error": "Parse error: invalid CSV format"
}
```

#### `batch_complete`

Emitted when all files have been processed.

```
event: batch_complete
data: {
  "batch_id": "uuid",
  "total": 5,
  "completed": 4,
  "failed": 1
}
```

### Event Sequence (Happy Path)

```
file_start (file 1)
file_complete (file 1)
file_start (file 2)
file_complete (file 2)
file_start (file 3)
file_complete (file 3)
batch_complete
```

### Error Handling

If a file fails, the batch continues with remaining files:

```
file_start (file 1)
file_complete (file 1)
file_start (file 2)
file_error (file 2)     ← File 2 failed, batch continues
file_start (file 3)
file_complete (file 3)
batch_complete           ← completed: 2, failed: 1
```

---

## Frontend Implementation

### Hooks

#### `useFileQueue`

Manages the file queue state:

```typescript
interface FileQueue {
  files: BatchFile[]
  addFiles: (files: File[]) => void
  removeFile: (id: string) => void
  updateFile: (id: string, updates: Partial<BatchFile>) => void
  clear: () => void
}
```

#### `useBatchUpload`

Orchestrates the upload-validate-progress flow:

```typescript
interface BatchUpload {
  phase: BatchPhase       // 'idle' | 'processing' | 'completed'
  files: BatchFile[]
  startUpload: () => void
  reset: () => void
}
```

#### `useUploadProgress`

Subscribes to SSE progress events:

```typescript
function useUploadProgress(
  batchId: string | null,
  onFileStart: (data) => void,
  onFileComplete: (data) => void,
  onFileError: (data) => void,
  onBatchComplete: (data) => void,
)
```

Uses `EventSource` API. Token is passed as a query parameter since EventSource doesn't support custom headers.

### Components

| Component | Phase | Purpose |
|-----------|-------|---------|
| `DropZone` | 1 | Drag-and-drop file selection area |
| `FormatBadge` | 1, 3 | Format pill badge (CSV, PDF, etc.) |
| `FileQueueItem` | 1 | Single file row in queue |
| `FileQueueList` | 1 | Full queue list with remove buttons |
| `FileProgressRow` | 2 | Per-file progress bar with status |
| `UploadProgress` | 2 | Overall progress view |
| `UploadProgressSteps` | 2 | Step indicators (upload → parse → validate) |
| `BatchSummary` | 3 | Results cards with links |

---

## Type Definitions

```typescript
type BatchPhase = 'idle' | 'processing' | 'completed'

type FileStatus =
  | 'queued'
  | 'uploading'
  | 'parsing'
  | 'validating'
  | 'complete'
  | 'error'

interface BatchFile {
  id: string              // UUID
  file: File              // Original File object
  name: string            // Display name
  size: number            // File size in bytes
  format: string          // File extension
  status: FileStatus
  progress: number        // 0-100
  uploadId?: string       // Backend upload UUID
  validationId?: string   // Backend validation UUID
  errorCount?: number
  warningCount?: number
  infoCount?: number
  error?: string          // Error message if failed
}
```

---

## Constants

```typescript
// Maximum file sizes
const MAX_FILE_SIZE = 50 * 1024 * 1024        // 50 MB for regular files
const MAX_ARCHIVE_SIZE = 200 * 1024 * 1024     // 200 MB for archives

// Accepted MIME types / extensions
const ACCEPT_CONFIG = {
  'text/csv': ['.csv'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/json': ['.json'],
  'application/pdf': ['.pdf'],
  'application/zip': ['.zip'],
  'application/x-tar': ['.tar'],
  'application/gzip': ['.gz'],
  'application/x-rar-compressed': ['.rar'],
}

// Format icons (for display)
const FORMAT_ICONS = {
  csv: FileSpreadsheet,
  xlsx: FileSpreadsheet,
  json: FileJson,
  pdf: FileText,
  zip: Archive,
  tar: Archive,
  gz: Archive,
  rar: Archive,
}
```
