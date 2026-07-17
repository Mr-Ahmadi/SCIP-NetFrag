"""
Environment definitions — network topologies and worker configurations.
Each env_* function returns the same 15-element tuple.

The shared _optimize_env() helper eliminates ~70 lines of duplicated
worker-deletion / port-cleanup logic that was copy-pasted across every env.
"""


# ---------------------------------------------------------------------------
# Shared optimization helper
# ---------------------------------------------------------------------------

def _optimize_env(pSwitchPorts, neighborsofEachSwitch, workersTopology,
                  pWorkerPorts, fragmentsofEachWorker):
    """
    Common 'Optimaze' logic: identify duplicate workers per switch,
    remove the extras, and rebuild ports / neighbors / topology / fragments.
    Returns (pSwitchPortsNew, neighborsofEachSwitchNew, workersTopologyNew,
             pWorkerPortsNew, workersNumberNew, fragmentsofEachWorkerNew,
             numAllFragsNew).
    """
    switchWorkerLinks = {}
    workersDelete = []

    for worker, sw in workersTopology.items():
        if sw not in switchWorkerLinks:
            switchWorkerLinks[sw] = [worker]
        else:
            switchWorkerLinks[sw].append(worker)
            workersDelete.append(worker)

    pSwitchPortsNew = {}
    for sw in pSwitchPorts:
        if sw in workersDelete:
            continue
        portDelete = []
        pSwitchPortsNew[sw] = pSwitchPorts[sw].copy()
        for port in pSwitchPortsNew[sw]:
            if pSwitchPortsNew[sw][port] in workersDelete:
                portDelete.append(port)
        for delete in portDelete:
            del pSwitchPortsNew[sw][delete]

    neighborsofEachSwitchNew = {}
    for sw in neighborsofEachSwitch:
        if sw in workersDelete:
            continue
        NeighborDelete = []
        neighborsofEachSwitchNew[sw] = neighborsofEachSwitch[sw].copy()
        for idx in range(len(neighborsofEachSwitchNew[sw])):
            if neighborsofEachSwitchNew[sw][idx] in workersDelete:
                NeighborDelete.append(idx)
        for delete in NeighborDelete:
            del neighborsofEachSwitchNew[sw][delete]

    workersTopologyNew = {w: workersTopology[w] for w in workersTopology
                          if w not in workersDelete}

    pWorkerPortsNew = {w: pWorkerPorts[w].copy() for w in pWorkerPorts
                       if w not in workersDelete}

    workersNumberNew = len(workersTopologyNew)

    fragmentsofEachWorkerNew = {}
    for worker in fragmentsofEachWorker:
        if worker not in workersDelete:
            fragmentsofEachWorkerNew[worker] = fragmentsofEachWorker[worker].copy()
            if len(fragmentsofEachWorkerNew[worker]) > 1:
                fragmentsofEachWorkerNew[worker] = [fragmentsofEachWorkerNew[worker][0]]

    numAllFragsNew = sum(len(v) for v in fragmentsofEachWorkerNew.values())

    return (pSwitchPortsNew, neighborsofEachSwitchNew, workersTopologyNew,
            pWorkerPortsNew, workersNumberNew, fragmentsofEachWorkerNew,
            numAllFragsNew)


# ---------------------------------------------------------------------------
# env_1Cluster_Test  (cell 18 — the one used in exec blocks)
# ---------------------------------------------------------------------------

