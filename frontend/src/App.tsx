import { BrowserRouter, Link, Route, Routes, useNavigate } from 'react-router-dom'
import { Wizard } from './wizard'
import { useState } from 'react'

const faqData = [
  {
    category: 'umum',
    title: 'Umum',
    questions: [
      ['Apakah RapiInDoc mengubah isi tulisanku?', 'Tidak. RapiInDoc hanya mengubah format, seperti margin, font, heading, daftar isi, dan nomor halaman. Kata-katamu tetap sama persis seperti aslinya.'],
      ['Perlu daftar akun?', 'Tidak perlu. Kamu bisa langsung mengunggah dokumen dan mengunduh hasilnya tanpa membuat akun atau memasukkan kata sandi apa pun.'],
      ['Dokumen apa yang bisa dirapikan?', 'Format Microsoft Word (.docx) seperti draf skripsi, tesis, proposal penelitian, makalah, hingga laporan magang.'],
    ]
  },
  {
    category: 'dokumen-acuan',
    title: 'Dokumen acuan',
    questions: [
      ['Apa itu dokumen acuan?', 'Contoh dokumen yang formatnya ingin kamu tiru, misalnya contoh skripsi atau template dari kampus. RapiInDoc membaca margin, font, spasi, dan gaya heading-nya.'],
      ['Bagaimana kalau aku tidak punya dokumen acuan?', 'Kamu bisa memilih standar bawaan yang sudah kami sediakan untuk berbagai kampus umum di Indonesia (misalnya margin 4-4-3-3, Times New Roman 12pt, spasi 1.5).'],
      ['Aturan hasil bacaan salah, bisa diubah?', 'Tentu saja bisa. Di layar konfirmasi sebelum proses dimulai, kamu bebas mengubah setiap aturan margin, ukuran font, perataan, maupun format bab.'],
    ]
  },
  {
    category: 'privasi',
    title: 'Privasi',
    questions: [
      ['Apakah dokumenku disimpan?', 'Tidak. File hanya ada sementara selama diproses dan dihapus otomatis. Kamu juga bisa menekan tombol Hapus sekarang setelah mengunduh berkas.'],
      ['Apakah AI membaca dokumenku?', 'Tidak ada model AI publik yang dilatih dengan naskahmu. Pemrosesan dilakukan murni secara algoritmik untuk tata letak struktural.'],
    ]
  },
  {
    category: 'hasil-dan-word',
    title: 'Hasil dan Word',
    questions: [
      ['Apakah hasilnya masih bisa diedit?', 'Ya. Hasil utama berupa DOCX standar dengan heading style asli, sehingga daftar isi dan penomoran otomatis tetap bisa kamu perbarui sewaktu-waktu di Microsoft Word.'],
      ['Kenapa nomor halaman di daftar isi bergeser?', 'Hal ini biasa terjadi ketika font bawaan di komputermu berbeda tipis. Cukup klik kanan pada daftar isi di Word, lalu pilih Update Field > Update entire table.'],
      ['Apa arti tanda Perlu dicek?', 'Tanda tersebut menandakan bagian seperti tabel berukuran sangat lebar atau rumus kompleks yang disarankan untuk ditinjau manual agar tidak meluber keluar margin.'],
    ]
  },
  {
    category: 'standar-kampus',
    title: 'Standar kampus',
    questions: [
      ['Kampus apa saja yang tersedia?', 'Kami menambahkannya bertahap. Kalau kampusmu belum ada di daftar, kamu cukup mengunggah file acuan atau contoh skripsi dari seniormu.'],
      ['Apakah hasilnya pasti sesuai pedoman kampusku?', 'Sistem mengikuti tepat parameter acuan yang dipilih. Kami tetap menyediakan pratinjau halaman demi halaman sebelum unduhan selesai.'],
    ]
  }
]

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/wizard" element={<Wizard />} />
        <Route path="/cara-kerja" element={<CaraKerja />} />
        <Route path="/standar-kampus" element={<StandarKampus />} />
        <Route path="/jenis-dokumen" element={<JenisDokumen />} />
        <Route path="/tanya-jawab" element={<TanyaJawab />} />
        <Route path="/privasi" element={<Privasi />} />
      </Routes>
    </BrowserRouter>
  )
}

