# Monitor Analisis Jurnal (Full Streamlit)

Dashboard mandiri untuk menjalankan dan memahami pipeline analisis —
**tidak perlu frontend React**: unggah PDF, pantau proses per tahap, dan baca
hasil akhirnya langsung di Streamlit.

## Halaman

1. **📊 Dashboard** — ringkasan (total analisis, selesai, berjalan, file),
   pemakaian server (CPU/RAM/GPU) dalam expander *collapsed*, dan **riwayat
   analisis** berupa kartu (status, waktu, file, jumlah topik/gap/usulan)
   dengan tombol *Buka detail & hasil*, tombol 🔁 **analisis ulang** (job baru
   dari PDF yang sama memakai engine LLM aktif; hasil lama tetap tersimpan
   untuk perbandingan), dan tombol 🗑️ **hapus** (dengan
   konfirmasi; job yang sedang berjalan harus dibatalkan dulu).
2. **🔎 Cari Paper** — dua mode: **💡 ide penelitian** (AI/LLM lokal mengubah ide
   Bahasa Indonesia menjadi kata kunci akademik Inggris) atau **🔑 kata kunci
   langsung**. Hasil dari 8 sumber akademik (arXiv, Europe PMC, CrossRef,
   Semantic Scholar, CORE, PubMed, Scopus, ScienceDirect), lihat badge
   🔓 open-access / 🎯 coba-via-DOI / 🔒 berbayar, centang paper, lalu
   **📥 Unduh & Analisis** — PDF open-access legal diunduh server (langsung /
   resolve Unpaywall) dan otomatis jadi job analisis baru.
3. **🔬 Proses & Hasil** — unggah PDF / pilih job; lalu:
   - **🤖 Unduh paket lengkap (.md)**: satu berkas Markdown berisi *seluruh*
     hasil run (korpus, ringkasan, status lapisan metode, tiap indikator gap
     lengkap dengan rantai provenans + kutipan verbatim, usulan + skor
     kebaruan, peta jalan, kekurangan per jurnal, metrik, keterbatasan).
     Diawali front-matter YAML agar metadatanya bisa diurai mesin — cukup
     lampirkan berkas ini ke agen AI tanpa perlu akses API. Dibangun oleh
     `export_bundle.py`, yang juga bisa dipanggil dari terminal bila UI tak
     terjangkau (mis. tunnel SSH bermasalah):

     ```bash
     .venv/bin/python export_bundle.py            # job terbaru
     .venv/bin/python export_bundle.py --list     # daftar job yang selesai
     .venv/bin/python export_bundle.py 977fdd5a   # job tertentu
     .venv/bin/python export_bundle.py -o hasil.md
     ```

     Alamat backend dibaca dari `MONITOR_API` (bawaan `http://127.0.0.1:8001/api`).
   - **📦 Unduh hasil ekstraksi PDF → chunk** (expander): data *mentah* sebelum
     diolah LLM — seluruh chunk milik job beserta `source`, `title`, `year`,
     `section`, dan `chunk_index`. Dua format: **JSONL** (satu chunk per baris,
     untuk program/agen) atau **Markdown** (dikelompokkan per jurnal). Berkasnya
     besar (±2 MB) sehingga baru diambil setelah tombol **⚙️ Siapkan berkas**
     ditekan, bukan pada tiap rerun. Sumbernya endpoint
     `GET /api/analysis-status/{job_id}/chunks?format=jsonl|md`, yang juga bisa
     dipakai langsung dari terminal:

     ```bash
     curl -OJ "http://127.0.0.1:8001/api/analysis-status/<job_id>/chunks?format=jsonl"
     ```

     Chunk lengkap tidak disimpan di `results` (di sana hanya ada 3 sampel per
     jurnal, dipangkas 350 karakter); teks utuhnya diambil ulang dari vector
     store dan dideduplikasi per `(source, chunk_index)` karena satu PDF bisa
     terindeks oleh beberapa job.
   - **🏁 Hasil Akhir** (tab): Ringkasan (metrik alur: jurnal → kekurangan →
     gap → usulan, plus **🧪 Status Lapisan Metode** run ini: indikator yang
     lolos per tipe, provenans lengkap X/Y, jumlah ditahan/abstain,
     temperature kalibrasi, dan rentang skor kebaruan usulan) · **Gap per
     Jurnal** (kekurangan tersurat/tersirat tiap
     jurnal + kutipan & dasarnya) · Topik · Gap Penelitian (menyebut jurnal
     yang terlibat per gap, plus 🔬 lensa taksonomi Miles 2017 dan 📅 rentang
     tahun basis literatur per gap) · Usulan (menunjuk gap yang dijawab) ·
     Peta Jalan.
   - **🕸️ Knowledge Graph** interaktif (fakta SPO, klaster berwarna, drag/zoom).
   - **🧭 Detail Proses per Tahap**: 8 tahap dengan durasi, 📦 hasil tiap tahap
     (teks ekstraksi per file, fakta SPO, dll), dan 🧠 prompt + jawaban LLM.
