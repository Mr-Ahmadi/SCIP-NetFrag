"""
main.py — entry point for all experiment blocks.

User selects which block to run at startup.
"""
import sys
import time
import signal

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

from sim import (
    env_1Cluster_Test,
    env_2Clusters,
    env_2Clusters_Zipf15,
    env_2Clusters_Zipf2,
    env_2Clusters_Percentages,
    defineModel,
    defineModel_ATP,
    defineModel_GRID,
    defineModel_ATP_GRID,
    defineModel_selectedSwitches,
    defineModel_InArt,
    create_Fragments,
    preProcessMappingY,
    preProcessMappingZ,
    TimeoutError,
    _timeout_handler,
)
from sim.runner import apply_constraints, apply_constraints_basic, apply_constraints_InArt
from sim.solver import objective, solveProblem
from sim.plots import plot_grouped_bars, plot_errorbar, plot_single_bars


BLOCKS = {
    "baseline":     "Block #1: baseline comparison",
    "models":       "Block #1b: model comparison (4 models, 2-cluster env)",
    "pct_2cluster": "Block #1c: switch percentage (2-cluster env)",
    "pct_1cluster": "Block #1d: switch percentage (1-cluster env)",
    "start_time":   "Block #2: start time experiment",
    "time_window":  "Block #3: time window experiment",
    "worker_dist":  "Block #4: worker distribution experiment",
    "inart":        "Block #5: InArt vs FlexINA comparison",
}


def _prompt_block():
    print("\n=== Experiment Blocks ===\n")
    for key, desc in BLOCKS.items():
        print(f"  {key:15s} — {desc}")
    print()
    choice = input("Enter block to run [baseline]: ").strip()
    if not choice:
        choice = "baseline"
    if choice not in BLOCKS:
        print(f"Unknown block '{choice}', defaulting to 'baseline'")
        choice = "baseline"
    return choice


def _unpack_env(envTemp):
    return envTemp(state='Optimaze')


def _prepare_dict_list(fragmentsofEachWorker, totalWorkers):
    finalWorkers = {k: totalWorkers[k] for k in fragmentsofEachWorker}
    num_dicts = len(next(iter(finalWorkers.values())))
    return [{k: [v[i]] for k, v in finalWorkers.items()} for i in range(num_dicts)]


# ============================================================
# Block #1 — baseline comparison
# ============================================================

def run_baseline():
    envs = [env_1Cluster_Test]
    models = [defineModel, defineModel_selectedSwitches]

    maxAggregate = 4
    ittrNum = 3
    percentage = 0.5
    errorRuntimesM = {}
    errorPacketsM = {}
    kindsofModelsPackets = {}
    kindsofModelsRuntime = {}
    solve_counter = 0

    for modelSolve in models:
        print(f"[{modelSolve.__name__}]")
        block_start = time.time()
        for envTemp in envs:
            (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
             pSwitchesNumber, numberSlotsSwitches, workersTopology,
             pWorkerPorts, workersNumber, numAllFrags,
             fragmentsofEachWorker, totalWorkers, stepsToSwitches,
             cutPorts, selectedSwitches, clusters) = _unpack_env(envTemp)

            dict_list = _prepare_dict_list(fragmentsofEachWorker, totalWorkers)
            total_solves = len(models) * len(envs) * (maxAggregate - 1) * ittrNum * len(dict_list)

            numPackets2 = []
            RuntimeTotal2 = []
            errorRuntime = []
            errorPackets = []
            for maxAggregation in range(1, maxAggregate):
                errorRuntime.append([])
                errorPackets.append([])
                for ittr in range(ittrNum):
                    T_max_1 = 0
                    T_max_2 = 8
                    addTime = int(1 * T_max_2)
                    Y_Used = []
                    Z_Used = []
                    numPackets = 0
                    RuntimeTotal = 0
                    avgPacket = []
                    avgRuntime = []
                    for items in range(0, len(dict_list)):
                        fragmentsofEachWorker = dict_list[items]
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
                        solve_counter += 1
                        print(f"  [{solve_counter}/{total_solves}] ", end="", flush=True)
                        Y_Value_One, Z_Value_One, Y_Used, Z_Used, numPacket, Runtime, status = \
                            solveProblem(model, Y_Used, Z_Used)
                        T_max_1 += addTime
                        T_max_2 += addTime
                        numPackets += numPacket
                        RuntimeTotal += Runtime
                    avgPacket.append(numPackets)
                    avgRuntime.append(RuntimeTotal)
                    errorRuntime[-1].append(RuntimeTotal)
                    errorPackets[-1].append(numPackets)
                numPackets2.append(sum(avgPacket) / len(avgPacket))
                RuntimeTotal2.append(sum(avgRuntime) / len(avgRuntime))
            kindsofModelsPackets[modelSolve] = numPackets2
            kindsofModelsRuntime[modelSolve] = RuntimeTotal2
            errorRuntimesM[modelSolve] = errorRuntime
            errorPacketsM[modelSolve] = errorPackets

    print(f"  done in {time.time() - block_start:.1f}s")
    print("Packets:", kindsofModelsPackets)
    print("Runtime:", kindsofModelsRuntime)

    # --- Plots ---
    labels = ['1', '2', '3']
    C_1 = kindsofModelsPackets[defineModel]
    C_5 = kindsofModelsPackets[defineModel_selectedSwitches]

    plot_grouped_bars(labels, [C_1, C_5], ['optimal', 'FlexINA'],
                      '# fragments', 'max. per switch agg.',
                      "plots/basic_fragments_vs_aggregation.pdf",
                      color_indices=[17, 1], hatch_list=['+', '.'],
                      legend_bbox=(1, 1), legend_ncol=2, legend_size=16)

    error_C1 = [np.std(vals) for vals in errorPacketsM[defineModel]]
    error_C5 = [np.std(vals) for vals in errorPacketsM[defineModel_selectedSwitches]]
    plot_errorbar(labels, [C_1, C_5], [error_C1, error_C5],
                  ['optimal', 'FlexINA'], '# fragments', 'max. per switch agg.',
                  "plots/basic_fragments_vs_aggregation_errorbar.pdf",
                  fmt_list=['o--', 'p--'], legend_bbox=(0.3, 1), legend_size=16)

    y1 = kindsofModelsRuntime[defineModel]
    y5 = kindsofModelsRuntime[defineModel_selectedSwitches]
    fig, ax = plt.subplots(figsize=(8, 6))
    plt.plot(labels, y1, ls='dashed', marker='o', markersize=10, label='optimal')
    plt.plot(labels, y5, ls='dashed', marker='p', markersize=10, label='FlexINA')
    plt.legend(loc='upper center', bbox_to_anchor=(0.3, 1), ncol=2, prop={'size': 16})
    plt.xlabel('max. per switch agg.')
    plt.ylabel('runtime(s)')
    formatter = ticker.ScalarFormatter(useMathText=True)
    formatter.set_powerlimits((-3, 3))
    ax.yaxis.set_major_formatter(formatter)
    fig.tight_layout()
    plt.grid(linestyle='--', linewidth=0.5)
    plt.rcParams.update({'font.size': 22})
    plt.savefig("plots/basic_runtime_vs_aggregation.pdf", bbox_inches="tight", format="pdf")
    plt.show()

    model_key = list(errorRuntimesM.keys())[0]
    flex_key = list(errorRuntimesM.keys())[1]
    error_y1 = [np.std(vals) for vals in errorRuntimesM[model_key]]
    error_y5 = [np.std(vals) for vals in errorRuntimesM[flex_key]]
    plot_errorbar(labels, [y1, y5], [error_y1, error_y5],
                  ['optimal', 'FlexINA'], 'runtime (s)', 'max. per switch agg.',
                  "plots/basic_runtime_vs_aggregation_errorbar.pdf",
                  fmt_list=['o--', 'p--'], legend_bbox=(0.3, 1), legend_size=16)

    C_1r = kindsofModelsRuntime[defineModel]
    C_5r = kindsofModelsRuntime[defineModel_selectedSwitches]
    plot_grouped_bars(labels, [C_1r, C_5r], ['optimal', 'FlexINA'],
                      '# fragments', 'max. per switch agg.',
                      "plots/basic_runtime_vs_aggregation_bars.pdf",
                      color_indices=[17, 1], hatch_list=['+', '.'],
                      legend_bbox=(1, 1), legend_ncol=1, legend_size=12)


