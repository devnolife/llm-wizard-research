"""Experiment 2 — Explainable AI untuk model fusi banjir.

Questions:
  (a) What drives the fusion model's predictions? (TreeSHAP global + dependence)
  (b) Are the explanations FAITHFUL? (deletion curve: mask top-SHAP features
      vs random features -> AUC must drop faster for SHAP ordering)
  (c) Can we produce an interpretable susceptibility map?

Inputs : results/fusion_model.txt, results/test_cache.npz (from exp1)
Outputs: results/exp2_metrics.json, results/exp2_shap_importance.png,
         results/exp2_faithfulness.png, results/exp2_susceptibility_map.png
"""
import json, os
import numpy as np
import lightgbm as lgb
import shap
from sklearn.metrics import roc_auc_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

from common import RESULTS, FUSION_FEATS, chip_features, _read

SEED = 42
N_SHAP = 30000          # pixels for SHAP computation
N_EVAL = 400000         # pixels for deletion-curve AUC


def load_cache():
    z = np.load(os.path.join(RESULTS, "test_cache.npz"), allow_pickle=True)
    slices = json.loads(str(z["chips"]))
    return z["Xte"], z["yte"], slices


def deletion_curve(model, X, y, order, fill):
    """AUC after masking first-k features of `order` with `fill` values."""
    aucs = []
    Xm = X.copy()
    aucs.append(roc_auc_score(y, model.predict(Xm)))
    for f in order:
        Xm[:, f] = fill[f]
        aucs.append(roc_auc_score(y, model.predict(Xm)))
    return aucs