def env_1Cluster_Test(state):
    pSwitchesTopology = {0: [2, 3], 1: [2, 3], 2: [0, 1, 4],
                         3: [0, 1, 4], 4: [2, 3, "PS"]}

    pSwitchPorts = {0: {0: 11, 1: 22, 2: 3, 3: 2},
                    1: {0: 33, 1: 44, 2: 3, 3: 2},
                    2: {0: 0, 1: 1, 2: 55, 3: 66, 4: 4},
                    3: {0: 0, 1: 1, 2: 77, 3: 88, 4: 4},
                    4: {0: 2, 1: 3, 4: "PS"},
                    11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                    55: {0: 2}, 66: {0: 2}, 77: {0: 3}, 88: {0: 3}}

    clusters = {0: [0, 1, 2, 3]}
    selectedSwitches = [2, 3, 4, 0, 1]
    cutPorts = {0: {3: 2}, 1: {2: 3}, 2: {4: 4}, 3: {4: 4}, 4: {4: "PS"},
                11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                55: {0: 2}, 66: {0: 2}, 77: {0: 3}, 88: {0: 3}}

    neighborsofEachSwitch = {0: [11, 22, 2, 3], 1: [33, 44, 2, 3],
                             2: [55, 66, 0, 1, 4], 3: [77, 88, 0, 1, 4],
                             4: [2, 3],
                             11: [0], 22: [0], 33: [1], 44: [1],
                             55: [2], 66: [2], 77: [3], 88: [3]}

    pSwitchesNumber = len(pSwitchesTopology)
    numberSlotsSwitches = {0: [], 1: [0], 2: [0], 3: [], 4: [0]}

    workersTopology = {11: 0, 22: 0, 33: 1, 44: 1,
                       55: 2, 66: 2, 77: 3, 88: 3}

    pWorkerPorts = {11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                    55: {0: 2}, 66: {0: 2}, 77: {0: 3}, 88: {0: 3}}

    workersNumber = len(workersTopology)

    fragmentsofEachWorker = {11: ["A0", "B0", "C0"], 22: ["A1", "B1", "C1"],
                             33: ["A2", "B2", "C2"], 44: ["A3", "B3", "C3"],
                             55: ["A4", "B4", "C4"], 66: ["A5", "B5", "C5"],
                             77: ["A6", "B6", "C6"], 88: ["A7", "B7", "C7"]}

    totalWorkers = fragmentsofEachWorker.copy()
    numAllFrags = sum(len(v) for v in fragmentsofEachWorker.values())

    stepsToSwitches = {11: [1, 3, 2, 2, 3], 22: [1, 3, 2, 2, 3],
                       33: [3, 1, 2, 2, 3], 44: [3, 1, 2, 2, 3],
                       55: [2, 2, 1, 3, 2], 66: [2, 2, 1, 3, 2],
                       77: [2, 2, 3, 1, 2], 88: [2, 2, 3, 1, 2]}

    if state == "Optimaze":
        result = _optimize_env(pSwitchPorts, neighborsofEachSwitch,
                               workersTopology, pWorkerPorts,
                               fragmentsofEachWorker)
        (pSwitchPorts, neighborsofEachSwitch, workersTopology,
         pWorkerPorts, workersNumber, fragmentsofEachWorker,
         numAllFrags) = result

    return (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
            pSwitchesNumber, numberSlotsSwitches, workersTopology,
            pWorkerPorts, workersNumber, numAllFrags,
            fragmentsofEachWorker, totalWorkers, stepsToSwitches,
            cutPorts, selectedSwitches, clusters)


# ---------------------------------------------------------------------------
# env_2Clusters  (cell 9)
# ---------------------------------------------------------------------------