# ============================================================
# Block #1b — model comparison (4 models)
# ============================================================

def run_models():
    envs = [env_2Clusters]
    models = [defineModel_ATP, defineModel_GRID, defineModel_ATP_GRID,
              defineModel_selectedSwitches]

    maxAggregate = 4
    ittrNum = 3
    percentage = 0.6
    errorRuntimesM = {}
    errorPacketsM = {}
    kindsofModelsPackets = {}
    kindsofModelsRuntime = {}
    solve_counter = 0

    for modelSolve in models:
        print(f"[{modelSolve.__name__}]")
        block_start = time.time()
        for envTemp in envs:
            (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
             pSwitchesNumber, numberSlotsSwitches, workersTopology,
             pWorkerPorts, workersNumber, numAllFrags,
             fragmentsofEachWorker, totalWorkers, stepsToSwitches,
             cutPorts, selectedSwitches, clusters) = _unpack_env(envTemp)

            dict_list = _prepare_dict_list(fragmentsofEachWorker, totalWorkers)
            total_solves = len(models) * len(envs) * (maxAggregate - 1) * ittrNum * len(dict_list)
            numPackets2 = []
            RuntimeTotal2 = []
            errorRuntime = []
            errorPackets = []
            for maxAggregation in range(1, maxAggregate):
                errorRuntime.append([])
                errorPackets.append([])
                for ittr in range(ittrNum):
                    T_max_1 = 0
                    T_max_2 = 8
                    addTime = int(1 * T_max_2)
                    Y_Used = []
                    Z_Used = []
                    numPackets = 0
                    RuntimeTotal = 0
                    avgPacket = []
                    avgRuntime = []
                    for items in range(0, len(dict_list)):
                        fragmentsofEachWorker = dict_list[items]
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
                        solve_counter += 1
                        print(f"  [{solve_counter}/{total_solves}] ", end="", flush=True)
                        Y_Value_One, Z_Value_One, Y_Used, Z_Used, numPacket, Runtime, status = \
                            solveProblem(model, Y_Used, Z_Used)
                        T_max_1 += addTime
                        T_max_2 += addTime
                        numPackets += numPacket
                        RuntimeTotal += Runtime
                    avgPacket.append(numPackets)
                    avgRuntime.append(RuntimeTotal)
                    errorRuntime[-1].append(RuntimeTotal)
                    errorPackets[-1].append(numPackets)
                numPackets2.append(sum(avgPacket) / len(avgPacket))
                RuntimeTotal2.append(sum(avgRuntime) / len(avgRuntime))
            kindsofModelsPackets[modelSolve] = numPackets2
            kindsofModelsRuntime[modelSolve] = RuntimeTotal2
            errorRuntimesM[modelSolve] = errorRuntime
            errorPacketsM[modelSolve] = errorPackets

    print(f"  done in {time.time() - block_start:.1f}s")
    print("Packets:", kindsofModelsPackets)
    print("Runtime:", kindsofModelsRuntime)

    # --- Plots ---
    labels = ['1', '2', '3']
    C_2 = kindsofModelsPackets[defineModel_ATP]
    C_3 = kindsofModelsPackets[defineModel_GRID]
    C_4 = kindsofModelsPackets[defineModel_ATP_GRID]
    C_5 = kindsofModelsPackets[defineModel_selectedSwitches]

    plot_grouped_bars(labels, [C_2, C_3, C_4, C_5],
                      ['FixR-ToRS', 'FixR-AS', 'FlexR-ToRS', 'FlexINA'],
                      '# fragments', 'max. per switch agg.',
                      "plots/aggregation_fragments.pdf",
                      color_indices=[5, 9, 13, 1], hatch_list=['/', 'o', '*', '.'],
                      width=0.2, legend_bbox=(1.015, 1.11), legend_ncol=5, legend_size=14)

    y2 = kindsofModelsRuntime[defineModel_ATP]
    y3 = kindsofModelsRuntime[defineModel_GRID]
    y4 = kindsofModelsRuntime[defineModel_ATP_GRID]
    y5 = kindsofModelsRuntime[defineModel_selectedSwitches]
    e2 = [np.std(vals) for vals in errorRuntimesM[defineModel_ATP]]
    e3 = [np.std(vals) for vals in errorRuntimesM[defineModel_GRID]]
    e4 = [np.std(vals) for vals in errorRuntimesM[defineModel_ATP_GRID]]
    e5 = [np.std(vals) for vals in errorRuntimesM[defineModel_selectedSwitches]]
    plot_errorbar(labels, [y2, y3, y4, y5], [e2, e3, e4, e5],
                  ['fixR-ToRS', 'fixR-AS', 'flexR-ToRS', 'FlexINA'],
                  'runtime(s)', 'max. per switch agg.',
                  "plots/aggregation_runtime_errorbar.pdf",
                  fmt_list=['s--', '*--', '^--', 'p--'],
                  legend_bbox=(0.35, 1), legend_size=16)

    # Scalability Tree
    cmap = sns.color_palette("tab20c")
    x = np.array(["Tree", "Three_Tree", "Four_Tree"])
    y = np.array([0.23863816261291504, 0.48981642723083496, 0.5911757946014404])
    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar(x, y, color=[cmap[4]], edgecolor='black')
    for bar in bars:
        bar.set_hatch('/')
    ax.set_ylabel('Runtime(s)')
    ax.set_xlabel('Number of fragments')
    ax.set_xticks(np.arange(len(x)))
    ax.set_xticklabels(x)
    ax.grid(axis='y', linestyle='--', linewidth=0.5)
    formatter = ticker.ScalarFormatter(useMathText=True)
    formatter.set_powerlimits((-3, 3))
    ax.yaxis.set_major_formatter(formatter)
    fig.tight_layout()
    ax.set_axisbelow(True)
    plt.rcParams.update({'font.size': 25})
    plt.savefig("plots/aggregation_scalability_tree.pdf", bbox_inches="tight", format="pdf")
    plt.show()

    # Slot Packets
    plot_grouped_bars(labels, [C_2, C_3, C_4, C_5],
                      ['FixR-ToRS', 'FixR-AS', 'FlexR-ToRS', 'FlexINA'],
                      '# fragments', 'number of slots', "plots/aggregation_fragments_vs_slots.pdf",
                      color_indices=[5, 9, 13, 1], hatch_list=['/', 'o', '*', '.'],
                      width=0.2, legend_bbox=(1.015, 1.12), legend_ncol=5, legend_size=14)

    # Environment Packets
    plot_grouped_bars(['tree', '1 Cluster', '2 Clusters'], [C_2, C_3, C_4, C_5],
                      ['FixR-ToRS', 'FixR-AS', 'FlexR-ToRS', 'FlexINA'],
                      '# fragments', 'Topology', "plots/aggregation_fragments_vs_topology.pdf",
                      color_indices=[5, 9, 13, 1], hatch_list=['/', 'o', '*', '.'],
                      width=0.2, legend_bbox=(1.015, 1.12), legend_ncol=5, legend_size=14)

    # Environment Runtime errorbar
    plot_errorbar(['tree', '1 Cluster', '2 Clusters'],
                  [y2, y3, y4, y5], [e2, e3, e4, e5],
                  ['fixR-ToRS', 'fixR-AS', 'flexR-ToRS', 'FlexINA'],
                  'runtime(s)', 'Topology', "plots/aggregation_runtime_vs_topology_errorbar.pdf",
                  fmt_list=['s--', '*--', '^--', 'p--'],
                  legend_bbox=(0.35, 1), legend_size=14)

    # Environment Runtime log scale
    plot_grouped_bars(['tree', '1 Cluster', '2 Clusters'],
                      [y2, y3, y4, y5],
                      ['FixR-ToRS', 'FixR-AS', 'FlexR-ToRS', 'FlexINA'],
                      'runtime (s, $\\log_{10}$ scale)', 'Topology',
                      "plots/aggregation_runtime_vs_topology_logscale.pdf",
                      color_indices=[5, 9, 13, 1], hatch_list=['/', 'o', '*', '.'],
                      width=0.2, legend_bbox=(1.015, 1.12), legend_ncol=5, legend_size=14)

    # Slot Runtime errorbar
    plot_errorbar(['1', '2', '3'], [y2, y3, y4, y5], [e2, e3, e4, e5],
                  ['fixR-ToRS', 'fixR-AS', 'flexR-ToRS', 'FlexINA'],
                  'runtime(s)', 'number of slots', "plots/aggregation_runtime_vs_slots_errorbar.pdf",
                  fmt_list=['s--', '*--', '^--', 'p--'],
                  legend_bbox=(0.33, 1), legend_size=16)

    # Scalability Fragments
    x = np.array(["8", "16", "24", "32", "40"])
    y = np.array([0.23863816261291504, 0.48981642723083496, 0.5911757946014404,
                  0.8037800788879395, 1.414642095565796])
    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar(x, y, color=[cmap[9]], edgecolor='black')
    for bar in bars:
        bar.set_hatch('.')
    ax.set_ylabel('Runtime(s)')
    ax.set_xlabel('Number of fragments')
    ax.set_xticks(np.arange(len(x)))
    ax.set_xticklabels(x)
    ax.grid(axis='y', linestyle='--', linewidth=0.5)
    formatter = ticker.ScalarFormatter(useMathText=True)
    formatter.set_powerlimits((-3, 3))
    ax.yaxis.set_major_formatter(formatter)
    fig.tight_layout()
    ax.set_axisbelow(True)
    plt.rcParams.update({'font.size': 25})
    plt.savefig("plots/aggregation_scalability_fragments.pdf", bbox_inches="tight", format="pdf")
    plt.show()


