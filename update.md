# Prompt: Upgrade Pipeline — Chunking PDF Jurnal + Ekstraksi Gap Penelitian

Salin seluruh isi di bawah garis ini ke agent Anda.

---

## Tugas

Upgrade pipeline pemrosesan PDF jurnal ilmiah dalam 3 tahap:

- **TAHAP 1** — Perbaiki ekstraksi & chunking (output JSONL saat ini punya 10 cacat terukur, daftar di bawah).
- **TAHAP 2** — Tambahkan modul ekstraksi gap penelitian (*research gap / future work / limitations*) di atas hasil chunking yang sudah bersih.
- **TAHAP 3** — Tambahkan verifikasi kebaruan (novelty check) gap terhadap literatur terbaru via API eksternal.

Kerjakan berurutan; setiap tahap punya kriteria selesai sendiri. Buktikan dengan re-run pada korpus yang sama (35 PDF) dan laporkan metrik sebelum/sesudah.

---

# TAHAP 1 — Perbaikan Ekstraksi & Chunking

## Format output saat ini

File: `chunks_<n>jurnal_<jobid>.jsonl`

Baris 1 (meta):
```json
{"record": "meta", "job_id": "...", "diekspor_pada": "...", "jumlah_jurnal": 35, "jumlah_chunk": 3095, "catatan": "Teks verbatim hasil ekstraksi PDF, belum diringkas LLM."}
```

Baris berikutnya (chunk):
```json
{"record": "chunk", "source": "Nama_File.pdf", "title": "...", "year": 2022, "section": "...", "chunk_index": 0, "chars": 322, "text": "..."}
```

## Masalah terukur yang HARUS diperbaiki

Hasil audit pada output nyata (35 jurnal, 3.095 chunk):

1. **40% chunk terpotong di tengah kalimat** (1.244/3.095) — chunking pakai fixed window ~512 karakter tanpa peduli batas kalimat/paragraf.
2. **Overlap antar chunk tidak konsisten** — hanya ~39% pasangan chunk berurutan yang overlap; sisanya berpotensi kehilangan informasi di batas chunk.
3. **Field `title` salah isi** (35/35 jurnal) — berisi nama jurnal, ISSN, DOI, atau teks acak dari header PDF, BUKAN judul paper.
4. **Field `year` salah/kosong** (9/35) — 8 jurnal `null`, 1 jurnal tercatat 1999 padahal DOI-nya `10.32631/v.2023.4.19` (2023). Penyebab: tahun diambil dari angka pertama yang ketemu di teks.
5. **Field `section` tidak berguna** — 629 nilai unik berisi ISSN, potongan kalimat, header halaman (contoh: `"NATURE &"`, `"P-ISSN: 2356-4962..."`, `"methods used for classification and regression."`). Bukan judul section sebenarnya.
6. **164 chunk berisi daftar pustaka (References)** ikut ter-index tanpa penanda — jadi noise saat retrieval RAG.
7. **682 chunk (22%) mengandung artefak ekstraksi PDF**: ligatur rusak (`speci?cally`, `veri?cation` — seharusnya fi/fl), hyphenation sisa line-break (`investiga- tive`), dan karakter pengganti `�`.
8. **Header/footer/nomor halaman ikut masuk teks** (nomor halaman, "Received June 1st 2012", copyright notice, running head jurnal).
9. **3 chunk duplikat persis.**
10. **Teks Cyrillic/non-Latin hancur total** pada minimal 1 PDF (semua karakter jadi `?`) — tidak ada fallback OCR/deteksi encoding.

## Perbaikan yang diminta

### A. Metadata (masalah 3, 4, 5)
- Integrasikan **GROBID** (`processFulltextDocument`) untuk ekstrak: judul paper asli, penulis, tahun terbit, DOI, abstrak, dan struktur section IMRaD dari TEI XML.
- Jika GROBID tidak memungkinkan, minimal: regex DOI dari teks → lookup metadata via **CrossRef API** (`https://api.crossref.org/works/{doi}`).
- `year` wajib divalidasi: rentang masuk akal (1990–tahun sekarang) dan konsisten dengan DOI/CrossRef jika tersedia.

