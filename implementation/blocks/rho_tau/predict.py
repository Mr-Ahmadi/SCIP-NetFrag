"""Inference helper: load the trained multi-objective cost-predictor and pick (rho, tau_F).

Usage from another script:
    from blocks.rho_tau.predict import select_rho_tau
    rho, tau, pred_rt, pred_pk = select_rho_tau(state, objective="tradeoff",
                                                w_runtime=1.0, w_packets=1.0)

`state` keys: num_switches, num_workers, num_all_frags, num_clusters,
    num_active_frags, num_active_workers, slot_idx,
    per_worker_num_frags (optional).

The MLP predicts BOTH objectives (solve runtime and ILP packet count, i.e.
the primary objective) as standardized log1p targets. The selector minimizes
``w_runtime * pred_runtime_z + w_packets * pred_packets_z``, so the
importance ratio w_runtime:w_packets is expressed in training-set std units:
'packets' objective == fewest packets (max aggregation gain), 'runtime'
objective == fastest solve.

T_max_1/T_max_2 and ittr are NOT model inputs: the time window is a
deterministic function of the chosen (slot_idx, tau) and ittr is a pure
repetition index, so neither adds information the model can use.
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

# Resolve artéfacts relative to the implementation root so default
# paths stay stable regardless of caller CWD.
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
    # Detect output width from the final Linear layer so old single-objective
    # checkpoints (n_out=1) still load; new checkpoints train n_out=2.
    wkeys = [k for k in ck["state_dict"] if k.endswith(".weight")]
    n_out = int(ck["state_dict"][wkeys[-1]].shape[0])
    model = CostMLP(in_dim=FEATURE_DIM, hidden=ck.get("hidden", 128),
                    n_layers=ck.get("n_layers", 3),
                    dropout=ck.get("dropout", 0.1), n_out=n_out).to(device)
    model.load_state_dict(ck["state_dict"])
    model.eval()
    if os.path.exists(features_path):
        with open(features_path) as f:
            fs = json.load(f)
        rho_grid = [float(x) for x in fs["rho_grid"]]
        tau_grid = [int(x) for x in fs["tau_grid"]]
    else:
        rho_grid = [round(0.10 * i, 2) for i in range(1, 10)]
        tau_grid = list(range(6, 13))
    return {
        "model": model, "feature_stats": feature_stats,
        "rho_grid": rho_grid, "tau_grid": tau_grid,
        "target_stats": ck.get("target_stats"),
        "penalty_runtime": ck.get("penalty_runtime", 30.0),
    }


def select_rho_tau(state, model_pack=None, *, device="cpu",
                   feasibility=None, reduction_floor=None, ref_pkts_by_env=None,
                   objective="tradeoff", w_runtime=1.0, w_packets=1.0):
    """Pick (rho*, tau*) minimizing the weighted objective over the grid.

    feasibility: dict[(rho, tau)] -> 0/1; pairs marked 0 are skipped.
    objective: 'runtime' -> w=(1,0), 'packets' -> w=(0,1),
               'tradeoff' -> w=(w_runtime, w_packets).
    The score combines the model's standardized log1p outputs directly:
        score = w_runtime * z_runtime + w_packets * z_packets
    so the importance ratio is in training-set std units (weights set as
    0/1 for the single-objective modes). Returns (rho*, tau*, pred_rt_s,
    pred_packets). For old n_out=1 checkpoints the score is pred_runtime.
    reduction_floor / ref_pkts_by_env: kept for forward compatibility.
    """
    if model_pack is None:
        model_pack = load_model(device=device)
    model = model_pack["model"]
    feature_stats = model_pack["feature_stats"]
    rho_grid = model_pack["rho_grid"]
    tau_grid = model_pack["tau_grid"]

    base = _complete_state(state)
    nw = base["num_workers"] if base["num_workers"] > 0 else 1
    rows = []
    for rho in rho_grid:
        for tau in tau_grid:
            row = dict(base)
            row["rho"] = float(rho)
            row["tau"] = float(tau)
            row["rho_x_active_frags"] = float(rho) * base["num_active_frags"]
            row["tau_x_workers"] = float(tau) * nw
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
        pred_z = model(torch.tensor(X, device=device)).cpu().numpy()
    pred_z = np.clip(pred_z, -6.0, 6.0)   # 6 sigma, plenty of headroom

    ts = model_pack.get("target_stats") or {}
    mu_rt, sd_rt = ts.get("runtime", (0.0, 1.0))
    pred_rt = np.expm1(np.clip(pred_z[:, 0] * sd_rt + mu_rt, -5.0, 8.0))
    pred_rt = np.maximum(pred_rt, 0.0)
    if pred_z.shape[1] >= 2:
        mu_pk, sd_pk = ts.get("packets", (0.0, 1.0))
        pred_pk = np.expm1(np.clip(pred_z[:, 1] * sd_pk + mu_pk, -5.0, 12.0))
        pred_pk = np.maximum(pred_pk, 0.0)
    else:
        pred_pk = np.zeros_like(pred_rt)

    if pred_z.shape[1] >= 2:
        if objective == "runtime":
            w_rt, w_pk = 1.0, 0.0
        elif objective == "packets":
            w_rt, w_pk = 0.0, 1.0
        else:  # tradeoff
            w_rt, w_pk = w_runtime, w_packets
        if w_rt == 0.0 and w_pk == 0.0:
            w_rt, w_pk = 1.0, 0.0
        score = w_rt * pred_z[:, 0] + w_pk * pred_z[:, 1]
    else:
        score = pred_rt.copy()
    if feasibility is not None:
        for i, (rho, tau) in enumerate(zip(df["rho"], df["tau"])):
            if not feasibility.get((float(rho), int(tau)), 1):
                score[i] = np.inf
    best = int(np.argmin(score))
    return (float(df["rho"].iloc[best]), int(df["tau"].iloc[best]),
            float(pred_rt[best]), float(pred_pk[best]))


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
    p.add_argument("--slot_idx", type=int, default=0)
    p.add_argument("--per_worker_num_frags", default="",
                   help='JSON dict like {"11":1,"33":1,"55":1,"77":1}')
    p.add_argument("--objective", default="tradeoff",
                   choices=["runtime", "packets", "tradeoff"])
    p.add_argument("--w_runtime", type=float, default=1.0)
    p.add_argument("--w_packets", type=float, default=1.0)
    args = p.parse_args()

    state = {
        "num_switches": args.num_switches,
        "num_workers": args.num_workers,
        "num_all_frags": args.num_all_frags,
        "num_clusters": args.num_clusters,
        "num_active_frags": args.num_active_frags,
        "num_active_workers": args.num_active_workers,
        "slot_idx": args.slot_idx,
    }
    if args.per_worker_num_frags:
        state["per_worker_num_frags"] = json.loads(args.per_worker_num_frags)

    model_pack = load_model(model_path=args.model, features_path=args.features)
    rho, tau, pred_rt, pred_pk = select_rho_tau(
        state, model_pack=model_pack, objective=args.objective,
        w_runtime=args.w_runtime, w_packets=args.w_packets)
    print(f"Selected: rho={rho:.2f}  tau_F={tau}  "
          f"predicted_runtime={pred_rt:.4f}s  predicted_packets={pred_pk:.2f}  "
          f"(objective={args.objective}, w_rt={args.w_runtime}, w_pk={args.w_packets})")