function MainHeader() {
  return (
    <header className="sticky top-0 z-50 bg-kertas/90 backdrop-blur-md border-b-2 border-tinta/15 transition-all">
      <div className="max-w-[1440px] mx-auto px-6 md:px-12 h-20 flex items-center justify-between">
        <Link className="flex items-center gap-3 group" to="/">
          <div className="w-10 h-10 rounded-2xl bg-permen border-2 border-tinta flex items-center justify-center shadow-sticker-sm transform group-hover:-rotate-6 transition-transform">
            <svg className="w-6 h-6 text-tinta" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
              <path d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" strokeLinecap="round" strokeLinejoin="round"></path>
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="font-serif text-2xl font-bold tracking-tight text-tinta leading-none">RapiInDoc</span>
            <span className="font-mono text-[10px] tracking-wider text-tinta/70 uppercase">Format Kampus Otomatis</span>
          </div>
        </Link>
        <nav className="hidden md:flex items-center gap-8 font-medium text-sm text-tinta/80">
          <Link className="hover:text-tinta transition-colors py-1 relative hover:underline decoration-permen decoration-2 underline-offset-8" to="/cara-kerja">Cara kerja</Link>
          <Link className="hover:text-tinta transition-colors py-1 relative hover:underline decoration-langit decoration-2 underline-offset-8" to="/standar-kampus">Standar kampus</Link>
          <Link className="hover:text-tinta transition-colors py-1 relative hover:underline decoration-daun decoration-2 underline-offset-8" to="/jenis-dokumen">Jenis dokumen</Link>
          <Link className="hover:text-tinta transition-colors py-1 relative hover:underline decoration-bintang decoration-2 underline-offset-8" to="/tanya-jawab">Tanya jawab</Link>
        </nav>
        <div className="flex items-center gap-3">
          <Link className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-kertas border-2 border-tinta text-xs font-semibold uppercase tracking-wider shadow-sticker-sm hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] transition-all" to="/wizard">
            <span className="w-2.5 h-2.5 rounded-full bg-daun border border-tinta"></span>
            Rapikan dokumen
          </Link>
        </div>
      </div>
    </header>
  )
}

function MainFooter() {
  return (
    <footer className="bg-kertas border-t-2 border-tinta py-10 px-6 md:px-12 text-center text-xs text-tinta/70 font-mono">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-white rounded-full border-2 border-tinta shadow-sticker-sm">
          <span className="text-tertiary font-bold">🔒</span>
          <span className="font-bold uppercase">Enkripsi Sisi Klien Penuh • Tidak Ada Data yang Disimpan di Server</span>
        </div>
        <div>© 2025 RapiInDoc Personal Publishing. Hak Cipta Dilindungi Undang-Undang.</div>
      </div>
    </footer>
  )
}

