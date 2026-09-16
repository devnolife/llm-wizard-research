#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grafik untuk deck sidang — dibangun dari angka BAB IV (drafts/BAB_IV_*.md)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)
NAVY, RED, GREY, GREEN, AMBER = "#1F3A5F", "#B22222", "#6B7280", "#2E7D32", "#C77700"
plt.rcParams.update({"font.size": 13, "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


# 1) Stabilitas k/n (Subbab 4.3.10)
fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1.3]})
k = ["k = 1\n(tidak stabil)", "k = 2", "k = 3"]
v = [221, 111, 196]
cols = [GREY, NAVY, NAVY]
bars = a.bar(k, v, color=cols)
for bar, val in zip(bars, v):
    a.text(bar.get_x() + bar.get_width() / 2, val + 5, f"{val}\n({val/528:.0%})", ha="center", fontsize=12)
a.set_title("528 pernyataan gap dari 3 run identik", fontsize=14, color=NAVY)
a.set_ylabel("jumlah gap")
a.set_ylim(0, 260)
a.text(1.5, 240, "stabil (k ≥ 2): 307 = 58,1%", ha="center", fontsize=12, color=NAVY, fontweight="bold")

types = ["Keterbatasan\ntersurat", "Future work\neksplisit", "Gap implisit\n(inferensi LLM)"]
stable = [197, 70, 40]
total = [315, 116, 97]
unstable = [t - s for t, s in zip(total, stable)]
b.barh(types, stable, color=NAVY, label="stabil (k ≥ 2)")
b.barh(types, unstable, left=stable, color="#D1D5DB", label="tidak stabil (k = 1)")
for i, (s, t) in enumerate(zip(stable, total)):
    b.text(t + 4, i, f"{s/t:.0%} stabil", va="center", fontsize=12, color=NAVY, fontweight="bold")
b.set_xlim(0, 400)
b.invert_yaxis()
b.set_title("Stabilitas menurut jenis pernyataan", fontsize=14, color=NAVY)
b.legend(loc="lower right", frameon=False)
fig.suptitle("M13 — Angka satu run adalah satu undian: Jaccard antar-run 0,45–0,65", fontsize=13, color=GREY, y=1.02)
save(fig, "kn_stability")

# 2) Multi-run semua mode (Subbab 4.3.6 & 4.3.12)
fig, ax = plt.subplots(figsize=(12, 4.8))
modes = ["linear-baseline", "no-rule-engine", "full", "no-nli", "nli", "cross-critic"]
mean = [20.0, 18.2, 17.2, 15.2, 24.3, 4.2]
sd = [0.0, 5.5, 3.2, 1.9, 2.3, 4.1]
conf = [0.709, 0.728, 0.730, 0.749, 0.791, 0.884]
colors = [GREY, GREY, NAVY, GREY, GREEN, RED]
y = list(range(len(modes)))
ax.barh(y, mean, xerr=sd, color=colors, capsize=5, error_kw={"lw": 1.2})
ax.set_yticks(y)
ax.set_yticklabels(modes)
ax.invert_yaxis()
ax.set_xlabel("indikator per run (mean ± sd, llama3.2, seed 43–47/49)")
for i, (m, s, c) in enumerate(zip(mean, sd, conf)):
    ax.text(m + s + 0.6, i, f"confidence {c:.3f}", va="center", fontsize=12, color=GREY)
ax.set_xlim(0, 34)
ax.text(27.5, 4.45, "H9: nli > no-nli — Δmed = 8, p Holm = 0,043, δ = 1,0", fontsize=12, color=GREEN, fontweight="bold")
ax.text(12.5, 5.45, "H10: cross-critic < nli — Δmed = −19, p Holm = 0,043; 85,6% kandidat ditolak", fontsize=12, color=RED, fontweight="bold")
fig.text(0.13, -0.02, "H6 (full vs linear) & H7 (full vs no-rule-engine): tidak signifikan (p Holm ≥ 0,48) — kontribusi Rule Engine kualitatif",
         fontsize=11.5, color=GREY)