# ============================================================
# Block #1c — switch percentage (2-cluster)
# ============================================================

def run_pct_2cluster():
    envs = [env_2Clusters_Percentages]
    models = [defineModel_selectedSwitches]

    maxAggregate = 3
    ittrNum = 3
    Percentages = [0.1, 0.3, 0.5, 0.7]
    errorRuntimesM = {}
    errorPacketsM = {}
    kindsofModelsPackets = {}
    kindsofModelsRuntime = {}
    solve_counter = 0

    for modelSolve in models:
        print(f"[{modelSolve.__name__}]")
        block_start = time.time()
        numPackets2 = []
        RuntimeTotal2 = []
        errorRuntime = []
        errorPackets = []
        for percentage in Percentages:
            errorRuntime.append([])
            errorPackets.append([])
            envTemp = env_2Clusters_Percentages
            (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
             pSwitchesNumber, numberSlotsSwitches, workersTopology,
             pWorkerPorts, workersNumber, numAllFrags,
             fragmentsofEachWorker, totalWorkers, stepsToSwitches,
             cutPorts, selectedSwitches, clusters) = _unpack_env(envTemp)

            dict_list = _prepare_dict_list(fragmentsofEachWorker, totalWorkers)
            total_solves = len(models) * len(Percentages) * (maxAggregate - 2) * ittrNum * len(dict_list)
            for maxAggregation in range(2, maxAggregate):
                avgPacket = []
                avgRuntime = []
                for ittr in range(ittrNum):
                    T_max_1 = 0
                    T_max_2 = 6
                    addTime = int(1 * T_max_2)
                    Y_Used = []
                    Z_Used = []
                    numPackets = 0
                    RuntimeTotal = 0
                    for items in range(0, len(dict_list)):
                        fragmentsofEachWorker = dict_list[items]
                        solve_counter += 1
                        timed_out = False
                        signal.signal(signal.SIGALRM, _timeout_handler)
                        signal.alarm(60)
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
                            print(f"  [{solve_counter}/{total_solves}] ", end="", flush=True)
                            Y_Value_One, Z_Value_One, Y_Used, Z_Used, numPacket, Runtime, status = \
                                solveProblem(model, Y_Used, Z_Used)
                        except TimeoutError:
                            signal.alarm(0)
                            print(f"  [{solve_counter}/{total_solves}] TIMEOUT (skipped)", flush=True)
                            timed_out = True
                            numPacket = 0
                            Runtime = 0
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
            numPackets2.append(sum(avgPacket) / len(avgPacket))
            RuntimeTotal2.append(sum(avgRuntime) / len(avgRuntime))
            errorRuntimesM[percentage] = errorRuntime
            errorPacketsM[percentage] = errorPackets
        kindsofModelsPackets[modelSolve] = numPackets2
        kindsofModelsRuntime[modelSolve] = RuntimeTotal2

    print(f"  done in {time.time() - block_start:.1f}s")
    print("Packets:", kindsofModelsPackets)
    print("Runtime:", kindsofModelsRuntime)

    # --- Plots ---
    plot_single_bars(["1", "3", "5", "7"],
                     kindsofModelsPackets[defineModel_selectedSwitches],
                     '# fragments', 'number of switch selection',
                     "plots/percentage_2cluster_fragments.pdf", color_index=1)

    plot_single_bars(["1", "3", "5", "7"],
                     kindsofModelsRuntime[defineModel_selectedSwitches],
                     'runtime (s)', 'number of switch selection',
                     "plots/percentage_2cluster_runtime.pdf", color_index=1)


