from blocks._imports import (
    BlockRun, XLEN_RHO, XLEN_REDUCTION, XLEN_TAU_WINDOW, YLEN_FRAG, YLEN_RUNTIME,
    _block_json_default, _prepare_dict_list, _unpack_env, apply_plot_style,
    env_1c_5sw_3f, env_2c_10sw_3f, env_2c_10sw_6f, env_2c_10sw_skew15,
    env_3c_14sw_4f, fmt_axis, json, new_fig, np, os, plot_grid, plot_legend,
    plt, save_fig, style, time,
)
from blocks._common import ADD_TIME_FACTOR
from blocks._flexina_helpers import _solve_flexina_once, _no_aggregation_packets
from blocks.rho_tau.topo_features import topology_features


def _heatmap(grid, rho_labels, tau_labels, title, fname, cmap_name,
             cbar_label, annotate=True):
    """Adaptive-size heatmap; figure + font scale with grid dimensions."""
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
    ax.set_xlabel(XLEN_TAU_WINDOW, fontsize=s.label_size)
    ax.set_ylabel(XLEN_RHO, fontsize=s.label_size)
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
        finite = grid[np.isfinite(grid)]
        vmax = float(finite.max()) if finite.size else 0.0
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
    """Joint (rho x tau_F) parameter sweep on FlexINA.

    Produces heatmaps per env for fragments and runtime, plus trade-off
    scatter (packet reduction vs runtime) per env with Pareto front.
    """
    # Envs already exercised by other blocks for cross-checking. Load-preserving
    # mode keeps each env's true fragment counts.
    envs = [
        env_1c_5sw_3f,        # 1-cluster reference
        env_2c_10sw_3f,       # 2-cluster reference
        env_2c_10sw_6f,       # heavier load
        env_2c_10sw_skew15,   # mild Zipf-skew placement
        env_3c_14sw_4f,       # 3-cluster fabric
    ]
    maxAggregate = 2
    ittrNum = 2
    # rho: 10%..90% in 10% steps -> 9 values; tau_F: 6..12 -> 7 values.
    Percentages = [round(0.10 * i, 2) for i in range(1, 10)]
    Taus = list(range(6, 13))
    timeout_per_solve = 120
    timeout_no_agg = 120
    solve_counter = 0
    _solve_per_env = {
        e: len(_prepare_dict_list(_unpack_env(e, load=True)[9],
                                  _unpack_env(e, load=True)[10]))
        for e in envs
    }
    total_solves = (len(Percentages) * len(Taus) * ittrNum
                    * sum(_solve_per_env.values()))

    grids = {}  # env_name -> {'packets': 2-D array, 'runtime': 2-D array}
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
        "addTime_factor": ADD_TIME_FACTOR,
    }, axis={"x": XLEN_RHO, "x_extra": "τ_F (time window)",
             "y_fragments": YLEN_FRAG, "y_runtime": YLEN_RUNTIME,
             "x_ticks": rho_labels, "x_ticks_tau": tau_labels})

    raw_rows = []
    per_solve_rows = []    # per individual sub-solve (state + load for training)
    tradeoff_rows = []
    block_start = time.time()
    for envTemp in envs:
        env_tuple = _unpack_env(envTemp, load=True)
        dict_list = _prepare_dict_list(env_tuple[9], env_tuple[10])
        env_name = envTemp.__name__
        # Topology descriptors (constant per env) so the cost-predictor can
        # separate connectivity-distinct envs even when their per-solve load
        # statistics coincide; recorded on every per_solve row.
        topo_feats = topology_features(env_tuple)
        # Topology fields for per-solve row labels.
        (_, _, _, pSwitchesNumber, _,
         _, _, workersNumber, numAllFrags,
         _, _, _, _, _, clusters) = env_tuple
        pkt_grid = np.full((len(Percentages), len(Taus)), np.nan)
        rt_grid = np.full((len(Percentages), len(Taus)), np.nan)
        # Reference packet count (no aggregation) for reduction = 1 - pkts/ref.
        ref_pkts, _ = _no_aggregation_packets(
            env_tuple, dict_list, T_max_1=0, T_max_2=8,
            timeout_sec=timeout_no_agg)
        if ref_pkts == 0:
            print(f"[{env_name}] reference (no-agg) UNAVAILABLE — "
                  f"no-aggregation solve failed; reduction column will be nan")
        else:
            print(f"[{env_name}] reference (no-agg) packets = {ref_pkts}")
        print(f"[{env_name}] sweep (ρ ∈ 10%..90%) × (τ_F ∈ 6..12), "
              f"{len(Percentages) * len(Taus)} cells")
        env_tradeoff_rows = []
        for i_rho, percentage in enumerate(Percentages):
            for i_tau, tau_F in enumerate(Taus):
                pkt_runs, rt_runs = [], []
                for ittr in range(ittrNum):
                    T_max_1 = 0
                    T_max_2 = tau_F
                    addTime = int(ADD_TIME_FACTOR * T_max_2)
                    numPackets, RuntimeTotal = 0, 0
                    any_ok = False
                    sub_statuses = []
                    cell_construction = 0.0
                    cell_solve = 0.0
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
                        # Observable load/state for this sub-solve.
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
                            **topo_feats,
                        })
                        # Credit real time of every sub-solve (including
                        # timeouts) so RuntimeTotal reflects total wall time.
                        RuntimeTotal += Runtime
                        if numPacket and numPacket > 0:
                            numPackets += numPacket
                            any_ok = True
                        T_max_1 += addTime
                        T_max_2 += addTime
                        print(f"-> {status} pkts={numPacket} {Runtime:.3f}s")
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

        _heatmap(pkt_grid, rho_labels, tau_labels,
                 f'# fragments  ({env_name})',
                 f"plots/param_sweep_fragments_heatmap_{env_name}.pdf",
                 cmap_name=style.cmap_fragments, cbar_label=YLEN_FRAG)
        _heatmap(rt_grid, rho_labels, tau_labels,
                 f'runtime  ({env_name})',
                 f"plots/param_sweep_runtime_heatmap_{env_name}.pdf",
                 cmap_name=style.cmap_runtime, cbar_label=YLEN_RUNTIME)
        print(f"  [{env_name}] heatmaps saved "
              f"-> plots/param_sweep_{{fragments,runtime}}_heatmap_{env_name}.pdf")

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
            ax.set_xlabel(XLEN_REDUCTION, fontsize=style.label_size)
            ax.set_ylabel(YLEN_RUNTIME, fontsize=style.label_size)
            ax.set_title(f'Trade-off ({env_name})',
                        fontsize=style.title_size)
            ax.tick_params(labelsize=style.tick_size)
            plot_grid(ax, axis='both')
            fmt_axis(ax, axis='both')
            save_fig(fig, f"plots/param_sweep_tradeoff_{env_name}.pdf")
            print(f"  [{env_name}] trade-off plot saved "
                  f"-> plots/param_sweep_tradeoff_{env_name}.pdf")

        print(f"\n=== {env_name} ===")
        print("packets grid (rows=ρ, cols=τ_F):")
        print(np.array_str(pkt_grid, precision=2, suppress_small=True))
        print("runtime grid (rows=ρ, cols=τ_F):")
        print(np.array_str(rt_grid, precision=3, suppress_small=True))

    print(f"\n  done in {time.time() - block_start:.1f}s")

    print(f">>> All {total_solves} sub-solves complete "
          f"(solve_counter={solve_counter}). Block finished in "
          f"{time.time() - block_start:.1f}s — proceeding to plots/JSON.")

    import json, os
    os.makedirs("plots", exist_ok=True)

    plot_files = []
    for envTemp in envs:
        n = envTemp.__name__
        plot_files.extend([
            f"plots/param_sweep_fragments_heatmap_{n}.pdf",
            f"plots/param_sweep_runtime_heatmap_{n}.pdf",
            f"plots/param_sweep_tradeoff_{n}.pdf",
        ])

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

    with open("plots/param_sweep_tradeoff_data.json", "w") as f:
        json.dump(tradeoff_rows, f, indent=2, default=_block_json_default)
