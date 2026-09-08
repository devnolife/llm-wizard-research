# Pipeline Penemuan Research Gap — Dokumentasi Lengkap

Dokumentasi ujung-ke-ujung pekerjaan **upgrade pipeline pemrosesan PDF jurnal ilmiah**:
dari PDF mentah → chunk bersih → ekstraksi *research gap* → verifikasi kebaruan →
rekomendasi topik penelitian.

> Ringkasan Q&A sesi pengembangan ada di [`../../data/processed/KONTEKS_SESI.md`](../../data/processed/KONTEKS_SESI.md).
> Riwayat lengkap semua sesi Copilot repo ini ada di [`COPILOT_HISTORY.md`](COPILOT_HISTORY.md).

---

## 1. Latar Belakang & Tujuan

Output JSONL pipeline lama memiliki **10 cacat terukur** (chunk terpotong tengah kalimat,
judul/tahun/section salah, noise daftar pustaka, artefak ekstraksi PDF, header/footer bocor,
duplikat, teks non-Latin hancur). Tujuan akhir korpus adalah **menemukan research gap** untuk
menghasilkan **usulan judul penelitian** yang aman (belum terjawab literatur terbaru).

Pekerjaan dibagi 3 tahap berurutan, masing-masing dengan kriteria selesai sendiri, dan
diuji ulang pada **korpus yang sama (35 PDF jurnal forensik digital)**.

---

## 2. Arsitektur Akhir

```
PDF (35 jurnal)
  → [metadata_resolver]  GROBID (opsional) → DOI-regex → CrossRef → OpenAlex-title   [TAHAP 1]
  → [text_cleaning]      NFKC+ftfy, de-hyphenation, buang header/footer, quality flag [TAHAP 1]
  → [layout+section]     deteksi header sadar-font → section_normalized (IMRaD)        [TAHAP 1]
  → [token_chunker]      256–512 token, sadar-kalimat, overlap 10–15%, tidak lintas-section
  → [dedup]              buang chunk identik (hash)
  → chunks_<jobid>.jsonl (skema baru)                                                  [TAHAP 1]
  → [gap_mining L1]      kandidat: section conclusion/discussion + frasa gap multibahasa [TAHAP 2]
  → [gap_mining L2]      LLM (Copilot) → JSON gap terstruktur (verbatim)                [TAHAP 2]
  → [verify]             100% gap_statement diverifikasi verbatim (anti-halusinasi)     [TAHAP 2]
  → gaps_<jobid>.jsonl
  → [novelty]            query OpenAlex 2024+ (+cache/backoff) → open/partial/addressed [TAHAP 3]
  → gaps_<jobid>_novelty.jsonl
  → [recommend_topics]   rank_proposals resmi project → judul kandidat per topik
  → final_report.md
```

**Prinsip desain:** *shared core* dipakai oleh **FastAPI ingestion** (upload PDF di web) **dan**
**CLI reproducible** (re-run korpus), sehingga hasil keduanya identik.

---

## 3. Hasil Akhir (diverifikasi pada 35 PDF)

### TAHAP 1 — Ekstraksi & Chunking — **GATE: LULUS**
| Masalah | Sebelum | Sesudah |
|---|---:|---:|
| 1. Potong tengah kalimat (prosa) | 20.5% | **4.7%** (ambang ≤5%) |
| 2. Overlap konsisten | 0.6% | **93.8%** |
| 3. Judul salah (isi nama jurnal/ISSN) | 17 jurnal | **0** |
| 4. Tahun null/invalid | 8 jurnal | **2** |
| 5. Section tak berguna ("other") | 30.3% (707 label unik) | **19.2%** (9 label) |
| 6. Chunk daftar pustaka | tak ditandai | **ditandai `is_reference`** |
| 7. Artefak ekstraksi (ligatur/�) | 455 chunk | **237** |
| 8. Header/footer/nomor halaman | 122 chunk | **54** |
| 9. Duplikat | 2 | **0** |
| 10. Teks non-Latin (Cyrillic) | hancur | **utuh** |

