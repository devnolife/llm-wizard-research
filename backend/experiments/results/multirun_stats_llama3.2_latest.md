## Statistik Multi-Run — model llama3.2:latest

| Mode | n run | Seeds | Indikator (mean±std) | Avg Conf (mean±std) | Fakta SPO (mean±std) | RERR % (mean±std) |
|---|---|---|---|---|---|---|
| full | 5 | 43, 44, 45, 46, 47 | 17.2 ± 3.2 | 0.73 ± 0.021 | 133 ± 9.3 | 3.8 ± 8.5 |
| no-rule-engine | 5 | 43, 44, 45, 46, 47 | 18.2 ± 5.5 | 0.728 ± 0.021 | 127 ± 3.2 | 0 ± 0 |
| linear-baseline | 5 | 43, 44, 45, 46, 47 | 20 ± 0 | 0.709 ± 0.0082 | 0 ± 0 | 0 ± 0 |
| nli | 5 | 43, 44, 45, 46, 47 | 25 ± 2.3 | 0.788 ± 0.013 | 128 ± 8.9 | 0 ± 0 |
| no-nli | 5 | 43, 44, 45, 46, 47 | 15.2 ± 1.9 | 0.749 ± 0.025 | 137 ± 12 | 4.44 ± 9.9 |

### Uji Signifikansi Primer — per-run summaries

| Perbandingan | Hipotesis | Variabel | U | p-value | p Holm | Sig Holm (α=0.05) | Effect size & 95% CI |
|---|---|---|---|---|---|---|---|
| full vs no-rule-engine | H7 | jumlah indikator/run | 11.5 | 0.9155 | 1.0000 | tidak | δ=-0.08 (negligible); r=0.08; Δmed=3 [-9, 6] |
| full vs no-rule-engine | H7 | mean confidence/run | 12.0 | 1.0000 | 1.0000 | tidak | δ=-0.04 (negligible); r=0.04; Δmed=0.014 [-0.039, 0.04] |
| full vs linear-baseline | H6 | jumlah indikator/run | 5.0 | 0.1188 | 0.4752 | tidak | δ=-0.6 (large); r=0.6; Δmed=-2 [-7, 1] |
| full vs linear-baseline | H6 | mean confidence/run | 19.0 | 0.2073 | 0.6219 | tidak | δ=0.52 (large); r=-0.52; Δmed=0.017 [-0.01, 0.043] |
| nli vs no-nli | H9 | jumlah indikator/run | 25.0 | 0.0119 | 0.0716 | tidak | δ=1.0 (large); r=-1.0; Δmed=11 [6, 13] |
| nli vs no-nli | H9 | mean confidence/run | 25.0 | 0.0119 | 0.0716 | tidak | δ=1.0 (large); r=-1.0; Δmed=0.026 [0.006, 0.07] |

### Uji Eksploratori — pooled confidence per indikator

_Caveat: confidence indikator dipool lintas topik/run hanya untuk kontinuitas analisis; ini berisiko pseudo-replication karena indikator dari run yang sama tidak independen._

| Perbandingan | Hipotesis | Variabel | U | p-value | p Holm | Sig Holm (α=0.05) | Effect size & 95% CI |
|---|---|---|---|---|---|---|---|
| full vs no-rule-engine | H7 | confidence per indikator (pooled; eksploratori) | 3884.5 | 0.9336 | 0.9336 | tidak | δ=-0.007 (negligible); r=0.007; Δmed=0.0 [-0.1, 0.0] |
| full vs linear-baseline | H6 | confidence per indikator (pooled; eksploratori) | 4835.5 | 0.1394 | 0.4183 | tidak | δ=0.125 (negligible); r=-0.125; Δmed=0.1 [0.0, 0.1] |
| nli vs no-nli | H9 | confidence per indikator (pooled; eksploratori) | 5089.0 | 0.3940 | 0.7880 | tidak | δ=0.071 (negligible); r=-0.071; Δmed=0.0 [-0.05, 0.05] |

_Effect size: Cliff's δ (negligible/small/medium/large), rank-biserial r, dan selisih median dengan 95% CI bootstrap. Uji primer memakai satu observasi per run; n run kecil (default 3) membatasi power, sehingga p ≥ 0.05 berarti 'belum ada bukti perbedaan', bukan 'terbukti sama'. Holm-Bonferroni diterapkan per tabel pada keluarga perbandingan ablation._