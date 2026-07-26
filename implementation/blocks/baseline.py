"""Block downloaded from the old main.py — see blocks/__init__.py for the registry."""
from blocks._imports import (
    BAR_WIDTH, BASELINE_COLORS, BASELINE_HATCHES, BASELINE_LABELS, BASELINE_MARKERS, BlockRun, LEGEND_BBOX_BARS, LEGEND_BBOX_LINE, LEGEND_NCOL_2, LEGEND_SIZE, XLEN_AGG, YLEN_FRAG, YLEN_RUNTIME, _prepare_dict_list, _unpack_env, apply_constraints, apply_constraints_basic, apply_plot_style, create_Fragments, defineModel, defineModel_selectedSwitches, env_1c_5sw_3f, fmt_axis, new_fig, np, objective, plot_errorbar, plot_grid, plot_grouped_bars, plot_legend, preProcessMappingY, preProcessMappingZ, save_fig, solveProblem, style, time,
)

def run_baseline():
    envs = [env_1c_5sw_3f]
    models = [defineModel, defineModel_selectedSwitches]
    model_labels = BASELINE_LABELS                    # ['optimal', 'FlexINA']

    maxAggregate = 4
    ittrNum = 3
    percentage = 0.5
    solve_counter = 0

    # x-axis tick labels: aggregation levels (1,2,3).
    x_labels = [str(a) for a in range(1, maxAggregate)]
    run = BlockRun("baseline", config={
        "envs": [e.__name__ for e in envs],
        "models": [m.__name__ for m in models],
        "model_labels": model_labels,
        "maxAggregate": maxAggregate,
        "ittrNum": ittrNum,
        "percentage": percentage,
        "T_max_2_init": 8,
        "addTime_factor": 1.0,
    }, axis={"x": XLEN_AGG, "y_fragments": YLEN_FRAG, "y_runtime": YLEN_RUNTIME,
             "x_ticks": x_labels})

    kindsofModelsPackets = {m: [] for m in models}
    kindsofModelsRuntime = {m: [] for m in models}
    errorRuntimesM = {m: [] for m in models}    # per model: list per agg of [rt per ittr]
    errorPacketsM = {m: [] for m in models}

    # Total sub-solves across all envs — computed once before the loops so
    # the [N/total] counter doesn't shift when envs have different dict_list
    # sizes (otherwise the denominator jumps mid-run and the counter can
    # appear to stall or even run past 100%).
    _solve_per_env = {
        e: len(_prepare_dict_list(_unpack_env(e)[9], _unpack_env(e)[10]))
        for e in envs
    }
    total_solves = (len(models) * len(envs) * (maxAggregate - 1)
                    * ittrNum * sum(_solve_per_env.values()))

    block_start = time.time()
    for modelSolve in models:
        print(f"[{modelSolve.__name__}]")
        for envTemp in envs:
            (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
             pSwitchesNumber, numberSlotsSwitches, workersTopology,
             pWorkerPorts, workersNumber, numAllFrags,
             fragmentsofEachWorker, totalWorkers, stepsToSwitches,
             cutPorts, selectedSwitches, clusters) = _unpack_env(envTemp)

            dict_list = _prepare_dict_list(fragmentsofEachWorker, totalWorkers)
            numPackets2 = []
            RuntimeTotal2 = []
            errorRuntime = []
            errorPackets = []
            for maxAggregation in range(1, maxAggregate):
                errorRuntime.append([])
                errorPackets.append([])
                x_label = str(maxAggregation)
                for ittr in range(ittrNum):
                    T_max_1 = 0
                    T_max_2 = 8
                    addTime = int(1 * T_max_2)
                    Y_Used = set()
                    Z_Used = set()
                    numPackets = 0
                    RuntimeTotal = 0
                    avgPacket = []
                    avgRuntime = []
                    construction_total = 0.0
                    solve_total = 0.0
                    statuses = []
                    for items in range(0, len(dict_list)):
                        fragmentsofEachWorker = dict_list[items]
                        tc0 = time.time()
                        subSets, allofSubsets, usefulIntervalTime, fragments = \
                            create_Fragments(fragmentsofEachWorker, T_max_1, T_max_2, maxAggregation)
                        Y_Used = preProcessMappingY(Y_Used, allofSubsets[0])
                        Z_Used = preProcessMappingZ(Z_Used, subSets, usefulIntervalTime)
                        if modelSolve == defineModel_selectedSwitches:
                            (model, Z_Variables, Y_Variables, Prm1, Prm2,
                             clusterSets, switchinClusters, AllClusters) = \
                                modelSolve(allofSubsets, pSwitchesTopology, pSwitchPorts,
                                           T_max_1, T_max_2, workersTopology,
                                           fragmentsofEachWorker, pWorkerPorts,
                                           subSets, numberSlotsSwitches, usefulIntervalTime,
                                           Y_Used, Z_Used, maxAggregation, stepsToSwitches,
                                           cutPorts, selectedSwitches, percentage, clusters)
                            apply_constraints(
                                modelSolve, pSwitchesTopology, numberSlotsSwitches,
                                usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                                Z_Used, Y_Used, neighborsofEachSwitch, pSwitchPorts,
                                workersTopology, fragmentsofEachWorker, pWorkerPorts,
                                numAllFrags, clusterSets, switchinClusters, AllClusters,
                                Y_Variables, Z_Variables)
                        else:
                            (model, Z_Variables, Y_Variables, Prm1, Prm2) = \
                                modelSolve(allofSubsets, pSwitchesTopology, pSwitchPorts,
                                           T_max_1, T_max_2, workersTopology,
                                           fragmentsofEachWorker, pWorkerPorts,
                                           subSets, numberSlotsSwitches, usefulIntervalTime,
                                           Y_Used, Z_Used, maxAggregation, stepsToSwitches,
                                           cutPorts, selectedSwitches)
                            apply_constraints_basic(
                                modelSolve, pSwitchesTopology, numberSlotsSwitches,
                                usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                                Z_Used, Y_Used, neighborsofEachSwitch, pSwitchPorts,
                                workersTopology, fragmentsofEachWorker, pWorkerPorts,
                                numAllFrags, Y_Variables, Z_Variables)
                        objective(Y_Variables, model)
                        construction_total += time.time() - tc0

                        solve_counter += 1
                        print(f"  [{solve_counter}/{total_solves}] ", end="", flush=True)
                        ts0 = time.time()
                        (Y_Value_One, Z_Value_One, Y_Used, Z_Used,
                         numPacket, Runtime, status) = \
                            solveProblem(model, Y_Used, Z_Used)
                        solve_total += time.time() - ts0
                        statuses.append(status)
                        T_max_1 += addTime
                        T_max_2 += addTime
                        numPackets += numPacket
                        RuntimeTotal += Runtime
                    avgPacket.append(numPackets)
                    avgRuntime.append(RuntimeTotal)
                    errorRuntime[-1].append(RuntimeTotal)
                    errorPackets[-1].append(numPackets)
                    run.observe(
                        model=model_labels[models.index(modelSolve)],
                        env=envTemp.__name__, x=x_label, ittr=ittr,
                        packets=numPackets, runtime=RuntimeTotal,
                        construction_time_s=construction_total,
                        solve_time_s=solve_total,
                        status=",".join(statuses))
                numPackets2.append(sum(avgPacket) / len(avgPacket))
                RuntimeTotal2.append(sum(avgRuntime) / len(avgRuntime))
            kindsofModelsPackets[modelSolve] = numPackets2
            kindsofModelsRuntime[modelSolve] = RuntimeTotal2
            errorRuntimesM[modelSolve] = errorRuntime
            errorPacketsM[modelSolve] = errorPackets

    print(f"  done in {time.time() - block_start:.1f}s")
    print("Packets:", kindsofModelsPackets)
    print("Runtime:", kindsofModelsRuntime)

    # All sub-solves across all models/envs are finished.
    print(f"\n>>> All {total_solves} sub-solves complete "
          f"(solve_counter={solve_counter}). Block finished in "
          f"{time.time() - block_start:.1f}s — proceeding to plots.")

    # --- Plots (consistent style: centralized labels + legend bbox) ---
    C_1 = kindsofModelsPackets[defineModel]
    C_5 = kindsofModelsPackets[defineModel_selectedSwitches]

    plot_grouped_bars(x_labels, [C_1, C_5], BASELINE_LABELS,
                      YLEN_FRAG, XLEN_AGG,
                      "plots/basic_fragments_vs_aggregation.pdf",
                      color_indices=BASELINE_COLORS, hatch_list=BASELINE_HATCHES,
                      width=BAR_WIDTH, legend_bbox=LEGEND_BBOX_BARS,
                      legend_ncol=LEGEND_NCOL_2, legend_size=LEGEND_SIZE)

    error_C1 = [np.std(vals) for vals in errorPacketsM[defineModel]]
    error_C5 = [np.std(vals) for vals in errorPacketsM[defineModel_selectedSwitches]]
    plot_errorbar(x_labels, [C_1, C_5], [error_C1, error_C5],
                  BASELINE_LABELS, YLEN_FRAG, XLEN_AGG,
                  "plots/basic_fragments_vs_aggregation_errorbar.pdf",
                  fmt_list=BASELINE_MARKERS,
                  legend_bbox=LEGEND_BBOX_LINE, legend_size=LEGEND_SIZE)

    y1 = kindsofModelsRuntime[defineModel]
    y5 = kindsofModelsRuntime[defineModel_selectedSwitches]
    error_y1 = [np.std(vals) for vals in errorRuntimesM[defineModel]]
    error_y5 = [np.std(vals) for vals in errorRuntimesM[defineModel_selectedSwitches]]
    plot_errorbar(x_labels, [y1, y5], [error_y1, error_y5],
                  BASELINE_LABELS, YLEN_RUNTIME, XLEN_AGG,
                  "plots/basic_runtime_vs_aggregation_errorbar.pdf",
                  fmt_list=BASELINE_MARKERS,
                  legend_bbox=LEGEND_BBOX_LINE, legend_size=LEGEND_SIZE)

    # Line chart variant (kept alongside the errorbar plot for readers
    # who prefer the plain line form). Same style as the errorbar figure.
    apply_plot_style()
    fig, ax = new_fig()
    ax.plot(x_labels, y1, ls='dashed', marker='o',
            markersize=style.marker_size, label=BASELINE_LABELS[0])
    ax.plot(x_labels, y5, ls='dashed', marker='p',
            markersize=style.marker_size, label=BASELINE_LABELS[1])
    plot_legend(ax, loc='upper center', bbox_to_anchor=LEGEND_BBOX_LINE,
                ncol=LEGEND_NCOL_2)
    ax.set_xlabel(XLEN_AGG)
    ax.set_ylabel(YLEN_RUNTIME)
    fmt_axis(ax, axis="both")
    plot_grid(ax, axis='both')
    save_fig(fig, "plots/basic_runtime_vs_aggregation.pdf")

    plot_grouped_bars(x_labels, [y1, y5], BASELINE_LABELS,
                      YLEN_FRAG, XLEN_AGG,
                      "plots/basic_runtime_vs_aggregation_bars.pdf",
                      color_indices=BASELINE_COLORS, hatch_list=BASELINE_HATCHES,
                      width=BAR_WIDTH, legend_bbox=LEGEND_BBOX_BARS,
                      legend_ncol=LEGEND_NCOL_2, legend_size=LEGEND_SIZE)

    # --- Save clean JSON ---
    summary = run.summary(
        x_labels, series_order=BASELINE_LABELS,
        y_fragments=YLEN_FRAG, y_runtime=YLEN_RUNTIME, x_label=XLEN_AGG)
    run.save("plots/baseline_data.json", extra={"summary": summary,
                                                "plot_files": [
        "plots/basic_fragments_vs_aggregation.pdf",
        "plots/basic_fragments_vs_aggregation_errorbar.pdf",
        "plots/basic_runtime_vs_aggregation.pdf",
        "plots/basic_runtime_vs_aggregation_errorbar.pdf",
        "plots/basic_runtime_vs_aggregation_bars.pdf",
    ]})


# ============================================================
# Block #1b — model comparison (4 models)
# ============================================================
