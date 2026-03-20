# 17 — PDF Report Generation

## Overview

The application generates two types of PDF reports from validation results:

1. **Styled Validation Report** — Executive summary of findings
2. **Annotated Data PDF** — Full source data with highlighted issue cells

Both are generated on-demand and streamed as binary downloads.

---

## Styled Validation Report

**Endpoint**: `GET /api/validations/{validation_id}/pdf`
**Service**: `backend/app/services/pdf_service.py`
**Library**: ReportLab

### Content

The PDF includes:

#### Header Section
- Application title ("Royalty Statement Validator")
- Original filename
- Validation date and time
- Summary counts in a colored bar:
  - 🔴 Errors: N
  - 🟡 Warnings: N
  - 🔵 Info: N
  - ✅ Passed: N

#### Per-Rule Sections

For each of the 11 validation rules:
- Rule name and description
- Pass ✅ or Fail ❌ indicator
- Issue count (if any)

#### Issue Detail Table

| Column | Content |
|--------|---------|
| Severity | Color-coded badge (red/amber/blue) |
| Rule | Rule ID |
| Row | Source row number |
| Field | Column name with the issue |
| Expected | What the value should be |
| Actual | What the value was |
| Message | Human-readable description |

### Styling

- Professional layout with header/footer on each page
- Color-coded severity indicators
- Alternating row colors in tables
- Page numbers in footer
- Generated with ReportLab's Platypus layout engine

---

## Annotated Data PDF

**Endpoint**: `GET /api/validations/{validation_id}/annotated-pdf`
**Service**: `backend/app/services/annotated_pdf_service.py`
**Library**: ReportLab

### Content

The PDF renders the **original source data** as a table, with cells color-coded based on validation issues:

- 🔴 **Red background**: Cell triggered an ERROR-severity issue
- 🟡 **Amber background**: Cell triggered a WARNING-severity issue
- 🔵 **Blue background**: Cell triggered an INFO-severity issue
- ⬜ **White/default**: No issues on this cell

### Layout

```
┌─────────────────────────────────────────────────────────┐
│  Annotated Validation Report                             │
│  File: statement.csv | 1250 rows | 11 rules             │
│                                                          │
│  Legend: 🔴 Error  🟡 Warning  🔵 Info                   │
│                                                          │
│  ┌────────┬──────┬──────┬──────┬───────┬──────┬────────┐│
│  │TRANSNR │TYPE  │KONTO │ARTNR │ANTAL  │PRIS  │BELOEB  ││
│  ├────────┼──────┼──────┼──────┼───────┼──────┼────────┤│
│  │ 1001   │ Salg │ A042 │      │ 100   │249.95│2499.50 ││
│  │        │      │      │🔴    │       │      │        ││
│  ├────────┼──────┼──────┼──────┼───────┼──────┼────────┤│
│  │ 1002   │ Salg │ A042 │ 978  │ 50    │149.00│ 800.00 ││
│  │        │      │      │      │       │      │🟡      ││
│  └────────┴──────┴──────┴──────┴───────┴──────┴────────┘│
│                                                          │
│  Issue Summary:                                          │
│  Row 1: missing_titles — No product identifier (ARTNR)   │
│  Row 2: amount_consistency — Expected 745.00, got 800.00 │
└─────────────────────────────────────────────────────────┘
```

### Features

- Full source data rendered in tabular format
- Color-coded highlighting on specific cells
- Issue summary at the end of the document
- Handles wide tables with horizontal overflow (landscape orientation if needed)
- Row numbers included for cross-reference

---

## PDF Download (Frontend)

### Styled Report

```typescript
async function downloadValidationPdf(validationId: string): Promise<Blob> {
  const response = await fetch(`/api/validations/${validationId}/pdf`, {
    headers: authHeaders()
  })
  return response.blob()
}
```

### Annotated PDF

```typescript
async function downloadAnnotatedPdf(validationId: string): Promise<Blob> {
  const response = await fetch(`/api/validations/${validationId}/annotated-pdf`, {
    headers: authHeaders()
  })
  return response.blob()
}
```

### Download Trigger

Both PDFs are downloaded by creating a temporary anchor element:

```typescript
const blob = await downloadValidationPdf(validationId)
const url = URL.createObjectURL(blob)
const a = document.createElement('a')
a.href = url
a.download = `validation-report-${validationId}.pdf`
a.click()
URL.revokeObjectURL(url)
```

---

## Document Preview (PDF Iframe)

Separately from report generation, uploaded PDF files can be previewed inline using an `<iframe>`:

```typescript
// Fetch PDF as blob (auth workaround for iframe)
const response = await fetch(`/api/uploads/${uploadId}/file?token=${token}`)
const blob = await response.blob()
const objectUrl = URL.createObjectURL(blob)

// Render in iframe
<iframe src={objectUrl} width="100%" height="600px" />
```

The token is passed as a query parameter since `<iframe>` cannot send custom Authorization headers.
