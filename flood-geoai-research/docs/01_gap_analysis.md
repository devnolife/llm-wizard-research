# Analisis Gap Penelitian

**Judul:** Pengembangan Model Multimodal GeoAI untuk Penilaian Kerawanan Banjir
dengan Pendekatan Explainable Artificial Intelligence

## 1. Peta riset saat ini (tiga klaster)

### Klaster A — Pemetaan kerawanan banjir berbasis ML tabular
Studi *flood susceptibility mapping* klasik (RF, SVM, XGBoost, ensemble)
memakai faktor kondisi statis: elevasi, kemiringan, curah hujan, tutupan lahan,
jarak-ke-sungai. Kekuatan: interpretasi mudah, data ringan. Kelemahan:
**unimodal-tabular** — tidak memanfaatkan observasi satelit aktual kejadian
banjir; label sering berasal dari inventaris titik yang bias pelaporan.

### Klaster B — Deep learning pemetaan genangan dari citra satelit
Benchmark seperti Sen1Floods11, WorldFloods, MMFlood memicu gelombang CNN/U-Net
untuk segmentasi air dari Sentinel-1/-2. Kekuatan: akurasi tinggi, skala global.
Kelemahan: (i) mayoritas **satu modality** (SAR saja atau optik saja);
(ii) model **black-box** — hampir tidak ada evaluasi keterjelasan;
(iii) fokus pada *extent mapping* kejadian, bukan *susceptibility*.

### Klaster C — XAI pada pemodelan bahaya geospasial
SHAP/LIME mulai dipakai pada model kerawanan (banjir, longsor), namun:
(i) hampir selalu di **model tabular Klaster A** — bukan model citra/multimodal;
(ii) penjelasan disajikan **deskriptif** (bar plot kepentingan) tanpa
**validasi faithfulness** — apakah penjelasan benar-benar mencerminkan
perilaku model tidak pernah diuji.

## 2. Gap yang teridentifikasi

| # | Gap | Bukti dari literatur | Konsekuensi |
|---|---|---|---|
| G1 | **Fusi multimodal jarang & tidak sistematis** — SAR+optik+terrain jarang digabung dengan ablasi per-modality yang adil | Klaster B didominasi unimodal; studi fusi tidak melaporkan gain per-modality dengan biaya/latensi | Kontribusi tiap sensor tidak diketahui; desain sistem operasional tidak berbasis bukti |
| G2 | **XAI absen dari model citra banjir** — DL flood mapping tidak dijelaskan; XAI banjir terbatas pada model tabular | Klaster B (black-box) vs Klaster C (tabular-only) tidak pernah bertemu | Model akurat tapi tidak dipercaya pengambil kebijakan mitigasi |
| G3 | **Penjelasan tidak pernah divalidasi** — tidak ada uji faithfulness (deletion/insertion) pada XAI kebencanaan | Klaster C menyajikan SHAP sebagai gambar akhir, bukan objek yang diuji | Risiko penjelasan menyesatkan (plausible tapi tidak faithful) |
| G4 | **Kerawanan vs genangan terpisah** — susceptibility statis (A) dan extent dinamis (B) tidak terintegrasi | Dua komunitas, dua jenis label, jarang digabung | Peta kerawanan tidak ter-update oleh observasi kejadian nyata |

## 3. Posisi kontribusi penelitian ini

> **Satu kerangka GeoAI multimodal (SAR + optik + terrain) untuk penilaian
> kerawanan banjir yang penjelasannya diverifikasi secara kuantitatif
> (faithfulness), bukan sekadar divisualisasikan.**

1. **Kontribusi 1 (→G1):** ablasi fusi sistematis S1/S2/terrain dengan metrik
   identik pada benchmark publik — gain fusi terukur per-modality.
2. **Kontribusi 2 (→G2):** integrasi XAI (TreeSHAP untuk model tabular;
   Grad-CAM/attention untuk CNN) langsung pada model multimodal.
3. **Kontribusi 3 (→G3):** protokol evaluasi penjelasan berbasis
   *deletion/insertion test* + konsistensi domain (indeks air fisik).
4. **Kontribusi 4 (→G4):** kerangka kerawanan yang menggabungkan faktor statis
   (terrain, iklim) dan observasi dinamis (genangan multi-kejadian).

## 4. Validasi awal gap (pra-penelitian)

Pra-penelitian pada Sen1Floods11 membuktikan tiga hal (lihat
`04_preliminary_results.md`):
- G1 nyata dan teratasi: fusi S1+S2 menang di semua metrik (IoU 0,876 vs 0,838/0,480).
- G2+G3 dapat dijawab: SHAP pada model fusi menghasilkan penjelasan yang
  **lulus uji faithfulness** (ABC deletion 0,209) dan selaras fisika (MNDWI).
- Pipeline sepenuhnya reproducible dengan data publik dan CPU.
