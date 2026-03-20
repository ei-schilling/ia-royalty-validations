# 04 — Backend API Reference

## Base URL

- **Docker**: `http://localhost:8000`
- **Local dev**: `http://localhost:8000`
- **Through Nginx**: `http://localhost/api/...`

All API endpoints are prefixed with `/api/` (except `/health`).

Interactive documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Authentication

All protected endpoints require a JWT bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens are obtained via `/api/auth/login` or `/api/auth/register`.

---

## Endpoints

### Health Check

#### `GET /health`

Returns service health status. No authentication required.

**Response** `200`:
```json
{
  "status": "ok"
}
```

---

### Auth — `/api/auth`

#### `POST /api/auth/register`

Create a new user account.

**Request Body**:
```json
{
  "nickname": "string (3-100 chars)",
  "password": "string (min 6 chars)"
}
```

**Response** `201`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "user_id": "uuid",
    "nickname": "string",
    "created_at": "2026-03-19T10:00:00Z"
  }
}
```

**Errors**:
- `400`: Nickname already taken
- `422`: Validation error (nickname too short, password too short)

---

#### `POST /api/auth/login`

Authenticate an existing user.

**Request Body**:
```json
{
  "nickname": "string",
  "password": "string"
}
```

**Response** `200`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "user_id": "uuid",
    "nickname": "string",
    "created_at": "2026-03-19T10:00:00Z"
  }
}
```

**Errors**:
- `401`: Invalid nickname or password

---

#### `GET /api/auth/me`

Get the currently authenticated user's profile.

**Auth**: Required (Bearer JWT)

**Response** `200`:
```json
{
  "user_id": "uuid",
  "nickname": "string",
  "created_at": "2026-03-19T10:00:00Z"
}
```

**Errors**:
- `401`: Invalid or expired token

---

### Uploads — `/api/uploads`

#### `POST /api/uploads/`

Upload a royalty statement file.

**Auth**: Required (Bearer JWT)

**Request**: `multipart/form-data`
- `file`: The file to upload

**Constraints**:
- Max size: 50 MB (configurable via `MAX_UPLOAD_SIZE_MB`)
- Allowed extensions: `csv`, `xlsx`, `json`, `pdf`, `zip`, `tar`, `gz`, `rar`

**Response** `201`:
```json
{
  "upload_id": "uuid",
  "filename": "afregning_20230410_126.csv",
  "file_format": "csv",
  "row_count": 1250,
  "uploaded_at": "2026-03-19T10:05:00Z"
}
```

**Errors**:
- `400`: Unsupported file type, file too large
- `401`: Unauthorized
- `422`: No file provided

---

#### `GET /api/uploads/`

List all uploads for the current user, newest first. Includes nested validation run summaries.

**Auth**: Required (Bearer JWT)

**Query Parameters**: None (limit 50)

**Response** `200`:
```json
[
  {
    "upload_id": "uuid",
    "filename": "afregning_20230410_126.csv",
    "file_format": "csv",
    "row_count": 1250,
    "uploaded_at": "2026-03-19T10:05:00Z",
    "validation_runs": [
      {
        "validation_id": "uuid",
        "status": "completed",
        "error_count": 2,
        "warning_count": 5,
        "info_count": 3,
        "completed_at": "2026-03-19T10:05:03Z"
      }
    ]
  }
]
```

---

#### `GET /api/uploads/{upload_id}`

Get details of a specific upload.

**Auth**: Required (Bearer JWT)

**Response** `200`:
```json
{
  "upload_id": "uuid",
  "filename": "afregning_20230410_126.csv",
  "file_format": "csv",
  "row_count": 1250,
  "uploaded_at": "2026-03-19T10:05:00Z"
}
```

**Errors**:
- `404`: Upload not found or not owned by current user

---

#### `GET /api/uploads/{upload_id}/content`

Get a preview of the file contents (up to 50,000 rows / 500 KB).

**Auth**: Required (Bearer JWT)

**Response** `200`:
```json
{
  "format": "csv",
  "headers": ["TRANSNR", "TRANSTYPE", "KONTO", "AFTALE", "ARTNR", ...],
  "rows": [
    {"TRANSNR": "1001", "TRANSTYPE": "Salg", "KONTO": "AUTH-0042", ...},
    ...
  ],
  "raw": null
}
```

For non-tabular formats (raw text), `rows` may be empty and `raw` contains the text content.

---

### Validations — `/api/validations`

#### `POST /api/validations/{upload_id}/run`

Trigger a validation run on an uploaded file.

**Auth**: Required (Bearer JWT)

**Request Body** (optional):
```json
{
  "rules": ["all"]
}
```

> Currently only `"all"` is supported. Future versions may allow selective rule execution.

**Response** `201`:
```json
{
  "validation_id": "uuid",
  "status": "completed"
}
```

---

#### `GET /api/validations/{validation_id}`

Get full validation results including summary and all issues.