# ============================================================
# Block #1d — switch percentage (1-cluster)
# ============================================================

def run_pct_1cluster():
    envs = [env_1Cluster_Test]
    models = [defineModel_selectedSwitches]

    maxAggregate = 3
    ittrNum = 3
    Percentages = [0.1, 0.3, 0.5, 0.7]
    errorRuntimesM = {}
    errorPacketsM = {}
    kindsofModelsPackets = {}
    kindsofModelsRuntime = {}
    solve_counter = 0

    for modelSolve in models:
        print(f"[{modelSolve.__name__}]")
        block_start = time.time()
        numPackets2 = []
        RuntimeTotal2 = []
        errorRuntime = []
        errorPackets = []
        for percentage in Percentages:
            errorRuntime.append([])
            errorPackets.append([])
            envTemp = env_1Cluster_Test
            (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
             pSwitchesNumber, numberSlotsSwitches, workersTopology,
             pWorkerPorts, workersNumber, numAllFrags,
             fragmentsofEachWorker, totalWorkers, stepsToSwitches,
             cutPorts, selectedSwitches, clusters) = _unpack_env(envTemp)

            dict_list = _prepare_dict_list(fragmentsofEachWorker, totalWorkers)
            total_solves = len(models) * len(Percentages) * (maxAggregate - 2) * ittrNum * len(dict_list)
            for maxAggregation in range(2, maxAggregate):
                avgPacket = []
                avgRuntime = []
                for ittr in range(ittrNum):
                    T_max_1 = 0
                    T_max_2 = 8
                    addTime = int(1 * T_max_2)
                    Y_Used = []
                    Z_Used = []
                    numPackets = 0
                    RuntimeTotal = 0
                    for items in range(0, len(dict_list)):
                        fragmentsofEachWorker = dict_list[items]
                        solve_counter += 1
                        timed_out = False
                        signal.signal(signal.SIGALRM, _timeout_handler)
                        signal.alarm(60)
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
                            print(f"  [{solve_counter}/{total_solves}] ", end="", flush=True)
                            Y_Value_One, Z_Value_One, Y_Used, Z_Used, numPacket, Runtime, status = \
                                solveProblem(model, Y_Used, Z_Used)
                        except TimeoutError:
                            signal.alarm(0)
                            print(f"  [{solve_counter}/{total_solves}] TIMEOUT (skipped)", flush=True)
                            timed_out = True
                            numPacket = 0
                            Runtime = 0
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
            numPackets2.append(sum(avgPacket) / len(avgPacket))
            RuntimeTotal2.append(sum(avgRuntime) / len(avgRuntime))
            errorRuntimesM[percentage] = errorRuntime
            errorPacketsM[percentage] = errorPackets
        kindsofModelsPackets[modelSolve] = numPackets2
        kindsofModelsRuntime[modelSolve] = RuntimeTotal2

    print(f"  done in {time.time() - block_start:.1f}s")
    print("Packets:", kindsofModelsPackets)
    print("Runtime:", kindsofModelsRuntime)

    # --- Plots ---
    plot_single_bars(["1", "3", "5", "7"],
                     kindsofModelsPackets[defineModel_selectedSwitches],
                     '# fragments', 'number of switch selection',
                     "plots/percentage_1cluster_fragments.pdf", color_index=1)

    plot_single_bars(["1", "3", "5", "7"],
                     kindsofModelsRuntime[defineModel_selectedSwitches],
                     'runtime (s)', 'number of switch selection',
                     "plots/percentage_1cluster_runtime.pdf", color_index=1)


