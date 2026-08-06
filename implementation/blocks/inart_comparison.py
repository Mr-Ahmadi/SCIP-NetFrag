"""InArt vs FlexINA comparison — same model, InArt adds constraintInArt."""
from blocks._flexina_helpers import _solve_flexina_once
from blocks._imports import (
    BAR_WIDTH, BlockRun, INART_COLORS, INART_HATCHES, INART_LABELS,
    INART_MARKERS, LEGEND_BBOX_BARS, LEGEND_BBOX_LINE, LEGEND_NCOL_2,
    LEGEND_SIZE, XLEN_TOPOLOGY, YLEN_FRAG, YLEN_RUNTIME, env_labels,
    _prepare_dict_list, _unpack_env, apply_constraints,
    apply_constraints_InArt, apply_plot_style,
    env_2c_10sw_3f, env_2c_10sw_uneven, env_3c_14sw_4f,
    env_2c_10sw_skew15, fmt_axis, new_fig, np, plot_errorbar, plot_grid,
    plot_grouped_bars, plot_legend, plt,
    save_fig, style, time,
)

# Model configs: (name, apply_constraints_fn)
# Both use the same model builder; InArt = FlexINA + constraintInArt.
MODEL_VARIANTS = [
    (INART_LABELS[0], apply_constraints_InArt),
    (INART_LABELS[1], apply_constraints),
]


