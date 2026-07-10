## Statistik Multi-Run — model gpt-oss:latest

| Mode | n run | Seeds | Indikator (mean±std) | Avg Conf (mean±std) | Fakta SPO (mean±std) | RERR % (mean±std) |
|---|---|---|---|---|---|---|
| full | 3 | 43, 44, 45 | 13 ± 1 | 0.732 ± 0.009 | 17 ± 7.2 | 0 ± 0 |
| no-rule-engine | 3 | 43, 44, 45 | 16 ± 2.6 | 0.738 ± 0.019 | 14.3 ± 10 | 0 ± 0 |
| linear-baseline | 3 | 43, 44, 45 | 17.3 ± 2.3 | 0.739 ± 0.031 | 0 ± 0 | 0 ± 0 |
| nli | 3 | 43, 44, 45 | 22.3 ± 1.2 | 0.791 ± 0.0029 | 17.7 ± 8.1 | 0 ± 0 |
| no-nli | 3 | 43, 44, 45 | 14.3 ± 0.58 | 0.704 ± 0.0084 | 14.3 ± 0.58 | 0 ± 0 |

### Uji Signifikansi Primer — per-run summaries

| Perbandingan | Hipotesis | Variabel | U | p-value | p Holm | Sig Holm (α=0.05) | Effect size & 95% CI |
|---|---|---|---|---|---|---|---|
| full vs no-rule-engine | H7 | jumlah indikator/run | 0.5 | 0.1212 | 0.4332 | tidak | δ=-0.889 (large); r=0.889; Δmed=-2 [-7, 0] |
| full vs no-rule-engine | H7 | mean confidence/run | 3.5 | 0.8248 | 1.0000 | tidak | δ=-0.222 (small); r=0.222; Δmed=-0.008 [-0.034, 0.023] |
| full vs linear-baseline | H6 | jumlah indikator/run | 0.0 | 0.0765 | 0.4332 | tidak | δ=-1.0 (large); r=1.0; Δmed=-3 [-8, -2] |
| full vs linear-baseline | H6 | mean confidence/run | 4.0 | 1.0000 | 1.0000 | tidak | δ=-0.111 (negligible); r=0.111; Δmed=-0.008 [-0.046, 0.033] |
| nli vs no-nli | H9 | jumlah indikator/run | 9.0 | 0.0722 | 0.4332 | tidak | δ=1.0 (large); r=-1.0; Δmed=9 [6, 9] |
| nli vs no-nli | H9 | mean confidence/run | 9.0 | 0.0765 | 0.4332 | tidak | δ=1.0 (large); r=-1.0; Δmed=0.085 [0.079, 0.099] |

### Uji Eksploratori — pooled confidence per indikator

_Caveat: confidence indikator dipool lintas topik/run hanya untuk kontinuitas analisis; ini berisiko pseudo-replication karena indikator dari run yang sama tidak independen._

| Perbandingan | Hipotesis | Variabel | U | p-value | p Holm | Sig Holm (α=0.05) | Effect size & 95% CI |
|---|---|---|---|---|---|---|---|
| full vs no-rule-engine | H7 | confidence per indikator (pooled; eksploratori) | 876.0 | 0.6044 | 0.6044 | tidak | δ=-0.064 (negligible); r=0.064; Δmed=-0.05 [-0.05, 0.05] |
| full vs linear-baseline | H6 | confidence per indikator (pooled; eksploratori) | 1248.0 | 0.0588 | 0.1176 | tidak | δ=0.231 (small); r=-0.231; Δmed=0.05 [0.035, 0.15] |
| nli vs no-nli | H9 | confidence per indikator (pooled; eksploratori) | 1792.5 | 0.0300 | 0.0901 | tidak | δ=0.244 (small); r=-0.244; Δmed=0.05 [0.0, 0.15] |

_Effect size: Cliff's δ (negligible/small/medium/large), rank-biserial r, dan selisih median dengan 95% CI bootstrap. Uji primer memakai satu observasi per run; n run kecil (default 3) membatasi power, sehingga p ≥ 0.05 berarti 'belum ada bukti perbedaan', bukan 'terbukti sama'. Holm-Bonferroni diterapkan per tabel pada keluarga perbandingan ablation._