# ============================================================
# Block #2 — start time experiment
# ============================================================

def run_start_time():
    envs = [env_2Clusters]
    models = [defineModel_ATP, defineModel_GRID, defineModel_ATP_GRID,
              defineModel_selectedSwitches]

    maxAggregate = 3
    ittrNum = 3
    percentage = 0.6
    errorRuntimesM = {}
    errorPacketsM = {}
    kindsofModelsPackets = {}
    kindsofModelsRuntime = {}
    T_max_2_Array = [8, 9, 10, 11]
    solve_counter = 0

    for modelSolve in models:
        print(f"[{modelSolve.__name__}]")
        block_start = time.time()
        numPackets2 = []
        RuntimeTotal2 = []
        errorRuntime = []
        errorPackets = []
        for T_max_2_index in T_max_2_Array:
            errorRuntime.append([])
            errorPackets.append([])
            envTemp = env_2Clusters
            (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
             pSwitchesNumber, numberSlotsSwitches, workersTopology,
             pWorkerPorts, workersNumber, numAllFrags,
             fragmentsofEachWorker, totalWorkers, stepsToSwitches,
             cutPorts, selectedSwitches, clusters) = _unpack_env(envTemp)

            dict_list = _prepare_dict_list(fragmentsofEachWorker, totalWorkers)
            total_solves = len(models) * len(T_max_2_Array) * (maxAggregate - 2) * ittrNum * len(dict_list)
            for maxAggregation in range(2, maxAggregate):
                for ittr in range(ittrNum):
                    T_max_1 = 0
                    T_max_2 = T_max_2_index
                    addTime = int(0.6 * T_max_2)
                    Y_Used = []
                    Z_Used = []
                    numPackets = 0
                    RuntimeTotal = 0
                    avgPacket = []
                    avgRuntime = []
                    for items in range(0, len(dict_list)):
                        fragmentsofEachWorker = dict_list[items]
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
                        solve_counter += 1
                        print(f"  [{solve_counter}/{total_solves}] ", end="", flush=True)
                        Y_Value_One, Z_Value_One, Y_Used, Z_Used, numPacket, Runtime, status = \
                            solveProblem(model, Y_Used, Z_Used)
                        T_max_1 += addTime
                        T_max_2 += addTime
                        numPackets += numPacket
                        RuntimeTotal += Runtime
                    avgPacket.append(numPackets)
                    avgRuntime.append(RuntimeTotal)
                    errorRuntime[-1].append(RuntimeTotal)
                    errorPackets[-1].append(numPackets)
            numPackets2.append(sum(avgPacket) / len(avgPacket))
            RuntimeTotal2.append(sum(avgRuntime) / len(avgRuntime))
        kindsofModelsPackets[modelSolve] = numPackets2
        kindsofModelsRuntime[modelSolve] = RuntimeTotal2
        errorRuntimesM[modelSolve] = errorRuntime
        errorPacketsM[modelSolve] = errorPackets

    print(f"  done in {time.time() - block_start:.1f}s")
    print("Packets:", kindsofModelsPackets)
    print("Runtime:", kindsofModelsRuntime)

    # --- Plots ---
    labels = ['8', '9', '10', '11']
    C_2 = kindsofModelsPackets[defineModel_ATP]
    C_3 = kindsofModelsPackets[defineModel_GRID]
    C_4 = kindsofModelsPackets[defineModel_ATP_GRID]
    C_5 = kindsofModelsPackets[defineModel_selectedSwitches]

    plot_grouped_bars(labels, [C_2, C_3, C_4, C_5],
                      ['FixR-ToRS', 'FixR-AS', 'FlexR-ToRS', 'FlexINA'],
                      '# fragments', 'time window',
                      "plots/starttime_fragments.pdf",
                      color_indices=[5, 9, 13, 1], hatch_list=['/', 'o', '*', '.'],
                      width=0.2, legend_bbox=(1.015, 1.11), legend_ncol=5, legend_size=14)

    y2 = kindsofModelsRuntime[defineModel_ATP]
    y3 = kindsofModelsRuntime[defineModel_GRID]
    y4 = kindsofModelsRuntime[defineModel_ATP_GRID]
    y5 = kindsofModelsRuntime[defineModel_selectedSwitches]
    e2 = [np.std(vals) for vals in errorRuntimesM[defineModel_ATP]]
    e3 = [np.std(vals) for vals in errorRuntimesM[defineModel_GRID]]
    e4 = [np.std(vals) for vals in errorRuntimesM[defineModel_ATP_GRID]]
    e5 = [np.std(vals) for vals in errorRuntimesM[defineModel_selectedSwitches]]
    plot_errorbar(labels, [y2, y3, y4, y5], [e2, e3, e4, e5],
                  ['fixR-ToRS', 'fixR-AS', 'flexR-ToRS', 'FlexINA'],
                  'runtime(s)', 'Start Time',
                  "plots/starttime_runtime.pdf",
                  fmt_list=['s--', '*--', '^--', 'p--'],
                  legend_bbox=(0.33, 1), legend_size=16)