def env_2Clusters(state):
    pSwitchesTopology = {0: [2, 3], 1: [2, 3], 2: [0, 1, 8, 9],
                         3: [0, 1], 4: [6, 7], 5: [6, 7], 6: [4, 5],
                         7: [4, 5, 8, 9], 8: [2, 7, "PS"], 9: [2, 7, "PS"]}

    pSwitchPorts = {0: {0: 11, 1: 22, 2: 2, 3: 3},
                    1: {0: 33, 1: 44, 2: 2, 3: 3},
                    2: {0: 0, 1: 1, 2: 8, 3: 9},
                    3: {0: 0, 1: 1, 2: 8, 3: 9},
                    4: {0: 55, 1: 66, 2: 6, 3: 7},
                    5: {0: 77, 1: 88, 2: 6, 3: 7},
                    6: {0: 4, 1: 5, 2: 8, 3: 9},
                    7: {0: 4, 1: 5, 2: 8, 3: 9},
                    8: {0: 2, 1: 7, 2: "PS", 3: 3, 4: 6},
                    9: {0: 7, 1: 2, 2: "PS", 3: 3, 4: 6},
                    11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                    55: {0: 4}, 66: {0: 4}, 77: {0: 5}, 88: {0: 5}}

    selectedSwitches = [2, 3, 6, 7, 8, 9, 0, 1, 4, 5]

    cutPorts = {0: {2: 2}, 1: {2: 2}, 2: {2: 8}, 3: {3: 9},
                4: {3: 7}, 5: {3: 7}, 6: {2: 8}, 7: {3: 9},
                8: {2: "PS"}, 9: {2: "PS"},
                11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                55: {0: 4}, 66: {0: 4}, 77: {0: 5}, 88: {0: 5}}

    neighborsofEachSwitch = {0: [11, 22, 2, 3], 1: [33, 44, 2, 3],
                             2: [0, 1, 8, 9], 3: [0, 1, 8, 9],
                             4: [55, 66, 6, 7], 5: [77, 88, 6, 7],
                             6: [4, 5, 8, 9], 7: [4, 5, 8, 9],
                             8: [2, 7, 3, 6], 9: [2, 7, 3, 6],
                             11: [0], 22: [0], 33: [1], 44: [1],
                             55: [4], 66: [4], 77: [5], 88: [5]}

    pSwitchesNumber = len(pSwitchesTopology)

    numberSlotsSwitches = {0: [0], 1: [0], 2: [], 3: [0], 4: [], 5: [0],
                           6: [], 7: [], 8: [0], 9: []}

    workersTopology = {11: 0, 22: 0, 33: 1, 44: 1,
                       55: 4, 66: 4, 77: 5, 88: 5}

    clusters = {0: [0, 1, 2, 3], 1: [4, 5, 6, 7]}

    pWorkerPorts = {11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                    55: {0: 4}, 66: {0: 4}, 77: {0: 5}, 88: {0: 5}}

    workersNumber = len(workersTopology)

    fragmentsofEachWorker = {11: ["A0", "B0", "C0"], 22: ["A1", "B1", "C1"],
                             33: ["A2", "B2", "C2"], 44: ["A3", "B3", "C3"],
                             55: ["A4", "B4", "C4"], 66: ["A5", "B5", "C5"],
                             77: ["A6", "B6", "C6"], 88: ["A7", "B7", "C7"]}

    totalWorkers = fragmentsofEachWorker.copy()
    numAllFrags = sum(len(v) for v in fragmentsofEachWorker.values())

    stepsToSwitches = {11: [1, 3, 2, 2, 5, 5, 6, 4, 3, 3],
                       22: [1, 3, 2, 2, 5, 5, 6, 4, 3, 3],
                       33: [3, 1, 2, 2, 5, 5, 6, 4, 3, 3],
                       44: [3, 1, 2, 2, 5, 5, 6, 4, 3, 3],
                       55: [5, 5, 4, 6, 1, 3, 2, 2, 3, 3],
                       66: [5, 5, 4, 6, 1, 3, 2, 2, 3, 3],
                       77: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       88: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3]}

    if state == "Optimaze":
        result = _optimize_env(pSwitchPorts, neighborsofEachSwitch,
                               workersTopology, pWorkerPorts,
                               fragmentsofEachWorker)
        (pSwitchPorts, neighborsofEachSwitch, workersTopology,
         pWorkerPorts, workersNumber, fragmentsofEachWorker,
         numAllFrags) = result

    return (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
            pSwitchesNumber, numberSlotsSwitches, workersTopology,
            pWorkerPorts, workersNumber, numAllFrags,
            fragmentsofEachWorker, totalWorkers, stepsToSwitches,
            cutPorts, selectedSwitches, clusters)


# ---------------------------------------------------------------------------
# env_2Clusters_Zipf15  (cell 13)
# ---------------------------------------------------------------------------