**Auth**: Required (Bearer JWT)

**Response** `200`:
```json
{
  "validation_id": "uuid",
  "upload_id": "uuid",
  "status": "completed",
  "rules_executed": 11,
  "passed_count": 9,
  "warning_count": 5,
  "error_count": 2,
  "info_count": 3,
  "started_at": "2026-03-19T10:05:01Z",
  "completed_at": "2026-03-19T10:05:03Z",
  "issues": [
    {
      "id": "uuid",
      "severity": "error",
      "rule_id": "amount_consistency",
      "rule_description": "Quantity × Unit Price × Rate must equal the reported amount",
      "row_number": 47,
      "field": "BELOEB",
      "expected_value": "1250.00",
      "actual_value": "1350.00",
      "message": "Amount mismatch: expected 1250.00, got 1350.00 (diff: 100.00)",
      "context": {
        "agreement": "AFT-2024-001",
        "product": "978-87-1234-567-8"
      }
    }
  ]
}
```

---

#### `GET /api/validations/{validation_id}/issues`

Get paginated, filterable issues for a validation run.

**Auth**: Required (Bearer JWT)

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `severity` | string | all | Filter: `error`, `warning`, `info` |
| `page` | int | 1 | Page number (1-based) |
| `size` | int | 50 | Page size (max 200) |

**Response** `200`:
```json
[
  {
    "id": "uuid",
    "severity": "warning",
    "rule_id": "invalid_rates",
    "rule_description": "Royalty rate should be present and within valid bounds",
    "row_number": 23,
    "field": "STKAFREGNSATS",
    "expected_value": "0.01 - 1.00",
    "actual_value": "0.00",
    "message": "Zero royalty rate detected"
  }
]
```

---

#### `GET /api/validations/{validation_id}/pdf`

Download a styled PDF validation report.

**Auth**: Required (Bearer JWT)

**Response**: `application/pdf` binary

The PDF includes:
- Header with filename, date, summary counts
- Per-rule section with pass/fail status
- Detailed issue table with severity, row, field, message

---

#### `GET /api/validations/{validation_id}/annotated-pdf`

Download an annotated data PDF with all source rows and highlighted issue cells.

**Auth**: Required (Bearer JWT)

**Response**: `application/pdf` binary

The PDF shows the original data in a table format with cells color-coded by severity.

---

#### `POST /api/validations/batch`

Trigger batch validation on multiple uploads.

**Auth**: Required (Bearer JWT)

**Request Body**:
```json
{
  "upload_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response** `201`:
```json
{
  "batch_id": "uuid",
  "status": "processing"
}
```

---

#### `GET /api/validations/batch/{batch_id}/progress`

Subscribe to batch validation progress via Server-Sent Events (SSE).

**Auth**: Token passed as query parameter (`?token=<jwt>`)

**Response**: `text/event-stream`

**Event types**:
```
event: file_start
data: {"upload_id": "uuid", "filename": "file.csv"}

event: file_complete
data: {"upload_id": "uuid", "validation_id": "uuid", "error_count": 2, "warning_count": 5}

event: file_error
data: {"upload_id": "uuid", "error": "Parse error: invalid CSV format"}

event: batch_complete
data: {"total": 3, "completed": 3, "failed": 0}
```

---

### Chat — `/api/chat`

#### `POST /api/chat/stream`

Stream an AI chat response via Server-Sent Events.

**Auth**: None (public endpoint)

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | string | `query` | `query` (RAG), `chat` (direct), `agent` (SQL agent) |

**Request Body**:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Explain what STKAFREGNSATS means in a royalty statement"
    }
  ]
}
```

**Response**: `text/event-stream` (AG-UI protocol)

```
data: {"type":"RUN_STARTED","threadId":"uuid","runId":"uuid"}

data: {"type":"TEXT_MESSAGE_START","messageId":"uuid","role":"assistant"}

data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"uuid","delta":"STKAFREGNSATS is the "}

data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"uuid","delta":"settlement unit rate..."}

data: {"type":"TEXT_MESSAGE_END","messageId":"uuid"}

data: {"type":"RUN_FINISHED","threadId":"uuid","runId":"uuid"}
```

---

#### `POST /api/chat/upload`

Upload a file for analysis in the chat context.

**Auth**: None

**Request**: `multipart/form-data`
- `file`: The file to analyze

**Response** `200`:
```json
{
  "success": true,
  "document": {
    "title": "statement.csv",
    "type": "text/csv",
    "content": "TRANSNR;TRANSTYPE;KONTO;...\n1001;Salg;AUTH-0042;..."
  }
}
```

For images, `content` is replaced by a `dataUri` (base64).

---

## Error Response Format

All errors follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
| Code | Meaning |
|------|---------|
| `400` | Bad request (invalid input) |
| `401` | Unauthorized (missing/invalid token) |
| `404` | Resource not found |
| `422` | Validation error (Pydantic) |
| `500` | Internal server error |
