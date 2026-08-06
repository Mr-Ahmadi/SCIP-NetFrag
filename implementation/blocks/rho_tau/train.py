"""
Offline training of a (rho, tau_F) selector from param_sweep data.
"""
import argparse
import json
import os
from collections import Counter

import numpy as np
import pandas as pd
import torch
import torch.nn as nn


NUMERIC_FEATURES = [
    "rho",
    "tau",
    "num_switches",
    "num_workers",
    "num_all_frags",
    "num_clusters",
    "num_active_frags",
    "num_active_workers",
    "slot_idx",
    # engineered cross terms for faster convergence
    "rho_x_active_frags",   # rho * num_active_frags
    "tau_x_workers",        # tau * num_workers
    "tau_over_frags",       # tau / (num_active_frags+1)
    "active_ratio",         # num_active_workers / num_workers
    "load_entropy",         # entropy of per-worker fragment distribution
]

# Deliberately NOT features: T_max_1/T_max_2 (deterministic of slot_idx/tau)
# and ittr (pure repetition index). ittr stays as a row/grouping key for
# per-iteration regret samples but is never fed to the model.

# Per-worker histogram bins (capped for unseen topologies).
WORKER_HIST_BINS = 8

FEATURE_DIM = len(NUMERIC_FEATURES) + WORKER_HIST_BINS


def _load_entropy(per_worker_num_frags):
    counts = np.array(list(per_worker_num_frags.values()), dtype=float)
    if counts.sum() <= 0:
        return 0.0
    p = counts / counts.sum()
    p = p[p > 0]
    return float(-(p * np.log(p)).sum())


def rows_to_dataframe(per_solve_rows):
    """Flatten per_solve rows into a DataFrame with engineered features."""
    feats = []
    for r in per_solve_rows:
        pw = r.get("per_worker_num_frags") or {}
        counts = np.array(list(pw.values()), dtype=float)
        hist = np.zeros(WORKER_HIST_BINS, dtype=float)
        if counts.size:
            for c in counts:
                b = int(min(WORKER_HIST_BINS - 1, c))
                hist[b] += 1
            hist /= max(1.0, hist.sum())
        naf = r.get("num_active_frags", 0)
        naw = r.get("num_active_workers", 0)
        nw = r.get("num_workers", 0) or 1
        feats.append({
            "env": r["env"],
            "rho": r["rho"],
            "tau": r["tau"],
            "num_switches": r["num_switches"],
            "num_workers": r["num_workers"],
            "num_all_frags": r["num_all_frags"],
            "num_clusters": r["num_clusters"],
            "num_active_frags": naf,
            "num_active_workers": naw,
            "slot_idx": r["slot_idx"],
            "ittr": r["ittr"],
            "rho_x_active_frags": r["rho"] * naf,
            "tau_x_workers": r["tau"] * nw,
            "tau_over_frags": r["tau"] / (naf + 1.0),
            "active_ratio": naw / nw,
            "load_entropy": _load_entropy(pw),
            "packets": r["packets"],
            "runtime": r["runtime"],
            "status": r["status"],
        })
        feats[-1].update({f"whist_{i}": float(hist[i])
                         for i in range(WORKER_HIST_BINS)})
    return pd.DataFrame(feats)


def build_feature_matrix(df, feature_stats=None, fit_stats=False):
    """Return (X, feature_stats). Pass feature_stats back at inference."""
    X_num = df[NUMERIC_FEATURES].values.astype(np.float32)
    hist_cols = [f"whist_{i}" for i in range(WORKER_HIST_BINS)]
    X_hist = df[hist_cols].values.astype(np.float32)
    if feature_stats is None:
        feature_stats = {}
    if fit_stats:
        mu = X_num.mean(axis=0)
        sd = X_num.std(axis=0)
        sd[sd < 1e-8] = 1.0
        feature_stats = {"mean": mu, "std": sd}
    mu = feature_stats["mean"]
    sd = feature_stats["std"]
    X_num = (X_num - mu) / sd
    X = np.concatenate([X_num, X_hist], axis=1).astype(np.float32)
    return X, feature_stats


