"""
env_1c_5sw_3f_2acc — 1 cluster, 5 switches, 8 workers on 2 access switches,
3 frags/worker.

Ported verbatim from ``archive/Untitled.py`` (``env_1Cluster``); this is the
"5-switch single-cluster Fat-Tree" point of the submitted version's topology
comparison, and reproduces its Fig. 3 column exactly.

Same wiring, memory budget, cluster and switch ranking as
:mod:`env_1c_5sw_3f`.  The one difference is worker placement: all eight
workers hang off switches 0 and 1 (four each) instead of being spread over
0-3, so Phase 1 collapses them to *two* sources rather than four.  That is
what makes this the denser-access variant, and why its fragment counts are
much lower than :mod:`env_1c_5sw_3f`'s for the same load.

Topology:
    switches 0,1 : access layer, 4 workers each (dedup'd to 1 by Optimaze)
    switches 2,3 : aggregation layer
    switch  4    : spine, carries "PS"

Cluster: {0: [0,1,2,3]} — spine switch 4 is not clustered.
"""
from sim.environments._common import build_env


def env_1c_5sw_3f_2acc(state):
    pSwitchesTopology = {0: [2, 3], 1: [2, 3], 2: [0, 1, 4],
                         3: [0, 1, 4], 4: [2, 3, "PS"]}

    pSwitchPorts = {0: {0: 11, 1: 22, 2: 3, 3: 2, 4: 33, 5: 44},
                    1: {0: 55, 1: 66, 2: 3, 3: 2, 4: 77, 5: 88},
                    2: {0: 0, 1: 1, 4: 4},
                    3: {0: 0, 1: 1, 4: 4},
                    4: {0: 2, 1: 3, 4: "PS"},
                    11: {0: 0}, 22: {0: 0}, 33: {0: 0}, 44: {0: 0},
                    55: {0: 1}, 66: {0: 1}, 77: {0: 1}, 88: {0: 1}}

    clusters = {0: [0, 1, 2, 3]}
    selectedSwitches = [2, 3, 4, 0, 1]
    cutPorts = {0: {3: 2}, 1: {2: 3}, 2: {4: 4}, 3: {4: 4}, 4: {4: "PS"},
                11: {0: 0}, 22: {0: 0}, 33: {0: 0}, 44: {0: 0},
                55: {0: 1}, 66: {0: 1}, 77: {0: 1}, 88: {0: 1}}

    neighborsofEachSwitch = {0: [11, 22, 33, 44, 2, 3],
                             1: [55, 66, 77, 88, 2, 3],
                             2: [0, 1, 4], 3: [0, 1, 4], 4: [2, 3],
                             11: [0], 22: [0], 33: [0], 44: [0],
                             55: [1], 66: [1], 77: [1], 88: [1]}

    numberSlotsSwitches = {0: [], 1: [0], 2: [0], 3: [], 4: [0]}

    workersTopology = {11: 0, 22: 0, 33: 0, 44: 0,
                       55: 1, 66: 1, 77: 1, 88: 1}

    pWorkerPorts = {11: {0: 0}, 22: {0: 0}, 33: {0: 0}, 44: {0: 0},
                    55: {0: 1}, 66: {0: 1}, 77: {0: 1}, 88: {0: 1}}

    fragmentsofEachWorker = {11: ["A0", "B0", "C0"], 22: ["A1", "B1", "C1"],
                             33: ["A2", "B2", "C2"], 44: ["A3", "B3", "C3"],
                             55: ["A4", "B4", "C4"], 66: ["A5", "B5", "C5"],
                             77: ["A6", "B6", "C6"], 88: ["A7", "B7", "C7"]}

    stepsToSwitches = {11: [1, 3, 2, 2, 3], 22: [1, 3, 2, 2, 3],
                       33: [1, 3, 2, 2, 3], 44: [1, 3, 2, 2, 3],
                       55: [3, 1, 2, 2, 3], 66: [3, 1, 2, 2, 3],
                       77: [3, 1, 2, 2, 3], 88: [3, 1, 2, 2, 3]}

    return build_env(
        state,
        pSwitchesTopology=pSwitchesTopology, pSwitchPorts=pSwitchPorts,
        neighborsofEachSwitch=neighborsofEachSwitch,
        numberSlotsSwitches=numberSlotsSwitches, workersTopology=workersTopology,
        pWorkerPorts=pWorkerPorts, fragmentsofEachWorker=fragmentsofEachWorker,
        stepsToSwitches=stepsToSwitches, cutPorts=cutPorts,
        selectedSwitches=selectedSwitches, clusters=clusters)
