"""
Offline training of a (rho, tau_F) selector from param_sweep data.

Censoring
---------
A `timelimit` row is NOT a failure and NOT a normal observation: the solver hit
`timeout_per_solve` and returned its best-effort incumbent. That means

  * runtime is **right-censored** — the true solve time is >= the timeout, we
    only know a lower bound;
  * packets is **fully observed** — the incumbent is the packet count the
    pipeline would actually ship for that (rho, tau) under that time budget
    (`sim/solver.py` keeps best-effort primal solutions), so it is a real label.

`--censoring` picks how those rows are used:

  drop (default)     : rows are excluded from both regressions but still train
                       the timeout head (the one thing they unambiguously say).
  censored            : runtime gets a one-sided hinge (only underprediction is
                       penalized, so the model learns ">= timeout" without
                       inventing a value), packets trains normally, and every
                       row feeds a timeout-probability head.
  penalty            : legacy behaviour — overwrite both targets with a
                       constant penalty. Kept only for comparison; it labels
                       censored rows with a runtime *below* the observed
                       timeout and a packet count *worse* than the one actually
                       achieved, i.e. it contradicts the data on both axes.

`censored` looks better-founded on paper (it lets the ~10% of rows that hit
the time limit still contribute a lower bound instead of throwing them away),
but a two-seed ablation on this dataset (`--seed 7` and `--seed 3`, everything
else equal) shows it *costs* held-out accuracy: val runtime r2_log1p
0.924/0.943 (censored) vs. 0.951/0.957 (drop), val runtime mae_s 6.49/2.66 vs.
3.45/1.97 — packets and the timeout head are roughly a wash either way (the
timeout head trains on every row's status regardless of `--censoring`, so
switching policy costs it nothing). The one-sided hinge, even at the tuned
`--w_censor 0.1`, still drags the shared trunk's runtime head upward for rows
that *did* finish, because gradients from the ~200 censored rows and the
~1800 finished rows land on the same parameters. `drop` is the default
because it wins on data, not just simplicity; pass `--censoring censored`
only if you have a reason to trade that accuracy for keeping the lower-bound
signal (e.g. the timeout region itself is under-sampled).

The model has three heads: standardized log1p runtime, standardized log1p
packets, and a timeout logit. The timeout head is what lets the selector avoid
infeasible (rho, tau) regions at inference time without peeking at ground-truth
statuses.
"""
import argparse
import json
import os
from collections import Counter

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from blocks.rho_tau.topo_features import TOPOLOGY_FEATURES


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
    # search-space size proxies: the ILP grows with selected switches x window
    "sel_switches",         # rho * num_switches (switches FlexINA may use)
    "space_log",            # log1p(sel_switches * tau * num_active_frags)
    "frags_per_worker",     # num_active_frags / num_active_workers
]
# Topology descriptors (constant per env, from the collapsed env tuple) so
# connectivity-distinct envs stay separable even where per-solve load stats
# coincide; see topo_features.py.
NUMERIC_FEATURES += TOPOLOGY_FEATURES

# Deliberately NOT features: T_max_1/T_max_2 (deterministic of slot_idx/tau)
# and ittr (pure repetition index). ittr stays as a row/grouping key for
# per-iteration regret samples but is never fed to the model.

# Per-worker histogram bins (capped for unseen topologies).
WORKER_HIST_BINS = 8

FEATURE_DIM = len(NUMERIC_FEATURES) + WORKER_HIST_BINS

# One state = one solver invocation context; every (rho, tau) cell of a state is
# a candidate for the same decision. Splits must keep a state intact, otherwise
# validation is memorization of its siblings.
STATE_COLS = ["env", "ittr", "slot_idx"]

N_OUT = 3  # [runtime_z, packets_z, timeout_logit]


def _load_entropy(per_worker_num_frags):
    counts = np.array(list(per_worker_num_frags.values()), dtype=float)
    if counts.sum() <= 0:
        return 0.0
    p = counts / counts.sum()
    p = p[p > 0]
    return float(-(p * np.log(p)).sum())


def derived_features(rho, tau, num_switches, num_workers, num_active_frags,
                     num_active_workers):
    """Cross terms shared by training rows and inference candidates."""
    nw = float(num_workers) if num_workers else 1.0
    naw = float(num_active_workers) if num_active_workers else 1.0
    naf = float(num_active_frags)
    sel = float(rho) * float(num_switches)
    return {
        "rho_x_active_frags": float(rho) * naf,
        "tau_x_workers": float(tau) * nw,
        "tau_over_frags": float(tau) / (naf + 1.0),
        "active_ratio": float(num_active_workers) / nw,
        "sel_switches": sel,
        "space_log": float(np.log1p(max(0.0, sel) * float(tau) * max(0.0, naf))),
        "frags_per_worker": naf / naw,
    }


def worker_hist(per_worker_num_frags):
    """Normalized per-worker fragment-count histogram (WORKER_HIST_BINS bins)."""
    hist = np.zeros(WORKER_HIST_BINS, dtype=float)
    counts = np.array(list((per_worker_num_frags or {}).values()), dtype=float)
    for c in counts:
        hist[int(min(WORKER_HIST_BINS - 1, max(0, c)))] += 1
    if hist.sum() > 0:
        hist /= hist.sum()
    return hist