class CostMLP(nn.Module):
    """Multi-output cost predictor over standardized log1p targets.

    Outputs combine as w_rt*out[:,0] + w_pk*out[:,1] — each weight is one
    training-set std of that objective. n_out=1 keeps old checkpoints loadable.
    """
    def __init__(self, in_dim=FEATURE_DIM, hidden=128, n_layers=3, dropout=0.1,
                 n_out=2):
        super().__init__()
        layers = []
        d = in_dim
        for _ in range(n_layers):
            layers += [nn.Linear(d, hidden), nn.GELU(), nn.Dropout(dropout)]
            d = hidden
        layers += [nn.Linear(d, n_out)]
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def _targets(df):
    """Targets; non-optimal rows are penalized on both axes so the model avoids
    those (rho, tau) regions regardless of which objective is weighted.

    Returns (y_runtime, y_packets, penalty_runtime, penalty_packets).
    """
    ok_rt = df.loc[df["status"] == "optimal", "runtime"].values
    if ok_rt.size == 0:
        penalty_rt = 30.0
    else:
        penalty_rt = max(30.0, float(np.percentile(ok_rt, 95)) + 5.0)
    ok_pk = df.loc[df["status"] == "optimal", "packets"].values
    if ok_pk.size == 0:
        penalty_pk = 30.0
    else:
        penalty_pk = max(1.0, float(np.percentile(ok_pk, 95)) + 5.0)
    penalties = (df["status"].values != "optimal")
    y_rt = np.where(penalties, penalty_rt, df["runtime"].astype(float).values)
    y_pk = np.where(penalties, penalty_pk, df["packets"].astype(float).values)
    return (y_rt.astype(np.float32), y_pk.astype(np.float32),
            float(penalty_rt), float(penalty_pk))


def _zscore_targets(y_tr_rt, y_tr_pk, y_val_rt, y_val_pk):
    """Z-score log1p targets on the TRAIN split; reuse stats for val/inference.

    Returns (Y_tr, Y_val, target_stats) where target_stats maps each output
    name to [mu, sigma] of its log1p space.
    """
    l_tr = np.stack([np.log1p(y_tr_rt), np.log1p(y_tr_pk)], axis=1)
    l_val = np.stack([np.log1p(y_val_rt), np.log1p(y_val_pk)], axis=1)
    mu = l_tr.mean(axis=0)
    sd = l_tr.std(axis=0)
    sd[sd < 1e-6] = 1.0
    target_stats = {"runtime": (float(mu[0]), float(sd[0])),
                    "packets": (float(mu[1]), float(sd[1]))}
    Y_tr = ((l_tr - mu) / sd).astype(np.float32)
    Y_val = ((l_val - mu) / sd).astype(np.float32)
    return Y_tr, Y_val, target_stats


def train(X_tr, y_tr, X_val, y_val, *, hidden=128, n_layers=3, dropout=0.1,
          epochs=200, lr=1e-3, weight_decay=1e-4, patience=30, device="cpu"):
    """Train the multi-output MLP on (n, 2) standardized log1p targets."""
    model = CostMLP(in_dim=X_tr.shape[1], hidden=hidden,
                    n_layers=n_layers, dropout=dropout,
                    n_out=y_tr.shape[1]).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
        opt, mode="min", factor=0.5, patience=10, min_lr=1e-5)
    loss_fn = nn.HuberLoss(delta=1.0)

    Xt = torch.tensor(X_tr, device=device)
    yt = torch.tensor(y_tr, device=device)
    Xv = torch.tensor(X_val, device=device)
    yv = torch.tensor(y_val, device=device)

    best_val, best_state, bad = float("inf"), None, 0
    for ep in range(1, epochs + 1):
        model.train()
        opt.zero_grad()
        pred = model(Xt)
        loss = loss_fn(pred, yt)
        loss.backward()
        opt.step()
        model.eval()
        with torch.no_grad():
            val_pred = model(Xv)
            val_loss = loss_fn(val_pred, yv).item()
            val_mae = (val_pred - yv).abs().mean().item()
        sched.step(val_loss)
        if val_loss < best_val - 1e-6:
            best_val = val_loss
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            bad = 0
        else:
            bad += 1
        if ep % 20 == 0 or ep == 1:
            print(f"  epoch {ep:3d}  train_loss={loss.item():.4f}  "
                  f"val_loss={val_loss:.4f}  val_mae={val_mae:.4f}  "
                  f"best_val={best_val:.4f}  bad={bad}")
        if bad >= patience:
            print(f"  early stop at epoch {ep} (no improvement for {patience} epochs)")
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    return model, best_val