# ============================================================
# Block #3 — time window experiment
# ============================================================

def run_time_window():
    envs = [env_1Cluster_Test]
    models = [defineModel_ATP, defineModel_GRID, defineModel_ATP_GRID,
              defineModel_selectedSwitches]

    maxAggregate = 3
    ittrNum = 3
    PercentagesTimes = [0.4, 0.6, 1]
    percentage = 0.6
    errorRuntimesM = {}
    errorPacketsM = {}
    kindsofModelsPackets = {}
    kindsofModelsRuntime = {}
    solve_counter = 0
    total_solves = None

    for modelSolve in models:
        print(f"[{modelSolve.__name__}]")
        block_start = time.time()
        numPackets2 = []
        RuntimeTotal2 = []
        errorRuntime = []
        errorPackets = []
        for percentageTime in PercentagesTimes:
            errorRuntime.append([])
            errorPackets.append([])
            envTemp = env_1Cluster_Test
            (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
             pSwitchesNumber, numberSlotsSwitches, workersTopology,
             pWorkerPorts, workersNumber, numAllFrags,
             fragmentsofEachWorker, totalWorkers, stepsToSwitches,
             cutPorts, selectedSwitches, clusters) = _unpack_env(envTemp)

            dict_list = _prepare_dict_list(fragmentsofEachWorker, totalWorkers)
            if total_solves is None:
                total_solves = len(models) * len(PercentagesTimes) * len(dict_list) * (maxAggregate - 2) * ittrNum
            for maxAggregation in range(2, maxAggregate):
                for ittr in range(ittrNum):
                    T_max_1 = 0
                    T_max_2 = 9
                    addTime = int(percentageTime * T_max_2)
                    Y_Used = []
                    Z_Used = []
                    numPackets = 0
                    RuntimeTotal = 0
                    avgPacket = []
                    avgRuntime = []
                    for items in range(0, len(dict_list)):
                        fragmentsofEachWorker = dict_list[items]
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
                        solve_counter += 1
                        print(f"  [{solve_counter}/{total_solves}] ", end="", flush=True)
                        Y_Value_One, Z_Value_One, Y_Used, Z_Used, numPacket, Runtime, status = \
                            solveProblem(model, Y_Used, Z_Used)
                        T_max_1 += addTime
                        T_max_2 += addTime
                        numPackets += numPacket
                        RuntimeTotal += Runtime
                    avgPacket.append(numPackets)
                    avgRuntime.append(RuntimeTotal)
                    errorRuntime[-1].append(RuntimeTotal)
                    errorPackets[-1].append(numPackets)
            numPackets2.append(sum(avgPacket) / len(avgPacket))
            RuntimeTotal2.append(sum(avgRuntime) / len(avgRuntime))
        kindsofModelsPackets[modelSolve] = numPackets2
        kindsofModelsRuntime[modelSolve] = RuntimeTotal2
        errorRuntimesM[modelSolve] = errorRuntime
        errorPacketsM[modelSolve] = errorPackets

    print(f"  done in {time.time() - block_start:.1f}s")
    print("Packets:", kindsofModelsPackets)
    print("Runtime:", kindsofModelsRuntime)

    # --- Plots ---
    labels = ['40%', '60%', '100%']
    C_2 = kindsofModelsPackets[defineModel_ATP]
    C_3 = kindsofModelsPackets[defineModel_GRID]
    C_4 = kindsofModelsPackets[defineModel_ATP_GRID]
    C_5 = kindsofModelsPackets[defineModel_selectedSwitches]

    plot_grouped_bars(labels, [C_2, C_3, C_4, C_5],
                      ['FixR-ToRS', 'FixR-AS', 'FlexR-ToRS', 'FlexINA'],
                      '# fragments', 'time windows',
                      "plots/timewindow_fragments.pdf",
                      color_indices=[5, 9, 13, 1], hatch_list=['/', 'o', '*', '.'],
                      width=0.2, legend_bbox=(1.015, 1.11), legend_ncol=5, legend_size=14)

    y2 = kindsofModelsRuntime[defineModel_ATP]
    y3 = kindsofModelsRuntime[defineModel_GRID]
    y4 = kindsofModelsRuntime[defineModel_ATP_GRID]
    y5 = kindsofModelsRuntime[defineModel_selectedSwitches]
    e2 = [np.std(vals) for vals in errorRuntimesM[defineModel_ATP]]
    e3 = [np.std(vals) for vals in errorRuntimesM[defineModel_GRID]]
    e4 = [np.std(vals) for vals in errorRuntimesM[defineModel_ATP_GRID]]
    e5 = [np.std(vals) for vals in errorRuntimesM[defineModel_selectedSwitches]]
    plot_errorbar(labels, [y2, y3, y4, y5], [e2, e3, e4, e5],
                  ['fixR-ToRS', 'fixR-AS', 'flexR-ToRS', 'FlexINA'],
                  'runtime(s)', 'time windows',
                  "plots/timewindow_runtime.pdf",
                  fmt_list=['s--', '*--', '^--', 'p--'],
                  legend_bbox=(0.3, 1), legend_size=14)


