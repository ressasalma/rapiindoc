import type {
  CompatibilityReport,
  DocumentType,
  DownloadLink,
  JobStatusResponse,
  RuleGroup,
  RulePreset,
  RuleProfile,
  RuleSummaryItem,
  StandardMode,
  University,
} from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers)
  if (token) headers.set('X-Session-Token', token)
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_URL}${path}`, { ...init, headers })
  if (!response.ok) {
    const detail = await response.text()
    throw new ApiError(response.status, detail || `Permintaan gagal (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  baseUrl: API_URL,
  createSession: () =>
    request<{ session_token: string; expires_in_seconds: number }>('/api/v1/session', { method: 'POST' }),
  createJob: (token: string, body: { doc_type: DocumentType; standard_mode: StandardMode; rule_profile: RuleProfile }) =>
    request<JobStatusResponse>('/api/v1/jobs', { method: 'POST', body: JSON.stringify(body) }, token),
  uploadDocument: (token: string, jobId: string, form: FormData) =>
    request<JobStatusResponse>(`/api/v1/jobs/${jobId}/upload`, { method: 'POST', body: form }, token),
  uploadReference: (token: string, jobId: string, form: FormData) =>
    request<{ extracted_groups: string[]; confidence: number }>(
      `/api/v1/jobs/${jobId}/reference`,
      { method: 'POST', body: form },
      token,
    ),
  status: (token: string, jobId: string) =>
    request<JobStatusResponse>(`/api/v1/jobs/${jobId}/status`, {}, token),
  review: (token: string, jobId: string, body: unknown) =>
    request<JobStatusResponse>(`/api/v1/jobs/${jobId}/review`, { method: 'POST', body: JSON.stringify(body) }, token),
  downloads: (token: string, jobId: string) =>
    request<DownloadLink[]>(`/api/v1/jobs/${jobId}/download-links`, {}, token),
  downloadFile: async (token: string, url: string) => {
    const response = await fetch(new URL(url, API_URL), { headers: { 'X-Session-Token': token } })
    if (!response.ok) throw new Error(`Unduhan gagal (${response.status})`)
    return response.blob()
  },
  compliance: (token: string, jobId: string) =>
    request<unknown>(`/api/v1/jobs/${jobId}/compliance`, {}, token),
  remove: (token: string, jobId: string) =>
    request<void>(`/api/v1/jobs/${jobId}`, { method: 'DELETE' }, token),
  universities: () => request<University[]>('/api/v1/presets/universities?aktif=true'),
  groups: () => request<RuleGroup[]>('/api/v1/presets/groups'),
  presets: (universitySlug: string, docType: DocumentType) =>
    request<RulePreset[]>(`/api/v1/presets/?university_slug=${encodeURIComponent(universitySlug)}&doc_type=${docType}`),
  compatibility: (profile: RuleProfile) =>
    request<CompatibilityReport>('/api/v1/rules/compatibility', { method: 'POST', body: JSON.stringify(profile) }),
  summary: (profile: RuleProfile) =>
    request<{ summary: RuleSummaryItem[] }>('/api/v1/rules/summary', { method: 'POST', body: JSON.stringify(profile) }),
}
