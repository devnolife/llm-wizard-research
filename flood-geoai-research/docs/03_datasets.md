# Dataset Publik untuk Penelitian

Daftar dataset publik yang digunakan / dapat digunakan pada penelitian
"Pengembangan Model Multimodal GeoAI untuk Penilaian Kerawanan Banjir dengan
Pendekatan Explainable Artificial Intelligence".

## 1. Dataset utama pra-penelitian (sudah diunduh & dipakai)

### Sen1Floods11 ⭐ (dipakai di Exp1 & Exp2)
- **Sumber:** Cloud to Street — `gs://sen1floods11` (Google Cloud Storage, publik, tanpa login)
- **Referensi:** Bonafilia et al., 2020, *CVPR Workshops (EarthVision)*
- **Isi:** 4.831 chip 512×512 px (10 m/px) dari 11 kejadian banjir di 11 negara
  (Bolivia, Ghana, India, Mekong, Nigeria, Pakistan, Paraguay, Somalia, Spanyol,
  Sri Lanka, AS); 446 chip **berlabel tangan** (train 252 / val 89 / test 90).
- **Modality:** Sentinel-1 GRD (VV+VH, dB) **dan** Sentinel-2 L1C (13 band) yang
  ko-registrasi — ideal untuk studi fusi multimodal.
- **Label:** -1 tak-valid, 0 bukan-air, 1 air.
- **Subset lokal:** 85 chip (60 train + 25 test) × 3 file = 255 GeoTIFF (~350 MB)
  di `data/{S1Hand,S2Hand,LabelHand}/`.

## 2. Dataset pelengkap untuk tesis penuh

| Dataset | Modality | Resolusi | Akses | Peran dalam tesis |
|---|---|---|---|---|
| **MMFlood** (Montello et al., 2022) | S1 + DEM + hydrography, 1.748 kejadian | 20 m | GitHub/Zenodo publik | Fusi SAR+DEM; validasi lintas-dataset |
| **WorldFloods** (Mateo-García et al., 2021) | Sentinel-2, 424 kejadian | 10 m | Hugging Face / GCS | Pre-training model optik |
| **FloodNet** (Rahnemoonfar et al., 2021) | Citra UAV pasca-Harvey, VQA | ~1,5 cm | publik | Studi kasus resolusi sangat tinggi |
| **UrbanSARFloods** (Zhao et al., 2024) | S1 SLC koherensi, banjir urban | 20 m | publik | Kasus sulit: banjir perkotaan |
| **Copernicus DEM GLO-30** | Elevasi global | 30 m | AWS/Copernicus publik | Fitur terrain: slope, TWI, HAND |
| **HydroSHEDS / HydroRIVERS** | Jaringan sungai, akumulasi aliran | 3–15 detik busur | publik | Jarak-ke-sungai, drainase |
| **CHIRPS v2** | Curah hujan harian 1981–kini | 0,05° | publik | Faktor pemicu hujan |
| **ESA WorldCover 2021** | Tutupan lahan 11 kelas | 10 m | publik | Faktor kondisi permukaan |
| **Global Flood Database** (Tellman et al., 2021, *Nature*) | 913 banjir MODIS 2000–2018 | 250 m | publik | Inventaris kejadian historis |
| **EM-DAT** | Basis data bencana global | tabular | registrasi gratis | Konteks dampak & pemilihan kejadian |

## 3. Alasan pemilihan Sen1Floods11 untuk pra-penelitian
1. **Satu-satunya benchmark** dengan pasangan S1+S2 ko-registrasi *dan* label tangan
   berkualitas — prasyarat eksperimen fusi yang adil.
2. Split train/test **terpisah secara geografis** (chip uji tidak pernah dilihat),
   mendukung klaim generalisasi.
3. Ukuran chip moderat → eksperimen CPU cepat dan dapat direproduksi.
4. Lisensi terbuka, unduh langsung via HTTPS tanpa autentikasi.

## 4. Struktur data lokal

```
data/
├── flood_train_data.csv     # split resmi (252 chip)
├── flood_valid_data.csv     # split resmi (89 chip)
├── flood_test_data.csv      # split resmi (90 chip)
├── sel_train.csv            # 60 chip terpilih merata
├── sel_test.csv             # 25 chip terpilih merata
├── chips.txt                # 85 nama chip
├── S1Hand/   *_S1Hand.tif   # (2,512,512) float32 — VV,VH dB
├── S2Hand/   *_S2Hand.tif   # (13,512,512) int16 — refl ×10⁴
└── LabelHand/*_LabelHand.tif # (1,512,512) int16 — {-1,0,1}
```