function Landing() {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen bg-kertas text-tinta flex flex-col">
      <MainHeader />
      <main className="flex-1">
        <section className="relative pt-12 pb-24 px-6 md:px-12 bg-gradient-to-b from-langit/40 via-langit/15 to-kertas bg-paper-grid overflow-hidden border-b-2 border-tinta">
          <div className="max-w-[1280px] mx-auto text-center flex flex-col items-center relative z-10">
            <div className="inline-block relative mb-6 transform -rotate-2">
              <div className="bg-permen border-2 border-tinta px-4 py-1.5 rounded-full shadow-sticker-sm">
                <p className="font-mono text-xs font-semibold tracking-wide text-tinta uppercase">✦ Untuk yang deadline-nya sudah dekat</p>
              </div>
            </div>
            <h1 className="font-serif text-5xl md:text-7xl lg:text-8xl tracking-tight text-tinta leading-[1.04] max-w-5xl mb-6">
              Tulis dulu,<br className="hidden sm:inline" />
              <span className="relative inline-block mt-1">
                <span className="relative z-10 italic">rapikan</span> belakangan.
                <span className="absolute -bottom-2 left-0 right-0 h-4 bg-daun/60 -z-0 rounded-full transform -rotate-1"></span>
              </span>
            </h1>
            <p className="text-base md:text-xl text-tinta/80 max-w-2xl font-normal leading-relaxed mb-8">
              Unggah makalah, laporan, jurnal, atau proposal. <span className="font-semibold text-tinta">RapiInDoc</span> otomatis menyusun cover, margin, font, daftar isi bertitik, dan daftar pustaka sesuai standar kampusmu.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4 mb-4">
              <button onClick={() => navigate('/wizard')} className="inline-flex items-center gap-3 px-8 py-4 rounded-full bg-permen border-2 border-tinta font-bold text-sm tracking-wider uppercase shadow-sticker hover:shadow-none hover:translate-x-[3px] hover:translate-y-[3px] transition-all transform hover:-rotate-1">
                <span className="w-3 h-3 rounded-full bg-rose-500 border border-tinta animate-ping"></span>
                Mulai rapikan sekarang
                <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path d="M14 5l7 7m0 0l-7 7m7-7H3" strokeLinecap="round" strokeLinejoin="round"></path>
                </svg>
              </button>
              <Link to="/cara-kerja" className="inline-flex items-center gap-2 px-7 py-4 rounded-full bg-kertas border-2 border-tinta font-semibold text-sm tracking-wider uppercase shadow-sticker-sm hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] transition-all">
                Lihat contoh hasil
              </Link>
            </div>
            <div className="inline-flex items-center gap-2 font-mono text-xs text-tinta/70 mb-14 bg-white/70 px-4 py-1 rounded-full border border-tinta/20">
              Tanpa login. Dokumen diproses instan & tidak pernah disimpan.
            </div>

            <div className="relative w-full max-w-4xl mx-auto mt-2">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center justify-center relative">
                <div className="bg-white border-2 border-tinta rounded-xl p-6 shadow-paper transform -rotate-3 text-left">
                  <div className="flex items-center justify-between pb-3 border-b border-dashed border-red-300 mb-4">
                    <span className="font-mono text-[11px] font-bold text-red-600 bg-red-100 px-2.5 py-0.5 rounded-full border border-red-300">✕ Draf Berantakan</span>
                    <span className="font-mono text-[10px] text-tinta/40">Font campur aduk</span>
                  </div>
                  <div className="space-y-3 font-serif">
                    <div className="text-sm font-sans font-bold text-tinta underline decoration-red-400">bab 1 pendahuluan latar belakang msalah</div>
                    <p className="text-[12px] leading-relaxed font-sans text-tinta/70">dewasa ini penggunaan teknologi informasi sangat berpengaruh... namun demikian seringkali mahasiswa bingung menentukan margin.</p>
                  </div>
                </div>
                <div className="bg-white border-2 border-tinta rounded-xl p-6 shadow-paper transform rotate-2 text-left">
                  <div className="flex items-center justify-between pb-3 border-b-2 border-tinta/10 mb-4">
                    <span className="font-mono text-[11px] font-bold text-green-700 bg-daun/40 px-2.5 py-0.5 rounded-full border border-tinta">✓ Standar Kampus Rapi</span>
                    <span className="font-mono text-[10px] text-tinta/60">Times New Roman 12pt</span>
                  </div>
                  <div className="space-y-3 font-serif">
                    <div className="text-center font-bold text-xs uppercase tracking-wider text-tinta border-b border-neutral-200 pb-1">BAB I<br/>PENDAHULUAN</div>
                    <p className="text-[12px] leading-relaxed font-serif text-justify text-tinta indent-8">Perkembangan teknologi informasi memberikan dampak signifikan terhadap efisiensi administrasi akademik...</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="bg-kertas border-b-2 border-tinta overflow-hidden py-3 font-mono text-xs uppercase tracking-widest font-semibold">
          <div className="animate-ticker flex items-center gap-8">
            <span className="inline-flex items-center gap-2"><span>✦</span> Tanpa login</span>
            <span className="inline-flex items-center gap-2"><span>✦</span> Dokumen tidak pernah disimpan</span>
            <span className="inline-flex items-center gap-2"><span>✦</span> Hasil DOCX bisa diedit kembali</span>
            <span className="inline-flex items-center gap-2"><span>✦</span> Format cover & daftar isi otomatis</span>
            <span className="inline-flex items-center gap-2"><span>✦</span> Sesuai pedoman kampus Indonesia</span>
            <span className="inline-flex items-center gap-2"><span>✦</span> Unduh 100% Gratis</span>
            <span className="inline-flex items-center gap-2"><span>✦</span> Tanpa login</span>
            <span className="inline-flex items-center gap-2"><span>✦</span> Dokumen tidak pernah disimpan</span>
            <span className="inline-flex items-center gap-2"><span>✦</span> Hasil DOCX bisa diedit kembali</span>
            <span className="inline-flex items-center gap-2"><span>✦</span> Format cover & daftar isi otomatis</span>
            <span className="inline-flex items-center gap-2"><span>✦</span> Sesuai pedoman kampus Indonesia</span>
            <span className="inline-flex items-center gap-2"><span>✦</span> Unduh 100% Gratis</span>
          </div>
        </div>

        <section className="py-20 px-6 md:px-12 max-w-[1440px] mx-auto bg-paper-grid" id="dokumen">
          <div className="max-w-6xl mx-auto text-center">
            <div className="inline-block bg-permen border-2 border-tinta px-3 py-1 rounded-full font-mono text-xs font-bold uppercase mb-4 shadow-sticker-sm">Jenis tulisan</div>
            <h2 className="font-serif text-4xl lg:text-5xl font-bold tracking-tight text-tinta leading-tight mb-5">Dokumen yang bisa dirapikan.</h2>
            <p className="text-tinta/80 max-w-2xl mx-auto mb-8">Pilih struktur dokumen yang sesuai. RapiInDoc menyesuaikan cover, bab, daftar isi, sitasi, dan daftar pustaka.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 text-left">
              {[
                ['Makalah', 'Tugas kuliah, resensi, dan karya tulis dengan struktur Bab I–III.'],
                ['Laporan', 'Laporan PKL, praktikum, magang, lengkap dengan tabel dan lampiran.'],
                ['Proposal', 'Proposal penelitian, skripsi, hibah, kegiatan, jadwal, dan anggaran.'],
                ['Jurnal', 'Artikel ilmiah dengan abstrak, IMRAD, sitasi, dan referensi.'],
              ].map(([title, detail]) => <article key={title} className="bg-white border-2 border-tinta rounded-2xl p-5 shadow-sticker-sm"><h3 className="font-serif text-2xl font-bold mb-2">{title}</h3><p className="text-sm text-tinta/75 leading-relaxed">{detail}</p></article>)}
            </div>
          </div>
        </section>

        <section className="py-20 px-6 md:px-12 max-w-[1440px] mx-auto bg-paper-grid" id="standar-kampus">
          <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            <div className="lg:col-span-5 text-left">
              <div className="inline-block bg-langit border-2 border-tinta px-3 py-1 rounded-full font-mono text-xs font-bold uppercase mb-4 shadow-sticker-sm">Fleksibel & Cerdas</div>
              <h2 className="font-serif text-4xl lg:text-5xl font-bold tracking-tight text-tinta leading-tight mb-5">Pilih standar formatnya.</h2>
              <p className="text-tinta/80 text-base leading-relaxed mb-6">Punya contoh skripsi kating atau file template resmi dari fakultas? Cukup unggah sebagai dokumen acuan. RapiInDoc akan mendeteksi jenis font, ukuran margin, spasi baris, dan penomoran bab secara otomatis.</p>
            </div>
            <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="bg-white border-2 border-tinta rounded-3xl p-6 shadow-sticker">
                <div className="w-12 h-12 rounded-2xl bg-permen border-2 border-tinta flex items-center justify-center mb-5 shadow-sticker-sm font-bold">1</div>
                <h3 className="font-serif text-2xl font-bold text-tinta mb-2">Unggah Dokumen Acuan</h3>
                <p className="text-sm text-tinta/75 leading-relaxed">Unggah file skripsi kakak tingkat atau template .DOCX kampus. Sistem langsung meniru gaya layout-nya.</p>
              </div>
              <div className="bg-white border-2 border-tinta rounded-3xl p-6 shadow-sticker">
                <div className="w-12 h-12 rounded-2xl bg-daun border-2 border-tinta flex items-center justify-center mb-5 shadow-sticker-sm font-bold">2</div>
                <h3 className="font-serif text-2xl font-bold text-tinta mb-2">Pilih Standar Kampus</h3>
                <p className="text-sm text-tinta/75 leading-relaxed">Tersedia preset resmi: UI, ITB, UGM, Unpad, ITS, Undip, Brawijaya, Telkom Univ, dan puluhan kampus lain.</p>
              </div>
            </div>
          </div>
        </section>
      </main>
      <MainFooter />
    </div>
  )
}

