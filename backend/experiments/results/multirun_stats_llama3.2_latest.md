## Statistik Multi-Run — model llama3.2:latest

| Mode | n run | Seeds | Indikator (mean±std) | Avg Conf (mean±std) | Fakta SPO (mean±std) | RERR % (mean±std) |
|---|---|---|---|---|---|---|
| full | 5 | 43, 44, 45, 46, 47 | 17.2 ± 3.2 | 0.73 ± 0.021 | 133 ± 9.3 | 3.8 ± 8.5 |
| no-rule-engine | 5 | 43, 44, 45, 46, 47 | 18.2 ± 5.5 | 0.728 ± 0.021 | 127 ± 3.2 | 0 ± 0 |
| linear-baseline | 5 | 43, 44, 45, 46, 47 | 20 ± 0 | 0.709 ± 0.0082 | 0 ± 0 | 0 ± 0 |
| nli | 7 | 43, 44, 45, 46, 47, 48, 49 | 24.3 ± 2.3 | 0.791 ± 0.012 | 130 ± 8.4 | 0 ± 0 |
| no-nli | 5 | 43, 44, 45, 46, 47 | 15.2 ± 1.9 | 0.749 ± 0.025 | 137 ± 12 | 4.44 ± 9.9 |
| cross-critic | 5 | 43, 44, 45, 46, 47 | 4.2 ± 4.1 | 0.884 ± 0.07 | 124 ± 6.7 | 0 ± 0 |

### Kontrol Negatif — false-gap rate

_Topik kontrol (TC) sengaja tidak ada di korpus; sistem terkalibrasi seharusnya menemukan ≈0 indikator (false gaps) di sana._

| Mode | n run dgn kontrol | False gaps/run (mean±std) | Run bebas false-gap |
|---|---|---|---|
| full | 0 | — | — |
| no-rule-engine | 0 | — | — |
| linear-baseline | 0 | — | — |
| nli | 0 | — | — |
| no-nli | 0 | — | — |
| cross-critic | 5 | 0.2 ± 0.45 | 4/5 |

### Uji Signifikansi Primer — per-run summaries

| Perbandingan | Hipotesis | Variabel | U | p-value | p Holm | Sig Holm (α=0.05) | Effect size & 95% CI |
|---|---|---|---|---|---|---|---|
| full vs no-rule-engine | H7 | jumlah indikator/run | 11.5 | 0.9155 | 1.0000 | tidak | δ=-0.08 (negligible); r=0.08; Δmed=3 [-9, 6] |
| full vs no-rule-engine | H7 | mean confidence/run | 12.0 | 1.0000 | 1.0000 | tidak | δ=-0.04 (negligible); r=0.04; Δmed=0.014 [-0.039, 0.04] |
| full vs linear-baseline | H6 | jumlah indikator/run | 5.0 | 0.1188 | 0.4752 | tidak | δ=-0.6 (large); r=0.6; Δmed=-2 [-7, 1] |
| full vs linear-baseline | H6 | mean confidence/run | 19.0 | 0.2073 | 0.6219 | tidak | δ=0.52 (large); r=-0.52; Δmed=0.017 [-0.01, 0.043] |
| nli vs no-nli | H9 | jumlah indikator/run | 35.0 | 0.0055 | 0.0428 | ya | δ=1.0 (large); r=-1.0; Δmed=8 [5, 13] |
| nli vs no-nli | H9 | mean confidence/run | 35.0 | 0.0057 | 0.0428 | ya | δ=1.0 (large); r=-1.0; Δmed=0.038 [0.013, 0.082] |
| cross-critic vs nli | H10 | jumlah indikator/run | 0.0 | 0.0053 | 0.0428 | ya | δ=-1.0 (large); r=1.0; Δmed=-19 [-26, -12] |
| cross-critic vs nli | H10 | mean confidence/run | 35.0 | 0.0057 | 0.0428 | ya | δ=1.0 (large); r=-1.0; Δmed=0.059 [0.029, 0.2] |

### Uji Eksploratori — pooled confidence per indikator

_Caveat: confidence indikator dipool lintas topik/run hanya untuk kontinuitas analisis; ini berisiko pseudo-replication karena indikator dari run yang sama tidak independen._

| Perbandingan | Hipotesis | Variabel | U | p-value | p Holm | Sig Holm (α=0.05) | Effect size & 95% CI |
|---|---|---|---|---|---|---|---|
| full vs no-rule-engine | H7 | confidence per indikator (pooled; eksploratori) | 3884.5 | 0.9336 | 0.9336 | tidak | δ=-0.007 (negligible); r=0.007; Δmed=0.0 [-0.1, 0.0] |
| full vs linear-baseline | H6 | confidence per indikator (pooled; eksploratori) | 4835.5 | 0.1394 | 0.4183 | tidak | δ=0.125 (negligible); r=-0.125; Δmed=0.1 [0.0, 0.1] |
| nli vs no-nli | H9 | confidence per indikator (pooled; eksploratori) | 7017.0 | 0.2775 | 0.5551 | tidak | δ=0.086 (negligible); r=-0.086; Δmed=0.0 [-0.05, 0.05] |
| cross-critic vs nli | H10 | confidence per indikator (pooled; eksploratori) | 2329.0 | 0.0223 | 0.0892 | tidak | δ=0.305 (small); r=-0.305; Δmed=0.05 [0.0, 0.183] |

_Effect size: Cliff's δ (negligible/small/medium/large), rank-biserial r, dan selisih median dengan 95% CI bootstrap. Uji primer memakai satu observasi per run; n run kecil (default 3) membatasi power, sehingga p ≥ 0.05 berarti 'belum ada bukti perbedaan', bukan 'terbukti sama'. Holm-Bonferroni diterapkan per tabel pada keluarga perbandingan ablation._