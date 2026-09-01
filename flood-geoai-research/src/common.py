"""Shared utilities: Sen1Floods11 loading + multimodal feature extraction."""
import os
import numpy as np
import rasterio
from scipy.ndimage import uniform_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RESULTS = os.path.join(ROOT, "results")
os.makedirs(RESULTS, exist_ok=True)

# ---- feature names ----
S1_FEATS = ["S1_VV", "S1_VH", "S1_VV_minus_VH", "S1_VV_mean5", "S1_VH_mean5"]
S2_FEATS = ["S2_B2_blue", "S2_B3_green", "S2_B4_red", "S2_B8_nir",
            "S2_B11_swir1", "S2_B12_swir2", "S2_NDWI", "S2_MNDWI", "S2_NDVI"]
FUSION_FEATS = S1_FEATS + S2_FEATS


def list_chips(split_csv):
    """Return chip base names from a sel_*.csv file."""
    path = os.path.join(DATA, split_csv)
    chips = []
    with open(path) as f:
        for line in f:
            name = line.split(",")[0].strip().replace("_S1Hand.tif", "")
            if name:
                chips.append(name)
    return sorted(set(chips))


def _read(chip, kind):
    p = os.path.join(DATA, kind, f"{chip}_{kind}.tif")
    with rasterio.open(p) as src:
        return src.read().astype(np.float32)


def chip_features(chip):
    """Return (H*W, 14) feature matrix, (H*W,) labels, (H,W) shapes.
    Labels: 1 water, 0 no-water, -1 invalid."""
    s1 = _read(chip, "S1Hand")          # (2,H,W) dB
    s2 = _read(chip, "S2Hand") / 1e4    # (13,H,W) reflectance
    lab = _read(chip, "LabelHand")[0]   # (H,W)

    vv, vh = s1[0], s1[1]
    vv = np.nan_to_num(vv, nan=-50.0)
    vh = np.nan_to_num(vh, nan=-50.0)
    f_s1 = [vv, vh, vv - vh, uniform_filter(vv, 5), uniform_filter(vh, 5)]

    b2, b3, b4 = s2[1], s2[2], s2[3]
    b8, b11, b12 = s2[7], s2[11], s2[12]
    eps = 1e-6
    ndwi = (b3 - b8) / (b3 + b8 + eps)
    mndwi = (b3 - b11) / (b3 + b11 + eps)
    ndvi = (b8 - b4) / (b8 + b4 + eps)
    f_s2 = [b2, b3, b4, b8, b11, b12, ndwi, mndwi, ndvi]

    X = np.stack(f_s1 + f_s2, axis=-1).reshape(-1, len(FUSION_FEATS))
    y = lab.reshape(-1)
    return np.nan_to_num(X, nan=0.0), y, lab.shape


def sample_split(chips, n_per_class=4000, seed=0):
    """Stratified pixel sample per chip -> big X, y."""
    rng = np.random.default_rng(seed)
    Xs, ys = [], []
    for c in chips:
        X, y, _ = chip_features(c)
        for cls in (0, 1):
            idx = np.where(y == cls)[0]
            if len(idx) == 0:
                continue
            take = min(n_per_class, len(idx))
            sel = rng.choice(idx, size=take, replace=False)
            Xs.append(X[sel]); ys.append(y[sel])
    return np.concatenate(Xs), np.concatenate(ys).astype(np.int32)


def full_pixels(chips):
    """All valid pixels of chips -> X, y, plus per-chip slices."""
    Xs, ys, slices, pos = [], [], {}, 0
    for c in chips:
        X, y, _ = chip_features(c)
        m = y >= 0
        Xs.append(X[m]); ys.append(y[m])
        slices[c] = (pos, pos + int(m.sum()))
        pos += int(m.sum())
    return np.concatenate(Xs), np.concatenate(ys).astype(np.int32), slices


def feat_idx(names):
    return [FUSION_FEATS.index(n) for n in names]
