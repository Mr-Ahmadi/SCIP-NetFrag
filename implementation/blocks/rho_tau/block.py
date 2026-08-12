import sys

from blocks._imports import (
    BlockRun, LEGEND_BBOX_LINE, LEGEND_SIZE, LEGEND_NCOL_2,
    YLEN_RUNTIME, apply_plot_style, fmt_axis,
    json, new_fig, np, os, plot_grid, plot_legend, save_fig, sns,
    style, time,
)

# train/predict imported lazily to avoid pulling torch at package init time.


def _train_with_args(data, out_model, out_eval, out_features, *,
                     epochs=400, hidden=128, n_layers=3, dropout=0.1,
                     lr=1e-3, val_frac=0.15, seed=7, test_env=None,
                     device=None, objective="tradeoff",
                     w_runtime=1.0, w_packets=1.0, censoring="censored",
                     batch_size=256, patience=40, n_models=3,
                     n_report_models=4,
                     w_timeout=0.5, w_rank=0.3, w_censor=0.1,
                     low_w=3.0, timeout_thresh=0.5):
    """Invoke blocks.rho_tau.train.main() with a specific argument vector."""
    argv = ["blocks.rho_tau.train",
            "--data", str(data),
            "--out_model", str(out_model),
            "--out_eval", str(out_eval),
            "--out_features", str(out_features),
            "--epochs", str(epochs),
            "--hidden", str(hidden),
            "--n_layers", str(n_layers),
            "--dropout", str(dropout),
            "--lr", str(lr),
            "--val_frac", str(val_frac),
            "--seed", str(seed),
            "--objective", objective,
            "--w_runtime", str(w_runtime),
            "--w_packets", str(w_packets),
            "--censoring", censoring,
            "--batch_size", str(batch_size),
            "--patience", str(patience),
            "--n_models", str(n_models),
            "--n_report_models", str(n_report_models),
            "--w_timeout", str(w_timeout),
            "--w_rank", str(w_rank),
            "--w_censor", str(w_censor),
            "--low_w", str(low_w),
            "--timeout_thresh", str(timeout_thresh)]
    if test_env:
        argv += ["--test_env", test_env]
    if device:
        argv += ["--device", device]
    saved = sys.argv
    sys.argv = argv
    try:
        from blocks.rho_tau import train as trm
        trm.main()
    finally:
        sys.argv = saved


def _load_per_solve(path):
    """Read per_solve rows from run_param_sweep output.

    Returns ([], None) if the JSON is missing or has no per-solve rows.
    """
    if not os.path.exists(path):
        return [], None
    with open(path) as f:
        payload = json.load(f)
    rows = payload.get("per_solve") or []
    return rows, payload