### B. Chunking (masalah 1, 2)
- Ganti fixed 512-char → **splitter sadar-struktur**: pecah di batas paragraf dulu, lalu kalimat (jangan pernah memotong di tengah kalimat).
- Target ukuran **256–512 token** (bukan karakter), overlap konsisten **10–15%**.
- Chunk tidak boleh melintasi batas section.

### C. Pembersihan teks (masalah 7, 8, 10)
- Normalisasi Unicode NFKC + perbaiki ligatur (ﬁ→fi, ﬂ→fl, dst).
- De-hyphenation: gabungkan kata terpotong line-break (`investiga-\ntive` → `investigative`).
- Deteksi & buang header/footer berulang dan nomor halaman (pola yang muncul di ≥50% halaman).
- Jika rasio karakter non-alfanumerik abnormal tinggi (teks hancur), fallback ke OCR (mis. Tesseract dengan bahasa sesuai) atau tandai `extraction_quality: "poor"`.

### D. Skema output baru (masalah 5, 6, 9)
Tambahkan field per chunk:
```json
{
  "record": "chunk",
  "source": "...",
  "doi": "10.xxxx/... | null",
  "paper_title": "judul paper asli dari GROBID/CrossRef",
  "authors": ["..."],
  "year": 2023,
  "language": "en | id | ...",
  "section_raw": "judul section asli dari dokumen",
  "section_normalized": "abstract|introduction|related_work|methods|results|discussion|conclusion|references|other",
  "is_reference": false,
  "page_start": 3,
  "chunk_index": 0,
  "token_count": 384,
  "text": "...",
  "extraction_quality": "good|fair|poor"
}
```
- Chunk References tetap disimpan tapi `is_reference: true` agar bisa di-exclude saat indexing RAG.
- Deduplikasi: buang chunk dengan teks identik (hash).

### E. Validasi otomatis (wajib ada di pipeline)
Buat langkah audit yang jalan otomatis setelah export dan gagalkan job jika:
- chunk terpotong tengah kalimat > 5%
- `paper_title` kosong/sama dengan nama jurnal > 10% jurnal
- `year` null > 10% jurnal
- ada chunk duplikat
- `section_normalized = "other"` > 30% chunk

## Kriteria selesai Tahap 1
1. Re-run pipeline pada 35 PDF yang sama.
2. Laporkan tabel metrik sebelum vs sesudah untuk 10 masalah di atas.
3. Semua threshold validasi (bagian E) lolos.
4. Sertakan 3 contoh chunk sebelum vs sesudah dari jurnal yang sama sebagai bukti kualitatif.

---

# TAHAP 2 — Modul Ekstraksi Gap Penelitian

## Latar belakang
Tujuan akhir korpus ini adalah menemukan *research gap* untuk menghasilkan usulan judul penelitian. Percobaan gap mining pada output lama hanya bisa pakai regex frasa (`"future work"`, `"belum dilakukan"`, dst.) ke seluruh 3.095 chunk — menemukan 49 chunk, banyak false positive, dan gap implisit lolos. Dengan `section_normalized` dari Tahap 1, ekstraksi bisa ditarget dan jauh lebih akurat.

## Yang diminta

### A. Ekstraksi gap 2 lapis
1. **Lapis 1 — Kandidat berbasis section (murah, tanpa LLM):**
   Ambil semua chunk dengan `section_normalized` ∈ {`conclusion`, `discussion`} + chunk yang cocok pola frasa gap multi-bahasa:
   - EN: `future work|further research|open problem|research gap|limitation|remains unexplored|not yet been|little attention`
   - ID: `penelitian selanjutnya|belum dilakukan|belum pernah|keterbatasan penelitian|saran penelitian`
2. **Lapis 2 — Ekstraksi terstruktur dengan LLM:**
   Kirim kandidat (dengan konteks 1 chunk sebelum/sesudah) ke LLM, minta output JSON per gap:
   ```json
   {
     "source": "...", "paper_title": "...", "year": 2022, "doi": "...",
     "gap_type": "explicit_future_work | stated_limitation | implicit_gap",
     "gap_statement": "kutipan verbatim dari teks",
     "gap_paraphrase": "parafrase 1 kalimat dalam bahasa Indonesia",
     "topic": "image_forensics | mobile_forensics | legal | tools | multimedia | other",
     "evidence_chunk_ids": ["..."]
   }
   ```
   Wajib bedakan `gap_statement` (verbatim, bisa diverifikasi) dari interpretasi. Tolak halusinasi: setiap gap harus punya kutipan yang benar-benar ada di chunk.
