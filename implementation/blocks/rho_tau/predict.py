"""Inference helper: load the trained multi-objective cost-predictor and pick (rho, tau_F).

Usage from another script:
    from blocks.rho_tau.predict import select_rho_tau
    rho, tau, pred_rt, pred_pk = select_rho_tau(state, objective="tradeoff",
                                                w_runtime=1.0, w_packets=1.0)

`state` keys: num_switches, num_workers, num_all_frags, num_clusters,
    num_active_frags, num_active_workers, slot_idx,
    per_worker_num_frags (optional; or pre-computed whist_* keys).

The MLP has three heads: solve runtime and ILP packet count (the primary
objective) as standardized log1p regressions, plus P(the solve hits the time
limit). The selector minimizes ``w_runtime * pred_runtime_z + w_packets *
pred_packets_z`` over the (rho, tau) grid, so the importance ratio
w_runtime:w_packets is expressed in training-set std units: 'packets'
objective == fewest packets (max aggregation gain), 'runtime' objective ==
fastest solve.

Candidates whose predicted timeout probability exceeds `timeout_thresh` are
skipped — that is the deployment-time replacement for a ground-truth
feasibility mask. If every candidate is over threshold, the least-risky one is
returned rather than failing.

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
    NUMERIC_FEATURES, WORKER_HIST_BINS, FEATURE_DIM, N_OUT, CostMLP,
    build_feature_matrix, rows_to_dataframe, derived_features, worker_hist,
    _load_entropy,
)

# Resolve artéfacts relative to the implementation root so default
# paths stay stable regardless of caller CWD.
_HERE = os.path.dirname(os.path.abspath(__file__))
_IMPL_ROOT = os.path.dirname(os.path.dirname(_HERE)) or _HERE
DEFAULT_MODEL = os.path.join(_IMPL_ROOT, "plots", "rho_tau_model.pt")
DEFAULT_FEATURES = os.path.join(_IMPL_ROOT, "plots", "rho_tau_model_features.json")


def _default_state_template(numeric_features):
    return {c: 0.0 for c in numeric_features if c not in ("rho", "tau")}


def _complete_state(state, numeric_features=None, hist_bins=None):
    """Fill a state dict with every non-(rho, tau) feature the model expects."""
    numeric_features = numeric_features or NUMERIC_FEATURES
    hist_bins = WORKER_HIST_BINS if hist_bins is None else hist_bins
    s = _default_state_template(numeric_features)
    s.update({k: v for k, v in state.items() if k in s})
    # Worker histogram: prefer pre-computed whist_* (keeps eval features
    # bit-identical to training) and fall back to per_worker_num_frags.
    pw = state.get("per_worker_num_frags")
    if any(k.startswith("whist_") for k in state):
        for i in range(hist_bins):
            s[f"whist_{i}"] = float(state.get(f"whist_{i}", 0.0))
        if "load_entropy" not in state and pw:
            s["load_entropy"] = _load_entropy(pw)
    elif pw:
        hist = worker_hist(pw)
        for i in range(hist_bins):
            s[f"whist_{i}"] = float(hist[i])
        s["load_entropy"] = _load_entropy(pw)
    else:
        for i in range(hist_bins):
            s[f"whist_{i}"] = 0.0
    return s


def load_model(model_path=DEFAULT_MODEL, features_path=DEFAULT_FEATURES,
               device="cpu"):
    """Load a checkpoint into a model_pack (ensemble-aware, back-compatible)."""
    ck = torch.load(model_path, map_location=device, weights_only=False)
    feature_stats = {k: np.array(v, dtype=np.float32)
                     for k, v in ck["feature_stats"].items()}
    numeric_features = ck.get("numeric_features", NUMERIC_FEATURES)
    hist_bins = int(ck.get("worker_hist_bins", WORKER_HIST_BINS))
    in_dim = len(numeric_features) + hist_bins
    states = ck.get("state_dicts") or [ck["state_dict"]]
    # Output width from the last Linear so 1-/2-head checkpoints still load.
    wkeys = [k for k in states[0] if k.endswith(".weight")]
    n_out = int(states[0][wkeys[-1]].shape[0])

    def _build(sd):
        m = CostMLP(in_dim=in_dim, hidden=ck.get("hidden", 128),
                    n_layers=ck.get("n_layers", 3),
                    dropout=ck.get("dropout", 0.1), n_out=n_out).to(device)
        m.load_state_dict(sd)
        m.eval()
        return m

    models = [_build(sd) for sd in states]
    report_models = [_build(sd) for sd in (ck.get("report_state_dicts") or [])]
    if os.path.exists(features_path):
        with open(features_path) as f:
            fs = json.load(f)
        rho_grid = [float(x) for x in fs["rho_grid"]]
        tau_grid = [int(x) for x in fs["tau_grid"]]
    else:
        rho_grid = [round(0.10 * i, 2) for i in range(1, 10)]
        tau_grid = list(range(6, 13))
    return {
        "models": models, "model": models[0],
        "report_models": report_models,
        "feature_stats": feature_stats,
        "numeric_features": numeric_features,
        "worker_hist_bins": hist_bins,
        "rho_grid": rho_grid, "tau_grid": tau_grid,
        "target_stats": ck.get("target_stats"),
        "n_out": n_out,
        "timeout_thresh": ck.get("timeout_thresh", 0.5),
        "censoring": ck.get("censoring"),
        "penalty_runtime": ck.get("penalty_runtime"),
    }


def _forward(model_pack, X, device="cpu", use_report=False):
    """Ensemble-averaged raw outputs, shape (n, n_out).

    use_report=True scores with the report-only ensemble instead of the
    selection ensemble (see train.py's --n_report_models). Falls back to the
    selection ensemble if no report models were trained (older checkpoints).
    """
    models = model_pack.get("models") or [model_pack["model"]]
    if use_report:
        models = model_pack.get("report_models") or models
    with torch.no_grad():
        xt = torch.tensor(X, device=device)
        outs = [m(xt).cpu().numpy() for m in models]
    return np.mean(outs, axis=0)


def predict_frame(df, model_pack, device="cpu", use_report=False):
    """Predict on a feature DataFrame; returns runtime (s), packets, P(timeout).

    use_report=True: score with the independent report ensemble (see
    _forward) instead of the selection ensemble. Use this to report a
    prediction for a candidate that was itself chosen by an argmin search
    over the selection ensemble's own output — scoring it with the same
    ensemble that picked it is biased low (winner's curse); an ensemble that
    never saw the competition isn't.
    """
    numeric_features = model_pack.get("numeric_features", NUMERIC_FEATURES)
    hist_bins = int(model_pack.get("worker_hist_bins", WORKER_HIST_BINS))
    d = df.copy()
    for c in numeric_features:
        if c not in d.columns:
            d[c] = 0.0
    for i in range(hist_bins):
        if f"whist_{i}" not in d.columns:
            d[f"whist_{i}"] = 0.0
    X, _ = build_feature_matrix(d, feature_stats=model_pack["feature_stats"],
                                numeric_features=numeric_features,
                                hist_bins=hist_bins)
    out = np.clip(_forward(model_pack, X, device=device, use_report=use_report),
                  -6.0, 6.0)  # 6 sigma

    ts = model_pack.get("target_stats") or {}
    mu_rt, sd_rt = ts.get("runtime", (0.0, 1.0))
    runtime = np.maximum(np.expm1(np.clip(out[:, 0] * sd_rt + mu_rt, -5.0, 8.0)), 0.0)
    if out.shape[1] >= 2:
        mu_pk, sd_pk = ts.get("packets", (0.0, 1.0))
        packets = np.maximum(
            np.expm1(np.clip(out[:, 1] * sd_pk + mu_pk, -5.0, 12.0)), 0.0)
    else:
        packets = np.zeros_like(runtime)
    if out.shape[1] >= 3:
        p_timeout = 1.0 / (1.0 + np.exp(-out[:, 2]))
    else:
        p_timeout = np.zeros_like(runtime)
    return {"z": out, "runtime": runtime, "packets": packets,
            "p_timeout": p_timeout}


def candidate_frame(state, model_pack):
    """Cartesian product of the (rho, tau) grid with a fixed state."""
    numeric_features = model_pack.get("numeric_features", NUMERIC_FEATURES)
    hist_bins = int(model_pack.get("worker_hist_bins", WORKER_HIST_BINS))
    base = _complete_state(state, numeric_features, hist_bins)
    rows = []
    for rho in model_pack["rho_grid"]:
        for tau in model_pack["tau_grid"]:
            row = dict(base)
            row["rho"] = float(rho)
            row["tau"] = float(tau)
            row.update(derived_features(
                rho, tau, base.get("num_switches", 0), base.get("num_workers", 0),
                base.get("num_active_frags", 0), base.get("num_active_workers", 0)))
            rows.append(row)
    return pd.DataFrame(rows)


def select_rho_tau(state, model_pack=None, *, device="cpu",
                   feasibility=None, reduction_floor=None, ref_pkts_by_env=None,
                   objective="tradeoff", w_runtime=1.0, w_packets=1.0,
                   timeout_thresh=0.5, return_info=False):
    """Pick (rho*, tau*) minimizing the weighted objective over the grid.

    score = w_runtime*z_runtime + w_packets*z_packets over standardized log1p
    outputs; single-objective modes use w=(1,0)/(0,1).

    Candidates are filtered by the model's timeout head (P(timeout) >
    timeout_thresh is skipped). `feasibility` — dict[(rho, tau)] -> 0/1 — is an
    optional *ground-truth* override, so it must only be used for oracle-style
    analysis, never as the deployment path. If every candidate is filtered out,
    the one with the lowest predicted timeout probability wins.

    The argmin itself (rho*, tau*) is always chosen from the selection
    ensemble (`model_pack["models"]`) — the largest, best-tuned estimate
    available. But once a winner is picked, its own selection-ensemble
    prediction is a biased estimate of its true cost: it won specifically
    because that ensemble happened to score it lowest among ~dozens of
    candidates (winner's curse). If the checkpoint has a report ensemble
    (train.py's --n_report_models, each trained on an independent bootstrap
    resample of the training *state groups* — a same-data/different-seed
    ensemble converges to nearly the same function and barely decorrelates
    this — and never used in the argmin), `pred_runtime`/`pred_packets` are
    instead scored by that independent ensemble at the winning (rho*, tau*):
    an unbiased estimate, since it never competed to be picked. Falls back to
    the selection ensemble's own (biased-low) number if no report ensemble
    exists.

    Returns (rho*, tau*, pred_rt_s, pred_packets), or a dict when
    return_info=True. Old 1-/2-head checkpoints degrade gracefully: no timeout
    filtering, and n_out=1 scores on runtime only.
    """
    if model_pack is None:
        model_pack = load_model(device=device)
    df = candidate_frame(state, model_pack)
    pred = predict_frame(df, model_pack, device=device)
    z, n_out = pred["z"], model_pack.get("n_out", pred["z"].shape[1])

    if n_out >= 2:
        if objective == "runtime":
            w_rt, w_pk = 1.0, 0.0
        elif objective == "packets":
            w_rt, w_pk = 0.0, 1.0
        else:  # tradeoff
            w_rt, w_pk = w_runtime, w_packets
        if w_rt == 0.0 and w_pk == 0.0:
            w_rt, w_pk = 1.0, 0.0
        score = w_rt * z[:, 0] + w_pk * z[:, 1]
    else:
        score = pred["runtime"].copy()

    blocked = np.zeros(len(df), dtype=bool)
    if n_out >= 3 and timeout_thresh is not None:
        blocked |= pred["p_timeout"] > timeout_thresh
    if feasibility is not None:
        for i, (rho, tau) in enumerate(zip(df["rho"], df["tau"])):
            if not feasibility.get((float(rho), int(tau)), 1):
                blocked[i] = True
    if blocked.all():
        # Nothing looks safe — fall back to the least-risky candidate.
        best = int(np.argmin(pred["p_timeout"] if n_out >= 3 else score))
    else:
        masked = np.where(blocked, np.inf, score)
        best = int(np.argmin(masked))

    info = {
        "rho": float(df["rho"].iloc[best]), "tau": int(df["tau"].iloc[best]),
        "pred_runtime": float(pred["runtime"][best]),
        "pred_packets": float(pred["packets"][best]),
        "p_timeout": float(pred["p_timeout"][best]),
        "n_blocked": int(blocked.sum()), "n_candidates": int(len(df)),
        "all_blocked": bool(blocked.all()),
    }
    if model_pack.get("report_models"):
        # Re-score just the winner with the independent report ensemble —
        # unbiased, since it never took part in choosing this candidate.
        report_pred = predict_frame(df.iloc[[best]], model_pack, device=device,
                                    use_report=True)
        info["pred_runtime_selection_ensemble"] = float(pred["runtime"][best])
        info["pred_packets_selection_ensemble"] = float(pred["packets"][best])
        info["pred_runtime"] = float(report_pred["runtime"][0])
        info["pred_packets"] = float(report_pred["packets"][0])
    if return_info:
        return info
    return info["rho"], info["tau"], info["pred_runtime"], info["pred_packets"]


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
    p.add_argument("--timeout_thresh", type=float, default=0.5)
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
    info = select_rho_tau(state, model_pack=model_pack, objective=args.objective,
                          w_runtime=args.w_runtime, w_packets=args.w_packets,
                          timeout_thresh=args.timeout_thresh, return_info=True)
    print(f"Selected: rho={info['rho']:.2f}  tau_F={info['tau']}  "
          f"predicted_runtime={info['pred_runtime']:.4f}s  "
          f"predicted_packets={info['pred_packets']:.2f}  "
          f"P(timeout)={info['p_timeout']:.3f}  "
          f"[{info['n_blocked']}/{info['n_candidates']} candidates filtered]  "
          f"(objective={args.objective}, w_rt={args.w_runtime}, "
          f"w_pk={args.w_packets})")
