"""Block downloaded from the old main.py — see blocks/__init__.py for the registry."""
from blocks._imports import (
    BlockRun, TimeoutError, XLEN_RHO, YLEN_FRAG, YLEN_RUNTIME, _prepare_dict_list, _timeout_handler, _unpack_env, apply_constraints, create_Fragments, defineModel_selectedSwitches, env_1c_5sw_3f, np, objective, pct_labels, plot_single_bars, preProcessMappingY, preProcessMappingZ, signal, solveProblem, time,
)

def run_pct_1cluster():
    envs = [env_1c_5sw_3f]
    models = [defineModel_selectedSwitches]
    model_labels = ["FlexINA"]

    maxAggregate = 3
    ittrNum = 3
    Percentages = [0.1, 0.3, 0.5, 0.7]
    x_labels = pct_labels(Percentages)
    solve_counter = 0

    run = BlockRun("pct_1cluster", config={
        "envs": [e.__name__ for e in envs],
        "models": [m.__name__ for m in models],
        "model_labels": model_labels,
        "maxAggregate": maxAggregate,
        "ittrNum": ittrNum,
        "Percentages": Percentages,
        "T_max_2_init": 8,
        "addTime_factor": 1.0,
        "timeout_sec": 60,
    }, axis={"x": XLEN_RHO, "y_fragments": YLEN_FRAG,
             "y_runtime": YLEN_RUNTIME, "x_ticks": x_labels})

    kindsofModelsPackets = {m: [] for m in models}
    kindsofModelsRuntime = {m: [] for m in models}
    errorRuntimesM = {m: [] for m in models}
    errorPacketsM = {m: [] for m in models}

    # Total sub-solves across all percentages — computed once before the
    # loops so the [N/total] counter is stable throughout the run.
    _env_tuple = _unpack_env(env_1c_5sw_3f)
    _dict_list_len = len(_prepare_dict_list(_env_tuple[9], _env_tuple[10]))
    total_solves = (len(models) * len(Percentages)
                    * (maxAggregate - 2) * ittrNum * _dict_list_len)

    block_start = time.time()
    for modelSolve in models:
        print(f"[{modelSolve.__name__}]")
        numPackets2 = []
        RuntimeTotal2 = []
        errorRuntime = []
        errorPackets = []
        for percentage in Percentages:
            errorRuntime.append([])
            errorPackets.append([])
            envTemp = env_1c_5sw_3f
            (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
             pSwitchesNumber, numberSlotsSwitches, workersTopology,
             pWorkerPorts, workersNumber, numAllFrags,
             fragmentsofEachWorker, totalWorkers, stepsToSwitches,
             cutPorts, selectedSwitches, clusters) = _unpack_env(envTemp)

            dict_list = _prepare_dict_list(fragmentsofEachWorker, totalWorkers)
            x_label = f"{int(round(percentage * 100))}%"
            for maxAggregation in range(2, maxAggregate):
                avgPacket = []
                avgRuntime = []
                for ittr in range(ittrNum):
                    T_max_1 = 0
                    T_max_2 = 8
                    addTime = int(1 * T_max_2)
                    Y_Used = set()
                    Z_Used = set()
                    numPackets = 0
                    RuntimeTotal = 0
                    construction_total = 0.0
                    solve_total = 0.0
                    statuses = []
                    timed_out_any = False
                    for items in range(0, len(dict_list)):
                        fragmentsofEachWorker = dict_list[items]
                        solve_counter += 1
                        timed_out = False
                        signal.signal(signal.SIGALRM, _timeout_handler)
                        signal.alarm(60)
                        tc0 = time.time()
                        try:
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
                            print(f"  [{solve_counter}/{total_solves}] ", end="", flush=True)
                            ts0 = time.time()
                            (Y_Value_One, Z_Value_One, Y_Used, Z_Used,
                             numPacket, Runtime, status) = \
                                solveProblem(model, Y_Used, Z_Used)
                            solve_total += time.time() - ts0
                            statuses.append(status)
                        except TimeoutError:
                            signal.alarm(0)
                            # Solver ran for (close to) the full 60s SIGALRM
                            # window — record that real elapsed time instead
                            # of 0, so runtime statistics stay honest.
                            # Previously `Runtime = 0` hid the actual cost
                            # of timed-out solves.
                            Runtime = time.time() - tc0
                            solve_total += Runtime
                            print(f"  [{solve_counter}/{total_solves}] TIMEOUT "
                                  f"after {Runtime:.2f}s (skipped)", flush=True)
                            timed_out = True
                            timed_out_any = True
                            numPacket = 0
                            statuses.append("timeout")
                        finally:
                            signal.alarm(0)

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
                        timed_out_any=timed_out_any)
            numPackets2.append(sum(avgPacket) / len(avgPacket))
            RuntimeTotal2.append(sum(avgRuntime) / len(avgRuntime))
        kindsofModelsPackets[modelSolve] = numPackets2
        kindsofModelsRuntime[modelSolve] = RuntimeTotal2
        errorRuntimesM[modelSolve] = errorRuntime
        errorPacketsM[modelSolve] = errorPackets

    print(f"  done in {time.time() - block_start:.1f}s")
    print("Packets:", kindsofModelsPackets)
    print("Runtime:", kindsofModelsRuntime)

    # All sub-solves across all percentages are finished.
    print(f"\n>>> All {total_solves} sub-solves complete "
          f"(solve_counter={solve_counter}). Block finished in "
          f"{time.time() - block_start:.1f}s — proceeding to plots.")

    # --- Plots (consistent style: percent ticks + ρ label + errorbars) ---
    pkt_series = kindsofModelsPackets[defineModel_selectedSwitches]
    rt_series = kindsofModelsRuntime[defineModel_selectedSwitches]
    pkt_std = [np.std(vals) for vals in errorPacketsM[defineModel_selectedSwitches]]
    rt_std = [np.std(vals) for vals in errorRuntimesM[defineModel_selectedSwitches]]

    plot_single_bars(x_labels, pkt_series,
                     YLEN_FRAG, XLEN_RHO,
                     "plots/percentage_1cluster_fragments.pdf",
                     color_index=1, hatch='.', std=pkt_std)

    plot_single_bars(x_labels, rt_series,
                     YLEN_RUNTIME, XLEN_RHO,
                     "plots/percentage_1cluster_runtime.pdf",
                     color_index=1, hatch='.', std=rt_std)

    # --- Save clean JSON ---
    summary = run.summary(
        x_labels, series_order=model_labels,
        y_fragments=YLEN_FRAG, y_runtime=YLEN_RUNTIME, x_label=XLEN_RHO)
    run.save("plots/pct_1cluster_data.json", extra={"summary": summary,
                                                    "plot_files": [
        "plots/percentage_1cluster_fragments.pdf",
        "plots/percentage_1cluster_runtime.pdf",
    ]})