def evaluate_selector(model_pack, df_eval, *, device="cpu",
                      objective="tradeoff", w_runtime=1.0, w_packets=1.0):
    """Compare chosen (rho, tau) with oracle per state.

    Mirrors blocks.rho_tau.block._selector_quality so the train-time and
    block-time selector paths stay identical. objective/weights must match.
    """
    from blocks.rho_tau import predict as prd
    # T_max_1/T_max_2 and ittr are not model inputs; ittr is a grouping key only.
    state_cols = ["env", "ittr", "slot_idx",
                  "num_active_frags", "num_active_workers"]
    groups = df_eval.groupby(state_cols, sort=False)
    rows = []
    for key, g in groups:
        state = {c: g[c].iloc[0] for c in NUMERIC_FEATURES
                 if c not in ("rho", "tau")}
        for i in range(WORKER_HIST_BINS):
            state[f"whist_{i}"] = g[f"whist_{i}"].iloc[0]
        # Uniform per-worker load reproduces the training histogram features.
        state["per_worker_num_frags"] = {
            str(i): 1 for i in range(int(g["num_active_workers"].iloc[0]))}
        # Feasible only if solved optimally for this state.
        feas = {(float(r), int(t)): 0
                for r in model_pack["rho_grid"]
                for t in model_pack["tau_grid"]}
        for r, t, s in zip(g["rho"], g["tau"], g["status"]):
            if s == "optimal":
                feas[(float(r), int(t))] = 1
        rho_star, tau_star, _, _ = prd.select_rho_tau(
            state, model_pack=model_pack, device=device, feasibility=feas,
            objective=objective, w_runtime=w_runtime, w_packets=w_packets)
        chosen = g[(g["rho"] == rho_star) & (g["tau"] == tau_star)]
        if chosen.empty or chosen["status"].iloc[0] != "optimal":
            continue
        chosen_rt = float(chosen["runtime"].iloc[0])
        chosen_pk = float(chosen["packets"].iloc[0])
        ok = g[g["status"] == "optimal"]
        if ok.empty:
            continue
        best_rt = float(ok["runtime"].min())
        worst_rt = float(ok["runtime"].max())
        best_pk = float(ok["packets"].min())  # fewest packets = max reduction
        rows.append({
            "state": key,
            "rho_star": rho_star, "tau_star": tau_star,
            "chosen_runtime": chosen_rt,
            "best_runtime": best_rt, "worst_runtime": worst_rt,
            "chosen_packets": chosen_pk, "best_packets": best_pk,
            "regret": chosen_rt - best_rt,
            "packet_regret": chosen_pk - best_pk,
            "gap_to_worst": (worst_rt - chosen_rt) / max(1e-9, worst_rt - best_rt),
        })
    if not rows:
        return None
    r = pd.DataFrame(rows)
    return {
        "n_states": len(r),
        "mean_runtime": float(r["chosen_runtime"].mean()),
        "oracle_mean_runtime": float(r["best_runtime"].mean()),
        "mean_regret_s": float(r["regret"].mean()),
        "mean_packets": float(r["chosen_packets"].mean()),
        "oracle_mean_packets": float(r["best_packets"].mean()),
        "mean_packet_regret": float(r["packet_regret"].mean()),
        "frac_worst_avoided": float((r["gap_to_worst"] > 0.5).mean()),
    }