3. Simpan hasil ke `gaps_<jobid>.jsonl`.

### B. Referensi implementasi (pelajari, jangan tulis dari nol)
Gunakan salah satu sebagai fondasi atau referensi arsitektur:

| Repo | Peran |
|---|---|
| [Future-House/paper-qa](https://github.com/Future-House/paper-qa) (PaperQA2) | **Direkomendasikan** — RAG khusus paper ilmiah dengan sitasi per-klaim; bisa langsung ingest folder PDF; pakai untuk QA "what gaps/limitations are stated?" per paper |
| [IbrahimAlAzhar/FutureWorkGeneration](https://github.com/IbrahimAlAzhar/FutureWorkGeneration) (FutureGen, arXiv 2503.16561) | Paling spesifik: ekstraksi + generasi future-work berbasis RAG |
| [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher) | Agent riset otonom; mode dokumen lokal untuk laporan gap bersitasi |
| [shubhamagarwal92/LitLLM](https://github.com/shubhamagarwal92/LitLLM) | Toolkit related-work & gap analysis (RAG + reranking) |
| [Vardhman-Banthia/ResearchGapAI](https://github.com/Vardhman-Banthia/ResearchGapAI) | Referensi arsitektur: SciBERT + BERTopic + RAG untuk deteksi gap |
| [stanford-oval/storm](https://github.com/stanford-oval/storm) | Sintesis literatur terstruktur skala besar (opsional) |
| [Research Gap Discovery Dataset](https://data.mendeley.com/datasets/px9xd7tw8n) (Mendeley) | Dataset benchmark untuk evaluasi kualitas ekstraksi gap |

## Kriteria selesai Tahap 2
1. `gaps_<jobid>.jsonl` berisi gap terstruktur dari ≥ 25 dari 35 jurnal.
2. 100% `gap_statement` terverifikasi ada verbatim di chunk sumber (buat skrip cek otomatis).
3. Minimal 5 gap eksplisit yang pada output lama tidak tertangkap regex ikut ditemukan.

---

# TAHAP 3 — Verifikasi Kebaruan (Novelty Check)

## Latar belakang
Korpus mayoritas 2021–2023. Gap yang dinyatakan "belum dilakukan" pada 2022 bisa jadi sudah dijawab paper 2024–2026. Tanpa verifikasi, usulan judul berisiko duplikat.

## Yang diminta
1. Untuk setiap gap di `gaps_<jobid>.jsonl`, query literatur terbaru via API gratis:
   - **OpenAlex**: `https://api.openalex.org/works?search=<keywords>&filter=from_publication_date:2024-01-01` (tanpa API key)
   - **Semantic Scholar**: `https://api.semanticscholar.org/graph/v1/paper/search?query=<keywords>&year=2024-` (rate limit longgar tanpa key)
2. Tambahkan field per gap: `novelty_status` (`open` = tak ada paper baru yang menjawab | `partially_addressed` | `addressed`), `related_recent_papers` (maks 5: judul, tahun, DOI), `checked_at`.
3. Hormati rate limit (sleep antar request, backoff saat 429) dan cache respons API ke disk agar re-run tidak mengulang query.

## Kriteria selesai Tahap 3
1. 100% gap punya `novelty_status` terisi.
2. Ringkasan akhir: tabel gap dengan status `open`, diurutkan per topik — ini kandidat judul penelitian yang aman.

---

# Arsitektur akhir

```
PDF (35 jurnal)
  → GROBID (metadata + section IMRaD)          [Tahap 1]
  → cleaning + chunking token-aware + overlap   [Tahap 1]
  → chunks_<jobid>.jsonl (skema baru)           [Tahap 1]
  → gap extractor (section-target + LLM)        [Tahap 2]
  → gaps_<jobid>.jsonl                          [Tahap 2]
  → novelty check (OpenAlex/Semantic Scholar)   [Tahap 3]
  → laporan gap "open" per topik = kandidat judul penelitian
```

# Kriteria selesai keseluruhan
1. Ketiga tahap lolos kriteria masing-masing.
2. Laporan akhir tunggal: metrik chunking sebelum/sesudah + daftar gap `open` bersitasi + contoh kandidat judul per topik.
