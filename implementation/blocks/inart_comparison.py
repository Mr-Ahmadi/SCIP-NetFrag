"""Block downloaded from the old main.py — see blocks/__init__.py for the registry."""
from blocks._imports import (
    BAR_WIDTH, BlockRun, INART_COLORS, INART_HATCHES, INART_LABELS, INART_MARKERS, LEGEND_BBOX_BARS, LEGEND_BBOX_LINE, LEGEND_NCOL_2, LEGEND_SIZE, XLEN_TOPOLOGY, YLEN_FRAG, YLEN_RUNTIME, _prepare_dict_list, _unpack_env, apply_constraints, apply_constraints_InArt, apply_plot_style, create_Fragments, defineModel_InArt, defineModel_selectedSwitches, env_1c_5sw_3f, env_2c_10sw_3f, env_2c_10sw_uneven, env_3c_14sw_4f, fmt_axis, new_fig, np, objective, plot_errorbar, plot_grid, plot_grouped_bars, plot_legend, preProcessMappingY, preProcessMappingZ, save_fig, solveProblem, style, time,
)
from blocks._flexina_helpers import _solve_flexina_once, _no_aggregation_packets


def run_inart_comparison():
    """
    InArt vs FlexINA across multiple topologies.

    Runs both solvers on the same set of envs and produces three plots
    whose x-axis is the topology (one bar/point per env per model):
      * fragments (grouped bars)
      * runtime with errorbars (mean +- std over ittrs)
      * runtime line chart (style-equivalent to baseline's runtime line)

    Env selection spans the topology/load axes so the comparison isn't
    biased to one shape: 1-cluster reference, 2-cluster reference, an
    uneven-load 2-cluster variant, and the 3-cluster fabric.
    """
    envs = [
        env_1c_5sw_3f,        # 1-cluster reference
        env_2c_10sw_3f,       # 2-cluster reference
        env_2c_10sw_uneven,   # 2-cluster, uneven load
        env_3c_14sw_4f,       # 3-cluster fabric
    ]
    # Short human-readable label per env — used as the x-axis in the plots.
    x_labels = [e.__name__ for e in envs]
    models = [defineModel_InArt, defineModel_selectedSwitches]
    model_labels = INART_LABELS                    # ['InArt', 'FlexINA']

    maxAggregate = 3
    ittrNum = 3
    percentage = 0.6
    # Smaller ρ for FlexINA: fewer candidate switches = smaller MILP.
    # InArt explores the full switch set (uses `percentage`), while
    # defineModel_selectedSwitches (FlexINA) only retains the top ρ
    # fraction — so a smaller ρ here is the main speed lever.
    percentage_flexina = 0.5
    SOLVE_TIMEOUT_S = 60
    solve_counter = 0
    total_solves = (len(models) * len(envs)
                    * (maxAggregate - 2) * ittrNum
                    * sum(len(_prepare_dict_list(*_unpack_env(e)[9:11]))
                          for e in envs))

    run = BlockRun("inart", config={
        "envs": [e.__name__ for e in envs],
        "models": [m.__name__ for m in models],
        "model_labels": model_labels,
        "maxAggregate": maxAggregate,
        "ittrNum": ittrNum,
        "percentage": percentage,
        "percentage_flexina": percentage_flexina,
        "T_max_2_init": 8,
        "addTime_factor": 1.0,
        "solve_timeout_s": SOLVE_TIMEOUT_S,
        "note": ("Timed-out solves now record real elapsed time (not 0); "
                 "FlexINA uses percentage_flexina (smaller ρ) for speed."),
    }, axis={"x": XLEN_TOPOLOGY, "y_fragments": YLEN_FRAG,
             "y_runtime": YLEN_RUNTIME, "x_ticks": x_labels})

    errorRuntimesM = {}
    errorPacketsM = {}
    kindsofModelsPackets = {}
    kindsofModelsRuntime = {}

    block_start = time.time()
    for modelSolve in models:
        print(f"[{modelSolve.__name__}]")
        numPackets2 = []
        RuntimeTotal2 = []
        errorRuntime = []
        errorPackets = []
        for envTemp in envs:
            errorRuntime.append([])
            errorPackets.append([])
            (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
             pSwitchesNumber, numberSlotsSwitches, workersTopology,
             pWorkerPorts, workersNumber, numAllFrags,
             fragmentsofEachWorker, totalWorkers, stepsToSwitches,
             cutPorts, selectedSwitches, clusters) = _unpack_env(envTemp)

            dict_list = _prepare_dict_list(fragmentsofEachWorker, totalWorkers)
            x_label = envTemp.__name__
            for maxAggregation in range(2, maxAggregate):
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
                        solve_counter += 1
                        env_name = envTemp.__name__
                        print(f"  [{solve_counter}/{total_solves}] "
                              f"{modelSolve.__name__:30s} {env_name:22s} "
                              f"ittr={ittr} slot={items} ... ",
                              end="", flush=True)
                        timed_out = False
                        tc0 = time.time()
                        try:
                            subSets, allofSubsets, usefulIntervalTime, fragments = \
                                create_Fragments(fragmentsofEachWorker, T_max_1, T_max_2, maxAggregation)
                            print(f"createFragmentsOK:{time.time()-tc0:.2f}s ", end="", flush=True)
                            t1 = time.time()
                            Y_Used = preProcessMappingY(Y_Used, allofSubsets[0])
                            Z_Used = preProcessMappingZ(Z_Used, subSets, usefulIntervalTime)
                            (model, Z_Variables, Y_Variables, Prm1, Prm2,
                             clusterSets, switchinClusters, AllClusters) = \
                                modelSolve(allofSubsets, pSwitchesTopology, pSwitchPorts,
                                           T_max_1, T_max_2, workersTopology,
                                           fragmentsofEachWorker, pWorkerPorts,
                                           subSets, numberSlotsSwitches, usefulIntervalTime,
                                           Y_Used, Z_Used, maxAggregation, stepsToSwitches,
                                           cutPorts, selectedSwitches,
                                           percentage if modelSolve == defineModel_InArt
                                                     else percentage_flexina,
                                           clusters)
                            print(f"modelBuilt:{time.time()-t1:.2f}s Y={len(Y_Variables)} ", end="", flush=True)
                            if modelSolve == defineModel_InArt:
                                apply_constraints_InArt(
                                    modelSolve, pSwitchesTopology, numberSlotsSwitches,
                                    usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                                    Z_Used, Y_Used, neighborsofEachSwitch, pSwitchPorts,
                                    workersTopology, fragmentsofEachWorker, pWorkerPorts,
                                    numAllFrags, clusterSets, switchinClusters, AllClusters,
                                    Y_Variables, Z_Variables)
                            else:
                                apply_constraints(
                                    modelSolve, pSwitchesTopology, numberSlotsSwitches,
                                    usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                                    Z_Used, Y_Used, neighborsofEachSwitch, pSwitchPorts,
                                    workersTopology, fragmentsofEachWorker, pWorkerPorts,
                                    numAllFrags, clusterSets, switchinClusters, AllClusters,
                                    Y_Variables, Z_Variables)
                            objective(Y_Variables, model)
                            construction_total += time.time() - tc0
                            ts0 = time.time()
                            (Y_Value_One, Z_Value_One, Y_Used, Z_Used,
                             numPacket, Runtime, status) = \
                                solveProblem(model, Y_Used, Z_Used,
                                             time_limit=SOLVE_TIMEOUT_S)
                            solve_total += time.time() - ts0
                            statuses.append(status)
                            if status == "timelimit":
                                # The solver ran for the full timeout window —
                                # record that real time, not 0, so the
                                # computed runtime statistics stay honest.
                                # The fragment count drops to 0 only because
                                # we have no usable primal; the time itself
                                # was still spent. (main.py:1780 previously
                                # zeroed both numPacket and Runtime, hiding
                                # the actual cost of timed-out solves.)
                                timed_out = True
                                numPacket = 0
                                print(f"TIMELIMIT after {Runtime:.2f}s "
                                      f"(cap {SOLVE_TIMEOUT_S}s)")
                            else:
                                print(f"{status} pkts={numPacket} {Runtime:.3f}s")
                        except (IndexError, KeyError, ValueError,
                                AssertionError) as e:
                            # Some dict_list slices produce an empty/infeasible
                            # SCIP model. The construction work up to the
                            # failure was still spent — record that real time
                            # so runtime statistics stay honest. (Previously
                            # `Runtime = 0` hid the actual cost of failed
                            # sub-solves in this block too.)
                            Runtime = time.time() - tc0
                            solve_total += Runtime
                            print(f"ERROR ({type(e).__name__}: {e}) "
                                  f"skipped after {Runtime:.2f}s")
                            timed_out = True
                            numPacket = 0
                            statuses.append("skip")

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
                        model=model_labels[models.index(modelSolve)],
                        env=envTemp.__name__, x=x_label, ittr=ittr,
                        packets=numPackets, runtime=RuntimeTotal,
                        construction_time_s=construction_total,
                        solve_time_s=solve_total,
                        status=",".join(statuses),
                        timed_out_any=any(s in ("timelimit", "skip")
                                          for s in statuses))
            # Average over the per-aggregation/ittr observations for this env.
            numPackets2.append(sum(avgPacket) / max(1, len(avgPacket)))
            RuntimeTotal2.append(sum(avgRuntime) / max(1, len(avgRuntime)))
        errorRuntimesM[modelSolve] = errorRuntime
        errorPacketsM[modelSolve] = errorPackets
        kindsofModelsPackets[modelSolve] = numPackets2
        kindsofModelsRuntime[modelSolve] = RuntimeTotal2

        print(f"  done in {time.time() - block_start:.1f}s")
        print("Packets:", kindsofModelsPackets)
        print("Runtime:", kindsofModelsRuntime)

    # All sub-solves across all models/envs are finished.
    print(f"\n>>> All {total_solves} sub-solves complete "
          f"(solve_counter={solve_counter}). Block finished in "
          f"{time.time() - block_start:.1f}s — proceeding to plots.")

    # --- Plots (consistent style; x-axis = topology) ---
    C_inart = kindsofModelsPackets[defineModel_InArt]
    C_flex = kindsofModelsPackets[defineModel_selectedSwitches]

    plot_grouped_bars(x_labels, [C_inart, C_flex], INART_LABELS,
                      YLEN_FRAG, XLEN_TOPOLOGY,
                      "plots/inart_vs_flexina_fragments.pdf",
                      color_indices=INART_COLORS, hatch_list=INART_HATCHES,
                      width=BAR_WIDTH, legend_bbox=LEGEND_BBOX_BARS,
                      legend_ncol=LEGEND_NCOL_2, legend_size=LEGEND_SIZE)

    y_inart = kindsofModelsRuntime[defineModel_InArt]
    y_flex = kindsofModelsRuntime[defineModel_selectedSwitches]
    e_inart = [np.std(vals) for vals in errorRuntimesM[defineModel_InArt]]
    e_flex = [np.std(vals) for vals in errorRuntimesM[defineModel_selectedSwitches]]
    plot_errorbar(x_labels, [y_inart, y_flex], [e_inart, e_flex],
                  INART_LABELS, YLEN_RUNTIME, XLEN_TOPOLOGY,
                  "plots/inart_vs_flexina_runtime_errorbar.pdf",
                  fmt_list=INART_MARKERS,
                  legend_bbox=LEGEND_BBOX_LINE, legend_size=LEGEND_SIZE)

    # Line chart variant — same as baseline's basic_runtime_vs_aggregation.
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
    fmt_axis(ax, axis='both')
    plot_grid(ax, axis='both')
    save_fig(fig, "plots/inart_vs_flexina_runtime.pdf")

    # --- Save clean JSON ---
    summary = run.summary(x_labels, series_order=INART_LABELS,
                          y_fragments=YLEN_FRAG, y_runtime=YLEN_RUNTIME,
                          x_label=XLEN_TOPOLOGY)
    run.save("plots/inart_data.json", extra={"summary": summary,
                                              "plot_files": [
        "plots/inart_vs_flexina_fragments.pdf",
        "plots/inart_vs_flexina_runtime_errorbar.pdf",
        "plots/inart_vs_flexina_runtime.pdf",
    ]})
