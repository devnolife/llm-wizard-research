# REVIEW KONSISTENSI — Checklist Final (revisi.md §14)

Tanggal review: 2025-07-15
File yang di-review:
- `BAB_I_PENDAHULUAN.md`
- `BAB_II_TINJAUAN_PUSTAKA.md`
- `BAB_III_METODOLOGI.md`
- `NOVELTY_STATEMENT.md`

---

## Konseptual

| # | Item | Status | Lokasi/Bukti |
|---|------|--------|--------------|
| 1 | Rumusan masalah pola fenomena→kesenjangan→pertanyaan | ✅ PASS | BAB I §1.2 — Fenomena (sintesis membutuhkan penalaran tingkat tinggi), Kesenjangan (pipeline linear RAG+LLM tanpa validasi logis), Pertanyaan (3 RQ) |
| 2 | Definisi synthesis gap sesuai Cooper (1998) & Booth (2012) | ✅ PASS | BAB II §2.2.2 — definisi eksplisit dalam blockquote, merujuk Cooper [1998] dan Booth et al. [2012] |
| 3 | Ada sesi batasan epistemologis yang eksplisit | ✅ PASS | BAB I §1.5 (4 sub-bagian: DAPAT, TIDAK DAPAT, Posisi Sistem, Klaim yang TIDAK Dibuat); NOVELTY §4.2–4.3 |
| 4 | Klaim sistem = "alat bantu deteksi indikator", bukan "pengganti manusia" | ✅ PASS | BAB I §1.5.3 ("alat bantu keputusan, bukan pengganti penalaran manusia"); BAB III §3.8; NOVELTY §4.1 item 2 |
| 5 | Istilah "synthesis gap" konsisten di seluruh dokumen | ✅ PASS | Konsisten di 4 file (BAB I: 15×, BAB II: 16×, BAB III: 16×, NOVELTY: 7×). Tidak ditemukan varian seperti "research gap" yang disalahgunakan sebagai sinonim |
| 6 | Novelty statement jelas (Neuro-Symbolic Agentic, bukan sekadar RAG+LLM) | ✅ PASS | NOVELTY §2.1–2.2 (4 pilar kebaruan); BAB III §3.8 — eksplisit menyatakan "Kebaruan bukan pada RAG atau LLM…melainkan pada integrasi penalaran simbolik dengan penalaran neural" |

---

## Arsitektur

| # | Item | Status | Lokasi/Bukti |
|---|------|--------|--------------|
| 7 | Diagram alir 4 fase sudah digambar | ✅ PASS | BAB III §3.2 baris 62–80 (diagram ASCII 4 fase: Ingestion → Fact Extraction → Agentic Analysis → Logical Consistency Checker) |
| 8 | Ada blok "Logical Consistency Checker" di diagram | ✅ PASS | BAB III §3.2 Fase 4 (baris 70–76) — label eksplisit "LOGICAL CONSISTENCY CHECKER" dengan penanda "KOMPONEN BARU" |
| 9 | Mekanisme pembeda asosiasi semantik vs hubungan logis sudah dijelaskan | ✅ PASS | BAB III §3.3 — mekanisme 3 lapis (Semantic Filtering → Evidence Extraction → Rule-Based Validation) dengan diagram alir dan penanda linguistik |
| 10 | Rule-Based Validation Layer sudah didefinisikan (3 kategori, 9 aturan) | ✅ PASS | BAB III §3.4.2 — Feasibility (F1–F3), Causality (C1–C3), Consistency (K1–K3) lengkap dengan formalisasi dan contoh |
| 11 | Skema Fakta KG (SPO) sudah didefinisikan (8 tipe entitas, 12 predikat) | ✅ PASS | BAB III §3.5.1 — 8 tipe entitas (METHOD, CONCEPT, DOMAIN, FINDING, DATASET, METRIC, PAPER, CONSTRAINT) dan 12 predikat (USES_METHOD s.d. DISCUSSES) |
| 12 | Contoh transformasi teks→SPO sudah ditulis | ✅ PASS | BAB III §3.5.3 — contoh lengkap: teks input → entity extraction (10 entitas) → relation extraction (6 penanda) → 9 triple SPO |
| 13 | Contoh penalaran rule engine sudah ditulis | ✅ PASS | BAB III §3.4.4 dan §3.5.5 — skenario CNN_Segmentation + mobile health app, 4 langkah rule engine evaluation, verdict REJECT |

