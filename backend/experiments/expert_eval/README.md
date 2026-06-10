# Evaluasi Pakar — Wizard Research

Tooling untuk evaluasi pakar terhadap indikator synthesis gap yang dihasilkan
sistem (metrik EAR, LCS, AS, FDR, SHG, REP — RINGKASAN_REVISI.md §11).

## Alur

```
hasil eksperimen JSON ──▶ generate_form.py ──▶ expert_form.xlsx
                                                     │ (diisi pakar)
                                                     ▼
expert_metrics.json ◀── compute_metrics.py ◀── form terisi
```

## 1. Buat form penilaian

```bash
cd backend
python experiments/expert_eval/generate_form.py \
    --results experiments/results/experiment_full_llama3.2_latest.json \
    --output experiments/expert_eval/expert_form.xlsx
```

Berikan `expert_form.xlsx` kepada pakar. Sheet **Petunjuk** berisi panduan
pengisian; sheet **Penilaian** berisi indikator yang dinilai. Kolom hijau
diisi pakar, kolom biru (data sistem) jangan diubah.

Penilaian per indikator:

| Kolom | Isi |
|---|---|
| `label` | Genuine gap / Trivial / Illogical / Already addressed |
| `lcs_1to5` | Logical Coherence Score, 1 (tidak logis) – 5 (sangat logis) |
| `as_1to5` | Actionability Score, 1 – 5 |
| `expert_rank` | Peringkat kepentingan dalam satu topik (1 = paling penting) |
| `reject_justified` | yes/no — hanya untuk baris `system_verdict = REJECT` |
| `notes` | Komentar bebas (opsional) |

## 2. Hitung metrik dari form terisi

```bash
python experiments/expert_eval/compute_metrics.py \
    --forms experiments/expert_eval/expert_form_filled.xlsx
```

Untuk lebih dari satu penilai (menghasilkan Cohen's κ):

```bash
python experiments/expert_eval/compute_metrics.py \
    --forms rater1_filled.xlsx --forms rater2_filled.xlsx
```

Output: `expert_metrics.json` + tabel Markdown siap tempel ke BAB IV,
termasuk hasil uji hipotesis **H4** (EAR ≥ 50%) dan **H5** (LCS ≥ 3.5).

## Metrik

| Metrik | Definisi |
|---|---|
| EAR | % indikator berlabel *Genuine gap* |
| FDR | 100% − EAR |
| LCS | Rata-rata skor koherensi logis (1–5) |
| AS | Rata-rata skor aksiabilitas (1–5) |
| SHG | Korelasi Spearman ranking sistem (confidence) vs ranking pakar, per topik |
| REP | % verdict REJECT yang dikonfirmasi pakar sebagai tepat |
