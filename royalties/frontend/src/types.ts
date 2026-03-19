/** API response and request types matching the backend Pydantic schemas. */

export interface UserResponse {
  user_id: string
  nickname: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserResponse
}

export interface UploadResponse {
  upload_id: string
  filename: string
  file_format: string
  row_count: number | null
  status: string
  uploaded_at: string
}

export interface UploadContentResponse {
  format: string
  filename: string
  headers: string[]
  rows: string[][]
  raw: string
  total_rows: number | null
}

export interface ValidationIssueSummary {
  id: string
  severity: 'error' | 'warning' | 'info'
  rule_id: string
  rule_description: string
  row_number: number | null
  field: string | null
  expected_value: string | null
  actual_value: string | null
  message: string
  context: Record<string, unknown> | null
}

export interface ValidationSummary {
  total_rows: number
  rules_executed: number
  passed_checks: number
  warnings: number
  errors: number
  infos: number
}

export interface ValidationRunResponse {
  validation_id: string
  upload_id: string
  status: string
  started_at: string | null
  completed_at: string | null
  summary: ValidationSummary
  issues: ValidationIssueSummary[]
}

export interface ValidationRunStarted {
  validation_id: string
  status: string
}

export interface ValidationRunBrief {
  validation_id: string
  status: string
  errors: number
  warnings: number
  infos: number
  completed_at: string | null
}

export interface UploadHistoryItem {
  upload_id: string
  filename: string
  file_format: string
  row_count: number | null
  uploaded_at: string
  validations: ValidationRunBrief[]
}

// Re-export batch upload types from the feature module
export type {
  BatchFile,
  FileStatus,
  FileFormat,
  BatchPhase,
  ProgressEvent,
  FileSummary,
  BatchUploadResponse,
  BatchValidationStarted,
} from './features/uploads/types'