def _selector_quality(per_solve_rows, model_pack, *, device="cpu",
                      objective="tradeoff", w_runtime=1.0, w_packets=1.0,
                      timeout_thresh=0.5, oracle_feasibility=False):
    """Evaluate the selector on every unique state in the per-solve data.

    oracle_feasibility=False is the deployment path: infeasible (rho, tau)
    pairs are ruled out by the model's own timeout head, never by ground-truth
    statuses. Passing True leaks the statuses and only serves as an upper
    bound on achievable quality.

    A pick that times out is scored with its *real* observed cost (the timeout
    wall-clock and the best-effort incumbent packet count), not discarded — the
    pipeline ships that solution, so it belongs in the regret.

    objective/weights must match the trained config (see module constants
    OBJECTIVE / W_RUNTIME / W_PACKETS in run_rho_tau_model).
    """
    if not per_solve_rows:
        return []

    # Group by observable pre-choice state. T_max_1/T_max_2 are deterministic
    # of tau; ittr stays a grouping key so each repetition is an independent
    # regret sample.
    state_cols = ["env", "ittr", "slot_idx",
                  "num_active_frags", "num_active_workers"]
    buckets = {}
    for r in per_solve_rows:
        key = tuple(r[c] for c in state_cols)
        buckets.setdefault(key, []).append(r)

    out = []
    for key, rs in buckets.items():
        # Oracle runtime over solves that finished; oracle packets over any
        # solve that produced a primal solution (a censored incumbent is still
        # a shippable result).
        ok = [r for r in rs if r["status"] == "optimal"]
        primal = [r for r in rs if r["packets"]]
        if not ok or not primal:
            continue
        best = min(ok, key=lambda r: r["runtime"])
        worst = max(ok, key=lambda r: r["runtime"])
        best_pk = min(primal, key=lambda r: r["packets"])
        worst_pk = max(primal, key=lambda r: r["packets"])

        # State from the first row of the group.
        first = rs[0]
        state = {
            "num_switches": first["num_switches"],
            "num_workers": first["num_workers"],
            "num_all_frags": first["num_all_frags"],
            "num_clusters": first["num_clusters"],
            "num_active_frags": first["num_active_frags"],
            "num_active_workers": first["num_active_workers"],
            "slot_idx": first["slot_idx"],
            "per_worker_num_frags": first.get("per_worker_num_frags") or {},
        }
        base = {"env": first["env"], "ittr": first["ittr"],
                "slot_idx": first["slot_idx"],
                "best_runtime": float(best["runtime"]),
                "worst_runtime": float(worst["runtime"]),
                "best_packets": float(best_pk["packets"]),
                "worst_packets": float(worst_pk["packets"])}
        try:
            from blocks.rho_tau import predict as prd
            feas = None
            if oracle_feasibility:
                feas = {(float(r), int(t)): 0
                        for r in model_pack["rho_grid"]
                        for t in model_pack["tau_grid"]}
                for r in rs:
                    if r["status"] == "optimal":
                        feas[(float(r["rho"]), int(r["tau"]))] = 1
            sel = prd.select_rho_tau(
                state, model_pack=model_pack, device=device, feasibility=feas,
                objective=objective, w_runtime=w_runtime, w_packets=w_packets,
                timeout_thresh=timeout_thresh, return_info=True)
        except Exception as e:
            # Selector failure — record as a regretted state.
            out.append({**base,
                        "rho_star": None, "tau_star": None,
                        "pred_runtime": None, "pred_packets": None,
                        "p_timeout": None, "chosen_status": None,
                        "chosen_runtime": None, "chosen_packets": None,
                        "regret": None, "packet_regret": None,
                        "gap_to_worst": None,
                        "error": f"{type(e).__name__}: {e}"})
            continue

        # Observed outcome of the selected (rho, tau) pair.
        chosen = next((r for r in rs
                       if abs(r["rho"] - sel["rho"]) < 1e-9
                       and r["tau"] == sel["tau"]), None)
        chosen_rt = float(chosen["runtime"]) if chosen else None
        chosen_pk = (float(chosen["packets"])
                     if chosen and chosen["packets"] else None)
        regret = (chosen_rt - best["runtime"]) if chosen_rt is not None else None
        pk_regret = (chosen_pk - best_pk["packets"]) if chosen_pk is not None else None
        denom = (worst["runtime"] - best["runtime"]) or 1e-9
        gap = ((worst["runtime"] - chosen_rt) / denom) if chosen_rt is not None else None
        out.append({**base,
                    "rho_star": float(sel["rho"]), "tau_star": int(sel["tau"]),
                    "pred_runtime": float(sel["pred_runtime"]),
                    "pred_packets": float(sel["pred_packets"]),
                    "p_timeout": float(sel["p_timeout"]),
                    "chosen_status": (chosen or {}).get("status"),
                    "chosen_runtime": chosen_rt, "chosen_packets": chosen_pk,
                    "regret": regret, "packet_regret": pk_regret,
                    "gap_to_worst": gap})
    return out