Total chunk: 3.784 (lama) → **1.054** (baru, lebih padat & bersih).

### TAHAP 2 — Ekstraksi Research Gap
- **388 gap** dari **27 dari 35 jurnal** (syarat ≥25 ✓).
- **100% `gap_statement` terverifikasi verbatim** di chunk sumber (anti-halusinasi).
- **75 gap eksplisit** yang **tidak tertangkap** metode regex lama.
- 8 jurnal tanpa gap = buku/proceedings/editorial/handbook/paper deskriptif (wajar).
- Benchmark **Mendeley px9xd7tw8n** (3.326 paper gold, 30 sampel): fetch 30/30,
  semantic similarity ~**0.60**, LLM-as-judge ~**2.75/5**.

### TAHAP 3 — Verifikasi Kebaruan (Novelty)
- **388/388 gap** punya `novelty_status`: **open 358 / partially 22 / addressed 8**.
- Sumber utama **OpenAlex** (2024+) dengan cache disk + backoff 429.
- Semantic Scholar tak bisa diakses dari environment ini (SSL reset) → hook best-effort.

### Rekomendasi Topik (rumus resmi project)
- Peringkat via `app.core.recommendation.novelty.rank_proposals`:
  **skor = 0.5·gap_confidence + 0.3·novelty_credit + 0.2·actionability**, novelty diukur vs korpus
  35 paper (embedder multilingual), filter gap `open`. LLM hanya untuk narasi judul.
- `novelty_credit` bernilai **1,0 rata untuk seluruh rentang *sweet spot* (0,25–0,65)**. Akibatnya
  banyak proposal **seri persis** di skor maksimum 0,9333 (gap_conf 1,0 · sweet spot · actionability
  0,6667). Seri dipecahkan **hanya oleh urutan** (`sweet_spot_distance`, jarak ke titik tengah rentang),
  bukan oleh perubahan skor — commit `b38d72e`. Varian kredit kontinu (`5ed0910`) pernah dicoba dan
  **dikembalikan** agar rumus proposal tetap utuh; lihat §10 soal jejaknya di `rekomendasi_final.md`.
- Distribusi gap open: `tools=111, legal=94, image_forensics=69, other=43, mobile=36, multimedia=5`.
- Topik teratas (HIGH, novelty *sweet_spot*): protokol pengujian/validasi tool forensik terstandar,
  kerangka regulasi/SOP & chain-of-custody, steganografi+kriptografi.
- `rekomendasi_final.md` mengelompokkan proposal menjadi **tema lintas-jurnal**
  (`app.core.recommendation.themes.build_themes`): tema diurutkan menurut **jumlah jurnal berbeda**
  yang mendukungnya, skor prioritas hanya *tie-break*. Hasil: 245 tema dari 358 proposal, **hanya 5 tema
  didukung ≥ 2 jurnal**, 196 tema (80%) beranggota satu gap — indikasi literatur terfragmentasi
  (dikonfirmasi independen oleh kopling bibliografis, lihat §11).

---

## 4. Struktur Kode Baru

### Shared core — `backend/app/core/pipeline/`
| File | Peran |
|---|---|
| `schema.py` | Skema `PaperMeta` & `PipelineChunk` (JSONL v2 + metadata vektor). |
| `text_cleaning.py` | NFKC+ftfy, de-hyphenation, buang header/footer & tabel, `extraction_quality`, deteksi bahasa, reflow. |
| `layout.py` | Ekstraksi baris sadar-font (pymupdf) untuk deteksi header. |
| `section_normalizer.py` | Peta header mentah → kanonik IMRaD + deteksi `is_reference`. |
| `token_chunker.py` | Chunk 256–512 token, sadar-kalimat (pysbd), overlap konsisten, tidak lintas-section. |
| `metadata_resolver.py` | GROBID → DOI-regex → CrossRef → OpenAlex-title; validasi tahun. |
| `dedup.py` | Buang chunk identik (hash). |
| `io.py` | Writer/reader JSONL. |
| `pipeline.py` | Orkestrator `process_pdf` + adapter FastAPI `process_pdf_as_document`. |
| `corpus_relevance.py` | Uji koherensi korpus: menandai PDF yang tidak sebidang dengan batch (judul + 2 chunk awal), karena paper luar-domain justru bisa "dihadiahi" novelty *sweet spot*. |
| `references.py` | Penguraian daftar pustaka → entri berkunci DOI / penulis-tahun-judul, tanpa LLM (dipakai kopling bibliografis, §11). |

