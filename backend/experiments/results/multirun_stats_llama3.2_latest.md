## Statistik Multi-Run — model llama3.2:latest

| Mode | n run | Seeds | Indikator (mean±std) | Avg Conf (mean±std) | Fakta SPO (mean±std) | RERR % (mean±std) |
|---|---|---|---|---|---|---|
| cross-critic | 5 | 43, 44, 45, 46, 47 | 4.2 ± 4.1 | 0.884 ± 0.07 | 124 ± 6.7 | 0 ± 0 |

### Kontrol Negatif — false-gap rate

_Topik kontrol (TC) sengaja tidak ada di korpus; sistem terkalibrasi seharusnya menemukan ≈0 indikator (false gaps) di sana._

| Mode | n run dgn kontrol | False gaps/run (mean±std) | Run bebas false-gap |
|---|---|---|---|
| cross-critic | 5 | 0.2 ± 0.45 | 4/5 |

### Uji Signifikansi Primer — per-run summaries

_Tidak ada perbandingan dengan data lengkap._

### Uji Eksploratori — pooled confidence per indikator

_Caveat: confidence indikator dipool lintas topik/run hanya untuk kontinuitas analisis; ini berisiko pseudo-replication karena indikator dari run yang sama tidak independen._

_Tidak ada perbandingan dengan data lengkap._

_Effect size: Cliff's δ (negligible/small/medium/large), rank-biserial r, dan selisih median dengan 95% CI bootstrap. Uji primer memakai satu observasi per run; n run kecil (default 3) membatasi power, sehingga p ≥ 0.05 berarti 'belum ada bukti perbedaan', bukan 'terbukti sama'. Holm-Bonferroni diterapkan per tabel pada keluarga perbandingan ablation._