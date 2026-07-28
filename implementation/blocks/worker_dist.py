from blocks._imports import (
    BAR_WIDTH, BlockRun, LEGEND_BBOX_BARS, LEGEND_BBOX_LINE, LEGEND_NCOL_4, LEGEND_SIZE, MODEL_COLORS, MODEL_HATCHES, MODEL_LABELS, MODEL_MARKERS, XLEN_DISTRIBUTION, YLEN_FRAG, YLEN_RUNTIME, YLEN_RUNTIME_LOG, _prepare_dict_list, _unpack_env, apply_constraints, create_Fragments, defineModel_ATP, defineModel_ATP_GRID, defineModel_GRID, defineModel_selectedSwitches, env_2c_10sw_3f, env_2c_10sw_skew1, env_2c_10sw_skew15, np, objective, plot_errorbar, plot_grouped_bars, preProcessMappingY, preProcessMappingZ, solveProblem, time,
)

def run_worker_dist():
    envs = [env_2c_10sw_3f, env_2c_10sw_skew15, env_2c_10sw_skew1]
    models = [defineModel_ATP, defineModel_GRID, defineModel_ATP_GRID,
              defineModel_selectedSwitches]
    model_labels = MODEL_LABELS
    x_labels = ['Uniform', 'Zipf 1.5', 'Zipf 2']

    maxAggregate = 3
    ittrNum = 3
    percentage = 0.6
    solve_counter = 0

    run = BlockRun("worker_dist", config={
        "envs": [e.__name__ for e in envs],
        "models": [m.__name__ for m in models],
        "model_labels": model_labels,
        "maxAggregate": maxAggregate,
        "ittrNum": ittrNum,
        "percentage": percentage,
        "T_max_2_init": 8,
        "addTime_factor": 1.0,
        "x_labels": x_labels,
    }, axis={"x": XLEN_DISTRIBUTION, "y_fragments": YLEN_FRAG,
             "y_runtime": YLEN_RUNTIME, "x_ticks": x_labels})

    errorRuntimesM = {}
    errorPacketsM = {}
    kindsofModelsPackets = {}
    kindsofModelsRuntime = {}

    _solve_per_env = {
        e: len(_prepare_dict_list(_unpack_env(e)[9], _unpack_env(e)[10]))
        for e in envs
    }
    total_solves = (len(models) * len(envs) * (maxAggregate - 2)
                    * ittrNum * sum(_solve_per_env.values()))

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
            x_label = x_labels[envs.index(envTemp)]
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
        errorRuntimesM[modelSolve] = errorRuntime
        errorPacketsM[modelSolve] = errorPackets
        kindsofModelsPackets[modelSolve] = numPackets2
        kindsofModelsRuntime[modelSolve] = RuntimeTotal2

    print(f"  done in {time.time() - block_start:.1f}s")
    print("Packets:", kindsofModelsPackets)
    print("Runtime:", kindsofModelsRuntime)

    print(f"\n>>> All {total_solves} sub-solves complete "
          f"(solve_counter={solve_counter}). Block finished in "
          f"{time.time() - block_start:.1f}s — proceeding to plots.")

    C_2 = kindsofModelsPackets[defineModel_ATP]
    C_3 = kindsofModelsPackets[defineModel_GRID]
    C_4 = kindsofModelsPackets[defineModel_ATP_GRID]
    C_5 = kindsofModelsPackets[defineModel_selectedSwitches]

    plot_grouped_bars(x_labels, [C_2, C_3, C_4, C_5], MODEL_LABELS,
                      YLEN_FRAG, XLEN_DISTRIBUTION,
                      "plots/distribution_fragments.pdf",
                      color_indices=MODEL_COLORS, hatch_list=MODEL_HATCHES,
                      width=BAR_WIDTH, legend_bbox=LEGEND_BBOX_BARS,
                      legend_ncol=LEGEND_NCOL_4, legend_size=LEGEND_SIZE)

    y2 = kindsofModelsRuntime[defineModel_ATP]
    y3 = kindsofModelsRuntime[defineModel_GRID]
    y4 = kindsofModelsRuntime[defineModel_ATP_GRID]
    y5 = kindsofModelsRuntime[defineModel_selectedSwitches]

    plot_grouped_bars(x_labels, [y2, y3, y4, y5], MODEL_LABELS,
                      YLEN_RUNTIME_LOG, XLEN_DISTRIBUTION,
                      "plots/distribution_runtime.pdf",
                      color_indices=MODEL_COLORS, hatch_list=MODEL_HATCHES,
                      width=BAR_WIDTH, legend_bbox=LEGEND_BBOX_BARS,
                      legend_ncol=LEGEND_NCOL_4, legend_size=LEGEND_SIZE,
                      log_scale=True)

    e2 = [np.std(vals) for vals in errorRuntimesM[defineModel_ATP]]
    e3 = [np.std(vals) for vals in errorRuntimesM[defineModel_GRID]]
    e4 = [np.std(vals) for vals in errorRuntimesM[defineModel_ATP_GRID]]
    e5 = [np.std(vals) for vals in errorRuntimesM[defineModel_selectedSwitches]]
    plot_errorbar(x_labels, [y2, y3, y4, y5], [e2, e3, e4, e5],
                  MODEL_LABELS, YLEN_RUNTIME, XLEN_DISTRIBUTION,
                  "plots/distribution_runtime_errorbar.pdf",
                  fmt_list=MODEL_MARKERS,
                  legend_bbox=LEGEND_BBOX_LINE, legend_size=LEGEND_SIZE)

    summary = run.summary(x_labels, series_order=MODEL_LABELS,
                          y_fragments=YLEN_FRAG, y_runtime=YLEN_RUNTIME,
                          x_label=XLEN_DISTRIBUTION)
    run.save("plots/worker_dist_data.json", extra={"summary": summary,
                                                   "plot_files": [
        "plots/distribution_fragments.pdf",
        "plots/distribution_runtime.pdf",
        "plots/distribution_runtime_errorbar.pdf",
    ]})
