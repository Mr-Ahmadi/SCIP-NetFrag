"""
env_tree_7sw_3f — 3-layer tree, 7 switches, 4 active workers, 3 frags/worker.

Ported verbatim from ``archive/Untitled.py`` (``env_tree``, the topology the
submitted version used as the "7-switch tree" point of its topology
comparison).  Kept for the ``topologies`` block, which compares this tree
against the 5-switch single-cluster and 10-switch two-cluster fat trees.

Topology (3 layers, single root):
    switches 0,1,2,3 : access layer (each hosts 2 workers, dedup'd to 1
                       by Optimaze)
    switches 4,5     : aggregation layer — 4 over {0,1}, 5 over {2,3}
    switch  6        : root, carries "PS"

The name breaks the ``env_<C>c_<S>sw_<load>`` convention on purpose: this is
the only non-clustered topology in the set.  ``clusters = []`` disables the
Phase-2 clustering restriction, so aggregation sets are formed over all
sources and only the port-count filtration of Phase 2 applies — which is
exactly how the archive ran it.
"""
from sim.environments._common import build_env


def env_tree_7sw_3f(state):
    pSwitchesTopology = {0: [4], 1: [4], 2: [5], 3: [5],
                         4: [0, 1, 6], 5: [2, 3, 6], 6: [4, 5, "PS"]}

    pSwitchPorts = {0: {0: 4, 2: 11, 3: 22},
                    1: {0: 4, 2: 33, 3: 44},
                    2: {1: 5, 2: 55, 3: 66},
                    3: {1: 5, 2: 77, 3: 88},
                    4: {0: 0, 1: 1, 4: 6},
                    5: {2: 2, 3: 3, 4: 6},
                    6: {0: 4, 1: 5, 2: "PS"},
                    11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                    55: {0: 2}, 66: {0: 2}, 77: {0: 3}, 88: {0: 3}}

    clusters = []
    selectedSwitches = [4, 5, 6, 0, 1, 2, 3]

    cutPorts = {0: {0: 4}, 1: {0: 4}, 2: {1: 5}, 3: {1: 5},
                4: {4: 6}, 5: {4: 6}, 6: {2: "PS"},
                11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                55: {0: 2}, 66: {0: 2}, 77: {0: 3}, 88: {0: 3}}

    neighborsofEachSwitch = {0: [11, 22, 4], 1: [33, 44, 4],
                             2: [55, 66, 5], 3: [77, 88, 5],
                             4: [0, 1, 6], 5: [2, 3, 6], 6: [4, 5],
                             11: [0], 22: [0], 33: [1], 44: [1],
                             55: [2], 66: [2], 77: [3], 88: [3]}

    numberSlotsSwitches = {0: [0], 1: [0], 2: [0], 3: [0],
                           4: [0], 5: [0], 6: [0]}

    workersTopology = {11: 0, 22: 0, 33: 1, 44: 1,
                       55: 2, 66: 2, 77: 3, 88: 3}

    pWorkerPorts = {11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                    55: {0: 2}, 66: {0: 2}, 77: {0: 3}, 88: {0: 3}}

    fragmentsofEachWorker = {11: ["A0", "B0", "C0"], 22: ["A1", "B1", "C1"],
                             33: ["A2", "B2", "C2"], 44: ["A3", "B3", "C3"],
                             55: ["A4", "B4", "C4"], 66: ["A5", "B5", "C5"],
                             77: ["A6", "B6", "C6"], 88: ["A7", "B7", "C7"]}

    stepsToSwitches = {11: [1, 3, 5, 5, 2, 4, 3], 22: [1, 3, 5, 5, 2, 4, 3],
                       33: [3, 1, 5, 5, 2, 4, 3], 44: [3, 1, 5, 5, 2, 4, 3],
                       55: [5, 5, 1, 3, 4, 2, 3], 66: [5, 5, 1, 3, 4, 2, 3],
                       77: [5, 5, 3, 1, 4, 2, 3], 88: [5, 5, 3, 1, 4, 2, 3]}

    return build_env(
        state,
        pSwitchesTopology=pSwitchesTopology, pSwitchPorts=pSwitchPorts,
        neighborsofEachSwitch=neighborsofEachSwitch,
        numberSlotsSwitches=numberSlotsSwitches, workersTopology=workersTopology,
        pWorkerPorts=pWorkerPorts, fragmentsofEachWorker=fragmentsofEachWorker,
        stepsToSwitches=stepsToSwitches, cutPorts=cutPorts,
        selectedSwitches=selectedSwitches, clusters=clusters)