---

## Evaluasi

| # | Item | Status | Lokasi/Bukti |
|---|------|--------|--------------|
| 14 | 7 metrik evaluasi baru sudah ditambahkan | ✅ PASS | BAB III §3.7.1 — EAR, LCS, AS, FDR, SHG, RERR, REP (7 metrik dalam tabel) |
| 15 | Hipotesis H4–H8 sudah ditambahkan | ✅ PASS | BAB III §3.7.2 — H4 (EAR ≥ 50%), H5 (LCS ≥ 3.5), H6 (agentic > pipeline), H7 (rule engine ↓ FDR), H8 (waktu ↓ vs manual) |
| 16 | Ground truth sudah direvisi (pakar juga menilai output) | ✅ PASS | BAB III §3.7.3 — pakar memberikan label per indikator: Genuine Gap / Trivial / Illogical / Already Addressed |
| 17 | Success criteria mencakup expert acceptance rate | ✅ PASS | BAB III §3.7.5 — EAR ≥ 50% sebagai kriteria keberhasilan pertama dalam tabel |

---

## Referensi

| # | Item | Status | Lokasi/Bukti |
|---|------|--------|--------------|
| 18 | 15 referensi baru sudah ditambahkan | ✅ PASS | BAB II memuat 25 referensi; referensi baru mencakup: Bender & Koller 2020, Bosselut 2019, Bowman 2015, Buchanan & Shortliffe 1984, Garcez 2019, Giarratano 2005, Ji 2021, Marcus 2020, Marcus & Davis 2020, Muller-Bloch 2015, Robinson 2011, Yao 2023, Pare 2015, Ammar 2018, Williams 2018, Marshall 2019 (≥16 baru) |
| 19 | Sub-bab baru di BAB II sudah ditulis | ✅ PASS | §2.4 Batasan Penalaran LLM, §2.5 Neuro-Symbolic AI, §2.6 KG sebagai Fact Base, §2.7 Rule-Based Expert Systems, §2.8 NLI, §2.9 AI Agent & Multi-Step Reasoning, §2.10 Posisi Penelitian |
| 20 | Semua klaim didukung referensi | ✅ PASS | Spot check: semua klaim substantif di BAB I, II, III memiliki sitasi inline (Cooper 1998, Booth 2012, Garcez 2019, Marcus 2020, Bender & Koller 2020, dll.) |

---

## Anti-patterns (must NOT exist)

| # | Item | Status | Lokasi/Bukti |
|---|------|--------|--------------|
| 21 | Tidak ada klaim "menemukan gap secara otomatis" | ✅ PASS | `grep -ri` di seluruh /drafts/ — 0 match. Konsisten menggunakan "mendeteksi indikator" |
| 22 | Tidak ada definisi "Unexplored Combinations (Method A + Domain B)" | ✅ PASS | `grep -ri` di seluruh /drafts/ — 0 match. BAB II §2.2.2 bahkan secara eksplisit menyatakan bahwa ini BUKAN synthesis gap |
| 23 | Tidak ada diagram linear black-box | ✅ PASS | Semua diagram menunjukkan arsitektur 4 fase dengan Logical Consistency Checker dan feedback loop. Kata "black box" hanya muncul di NOVELTY_STATEMENT sebagai kritik terhadap pendekatan *lain* |

---

## Perbaikan yang Dilakukan

| # | File | Perubahan | Alasan |
|---|------|-----------|--------|
| 1 | `BAB_II_TINJAUAN_PUSTAKA.md` §2.6.3 | Ditambahkan "METRIC" ke daftar tipe entitas | Inkonsistensi: BAB II hanya mencantumkan 7 tipe entitas, padahal BAB III §3.5.1 dan NOVELTY mendefinisikan 8 tipe (termasuk METRIC) |

---

## Ringkasan

- **Total item checklist:** 23
- **PASS:** 23/23
- **FAIL:** 0/23
- **Perbaikan minor:** 1 (inkonsistensi tipe entitas di BAB II, sudah diperbaiki)

Semua dokumen draf sudah konsisten dengan checklist final revisi.md §14.