ax.set_title("Ablasi multi-run: satu observasi per run, Mann–Whitney U, koreksi Holm (8 uji)", fontsize=14, color=NAVY)
save(fig, "modes_multirun")

# 3) Cross-critic per seed + kontrol negatif (Subbab 4.3.12)
fig, ax = plt.subplots(figsize=(12, 4.6))
seeds = ["43", "44", "45", "46", "47"]
cand = [30, 31, 30, 31, 31]
rej = [26, 30, 19, 29, 27]
final = [4, 1, 11, 0, 4]
tc = [0, 0, 0, 1, 0]
x = list(range(len(seeds)))
w = 0.26
ax.bar([i - w for i in x], cand, w, color="#D1D5DB", label="kandidat indikator")
ax.bar(x, rej, w, color=RED, label="ditolak kritikus (gpt-oss)")
ax.bar([i + w for i in x], final, w, color=NAVY, label="indikator akhir (T1–T4)")
for i, t in enumerate(tc):
    if t:
        ax.annotate("1 indikator PALSU lolos pada topik kontrol\n(confidence 0,885 — lebih tinggi dari rerata)",
                    xy=(i + w, final[i] + 0.3), xytext=(i - 2.2, 22), fontsize=12, color=AMBER, fontweight="bold",
                    arrowprops={"arrowstyle": "->", "color": AMBER})
    else:
        ax.text(i + w, final[i] + 0.6, "TC: 0", ha="center", fontsize=11, color=GREEN)
ax.set_xticks(x)
ax.set_xticklabels([f"seed {s}" for s in seeds])
ax.set_ylabel("jumlah")
ax.set_ylim(0, 36)
ax.legend(loc="upper right", frameon=False, ncol=3, fontsize=11)
ax.set_title("Cross-critic (5 run) & topik kontrol negatif “quantum biology in marine ecosystems”: false-gap 0,2 ± 0,45 per run; 4/5 run bersih",
             fontsize=12.5, color=NAVY)
save(fig, "crosscritic_control")

# 4) Korpus aplikatif: 4 indikator versi akhir (Subbab 4.3.11)
fig, ax = plt.subplots(figsize=(12, 4.3))
labels = ["Fragmentasi —\nkopling bibliografis\n(bebas LLM)", "Ketidaklengkapan —\n10/10 aspek tak dibahas",
          "Fragmentasi —\nisolasi embedding 0,82", "Ketiadaan dukungan bukti —\n3/3 klaim tanpa bukti primer"]
raw = [0.828, 0.750, 0.720, 0.650]
cal = [0.911, 0.825, 0.792, 0.715]
held = [False, False, True, False]
corr = ["", "korroborasi penulis:\n1 pernyataan (skor 0,69)", "", "korroborasi penulis:\n3 pernyataan (0,68–0,71)"]
x = list(range(4))
ax.bar([i - 0.18 for i in x], raw, 0.36, color="#9CA3AF", label="confidence mentah")
ax.bar([i + 0.18 for i in x], cal, 0.36, color=[RED if h else NAVY for h in held], label="terkalibrasi (verdict PASS ×1,10)")
for i in x:
    ax.text(i + 0.18, cal[i] + 0.015, f"{cal[i]:.3f}", ha="center", fontsize=12)
    if corr[i]:
        ax.text(i, cal[i] + 0.075, corr[i], ha="center", fontsize=11, color=GREEN, fontweight="bold")
ax.text(2 + 0.18, cal[2] + 0.075, "DITAHAN untuk peninjauan:\nkutipan tidak terambil", ha="center", fontsize=11, color=RED, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=11.5)
ax.set_ylim(0, 1.15)
ax.set_ylabel("confidence")
ax.legend(loc="upper center", frameon=False, fontsize=11, ncol=2, bbox_to_anchor=(0.5, -0.28))
ax.set_title("Korpus 35 jurnal forensika digital — versi akhir: 4 indikator, 4 PASS (RERR 0%), 1 ditahan, korroborasi penulis 2/2",
             fontsize=12.5, color=NAVY)
save(fig, "forensik_indicators")

print("figures ->", OUT)