function StandarKampus() {
  return (
    <div className="min-h-screen bg-kertas text-tinta flex flex-col">
      <MainHeader />
      <main className="flex-1 max-w-[1280px] mx-auto px-6 py-16 w-full">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="inline-block bg-langit border-2 border-tinta px-4 py-2 rounded-full font-mono text-xs font-bold uppercase mb-5 shadow-sticker-sm">Fleksibel & Cerdas</div>
          <h1 className="font-serif text-4xl md:text-6xl font-bold mb-5">Pilih standar formatnya.</h1>
          <p className="text-lg text-tinta/80">Gunakan preset kampus terverifikasi atau ambil aturan dari dokumen acuan.</p>
        </div>
        <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
          <article className="bg-white border-2 border-tinta rounded-3xl p-8 shadow-sticker"><div className="w-12 h-12 rounded-2xl bg-permen border-2 border-tinta flex items-center justify-center mb-5 shadow-sticker-sm font-bold">1</div><h2 className="font-serif text-3xl font-bold mb-3">Unggah Dokumen Acuan</h2><p className="text-tinta/75 leading-relaxed">Unggah file DOCX pedoman atau contoh dokumen. Sistem membaca aturan format yang terdeteksi.</p></article>
          <article className="bg-white border-2 border-tinta rounded-3xl p-8 shadow-sticker"><div className="w-12 h-12 rounded-2xl bg-daun border-2 border-tinta flex items-center justify-center mb-5 shadow-sticker-sm font-bold">2</div><h2 className="font-serif text-3xl font-bold mb-3">Pilih Standar Kampus</h2><p className="text-tinta/75 leading-relaxed">Pilih preset kampus yang tersedia, lalu gunakan sebagai standar dokumenmu.</p></article>
        </div>
        <div className="text-center mt-10"><Link className="inline-flex items-center px-8 py-4 rounded-full bg-permen border-2 border-tinta font-bold uppercase shadow-sticker" to="/wizard">Pilih standar di wizard</Link></div>
      </main>
      <MainFooter />
    </div>
  )
}

