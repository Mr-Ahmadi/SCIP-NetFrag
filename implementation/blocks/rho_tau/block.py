import sys

from blocks._imports import (
    BlockRun, LEGEND_BBOX_LINE, LEGEND_SIZE, LEGEND_NCOL_2,
    YLEN_RUNTIME, apply_plot_style, fmt_axis,
    json, new_fig, np, os, plot_grid, plot_legend, save_fig, sns,
    style, time,
)

# train/predict imported lazily to avoid pulling torch at package init time.


def _train_with_args(data, out_model, out_eval, out_features, *,
                     epochs=200, hidden=128, n_layers=3, dropout=0.1,
                     lr=1e-3, val_frac=0.15, seed=7, test_env=None,
                     device=None, objective="tradeoff",
                     w_runtime=1.0, w_packets=1.0):
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
            "--w_packets", str(w_packets)]
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
                      objective="tradeoff", w_runtime=1.0, w_packets=1.0):
    """Evaluate selector on every unique state in per-solve data.

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
        # Observed best/worst runtime and packets for optimal solves (oracle).
        ok = [r for r in rs if r["status"] == "optimal"]
        if not ok:
            continue
        best = min(ok, key=lambda r: r["runtime"])
        worst = max(ok, key=lambda r: r["runtime"])
        best_pk = min(ok, key=lambda r: r["packets"])
        worst_pk = max(ok, key=lambda r: r["packets"])

        # State from the first row of the group.
        first = rs[0]
        state = {
            "env": first["env"],
            "num_switches": first["num_switches"],
            "num_workers": first["num_workers"],
            "num_all_frags": first["num_all_frags"],
            "num_clusters": first["num_clusters"],
            "num_active_frags": first["num_active_frags"],
            "num_active_workers": first["num_active_workers"],
            "slot_idx": first["slot_idx"],
            "per_worker_num_frags": first.get("per_worker_num_frags") or {},
        }
        try:
            from blocks.rho_tau import predict as prd
            # Mark every grid pair; a pair is feasible only if it solved optimally.
            feas = {(float(r), int(t)): 0
                    for r in model_pack["rho_grid"]
                    for t in model_pack["tau_grid"]}
            for r in rs:
                if r["status"] == "optimal":
                    feas[(float(r["rho"]), int(r["tau"]))] = 1
            rho_star, tau_star, pred_rt, pred_pk = prd.select_rho_tau(
                state, model_pack=model_pack, device=device, feasibility=feas,
                objective=objective, w_runtime=w_runtime, w_packets=w_packets)
        except Exception as e:
            # Selector failure — record as a regretted state.
            out.append({
                "env": first["env"], "ittr": first["ittr"],
                "slot_idx": first["slot_idx"],
                "rho_star": None, "tau_star": None,
                "pred_runtime": None, "pred_packets": None,
                "best_runtime": float(best["runtime"]),
                "worst_runtime": float(worst["runtime"]),
                "best_packets": float(best_pk["packets"]),
                "worst_packets": float(worst_pk["packets"]),
                "chosen_runtime": None, "chosen_packets": None,
                "regret": None, "packet_regret": None, "gap_to_worst": None,
                "error": f"{type(e).__name__}: {e}",
            })
            continue

        # Actual runtime for the selected (rho, tau) pair.
        chosen = next((r for r in rs
                       if abs(r["rho"] - rho_star) < 1e-9
                       and r["tau"] == tau_star), None)
        chosen_rt = float(chosen["runtime"]) if chosen and chosen["status"] == "optimal" else None
        chosen_pk = float(chosen["packets"]) if chosen and chosen["status"] == "optimal" else None
        regret = (chosen_rt - best["runtime"]) if chosen_rt is not None else None
        pk_regret = (chosen_pk - best_pk["packets"]) if chosen_pk is not None else None
        denom = (worst["runtime"] - best["runtime"]) or 1e-9
        gap = ((worst["runtime"] - chosen_rt) / denom) if chosen_rt is not None else None
        out.append({
            "env": first["env"], "ittr": first["ittr"],
            "slot_idx": first["slot_idx"],
            "rho_star": float(rho_star), "tau_star": int(tau_star),
            "pred_runtime": float(pred_rt),
            "pred_packets": float(pred_pk),
            "best_runtime": float(best["runtime"]),
            "worst_runtime": float(worst["runtime"]),
            "best_packets": float(best_pk["packets"]),
            "worst_packets": float(worst_pk["packets"]),
            "chosen_runtime": chosen_rt,
            "chosen_packets": chosen_pk,
            "regret": regret, "packet_regret": pk_regret,
            "gap_to_worst": gap,
        })
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
    ax.set_title("Selector regret vs oracle (mean \u00b1 std)",
                 fontsize=s.title_size)
    plot_grid(ax, axis="y")
    fmt_axis(ax, axis="y")
    fig.tight_layout()
    save_fig(fig, path)


def _plot_pred_vs_actual(qualities, path):
    """Scatter: predicted vs actual runtime for the selected (rho, tau)."""
    pts = [q for q in qualities
           if q["pred_runtime"] is not None and q["chosen_runtime"] is not None]
    if not pts:
        return
    s = apply_plot_style()
    cmap = sns.color_palette(style.palette)
    fig, ax = new_fig()
    envs = sorted({q["env"] for q in pts})
    for i, e in enumerate(envs):
        xs = [q["pred_runtime"] for q in pts if q["env"] == e]
        ys = [q["chosen_runtime"] for q in pts if q["env"] == e]
        ax.scatter(xs, ys, s=60, color=cmap[i % len(cmap)],
                   edgecolor="black", label=e)
    # y = x reference line
    all_v = [v for q in pts for v in (q["pred_runtime"], q["chosen_runtime"])]
    if all_v:
        lo, hi = min(all_v), max(all_v)
        ax.plot([lo, hi], [lo, hi], ls="--", color="gray", lw=1,
                label="pred = actual")
    ax.set_xlabel("predicted runtime (s)", fontsize=s.label_size)
    ax.set_ylabel("observed runtime (s)", fontsize=s.label_size)
    ax.set_title("Predicted vs observed runtime for selected (\u03c1, \u03c4)",
                 fontsize=s.title_size)
    plot_legend(ax, loc="upper center", bbox_to_anchor=LEGEND_BBOX_LINE,
                ncol=min(LEGEND_NCOL_2, len(envs) + 1),
                fontsize=LEGEND_SIZE)
    plot_grid(ax, axis="both")
    fmt_axis(ax, axis="both")
    fig.tight_layout()
    save_fig(fig, path)


# Selector objective for the multi-output cost-predictor:
#   'runtime'  -> minimize predicted solve time only
#   'packets'  -> minimize predicted packet count (max aggregation gain) only
#   'tradeoff' -> minimize w_runtime*z_rt + w_packets*z_pk (z = training-set
#                 std units, so the ratio is directly interpretable)
OBJECTIVE = "tradeoff"
W_RUNTIME = 1.0
W_PACKETS = 1.0


def run_rho_tau_model():
    """Train (rho, tau_F) cost-predictor and evaluate selector quality."""
    data_path = "plots/param_sweep_data.json"
    out_model = "plots/rho_tau_model.pt"
    out_eval = "plots/rho_tau_model_eval.json"
    out_features = "plots/rho_tau_model_features.json"
    out_data = "plots/rho_tau_model_data.json"
    plot_regret = "plots/rho_tau_model_regret_by_env.pdf"
    plot_pred_vs_act = "plots/rho_tau_model_pred_vs_actual.pdf"

    epochs = 200
    hidden = 128
    n_layers = 3
    dropout = 0.1
    lr = 1e-3
    val_frac = 0.15
    seed = 7
    test_env = None
    device = None

    run = BlockRun("rho_tau_model", config={
        "data": data_path,
        "out_model": out_model,
        "out_eval": out_eval,
        "out_features": out_features,
        "epochs": epochs, "hidden": hidden, "n_layers": n_layers,
        "dropout": dropout, "lr": lr,
        "val_frac": val_frac, "seed": seed, "test_env": test_env,
        "objective": OBJECTIVE, "w_runtime": W_RUNTIME, "w_packets": W_PACKETS,
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
    run.config["envs_in_data"] = envs_seen
    print(f"  envs: {envs_seen}")

    # 1. Train
    print("\n[1/3] Training cost-predictor ...")
    train_t0 = time.time()
    _train_with_args(
        data_path, out_model, out_eval, out_features,
        epochs=epochs, hidden=hidden, n_layers=n_layers,
        dropout=dropout, lr=lr, val_frac=val_frac, seed=seed,
        test_env=test_env, device=device, objective=OBJECTIVE,
        w_runtime=W_RUNTIME, w_packets=W_PACKETS)
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
    qualities = _selector_quality(per_solve_rows, model_pack,
                                  device=(device or "cpu"),
                                  objective=OBJECTIVE,
                                  w_runtime=W_RUNTIME,
                                  w_packets=W_PACKETS)
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
            status=("optimal" if q.get("chosen_runtime") is not None
                    else "missing"),
            rho_star=q.get("rho_star"), tau_star=q.get("tau_star"),
            pred_runtime=q.get("pred_runtime"),
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
        _plot_pred_vs_actual(qualities, plot_pred_vs_act)
        plot_files.append(plot_pred_vs_act)

    regrets = [q["regret"] for q in qualities if q["regret"] is not None]
    gaps = [q["gap_to_worst"] for q in qualities if q["gap_to_worst"] is not None]
    pk_regrets = [q["packet_regret"] for q in qualities
                  if q["packet_regret"] is not None]
    summary = {
        "n_states": len(qualities),
        "n_states_with_choice": sum(1 for q in qualities
                                    if q.get("chosen_runtime") is not None),
        "mean_regret_s": float(np.mean(regrets)) if regrets else None,
        "std_regret_s": float(np.std(regrets)) if regrets else None,
        "mean_gap_to_worst": float(np.mean(gaps)) if gaps else None,
        "frac_worst_avoided": (float(np.mean([g > 0.5 for g in gaps]))
                               if gaps else None),
        "mean_packet_regret": float(np.mean(pk_regrets)) if pk_regrets else None,
        "std_packet_regret": float(np.std(pk_regrets)) if pk_regrets else None,
        "training_time_s": float(train_time),
        "training_eval": eval_payload,
    }
    for k, v in summary.items():
        print(f"  {k}: {v}")

    run.save(out_data, extra={
        "summary": summary,
        "per_state_quality": qualities,
        "plot_files": plot_files,
        "block_runtime_s": time.time() - block_start,
    })
    print(f"\nSaved block JSON -> {out_data}")