def rows_to_dataframe(per_solve_rows):
    """Flatten per_solve rows into a DataFrame with engineered features."""
    feats = []
    for r in per_solve_rows:
        pw = r.get("per_worker_num_frags") or {}
        hist = worker_hist(pw)
        naf = r.get("num_active_frags", 0)
        naw = r.get("num_active_workers", 0)
        row = {
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
            "load_entropy": _load_entropy(pw),
            "packets": r["packets"],
            "runtime": r["runtime"],
            "status": r["status"],
        }
        row.update(derived_features(r["rho"], r["tau"], r["num_switches"],
                                    r["num_workers"], naf, naw))
        for name in TOPOLOGY_FEATURES:
            row[name] = float(r.get(name, 0.0))
        row.update({f"whist_{i}": float(hist[i])
                    for i in range(WORKER_HIST_BINS)})
        feats.append(row)
    return pd.DataFrame(feats)


def build_feature_matrix(df, feature_stats=None, fit_stats=False,
                         numeric_features=None, hist_bins=None):
    """Return (X, feature_stats). Pass feature_stats back at inference."""
    numeric_features = numeric_features or NUMERIC_FEATURES
    hist_bins = WORKER_HIST_BINS if hist_bins is None else hist_bins
    X_num = df[numeric_features].values.astype(np.float32)
    hist_cols = [f"whist_{i}" for i in range(hist_bins)]
    X_hist = df[hist_cols].values.astype(np.float32)
    if fit_stats:
        mu = X_num.mean(axis=0)
        sd = X_num.std(axis=0)
        sd[sd < 1e-8] = 1.0
        feature_stats = {"mean": mu, "std": sd}
    if feature_stats is None:
        raise ValueError("feature_stats required when fit_stats=False")
    X_num = (X_num - feature_stats["mean"]) / feature_stats["std"]
    return np.concatenate([X_num, X_hist], axis=1).astype(np.float32), feature_stats


class CostMLP(nn.Module):
    """Multi-head cost predictor.

    Outputs [runtime_z, packets_z, timeout_logit]: the first two are
    standardized log1p regressions, the third a logit for P(solve hits the time
    limit). n_out is read from the checkpoint so 1-/2-output models still load.
    """
    def __init__(self, in_dim=FEATURE_DIM, hidden=128, n_layers=3, dropout=0.1,
                 n_out=N_OUT):
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


def _targets(df, *, censoring="censored", penalty_stats=None):
    """Build targets + per-head masks.

    Returns a dict with:
      y_rt, y_pk        raw-unit targets (seconds / packets)
      m_rt, m_pk        1.0 where the row trains that regression head normally
      m_cens            1.0 where runtime is a censored lower bound (hinge only)
      y_to              1.0 where the solve hit the time limit
      meta              penalty constants (legacy mode) + row counts

    penalty_stats: reuse train-split constants for val/test under 'penalty'.
    """
    status = df["status"].values
    is_to = (status != "optimal")
    packets = df["packets"].astype(float).values
    runtime = df["runtime"].astype(float).values
    has_primal = packets > 0

    y_to = is_to.astype(np.float32)
    meta = {"n_rows": int(len(df)), "n_timelimit": int(is_to.sum()),
            "n_timelimit_with_primal": int((is_to & has_primal).sum()),
            "censoring": censoring}

    if censoring == "penalty":
        # Legacy: invent a constant label for both axes. Documented as wrong;
        # kept so the comparison can be reproduced.
        if penalty_stats is None:
            ok_rt = runtime[~is_to]
            ok_pk = packets[~is_to]
            pen_rt = 30.0 if ok_rt.size == 0 else max(
                30.0, float(np.percentile(ok_rt, 95)) + 5.0)
            pen_pk = 30.0 if ok_pk.size == 0 else max(
                1.0, float(np.percentile(ok_pk, 95)) + 5.0)
            penalty_stats = {"runtime": pen_rt, "packets": pen_pk}
        y_rt = np.where(is_to, penalty_stats["runtime"], runtime)
        y_pk = np.where(is_to, penalty_stats["packets"], packets)
        m_rt = np.ones(len(df), dtype=np.float32)
        m_pk = np.ones(len(df), dtype=np.float32)
        m_cens = np.zeros(len(df), dtype=np.float32)
        meta["penalty"] = penalty_stats
    else:
        y_rt = runtime.copy()
        y_pk = packets.copy()
        # Optimal rows: both heads train normally.
        m_rt = (~is_to).astype(np.float32)
        m_pk = ((~is_to) & has_primal).astype(np.float32)
        if censoring == "censored":
            # Censored rows: runtime is a lower bound (hinge), packets is the
            # incumbent the pipeline would actually ship -> a real label.
            m_cens = is_to.astype(np.float32)
            m_pk = np.maximum(m_pk, (is_to & has_primal).astype(np.float32))
        elif censoring == "drop":
            m_cens = np.zeros(len(df), dtype=np.float32)
        else:
            raise ValueError(f"unknown censoring policy {censoring!r}")
        penalty_stats = None

    meta["n_rt_regression"] = int(m_rt.sum())
    meta["n_rt_censored"] = int(m_cens.sum())
    meta["n_pk_regression"] = int(m_pk.sum())
    return {
        "y_rt": y_rt.astype(np.float32), "y_pk": y_pk.astype(np.float32),
        "m_rt": m_rt, "m_pk": m_pk, "m_cens": m_cens.astype(np.float32),
        "y_to": y_to, "penalty_stats": penalty_stats, "meta": meta,
    }


def _fit_target_stats(t_tr):
    """Z-score stats for log1p targets, fitted on rows that actually train.

    Censored runtimes are included in the runtime stats: they are genuine
    observations of the upper tail, just inequality-valued, and excluding them
    would shrink the scale the hinge operates in.
    """
    lrt = np.log1p(t_tr["y_rt"][(t_tr["m_rt"] + t_tr["m_cens"]) > 0])
    lpk = np.log1p(t_tr["y_pk"][t_tr["m_pk"] > 0])
    def _ms(v, fallback=(0.0, 1.0)):
        if v.size == 0:
            return fallback
        mu, sd = float(v.mean()), float(v.std())
        return mu, (sd if sd > 1e-6 else 1.0)
    return {"runtime": _ms(lrt), "packets": _ms(lpk)}


