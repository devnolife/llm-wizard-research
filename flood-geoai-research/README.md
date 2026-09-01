# Flood GeoAI Research

**Pengembangan Model Multimodal GeoAI untuk Penilaian Kerawanan Banjir dengan
Pendekatan Explainable Artificial Intelligence**

Pra-penelitian end-to-end dengan data publik nyata (Sen1Floods11) — bukan simulasi.

## Hasil utama

| Eksperimen | Temuan | Angka kunci |
|---|---|---|
| **Exp1 — Fusi multimodal** | Fusi S1 SAR + S2 optik mengungguli tiap modality tunggal di semua metrik | IoU **0,876** (fusi) vs 0,838 (S2) vs 0,480 (S1); F1 0,934; AUC 0,996 — 5,9 juta piksel uji, 25 chip tak terlihat |
| **Exp2 — Explainable AI** | Penjelasan SHAP terbukti *faithful* & selaras fisika | ABC deletion **0,209**; MNDWI dominan (mean\|SHAP\| 1,82); share S2 86% / S1 14%; peta Mekong AUC 0,996 |

## Struktur

```
├── docs/
│   ├── 01_gap_analysis.md          # 4 gap (G1-G4) + posisi kontribusi
│   ├── 02_literature.md            # tinjauan pustaka (paper nyata terverifikasi)
│   ├── 03_datasets.md              # Sen1Floods11 + 10 dataset pelengkap
│   └── 04_preliminary_results.md   # hasil lengkap + tabel + interpretasi
├── src/
│   ├── common.py                   # loader chip + 14 fitur multimodal
│   ├── exp1_fusion.py              # LightGBM S1/S2/Fusi + evaluasi
│   └── exp2_xai.py                 # TreeSHAP + deletion test + peta
├── results/                        # *_metrics.json + 4 figur PNG + model
└── data/                           # 85 chip × (S1,S2,Label) GeoTIFF
```

## Reproduksi

```bash
python3 -m venv venv
./venv/bin/pip install numpy scikit-learn lightgbm shap matplotlib pandas tqdm rasterio
# unduh chip: bash data/dl.sh  (bucket publik gs://sen1floods11)
./venv/bin/python src/exp1_fusion.py   # ±2 menit CPU
./venv/bin/python src/exp2_xai.py     # ±3 menit CPU
```

## Desain eksperimen

- **Data:** Sen1Floods11 hand-labeled, split resmi; 60 chip latih / 25 chip uji
  (geografis terpisah, tidak pernah dilihat saat pelatihan).
- **Fitur (14):** S1 = VV, VH, VV−VH, rerata 5×5 VV/VH; S2 = B2,B3,B4,B8,B11,B12
  + NDWI, MNDWI, NDVI.
- **Model:** LightGBM binary, early stopping pada 12 chip validasi.
- **XAI:** TreeSHAP global + dependence; faithfulness via deletion test
  (mean-imputation, urutan SHAP vs 5 urutan acak).