function JenisDokumen() {
  return (
    <div className="min-h-screen bg-kertas text-tinta flex flex-col">
      <MainHeader />
      <main className="flex-1 max-w-[1280px] mx-auto px-6 py-16 w-full">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="inline-block bg-daun border-2 border-tinta px-4 py-2 rounded-full font-mono text-xs font-bold uppercase mb-5 shadow-sticker-sm">Jenis tulisan</div>
          <h1 className="font-serif text-4xl md:text-6xl font-bold mb-5">Dokumen yang bisa dirapikan.</h1>
          <p className="text-lg text-tinta/80">Pilih jenis dokumen untuk melihat struktur yang disiapkan RapiInDoc.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {[
            ['Makalah Tugas Kuliah', 'Cover, kata pengantar, daftar isi, Bab I–III, dan daftar pustaka.'],
            ['Laporan Magang / Praktikum', 'Lembar pengesahan, daftar tabel dan gambar, bab, serta lampiran.'],
            ['Proposal Skripsi / Hibah', 'Pendahuluan, tinjauan pustaka, metode, jadwal, dan anggaran.'],
            ['Artikel Jurnal Ilmiah', 'Judul, abstrak, kata kunci, bagian IMRAD, dan referensi.'],
          ].map(([title, detail]) => <article key={title} className="bg-white border-2 border-tinta rounded-2xl p-6 shadow-sticker-sm"><h2 className="font-serif text-2xl font-bold mb-3">{title}</h2><p className="text-sm text-tinta/75 leading-relaxed">{detail}</p></article>)}
        </div>
        <div className="text-center mt-10"><Link className="inline-flex items-center px-8 py-4 rounded-full bg-permen border-2 border-tinta font-bold uppercase shadow-sticker" to="/wizard">Pilih jenis dokumen</Link></div>
      </main>
      <MainFooter />
    </div>
  )
}