4. **📚 Jurnal & Gap** — halaman khusus membaca jurnal satu per satu: metrik
   (jurnal, kekurangan tersurat/tersirat, terlibat gap), 🔍 cari + saring +
   urutkan, tabel ringkasan dengan **unduh CSV** (lampiran tesis), dan kartu
   per jurnal berisi kekurangan (kutipan ✅terverifikasi + dasarnya) serta
   **gap kolektif yang melibatkan jurnal itu**.
5. **🚀 Tindak Lanjut Gap** — proses **setelah gap ditemukan**: ① pilih gap
   (plus tombol 🔎 *cari jurnal baru untuk menguji gap* → melompat ke Cari
   Paper dengan ide terisi) → ② baca usulan penelitian yang menjawabnya
   (mengapa & bagaimana, prioritas) → ③ peta jalan pelaksanaan → ④ **unduh
   paket tindak lanjut (.md)** atau tombol 🧠 *Kembangkan jadi rencana
   penelitian lengkap* (melompat ke Skill Riset dengan ide sudah terisi).
   Dilengkapi expander ℹ️ *bagaimana gap ditentukan & metode alternatifnya*.
6. **🎓 Metode & Uji Coba** — peta metode proposal → bagian sistem (diagram
   pipeline 4 fase + 8 kartu komponen dengan penunjuk “lihat di web ini” dan
   path kodenya), hasil **eksperimen ablasi** (rata-rata ± std antar run per
   varian × model, bar chart + tabel), dan **uji adversarial Rule Engine**.