def env_2Clusters_Zipf15(state):
    pSwitchesTopology = {0: [2, 3], 1: [2, 3], 2: [0, 1, 8, 9],
                         3: [0, 1], 4: [6, 7], 5: [6, 7], 6: [4, 5],
                         7: [4, 5, 8, 9], 8: [2, 7, "PS"], 9: [2, 7, "PS"]}

    pSwitchPorts = {0: {0: 11, 1: 22, 2: 2, 3: 3, 4: 33, 5: 44},
                    1: {2: 2, 3: 3},
                    2: {0: 0, 1: 1, 2: 8, 3: 9},
                    3: {0: 0, 1: 1, 2: 8, 3: 9},
                    4: {2: 6, 3: 7},
                    5: {0: 77, 1: 88, 2: 6, 3: 7, 4: 55, 5: 66},
                    6: {0: 4, 1: 5, 2: 8, 3: 9},
                    7: {0: 4, 1: 5, 2: 8, 3: 9},
                    8: {0: 2, 1: 7, 2: "PS", 3: 3, 4: 6},
                    9: {0: 7, 1: 2, 2: "PS", 3: 3, 4: 6},
                    11: {0: 0}, 22: {0: 0}, 33: {0: 0}, 44: {0: 0},
                    55: {0: 5}, 66: {0: 5}, 77: {0: 5}, 88: {0: 5}}

    selectedSwitches = [2, 3, 6, 7, 8, 9, 0, 1, 4, 5]
    clusters = {0: [0, 1, 2, 3], 1: [4, 5, 6, 7]}

    cutPorts = {0: {2: 2}, 1: {2: 2}, 2: {2: 8}, 3: {3: 9},
                4: {3: 7}, 5: {3: 7}, 6: {2: 8}, 7: {3: 9},
                8: {2: "PS"}, 9: {2: "PS"},
                11: {0: 0}, 22: {0: 0}, 33: {0: 0}, 44: {0: 0},
                55: {0: 5}, 66: {0: 5}, 77: {0: 5}, 88: {0: 5}}

    neighborsofEachSwitch = {0: [11, 22, 33, 44, 2, 3], 1: [2, 3],
                             2: [0, 1, 8, 9], 3: [0, 1, 8, 9],
                             4: [6, 7], 5: [55, 66, 77, 88, 6, 7],
                             6: [4, 5, 8, 9], 7: [4, 5, 8, 9],
                             8: [2, 7, 3, 6], 9: [2, 7, 3, 6],
                             11: [0], 22: [0], 33: [0], 44: [0],
                             55: [5], 66: [5], 77: [5], 88: [5]}

    pSwitchesNumber = len(pSwitchesTopology)

    numberSlotsSwitches = {0: [0], 1: [0], 2: [], 3: [0], 4: [], 5: [0],
                           6: [0], 7: [0], 8: [0], 9: []}

    workersTopology = {11: 0, 22: 0, 33: 0, 44: 0,
                       55: 5, 66: 5, 77: 5, 88: 5}

    pWorkerPorts = {11: {0: 0}, 22: {0: 0}, 33: {0: 0}, 44: {0: 0},
                    55: {0: 5}, 66: {0: 5}, 77: {0: 5}, 88: {0: 5}}

    workersNumber = len(workersTopology)

    fragmentsofEachWorker = {11: ["A0", "B0", "C0"], 22: ["A1", "B1", "C1"],
                             33: ["A2", "B2", "C2"], 44: ["A3", "B3", "C3"],
                             55: ["A4", "B4", "C4"], 66: ["A5", "B5", "C5"],
                             77: ["A6", "B6", "C6"], 88: ["A7", "B7", "C7"]}
    totalWorkers = fragmentsofEachWorker.copy()
    numAllFrags = sum(len(v) for v in fragmentsofEachWorker.values())

    stepsToSwitches = {11: [1, 3, 2, 2, 5, 5, 6, 4, 3, 3],
                       22: [1, 3, 2, 2, 5, 5, 6, 4, 3, 3],
                       33: [1, 3, 2, 2, 5, 5, 6, 4, 3, 3],
                       44: [1, 3, 2, 2, 5, 5, 6, 4, 3, 3],
                       55: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       66: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       77: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       88: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3]}

    if state == "Optimaze":
        result = _optimize_env(pSwitchPorts, neighborsofEachSwitch,
                               workersTopology, pWorkerPorts,
                               fragmentsofEachWorker)
        (pSwitchPorts, neighborsofEachSwitch, workersTopology,
         pWorkerPorts, workersNumber, fragmentsofEachWorker,
         numAllFrags) = result

    return (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
            pSwitchesNumber, numberSlotsSwitches, workersTopology,
            pWorkerPorts, workersNumber, numAllFrags,
            fragmentsofEachWorker, totalWorkers, stepsToSwitches,
            cutPorts, selectedSwitches, clusters)


# ---------------------------------------------------------------------------
# env_2Clusters_Zipf2  (cell 14)
# ---------------------------------------------------------------------------