function CaraKerja() {
  const navigate = useNavigate()
  return (
    <div className="min-h-screen bg-kertas text-tinta flex flex-col">
      <MainHeader />
      <main className="flex-1 max-w-[1280px] mx-auto px-6 py-16">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-langit text-tinta rounded-full border-2 border-tinta shadow-sticker-sm mb-4">
            <span className="font-mono text-xs font-bold uppercase">Alur kerja RapiInDoc</span>
          </div>
          <h1 className="font-serif text-4xl md:text-6xl font-bold mb-4">Begini cara RapiInDoc merapikan dokumenmu.</h1>
          <p className="text-lg text-tinta/80">Dari naskah mentah sampai file siap kumpul, tanpa daftar akun.</p>
        </div>

        <div className="space-y-12 mb-20">
          {[
            ['01', 'Pilih jenis dokumen', 'Makalah, laporan, proposal, atau jurnal. Setiap jenis punya susunan bagian yang berbeda.'],
            ['02', 'Tentukan standar', 'Pakai standar kampus, atau unggah dokumen acuan. RapiInDoc membaca margin, font, spasi, dan gaya heading-nya.'],
            ['03', 'Unggah atau tempel naskah', 'File DOCX atau teks mentah. Teks yang mirip cover otomatis masuk ke formulir cover.'],
            ['04', 'Cek struktur', 'Kamu melihat bagian mana yang sudah dikenali, dan bagian mana yang perlu dicek.'],
            ['05', 'Unduh hasilnya', 'DOCX yang masih bisa diedit, atau PDF. Setelah itu file dihapus.'],
          ].map(([num, title, desc]) => (
            <div key={num} className="bg-white border-2 border-tinta rounded-3xl p-8 shadow-sticker flex flex-col md:flex-row gap-6 items-center">
              <div className="w-16 h-16 rounded-2xl bg-permen border-2 border-tinta flex items-center justify-center font-mono text-xl font-bold shadow-sticker-sm shrink-0">{num}</div>
              <div className="flex-1 text-left">
                <h3 className="font-serif text-2xl font-bold mb-2">{title}</h3>
                <p className="text-tinta/80">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="text-center">
          <button onClick={() => navigate('/wizard')} className="inline-flex items-center gap-3 px-8 py-4 rounded-full bg-permen border-2 border-tinta font-bold text-sm tracking-wider uppercase shadow-sticker hover:shadow-none hover:translate-x-[3px] hover:translate-y-[3px] transition-all">
            Mulai rapikan dokumen
          </button>
        </div>
      </main>
      <MainFooter />
    </div>
  )
}

function TanyaJawab() {
  const [activeCat, setActiveCat] = useState('all')
  const [expanded, setExpanded] = useState<Record<string, boolean>>({ '0': true })

  return (
    <div className="min-h-screen bg-kertas text-tinta flex flex-col">
      <MainHeader />
      <main className="flex-1 max-w-4xl mx-auto px-6 py-16 w-full">
        <div className="text-center mb-12">
          <h1 className="font-serif text-4xl md:text-5xl font-bold mb-3">Ada yang mau ditanyakan?</h1>
          <p className="text-tinta/80">Jawaban singkat sebelum kamu mulai merapikan.</p>
        </div>

        <div className="flex flex-wrap gap-2 justify-center mb-10">
          <button onClick={() => setActiveCat('all')} className={`px-4 py-2 rounded-full border-2 border-tinta font-bold text-xs uppercase ${activeCat === 'all' ? 'bg-permen shadow-sticker-sm' : 'bg-white'}`}>Semua</button>
          {faqData.map((group) => (
            <button key={group.category} onClick={() => setActiveCat(group.category)} className={`px-4 py-2 rounded-full border-2 border-tinta font-bold text-xs uppercase ${activeCat === group.category ? 'bg-permen shadow-sticker-sm' : 'bg-white'}`}>{group.title}</button>
          ))}
        </div>

        <div className="space-y-8">
          {faqData.filter((g) => activeCat === 'all' || g.category === activeCat).map((group) => (
            <div key={group.category} className="space-y-4">
              <h2 className="font-serif text-2xl font-bold text-tinta border-b-2 border-tinta/20 pb-2">{group.title}</h2>
              {group.questions.map(([q, a], idx) => {
                const key = `${group.category}-${idx}`
                const isOpen = !!expanded[key]
                return (
                  <div key={key} className="bg-white border-2 border-tinta rounded-2xl shadow-sticker overflow-hidden">
                    <button onClick={() => setExpanded({ ...expanded, [key]: !isOpen })} className="w-full px-6 py-4 flex items-center justify-between text-left font-serif font-bold text-lg cursor-pointer">
                      <span>{q}</span>
                      <span>{isOpen ? '−' : '+'}</span>
                    </button>
                    {isOpen && <div className="px-6 pb-4 text-tinta/80 font-sans border-t border-tinta/10 pt-3">{a}</div>}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </main>
      <MainFooter />
    </div>
  )
}

function Privasi() {
  return (
    <div className="min-h-screen bg-kertas text-tinta flex flex-col">
      <MainHeader />
      <main className="flex-1 max-w-3xl mx-auto px-6 py-16 w-full space-y-6">
        <h1 className="font-serif text-4xl font-bold">Privasi & Keamanan</h1>
        <p className="text-tinta/80">RapiInDoc dirancang dengan prinsip privasi total (Zero Retention). Dokumen Anda hanya diproses di memori sementara dan langsung dihapus setelah Anda mengunduh hasilnya atau setelah sesi berakhir.</p>
        <div className="bg-white border-2 border-tinta rounded-2xl p-6 shadow-sticker space-y-3">
          <h2 className="font-serif text-xl font-bold">Enkripsi End-to-End</h2>
          <p className="text-sm text-tinta/80">Seluruh transfer data menggunakan SSL 256-bit kelas perbankan. Tidak ada pihak ketiga yang dapat membaca naskah Anda.</p>
        </div>
      </main>
      <MainFooter />
    </div>
  )
}