# ============================================================
# Block #4 — worker distribution experiment
# ============================================================

def run_worker_dist():
    envs = [env_2Clusters, env_2Clusters_Zipf15, env_2Clusters_Zipf2]
    models = [defineModel_ATP, defineModel_GRID, defineModel_ATP_GRID,
              defineModel_selectedSwitches]

    maxAggregate = 3
    ittrNum = 3
    percentage = 0.6
    errorRuntimesM = {}
    errorPacketsM = {}
    kindsofModelsPackets = {}
    kindsofModelsRuntime = {}
    solve_counter = 0

    for modelSolve in models:
        print(f"[{modelSolve.__name__}]")
        block_start = time.time()
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
            total_solves = len(models) * len(envs) * (maxAggregate - 2) * ittrNum * len(dict_list)
            for maxAggregation in range(2, maxAggregate):
                for ittr in range(ittrNum):
                    T_max_1 = 0
                    T_max_2 = 8
                    addTime = int(1 * T_max_2)
                    Y_Used = []
                    Z_Used = []
                    numPackets = 0
                    RuntimeTotal = 0
                    avgPacket = []
                    avgRuntime = []
                    for items in range(0, len(dict_list)):
                        fragmentsofEachWorker = dict_list[items]
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
                        solve_counter += 1
                        print(f"  [{solve_counter}/{total_solves}] ", end="", flush=True)
                        Y_Value_One, Z_Value_One, Y_Used, Z_Used, numPacket, Runtime, status = \
                            solveProblem(model, Y_Used, Z_Used)
                        T_max_1 += addTime
                        T_max_2 += addTime
                        numPackets += numPacket
                        RuntimeTotal += Runtime
                    avgPacket.append(numPackets)
                    avgRuntime.append(RuntimeTotal)
                    errorRuntime[-1].append(RuntimeTotal)
                    errorPackets[-1].append(numPackets)
            numPackets2.append(sum(avgPacket) / len(avgPacket))
            RuntimeTotal2.append(sum(avgRuntime) / len(avgRuntime))
        errorRuntimesM[modelSolve] = errorRuntime
        errorPacketsM[modelSolve] = errorPackets
        kindsofModelsPackets[modelSolve] = numPackets2
        kindsofModelsRuntime[modelSolve] = RuntimeTotal2

    print(f"  done in {time.time() - block_start:.1f}s")
    print("Packets:", kindsofModelsPackets)
    print("Runtime:", kindsofModelsRuntime)

    # --- Plots ---
    labels = ['Uniform', 'Zipf 1.5', 'Zipf 2']
    C_2 = kindsofModelsPackets[defineModel_ATP]
    C_3 = kindsofModelsPackets[defineModel_GRID]
    C_4 = kindsofModelsPackets[defineModel_ATP_GRID]
    C_5 = kindsofModelsPackets[defineModel_selectedSwitches]

    plot_grouped_bars(labels, [C_2, C_3, C_4, C_5],
                      ['FixR-ToRS', 'FixR-AS', 'FlexR-ToRS', 'FlexINA'],
                      '# fragments', 'distribution of workers',
                      "plots/distribution_fragments.pdf",
                      color_indices=[5, 9, 13, 1], hatch_list=['/', 'o', '*', '.'],
                      width=0.2, legend_bbox=(1.015, 1.11), legend_ncol=5, legend_size=14)

    y2 = kindsofModelsRuntime[defineModel_ATP]
    y3 = kindsofModelsRuntime[defineModel_GRID]
    y4 = kindsofModelsRuntime[defineModel_ATP_GRID]
    y5 = kindsofModelsRuntime[defineModel_selectedSwitches]

    plot_grouped_bars(labels, [y2, y3, y4, y5],
                      ['FixR-ToRS', 'FixR-AS', 'FlexR-ToRS', 'FlexINA'],
                      'runtime (s, $\\log_{10}$ scale)', 'distribution of workers',
                      "plots/distribution_runtime.pdf",
                      color_indices=[5, 9, 13, 1], hatch_list=['/', 'o', '*', '.'],
                      width=0.2, legend_bbox=(1.015, 1.13), legend_ncol=5, legend_size=14,
                      log_scale=False)

    e2 = [np.std(vals) for vals in errorRuntimesM[defineModel_ATP]]
    e3 = [np.std(vals) for vals in errorRuntimesM[defineModel_GRID]]
    e4 = [np.std(vals) for vals in errorRuntimesM[defineModel_ATP_GRID]]
    e5 = [np.std(vals) for vals in errorRuntimesM[defineModel_selectedSwitches]]
    plot_errorbar(labels, [y2, y3, y4, y5], [e2, e3, e4, e5],
                  ['fixR-ToRS', 'fixR-AS', 'flexR-ToRS', 'FlexINA'],
                  'runtime(s)', 'distribution of workers',
                  "plots/distribution_runtime_errorbar.pdf",
                  fmt_list=['s--', '*--', '^--', 'p--'],
                  legend_bbox=(0.65, 1), legend_size=16)


