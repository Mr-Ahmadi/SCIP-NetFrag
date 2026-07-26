"""
Inference helper: load the trained cost-predictor and pick (rho, tau_F)
for a given observable environment state.

Usage from another script:
    from blocks.rho_tau.predict import select_rho_tau
    rho, tau, runtime_pred = select_rho_tau(state)

where `state` is a dict with at least:
    num_switches, num_workers, num_all_frags, num_clusters,
    num_active_frags, num_active_workers, T_max_1, T_max_2,
    slot_idx, ittr, per_worker_num_frags

`per_worker_num_frags` may be omitted — it defaults to empty (uniform hist).
"""
import json
import os

import numpy as np
import pandas as pd
import torch

from blocks.rho_tau.train import (
    NUMERIC_FEATURES, WORKER_HIST_BINS, FEATURE_DIM, CostMLP,
    build_feature_matrix, rows_to_dataframe, _load_entropy,
)

# Resolve artéfacts relative to the implementation root (two levels up
# from this file), so the default model/features paths stay stable
# regardless of the caller's CWD.  Falls back to the package dir for
# legacy callers that placed the .pt next to the source.
_HERE = os.path.dirname(os.path.abspath(__file__))
_IMPL_ROOT = os.path.dirname(os.path.dirname(_HERE)) or _HERE
DEFAULT_MODEL = os.path.join(_IMPL_ROOT, "plots", "rho_tau_model.pt")
DEFAULT_FEATURES = os.path.join(_IMPL_ROOT, "plots", "rho_tau_model_features.json")


def _default_state_template():
    return {c: 0.0 for c in NUMERIC_FEATURES if c not in ("rho", "tau")}


def _complete_state(state):
    s = _default_state_template()
    s.update({k: v for k, v in state.items() if k in s or k.startswith("whist_")})
    # Build worker-histogram features from per_worker_num_frags if provided.
    pw = state.get("per_worker_num_frags")
    if pw:
        counts = np.array(list(pw.values()), dtype=float)
        hist = np.zeros(WORKER_HIST_BINS, dtype=float)
        for c in counts:
            hist[min(WORKER_HIST_BINS - 1, int(c))] += 1
        if hist.sum() > 0:
            hist /= hist.sum()
        for i in range(WORKER_HIST_BINS):
            s[f"whist_{i}"] = float(hist[i])
    # Derived cross-features (kept in sync with rows_to_dataframe).
    naf = float(state.get("num_active_frags", s.get("num_active_frags", 0)) or 0)
    naw = float(state.get("num_active_workers", s.get("num_active_workers", 0)) or 0)
    nw = float(state.get("num_workers", s.get("num_workers", 0)) or 1)
    nw = nw if nw > 0 else 1
    s["rho_x_active_frags"] = 0.0  # filled per-candidate
    s["tau_x_workers"] = 0.0       # filled per-candidate
    s["tau_over_frags"] = 0.0     # filled per-candidate
    s["active_ratio"] = naw / nw
    s["load_entropy"] = _load_entropy(pw) if pw else 0.0
    return s


def load_model(model_path=DEFAULT_MODEL, features_path=DEFAULT_FEATURES,
               device="cpu"):
    ck = torch.load(model_path, map_location=device, weights_only=False)
    feature_stats = {k: np.array(v, dtype=np.float32)
                     for k, v in ck["feature_stats"].items()}
    model = CostMLP(in_dim=FEATURE_DIM, hidden=ck.get("hidden", 128),
                    n_layers=ck.get("n_layers", 3),
                    dropout=ck.get("dropout", 0.1)).to(device)
    model.load_state_dict(ck["state_dict"])
    model.eval()
    if os.path.exists(features_path):
        with open(features_path) as f:
            fs = json.load(f)
        rho_grid = [float(x) for x in fs["rho_grid"]]
        tau_grid = [int(x) for x in fs["tau_grid"]]
    else:
        rho_grid = [round(0.10 * i, 2) for i in range(1, 10)]
        tau_grid = list(range(6, 15))
    return {
        "model": model, "feature_stats": feature_stats,
        "rho_grid": rho_grid, "tau_grid": tau_grid,
        "penalty_runtime": ck.get("penalty_runtime", 30.0),
    }