def run_inart_comparison():
    """
    InArt vs FlexINA across multiple topologies.
    """
    envs = [
        env_2c_10sw_3f,
        env_2c_10sw_uneven,
        env_2c_10sw_skew15,
        env_3c_14sw_4f,
    ]
    x_labels = env_labels(envs)

    # max-agg 2 ties both models on these envs; max-agg 3 is where chaining
    # separates them. Envs chosen for proven optimality without time limits
    # (env_1c_5sw_3f was dropped: its first slot hit the per-solve limit).
    MAX_AGGREGATION = 3
    ittrNum = 3
    # Equal ρ for both — same candidate-switch set.
    percentage = 0.5
    SOLVE_TIMEOUT_S = 120
    ADD_TIME_FACTOR = 1.0
    solve_counter = 0
    total_solves = (len(MODEL_VARIANTS) * ittrNum
                    * sum(len(_prepare_dict_list(*_unpack_env(e)[9:11]))
                          for e in envs))

    run = BlockRun("inart", config={
        "envs": [e.__name__ for e in envs],
        "model_labels": INART_LABELS,
        "max_aggregation": MAX_AGGREGATION,
        "ittrNum": ittrNum,
        "percentage": percentage,
        "T_max_2_init": 8,
        "addTime_factor": ADD_TIME_FACTOR,
        "solve_timeout_s": SOLVE_TIMEOUT_S,
        "note": ("Fair comparison: both models use defineModel_selectedSwitches "
                 "with identical constraints/objective. InArt adds only "
                 "constraintInArt (single-aggregation-per-fragment)."),
    }, axis={"x": XLEN_TOPOLOGY, "y_fragments": YLEN_FRAG,
             "y_runtime": YLEN_RUNTIME, "x_ticks": x_labels})

    results_by_label = {}   # {label: {"packets": [...], "runtime": [...],
                            #           "err_runtime": [[],[],...]}}

    block_start = time.time()
    for label, apply_fn in MODEL_VARIANTS:
        print(f"[{label}]")
        numPackets2 = []
        RuntimeTotal2 = []
        errorRuntime = []
        errorPackets = []
        for envTemp in envs:
            errorRuntime.append([])
            errorPackets.append([])
            env_tuple = _unpack_env(envTemp)
            fragmentsofEachWorker, totalWorkers = env_tuple[9], env_tuple[10]

            dict_list = _prepare_dict_list(fragmentsofEachWorker, totalWorkers)
            x_label = env_labels([envTemp])[0]
            avgPacket = []
            avgRuntime = []
            for ittr in range(ittrNum):
                T_max_1 = 0
                T_max_2 = 8
                addTime = int(ADD_TIME_FACTOR * T_max_2)
                # Carried across dict_list items within this ittr (FlexINA Phase 3).
                Y_Used, Z_Used = set(), set()
                numPackets = 0
                RuntimeTotal = 0
                construction_total = 0.0
                solve_total = 0.0
                statuses = []
                any_failed = False
                for items in range(0, len(dict_list)):
                    solve_counter += 1
                    env_name = envTemp.__name__
                    print(f"  [{solve_counter}/{total_solves}] "
                          f"{label:15s} {env_name:22s} "
                          f"ittr={ittr} slot={items} ... ",
                          end="", flush=True)
                    (numPacket, Runtime, status, Y_Used, Z_Used,
                     timed_out, construction_time) = _solve_flexina_once(
                        env_tuple, dict_list[items], MAX_AGGREGATION,
                        T_max_1, T_max_2, percentage,
                        timeout_sec=SOLVE_TIMEOUT_S, apply_fn=apply_fn,
                        Y_Used=Y_Used, Z_Used=Z_Used)
                    construction_total += construction_time
                    solve_total += Runtime
                    statuses.append(status)
                    print(f"{status} pkts={numPacket} {Runtime:.3f}s"
                          + (" (no incumbent)" if timed_out else ""))
                    any_failed = any_failed or timed_out

                    if not timed_out:
                        T_max_1 += addTime
                        T_max_2 += addTime
                    numPackets += numPacket
                    RuntimeTotal += Runtime
                errorRuntime[-1].append(RuntimeTotal)
                errorPackets[-1].append(numPackets)
                avgPacket.append(numPackets)
                avgRuntime.append(RuntimeTotal)
                run.observe(
                    model=label,
                    env=envTemp.__name__, x=x_label, ittr=ittr,
                    packets=numPackets, runtime=RuntimeTotal,
                    construction_time_s=construction_total,
                    solve_time_s=solve_total,
                    status=",".join(statuses),
                    # True only when some sub-solve produced NO usable incumbent.
                    timed_out_any=any_failed,
                    not_proven_optimal_any=any(
                        s in ("timelimit", "gaplimit", "nodelimit",
                              "sollimit", "stallnodelimit")
                        for s in statuses))
            numPackets2.append(sum(avgPacket) / max(1, len(avgPacket)))
            RuntimeTotal2.append(sum(avgRuntime) / max(1, len(avgRuntime)))
        results_by_label[label] = {
            "packets": numPackets2,
            "runtime": RuntimeTotal2,
            "err_runtime": errorRuntime,
        }

        print(f"  done in {time.time() - block_start:.1f}s")

    print(f"\n>>> All {total_solves} sub-solves complete "
          f"(solve_counter={solve_counter}). Block finished in "
          f"{time.time() - block_start:.1f}s — proceeding to plots.")

    C_inart = results_by_label[INART_LABELS[0]]["packets"]
    C_flex  = results_by_label[INART_LABELS[1]]["packets"]

    plot_grouped_bars(x_labels, [C_inart, C_flex], INART_LABELS,
                      YLEN_FRAG, XLEN_TOPOLOGY,
                      "plots/inart_fragments.pdf",
                      color_indices=INART_COLORS, hatch_list=INART_HATCHES,
                      width=BAR_WIDTH, legend_bbox=LEGEND_BBOX_BARS,
                      legend_ncol=LEGEND_NCOL_2, legend_size=LEGEND_SIZE,
                      xtick_rotation=20)

    y_inart = results_by_label[INART_LABELS[0]]["runtime"]
    y_flex  = results_by_label[INART_LABELS[1]]["runtime"]
    e_inart = [np.std(vals) for vals in results_by_label[INART_LABELS[0]]["err_runtime"]]
    e_flex  = [np.std(vals) for vals in results_by_label[INART_LABELS[1]]["err_runtime"]]
    plot_errorbar(x_labels, [y_inart, y_flex], [e_inart, e_flex],
                  INART_LABELS, YLEN_RUNTIME, XLEN_TOPOLOGY,
                  "plots/inart_runtime_errorbar.pdf",
                  fmt_list=INART_MARKERS,
                  legend_bbox=LEGEND_BBOX_LINE, legend_size=LEGEND_SIZE,
                  xtick_rotation=20)

    apply_plot_style()
    fig, ax = new_fig()
    ax.plot(x_labels, y_inart, ls='dashed', marker='s',
            markersize=style.marker_size, label=INART_LABELS[0])
    ax.plot(x_labels, y_flex, ls='dashed', marker='p',
            markersize=style.marker_size, label=INART_LABELS[1])
    plot_legend(ax, loc='upper center', bbox_to_anchor=LEGEND_BBOX_LINE,
                ncol=LEGEND_NCOL_2)
    ax.set_xlabel(XLEN_TOPOLOGY)
    ax.set_ylabel(YLEN_RUNTIME)
    plt.setp(ax.get_xticklabels(), rotation=20, ha='right')
    fmt_axis(ax, axis='both')
    plot_grid(ax, axis='both')
    save_fig(fig, "plots/inart_runtime.pdf")

    summary = run.summary(x_labels, series_order=INART_LABELS,
                          y_fragments=YLEN_FRAG, y_runtime=YLEN_RUNTIME,
                          x_label=XLEN_TOPOLOGY)
    run.save("plots/inart_data.json", extra={"summary": summary,
                                              "plot_files": [
        "plots/inart_fragments.pdf",
        "plots/inart_runtime_errorbar.pdf",
        "plots/inart_runtime.pdf",
    ]})