def _standardize(t, target_stats):
    """Attach standardized log1p targets to a target dict."""
    mu_rt, sd_rt = target_stats["runtime"]
    mu_pk, sd_pk = target_stats["packets"]
    t["z_rt"] = ((np.log1p(t["y_rt"]) - mu_rt) / sd_rt).astype(np.float32)
    t["z_pk"] = ((np.log1p(t["y_pk"]) - mu_pk) / sd_pk).astype(np.float32)
    return t


def _rank_loss(pred, target, mask, group_ids):
    """RankNet-style pairwise loss inside each state group of the batch.

    Selection only needs the *ordering* of candidates within one state, which a
    pure regression loss optimizes only indirectly. Pairs are formed between
    rows of the same group that both have a usable target.
    """
    valid = mask > 0
    if valid.sum() < 2:
        return pred.sum() * 0.0
    p = pred[valid]
    y = target[valid]
    g = group_ids[valid]
    same = (g[:, None] == g[None, :])
    dy = y[:, None] - y[None, :]
    pairs = same & (dy.abs() > 1e-3)
    pairs = torch.triu(pairs, diagonal=1)
    if pairs.sum() == 0:
        return pred.sum() * 0.0
    dp = (p[:, None] - p[None, :])[pairs]
    sgn = torch.sign(dy[pairs])
    # softplus(-sgn * dp): zero when the predicted order matches the observed.
    return torch.nn.functional.softplus(-sgn * dp).mean()


def train(X_tr, t_tr, g_tr, X_val, t_val, g_val, *, hidden=128, n_layers=3,
          dropout=0.1, epochs=200, lr=1e-3, weight_decay=1e-4, patience=30,
          batch_size=256, w_timeout=0.5, w_rank=0.3, w_censor=0.1,
          low_w=3.0, w_cheap=0.0, cheap_thresh=0.5,
          device="cpu", seed=0, verbose=True):
    """Mini-batch training of the 3-head MLP with censored-runtime handling.

    low_w > 0 reweights the runtime regression rows that fall at/below the
    training mean (in z-space) so the model spends capacity on the cheap-solve
    regime the selector actually operates in. That regime spans a tiny slice
    of the raw runtime axis (0.01-0.5 s vs. a median of ~2.9 s), and an
    unweighted Huber/log1p fit spends nearly all its capacity on the
    expensive tail, which is why an unweighted model reports "~0 s" for almost
    every cheap config. low_w=0 restores the old unweighted behaviour.

    w_cheap > 0 adds a flat extra weight to runtime rows whose raw runtime is
    below cheap_thresh (default 0.5 s), on top of the low_w gaussian. The
    gaussian alone peaks at the z-mean (the *median* runtime), so the extreme
    cheap corner (sub-0.05 s solves) gets ~1.5x less weight than mid-cheap
    rows and is sacrificed: predictions there are pulled toward the floor and
    clamp to exactly 0. The flat cheap boost gives that corner equal standing
    with mid-cheap rows, which is what actually moves the sub-0.05 s
    predictions off the 0.0 floor.
    """
    torch.manual_seed(seed)
    model = CostMLP(in_dim=X_tr.shape[1], hidden=hidden, n_layers=n_layers,
                    dropout=dropout, n_out=N_OUT).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
        opt, mode="min", factor=0.5, patience=8, min_lr=1e-5)
    huber = nn.HuberLoss(delta=1.0, reduction="none")
    bce = nn.BCEWithLogitsLoss(reduction="none")

    def _t(a, dtype=torch.float32):
        return torch.tensor(np.asarray(a), dtype=dtype, device=device)

    tr = {k: _t(t_tr[k]) for k in ("z_rt", "z_pk", "m_rt", "m_pk", "m_cens", "y_to")}
    va = {k: _t(t_val[k]) for k in ("z_rt", "z_pk", "m_rt", "m_pk", "m_cens", "y_to")}
    Xt, Xv = _t(X_tr), _t(X_val)
    gt, gv = _t(g_tr, torch.long), _t(g_val, torch.long)

    # Low-end runtime emphasis: weight rows below the z-mean with a gaussian
    # bump so the cheap-solve regime (where the selector picks) drives the
    # runtime head as much as the expensive tail does. w_cheap adds a flat
    # boost for the sub-cheap_thresh rows the gaussian under-serves.
    if low_w > 0 or w_cheap > 0:
        z = t_tr["z_rt"]
        w_rt = np.ones_like(z, dtype=np.float32)
        if low_w > 0:
            w_rt += low_w * np.exp(-(z ** 2) / 2.0) * (z < 0)
        if w_cheap > 0:
            w_rt += w_cheap * (t_tr["y_rt"] < cheap_thresh).astype(np.float32)
        tr["w_rt"] = _t(w_rt)

    # Class balance for the timeout head (timeouts are the minority class).
    pos = float(t_tr["y_to"].sum())
    neg = float(len(t_tr["y_to"]) - pos)
    pos_weight = torch.tensor(max(1.0, neg / max(1.0, pos)), device=device)

    def _loss(out, tg, gids):
        m_rt, m_pk, m_c = tg["m_rt"], tg["m_pk"], tg["m_cens"]
        l = out.sum() * 0.0
        if m_rt.sum() > 0:
            base = huber(out[:, 0], tg["z_rt"]) * m_rt
            wr = tg.get("w_rt")
            if wr is not None:
                base = base * wr
                l = l + base.sum() / (m_rt * wr).sum().clamp(min=1.0)
            else:
                l = l + base.sum() / m_rt.sum()
        if m_pk.sum() > 0:
            l = l + (huber(out[:, 1], tg["z_pk"]) * m_pk).sum() / m_pk.sum()
        if m_c.sum() > 0:
            # One-sided: only underpredicting a censored runtime is an error.
            hinge = torch.clamp(tg["z_rt"] - out[:, 0], min=0.0)
            l = l + w_censor * (hinge * m_c).sum() / m_c.sum()
        # Row weights upweight the minority (timeout) class only.
        wcls = 1.0 + (pos_weight.clamp(max=10.0) - 1.0) * tg["y_to"]
        l = l + w_timeout * ((bce(out[:, 2], tg["y_to"]) * wcls).sum()
                             / wcls.sum().clamp(min=1.0))
        if w_rank > 0:
            l = l + w_rank * _rank_loss(out[:, 0], tg["z_rt"], m_rt, gids)
            l = l + w_rank * _rank_loss(out[:, 1], tg["z_pk"], m_pk, gids)
        return l

    n = Xt.shape[0]
    best_val, best_state, bad = float("inf"), None, 0
    for ep in range(1, epochs + 1):
        model.train()
        perm = torch.randperm(n, device=device)
        ep_loss, nb = 0.0, 0
        for s in range(0, n, batch_size):
            idx = perm[s:s + batch_size]
            opt.zero_grad()
            out = model(Xt[idx])
            loss = _loss(out, {k: v[idx] for k, v in tr.items()}, gt[idx])
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            ep_loss += float(loss.item())
            nb += 1
        model.eval()
        with torch.no_grad():
            vout = model(Xv)
            val_loss = float(_loss(vout, va, gv).item())
            m = va["m_rt"]
            val_mae = float(((vout[:, 0] - va["z_rt"]).abs() * m).sum()
                            / m.clamp(min=1).sum()) if m.sum() > 0 else float("nan")
        sched.step(val_loss)
        if val_loss < best_val - 1e-6:
            best_val, bad = val_loss, 0
            best_state = {k: v.detach().clone()
                          for k, v in model.state_dict().items()}
        else:
            bad += 1
        if verbose and (ep % 20 == 0 or ep == 1):
            print(f"  epoch {ep:3d}  train_loss={ep_loss / max(1, nb):.4f}  "
                  f"val_loss={val_loss:.4f}  val_rt_mae_z={val_mae:.4f}  "
                  f"best_val={best_val:.4f}  bad={bad}")
        if bad >= patience:
            if verbose:
                print(f"  early stop at epoch {ep} "
                      f"(no improvement for {patience} epochs)")
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    return model, best_val