def _plot_regret_by_env(qualities, path):
    """Grouped-bar chart: mean regret per env with std errorbars."""
    envs = sorted({q["env"] for q in qualities})
    means, stds = [], []
    for e in envs:
        regrets = [q["regret"] for q in qualities
                   if q["env"] == e and q["regret"] is not None]
        means.append(float(np.mean(regrets)) if regrets else 0.0)
        stds.append(float(np.std(regrets)) if regrets else 0.0)
    s = apply_plot_style()
    cmap = sns.color_palette(style.palette)
    fig, ax = new_fig()
    x = np.arange(len(envs))
    ax.bar(x, means, yerr=stds, width=0.6, color=cmap[1],
           edgecolor="black", capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(envs, rotation=30, ha="right", fontsize=s.tick_size)
    ax.set_ylabel("regret (s)", fontsize=s.label_size)
    ax.set_title("Selector regret vs oracle (mean ± std)",
                 fontsize=s.title_size)
    plot_grid(ax, axis="y")
    fmt_axis(ax, axis="y")
    fig.tight_layout()
    save_fig(fig, path)


def _plot_pred_vs_actual(qualities, path, *, kind="runtime", log_scale=False,
                         held_out=None):
    """Scatter: predicted vs observed target for the selected (rho, tau).

    `pred_*` here is already the report-ensemble (de-biased) estimate — see
    predict.select_rho_tau — but a handful of states still land near the
    grid's cheapest corner (smallest rho/tau), where predicted values span
    several orders of magnitude down to ~0. log_scale makes that legible
    instead of piling everything up against the linear-scale origin. The
    annotation quotes the held-out regression metrics (`held_out`, from the
    eval report, over every grid cell of the validation states) — the same
    numbers the model is reported with — because R² computed over just the
    argmin picks is a pessimistically-biased subset (winner's curse).
    """
    pkey = "pred_runtime" if kind == "runtime" else "pred_packets"
    ckey = "chosen_runtime" if kind == "runtime" else "chosen_packets"
    unit = " (s)" if kind == "runtime" else ""
    pts = [q for q in qualities
           if q.get(pkey) is not None and q.get(ckey) is not None]
    if not pts:
        return
    xs = np.array([q[pkey] for q in pts], dtype=float)
    ys = np.array([q[ckey] for q in pts], dtype=float)
    s = apply_plot_style()
    cmap = sns.color_palette(style.palette)
    fig, ax = new_fig()
    envs = sorted({q["env"] for q in pts})
    for i, e in enumerate(envs):
        sel = np.array([q["env"] == e for q in pts])
        ax.scatter(xs[sel], ys[sel], s=42, alpha=0.85, color=cmap[i % len(cmap)],
                   edgecolor="none", label=e)
    # y = x reference line
    all_v = list(xs) + list(ys)
    if all_v:
        lo, hi = min(all_v), max(all_v)
        ax.plot([lo, hi], [lo, hi], ls="--", color="gray", lw=1,
                label="pred = actual")
    if log_scale:
        # symlog, not log: several predictions are genuinely ~0 (the model
        # is confident these configs are essentially free), and a hard log
        # floor would clip them all onto one artificial vertical line. symlog
        # keeps a linear region near 0 so those points stay distinguishable.
        lin_thresh = max(1e-3, min(v for v in all_v if v > 0) / 2) if all_v else 1e-3
        ax.set_xscale("symlog", linthresh=lin_thresh)
        ax.set_yscale("symlog", linthresh=lin_thresh)
    # honest accuracy annotation: held-out regression from the eval report
    # when available (same numbers the model is reported with), else computed
    # on the picks themselves
    if held_out is not None and kind in held_out:
        h = held_out[kind]
        n = int(h.get("n", "?"))
        r2 = float(h["r2_log1p"] if kind == "runtime" else h["r2"])
        rho = float(h.get("spearman", float("nan")))
        if kind == "runtime":
            mae = float(h.get("mae_s"))
            txt = (f"held-out val (n={n})\n"
                   f"R$^2$ (log) = {r2:.3f}\n"
                   f"Spearman = {rho:.3f}")
        else:
            txt = (f"held-out val (n={n})\n"
                   f"R$^2$ = {r2:.3f}\n"
                   f"Spearman = {rho:.3f}")
    else:
        if kind == "runtime":
            tx, ty = np.log1p(xs), np.log1p(ys)
            mae = float(np.abs(xs - ys).mean())
        else:
            tx, ty = xs, ys
            mae = None
        r2 = 1 - np.sum((tx - ty) ** 2) / np.sum((ty - ty.mean()) ** 2)
        rx = np.argsort(np.argsort(tx)).astype(float)
        ry = np.argsort(np.argsort(ty)).astype(float)
        rho = float(np.corrcoef(rx, ry)[0, 1])
        if mae is not None:
            txt = (f"R$^2$ (log) = {r2:.2f}\n"
                   f"Spearman = {rho:.2f}\n"
                   f"MAE = {mae:.3f}s")
        else:
            txt = (f"R$^2$ = {r2:.2f}\n"
                   f"Spearman = {rho:.2f}")
    ax.text(0.03, 0.97, txt, transform=ax.transAxes, va="top", ha="left",
            fontsize=LEGEND_SIZE, family="monospace",
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="0.75",
                      lw=0.8, alpha=0.9))
    ax.set_xlabel(f"predicted {kind}{unit}", fontsize=s.label_size)
    ax.set_ylabel(f"observed {kind}{unit}", fontsize=s.label_size)
    ax.set_title(f"Predicted vs observed {kind} at the selector's pick "
                 f"(n={len(pts)} states)", fontsize=s.title_size)
    plot_legend(ax, loc="upper center", bbox_to_anchor=LEGEND_BBOX_LINE,
                ncol=min(LEGEND_NCOL_2, len(envs) + 1),
                fontsize=LEGEND_SIZE)
    plot_grid(ax, axis="both")
    fmt_axis(ax, axis="both")
    fig.tight_layout()
    save_fig(fig, path)