def main():
    rng = np.random.default_rng(SEED)
    model = lgb.Booster(model_file=os.path.join(RESULTS, "fusion_model.txt"))
    Xte, yte, slices = load_cache()

    # ---------- (a) SHAP global ----------
    idx = rng.choice(len(yte), size=min(N_SHAP, len(yte)), replace=False)
    Xs, ys = Xte[idx], yte[idx]
    print("computing TreeSHAP ...")
    expl = shap.TreeExplainer(model)
    sv = expl.shap_values(Xs)
    if isinstance(sv, list):
        sv = sv[1]
    mean_abs = np.abs(sv).mean(axis=0)
    rank = np.argsort(mean_abs)[::-1]
    print("top-5:", [(FUSION_FEATS[i], round(float(mean_abs[i]), 3)) for i in rank[:5]])

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))
    names = [FUSION_FEATS[i] for i in rank][::-1]
    vals = mean_abs[rank][::-1]
    cols = ["#fc8d62" if n.startswith("S1") else "#66c2a5" for n in names]
    axes[0].barh(names, vals, color=cols)
    axes[0].set_xlabel("mean |SHAP| (log-odds)")
    axes[0].set_title("(a) Kepentingan fitur global — TreeSHAP")
    axes[0].grid(axis="x", alpha=.3)
    from matplotlib.patches import Patch
    axes[0].legend(handles=[Patch(color="#66c2a5", label="Sentinel-2 (optik)"),
                            Patch(color="#fc8d62", label="Sentinel-1 (SAR)")],
                   loc="lower right", fontsize=8)

    top = rank[0]
    sc = axes[1].scatter(Xs[:, top], sv[:, top], c=ys, cmap=ListedColormap(
        ["#bbbbbb", "#2166ac"]), s=2, alpha=.4)
    axes[1].set_xlabel(FUSION_FEATS[top]); axes[1].set_ylabel("nilai SHAP")
    axes[1].set_title(f"(b) Dependence plot — {FUSION_FEATS[top]}")
    axes[1].grid(alpha=.3)
    axes[1].legend(handles=sc.legend_elements()[0], labels=["bukan air", "air"],
                   fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "exp2_shap_importance.png"), dpi=150)

    # ---------- (b) faithfulness: deletion test ----------
    print("deletion curves ...")
    eidx = rng.choice(len(yte), size=min(N_EVAL, len(yte)), replace=False)
    Xe, ye = Xte[eidx], yte[eidx]
    fill = Xe.mean(axis=0)
    shap_order = list(rank)
    auc_shap = deletion_curve(model, Xe, ye, shap_order, fill)
    rand_aucs = []
    for r in range(5):
        perm = list(np.random.default_rng(100 + r).permutation(len(FUSION_FEATS)))
        rand_aucs.append(deletion_curve(model, Xe, ye, perm, fill))
    rand_aucs = np.array(rand_aucs)
    auc_rand_mean, auc_rand_std = rand_aucs.mean(0), rand_aucs.std(0)
    abc = float(np.trapezoid(auc_rand_mean) - np.trapezoid(auc_shap)) / len(FUSION_FEATS)

    fig2, ax = plt.subplots(figsize=(6.5, 4.4))
    ks = np.arange(len(auc_shap))
    ax.plot(ks, auc_shap, "o-", color="#d62728",
            label="hapus urut |SHAP| terbesar")
    ax.plot(ks, auc_rand_mean, "s--", color="#7f7f7f", label="hapus acak (5 seed)")
    ax.fill_between(ks, auc_rand_mean - auc_rand_std, auc_rand_mean + auc_rand_std,
                    color="#7f7f7f", alpha=.25)
    ax.axhline(0.5, ls=":", color="k", lw=.8)
    ax.set_xlabel("jumlah fitur dihapus (mean-imputed)")
    ax.set_ylabel("ROC-AUC")
    ax.set_title(f"Uji faithfulness (deletion) — ABC = {abc:.3f}")
    ax.legend(); ax.grid(alpha=.3)
    fig2.tight_layout()
    fig2.savefig(os.path.join(RESULTS, "exp2_faithfulness.png"), dpi=150)

    # ---------- (c) susceptibility map ----------
    water_frac = {c: float((yte[a:b] == 1).mean()) for c, (a, b) in slices.items()}
    chip = max(water_frac, key=water_frac.get)
    print("map chip:", chip, f"(water {water_frac[chip]:.1%})")
    X, y, shape = chip_features(chip)
    prob = model.predict(X).reshape(shape)
    s2 = _read(chip, "S2Hand") / 1e4
    rgb = np.clip(np.stack([s2[3], s2[2], s2[1]], -1) * 3.2, 0, 1)
    lab = y.reshape(shape)

    fig3, axs = plt.subplots(1, 4, figsize=(16, 4.2))
    axs[0].imshow(rgb); axs[0].set_title("Sentinel-2 RGB")
    axs[1].imshow(_read(chip, "S1Hand")[0], cmap="gray", vmin=-25, vmax=0)
    axs[1].set_title("Sentinel-1 VV (dB)")
    im = axs[2].imshow(prob, cmap="RdYlBu_r", vmin=0, vmax=1)
    axs[2].set_title("Peta probabilitas kerawanan")
    plt.colorbar(im, ax=axs[2], fraction=.046)
    lab_show = np.ma.masked_where(lab < 0, lab)
    axs[3].imshow(lab_show, cmap=ListedColormap(["#f0f0f0", "#08519c"]), vmin=0, vmax=1)
    axs[3].set_title("Label referensi (air=biru)")
    for a in axs:
        a.set_xticks([]); a.set_yticks([])
    fig3.suptitle(f"Chip uji: {chip}")
    fig3.tight_layout()
    fig3.savefig(os.path.join(RESULTS, "exp2_susceptibility_map.png"), dpi=150)

    # chip-level AUC for the map chip
    m = y >= 0
    chip_auc = float(roc_auc_score(y[m], prob.reshape(-1)[m])) if (y[m] == 1).any() else None

    out = dict(
        seed=SEED, n_shap_px=int(len(Xs)), n_eval_px=int(len(Xe)),
        shap_importance={FUSION_FEATS[i]: float(mean_abs[i]) for i in rank},
        modality_share=dict(
            S1=float(mean_abs[:5].sum() / mean_abs.sum()),
            S2=float(mean_abs[5:].sum() / mean_abs.sum())),
        deletion=dict(auc_shap_order=[float(a) for a in auc_shap],
                      auc_random_mean=[float(a) for a in auc_rand_mean],
                      auc_random_std=[float(a) for a in auc_rand_std],
                      area_between_curves=abc),
        map_chip=dict(name=chip, water_frac=water_frac[chip], auc=chip_auc))
    with open(os.path.join(RESULTS, "exp2_metrics.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("saved exp2_metrics.json + 3 PNGs")


if __name__ == "__main__":
    main()
