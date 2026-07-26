"""Block downloaded from the old main.py — see blocks/__init__.py for the registry."""
from blocks._imports import (
    BlockRun, XLEN_RHO, YLEN_FRAG, YLEN_RUNTIME, _block_json_default, _prepare_dict_list, _unpack_env, apply_plot_style, env_1c_3sw_4f, env_1c_5sw_2f, env_1c_5sw_3f, env_2c_10sw_3f, env_2c_10sw_6f, env_2c_10sw_8f, env_2c_10sw_skew15, env_2c_10sw_uneven, env_3c_14sw_4f, fmt_axis, json, new_fig, np, os, plot_grid, plot_legend, plt, save_fig, style, time,
)
from blocks._flexina_helpers import _solve_flexina_once, _no_aggregation_packets


def _heatmap(grid, rho_labels, tau_labels, title, fname, cmap_name,
             cbar_label, annotate=True):
    """Adaptive-size heatmap; figure + font scale with grid dimensions.

    Axis ticks, title, and colorbar labels reuse the project's central
    style defaults (sim.plot.style) so the heatmap is visually
    consistent with the rest of the project's plots. Only the cell-
    annotation font size scales down on dense grids (where there's no
    room for the default project font size).
    """
    s = apply_plot_style()
    n_rows, n_cols = grid.shape
    fig_w = max(9, 1.2 * n_cols)
    fig_h = max(7, 0.6 * n_rows)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    im = ax.imshow(grid, origin='lower', aspect='auto',
                   cmap=cmap_name, interpolation='nearest')
    ax.set_xticks(np.arange(len(tau_labels)))
    ax.set_yticks(np.arange(len(rho_labels)))
    ax.set_xticklabels(tau_labels, fontsize=s.tick_size)
    ax.set_yticklabels(rho_labels, fontsize=s.tick_size)
    ax.set_xlabel('τ_F (time window)', fontsize=s.label_size)
    ax.set_ylabel('ρ (switch selection)', fontsize=s.label_size)
    ax.set_title(title, fontsize=s.title_size)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label, fontsize=s.label_size)
    cbar.ax.tick_params(labelsize=s.tick_size)
    # Tick labels for dense grids: shrink & keep rho labels readable.
    if n_rows > 12:
        for lbl in ax.get_yticklabels():
            lbl.set_rotation(0)
            lbl.set_fontsize(max(7, s.tick_size - 0.18 * n_rows))
    if n_cols > 8:
        for lbl in ax.get_xticklabels():
            lbl.set_fontsize(max(7, s.tick_size - 0.18 * n_cols))
    if annotate:
        font_size = max(5, 11 - 0.18 * max(n_rows, n_cols))
        vmax = np.nanmax(grid) if np.isfinite(np.nanmax(grid)) else 0.0
        for i in range(n_rows):
            for j in range(n_cols):
                val = grid[i, j]
                if np.isnan(val):
                    txt = "—"
                elif cbar_label.startswith('runtime'):
                    txt = f"{val:.2g}"
                else:
                    txt = f"{val:.1f}"
                color = ('white' if vmax > 0 and val > 0.55 * vmax
                         else 'black')
                ax.text(j, i, txt, ha='center', va='center',
                        color=color, fontsize=font_size)
    save_fig(fig, fname)


