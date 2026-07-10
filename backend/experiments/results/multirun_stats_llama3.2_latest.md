## Statistik Multi-Run — model llama3.2:latest

| Mode | n run | Seeds | Indikator (mean±std) | Avg Conf (mean±std) | Fakta SPO (mean±std) | RERR % (mean±std) |
|---|---|---|---|---|---|---|
| full | 3 | 43, 44, 45 | 19.3 ± 1.5 | 0.729 ± 0.014 | 128 ± 6.5 | 6.33 ± 11 |
| no-rule-engine | 3 | 43, 44, 45 | 21 ± 5.6 | 0.723 ± 0.019 | 127 ± 2.1 | 0 ± 0 |
| linear-baseline | 3 | 43, 44, 45 | 20 ± 0 | 0.71 ± 0.0087 | 0 ± 0 | 0 ± 0 |
| nli | 3 | 43, 44, 45 | 26.7 ± 0.58 | 0.78 ± 0.00058 | 127 ± 12 | 0 ± 0 |
| no-nli | 3 | 43, 44, 45 | 15.7 ± 2.5 | 0.765 ± 0.0097 | 141 ± 14 | 7.4 ± 13 |

### Uji Signifikansi Primer — per-run summaries

| Perbandingan | Hipotesis | Variabel | U | p-value | p Holm | Sig Holm (α=0.05) | Effect size & 95% CI |
|---|---|---|---|---|---|---|---|
| full vs no-rule-engine | H7 | jumlah indikator/run | 3.0 | 0.7000 | 1.0000 | tidak | δ=-0.333 (medium); r=0.333; Δmed=-3 [-8, 6] |
| full vs no-rule-engine | H7 | mean confidence/run | 5.0 | 1.0000 | 1.0000 | tidak | δ=0.111 (negligible); r=-0.111; Δmed=0.014 [-0.03, 0.035] |
| full vs linear-baseline | H6 | jumlah indikator/run | 3.0 | 0.6428 | 1.0000 | tidak | δ=-0.333 (medium); r=0.333; Δmed=-1 [-2, 1] |
| full vs linear-baseline | H6 | mean confidence/run | 7.0 | 0.4000 | 1.0000 | tidak | δ=0.556 (large); r=-0.556; Δmed=0.017 [-0.001, 0.041] |
| nli vs no-nli | H9 | jumlah indikator/run | 9.0 | 0.0765 | 0.4591 | tidak | δ=1.0 (large); r=-1.0; Δmed=11 [8, 14] |
| nli vs no-nli | H9 | mean confidence/run | 9.0 | 0.0765 | 0.4591 | tidak | δ=1.0 (large); r=-1.0; Δmed=0.013 [0.006, 0.026] |

### Uji Eksploratori — pooled confidence per indikator

_Caveat: confidence indikator dipool lintas topik/run hanya untuk kontinuitas analisis; ini berisiko pseudo-replication karena indikator dari run yang sama tidak independen._

| Perbandingan | Hipotesis | Variabel | U | p-value | p Holm | Sig Holm (α=0.05) | Effect size & 95% CI |
|---|---|---|---|---|---|---|---|
| full vs no-rule-engine | H7 | confidence per indikator (pooled; eksploratori) | 1841.5 | 0.9411 | 1.0000 | tidak | δ=0.008 (negligible); r=-0.008; Δmed=0.0 [-0.1, 0.1] |
| full vs linear-baseline | H6 | confidence per indikator (pooled; eksploratori) | 1951.0 | 0.2512 | 0.7537 | tidak | δ=0.121 (negligible); r=-0.121; Δmed=0.1 [-0.1, 0.125] |
| nli vs no-nli | H9 | confidence per indikator (pooled; eksploratori) | 1895.5 | 0.9398 | 1.0000 | tidak | δ=0.008 (negligible); r=-0.008; Δmed=0.0 [-0.083, 0.05] |

_Effect size: Cliff's δ (negligible/small/medium/large), rank-biserial r, dan selisih median dengan 95% CI bootstrap. Uji primer memakai satu observasi per run; n run kecil (default 3) membatasi power, sehingga p ≥ 0.05 berarti 'belum ada bukti perbedaan', bukan 'terbukti sama'. Holm-Bonferroni diterapkan per tabel pada keluarga perbandingan ablation._