# ---------------------------------------------------------------- metrics ---

def _spearman(a, b):
    """Rank correlation without a scipy dependency (ties -> average ranks)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.size < 2:
        return float("nan")
    def _rank(v):
        order = v.argsort()
        r = np.empty(len(v), float)
        r[order] = np.arange(len(v), dtype=float)
        # average ranks over ties
        _, inv, cnt = np.unique(v, return_inverse=True, return_counts=True)
        sums = np.zeros(len(cnt))
        np.add.at(sums, inv, r)
        return (sums / cnt)[inv]
    ra, rb = _rank(a), _rank(b)
    if ra.std() < 1e-12 or rb.std() < 1e-12:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def _auc(y_true, score):
    """ROC AUC via rank statistic; nan when only one class is present."""
    y = np.asarray(y_true, float)
    s = np.asarray(score, float)
    pos, neg = (y > 0.5).sum(), (y <= 0.5).sum()
    if pos == 0 or neg == 0:
        return float("nan")
    order = s.argsort()
    ranks = np.empty(len(s), float)
    ranks[order] = np.arange(1, len(s) + 1, dtype=float)
    _, inv, cnt = np.unique(s, return_inverse=True, return_counts=True)
    sums = np.zeros(len(cnt))
    np.add.at(sums, inv, ranks)
    ranks = (sums / cnt)[inv]
    return float((ranks[y > 0.5].sum() - pos * (pos + 1) / 2) / (pos * neg))


def regression_report(model_pack, df, targets, *, device="cpu"):
    """Per-head accuracy in real units on the rows each head actually supervises."""
    from blocks.rho_tau import predict as prd
    pred = prd.predict_frame(df, model_pack, device=device)
    ts = model_pack["target_stats"]
    out = {}

    m = targets["m_rt"] > 0
    if m.sum():
        yt, yp = targets["y_rt"][m], pred["runtime"][m]
        out["runtime"] = {
            "n": int(m.sum()),
            "mae_s": float(np.abs(yp - yt).mean()),
            "medae_s": float(np.median(np.abs(yp - yt))),
            "mae_log1p": float(np.abs(np.log1p(yp) - np.log1p(yt)).mean()),
            "r2_log1p": _r2(np.log1p(yt), np.log1p(yp)),
            "spearman": _spearman(yt, yp),
        }
    mc = targets["m_cens"] > 0
    if mc.sum():
        # For censored rows the only defensible check: does the model place them
        # at or above the observed lower bound?
        out["runtime_censored"] = {
            "n": int(mc.sum()),
            "frac_at_or_above_bound": float(
                (pred["runtime"][mc] >= targets["y_rt"][mc] * 0.95).mean()),
            "median_pred_s": float(np.median(pred["runtime"][mc])),
            "median_bound_s": float(np.median(targets["y_rt"][mc])),
        }
    m = targets["m_pk"] > 0
    if m.sum():
        yt, yp = targets["y_pk"][m], pred["packets"][m]
        out["packets"] = {
            "n": int(m.sum()),
            "mae": float(np.abs(yp - yt).mean()),
            "medae": float(np.median(np.abs(yp - yt))),
            "r2": _r2(yt, yp),
            "spearman": _spearman(yt, yp),
        }
    y_to = targets["y_to"]
    if 0 < y_to.sum() < len(y_to):
        p_to = pred["p_timeout"]
        hit = (p_to > 0.5).astype(float)
        tp = float(((hit > 0.5) & (y_to > 0.5)).sum())
        out["timeout_head"] = {
            "n": int(len(y_to)), "n_timeouts": int(y_to.sum()),
            "auc": _auc(y_to, p_to),
            "accuracy": float((hit == y_to).mean()),
            "precision": float(tp / max(1.0, (hit > 0.5).sum())),
            "recall": float(tp / max(1.0, (y_to > 0.5).sum())),
        }
    # Within-state ranking is what the argmin selector consumes.
    ok = targets["m_rt"] > 0
    if ok.sum() > 1:
        gid = df.loc[ok, STATE_COLS].astype(str).agg("|".join, axis=1).values
        rhos = [_spearman(targets["y_rt"][ok][gid == g], pred["runtime"][ok][gid == g])
                for g in np.unique(gid)]
        rhos = [r for r in rhos if np.isfinite(r)]
        out["within_state_spearman_runtime"] = float(np.mean(rhos)) if rhos else None
    return out


def _r2(y, yhat):
    y, yhat = np.asarray(y, float), np.asarray(yhat, float)
    ss_res = float(((y - yhat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")


def evaluate_selector(model_pack, df_eval, *, device="cpu",
                      objective="tradeoff", w_runtime=1.0, w_packets=1.0,
                      use_oracle_feasibility=False, timeout_thresh=0.5):
    """Compare chosen (rho, tau) with the oracle, per state.

    use_oracle_feasibility=False is the honest setting: candidates are filtered
    by the model's own timeout head, exactly as at deployment. Passing True
    reveals ground-truth statuses and is only meaningful as an upper bound.

    Oracle runtime is taken over optimal rows; oracle packets over any row with
    a primal solution, since a censored incumbent is still a shippable result.
    """
    from blocks.rho_tau import predict as prd
    rows = []
    for key, g in df_eval.groupby(STATE_COLS, sort=False):
        state = _state_from_group(g)
        feas = None
        if use_oracle_feasibility:
            feas = {(float(r), int(t)): 0
                    for r in model_pack["rho_grid"] for t in model_pack["tau_grid"]}
            for r, t, s in zip(g["rho"], g["tau"], g["status"]):
                if s == "optimal":
                    feas[(float(r), int(t))] = 1
        sel = prd.select_rho_tau(
            state, model_pack=model_pack, device=device, feasibility=feas,
            objective=objective, w_runtime=w_runtime, w_packets=w_packets,
            timeout_thresh=timeout_thresh, return_info=True)
        chosen = g[(np.isclose(g["rho"], sel["rho"])) & (g["tau"] == sel["tau"])]
        if chosen.empty:
            continue
        c = chosen.iloc[0]
        ok = g[g["status"] == "optimal"]
        primal = g[g["packets"] > 0]
        if ok.empty or primal.empty:
            continue
        best_rt, worst_rt = float(ok["runtime"].min()), float(ok["runtime"].max())
        best_pk = float(primal["packets"].min())  # fewest packets = max reduction
        chosen_rt = float(c["runtime"])
        chosen_pk = float(c["packets"]) if c["packets"] > 0 else None
        rows.append({
            "state": key, "rho_star": sel["rho"], "tau_star": sel["tau"],
            "chosen_status": c["status"],
            "chosen_runtime": chosen_rt, "chosen_packets": chosen_pk,
            "best_runtime": best_rt, "worst_runtime": worst_rt,
            "best_packets": best_pk,
            "regret": chosen_rt - best_rt,
            "packet_regret": (chosen_pk - best_pk) if chosen_pk is not None else None,
            "gap_to_worst": (worst_rt - chosen_rt) / max(1e-9, worst_rt - best_rt),
            "timed_out": c["status"] != "optimal",
        })
    if not rows:
        return None
    r = pd.DataFrame(rows)
    pk = r["packet_regret"].dropna()
    return {
        "n_states": len(r),
        "oracle_feasibility": bool(use_oracle_feasibility),
        "mean_runtime": float(r["chosen_runtime"].mean()),
        "oracle_mean_runtime": float(r["best_runtime"].mean()),
        "mean_regret_s": float(r["regret"].mean()),
        "median_regret_s": float(r["regret"].median()),
        "mean_packets": float(r["chosen_packets"].dropna().mean()),
        "oracle_mean_packets": float(r["best_packets"].mean()),
        "mean_packet_regret": float(pk.mean()) if len(pk) else None,
        "frac_worst_avoided": float((r["gap_to_worst"] > 0.5).mean()),
        "frac_optimal_pick": float((r["regret"] <= 1e-9).mean()),
        "frac_timeout_pick": float(r["timed_out"].mean()),
    }


def _state_from_group(g):
    """Rebuild an inference state dict from a group of rows of one state.

    Histogram/entropy features are copied verbatim from the row instead of
    being re-derived from a synthetic uniform load, so eval features are bit-
    identical to training features.
    """
    first = g.iloc[0]
    state = {c: float(first[c]) for c in NUMERIC_FEATURES
             if c in g.columns and c not in ("rho", "tau")}
    for i in range(WORKER_HIST_BINS):
        state[f"whist_{i}"] = float(first[f"whist_{i}"])
    return state


# ------------------------------------------------------------------ split ---

def _group_split(df, val_frac, seed, exclude_env=None):
    """Stratified grouped split by state group.

    Splitting by state group keeps a state's (rho, tau) cells on one side of
    the split — otherwise validation is memorization of its siblings. On top
    of that, groups are drawn *per env*, so each environment contributes
    (roughly) its val_frac share to validation instead of a single global
    shuffle deciding it. With ~30 state groups a plain random draw routinely
    drops whole environments out of validation (or out of training), which
    silently biases both early stopping and the reported held-out accuracy
    toward whichever envs happen to land in val. Environments with a single
    state group can't be split and stay entirely in training.
    """
    d = df if exclude_env is None else df[df["env"] != exclude_env]
    rng = np.random.RandomState(seed)
    val_keys = set()
    for env, g in d.groupby("env"):
        uniq = np.array(sorted(
            g[STATE_COLS].astype(str).agg("|".join, axis=1).unique()))
        if len(uniq) <= 1:
            continue
        rng.shuffle(uniq)
        n_val = min(max(1, int(round(val_frac * len(uniq)))), len(uniq) - 1)
        val_keys.update(uniq[:n_val])
    keys = d[STATE_COLS].astype(str).agg("|".join, axis=1)
    is_val = keys.isin(val_keys)
    if is_val.sum() == 0:
        # Degenerate: every env is unsplittable. Fall back to a plain grouped
        # split so the train/val pair still exists.
        uniq = np.array(sorted(keys.unique()))
        rng.shuffle(uniq)
        n_val = max(1, int(round(val_frac * len(uniq))))
        is_val = keys.isin(set(uniq[:n_val]))
    return d[~is_val].copy(), d[is_val].copy()


def _group_ids(df):
    keys = df[STATE_COLS].astype(str).agg("|".join, axis=1)
    return pd.factorize(keys)[0].astype(np.int64)


def main():
    p = argparse.ArgumentParser(prog="blocks.rho_tau.train")
    p.add_argument("--data", default="plots/param_sweep_data.json")
    p.add_argument("--out_model", default="plots/rho_tau_model.pt")
    p.add_argument("--out_eval", default="plots/rho_tau_model_eval.json")
    p.add_argument("--out_features", default="plots/rho_tau_model_features.json")
    p.add_argument("--test_env", default=None,
                   help="Leave-one-env-out: hold out this env entirely.")
    p.add_argument("--val_frac", type=float, default=0.15,
                   help="Fraction of *state groups* held out for validation, "
                        "drawn per env so every env contributes a validation "
                        "share (stratified grouped split).")
    p.add_argument("--seed", type=int, default=5)
    p.add_argument("--epochs", type=int, default=400)
    p.add_argument("--hidden", type=int, default=256)
    p.add_argument("--n_layers", type=int, default=3)
    p.add_argument("--dropout", type=float, default=0.05)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--batch_size", type=int, default=128)
    p.add_argument("--patience", type=int, default=40)
    p.add_argument("--n_models", type=int, default=3,
                   help="Deep-ensemble size; predictions are averaged.")
    p.add_argument("--n_report_models", type=int, default=2,
                   help="Size of a second ensemble, each member trained on an "
                        "independent bootstrap resample of the training state "
                        "groups, used only to score the selector's *already-"
                        "chosen* (rho, tau) for diagnostics. Never participates "
                        "in the argmin search, so its predictions aren't "
                        "subject to the winner's-curse bias an argmin-selected "
                        "candidate's own ensemble has (see "
                        "predict.select_rho_tau). Bootstrapping matters: a "
                        "same-data/different-seed ensemble converges to "
                        "nearly the same function and barely decorrelates the "
                        "bias it exists to audit. 0 disables it and "
                        "diagnostics fall back to the main ensemble (biased "
                        "low).")
    p.add_argument("--censoring", default="drop",
                   choices=["censored", "drop", "penalty"],
                   help="How timelimit rows are labelled (see module docstring). "
                        "'drop' is the empirically-validated default.")
    p.add_argument("--w_timeout", type=float, default=0.5,
                   help="Weight of the timeout-classification head.")
    p.add_argument("--w_rank", type=float, default=0.3,
                   help="Weight of the within-state pairwise ranking loss.")
    p.add_argument("--w_censor", type=float, default=0.1,
                   help="Weight of the censored-runtime hinge. Tuned on a held-"
                        "out grouped split: raising it makes the model respect "
                        "the '>= timeout' bound but drags the shared trunk "
                        "upward and degrades runtime accuracy on solves that "
                        "did finish; 0.1 keeps both.")
    p.add_argument("--low_w", type=float, default=3.0,
                   help="Low-end runtime emphasis: how strongly to reweight "
                        "training rows at/below the runtime mean (z-space "
                        "gaussian bump) so the model spends capacity on the "
                        "cheap-solve regime the selector actually picks in. "
                        "0 disables it. Tuned on a held-out grouped split: it "
                        "roughly halves the selector's runtime regret on "
                        "held-out states (median rel. err ~0.26 vs ~1.0) at a "
                        "small cost to tail accuracy (val runtime r2_log1p "
                        "0.941 vs 0.951).")
    p.add_argument("--w_cheap", type=float, default=0.0,
                   help="Extra flat weight for runtime-regression rows with "
                        "raw runtime below --cheap_thresh, on top of the "
                        "low_w gaussian. The gaussian peaks at the z-mean "
                        "(median runtime), so the extreme cheap corner "
                        "(sub-0.05 s) is under-weighted and its predictions "
                        "clamp to exactly 0.0; this gives that corner equal "
                        "standing with mid-cheap rows. 0 disables it.")
    p.add_argument("--cheap_thresh", type=float, default=0.5,
                   help="Raw-runtime cutoff (seconds) for the --w_cheap "
                        "flat weight.")
    p.add_argument("--timeout_thresh", type=float, default=0.5,
                   help="Candidates with predicted P(timeout) above this are "
                        "skipped by the selector.")
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
    print("status distribution:", dict(Counter(r["status"] for r in rows)))
    print("env distribution:", dict(Counter(r["env"] for r in rows)))

    df = rows_to_dataframe(rows).reset_index(drop=True)

    # Splits: by state group, and (optionally) leave-one-env-out on top.
    if args.test_env:
        if (df["env"] == args.test_env).sum() == 0:
            raise SystemExit(f"No rows for test_env={args.test_env}.")
        test_df = df[df["env"] == args.test_env].copy()
        tr_df, val_df = _group_split(df, args.val_frac, args.seed,
                                     exclude_env=args.test_env)
        print(f"Leave-one-env-out: test_env={args.test_env}")
    else:
        test_df = None
        tr_df, val_df = _group_split(df, args.val_frac, args.seed)
        print(f"Grouped split on {STATE_COLS}: val_frac={args.val_frac}")
    if tr_df.empty or val_df.empty:
        raise SystemExit("Split produced an empty side; lower --val_frac.")
    print(f"  train rows={len(tr_df)}  val rows={len(val_df)}"
          + (f"  test rows={len(test_df)}" if test_df is not None else ""))
    print("  val groups per env:",
          dict(Counter(val_df["env"])))
    print("  train groups per env:",
          dict(Counter(tr_df["env"])))

    t_tr = _targets(tr_df, censoring=args.censoring)
    pen = t_tr["penalty_stats"]
    t_val = _targets(val_df, censoring=args.censoring, penalty_stats=pen)
    t_test = (_targets(test_df, censoring=args.censoring, penalty_stats=pen)
              if test_df is not None else None)
    print(f"Censoring policy '{args.censoring}': "
          f"{t_tr['meta']['n_timelimit']} timelimit train rows "
          f"({t_tr['meta']['n_timelimit_with_primal']} with a primal solution) "
          f"-> {t_tr['meta']['n_rt_regression']} runtime-regression, "
          f"{t_tr['meta']['n_rt_censored']} runtime-hinge, "
          f"{t_tr['meta']['n_pk_regression']} packet-regression rows")

    target_stats = _fit_target_stats(t_tr)
    for t in (t_tr, t_val, t_test):
        if t is not None:
            _standardize(t, target_stats)
    print(f"Target z-score stats (log1p): runtime mu/sd={target_stats['runtime']}, "
          f"packets mu/sd={target_stats['packets']}")

    X_tr, feature_stats = build_feature_matrix(tr_df, fit_stats=True)
    X_val, _ = build_feature_matrix(val_df, feature_stats=feature_stats)
    g_tr, g_val = _group_ids(tr_df), _group_ids(val_df)

    print(f"Training {args.n_models}x MLP (in_dim={X_tr.shape[1]}, "
          f"hidden={args.hidden}, layers={args.n_layers}, "
          f"batch={args.batch_size}) on {device} ...")
    models, val_losses = [], []
    for i in range(max(1, args.n_models)):
        print(f" [model {i + 1}/{max(1, args.n_models)}]")
        m, bv = train(X_tr, t_tr, g_tr, X_val, t_val, g_val,
                      hidden=args.hidden, n_layers=args.n_layers,
                      dropout=args.dropout, epochs=args.epochs, lr=args.lr,
                      patience=args.patience, batch_size=args.batch_size,
                      w_timeout=args.w_timeout, w_rank=args.w_rank,
                      w_censor=args.w_censor, low_w=args.low_w,
                      w_cheap=args.w_cheap, cheap_thresh=args.cheap_thresh,
                      device=device,
                      seed=args.seed + i)
        models.append(m)
        val_losses.append(bv)

    report_models = []
    if args.n_report_models > 0:
        # Bootstrap-resample by *state group* (not row) so each report model
        # sees a genuinely different training sample, not just a different
        # init seed on the identical data. A same-data, different-seed
        # ensemble converges to nearly the same function (empirically,
        # ensemble std in z-units was ~0.02-0.05 vs. a target scale of ~1.4)
        # and so barely decorrelates the argmin-selection noise it exists to
        # audit; resampling groups gives the report ensemble its own sampling
        # noise, closer to genuine epistemic uncertainty in sparse regions.
        print(f"Training {args.n_report_models}x report-only MLP on bootstrap "
              f"resamples (held out of selection, used to de-bias diagnostics) ...")
        boot_rng = np.random.RandomState(args.seed + 2000)
        tr_keys = tr_df[STATE_COLS].astype(str).agg("|".join, axis=1).values
        uniq_keys = np.unique(tr_keys)
        for i in range(args.n_report_models):
            print(f" [report model {i + 1}/{args.n_report_models}]")
            chosen = boot_rng.choice(uniq_keys, size=len(uniq_keys), replace=True)
            tr_boot = pd.concat([tr_df[tr_keys == k] for k in chosen],
                                ignore_index=True)
            t_tr_boot = _targets(tr_boot, censoring=args.censoring,
                                 penalty_stats=pen)
            _standardize(t_tr_boot, target_stats)
            X_tr_boot, _ = build_feature_matrix(tr_boot, feature_stats=feature_stats)
            g_tr_boot = _group_ids(tr_boot)
            m, _ = train(X_tr_boot, t_tr_boot, g_tr_boot, X_val, t_val, g_val,
                        hidden=args.hidden, n_layers=args.n_layers,
                        dropout=args.dropout, epochs=args.epochs, lr=args.lr,
                        patience=args.patience, batch_size=args.batch_size,
                        w_timeout=args.w_timeout, w_rank=args.w_rank,
                        w_censor=args.w_censor, low_w=args.low_w,
                        w_cheap=args.w_cheap, cheap_thresh=args.cheap_thresh,
                        device=device,
                        seed=args.seed + 1000 + i, verbose=False)
            report_models.append(m)

    rho_grid = [float(x) for x in sorted(df["rho"].unique())]
    tau_grid = [int(x) for x in sorted(df["tau"].unique())]
    print(f"Selector grid: rho={rho_grid}, tau={tau_grid}")

    model_pack = {
        "models": models, "model": models[0],
        "report_models": report_models,
        "feature_stats": feature_stats,
        "numeric_features": NUMERIC_FEATURES,
        "worker_hist_bins": WORKER_HIST_BINS,
        "rho_grid": rho_grid, "tau_grid": tau_grid,
        "target_stats": target_stats,
        "n_out": N_OUT,
    }

    torch.save({
        "state_dicts": [m.state_dict() for m in models],
        "state_dict": models[0].state_dict(),   # back-compat
        "report_state_dicts": [m.state_dict() for m in report_models],
        "feature_stats": {k: v.tolist() for k, v in feature_stats.items()},
        "numeric_features": NUMERIC_FEATURES,
        "worker_hist_bins": WORKER_HIST_BINS,
        "hidden": args.hidden, "n_layers": args.n_layers,
        "dropout": args.dropout, "n_out": N_OUT,
        "target_stats": target_stats,
        "censoring": args.censoring,
        "timeout_thresh": args.timeout_thresh,
        "low_w": args.low_w,
        "w_cheap": args.w_cheap,
        "cheap_thresh": args.cheap_thresh,
        "penalty_runtime": (pen or {}).get("runtime"),
        "penalty_packets": (pen or {}).get("packets"),
    }, args.out_model)
    print(f"Saved model -> {args.out_model}")

    eval_report = {
        "censoring": args.censoring,
        "low_w": args.low_w,
        "w_cheap": args.w_cheap,
        "cheap_thresh": args.cheap_thresh,
        "n_models": len(models),
        "best_val_loss": float(np.min(val_losses)),
        "val_loss_per_model": [float(v) for v in val_losses],
        "split": {"kind": "leave_one_env_out" if args.test_env else "grouped_stratified_by_env",
                  "state_cols": STATE_COLS, "val_frac": args.val_frac,
                  "train_rows": len(tr_df), "val_rows": len(val_df),
                  "test_rows": (len(test_df) if test_df is not None else 0)},
        "label_counts": {"train": t_tr["meta"], "val": t_val["meta"]},
    }

    print("\nRegression accuracy (train split):")
    eval_report["regression_train"] = regression_report(model_pack, tr_df, t_tr,
                                                        device=device)
    print(json.dumps(eval_report["regression_train"], indent=2))
    print("\nRegression accuracy (held-out val states):")
    eval_report["regression_val"] = regression_report(model_pack, val_df, t_val,
                                                      device=device)
    print(json.dumps(eval_report["regression_val"], indent=2))

    sel_kwargs = dict(device=device, objective=args.objective,
                      w_runtime=args.w_runtime, w_packets=args.w_packets,
                      timeout_thresh=args.timeout_thresh)
    for tag, frame in (("val", val_df), ("trainval", pd.concat([tr_df, val_df]))):
        s = evaluate_selector(model_pack, frame, use_oracle_feasibility=False,
                              **sel_kwargs)
        if s is not None:
            print(f"\nSelector quality on {tag} states "
                  f"(objective={args.objective}, w_rt={args.w_runtime}, "
                  f"w_pk={args.w_packets}, model-predicted feasibility):")
            for k, v in s.items():
                print(f"  {k}: {v}")
            eval_report[f"selector_{tag}"] = s

    if test_df is not None:
        eval_report["regression_test_env"] = regression_report(
            model_pack, test_df, t_test, device=device)
        s = evaluate_selector(model_pack, test_df, use_oracle_feasibility=False,
                              **sel_kwargs)
        if s is not None:
            print(f"\nSelector quality on held-out env ({args.test_env}):")
            for k, v in s.items():
                print(f"  {k}: {v}")
            eval_report["selector_test_env"] = {"test_env": args.test_env, **s}

    with open(args.out_eval, "w") as f:
        json.dump(eval_report, f, indent=2, default=float)
    print(f"\nSaved eval report -> {args.out_eval}")

    with open(args.out_features, "w") as f:
        json.dump({
            "numeric_features": NUMERIC_FEATURES,
            "worker_hist_bins": WORKER_HIST_BINS,
            "rho_grid": rho_grid, "tau_grid": tau_grid,
            "target_stats": {k: list(v) for k, v in target_stats.items()},
            "objective": args.objective,
            "w_runtime": args.w_runtime,
            "w_packets": args.w_packets,
            "timeout_thresh": args.timeout_thresh,
            "censoring": args.censoring,
            "low_w": args.low_w,
            "w_cheap": args.w_cheap,
            "cheap_thresh": args.cheap_thresh,
        }, f, indent=2)
    print(f"Saved features spec -> {args.out_features}")


if __name__ == "__main__":
    main()