def env_2Clusters_Zipf2(state):
    pSwitchesTopology = {0: [2, 3], 1: [2, 3], 2: [0, 1, 8, 9],
                         3: [0, 1], 4: [6, 7], 5: [6, 7], 6: [4, 5],
                         7: [4, 5, 8, 9], 8: [2, 7, "PS"], 9: [2, 7, "PS"]}

    pSwitchPorts = {0: {2: 2, 3: 3}, 1: {2: 2, 3: 3},
                    2: {0: 0, 1: 1, 2: 8, 3: 9},
                    3: {0: 0, 1: 1, 2: 8, 3: 9},
                    4: {2: 6, 3: 7},
                    5: {0: 77, 1: 88, 2: 6, 3: 7, 4: 11, 5: 22,
                        6: 33, 7: 44, 8: 55, 9: 66},
                    6: {0: 4, 1: 5, 2: 8, 3: 9},
                    7: {0: 4, 1: 5, 2: 8, 3: 9},
                    8: {0: 2, 1: 7, 2: "PS", 3: 3, 4: 6},
                    9: {0: 7, 1: 2, 2: "PS", 3: 3, 4: 6},
                    11: {0: 5}, 22: {0: 5}, 33: {0: 5}, 44: {0: 5},
                    55: {0: 5}, 66: {0: 5}, 77: {0: 5}, 88: {0: 5}}

    selectedSwitches = [2, 3, 6, 7, 8, 9, 0, 1, 4, 5]
    clusters = {0: [0, 1, 2, 3], 1: [4, 5, 6, 7]}

    cutPorts = {0: {2: 2}, 1: {2: 2}, 2: {2: 8}, 3: {3: 9},
                4: {3: 7}, 5: {3: 7}, 6: {2: 8}, 7: {3: 9},
                8: {2: "PS"}, 9: {2: "PS"},
                11: {0: 5}, 22: {0: 5}, 33: {0: 5}, 44: {0: 5},
                55: {0: 5}, 66: {0: 5}, 77: {0: 5}, 88: {0: 5}}

    neighborsofEachSwitch = {0: [2, 3], 1: [2, 3],
                             2: [0, 1, 8, 9], 3: [0, 1, 8, 9],
                             4: [6, 7],
                             5: [11, 22, 33, 44, 55, 66, 77, 88, 6, 7],
                             6: [4, 5, 8, 9], 7: [4, 5, 8, 9],
                             8: [2, 7, 3, 6], 9: [2, 7, 3, 6],
                             11: [5], 22: [5], 33: [5], 44: [5],
                             55: [5], 66: [5], 77: [5], 88: [5]}

    pSwitchesNumber = len(pSwitchesTopology)

    numberSlotsSwitches = {0: [0], 1: [0], 2: [], 3: [0], 4: [], 5: [0],
                           6: [0], 7: [0], 8: [0], 9: []}

    workersTopology = {11: 5, 22: 5, 33: 5, 44: 5,
                       55: 5, 66: 5, 77: 5, 88: 5}

    pWorkerPorts = {11: {0: 5}, 22: {0: 5}, 33: {0: 5}, 44: {0: 5},
                    55: {0: 5}, 66: {0: 5}, 77: {0: 5}, 88: {0: 5}}

    workersNumber = len(workersTopology)

    fragmentsofEachWorker = {11: ["A0", "B0", "C0"], 22: ["A1", "B1", "C1"],
                             33: ["A2", "B2", "C2"], 44: ["A3", "B3", "C3"],
                             55: ["A4", "B4", "C4"], 66: ["A5", "B5", "C5"],
                             77: ["A6", "B6", "C6"], 88: ["A7", "B7", "C7"]}
    totalWorkers = fragmentsofEachWorker.copy()
    numAllFrags = sum(len(v) for v in fragmentsofEachWorker.values())

    stepsToSwitches = {11: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       22: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       33: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       44: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       55: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       66: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       77: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       88: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3]}

    if state == "Optimaze":
        result = _optimize_env(pSwitchPorts, neighborsofEachSwitch,
                               workersTopology, pWorkerPorts,
                               fragmentsofEachWorker)
        (pSwitchPorts, neighborsofEachSwitch, workersTopology,
         pWorkerPorts, workersNumber, fragmentsofEachWorker,
         numAllFrags) = result

    return (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
            pSwitchesNumber, numberSlotsSwitches, workersTopology,
            pWorkerPorts, workersNumber, numAllFrags,
            fragmentsofEachWorker, totalWorkers, stepsToSwitches,
            cutPorts, selectedSwitches, clusters)


# ---------------------------------------------------------------------------
# env_2Clusters_Percentages
# ---------------------------------------------------------------------------