# ============================================================
# Block #5 — InArt vs FlexINA comparison
# ============================================================

def run_inart_comparison():
    envs = [env_2Clusters]
    models = [defineModel_InArt, defineModel_selectedSwitches]

    maxAggregate = 3
    ittrNum = 3
    percentage = 0.6
    errorRuntimesM = {}
    errorPacketsM = {}
    kindsofModelsPackets = {}
    kindsofModelsRuntime = {}
    solve_counter = 0

    for modelSolve in models:
        print(f"[{modelSolve.__name__}]")
        block_start = time.time()
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
            total_solves = len(models) * len(envs) * (maxAggregate - 2) * ittrNum * len(dict_list)
            for maxAggregation in range(2, maxAggregate):
                for ittr in range(ittrNum):
                    T_max_1 = 0
                    T_max_2 = 8
                    addTime = int(1 * T_max_2)
                    Y_Used = []
                    Z_Used = []
                    numPackets = 0
                    RuntimeTotal = 0
                    avgPacket = []
                    avgRuntime = []
                    for items in range(0, len(dict_list)):
                        fragmentsofEachWorker = dict_list[items]
                        solve_counter += 1
                        timed_out = False
                        signal.signal(signal.SIGALRM, _timeout_handler)
                        signal.alarm(60)
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
                            print(f"  [{solve_counter}/{total_solves}] ", end="", flush=True)
                            Y_Value_One, Z_Value_One, Y_Used, Z_Used, numPacket, Runtime, status = \
                                solveProblem(model, Y_Used, Z_Used)
                        except TimeoutError:
                            signal.alarm(0)
                            print(f"  [{solve_counter}/{total_solves}] TIMEOUT (skipped)", flush=True)
                            timed_out = True
                            numPacket = 0
                            Runtime = 0
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
            numPackets2.append(sum(avgPacket) / len(avgPacket))
            RuntimeTotal2.append(sum(avgRuntime) / len(avgRuntime))
        errorRuntimesM[modelSolve] = errorRuntime
        errorPacketsM[modelSolve] = errorPackets
        kindsofModelsPackets[modelSolve] = numPackets2
        kindsofModelsRuntime[modelSolve] = RuntimeTotal2

    print(f"  done in {time.time() - block_start:.1f}s")
    print("Packets:", kindsofModelsPackets)
    print("Runtime:", kindsofModelsRuntime)

    # --- Plots ---
    labels = ['2 Clusters']
    C_inart = kindsofModelsPackets[defineModel_InArt]
    C_flex = kindsofModelsPackets[defineModel_selectedSwitches]

    plot_grouped_bars(labels, [C_inart, C_flex],
                      ['InArt', 'FlexINA'],
                      '# fragments', 'topology',
                      "plots/inart_vs_flexina_fragments.pdf",
                      color_indices=[5, 1], hatch_list=['/', '.'],
                      width=0.2, legend_bbox=(1, 1), legend_ncol=2, legend_size=16)

    y_inart = kindsofModelsRuntime[defineModel_InArt]
    y_flex = kindsofModelsRuntime[defineModel_selectedSwitches]
    e_inart = [np.std(vals) for vals in errorRuntimesM[defineModel_InArt]]
    e_flex = [np.std(vals) for vals in errorRuntimesM[defineModel_selectedSwitches]]
    plot_errorbar(labels, [y_inart, y_flex], [e_inart, e_flex],
                  ['InArt', 'FlexINA'], 'runtime(s)', 'topology',
                  "plots/inart_vs_flexina_runtime_errorbar.pdf",
                  fmt_list=['s--', 'p--'],
                  legend_bbox=(0.3, 1), legend_size=16)

    fig, ax = plt.subplots(figsize=(8, 6))
    plt.plot(labels, y_inart, ls='dashed', marker='s', markersize=10, label='InArt')
    plt.plot(labels, y_flex, ls='dashed', marker='p', markersize=10, label='FlexINA')
    plt.legend(loc='upper center', bbox_to_anchor=(0.3, 1), ncol=2, prop={'size': 16})
    plt.xlabel('topology')
    plt.ylabel('runtime(s)')
    formatter = ticker.ScalarFormatter(useMathText=True)
    formatter.set_powerlimits((-3, 3))
    ax.yaxis.set_major_formatter(formatter)
    fig.tight_layout()
    plt.grid(linestyle='--', linewidth=0.5)
    plt.rcParams.update({'font.size': 22})
    plt.savefig("plots/inart_vs_flexina_runtime.pdf", bbox_inches="tight", format="pdf")
    plt.show()


# ============================================================
# Main — prompt user and dispatch
# ============================================================

BLOCK_RUNNERS = {
    "baseline":     run_baseline,
    "models":       run_models,
    "pct_2cluster": run_pct_2cluster,
    "pct_1cluster": run_pct_1cluster,
    "start_time":   run_start_time,
    "time_window":  run_time_window,
    "worker_dist":  run_worker_dist,
    "inart":        run_inart_comparison,
}

if __name__ == "__main__":
    RUN_BLOCK = _prompt_block()
    BLOCK_RUNNERS[RUN_BLOCK]()