### Gap mining — `backend/app/core/gap_mining/`
| File | Peran |
|---|---|
| `candidates.py` | L1: pilih chunk kandidat (section + frasa gap EN/ID). |
| `extractor.py` | L2: LLM (Copilot) → JSON gap terstruktur (prompt ala FutureGen). |
| `verify.py` | Verifikasi verbatim (reuse `gap_detection/quote_grounding`). |
| `novelty.py` | Cek kebaruan gap vs OpenAlex 2024+; gagal/kuota habis → status `unchecked`, **bukan** `open`. |

### Rekomendasi — `backend/app/core/recommendation/`
| File | Peran |
|---|---|
| `novelty.py` | `rank_proposals` — rumus prioritas resmi project + pemecah seri `sweet_spot_distance`. |
| `themes.py` | Pengelompokan proposal menjadi tema lintas-jurnal; urut menurut jumlah jurnal pendukung. |

### Orkestrasi job — `backend/app/services/research_pipeline.py`
Menjalankan TAHAP 1–3 + rekomendasi sebagai **job terpantau** (event & artefak per tahap ke `job_store`)
memakai komponen inti yang sama dengan CLI. Mendukung `gap_runs` 1–5 dan `min_run_hits` (konsensus
multi-run k/n, lihat §10); gap `stable=False` tidak diteruskan ke novelty.

### Klien API — `backend/app/services/paper_apis/`
| File | Peran |
|---|---|
| `grobid.py` | Klien GROBID opsional (`GROBID_URL`), parsing TEI XML. |
| `openalex.py` | Klien OpenAlex (tanpa API key) untuk novelty; `get_work_by_doi` untuk pengayaan referensi. |
| `http_cache.py` | Cache disk + rate-limit + backoff 429 (dipakai CrossRef/OpenAlex); *cooldown* per host bila `Retry-After` panjang. |

### CLI — `backend/scripts/`
| Perintah | Fungsi |
|---|---|
| `run_pipeline.py` | PDF folder → `chunks_<jobid>.jsonl` (mode `--legacy` untuk baseline). |
| `mine_gaps.py` | chunks → `gaps_<jobid>.jsonl` (L1→L2→verify). |
| `check_novelty.py` | gaps → `gaps_<jobid>_novelty.jsonl`. |

### Harness/evaluasi — `backend/experiments/`
| File | Fungsi |
|---|---|
| `audit_chunks.py` | Audit 10 masalah + **gate validasi bagian E**. |
| `verify_gaps.py` | Cek 100% gap verbatim + hitung gap yang lolos regex lama. |
| `gap_benchmark_mendeley.py` | Benchmark vs dataset Mendeley (similarity + LLM-judge). |
| `consensus_gaps.py` | **Produsen resmi `gaps_union.jsonl`**: gabungkan n run gap mining → union beranotasi k/n (kunci & ambang sama dengan `merge_gap_runs` di job). |
| `final_report.py` | Laporan tunggal akhir (+ bagian "Stabilitas lintas-run" bila input union). |
| `recommend_topics.py` | Peringkat topik via rumus resmi project; `--min-run-hits` memfilter **sebelum** `rank_proposals` (rumus tidak berubah). |