def select_rho_tau(state, model_pack=None, *, device="cpu",
                   feasibility=None, reduction_floor=None, ref_pkts_by_env=None):
    """Pick (rho*, tau*) minimizing predicted runtime for `state`.

    `state`: dict of observable fields (see module docstring).

    Optional:
      feasibility: dict[(rho, tau)] -> 0/1. Pairs marked 0 are skipped
        (set to +inf cost). Pass None to allow all pairs.
      reduction_floor: float in [0,1]. If given, require the *predicted*
        packet reduction (1 - pred_packets/ref) to be >= this floor — but
        the saved model only predicts runtime, so this is ignored unless a
        packets head is added later. Kept for forward compatibility.
      ref_pkts_by_env: kept for forward compatibility (unused here).
    """
    if model_pack is None:
        model_pack = load_model(device=device)
    model = model_pack["model"]
    feature_stats = model_pack["feature_stats"]
    rho_grid = model_pack["rho_grid"]
    tau_grid = model_pack["tau_grid"]

    base = _complete_state(state)
    rows = []
    for rho in rho_grid:
        for tau in tau_grid:
            row = dict(base)
            row["rho"] = float(rho)
            row["tau"] = float(tau)
            row["rho_x_active_frags"] = float(rho) * base["num_active_frags"]
            row["tau_x_workers"] = float(tau) * base["num_workers"]
            row["tau_over_frags"] = float(tau) / (base["num_active_frags"] + 1.0)
            rows.append(row)
    df = pd.DataFrame(rows)
    for c in NUMERIC_FEATURES:
        if c not in df.columns:
            df[c] = 0.0
    for i in range(WORKER_HIST_BINS):
        if f"whist_{i}" not in df.columns:
            df[f"whist_{i}"] = 0.0
    X, _ = build_feature_matrix(df, feature_stats=feature_stats)
    with torch.no_grad():
        Xt = torch.tensor(X, device=device)
        # model predicts log1p(runtime); undo that.
        # Clip raw output to a sane log range so OOD inputs (unseen
        # topologies) can't produce exp() overflow / inf predictions.
        pred_log = model(Xt).cpu().numpy()
    pred_log = np.clip(pred_log, -5.0, 5.0)   # expm1(5) \u2248 147s, plenty of headroom
    pred_rt = np.expm1(pred_log)
    pred_rt = np.maximum(pred_rt, 0.0)        # runtime is non-negative
    if feasibility is not None:
        for i, (rho, tau) in enumerate(zip(df["rho"], df["tau"])):
            if not feasibility.get((float(rho), int(tau)), 1):
                pred_rt[i] = np.inf
    best = int(np.argmin(pred_rt))
    return (float(df["rho"].iloc[best]), int(df["tau"].iloc[best]),
            float(pred_rt[best]))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(prog="blocks.rho_tau.predict")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--features", default=DEFAULT_FEATURES)
    p.add_argument("--num_switches", type=float, default=5)
    p.add_argument("--num_workers", type=float, default=4)
    p.add_argument("--num_all_frags", type=float, default=4)
    p.add_argument("--num_clusters", type=float, default=1)
    p.add_argument("--num_active_frags", type=float, default=4)
    p.add_argument("--num_active_workers", type=float, default=4)
    p.add_argument("--T_max_1", type=float, default=0)
    p.add_argument("--T_max_2", type=float, default=8)
    p.add_argument("--slot_idx", type=int, default=0)
    p.add_argument("--ittr", type=int, default=0)
    p.add_argument("--per_worker_num_frags", default="",
                   help='JSON dict like {"11":1,"33":1,"55":1,"77":1}')
    args = p.parse_args()

    state = {
        "num_switches": args.num_switches,
        "num_workers": args.num_workers,
        "num_all_frags": args.num_all_frags,
        "num_clusters": args.num_clusters,
        "num_active_frags": args.num_active_frags,
        "num_active_workers": args.num_active_workers,
        "T_max_1": args.T_max_1,
        "T_max_2": args.T_max_2,
        "slot_idx": args.slot_idx,
        "ittr": args.ittr,
    }
    if args.per_worker_num_frags:
        state["per_worker_num_frags"] = json.loads(args.per_worker_num_frags)

    rho, tau, rt = select_rho_tau(state)
    print(f"Selected: rho={rho:.2f}  tau_F={tau}  predicted_runtime={rt:.4f}s")