def main():
    p = argparse.ArgumentParser(prog="blocks.rho_tau.train")
    p.add_argument("--data", default="plots/param_sweep_data.json")
    p.add_argument("--out_model", default="plots/rho_tau_model.pt")
    p.add_argument("--out_eval", default="plots/rho_tau_model_eval.json")
    p.add_argument("--out_features", default="plots/rho_tau_model_features.json")
    p.add_argument("--test_env", default=None,
                   help="Leave-one-env-out: hold out this env entirely.")
    p.add_argument("--val_frac", type=float, default=0.15,
                   help="If test_env is None, random val split fraction.")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--epochs", type=int, default=200)
    p.add_argument("--hidden", type=int, default=128)
    p.add_argument("--n_layers", type=int, default=3)
    p.add_argument("--dropout", type=float, default=0.1)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--objective", default="tradeoff",
                   choices=["runtime", "packets", "tradeoff"],
                   help="Selector objective: runtime / packets / tradeoff.")
    p.add_argument("--w_runtime", type=float, default=1.0,
                   help="Importance of runtime in 'tradeoff' (z-score units).")
    p.add_argument("--w_packets", type=float, default=1.0,
                   help="Importance of packets in 'tradeoff' (z-score units).")
    p.add_argument("--device", default=None)
    args = p.parse_args()

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    with open(args.data) as f:
        data = json.load(f)
    rows = data.get("per_solve") or []
    if not rows:
        raise SystemExit(f"No `per_solve` rows in {args.data}. Re-run param_sweep"
                         " with the updated main.py (it captures per-sub-solve"
                         " state + load).")
    print(f"Loaded {len(rows)} per-solve rows from {args.data}")
    print("status distribution:",
          dict(Counter(r["status"] for r in rows)))
    print("env distribution:",
          dict(Counter(r["env"] for r in rows)))

    df = rows_to_dataframe(rows)
    y_rt, y_pk, penalty_rt, penalty_pk = _targets(df)
    print(f"Penalty runtime for non-optimal solves: {penalty_rt:.2f}s "
          f"(rows penalized: {(df['status']!='optimal').sum()})")
    print(f"Penalty packets for non-optimal solves: {penalty_pk:.2f} "
          f"(same {int((df['status']!='optimal').sum())} rows)")

    if args.test_env:
        test_env = args.test_env
        train_df = df[df["env"] != test_env].copy()
        test_df = df[df["env"] == test_env].copy()
        if train_df.empty or test_df.empty:
            raise SystemExit(f"Leave-one-env-out split failed: need rows for "
                             f"both env != {test_env} and env == {test_env}.")
        val_df = train_df.sample(frac=args.val_frac, random_state=args.seed)
        tr_df = train_df.drop(val_df.index)
        print(f"Leave-one-env-out: test_env={test_env}")
    else:
        test_env = None
        val_df = df.sample(frac=args.val_frac, random_state=args.seed)
        tr_df = df.drop(val_df.index)
        test_df = None
        print(f"Random split: val_frac={args.val_frac}")
    print(f"  train rows={len(tr_df)}  val rows={len(val_df)}"
          + (f"  test rows={len(test_df)}" if test_df is not None else ""))

    X_tr_raw, feature_stats = build_feature_matrix(tr_df, fit_stats=True)
    X_val_raw, _ = build_feature_matrix(val_df, feature_stats=feature_stats)
    y_tr, y_val, target_stats = _zscore_targets(
        y_rt[tr_df.index.values], y_pk[tr_df.index.values],
        y_rt[val_df.index.values], y_pk[val_df.index.values])
    print(f"Target z-score stats (log1p): runtime mu/sd="
          f"{target_stats['runtime']}, packets mu/sd={target_stats['packets']}")

    print(f"Training MLP (in_dim={X_tr_raw.shape[1]}, hidden={args.hidden}, "
          f"layers={args.n_layers}) on {device} ...")
    model, best_val = train(
        X_tr_raw, y_tr, X_val_raw, y_val,
        hidden=args.hidden, n_layers=args.n_layers, dropout=args.dropout,
        epochs=args.epochs, lr=args.lr, device=device)

    torch.save({
        "state_dict": model.state_dict(),
        "feature_stats": {k: v.tolist() for k, v in feature_stats.items()},
        "numeric_features": NUMERIC_FEATURES,
        "worker_hist_bins": WORKER_HIST_BINS,
        "hidden": args.hidden, "n_layers": args.n_layers,
        "dropout": args.dropout,
        "n_out": y_tr.shape[1],
        "target_stats": target_stats,
        "penalty_runtime": penalty_rt,
        "penalty_packets": penalty_pk,
    }, args.out_model)
    print(f"Saved model -> {args.out_model}")

    rho_grid = sorted(df["rho"].unique())
    tau_grid = sorted(df["tau"].unique())
    rho_grid = [float(x) for x in rho_grid]
    tau_grid = [int(x) for x in tau_grid]
    print(f"Selector grid: rho={rho_grid}, tau={tau_grid}")

    model_pack = {
        "model": model,
        "feature_stats": feature_stats,
        "rho_grid": rho_grid,
        "tau_grid": tau_grid,
    }

    eval_report = {"best_val_loss_log1p": best_val,
                   "val_mae_log1p": float(
                       (model(torch.tensor(X_val_raw, device=device))
                        - torch.tensor(y_val, device=device)).abs().mean().detach())}

    eval_on = pd.concat([tr_df, val_df])
    sel_tr = evaluate_selector(model_pack, eval_on, device=device,
                               objective=args.objective,
                               w_runtime=args.w_runtime,
                               w_packets=args.w_packets)
    if sel_tr is not None:
        print(f"\nSelector quality on train+val states "
              f"(objective={args.objective}, w_rt={args.w_runtime}, "
              f"w_pk={args.w_packets}):")
        for k, v in sel_tr.items():
            print(f"  {k}: {v}")
        eval_report["selector_trainval"] = sel_tr

    if test_df is not None:
        sel_te = evaluate_selector(model_pack, test_df, device=device,
                                   objective=args.objective,
                                   w_runtime=args.w_runtime,
                                   w_packets=args.w_packets)
        if sel_te is not None:
            print(f"\nSelector quality on held-out env ({test_env}):")
            for k, v in sel_te.items():
                print(f"  {k}: {v}")
            eval_report["selector_test_env"] = {"test_env": test_env, **sel_te}

    with open(args.out_eval, "w") as f:
        json.dump(eval_report, f, indent=2)
    print(f"\nSaved eval report -> {args.out_eval}")

    with open(args.out_features, "w") as f:
        json.dump({
            "numeric_features": NUMERIC_FEATURES,
            "worker_hist_bins": WORKER_HIST_BINS,
            "rho_grid": [float(x) for x in rho_grid],
            "tau_grid": [int(x) for x in tau_grid],
            "target_stats": {k: list(v) for k, v in target_stats.items()},
            "objective": args.objective,
            "w_runtime": args.w_runtime,
            "w_packets": args.w_packets,
        }, f, indent=2)
    print(f"Saved features spec -> {args.out_features}")


if __name__ == "__main__":
    main()