def env_2Clusters_Percentages(state):
    pSwitchesTopology = {0: [2, 3], 1: [2, 3], 2: [0, 1, 8, 9],
                         3: [0, 1], 4: [6, 7], 5: [6, 7], 6: [4, 5],
                         7: [4, 5, 8, 9], 8: [2, 7, "PS"], 9: [2, 7, "PS"]}

    pSwitchPorts = {0: {0: 11, 1: 22, 2: 2, 3: 3},
                    1: {0: 33, 1: 44, 2: 2, 3: 3},
                    2: {0: 0, 1: 1, 2: 8, 3: 9},
                    3: {0: 0, 1: 1, 2: 8, 3: 9},
                    4: {0: 55, 1: 66, 2: 6, 3: 7},
                    5: {0: 77, 1: 88, 2: 6, 3: 7},
                    6: {0: 4, 1: 5, 2: 8, 3: 9},
                    7: {0: 4, 1: 5, 2: 8, 3: 9},
                    8: {0: 2, 1: 7, 2: "PS", 3: 3, 4: 6},
                    9: {0: 7, 1: 2, 2: "PS", 3: 3, 4: 6},
                    11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                    55: {0: 4}, 66: {0: 4}, 77: {0: 5}, 88: {0: 5}}

    selectedSwitches = [2, 3, 6, 7, 8, 9, 0, 1, 4, 5]

    cutPorts = {0: {2: 2}, 1: {2: 2}, 2: {2: 8}, 3: {3: 9},
                4: {3: 7}, 5: {3: 7}, 6: {2: 8}, 7: {3: 9},
                8: {2: "PS"}, 9: {2: "PS"},
                11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                55: {0: 4}, 66: {0: 4}, 77: {0: 5}, 88: {0: 5}}

    neighborsofEachSwitch = {0: [11, 22, 2, 3], 1: [33, 44, 2, 3],
                             2: [0, 1, 8, 9], 3: [0, 1, 8, 9],
                             4: [55, 66, 6, 7], 5: [77, 88, 6, 7],
                             6: [4, 5, 8, 9], 7: [4, 5, 8, 9],
                             8: [2, 7, 3, 6], 9: [2, 7, 3, 6],
                             11: [0], 22: [0], 33: [1], 44: [1],
                             55: [4], 66: [4], 77: [5], 88: [5]}

    pSwitchesNumber = len(pSwitchesTopology)

    numberSlotsSwitches = {0: [0], 1: [0], 2: [0], 3: [0], 4: [0], 5: [0],
                           6: [0], 7: [0], 8: [0], 9: [0]}

    workersTopology = {11: 0, 22: 0, 33: 1, 44: 1,
                       55: 4, 66: 4, 77: 5, 88: 5}

    clusters = {0: [0, 1, 2, 3], 1: [4, 5, 6, 7]}

    pWorkerPorts = {11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                    55: {0: 4}, 66: {0: 4}, 77: {0: 5}, 88: {0: 5}}

    workersNumber = len(workersTopology)

    fragmentsofEachWorker = {11: ["A0", "B0", "C0", "D0", "E0", "F0"],
                             22: ["A1", "B1", "C1", "D1", "E1", "F1"],
                             33: ["A2", "B2", "C2", "D2", "E2", "F2"],
                             44: ["A3", "B3", "C3", "D3", "E3", "F3"],
                             55: ["A4", "B4", "C4", "D4", "E4", "F4"],
                             66: ["A5", "B5", "C5", "D5", "E5", "F5"],
                             77: ["A6", "B6", "C6", "D6", "E6", "F6"],
                             88: ["A7", "B7", "C7", "D7", "E7", "F7"]}

    totalWorkers = fragmentsofEachWorker.copy()
    numAllFrags = sum(len(v) for v in fragmentsofEachWorker.values())

    stepsToSwitches = {11: [1, 3, 2, 2, 5, 5, 6, 4, 3, 3],
                       22: [1, 3, 2, 2, 5, 5, 6, 4, 3, 3],
                       33: [3, 1, 2, 2, 5, 5, 6, 4, 3, 3],
                       44: [3, 1, 2, 2, 5, 5, 6, 4, 3, 3],
                       55: [5, 5, 4, 6, 1, 3, 2, 2, 3, 3],
                       66: [5, 5, 4, 6, 1, 3, 2, 2, 3, 3],
                       77: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       88: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3]}

    if state == "Optimaze":
        result = _optimize_env(pSwitchPorts, neighborsofEachSwitch,
                               workersTopology, pWorkerPorts,
                               fragmentsofEachWorker)
        (pSwitchPorts, neighborsofEachSwitch, workersTopology,
         pWorkerPorts, workersNumber, fragmentsofEachWorker,
         numAllFrags) = result

    return (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
            pSwitchesNumber, numberSlotsSwitches, workersTopology,
            pWorkerPorts, workersNumber, numAllFrags,
            fragmentsofEachWorker, totalWorkers, stepsToSwitches,
            cutPorts, selectedSwitches, clusters)
