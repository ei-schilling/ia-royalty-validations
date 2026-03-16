/** HTTP client for the Royalty Statement Validator API. */

import type {
  UserResponse,
  UploadResponse,
  ValidationRunStarted,
  ValidationRunResponse,
  ValidationIssueSummary,
} from './types';

const BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

/** Register or find user by nickname. */
export function identify(nickname: string) {
  return request<UserResponse>('/auth/identify', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nickname }),
  });
}

/** Upload a file for validation. */
export function uploadFile(file: File, userId: string) {
  const form = new FormData();
  form.append('file', file);
  form.append('user_id', userId);
  return request<UploadResponse>('/uploads/', { method: 'POST', body: form });
}

/** Get upload details by ID. */
export function getUpload(uploadId: string) {
  return request<UploadResponse>(`/uploads/${uploadId}`);
}

/** Trigger a validation run. */
export function triggerValidation(uploadId: string, rules: string[] = ['all']) {
  return request<ValidationRunStarted>(`/validations/${uploadId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rules }),
  });
}

/** Get full validation run results. */
export function getValidation(validationId: string) {
  return request<ValidationRunResponse>(`/validations/${validationId}`);
}

/** Get paginated validation issues. */
export function getValidationIssues(
  validationId: string,
  page = 1,
  size = 50,
  severity?: string,
) {
  const params = new URLSearchParams({ page: String(page), size: String(size) });
  if (severity) params.set('severity', severity);
  return request<ValidationIssueSummary[]>(
    `/validations/${validationId}/issues?${params}`,
  );
}