### Test — `backend/tests/`
`test_pipeline.py`, `test_gap_mining.py`, `test_consensus_gaps.py`, `test_research_pipeline.py`,
`test_references.py`, `test_citation_coupling.py`, `test_coverage_axes.py`, `test_paper_profiles.py`,
`test_workflow_stages.py`, dll. — seluruh suite backend **878 test terkumpul** (unit, offline; 2 *skip*
bergantung dependensi opsional).

---

## 5. Cara Menjalankan (dari direktori `backend/`)

```bash
# TAHAP 1 — chunking + audit gate
python -m scripts.run_pipeline --input ../data/raw/analysis_jobs/<jobid> \
    --out ../data/processed/chunks_<jobid>.jsonl
python -m scripts.run_pipeline --input <dir> --out ../data/processed/chunks_old.jsonl --legacy
python -m experiments.audit_chunks ../data/processed/chunks_<jobid>.jsonl \
    --baseline ../data/processed/chunks_old.jsonl --gate

# TAHAP 2 — ekstraksi gap + verifikasi + benchmark
python -m scripts.mine_gaps --chunks ../data/processed/chunks_<jobid>.jsonl \
    --out ../data/processed/gaps_<jobid>.jsonl
python -m experiments.verify_gaps --gaps ../data/processed/gaps_<jobid>.jsonl \
    --chunks ../data/processed/chunks_<jobid>.jsonl
python -m experiments.gap_benchmark_mendeley \
    --dataset ../data/benchmarks/mendeley_gaps.csv --sample 30 --judge \
    --out ../data/processed/mendeley_benchmark_result.json

# TAHAP 3 — novelty + laporan + rekomendasi
python -m scripts.check_novelty --gaps ../data/processed/gaps_<jobid>.jsonl \
    --out ../data/processed/gaps_<jobid>_novelty.jsonl --min-interval 1.5 --max-retries 1
python -m experiments.final_report \
    --chunks-new ../data/processed/chunks_<jobid>.jsonl \
    --chunks-old ../data/processed/chunks_old.jsonl \
    --gaps ../data/processed/gaps_<jobid>_novelty.jsonl \
    --mendeley ../data/processed/mendeley_benchmark_result.json \
    --out ../data/processed/final_report.md
python -m experiments.recommend_topics \
    --gaps ../data/processed/gaps_<jobid>_novelty.jsonl \
    --chunks ../data/processed/chunks_<jobid>.jsonl \
    --out ../data/processed/rekomendasi_penelitian.md

# KONSENSUS MULTI-RUN — jalankan mine_gaps ≥3× pada chunk yang sama, lalu gabungkan (k/n)
python -m experiments.consensus_gaps \
    --inputs ../data/processed/gaps_v3.jsonl ../data/processed/gaps_v4.jsonl \
             ../data/processed/gaps_d4eb6a1d.jsonl \
    --out ../data/processed/gaps_union.jsonl            # --stable-only untuk k ≥ ⌈2n/3⌉ saja
python -m experiments.recommend_topics --gaps ../data/processed/gaps_union_novelty.jsonl \
    --chunks ../data/processed/chunks_<jobid>.jsonl --min-run-hits 2 --out ../data/processed/rekomendasi_final.md
```

Lewat API/UI: `POST /api/research/start` menerima *form* `gap_runs` (1–5, bawaan 1) dan
`min_run_hits` (bawaan ⌈2n/3⌉); Wizard Lite (`:8502`, Langkah 2) menyediakan pilihan 1 atau 3 run.

