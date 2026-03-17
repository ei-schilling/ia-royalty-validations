/** HTTP client for the Royalty Statement Validator API. */

import type {
  TokenResponse,
  UserResponse,
  UploadResponse,
  UploadHistoryItem,
  ValidationRunStarted,
  ValidationRunResponse,
  ValidationIssueSummary,
} from './types'

const BASE = '/api'

function getToken(): string | null {
  return localStorage.getItem('rsv_token')
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = { ...authHeaders(), ...Object.fromEntries(new Headers(init?.headers)) }
  const res = await fetch(`${BASE}${path}`, { ...init, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

/** Register a new user. */
export function register(nickname: string, password: string) {
  return request<TokenResponse>('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nickname, password }),
  })
}

/** Login with nickname + password. */
export function login(nickname: string, password: string) {
  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nickname, password }),
  })
}

/** Get the currently authenticated user. */
export function getMe() {
  return request<UserResponse>('/auth/me')
}

/** Upload a file for validation. */
export function uploadFile(file: File) {
  const form = new FormData()
  form.append('file', file)
  return request<UploadResponse>('/uploads/', { method: 'POST', body: form })
}

/** List all uploads for the current user, newest first. */
export function listUploads() {
  return request<UploadHistoryItem[]>('/uploads/')
}

/** Get upload details by ID. */
export function getUpload(uploadId: string) {
  return request<UploadResponse>(`/uploads/${uploadId}`)
}

/** Trigger a validation run. */
export function triggerValidation(uploadId: string, rules: string[] = ['all']) {
  return request<ValidationRunStarted>(`/validations/${uploadId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rules }),
  })
}

/** Get full validation run results. */
export function getValidation(validationId: string) {
  return request<ValidationRunResponse>(`/validations/${validationId}`)
}

/** Get paginated validation issues. */
export function getValidationIssues(validationId: string, page = 1, size = 50, severity?: string) {
  const params = new URLSearchParams({ page: String(page), size: String(size) })
  if (severity) params.set('severity', severity)
  return request<ValidationIssueSummary[]>(`/validations/${validationId}/issues?${params}`)
}

/** Download validation report as PDF. */
export async function downloadValidationPdf(validationId: string) {
  const token = getToken()
  const res = await fetch(`${BASE}/validations/${validationId}/pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  const blob = await res.blob()
  const disposition = res.headers.get('Content-Disposition')
  const match = disposition?.match(/filename="?([^"]+)"?/)
  const filename = match?.[1] ?? `validation_${validationId}.pdf`
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/** Download annotated PDF with highlighted issues in the original data. */
export async function downloadAnnotatedPdf(validationId: string) {
  const token = getToken()
  const res = await fetch(`${BASE}/validations/${validationId}/annotated-pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  const blob = await res.blob()
  const disposition = res.headers.get('Content-Disposition')
  const match = disposition?.match(/filename="?([^"]+)"?/)
  const filename = match?.[1] ?? `validation_${validationId}_annotated.pdf`
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
