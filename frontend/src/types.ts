export type DocumentType = 'makalah' | 'laporan' | 'proposal' | 'jurnal' | 'lainnya'
export type StandardMode = 'satu' | 'campuran' | 'acuan'
export type JobStatus =
  | 'pending'
  | 'extracting'
  | 'composing'
  | 'parsing'
  | 'ai_classifying'
  | 'awaiting_review'
  | 'formatting'
  | 'rendering'
  | 'validating'
  | 'done'
  | 'error'
  | 'deleted'

export interface RuleProfile {
  mode?: StandardMode
  preset_id?: number
  university_slug?: string
  doc_type?: DocumentType
  groups?: Record<string, unknown>
}

export interface CoverData {
  jenis_dokumen?: string
  judul?: string
  nama_penulis?: string
  nim?: string
  dosen_pengampu?: string
  program_studi?: string
  fakultas?: string
  institusi?: string
  kota?: string
  tahun?: string
  logo_url?: string
  confidence?: number
}

export interface OutlineNode {
  id?: string
  role?: string
  title?: string
  text?: string
  confidence?: number
  ambiguous?: boolean
  children?: OutlineNode[]
}

export interface JobStatusResponse {
  job_id: string
  status: JobStatus
  progress_pct: number
  cover_data?: CoverData
  outline?: OutlineNode[]
  compatibility?: CompatibilityReport
  error_message?: string | null
}

export interface DownloadLink {
  url: string
  format: 'docx' | 'pdf'
  expires_at: number
}

export interface University {
  id: number
  nama: string
  slug: string
  aktif: boolean
}

export interface RuleGroup {
  key: string
  nama: string
  urutan: number
}

export interface RulePreset {
  id: number
  university_id?: number | null
  doc_type: string
  versi?: string
  sumber_pedoman?: string
  diverifikasi_pada?: string
}

export interface CompatibilityFinding {
  level: 'error' | 'warning' | 'info'
  group: string
  message: string
}

export interface CompatibilityReport {
  findings: CompatibilityFinding[]
  has_errors: boolean
  has_warnings: boolean
}

export interface RuleSummaryItem {
  group: string
  source: string
  value_summary: string
}