### Konfigurasi (env di `backend/.env`)
| Variabel | Fungsi |
|---|---|
| `COPILOT_MODEL`, `COPILOT_CONFIG_DIR`, `COPILOT_MAX_CONCURRENCY`, `COPILOT_CLI_PATH`, `COPILOT_DISABLED` | LLM lewat **GitHub Copilot SDK** (`app/services/copilot_client.py`) untuk ekstraksi gap & narasi. Tidak ada endpoint HTTP `COPILOTD_URL` — variabel itu sudah tidak dipakai. |
| `GROBID_URL` | (Opsional) server GROBID; kosong = fallback CrossRef/regex. |
| `CROSSREF_EMAIL` | Email *polite pool* **CrossRef** (respons lebih cepat). Untuk **OpenAlex** email tidak menaikkan kuota: tier gratisnya berbasis **kredit (~100 pencarian/hari per akun/IP)**; saat habis, server menjawab 429 dengan `Retry-After` ~13 jam dan gap yang belum dicek diberi status `unchecked`. |
| `PIPELINE_API_CACHE_DIR` | Direktori cache respons API (default `backend/data/cache/api`). |
| `OPENALEX_DISABLED` | `1` = TAHAP 3 tidak menyentuh jaringan: semua gap berstatus `unchecked`, tetap diteruskan ke rekomendasi. Skor prioritas **tidak berubah** (novelty proposal diukur terhadap korpus unggahan); yang hilang hanya penyaringan gap `addressed`. Aktif di mesin kerja sejak 8 Sep (pencarian luar bukan bagian proposal). |
| `COVERAGE_AXES_DIR` | Direktori ontologi sumbu *evidence gap map* (YAML; bawaan `backend/data/ontology`). |
| `BIBLIO_OPENALEX_ENRICH` | `true` = lengkapi daftar pustaka pendek dengan `referenced_works` OpenAlex (bawaan **mati**; kopling bibliografis berjalan sepenuhnya *offline* dari PDF). |

GROBID opsional: `docker compose --profile grobid up -d grobid` → set `GROBID_URL=http://localhost:8070`.

---

## 6. Skema Output Chunk (baru)

```json
{
  "record": "chunk",
  "source": "Nama_File.pdf",
  "doi": "10.xxxx/... | null",
  "paper_title": "judul paper asli",
  "authors": ["..."],
  "year": 2023,
  "language": "en | id | ...",
  "section_raw": "judul section asli",
  "section_normalized": "abstract|introduction|related_work|methods|results|discussion|conclusion|references|other",
  "is_reference": false,
  "page_start": 3,
  "chunk_index": 0,
  "chunk_id": "source::idx::hash",
  "token_count": 384,
  "chars": 1980,
  "text": "...",
  "extraction_quality": "good|fair|poor"
}
```

---

## 7. Deliverables (`data/processed/`)

> **Catatan:** `data/processed/*` dan `*.csv` ada di `.gitignore` (baris 50 & 52), jadi berkas di bawah
> hanya ada di mesin kerja (server `hpc-ai`), **tidak** ikut ke repositori. Tautan relatif ke
> `KONTEKS_SESI.md` di atas juga hanya berfungsi di *checkout* lokal tersebut.

- `chunks_new.jsonl` — chunk skema baru (35 jurnal, 1.054 chunk).
- `chunks_old.jsonl` — baseline pipeline lama (before/after).
- `gaps_d4eb6a1d.jsonl` — 388 gap terverifikasi verbatim (**satu run**).
- `gaps_v3.jsonl`, `gaps_v4.jsonl` — dua run tambahan pada chunk yang sama (307 dan 336 gap).
- `gaps_union.jsonl` — **union 3 run, 528 gap beranotasi k/n** (28 jurnal; baris pertama = record `meta`),
  produk `experiments/consensus_gaps.py`. `gaps_union_novelty.jsonl` — versi dengan `novelty_status`.
- `gaps_d4eb6a1d_novelty.jsonl` — gap run tunggal + `novelty_status`.
- `final_report.md` — laporan tunggal akhir (run tunggal, 30 Agu).
- `qualitative_examples.md` — 3 contoh chunk sebelum/sesudah.
- `mendeley_benchmark_result.json` — hasil benchmark Mendeley (n = 30 sampel).
- `rekomendasi_penelitian.md` — peringkat run tunggal (rumus asli; 8 proposal seri di 0,9333).
- `rekomendasi_final.md` — peringkat berbasis union + tema lintas-jurnal (lihat §10 soal versi rumus).
- `KONTEKS_SESI.md` — ringkasan Q&A sesi pengembangan.
- Dataset: `data/benchmarks/mendeley_gaps.csv`.