def _plot_regression_accuracy(df, pred, path, *, kind="runtime", log_scale=False):
    """Scatter: predicted vs observed target over every scored row.

    `_plot_pred_vs_actual` only shows the selector's *chosen* (rho, tau) per
    state — the argmin of ~60 noisy candidates, which is systematically
    biased low (winner's curse) and only has as many points as there are
    distinct states (tens, not thousands). This plots the regressor's raw
    accuracy on every row it was ever scored against, which is the honest
    answer to "is the model accurate."
    """
    if kind == "runtime":
        mask = (df["status"] == "optimal").values
        y = df["runtime"].values[mask]
        unit = " (s)"
    else:
        mask = (df["packets"] > 0).values
        y = df["packets"].values[mask]
        unit = ""
    x = pred[kind][mask]
    if len(x) == 0:
        return
    s = apply_plot_style()
    cmap = sns.color_palette(style.palette)
    fig, ax = new_fig()
    env_arr = df["env"].values[mask]
    envs = sorted(set(env_arr))
    for i, e in enumerate(envs):
        sel = env_arr == e
        ax.scatter(x[sel], y[sel], s=14, alpha=0.5, color=cmap[i % len(cmap)],
                   edgecolor="none", label=e)
    lo = min(x.min(), y.min())
    hi = max(x.max(), y.max())
    if log_scale:
        lo = max(lo, 1e-3)
        ax.set_xscale("log")
        ax.set_yscale("log")
    ax.plot([lo, hi], [lo, hi], ls="--", color="gray", lw=1, label="pred = actual")
    ax.set_xlabel(f"predicted {kind}{unit}", fontsize=s.label_size)
    ax.set_ylabel(f"observed {kind}{unit}", fontsize=s.label_size)
    ax.set_title(f"Regression accuracy: predicted vs observed {kind} "
                 f"(all rows, n={len(x)})", fontsize=s.title_size)
    plot_legend(ax, loc="upper center", bbox_to_anchor=LEGEND_BBOX_LINE,
                ncol=min(LEGEND_NCOL_2, len(envs) + 1), fontsize=LEGEND_SIZE)
    plot_grid(ax, axis="both")
    fmt_axis(ax, axis="both")
    fig.tight_layout()
    save_fig(fig, path)


def _summarize(qualities):
    """Aggregate per-state quality rows into scalar selector metrics."""
    regrets = [q["regret"] for q in qualities if q["regret"] is not None]
    gaps = [q["gap_to_worst"] for q in qualities if q["gap_to_worst"] is not None]
    pk_regrets = [q["packet_regret"] for q in qualities
                  if q["packet_regret"] is not None]
    statuses = [q["chosen_status"] for q in qualities if q.get("chosen_status")]
    return {
        "n_states": len(qualities),
        "n_states_with_choice": sum(1 for q in qualities
                                    if q.get("chosen_runtime") is not None),
        "mean_regret_s": float(np.mean(regrets)) if regrets else None,
        "median_regret_s": float(np.median(regrets)) if regrets else None,
        "std_regret_s": float(np.std(regrets)) if regrets else None,
        "frac_optimal_pick": (float(np.mean([r <= 1e-9 for r in regrets]))
                              if regrets else None),
        "mean_gap_to_worst": float(np.mean(gaps)) if gaps else None,
        "frac_worst_avoided": (float(np.mean([g > 0.5 for g in gaps]))
                               if gaps else None),
        "mean_packet_regret": float(np.mean(pk_regrets)) if pk_regrets else None,
        "std_packet_regret": float(np.std(pk_regrets)) if pk_regrets else None,
        "frac_timeout_pick": (float(np.mean([s != "optimal" for s in statuses]))
                              if statuses else None),
    }


