"""Experiment 1 — Multimodal fusion gain for flood mapping.

Question: does fusing Sentinel-1 SAR + Sentinel-2 optical beat each single
modality for per-pixel flood-water classification?

Design:
  - Sen1Floods11 hand-labeled chips (train sel: 60, test sel: 25).
  - LightGBM per-pixel classifier, three feature sets:
      S1-only (5 feats), S2-only (9 feats), Fusion (14 feats).
  - Train chips split 80/20 by chip for early stopping.
  - Test: ALL valid pixels of the 25 held-out chips (never seen in training).
  - Metrics: pooled ROC-AUC, F1 & IoU (water, thr=0.5), per-chip IoU mean±std
    (chips containing water only).
Outputs: results/exp1_metrics.json, results/exp1_fusion_gain.png,
         results/fusion_model.txt, results/test_cache.npz
"""
import json, os, time
import numpy as np
import lightgbm as lgb
from sklearn.metrics import roc_auc_score, f1_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import (RESULTS, S1_FEATS, S2_FEATS, FUSION_FEATS,
                    list_chips, sample_split, full_pixels, feat_idx)

SEED = 42
PARAMS = dict(objective="binary", learning_rate=0.05, num_leaves=63,
              min_data_in_leaf=50, feature_fraction=0.9, bagging_fraction=0.8,
              bagging_freq=1, seed=SEED, verbosity=-1, num_threads=8)


def iou(y_true, y_pred):
    inter = np.logical_and(y_true == 1, y_pred == 1).sum()
    union = np.logical_or(y_true == 1, y_pred == 1).sum()
    return float(inter / union) if union else float("nan")


def train_model(Xtr, ytr, Xva, yva, cols, name):
    dtr = lgb.Dataset(Xtr[:, cols], label=ytr)
    dva = lgb.Dataset(Xva[:, cols], label=yva, reference=dtr)
    t0 = time.time()
    m = lgb.train(PARAMS, dtr, num_boost_round=800, valid_sets=[dva],
                  callbacks=[lgb.early_stopping(50, verbose=False)])
    print(f"  {name}: best_iter={m.best_iteration} train_s={time.time()-t0:.1f}")
    return m


def evaluate(m, Xte, yte, cols, slices):
    p = m.predict(Xte[:, cols], num_iteration=m.best_iteration)
    yhat = (p >= 0.5).astype(np.int32)
    per_chip = []
    for c, (a, b) in slices.items():
        if (yte[a:b] == 1).sum() >= 50:          # chips with real water
            per_chip.append(iou(yte[a:b], yhat[a:b]))
    return dict(auc=float(roc_auc_score(yte, p)),
                f1=float(f1_score(yte, yhat)),
                iou_pooled=iou(yte, yhat),
                iou_chip_mean=float(np.mean(per_chip)),
                iou_chip_std=float(np.std(per_chip)),
                n_water_chips=len(per_chip))


def main():
    rng = np.random.default_rng(SEED)
    train_chips = list_chips("sel_train.csv")
    test_chips = list_chips("sel_test.csv")
    rng.shuffle(train_chips)
    n_val = max(1, len(train_chips) // 5)
    val_chips, tr_chips = train_chips[:n_val], train_chips[n_val:]
    print(f"chips: train={len(tr_chips)} val={len(val_chips)} test={len(test_chips)}")

    print("sampling train/val pixels ...")
    Xtr, ytr = sample_split(tr_chips, n_per_class=4000, seed=SEED)
    Xva, yva = sample_split(val_chips, n_per_class=4000, seed=SEED + 1)
    print(f"train px={len(ytr):,} (water {ytr.mean():.1%})  val px={len(yva):,}")

    print("loading ALL test pixels ...")
    Xte, yte, slices = full_pixels(test_chips)
    print(f"test px={len(yte):,} (water {yte.mean():.2%})")
    np.savez_compressed(os.path.join(RESULTS, "test_cache.npz"),
                        Xte=Xte.astype(np.float32), yte=yte,
                        chips=json.dumps({c: list(s) for c, s in slices.items()}))

    sets = {"S1_only": feat_idx(S1_FEATS),
            "S2_only": feat_idx(S2_FEATS),
            "Fusion": feat_idx(FUSION_FEATS)}
    metrics, models = {}, {}
    for name, cols in sets.items():
        print(f"training {name} ({len(cols)} feats) ...")
        m = train_model(Xtr, ytr, Xva, yva, cols, name)
        metrics[name] = evaluate(m, Xte, yte, cols, slices)
        metrics[name]["n_features"] = len(cols)
        models[name] = m
        print(f"  -> {metrics[name]}")

    models["Fusion"].save_model(os.path.join(RESULTS, "fusion_model.txt"))

    out = dict(seed=SEED,
               n_train_chips=len(tr_chips), n_val_chips=len(val_chips),
               n_test_chips=len(test_chips),
               n_train_px=int(len(ytr)), n_test_px=int(len(yte)),
               feature_sets={k: [FUSION_FEATS[i] for i in v] for k, v in sets.items()},
               metrics=metrics)
    with open(os.path.join(RESULTS, "exp1_metrics.json"), "w") as f:
        json.dump(out, f, indent=2)

    # ---- plot ----
    names = list(sets)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ks = ["auc", "f1", "iou_pooled"]
    w = 0.25
    x = np.arange(len(ks))
    colors = ["#8da0cb", "#66c2a5", "#fc8d62"]
    for i, n in enumerate(names):
        vals = [metrics[n][k] for k in ks]
        bars = axes[0].bar(x + (i - 1) * w, vals, w, label=n.replace("_", "-"),
                           color=colors[i])
        for b, v in zip(bars, vals):
            axes[0].text(b.get_x() + b.get_width() / 2, v + .008, f"{v:.3f}",
                         ha="center", fontsize=7.5)
    axes[0].set_xticks(x); axes[0].set_xticklabels(["ROC-AUC", "F1 (air)", "IoU (air)"])
    axes[0].set_ylim(0, 1.05); axes[0].legend(); axes[0].grid(axis="y", alpha=.3)
    axes[0].set_title("Kinerja piksel uji (25 chip tak terlihat)")

    ms = [metrics[n]["iou_chip_mean"] for n in names]
    ss = [metrics[n]["iou_chip_std"] for n in names]
    axes[1].bar(range(len(names)), ms, yerr=ss, capsize=5, color=colors)
    for i, (m_, s_) in enumerate(zip(ms, ss)):
        axes[1].text(i, m_ + s_ + .015, f"{m_:.3f}", ha="center", fontsize=8)
    axes[1].set_xticks(range(len(names)))
    axes[1].set_xticklabels([n.replace("_", "-") for n in names])
    axes[1].set_ylim(0, 1.05); axes[1].grid(axis="y", alpha=.3)
    axes[1].set_title(f"IoU rata-rata per chip ± SD (n={metrics['Fusion']['n_water_chips']})")
    fig.suptitle("Eksperimen 1 — Gain Fusi Multimodal (S1 SAR + S2 Optik), Sen1Floods11")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "exp1_fusion_gain.png"), dpi=150)
    print("saved exp1_metrics.json + exp1_fusion_gain.png")


if __name__ == "__main__":
    main()