---

## 8. Referensi yang Diadopsi
| Repo/Dataset | Peran dalam desain |
|---|---|
| PaperQA2 | Pola grounding sitasi per-klaim (via `quote_grounding`). |
| FutureGen (arXiv 2503.16561) | Prompt ekstraksi + rubrik LLM-as-judge 1–5. |
| Mendeley `px9xd7tw8n` | Dataset gold benchmark kualitas ekstraksi gap. |
| OpenAlex / CrossRef | Metadata & verifikasi kebaruan (gratis, tanpa key). |

---

## 9. Catatan & Langkah Lanjutan
- **Novelty "open" cenderung tinggi (358/388)** — bacalah dengan hati-hati. Ada dua sebab yang tidak
  bisa dipisahkan dari data yang ada: (a) *recall* pencarian OpenAlex dengan kueri kalimat gap memang
  rendah, dan (b) kuota **kredit** OpenAlex (~100 pencarian/hari) habis di tengah run. Sejak revisi,
  gap yang tidak sempat dicek berstatus **`unchecked`** (bukan `open`), dan `research_pipeline`
  menuliskan berapa gap yang terkena kuota. Menyetel `CROSSREF_EMAIL` **tidak** menaikkan kuota
  OpenAlex (klaim "polite pool" pada versi awal dokumen ini keliru); yang membantu adalah menjalankan
  ulang tahap novelty setelah kuota pulih, atau membatasi jumlah gap yang dicek per hari.
- Jalankan **GROBID** untuk metadata & struktur section yang lebih akurat.
- Refresh `requirements.lock` untuk *locked install* (manifes `requirements.txt` sudah diperbarui:
  `ftfy`, `pysbd`, `langdetect`, `lxml`, `tiktoken`).
- Semantic Scholar diblokir di environment ini; aktif kembali otomatis bila jaringan mengizinkan.

---

## 10. Batasan & Reproduksibilitas

1. **LLM tidak deterministik.** Dua run `mine_gaps` pada chunk identik hanya tumpang tindih ~75%
   (Jaccard antar-run 0,521 pada tiga run). Dari union 528 gap, hanya **196 (37,1%) muncul di ketiga
   run**, 111 di dua run, 221 di satu run saja. Angka "388 gap" dari satu run adalah **satu undian**.
   Karena itu setiap temuan bergantung-LLM kini dilaporkan sebagai **k/n** dengan ambang stabil
   ⌈2n/3⌉; gap tidak stabil tetap disimpan tetapi tidak diteruskan ke novelty/rekomendasi.
2. **Semua artefak §3 dibuat dari teks yang diekstrak *sebelum* perbaikan `join_spans`** (commit
   `f2daaab`, 7 Sep). Mode `dict` PyMuPDF membuang spasi antar *span* sehingga kata tergabung
   ("Weproposeanewsimplenetworkarchitecture"; 31,9% kata pada satu PDF Elsevier \u2192 0,02% setelah
   perbaikan). Kata yang tergabung merusak tokenisasi, kandidat frasa gap (L1), *grounding* verbatim,
   dan *embedding* novelty untuk jurnal yang terdampak. `chunks_new.jsonl`, ketiga run `gaps_*`, dan
   novelty **belum diregenerasi** dengan perbaikan ini; angka \u00a73 tetap dipertahankan agar sebanding
   dengan baseline yang diaudit pada tanggal yang sama. Untuk angka mutakhir jalankan ulang TAHAP 1\u20133.
3. **Skor pada `rekomendasi_final.md` (mis. 0,9186; 0,9171) tidak akan tereproduksi** oleh kode saat
   ini. Berkas itu dibuat 1 Sep 19:06, di antara commit `5ed0910` (kredit novelty kontinu) dan
   `b38d72e` (pengembalian rumus asli). Kode sekarang memberi 0,9333 untuk semua proposal *sweet
   spot* berkonfidensi 1,0 dan mengurutkan seri lewat `sweet_spot_distance`; **urutan** tema dan
   proposal teratas tetap sama, hanya angka skornya berbeda.
