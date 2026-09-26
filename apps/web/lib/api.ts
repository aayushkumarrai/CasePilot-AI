import { getSupabaseBrowserClient } from '@/lib/supabase'

export type CaseStatus = 'draft' | 'processing' | 'review' | 'ready'

export type CaseRecord = { id: string; case_id: string; case_name: string; status: CaseStatus; created_at: string; updated_at: string; archived_at: string | null }

export type DashboardResponse = { metrics: { total_cases: number; draft_cases: number; in_review: number; ready_cases: number; pending_tasks: number; unresolved_issues: number }; cases: CaseRecord[]; recent_activity: Array<{ id: string; action: string; actor_type: 'user' | 'ai' | 'system'; details: Record<string, unknown>; created_at: string }> }
export type DocumentStatus = 'uploaded' | 'processing' | 'ready' | 'failed' | 'unsupported'
export type Document = { id: string; case_id: string; file_name: string; content_type: string; size_bytes: number; status: DocumentStatus; error_message: string | null; created_at: string; updated_at: string }
export type DocumentPassage = { id: string; sequence_number: number; page_number: number | null; passage_label: string; content: string; created_at: string }
export type DocumentDetail = Document & { passages: DocumentPassage[]; read_url: string | null }
export type SignedUpload = { storage_path: string; upload_url: string; expires_in_seconds: number }

export class ApiError extends Error { constructor(message: string, public readonly status: number, public readonly details?: unknown) { super(message); this.name = 'ApiError' } }

function errorMessage(payload: unknown): string {
  if (typeof payload === 'object' && payload !== null && 'detail' in payload) {
    const detail = payload.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((item) => typeof item === 'object' && item && 'msg' in item ? String(item.msg) : String(item)).join(' ')
  }
  return 'Request failed. Please try again.'
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data: { session } } = await getSupabaseBrowserClient().auth.getSession()
  if (!session) throw new ApiError('Please sign in again.', 401)
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
  if (!baseUrl) throw new Error('CasePilot API is not configured. Add NEXT_PUBLIC_API_BASE_URL to apps/web/.env.local.')
  const response = await fetch(`${baseUrl}${path}`, { ...init, headers: { Authorization: `Bearer ${session.access_token}`, ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers } })
  if (response.status === 204) return undefined as T
  const payload: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const error = new ApiError(errorMessage(payload), response.status, payload)
    if (response.status === 401 && typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('casepilot:unauthorized'))
    throw error
  }
  return payload as T
}

export const caseApi = {
  dashboard: () => apiFetch<DashboardResponse>('/dashboard'),
  list: (includeArchived = false) => apiFetch<CaseRecord[]>(`/cases${includeArchived ? '?include_archived=true' : ''}`),
  get: (caseId: string) => apiFetch<CaseRecord>(`/cases/${caseId}`),
  create: (payload: { case_id: string; case_name: string }) => apiFetch<CaseRecord>('/cases', { method: 'POST', body: JSON.stringify(payload) }),
  update: (caseId: string, payload: { case_id?: string; case_name?: string }) => apiFetch<CaseRecord>(`/cases/${caseId}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  archive: (caseId: string) => apiFetch<void>(`/cases/${caseId}`, { method: 'DELETE' }),
  restore: (caseId: string) => apiFetch<CaseRecord>(`/cases/${caseId}/restore`, { method: 'POST' }),
}

export const documentApi = {
  requestUploadUrl: (caseId: string, payload: { file_name: string; content_type: string; size_bytes: number }) => apiFetch<SignedUpload>(`/cases/${caseId}/documents/upload-url`, { method: 'POST', body: JSON.stringify(payload) }),
  register: (caseId: string, payload: { file_name: string; content_type: string; size_bytes: number; storage_path: string | null }) => apiFetch<Document>(`/cases/${caseId}/documents`, { method: 'POST', body: JSON.stringify(payload) }),
  list: (caseId: string) => apiFetch<Document[]>(`/cases/${caseId}/documents`),
  get: (documentId: string) => apiFetch<DocumentDetail>(`/documents/${documentId}`),
  retry: (documentId: string) => apiFetch<Document>(`/documents/${documentId}/retry`, { method: 'POST' }),
}

export async function uploadToSignedUrl(file: File, uploadUrl: string, contentType: string): Promise<void> {
  const response = await fetch(uploadUrl, { method: 'PUT', headers: { 'Content-Type': contentType }, body: file })
  if (!response.ok) throw new Error('The file upload failed. Please try that file again.')
}

export type Citation = { document_id: string; document_name: string; passage_id: string; passage_label: string; page_number: number | null; quote: string }
export type AnalysisRun = { id: string; status: 'queued' | 'processing' | 'completed' | 'failed'; started_at: string | null; completed_at: string | null; error_message: string | null }
export type AnalysisStatus = { run: AnalysisRun | null; has_completed_outputs: boolean }
export type DocumentSummary = { id: string; document_id: string; document_name: string; summary: string; citations: Citation[] }
export type ReviewField = { id: string; field_key: string; label: string; value: string; status: 'pending' | 'confirmed' | 'rejected'; citations: Citation[] }
export type ReviewParty = { id: string; name: string; role: string; status: 'pending' | 'confirmed' | 'rejected'; citations: Citation[] }
export type TimelineEvent = { id: string; event_date_text: string; date_confidence: 'exact' | 'month' | 'year' | 'unknown'; title: string; description: string; citations: Citation[] }
export type Finding = { id: string; kind: 'conflict' | 'gap'; title: string; description: string; citations: Citation[] }
export type ReviewTask = { id: string; finding_id: string | null; title: string; description: string; status: string; citations: Citation[] }
export type ReviewActivity = { id: string; action: string; actor_type: string; details: Record<string, unknown>; created_at: string }
export type OverviewResponse = { case: CaseRecord; analysis_run: { id: string; completed_at: string | null } | null; lawyer_context: string | null; case_summary: string | null; case_summary_citations: Citation[]; document_summaries: DocumentSummary[]; fields: { pending: ReviewField[]; confirmed: ReviewField[]; rejected: ReviewField[] }; parties: ReviewParty[]; latest_issues: Finding[]; pending_tasks: ReviewTask[]; counts: { document_summaries: number; pending_fields: number; confirmed_fields: number; rejected_fields: number; parties: number; issues: number; pending_tasks: number } }

export const analysisApi = {
  start: (caseId: string, payload: { lawyer_context: string | null }) => apiFetch<AnalysisRun>(`/cases/${caseId}/analysis`, { method: 'POST', body: JSON.stringify(payload) }),
  status: (caseId: string) => apiFetch<AnalysisStatus>(`/cases/${caseId}/analysis`),
  overview: (caseId: string) => apiFetch<OverviewResponse>(`/cases/${caseId}/overview`),
  timeline: (caseId: string) => apiFetch<TimelineEvent[]>(`/cases/${caseId}/timeline`),
  issues: (caseId: string) => apiFetch<Finding[]>(`/cases/${caseId}/issues`),
  tasks: (caseId: string) => apiFetch<ReviewTask[]>(`/cases/${caseId}/tasks`),
  activity: (caseId: string) => apiFetch<ReviewActivity[]>(`/cases/${caseId}/activity`),
}

export const evidenceHref = (caseId: string, citation: Citation) => `/cases/${caseId}/documents?document=${citation.document_id}&passage=${citation.passage_id}`