def run_param_sweep():
    """
    Joint (ρ × τ_F) parameter sweep on FlexINA, producing BOTH:
      * Heatmap per env for fragments and runtime (cell annotations).
      * Trade-off scatter (packet reduction vs runtime) per env, with the
        trade-off Pareto front drawn inline per-env (in-section plots).

    All plotting happens inside the per-env loop, so each env's heatmap
    pair and trade-off scatter are emitted as soon as that env's sweep
    finishes — no separate post-sweep plot section.

    Raw observations are saved at the end to:
      * plots/param_sweep_data.json (per-cell grid + raw rows + per_solve
        rows carrying full observable state/load per individual prediction,
        for offline training of an adaptive (rho, tau) selector)
      * plots/param_sweep_tradeoff_data.json (per (env, rho, tau, ittr) row, with
        reduction field)
    """
    # Environments span the topology/load axes so the (rho, tau) selector
    # has enough diversity to generalize at inference time. 9 envs cover:
    #   * 1-cluster (light 2fr, reference 3fr)
    #   * 2-cluster reference (3fr), heavier (6fr, 8fr), uneven load, skew15
    #   * 3-cluster fabric (14 switches)
    # The two Zipf-skew variants (`env_2c_10sw_skew1` collapses to 1 worker
    # after `_optimize_env`) are degenerate for ρ×τ grid training, so we use
    # only the mild `env_2c_10sw_skew15` (4 cluster-0 workers on switch 0).
    envs = [
        env_1c_5sw_2f,        # 1-cluster, light 2 frags/worker
        env_1c_5sw_3f,        # 1-cluster reference, 3 frags/worker
        env_2c_10sw_3f,       # 2-cluster reference
        env_2c_10sw_6f,       # 2-cluster, heavier load
        env_2c_10sw_8f,       # 2-cluster, heavy load
        env_2c_10sw_uneven,   # 2-cluster, uneven load
        env_2c_10sw_skew15,   # 2-cluster, mild Zipf-skew placement
        env_3c_14sw_4f,       # 3-cluster fabric
        env_1c_3sw_4f,        # compact 3-switch spine-leaf, 4 frags/worker
    ]
    maxAggregate = 2
    ittrNum = 2
    # Coarser ρ grid to cut compute: 10% .. 90% in 10% steps -> 9 values
    # (drop the 5%-offset columns 5%,15%,25%,35%,45%,55%,65%,75%,85% —
    # they're linearly interpolable between the 10%-step cells).
    #   ρ  from 10% to 90% in 10% steps ->  9 values
    #   τ_F from 6 to 12 in 1-slot steps -> 7 values (trimmed from 6..14
    #   to offset the extra envs; the 7..12 τ range still covers the
    #   regime where more aggregation slots yield diminishing returns)
    Percentages = [round(0.10 * i, 2) for i in range(1, 10)]   # 0.10 .. 0.90
    Taus = list(range(6, 13))                                  # 6 .. 12
    timeout_per_solve = 60
    timeout_no_agg = 60
    solve_counter = 0
    # Total number of sub-solves actually performed (sum across envs).
    # Each env has its own dict_list length — sum per-env solve counts so
    # the progress counter actually reaches 100% instead of stopping at
    # (actual_total / max_dict_list_len) when envs have different sizes.
    _solve_per_env = {
        e: len(_prepare_dict_list(_unpack_env(e)[9], _unpack_env(e)[10]))
        for e in envs
    }
    total_solves = (len(Percentages) * len(Taus) * ittrNum
                    * sum(_solve_per_env.values()))

    grids = {  # env_name -> {'packets': 2-D array, 'runtime': 2-D array}
    }
    rho_labels = [f"{int(p * 100)}%" for p in Percentages]
    tau_labels = [str(t) for t in Taus]

    run = BlockRun("param_sweep", config={
        "envs": [e.__name__ for e in envs],
        "models": ["defineModel_selectedSwitches"],
        "model_labels": ["FlexINA"],
        "maxAggregate": maxAggregate,
        "ittrNum": ittrNum,
        "Percentages": Percentages,
        "Taus": Taus,
        "timeout_per_solve": timeout_per_solve,
        "timeout_no_agg": timeout_no_agg,
        "addTime_factor": 0.6,
    }, axis={"x": XLEN_RHO, "x_extra": "τ_F (time window)",
             "y_fragments": YLEN_FRAG, "y_runtime": YLEN_RUNTIME,
             "x_ticks": rho_labels, "x_ticks_tau": tau_labels})

    raw_rows = []          # full per-solve rows (for param_sweep_data.json)
    per_solve_rows = []    # one row per individual sub-solve (state + load)
    tradeoff_rows = []         # aggregated per (rho, tau, ittr) rows with reduction
    block_start = time.time()
    for envTemp in envs:
        env_tuple = _unpack_env(envTemp)
        dict_list = _prepare_dict_list(env_tuple[9], env_tuple[10])
        env_name = envTemp.__name__
        # Topology fields used to label per-sub-solve rows (one unpack).
        (_, _, _, pSwitchesNumber, _,
         _, _, workersNumber, numAllFrags,
         _, _, _, _, _, clusters) = env_tuple
        # 2-D arrays indexed [i_rho][i_tau]
        pkt_grid = np.full((len(Percentages), len(Taus)), np.nan)
        rt_grid = np.full((len(Percentages), len(Taus)), np.nan)
        # Reference packet count (no aggregation) — for reduction = 1 - pkts/ref
        ref_pkts, _ = _no_aggregation_packets(
            env_tuple, dict_list, T_max_1=0, T_max_2=8,
            timeout_sec=timeout_no_agg)
        if ref_pkts == 0:
            print(f"[{env_name}] reference (no-agg) UNAVAILABLE — "
                  f"no-aggregation solve failed; reduction column will be nan")
        else:
            print(f"[{env_name}] reference (no-agg) packets = {ref_pkts}")
        print(f"[{env_name}] sweep (ρ ∈ 10%..90%) × (τ_F ∈ 6..14), "
              f"{len(Percentages) * len(Taus)} cells")
        # Accumulator for trade-off scatter points per-env. We use ONE row per
        # (rho, tau, ittr) — matches the previous param_sweep block — and
        # derive (reduction, runtime) for that observation.
        env_tradeoff_rows = []
        for i_rho, percentage in enumerate(Percentages):
            for i_tau, tau_F in enumerate(Taus):
                pkt_runs, rt_runs = [], []
                for ittr in range(ittrNum):
                    T_max_1 = 0
                    T_max_2 = tau_F
                    addTime = int(0.6 * T_max_2)
                    numPackets, RuntimeTotal = 0, 0
                    any_ok = False
                    # Per-sub-solve outcomes — the `status` recorded in
                    # the raw_rows is a *summary* (e.g. "optimal,optimal
                    # ,timelimit"), not whatever status the last sub-solve
                    # happened to return. Otherwise a cell where the first
                    # two sub-solves succeeded and the third timed out
                    # would be marked "timelimit" despite producing actual
                    # packets — confusing for downstream JSON readers.
                    sub_statuses = []
                    cell_construction = 0.0  # sum of build times for this cell
                    cell_solve = 0.0         # sum of SCIP optimize times for this cell
                    for items in range(0, len(dict_list)):
                        fragmentsofEachWorker = dict_list[items]
                        solve_counter += 1
                        print(f"  [{solve_counter}/{total_solves}] {env_name} "
                              f"ρ={percentage} τ_F={tau_F} ittr={ittr} ",
                              end="", flush=True)
                        (numPacket, Runtime, status, _, _, _,
                         construction_time) = _solve_flexina_once(
                            env_tuple, fragmentsofEachWorker, maxAggregate,
                            T_max_1, T_max_2, percentage,
                            timeout_sec=timeout_per_solve)
                        sub_statuses.append(status)
                        cell_construction += construction_time
                        cell_solve += Runtime if Runtime else 0.0
                        # Observable load/state for this sub-solve — every
                        # field needed to train an offline (rho, tau)
                        # selector is captured here, for *each* prediction.
                        _load = {w: len(frags)
                                 for w, frags in fragmentsofEachWorker.items()}
                        num_active_frags = sum(_load.values())
                        num_active_workers = len(_load)
                        per_solve_rows.append({
                            'env': env_name,
                            'rho': percentage,
                            'tau': tau_F,
                            'ittr': ittr,
                            'slot_idx': items,
                            'status': status,
                            'packets': numPacket,
                            'runtime': Runtime,
                            'construction_time_s': construction_time,
                            'solve_time_s': Runtime,
                            'T_max_1': T_max_1,
                            'T_max_2': T_max_2,
                            'num_switches': pSwitchesNumber,
                            'num_workers': workersNumber,
                            'num_all_frags': numAllFrags,
                            'num_clusters': len(clusters),
                            'num_active_frags': num_active_frags,
                            'num_active_workers': num_active_workers,
                            'per_worker_num_frags': _load,
                        })
                        # Runtime accounting: credit the real time of every
                        # sub-solve — including timeouts / skips — so that
                        # RuntimeTotal reflects the *total wall time* of
                        # the cell, not just successful sub-solves. The
                        # packet count still only advances on success; a
                        # failed sub-solve that burned 60s now shows up
                        # in RuntimeTotal honestly. (Previously the gate
                        # `if numPacket and numPacket > 0` hid the cost of
                        # every failed sub-solve.)
                        RuntimeTotal += Runtime
                        if numPacket and numPacket > 0:
                            numPackets += numPacket
                            any_ok = True
                        # Advance the rolling time window on *every* sub-
                        # solve (successful or not); otherwise a failed
                        # sub-solve leaves the next dict_list slot solved
                        # against the same window, biasing failed cells'
                        # packet counts toward 0 in a way that isn't
                        # comparable across (ρ, τ) cells.
                        T_max_1 += addTime
                        T_max_2 += addTime
                        print(f"-> {status} pkts={numPacket} {Runtime:.3f}s")
                    # Summary status for the JSON row — grouped by
                    # occurrence so downstream readers can tell at a
                    # glance whether the row's "timelimit" came from one
                    # sub-solve or all of them.
                    from collections import Counter as _Counter
                    summary_status = ",".join(
                        f"{st}x{c}" for st, c in
                        _Counter(sub_statuses).most_common())
                    if any_ok:
                        pkt_runs.append(numPackets)
                        rt_runs.append(RuntimeTotal)
                        reduction = (1.0 - numPackets / ref_pkts) \
                            if ref_pkts else float('nan')
                        tradeoff_row = {'env': env_name, 'rho': percentage,
                                    'tau': tau_F, 'ittr': ittr,
                                    'packets': numPackets,
                                    'runtime': RuntimeTotal,
                                    'reduction': reduction}
                        env_tradeoff_rows.append(tradeoff_row)
                        tradeoff_rows.append(tradeoff_row)
                        # Mirror into the BlockRun observation set
                        # (one row per (env, ρ, τ, ittr) cell — the
                        # smallest unit that one trade-off plot point
                        # corresponds to).
                        run.observe(
                            model="FlexINA", env=env_name,
                            x=f"ρ={percentage},τ_F={tau_F}",
                            ittr=ittr,
                            packets=numPackets, runtime=RuntimeTotal,
                            construction_time_s=cell_construction,
                            solve_time_s=cell_solve,
                            status=summary_status,
                            rho=percentage, tau=tau_F, reduction=reduction,
                            ref_pkts=ref_pkts)
                    else:
                        env_tradeoff_rows.append({'env': env_name,
                                              'rho': percentage,
                                              'tau': tau_F, 'ittr': ittr,
                                              'packets': None,
                                              'runtime': None,
                                              'reduction': None})
                        run.observe(
                            model="FlexINA", env=env_name,
                            x=f"ρ={percentage},τ_F={tau_F}", ittr=ittr,
                            packets=None, runtime=None,
                            construction_time_s=cell_construction,
                            solve_time_s=cell_solve,
                            status=summary_status,
                            rho=percentage, tau=tau_F, reduction=None,
                            ref_pkts=ref_pkts)
                    raw_rows.append({'env': env_name, 'rho': percentage,
                                     'tau': tau_F, 'ittr': ittr,
                                     'packets': numPackets if any_ok else None,
                                     'runtime': RuntimeTotal if any_ok else None,
                                     'status': summary_status})
                if pkt_runs:
                    pkt_grid[i_rho, i_tau] = float(np.mean(pkt_runs))
                    rt_grid[i_rho, i_tau] = float(np.mean(rt_runs))
        grids[env_name] = {'packets': pkt_grid, 'runtime': rt_grid}

        # --- In-section plot #1: heatmaps for THIS env (fragments + runtime) ---
        _heatmap(pkt_grid, rho_labels, tau_labels,
                 f'# fragments  ({env_name})',
                 f"plots/param_sweep_fragments_heatmap_{env_name}.pdf",
                 cmap_name=style.cmap_fragments, cbar_label='# fragments')
        _heatmap(rt_grid, rho_labels, tau_labels,
                 f'runtime  ({env_name})',
                 f"plots/param_sweep_runtime_heatmap_{env_name}.pdf",
                 cmap_name=style.cmap_runtime, cbar_label='runtime (s)')
        print(f"  [{env_name}] heatmaps saved "
              f"-> plots/param_sweep_{{fragments,runtime}}_heatmap_{env_name}.pdf")

        # --- In-section plot #2: trade-off scatter + Pareto front for THIS env ---
        ok = [r for r in env_tradeoff_rows
              if r.get('reduction') is not None
              and np.isfinite(r['reduction'])
              and r['runtime'] is not None]
        if ok:
            xs = [r['reduction'] for r in ok]
            ys = [r['runtime'] for r in ok]
            rhos = [r['rho'] for r in ok]
            pts = sorted(zip(xs, ys), key=lambda p: (-p[0], p[1]))
            pareto, best_rt = [], float('inf')
            for x, y in pts:
                if y < best_rt:
                    pareto.append((x, y))
                    best_rt = y
            apply_plot_style()
            fig, ax = new_fig()
            sc = ax.scatter(xs, ys, c=rhos, cmap=style.cmap_scatter_rho,
                            s=80, edgecolor='black')
            if pareto:
                px, py = zip(*pareto)
                ax.plot(px, py, 'r--', lw=2, label='Pareto front')
                plot_legend(ax)
            cbar = plt.colorbar(sc, ax=ax)
            cbar.set_label('ρ', fontsize=style.label_size)
            cbar.ax.tick_params(labelsize=style.tick_size)
            ax.set_xlabel('Packet reduction (1 - pkts/pkts₀)',
                          fontsize=style.label_size)
            ax.set_ylabel('Runtime (s)', fontsize=style.label_size)
            ax.set_title(f'Trade-off ({env_name})',
                        fontsize=style.title_size)
            ax.tick_params(labelsize=style.tick_size)
            plot_grid(ax, axis='both')
            fmt_axis(ax, axis='both')
            save_fig(fig, f"plots/param_sweep_tradeoff_{env_name}.pdf")
            print(f"  [{env_name}] trade-off plot saved "
                  f"-> plots/param_sweep_tradeoff_{env_name}.pdf")

        # Print the env's grids to stdout
        print(f"\n=== {env_name} ===")
        print("packets grid (rows=ρ, cols=τ_F):")
        print(np.array_str(pkt_grid, precision=2, suppress_small=True))
        print("runtime grid (rows=ρ, cols=τ_F):")
        print(np.array_str(rt_grid, precision=3, suppress_small=True))

    print(f"\n  done in {time.time() - block_start:.1f}s")

    # All sub-solves across all envs/ρ/τ are finished.
    print(f">>> All {total_solves} sub-solves complete "
          f"(solve_counter={solve_counter}). Block finished in "
          f"{time.time() - block_start:.1f}s — proceeding to plots/JSON.")

    # --- Save raw observations for reuse by online-model block ---
    # The JSON preserves the existing schema (rows, per_solve, Percentages,
    # Taus, grids) consumed by blocks/rho_tau/train.py, but wraps it in the
    # BlockRun metadata (block name, host, python, block runtime, config,
    # per-observation rows for trade-off reduction/runtime) so the run can be
    # regenerated/understood from this single file.
    import json, os
    os.makedirs("plots", exist_ok=True)

    # Collect the per-env plot files emitted during the sweep, so the JSON
    # comprehensively lists everything produced by this block run.
    plot_files = []
    for envTemp in envs:
        n = envTemp.__name__
        plot_files.extend([
            f"plots/param_sweep_fragments_heatmap_{n}.pdf",
            f"plots/param_sweep_runtime_heatmap_{n}.pdf",
            f"plots/param_sweep_tradeoff_{n}.pdf",
        ])

    # Merge BlockRun metadata with the raw per-cell data, then save.
    run_payload = run.to_dict()
    run_payload.update({
        'rows': raw_rows,
        'per_solve': per_solve_rows,
        'Percentages': Percentages, 'Taus': Taus,
        'rho_labels': rho_labels, 'tau_labels': tau_labels,
        'grids': {k: {'packets': v['packets'].tolist(),
                      'runtime': v['runtime'].tolist()}
                  for k, v in grids.items()},
        'tradeoff_rows': tradeoff_rows,
        'plot_files': plot_files,
    })
    with open("plots/param_sweep_data.json", "w") as f:
        json.dump(run_payload, f, indent=2, default=_block_json_default)

    # Trade-off raw per-(env, rho, tau, ittr) rows — kept as the
    # existing standalone schema for backward compatibility.
    with open("plots/param_sweep_tradeoff_data.json", "w") as f:
        json.dump(tradeoff_rows, f, indent=2, default=_block_json_default)