# Selector objective for the multi-output cost-predictor:
#   'runtime'  -> minimize predicted solve time only
#   'packets'  -> minimize predicted packet count (max aggregation gain) only
#   'tradeoff' -> minimize w_runtime*z_rt + w_packets*z_pk (z = training-set
#                 std units, so the ratio is directly interpretable)
OBJECTIVE = "tradeoff"
W_RUNTIME = 1.0
W_PACKETS = 1.0

# How `timelimit` rows are labelled: 'drop' (regressions ignore them, the
# timeout head still learns from them — empirically the best held-out runtime
# accuracy, see blocks/rho_tau/train.py docstring), 'censored' (runtime is a
# one-sided lower-bound hinge, packets is the real incumbent — theoretically
# tidier but measurably worse on this data), or 'penalty' (legacy constant
# labels — wrong on both axes, kept only for comparison).
CENSORING = "drop"
# Candidates whose predicted P(timeout) exceeds this are skipped by the selector.
TIMEOUT_THRESH = 0.5


def run_rho_tau_model():
    """Train (rho, tau_F) cost-predictor and evaluate selector quality."""
    data_path = "plots/param_sweep_data.json"
    out_model = "plots/rho_tau_model.pt"
    out_eval = "plots/rho_tau_model_eval.json"
    out_features = "plots/rho_tau_model_features.json"
    out_data = "plots/rho_tau_model_data.json"
    plot_regret = "plots/rho_tau_model_regret_by_env.pdf"
    plot_pred_vs_act = "plots/rho_tau_model_pred_vs_actual.pdf"
    plot_pred_vs_act_pk = "plots/rho_tau_model_pred_vs_actual_packets.pdf"
    plot_reg_acc = "plots/rho_tau_model_regression_accuracy.pdf"
    plot_reg_acc_pk = "plots/rho_tau_model_regression_accuracy_packets.pdf"

    epochs = 400
    hidden = 256
    n_layers = 3
    dropout = 0.05
    lr = 1e-3
    batch_size = 128
    patience = 40
    n_models = 3
    n_report_models = 4
    val_frac = 0.15
    seed = 5
    test_env = None
    device = None
    low_w = 3.0

    run = BlockRun("rho_tau_model", config={
        "data": data_path,
        "out_model": out_model,
        "out_eval": out_eval,
        "out_features": out_features,
        "epochs": epochs, "hidden": hidden, "n_layers": n_layers,
        "dropout": dropout, "lr": lr, "batch_size": batch_size,
        "patience": patience, "n_models": n_models,
        "n_report_models": n_report_models,
        "val_frac": val_frac, "seed": seed, "test_env": test_env,
        "objective": OBJECTIVE, "w_runtime": W_RUNTIME, "w_packets": W_PACKETS,
        "censoring": CENSORING, "timeout_thresh": TIMEOUT_THRESH,
        "low_w": low_w,
        "device": device or "auto",
    }, axis={"x": "topology", "y_runtime": YLEN_RUNTIME,
             "x_ticks": []})

    block_start = time.time()
    per_solve_rows, payload = _load_per_solve(data_path)
    if not per_solve_rows:
        msg = (f"No `per_solve` rows in {data_path}. Run the "
               "`param_sweep` block first — it captures the per-sub-"
               "solve state+load this block trains on.")
        print(msg)
        run.config["error"] = msg
        run.save(out_data, extra={"plot_files": [],
                                   "block_runtime_s": time.time() - block_start})
        return

    print(f"Loaded {len(per_solve_rows)} per-solve rows from {data_path}")
    envs_seen = sorted({r["env"] for r in per_solve_rows})
    n_timelimit = sum(1 for r in per_solve_rows if r["status"] != "optimal")
    run.config["envs_in_data"] = envs_seen
    run.config["n_timelimit_rows"] = n_timelimit
    print(f"  envs: {envs_seen}")
    print(f"  timelimit rows: {n_timelimit}/{len(per_solve_rows)} "
          f"(censoring policy: {CENSORING})")

    # 1. Train
    print("\n[1/3] Training cost-predictor ...")
    train_t0 = time.time()
    _train_with_args(
        data_path, out_model, out_eval, out_features,
        epochs=epochs, hidden=hidden, n_layers=n_layers,
        dropout=dropout, lr=lr, val_frac=val_frac, seed=seed,
        test_env=test_env, device=device, objective=OBJECTIVE,
        w_runtime=W_RUNTIME, w_packets=W_PACKETS, censoring=CENSORING,
        batch_size=batch_size, patience=patience, n_models=n_models,
        n_report_models=n_report_models, timeout_thresh=TIMEOUT_THRESH,
        low_w=low_w)
    train_time = time.time() - train_t0
    print(f"  training done in {train_time:.1f}s")

    # 2. Test — drive inference path on every observable state.
    print("\n[2/3] Testing selector on observed states ...")
    eval_payload = {}
    if os.path.exists(out_eval):
        with open(out_eval) as f:
            eval_payload = json.load(f)
    from blocks.rho_tau import predict as prd
    model_pack = prd.load_model(model_path=out_model,
                                features_path=out_features,
                                device=(device or "cpu"))
    sel_kwargs = dict(device=(device or "cpu"), objective=OBJECTIVE,
                      w_runtime=W_RUNTIME, w_packets=W_PACKETS,
                      timeout_thresh=TIMEOUT_THRESH)
    qualities = _selector_quality(per_solve_rows, model_pack,
                                  oracle_feasibility=False, **sel_kwargs)
    # Same states, but told which pairs really solved — an upper bound that
    # quantifies how much the timeout head still costs us.
    qualities_oracle = _selector_quality(per_solve_rows, model_pack,
                                         oracle_feasibility=True, **sel_kwargs)
    print(f"  selector evaluated on {len(qualities)} states "
          f"(of {len(per_solve_rows)} per-solve rows)")
    for q in qualities:
        run.observe(
            model="FlexINA-MLP", env=q["env"],
            x=f"ittr={q['ittr']},slot={q['slot_idx']}",
            ittr=int(q["ittr"]),
            packets=q.get("chosen_packets"), runtime=q.get("chosen_runtime"),
            construction_time_s=None,
            solve_time_s=q.get("pred_runtime"),
            status=(q.get("chosen_status")
                    or ("optimal" if q.get("chosen_runtime") is not None
                        else "missing")),
            rho_star=q.get("rho_star"), tau_star=q.get("tau_star"),
            pred_runtime=q.get("pred_runtime"),
            pred_packets=q.get("pred_packets"),
            p_timeout=q.get("p_timeout"),
            best_runtime=q.get("best_runtime"),
            worst_runtime=q.get("worst_runtime"),
            regret=q.get("regret"), gap_to_worst=q.get("gap_to_worst"),
            error=q.get("error"))

    # 3. Plots
    print("\n[3/3] Plotting ...")
    plot_files = []
    if qualities:
        _plot_regret_by_env(qualities, plot_regret)
        plot_files.append(plot_regret)
        _plot_pred_vs_actual(qualities, plot_pred_vs_act, kind="runtime",
                             log_scale=True,
                             held_out=eval_payload.get("regression_val"))
        plot_files.append(plot_pred_vs_act)
        _plot_pred_vs_actual(qualities, plot_pred_vs_act_pk, kind="packets",
                             held_out=eval_payload.get("regression_val"))
        plot_files.append(plot_pred_vs_act_pk)

    # Regression accuracy over every scored row (not just the selector's
    # picks) — the honest view of model accuracy; see _plot_regression_accuracy.
    from blocks.rho_tau import train as trm
    df_all = trm.rows_to_dataframe(per_solve_rows).reset_index(drop=True)
    pred_all = prd.predict_frame(df_all, model_pack, device=(device or "cpu"))
    _plot_regression_accuracy(df_all, pred_all, plot_reg_acc,
                              kind="runtime", log_scale=True)
    plot_files.append(plot_reg_acc)
    _plot_regression_accuracy(df_all, pred_all, plot_reg_acc_pk,
                              kind="packets", log_scale=False)
    plot_files.append(plot_reg_acc_pk)

    summary = _summarize(qualities)
    summary["training_time_s"] = float(train_time)
    summary["censoring"] = CENSORING
    summary["timeout_thresh"] = TIMEOUT_THRESH
    summary["oracle_feasibility_upper_bound"] = _summarize(qualities_oracle)
    summary["training_eval"] = eval_payload
    for k, v in summary.items():
        if k not in ("training_eval",):
            print(f"  {k}: {v}")

    run.save(out_data, extra={
        "summary": summary,
        "per_state_quality": qualities,
        "per_state_quality_oracle_feasibility": qualities_oracle,
        "plot_files": plot_files,
        "block_runtime_s": time.time() - block_start,
    })
    print(f"\nSaved block JSON -> {out_data}")
