"""Block downloaded from the old main.py — see blocks/__init__.py for the registry."""
from blocks._imports import (
    BAR_WIDTH, BlockRun, LEGEND_BBOX_BARS, LEGEND_BBOX_LINE, LEGEND_NCOL_4, LEGEND_SIZE, MODEL_COLORS, MODEL_HATCHES, MODEL_LABELS, MODEL_MARKERS, XLEN_AGG, XLEN_FRAGS, XLEN_SLOTS, XLEN_TOPOLOGY, YLEN_FRAG, YLEN_RUNTIME, YLEN_RUNTIME_LOG, _prepare_dict_list, _unpack_env, apply_constraints, create_Fragments, defineModel_ATP, defineModel_ATP_GRID, defineModel_GRID, defineModel_selectedSwitches, env_2c_10sw_3f, np, objective, plot_errorbar, plot_grouped_bars, plot_single_bars, preProcessMappingY, preProcessMappingZ, solveProblem, time,
)

def run_models():
    envs = [env_2c_10sw_3f]
    models = [defineModel_ATP, defineModel_GRID, defineModel_ATP_GRID,
              defineModel_selectedSwitches]
    model_labels = MODEL_LABELS                    # 4-model style set

    maxAggregate = 4
    ittrNum = 3
    percentage = 0.6
    solve_counter = 0

    x_labels = [str(a) for a in range(1, maxAggregate)]
    run = BlockRun("models", config={
        "envs": [e.__name__ for e in envs],
        "models": [m.__name__ for m in models],
        "model_labels": model_labels,
        "maxAggregate": maxAggregate,
        "ittrNum": ittrNum,
        "percentage": percentage,
        "T_max_2_init": 8,
        "addTime_factor": 1.0,
        # Synthetic scalability rows (hardcoded in the original block;
        # preserved for continuity — the per-iteration observations above
        # don't directly back these two plots, so the data is stored here
        # to keep them reproducible from JSON alone).
        "scalability_tree": {
            "labels": ["8", "16", "24"],
            "runtime_s": [0.23863816261291504, 0.48981642723083496,
                           0.5911757946014404]},
        "scalability_fragments": {
            "labels": ["8", "16", "24", "32", "40"],
            "runtime_s": [0.23863816261291504, 0.48981642723083496,
                           0.5911757946014404, 0.8037800788879395,
                           1.414642095565796]},
    }, axis={"x": XLEN_AGG, "y_fragments": YLEN_FRAG, "y_runtime": YLEN_RUNTIME,
             "x_ticks": x_labels})

    errorRuntimesM = {}
    errorPacketsM = {}
    kindsofModelsPackets = {}
    kindsofModelsRuntime = {}

    # Total sub-solves across all envs — computed once before the loops so
    # the [N/total] counter doesn't shift when envs have different
    # dict_list sizes.
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

    # --- Plots (consistent style) ---
    # Aggregation axis — primary comparison.
    C_2 = kindsofModelsPackets[defineModel_ATP]
    C_3 = kindsofModelsPackets[defineModel_GRID]
    C_4 = kindsofModelsPackets[defineModel_ATP_GRID]
    C_5 = kindsofModelsPackets[defineModel_selectedSwitches]

    plot_grouped_bars(x_labels, [C_2, C_3, C_4, C_5], MODEL_LABELS,
                      YLEN_FRAG, XLEN_AGG,
                      "plots/aggregation_fragments.pdf",
                      color_indices=MODEL_COLORS, hatch_list=MODEL_HATCHES,
                      width=BAR_WIDTH, legend_bbox=LEGEND_BBOX_BARS,
                      legend_ncol=LEGEND_NCOL_4, legend_size=LEGEND_SIZE)

    y2 = kindsofModelsRuntime[defineModel_ATP]
    y3 = kindsofModelsRuntime[defineModel_GRID]
    y4 = kindsofModelsRuntime[defineModel_ATP_GRID]
    y5 = kindsofModelsRuntime[defineModel_selectedSwitches]
    e2 = [np.std(vals) for vals in errorRuntimesM[defineModel_ATP]]
    e3 = [np.std(vals) for vals in errorRuntimesM[defineModel_GRID]]
    e4 = [np.std(vals) for vals in errorRuntimesM[defineModel_ATP_GRID]]
    e5 = [np.std(vals) for vals in errorRuntimesM[defineModel_selectedSwitches]]
    plot_errorbar(x_labels, [y2, y3, y4, y5], [e2, e3, e4, e5],
                  MODEL_LABELS, YLEN_RUNTIME, XLEN_AGG,
                  "plots/aggregation_runtime_errorbar.pdf",
                  fmt_list=MODEL_MARKERS,
                  legend_bbox=LEGEND_BBOX_LINE, legend_size=LEGEND_SIZE)

    # Slot-axis (same data, retitled). Use XLEN_SLOTS.
    plot_grouped_bars(x_labels, [C_2, C_3, C_4, C_5], MODEL_LABELS,
                      YLEN_FRAG, XLEN_SLOTS,
                      "plots/aggregation_fragments_vs_slots.pdf",
                      color_indices=MODEL_COLORS, hatch_list=MODEL_HATCHES,
                      width=BAR_WIDTH, legend_bbox=LEGEND_BBOX_BARS,
                      legend_ncol=LEGEND_NCOL_4, legend_size=LEGEND_SIZE)
    plot_errorbar(x_labels, [y2, y3, y4, y5], [e2, e3, e4, e5],
                  MODEL_LABELS, YLEN_RUNTIME, XLEN_SLOTS,
                  "plots/aggregation_runtime_vs_slots_errorbar.pdf",
                  fmt_list=MODEL_MARKERS,
                  legend_bbox=LEGEND_BBOX_LINE, legend_size=LEGEND_SIZE)

    # Topology-axis (same data, relabeled x ticks).
    topo_labels = ['tree', '1 Cluster', '2 Clusters']
    plot_grouped_bars(topo_labels, [C_2, C_3, C_4, C_5], MODEL_LABELS,
                      YLEN_FRAG, XLEN_TOPOLOGY,
                      "plots/aggregation_fragments_vs_topology.pdf",
                      color_indices=MODEL_COLORS, hatch_list=MODEL_HATCHES,
                      width=BAR_WIDTH, legend_bbox=LEGEND_BBOX_BARS,
                      legend_ncol=LEGEND_NCOL_4, legend_size=LEGEND_SIZE)
    plot_errorbar(topo_labels, [y2, y3, y4, y5], [e2, e3, e4, e5],
                  MODEL_LABELS, YLEN_RUNTIME, XLEN_TOPOLOGY,
                  "plots/aggregation_runtime_vs_topology_errorbar.pdf",
                  fmt_list=MODEL_MARKERS,
                  legend_bbox=LEGEND_BBOX_LINE, legend_size=LEGEND_SIZE)
    plot_grouped_bars(topo_labels, [y2, y3, y4, y5], MODEL_LABELS,
                      YLEN_RUNTIME_LOG, XLEN_TOPOLOGY,
                      "plots/aggregation_runtime_vs_topology_logscale.pdf",
                      color_indices=MODEL_COLORS, hatch_list=MODEL_HATCHES,
                      width=BAR_WIDTH, legend_bbox=LEGEND_BBOX_BARS,
                      legend_ncol=LEGEND_NCOL_4, legend_size=LEGEND_SIZE,
                      log_scale=True)

    # Scalability (synthetic rows from config). Same style as other
    # single-series bar charts.
    tree_cfg = run.config["scalability_tree"]
    plot_single_bars(tree_cfg["labels"], tree_cfg["runtime_s"],
                    YLEN_RUNTIME, XLEN_FRAGS,
                    "plots/aggregation_scalability_tree.pdf",
                    color_index=4, hatch='/')
    frag_cfg = run.config["scalability_fragments"]
    plot_single_bars(frag_cfg["labels"], frag_cfg["runtime_s"],
                    YLEN_RUNTIME, XLEN_FRAGS,
                    "plots/aggregation_scalability_fragments.pdf",
                    color_index=9, hatch='.')

    # --- Save clean JSON ---
    summary = run.summary(
        x_labels, series_order=MODEL_LABELS,
        y_fragments=YLEN_FRAG, y_runtime=YLEN_RUNTIME, x_label=XLEN_AGG)
    run.save("plots/models_data.json", extra={"summary": summary,
                                              "plot_files": [
        "plots/aggregation_fragments.pdf",
        "plots/aggregation_runtime_errorbar.pdf",
        "plots/aggregation_fragments_vs_slots.pdf",
        "plots/aggregation_runtime_vs_slots_errorbar.pdf",
        "plots/aggregation_fragments_vs_topology.pdf",
        "plots/aggregation_runtime_vs_topology_errorbar.pdf",
        "plots/aggregation_runtime_vs_topology_logscale.pdf",
        "plots/aggregation_scalability_tree.pdf",
        "plots/aggregation_scalability_fragments.pdf",
    ]})


# ============================================================
# Block #1b-sparse — model comparison (4 models, sparse-slot env)
# ============================================================
# Mirror of run_models() over env_2c_10sw_3f_sparse — the 2-cluster
# reference env with the legacy sparse aggregation-slot mask (switches
# 2, 4, 6, 7, 9 carry no slot), reproducing the behaviour archived in
# archive/Untitled.py's env_2Clusters. Plots and JSON log use the
# models_sparse_* prefix so they never collide with the run_models
