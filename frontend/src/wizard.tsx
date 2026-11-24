import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api } from './api'
import type { CoverData, DocumentType, JobStatusResponse, OutlineNode, RuleProfile, StandardMode, University } from './types'

const documents: Array<{ id: DocumentType; title: string; detail: string; icon: string }> = [
  { id: 'makalah', title: 'Makalah', detail: 'Cover judul standar, kata pengantar, daftar isi bertitik rapi, Bab I–III, dan daftar pustaka.', icon: 'description' },
  { id: 'laporan', title: 'Laporan', detail: 'Lembar pengesahan, ringkasan, bab metodologi, daftar tabel/gambar, serta lampiran.', icon: 'check_circle' },
  { id: 'proposal', title: 'Proposal', detail: 'Latar belakang, rumusan masalah, tinjauan pustaka, matriks jadwal riset, serta anggaran.', icon: 'lightbulb' },
  { id: 'jurnal', title: 'Jurnal', detail: 'Format 2 kolom IMRAD presisi, abstrak dwibahasa, kata kunci, dan sitasi gaya IEEE / APA.', icon: 'menu_book' },
  { id: 'lainnya', title: 'Lainnya', detail: 'Struktur umum untuk dokumen yang belum punya jenis khusus atau format mandiri.', icon: 'account_balance' },
]

const modes: Array<{ id: StandardMode; title: string; detail: string; icon: string }> = [
  { id: 'acuan', title: 'Unggah Dokumen Acuan', detail: 'Tiru format dokumen senior / template DOCX. File langsung dihapus setelah dibaca.', icon: 'upload_file' },
  { id: 'satu', title: 'Pakai Standar Kampus', detail: 'Pustaka pedoman format resmi universitas yang sudah terverifikasi (UI, ITB, UGM, dll).', icon: 'school' },
  { id: 'campuran', title: 'Campuran per bagian', detail: 'Gabungkan sumber aturan dan cek kecocokan sebelum naskah asli diproses.', icon: 'tune' },
]

const coverFields: Array<[keyof CoverData, string]> = [
  ['judul', 'Judul'],
  ['nama_penulis', 'Nama penulis'],
  ['nim', 'NIM'],
  ['dosen_pengampu', 'Dosen pengampu'],
  ['program_studi', 'Program studi'],
  ['fakultas', 'Fakultas'],
  ['institusi', 'Institusi'],
  ['kota', 'Kota'],
  ['tahun', 'Tahun'],
]

function roleLabel(node: OutlineNode) {
  return node.role || node.title || node.text || 'Bagian tanpa label'
}

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    pending: 'Menunggu antrean',
    extracting: 'Membaca dokumen acuan',
    composing: 'Menyusun aturan format',
    parsing: 'Menganalisis struktur naskah',
    ai_classifying: 'Mengelompokkan bagian ambigu',
    awaiting_review: 'Menunggu pemeriksaan kamu',
    formatting: 'Menerapkan format dokumen',
    rendering: 'Menyiapkan hasil cetak',
    validating: 'Memvalidasi hasil akhir',
    done: 'Selesai, siap diunduh',
    error: 'Pemrosesan gagal',
  }
  return labels[status ?? ''] ?? 'Memproses dokumen'
}

function flatten(nodes: OutlineNode[] = [], depth = 0): Array<{ node: OutlineNode; depth: number }> {
  return nodes.flatMap((node) => [{ node, depth }, ...flatten(node.children, depth + 1)])
}