4. **Benchmark Mendeley** hanya 30 sampel (dari 3.326 gold); similarity ~0,60 dan LLM-judge ~2,75/5
   adalah indikasi, bukan estimasi yang stabil.
5. **Novelty** dibatasi kuota harian OpenAlex (butir §9) dan hanya mencakup literatur 2024+ yang
   terindeks OpenAlex; status `unchecked` harus dilaporkan terpisah, bukan dilebur ke `open`.
6. **Ketergantungan lingkungan:** GPU bersama, Copilot SDK (kredensial per pengguna), dan cache API
   lokal (`backend/data/cache/api`) — run ulang dari mesin lain tanpa cache akan lebih lambat dan
   dapat menabrak kuota lebih cepat.

---

## 11. Posisi terhadap Proposal Tesis

Pipeline di dokumen ini (PDF → chunk → gap penulis → novelty → rekomendasi) adalah **pipeline A**:
ia menambang **pernyataan gap yang ditulis penulis sendiri** (`explicit_future_work`,
`stated_limitation`, `implicit_gap`) per jurnal. Proposal tesis (draf BAB III §3.6.2) berfokus pada
**pipeline B** — deteksi **synthesis gap** lintas-paper dengan empat indikator (fragmentasi,
inkonsistensi, ketidaklengkapan, ketiadaan dukungan bukti) yang divalidasi *Rule Engine*. Keduanya
kini terhubung tanpa mengubah rumus atau aturan yang sudah ada:

| Penambahan (branch `wizard-lite`, Sep 2026) | Modul | Peran dalam pipeline B |
|---|---|---|
| Korroborasi pernyataan penulis | `gap_detection/paper_profiles.py`; `analyzer._corroborate_with_author_statements` | Output pipeline A (kekurangan per jurnal + gap `gap_job_id`) dilekatkan ke indikator sebagai **bukti**, bukan skor; 9 aturan Rule Engine tidak berubah. |
| Workflow-stage mining | `gap_detection/workflow_stages.py` | Rekonstruksi 8 tahap metode per jurnal dengan kutipan terverifikasi → tahap homogen lintas jurnal = ketidaklengkapan metodologis. |
| Kopling bibliografis (bebas LLM) | `pipeline/references.py`, `gap_detection/citation_coupling.py` | Fragmentasi Metode 3: pada 35 jurnal forensik, 25 memenuhi syarat, **20 komponen**, 295/300 pasangan terputus, 2 sitasi langsung — memperkuat temuan "80% tema hanya 1 jurnal" di §3 dari arah independen. |
| Sumbu peta bukti sadar domain | `gap_detection/coverage_axes.py`, `data/ontology/*.yaml` | Baris/kolom *evidence gap map* dari ontologi kurasi > usulan LLM ber-*grounding* korpus > bawaan. |
| Konsensus multi-run k/n | `services/research_pipeline.py` (`merge_gap_runs`), `experiments/consensus_gaps.py` | Stabilitas temuan LLM sebagai anotasi/filter (§10 butir 1). |

Pencarian literatur eksternal (OpenAlex/CrossRef/Semantic Scholar) **bukan bagian dari klaim
proposal** (keputusan 7 Sep): fitur-fitur baru di atas berjalan *offline-first* dari PDF yang diunggah;
OpenAlex hanya opsional (`BIBLIO_OPENALEX_ENRICH`, bawaan mati) dan untuk tahap novelty pipeline A.

---

_Dependensi baru: `ftfy`, `pysbd`, `langdetect`, `lxml`, `tiktoken` (lihat `backend/requirements.txt`)._
_Semua balasan pengembangan memakai Bahasa Indonesia sesuai preferensi pengguna._
