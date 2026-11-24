# RapiInDoc

Website untuk merapikan makalah, laporan, proposal, dan jurnal secara otomatis sesuai standar kampus. Unggah naskah mentah, pilih standar format, lalu unduh DOCX atau PDF yang sudah rapi: cover, daftar isi, bab dan subbab, penomoran halaman, sitasi, dan daftar pustaka.

> **Status:** tahap perencanaan. Spesifikasi lengkap ada di PRD v1.2. Belum ada rilis yang bisa dipakai.

## Prinsip

- **Hanya format yang diubah, bukan isi.** Kata-kata pengguna tidak ditulis ulang. Setiap proses ditutup dengan pemeriksaan integritas teks.
- **Tanpa login dan tanpa penyimpanan dokumen.** File hanya ada sementara selama diproses lalu dihapus otomatis. Tidak ada riwayat.
- **Transparan.** Laporan kepatuhan mencatat apa yang diubah, apa yang ditebak, apa yang tidak ditemukan, dan dari standar mana setiap aturan berasal.

## Fitur yang direncanakan

- **Jenis dokumen:** makalah, laporan, proposal, jurnal (skripsi dan jenis lain menyusul).
- **Tiga cara menentukan standar format:**
  1. **Satu standar:** preset kampus atau standar bawaan.
  2. **Campuran per bagian:** pilih standar dasar, lalu ganti sumber untuk bagian tertentu. Contoh: dasar kampus A, tetapi penomoran halaman mengikuti kampus B. Ada 12 bagian aturan yang bisa dipilih sumbernya, dengan pemeriksaan kompatibilitas antar bagian.
  3. **Dokumen acuan:** unggah contoh dokumen (mis. contoh skripsi atau template kampus) agar aturannya dibaca otomatis.
- **Input:** DOCX atau salin-tempel teks. Input PDF opsional di tahap lanjut.
- **Penanganan dokumen mentah:** teks yang menyerupai cover diubah menjadi formulir cover, heading diduga dari pola dan kata kunci, bagian yang ragu ditandai untuk direview.
- **Penomoran halaman multi-seksi:** cover, bagian awal (romawi), isi (arab), lampiran.
- **Daftar pustaka dan sitasi:** MVP mendukung APA 7. IEEE dan gaya lain menyusul.
- **Keluaran:** DOCX yang masih bisa diedit (daftar isi berbasis field) dan PDF, beserta laporan kepatuhan.
- **AI opsional:** hanya untuk blok yang ambigu. AI memberi label peran blok, tidak menulis atau mengubah isi, dan bisa dimatikan.

## Cara kerja singkat

```
Pilih jenis dokumen -> Tentukan standar (satu / campuran / acuan)
-> Unggah atau tempel naskah -> Deteksi struktur + review pengguna
-> Terapkan format -> Validasi + laporan kepatuhan -> Unduh -> File dihapus
```

## Teknologi

| Lapisan | Teknologi |
|---|---|
| Frontend | React |
| Backend | Python, FastAPI |
| Pemrosesan dokumen | python-docx, lxml (manipulasi OOXML) |
| Konversi dan render | LibreOffice (headless) |
| Database | MySQL, hanya untuk data sistem (preset kampus, aturan, statistik anonim) |
| Penyimpanan sementara | Folder temp server dengan pembersih terjadwal |
| AI (opsional) | API model bahasa, hanya untuk blok ambigu |

Database **tidak** menyimpan isi dokumen, nama file, data cover, dokumen acuan, atau hasil.

## Struktur repositori (rencana)

```
rapiindoc/
├── backend/            # FastAPI: API, komposisi aturan, parsing, klien AI
├── frontend/           # React: wizard, matriks sumber per bagian, pohon outline
├── presets/            # Seed preset aturan format (JSON) dan katalog kampus
├── docs/               # PRD, katalog aturan format
└── README.md
```

## Menjalankan secara lokal (rencana, sesuaikan setelah kode ada)

Prasyarat: Python 3.11+, Node.js, MySQL, LibreOffice.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Contoh variabel lingkungan:

| Variabel | Fungsi |
|---|---|
| `MYSQL_URL` | Koneksi database data sistem |
| `TEMP_DIR` | Folder penyimpanan file sementara |
| `FILE_TTL_MINUTES` | Batas waktu file dihapus otomatis (usulan awal 30) |
| `AI_ENABLED` | Mengaktifkan atau mematikan AI untuk blok ambigu |
| `ANTHROPIC_API_KEY` | Kunci API untuk modul AI (hanya diisi jika AI diaktifkan) |

## Preset kampus

Preset aturan format ada di `presets/` dan disusun per 12 bagian aturan: halaman, tipografi, cover, bagian awal, heading bab, penomoran halaman, daftar isi, tabel dan gambar, sitasi, daftar pustaka, lampiran, header dan footer.

Catatan penting:

- Preset berasal dari dokumen pedoman yang tersedia di web. Tiap preset mencantumkan sumber, tahun edisi, dan status verifikasi.
- Banyak pedoman hanya berlaku di tingkat fakultas atau program studi, bukan seluruh universitas.
- Beberapa preset masih parsial atau belum ada. Lihat katalog di `docs/`.
- **Selalu cocokkan hasil dengan pedoman terbaru fakultas, prodi, atau dosen pembimbing sebelum mengumpulkan.** Standar campuran tidak mewakili pedoman resmi satu kampus.

## Dokumentasi

- `docs/PRD_RapiInDoc.md`: spesifikasi produk, alur proses (PFD), arsitektur, privasi.
- `docs/Aturan_Format_RapiInDoc.md`: katalog aturan format umum dan per kampus.

## Roadmap

1. **Fase 0:** riset pedoman kampus target dan penyusunan kumpulan dokumen uji.
2. **Fase 1 (MVP):** makalah, laporan, proposal; DOCX dan teks tempel; tiga mode standar; preset kampus; laporan kepatuhan; ekspor DOCX/PDF; penghapusan otomatis.
3. **Fase 2:** jurnal dan IEEE; acuan dan input PDF; lebih banyak kampus.
4. **Fase 3:** kajian model bisnis, template institusi, skripsi dan tugas akhir.

## Berkontribusi

Kontribusi paling dibutuhkan saat ini: **pedoman penulisan resmi kampus** (tautan dokumen, edisi, dan cakupan fakultas atau prodi) serta **dokumen uji** tanpa data pribadi. Buka issue dengan label `preset-kampus` atau `dokumen-uji`.

## Lisensi

Belum ditentukan.