7. **🧠 Skill Riset** — tulis ide penelitian → **LLM memilih sendiri** 2–3 skill
   paling relevan dari 95 [AI-Research-SKILLs](https://github.com/Orchestra-Research/AI-Research-SKILLs)
   (`.agents/skills/`) → menyusun **rekomendasi penelitian lengkap**: judul,
   latar belakang, rumusan masalah, tujuan, metodologi bertahap dengan **bagan
   alur (graphviz)**, rencana eksperimen (tabel), kontribusi, risiko, dan kata
   kunci literatur (tombol lompat ke halaman Cari Paper). Engine: GitHub
   Copilot via copilotd, fallback Ollama.
8. **🧾 Log Event** — riwayat event mentah (metadata-only) per job.

## Menjalankan

```bash
# 1. Pastikan backend berjalan (port 8001)
cd ~/wizard-research && bash run_backend.sh

# 2. Jalankan monitor (venv terisolasi, tidak mengganggu paket backend)
cd ~/wizard-research/tools/process_monitor
.venv/bin/streamlit run app.py
```

Buka `http://localhost:8501` (dari laptop:
`ssh -N -L 3031:127.0.0.1:8501 studio-server` → `http://localhost:3031`).
Bila venv belum ada:

```bash
python -m venv .venv && .venv/bin/pip install streamlit requests pyvis
```

## Struktur berkas

| Berkas | Isi |
| --- | --- |
| `app.py` | Entry `st.navigation` + sidebar pengaturan |
| `common.py` | Helper API, interpretasi event, semua renderer |
| `page_dashboard.py` | Halaman dashboard & riwayat |
| `page_papers.py` | Halaman cari paper multi-sumber + unduh OA + analisis |
| `page_analysis.py` | Halaman proses + hasil akhir + graph |
| `page_method.py` | Halaman metode proposal + eksperimen ablasi + adversarial |
| `page_skills.py` | Halaman ide → rekomendasi penelitian lengkap (LLM memilih skill) |
| `page_events.py` | Halaman log event mentah |

## Endpoint backend yang dipakai

- `GET /api/analysis-jobs` — daftar job untuk dashboard/riwayat.
- `GET /api/analysis-status/{job_id}` — status, progress, dan hasil akhir.
- `GET /api/analysis-status/{job_id}/events` — timeline event per tahap.
- `GET /api/analysis-status/{job_id}/artifacts` — hasil tiap tahap + prompt
  LLM (konten di-cap ±6000 char/field, retensi 14 hari).
- `GET /api/system-stats` — CPU/RAM/disk/GPU + proses per GPU.
- `GET /api/graph?job_id=` — jaringan fakta SPO (nodes/links/klaster).
- `POST /api/upload-and-analyze` — mulai analisis baru.
- `DELETE /api/analysis-jobs/{job_id}` — hapus job + event + artefak + chunk
  vektor + file unggahan (409 bila job masih berjalan).
- `POST /api/papers/search` — pencarian multi-sumber (arXiv, Europe PMC,
  CrossRef, Semantic Scholar, CORE, PubMed, Scopus, ScienceDirect).
  Scopus butuh `ELSEVIER_API_KEY` saja; ScienceDirect tambahan butuh
  IP kampus pelanggan atau `ELSEVIER_INSTTOKEN`.
- `POST /api/papers/download-and-analyze` — unduh PDF open-access legal
  (pdf_url langsung / resolve DOI via Unpaywall) lalu antrekan job analisis;
  paper berbayar dilaporkan `skipped` (unduh manual).
- `POST /api/papers/idea-to-query` — mengubah ide penelitian (Indonesia/Inggris)
  menjadi kata kunci pencarian akademik Inggris (JSON). Memakai **GitHub
  Copilot** (via `copilotd`, service Go Copilot SDK — env `COPILOTD_URL` +
  `COPILOTD_API_KEY`) dan fallback otomatis ke LLM lokal (Ollama) bila mati;
  respons menyertakan `engine` yang dipakai.
- `POST /api/papers/fetch-pdf` — unduh SATU PDF open-access untuk sebuah paper
  (pdf_url / DOI via Unpaywall) dan kirim sebagai berkas `application/pdf` —
  dipakai tombol ⬇️ PDF per dokumen di halaman Cari Paper.
- `GET /api/skills` — daftar 95 AI-Research-SKILLs terpasang (nama+deskripsi
  dari frontmatter `SKILL.md`).
- `POST /api/skills/ask` — jawab pertanyaan riset dengan satu skill sebagai
  system prompt (Copilot → fallback Ollama; respons menyertakan `engine`).
- `POST /api/skills/recommend` — dari sebuah ide: LLM me-routing sendiri 2–3
  skill relevan (fallback heuristik kata kunci) → dokumen skill jadi panduan →
  rekomendasi penelitian terstruktur JSON (judul, latar belakang, rumusan
  masalah, tujuan, metodologi, eksperimen, kontribusi, risiko, kata kunci).

Semua endpoint GET monitoring dikecualikan dari rate limit backend.

## Catatan

- Event (`/events`) tetap metadata-only; konten (hasil & prompt) datang dari
  artefak (`/artifacts`).
- Job lama (dibuat sebelum fitur ini) hanya punya sedikit event dan tanpa
  artefak — timeline tampil seadanya, tetapi hasil akhir tetap tampil.
- Halaman *Metode & Uji Coba* membaca hasil eksperimen langsung dari disk
  (`backend/experiments/results/experiment_*_latest.run*.json`) — tanpa
  endpoint backend baru.