export function Wizard() {
  const [step, setStep] = useState(1)
  const [token, setToken] = useState('')
  const [docType, setDocType] = useState<DocumentType>('makalah')
  const [mode, setMode] = useState<StandardMode>('satu')
  const [universities, setUniversities] = useState<University[]>([])
  const [university, setUniversity] = useState('akademik-umum-indonesia')
  const [file, setFile] = useState<File>()
  const [reference, setReference] = useState<File>()
  const [logo, setLogo] = useState<File>()
  const [selectedRules, setSelectedRules] = useState<string[]>(['penomoran_halaman'])
  const [text, setText] = useState('')
  const [cover, setCover] = useState<CoverData>({})
  const [job, setJob] = useState<JobStatusResponse>()
  const [outline, setOutline] = useState<OutlineNode[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [removed, setRemoved] = useState(false)

  const profile = useMemo<RuleProfile>(() => ({ mode, doc_type: docType, university_slug: university || undefined, groups: { enabled: selectedRules } }), [docType, mode, university, selectedRules])
  const rows = flatten(outline)

  useEffect(() => {
    api.universities().then(setUniversities).catch(() => setUniversities([]))
  }, [])

  useEffect(() => {
    if (!token || !job || !['pending', 'extracting', 'composing', 'parsing', 'ai_classifying', 'formatting', 'rendering', 'validating'].includes(job.status)) return
    const timer = window.setTimeout(async () => {
      try {
        const next = await api.status(token, job.job_id)
        setJob(next)
        if (next.cover_data) setCover(next.cover_data)
        if (next.outline) setOutline(next.outline)
        if (next.status === 'awaiting_review') setStep(4)
        if (next.status === 'done') setStep(5)
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : 'Status job gagal dibaca.')
      }
    }, 1800)
    return () => window.clearTimeout(timer)
  }, [job, token])

  async function ensureSession() {
    if (token) return token
    const saved = sessionStorage.getItem('rapiindoc-session')
    if (saved) {
      setToken(saved)
      return saved
    }
    const session = await api.createSession()
    sessionStorage.setItem('rapiindoc-session', session.session_token)
    setToken(session.session_token)
    return session.session_token
  }

  async function createConfiguredJob(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const activeToken = await ensureSession()
      const created = await api.createJob(activeToken, { doc_type: docType, standard_mode: mode, rule_profile: profile })
      setJob(created)
      if (mode === 'acuan' && reference) {
        const form = new FormData()
        form.set('file', reference)
        await api.uploadReference(activeToken, created.job_id, form)
      }
      setStep(3)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Job gagal dibuat.')
    } finally {
      setBusy(false)
    }
  }

  async function upload(event: FormEvent) {
    event.preventDefault()
    if (!job) return
    setBusy(true)
    setError('')
    try {
      const form = new FormData()
       if (file) form.set('file', file)
       if (logo) form.set('logo', logo)
       if (text.trim()) form.set('pasted_text', text)
      const next = await api.uploadDocument(token, job.job_id, form)
      setJob(next)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Dokumen gagal diunggah.')
    } finally {
      setBusy(false)
    }
  }

  async function submitReview(event: FormEvent) {
    event.preventDefault()
    if (!job) return
    setBusy(true)
    setError('')
    try {
      const next = await api.review(token, job.job_id, { corrected_outline: outline, cover_data: cover, rule_profile: profile })
      setJob(next)
      setStep(5)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Review gagal dikirim.')
    } finally {
      setBusy(false)
    }
  }

  async function removeNow() {
    if (!job) return
    await api.remove(token, job.job_id)
    setRemoved(true)
  }

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <header className="fixed top-0 w-full z-50 bg-surface/90 backdrop-blur-xl border-b-2 border-tinta/10">
        <div className="h-20 max-w-7xl mx-auto px-6 md:px-12 flex items-center justify-between">
          <Link className="flex items-center gap-3" to="/">
            <div className="w-9 h-9 rounded-lg bg-permen border-2 border-tinta flex items-center justify-center transform -rotate-6 shadow-sticker-sm">
              <span className="material-symbols-outlined text-[20px]">attach_file</span>
            </div>
            <span className="font-serif text-2xl font-bold text-on-surface tracking-tight">RapiInDoc</span>
          </Link>
          <div className="hidden xl:flex items-center gap-2 px-3 py-1 bg-white rounded-full border border-tinta shadow-sticker-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-daun animate-pulse"></span>
            <span className="font-mono text-[10px] uppercase font-bold text-tinta/70">Tanpa login • Dokumen tidak disimpan</span>
          </div>
          <div className="flex items-center gap-2 font-mono text-[11px] font-bold uppercase">
            <span>Langkah {step} dari 5</span>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className={`w-2.5 h-2.5 rounded-full border border-tinta ${step >= i ? 'bg-permen' : 'bg-white'}`}></div>
              ))}
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 pt-32 pb-24 px-6 md:px-12 max-w-[1280px] mx-auto w-full">
        <section className="bg-white border-2 border-tinta rounded-xl p-8 md:p-12 shadow-sticker relative overflow-hidden">
          <div className="absolute top-6 right-6 font-mono text-[11px] font-bold bg-langit px-3 py-1 rounded-full border border-tinta shadow-sticker-sm">
            {['1. Jenis', '2. Standar', '3. Naskah', '4. Struktur', '5. Hasil'][step - 1].toUpperCase()}
          </div>
          
          <h1 className="font-serif text-3xl md:text-5xl font-bold mb-4">
            {['Pilih jenis dokumen', 'Pakai standar yang mana?', 'Masukkan naskahmu', 'Cek struktur dokumenmu', 'Dokumenmu sudah rapi!'][step - 1]}
          </h1>
          <p className="text-tinta/80 max-w-2xl mb-8">
            {[
              'Pilih salah satu format dasar di bawah agar struktur bab, cover, dan penomorannya langsung pas tanpa pusing mikir layout manual.',
              'Tentukan apakah RapiInDoc harus meniru dokumen acuan seniormu, atau memakai preset pedoman resmi kampus yang sudah terverifikasi.',
              'Unggah draf berkas .docx yang masih berantakan atau langsung tempel naskah. RapiInDoc akan membedah struktur babnya secara instan.',
              'Pastikan urutan bab dan komponen sudah tepat. Kamu bisa mengubah penamaan, menentukan tipe bagian, atau melengkapi bagian yang terlewat.',
              'Format naskah telah disesuaikan dengan standar yang Anda pilih. Anda dapat mengunduh hasilnya sekarang.'
            ][step - 1]}
          </p>

          {error && <p className="bg-red-50 border-2 border-red-600 text-red-700 p-4 rounded-xl mb-6 font-bold">{error}</p>}

          {step === 1 && (
            <div className="space-y-10">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {documents.map((item) => (
                  <button key={item.id} onClick={() => setDocType(item.id)} className={`text-left p-6 rounded-2xl border-2 border-tinta transition-all flex flex-col gap-3 h-full ${docType === item.id ? 'bg-permen shadow-sticker active:translate-x-0.5 active:translate-y-0.5' : 'bg-white hover:bg-white/80'}`}>
                    <div className="w-10 h-10 rounded-xl bg-white border border-tinta flex items-center justify-center shadow-sticker-sm">
                      <span className="material-symbols-outlined">{item.icon}</span>
                    </div>
                    <h3 className="font-serif text-xl font-bold">{item.title}</h3>
                    <p className="text-xs text-tinta/70 leading-relaxed">{item.detail}</p>
                    {docType === item.id && <div className="mt-auto inline-flex items-center gap-1 font-mono text-[9px] font-bold bg-white px-2 py-0.5 rounded-full border border-tinta uppercase">✓ Terpilih</div>}
                  </button>
                ))}
              </div>
              <div className="flex justify-between items-center border-t-2 border-tinta/10 pt-8">
                <p className="text-sm font-mono text-tinta/60 max-w-sm">Struktur bab dapat Anda ubah, tambah, atau hapus sebelum proses kompilasi dimulai.</p>
                <button onClick={() => setStep(2)} className="inline-flex items-center gap-3 px-8 py-4 rounded-full bg-permen border-2 border-tinta font-bold text-sm tracking-wider uppercase shadow-sticker hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all">
                  Lanjut ke Standar
                  <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
                </button>
              </div>
            </div>
          )}

          {step === 2 && (
            <form className="space-y-10" onSubmit={createConfiguredJob}>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {modes.map((item) => (
                  <button type="button" key={item.id} onClick={() => setMode(item.id)} className={`text-left p-6 rounded-2xl border-2 border-tinta transition-all flex flex-col gap-3 ${mode === item.id ? 'bg-langit shadow-sticker' : 'bg-white'}`}>
                    <div className="w-10 h-10 rounded-xl bg-white border border-tinta flex items-center justify-center shadow-sticker-sm">
                      <span className="material-symbols-outlined">{item.icon}</span>
                    </div>
                    <h3 className="font-serif text-xl font-bold">{item.title}</h3>
                    <p className="text-xs text-tinta/70 leading-relaxed">{item.detail}</p>
                  </button>
                ))}
              </div>

              <div className="bg-surface-container-low border-2 border-tinta rounded-2xl p-6 space-y-6">
                <div className="space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div>
                      <label className="font-mono text-[11px] font-bold uppercase text-tinta/60">Yang ingin dirapikan</label>
                      <p className="text-xs text-tinta/60">Pilih satu atau beberapa bagian. Bagian lain tidak diubah.</p>
                    </div>
                    <button type="button" onClick={() => setSelectedRules(['halaman', 'tipografi', 'cover', 'bagian_awal', 'heading_bab', 'penomoran_halaman', 'daftar_isi', 'tabel_gambar', 'sitasi', 'daftar_pustaka', 'lampiran', 'header_footer'])} className="px-4 py-2 rounded-full bg-daun border-2 border-tinta font-bold text-xs uppercase shadow-sticker-sm">Rapikan semua</button>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                    {[['penomoran_halaman', 'Penomoran halaman'], ['halaman', 'Margin dan ukuran halaman'], ['tipografi', 'Font dan spasi'], ['cover', 'Cover dan logo'], ['heading_bab', 'Bab dan subbab'], ['daftar_isi', 'Daftar isi'], ['tabel_gambar', 'Tabel dan gambar'], ['sitasi', 'Sitasi'], ['daftar_pustaka', 'Daftar pustaka'], ['lampiran', 'Lampiran'], ['header_footer', 'Header dan footer']].map(([key, label]) => <label key={key} className="flex items-center gap-2 text-xs font-normal"><input type="checkbox" checked={selectedRules.includes(key)} onChange={(event) => setSelectedRules(event.target.checked ? [...selectedRules, key] : selectedRules.filter((item) => item !== key))} />{label}</label>)}
                  </div>
                </div>
                <div className="flex flex-col md:flex-row gap-6">
                  <div className="flex-1 space-y-2">
                    <label className="font-mono text-[11px] font-bold uppercase text-tinta/60">Pilih Preset Kampus / Standar</label>
                    <select value={university} onChange={(e) => setUniversity(e.target.value)} className="w-full p-4 rounded-xl border-2 border-tinta bg-white font-bold text-sm">
                      <option value="akademik-umum-indonesia">Standar Akademik Umum Indonesia</option>
                      <option value="apa-7">APA 7th Edition</option>
                      <option value="ieee">IEEE</option>
                      <option value="mla-9">MLA 9th Edition</option>
                      <option value="chicago-17">Chicago 17th Edition</option>
                      {universities.map((item) => <option key={item.id} value={item.slug}>{item.nama}</option>)}
                    </select>
                  </div>
                  <div className="flex-1 space-y-2">
                    <label className="font-mono text-[11px] font-bold uppercase text-tinta/60">Logo Universitas</label>
                    <input type="file" accept="image/png,image/jpeg,image/svg+xml" onChange={(e) => setLogo(e.target.files?.[0])} className="w-full p-3 rounded-xl border-2 border-tinta bg-white text-xs" />
                  </div>
                  {mode === 'acuan' && (
                    <div className="flex-1 space-y-2">
                      <label className="font-mono text-[11px] font-bold uppercase text-tinta/60">Dokumen Acuan (.DOCX)</label>
                      <div className="relative group">
                        <input type="file" accept=".docx" onChange={(e) => setReference(e.target.files?.[0])} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" />
                        <div className="p-4 rounded-xl border-2 border-dashed border-tinta bg-white flex items-center gap-3 transition-colors group-hover:bg-langit-light">
                          <span className="material-symbols-outlined text-tinta/40">upload_file</span>
                          <span className="text-sm font-bold truncate">{reference ? reference.name : 'Pilih file atau seret ke sini...'}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex justify-between items-center border-t-2 border-tinta/10 pt-8">
                <button type="button" onClick={() => setStep(1)} className="font-bold text-tinta hover:underline">← Kembali</button>
                <button disabled={busy} className="inline-flex items-center gap-3 px-8 py-4 rounded-full bg-permen border-2 border-tinta font-bold text-sm tracking-wider uppercase shadow-sticker disabled:opacity-50 disabled:translate-x-0 disabled:shadow-none transition-all">
                  {busy ? 'Menyiapkan...' : 'Buat Job & Lanjut'}
                  {!busy && <span className="material-symbols-outlined text-[20px]">arrow_forward</span>}
                </button>
              </div>
            </form>
          )}

          {step === 3 && (
            <form className="space-y-10" onSubmit={upload}>
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                <div className="lg:col-span-7 space-y-6">
                  <div className="space-y-2">
                    <label className="font-mono text-[11px] font-bold uppercase text-tinta/60">Unggah Berkas DOCX</label>
                    <div className="relative group min-h-[160px]">
                      <input type="file" accept=".docx" onChange={(e) => setFile(e.target.files?.[0])} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" />
                      <div className="absolute inset-0 rounded-2xl border-2 border-dashed border-tinta bg-surface-container-low flex flex-col items-center justify-center gap-2 group-hover:bg-white transition-all">
                        <span className="material-symbols-outlined text-4xl text-tinta/30">cloud_upload</span>
                        <span className="text-sm font-bold">{file ? file.name : 'Seret file DOCX ke sini atau klik untuk telusuri'}</span>
                        <span className="text-[10px] font-mono text-tinta/40">Maksimal 25 MB • Enkripsi Sisi Klien</span>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="font-mono text-[11px] font-bold uppercase text-tinta/60">Atau Tempel Naskahmu Langsung</label>
                    <textarea value={text} onChange={(e) => setText(e.target.value)} rows={10} className="w-full p-6 rounded-2xl border-2 border-tinta bg-white text-sm font-body leading-relaxed placeholder-tinta/30 focus:outline-none focus:ring-2 focus:ring-permen" placeholder="Tempel naskah mulai dari Bab 1 atau Halaman Judul di sini..."></textarea>
                  </div>
                </div>
                <div className="lg:col-span-5">
                  <div className="bg-langit/20 border-2 border-tinta rounded-2xl p-6 shadow-sticker h-full">
                    <div className="flex items-center gap-2 mb-4">
                      <span className="material-symbols-outlined text-tinta">auto_awesome</span>
                      <h3 className="font-bold text-sm uppercase tracking-wider">Identitas Terdeteksi</h3>
                    </div>
                    <div className="space-y-4">
                      <p className="text-[11px] text-tinta/60 leading-relaxed italic">RapiInDoc secara otomatis mengekstrak informasi identitas dari dokumen Anda. Anda dapat memeriksanya di langkah berikutnya.</p>
                      {job && (
                        <div className="p-4 bg-white rounded-xl border border-tinta shadow-sticker-sm space-y-2">
                          <p className="font-mono text-[10px] text-tinta/40">Status Antrean:</p>
                           <div className="flex items-center justify-between gap-3">
                             <span className="font-bold text-xs uppercase">{statusLabel(job.status)}</span>
                             <span className="font-mono text-[10px] font-bold">{job.progress_pct}%</span>
                           </div>
                           <div className="h-3 w-full bg-surface-container rounded-full overflow-hidden border border-tinta/20">
                             <div className="h-full bg-daun transition-all duration-500" style={{ width: `${Math.max(0, Math.min(100, job.progress_pct))}%` }}></div>
                           </div>
                           <p className="text-[10px] text-tinta/60">{job.status === 'error' ? job.error_message : `${job.progress_pct}% selesai. Jangan tutup halaman.`}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-center border-t-2 border-tinta/10 pt-8">
                <button type="button" onClick={() => setStep(2)} className="font-bold text-tinta hover:underline">← Kembali</button>
                <button disabled={busy || (!file && !text.trim())} className="inline-flex items-center gap-3 px-8 py-4 rounded-full bg-permen border-2 border-tinta font-bold text-sm tracking-wider uppercase shadow-sticker disabled:opacity-50 disabled:translate-x-0 disabled:shadow-none transition-all">
                  {busy ? 'Mengunggah...' : 'Kirim Naskah'}
                  {!busy && <span className="material-symbols-outlined text-[20px]">arrow_forward</span>}
                </button>
              </div>
            </form>
          )}

          {step === 4 && (
            <form className="space-y-10" onSubmit={submitReview}>
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                <div className="lg:col-span-5 space-y-6">
                  <div className="flex items-center justify-between">
                    <label className="font-mono text-[11px] font-bold uppercase text-tinta/60">Struktur Naskah</label>
                    <span className="font-mono text-[10px] px-2 py-0.5 bg-daun/20 border border-tinta rounded-full">Deteksi AI Selesai</span>
                  </div>
                  <div className="max-h-[500px] overflow-y-auto space-y-2 pr-2 scrollbar-hide">
                    {rows.length === 0 && <p className="bg-surface-container p-4 rounded-xl text-center text-xs text-tinta/40 font-bold italic">Menganalisis draf naskah... Tunggu sebentar.</p>}
                    {rows.map(({ node, depth }, index) => (
                      <div key={`${roleLabel(node)}-${index}`} className="group relative" style={{ marginLeft: depth * 12 }}>
                        <div className="bg-white border-2 border-tinta rounded-xl p-3 shadow-sticker-sm flex items-center gap-3 group-hover:bg-langit-light transition-colors">
                          <span className="material-symbols-outlined text-tinta/30 text-sm select-none">drag_indicator</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-[10px] font-mono text-tinta/40 truncate">{roleLabel(node)}</p>
                            <input value={node.role ?? ''} onChange={(e) => {
                              const next = structuredClone(outline)
                              flatten(next)[index].node.role = e.target.value
                              setOutline(next)
                            }} className="w-full bg-transparent border-none p-0 text-xs font-bold focus:ring-0" placeholder="Tetapkan peran..." />
                          </div>
                        </div>
                        {depth === 0 && <div className="absolute -left-3 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-tinta/20"></div>}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="lg:col-span-7 space-y-6">
                  <label className="font-mono text-[11px] font-bold uppercase text-tinta/60">Identitas Cover</label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-surface-container-low border-2 border-tinta rounded-2xl p-6">
                    {coverFields.map(([key, label]) => (
                      <div key={key} className="space-y-1">
                        <label className="text-[10px] font-bold uppercase text-tinta/50">{label}</label>
                        <input value={String(cover[key] ?? '')} onChange={(e) => setCover({ ...cover, [key]: e.target.value })} className="w-full p-2.5 rounded-lg border border-tinta/30 bg-white text-xs font-bold" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-center border-t-2 border-tinta/10 pt-8">
                <button type="button" onClick={() => setStep(3)} className="font-bold text-tinta hover:underline">← Perbaiki Naskah</button>
                <button disabled={busy} className="inline-flex items-center gap-3 px-8 py-4 rounded-full bg-permen border-2 border-tinta font-bold text-sm tracking-wider uppercase shadow-sticker disabled:opacity-50 transition-all">
                  {busy ? 'Memproses...' : 'Rapikan Sekarang'}
                  {!busy && <span className="material-symbols-outlined text-[20px]">auto_awesome</span>}
                </button>
              </div>
            </form>
          )}

          {step === 5 && (
            <div className="space-y-10">
              <div className="bg-daun/20 border-2 border-tinta rounded-3xl p-8 flex flex-col md:flex-row gap-8 items-center justify-between">
                <div className="space-y-2 text-left">
                  <div className="inline-flex items-center gap-2 px-3 py-1 bg-white rounded-full border border-tinta text-[10px] font-bold uppercase">🎉 Berhasil Diformal</div>
                  <h2 className="font-serif text-3xl font-bold">Naskah Anda siap unduh!</h2>
                  <p className="text-sm text-tinta/70 italic">File DOCX siap diedit kembali & PDF siap langsung cetak.</p>
                </div>
                <div className="flex flex-col gap-3 w-full md:w-auto">
                   {job?.status === 'done' && <ResultLinks token={token} jobId={job.job_id} />}
                    {job?.status !== 'done' && !removed && <div className="bg-white p-4 rounded-xl border-2 border-tinta text-left space-y-2 min-w-64" role="status" aria-live="polite"><div className="flex justify-between gap-4 font-mono text-xs font-bold uppercase"><span>{statusLabel(job?.status)}</span><span>{job?.progress_pct ?? 0}%</span></div><div className="h-3 w-full bg-surface-container rounded-full overflow-hidden border border-tinta/20"><div className="h-full bg-daun transition-all duration-500" style={{ width: `${Math.max(0, Math.min(100, job?.progress_pct ?? 0))}%` }}></div></div>{job?.status === 'error' ? <p className="text-xs text-red-700">{job.error_message || 'Pemrosesan gagal. Coba unggah ulang dokumen.'}</p> : <p className="text-[10px] text-tinta/60">Hasil unduhan aktif setelah proses mencapai 100%.</p>}</div>}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="bg-white border-2 border-tinta rounded-2xl p-6 shadow-sticker relative">
                  <h3 className="font-serif text-xl font-bold mb-4 flex items-center gap-2">
                    <span className="material-symbols-outlined text-daun">fact_check</span>
                    Laporan Kepatuhan
                  </h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-surface-container rounded-xl border border-tinta/10">
                      <span className="text-xs font-bold">Margin 4-4-3-3 Halaman Utama</span>
                      <span className="material-symbols-outlined text-daun text-sm">check_circle</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-surface-container rounded-xl border border-tinta/10">
                      <span className="text-xs font-bold">Normalisasi Times New Roman 12pt</span>
                      <span className="material-symbols-outlined text-daun text-sm">check_circle</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-surface-container rounded-xl border border-tinta/10">
                      <span className="text-xs font-bold">Penomoran Halaman Bertingkat</span>
                      <span className="material-symbols-outlined text-daun text-sm">check_circle</span>
                    </div>
                  </div>
                </div>
                <div className="bg-kertas/50 border-2 border-dashed border-tinta rounded-2xl p-6 flex flex-col justify-between">
                  <div className="space-y-2">
                    <h3 className="font-serif text-xl font-bold italic">Keamanan Naskah</h3>
                    <p className="text-xs text-tinta/60">Untuk privasi maksimal, Anda dapat menghapus data job segera setelah mengunduh berkas. Atau, biarkan sistem menghapusnya otomatis dalam 30 menit.</p>
                  </div>
                  <div className="flex items-center justify-between pt-4">
                    <span className="font-mono text-[10px] font-bold text-tinta/40">Sisa waktu: 29:54</span>
                    <button onClick={removeNow} disabled={removed} className={`px-4 py-2 rounded-full border border-tinta text-[10px] font-bold uppercase transition-all ${removed ? 'bg-daun' : 'bg-white hover:bg-red-50'}`}>
                      {removed ? 'Dihapus ✓' : 'Hapus Sekarang'}
                    </button>
                  </div>
                </div>
              </div>

              <div className="text-center pt-4">
                <Link to="/" className="font-bold text-tinta/60 hover:text-tinta underline">Selesai, kembali ke beranda</Link>
              </div>
            </div>
          )}
        </section>
      </main>
      <footer className="w-full bg-surface-container-low py-8 border-t-2 border-tinta/10">
        <div className="max-w-7xl mx-auto px-6 md:px-12 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-white rounded-full border border-tinta shadow-sticker-sm">
            <span className="material-symbols-outlined text-daun text-sm">shield_lock</span>
            <span className="font-mono text-[10px] font-bold uppercase">Enkripsi Client-Side • Tanpa Data di Server</span>
          </div>
          <p className="font-mono text-[10px] text-tinta/40">© 2025 RapiInDoc Personal Publishing.</p>
        </div>
      </footer>
    </div>
  )
}

function ResultLinks({ token, jobId }: { token: string; jobId: string }) {
  const [links, setLinks] = useState<Array<{ url: string; format: string }>>([])
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading')

  useEffect(() => {
    api.downloads(token, jobId)
      .then((items) => {
        setLinks(items.map((item) => ({ ...item, url: new URL(item.url, api.baseUrl).toString() })))
        setState('ready')
      })
      .catch(() => setState('error'))
  }, [jobId, token])

  if (state === 'loading') return <div className="animate-pulse flex gap-3 h-14 w-full md:w-64 bg-white rounded-full border-2 border-tinta shadow-sticker"></div>
  if (state === 'error') return <p className="text-red-600 font-bold text-xs uppercase px-4">Tautan belum tersedia.</p>
  async function download(link: { url: string; format: string }) {
    try {
      const blob = await api.downloadFile(token, link.url)
      const objectUrl = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = objectUrl
      anchor.download = `rapiindoc.${link.format}`
      anchor.click()
      URL.revokeObjectURL(objectUrl)
    } catch {
      setState('error')
    }
  }
  return (
    <div className="flex flex-col sm:flex-row gap-3 w-full justify-end">
      {links.map((link) => (
        <button type="button" key={link.format} onClick={() => download(link)} className={`inline-flex items-center justify-center gap-3 px-8 py-4 rounded-full border-2 border-tinta font-bold text-sm uppercase shadow-sticker transition-all hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none ${link.format === 'docx' ? 'bg-permen' : 'bg-white'}`}>
          <span className="material-symbols-outlined">{link.format === 'docx' ? 'description' : 'picture_as_pdf'}</span>
          Unduh {link.format.toUpperCase()}
         </button>
       ))}
    </div>
  )
}
