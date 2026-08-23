"""
env_1c_5sw_3f_m2 — env_1c_5sw_3f with switch memory at level 2.

Identical to :mod:`env_1c_5sw_3f` in topology, ports, worker placement and
load; the *only* difference is ``numberSlotsSwitches``.
Aggregation/spine switches {1, 2, 4} carry two memory slots and the ToR
switches {0, 3} carry one.

The three-point series env_1c_5sw_3f (level 1) / _m2 / _m3 is what the
``switch_memory`` block sweeps, so that the effect measured is memory size
alone.  Slot maps ported verbatim from ``archive/Untitled.py``
(``env_1Cluster_Test``, ``env_1Cluster_Test_2``, ``env_1Cluster_Test_3``).
"""
from sim.environments._common import build_env


def env_1c_5sw_3f_m2(state):
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

    numberSlotsSwitches = {0: [0], 1: [0, 1], 2: [0, 1], 3: [0], 4: [0, 1]}

    workersTopology = {11: 0, 22: 0, 33: 1, 44: 1,
                       55: 2, 66: 2, 77: 3, 88: 3}

    pWorkerPorts = {11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                    55: {0: 2}, 66: {0: 2}, 77: {0: 3}, 88: {0: 3}}

    fragmentsofEachWorker = {11: ["A0", "B0", "C0"], 22: ["A1", "B1", "C1"],
                             33: ["A2", "B2", "C2"], 44: ["A3", "B3", "C3"],
                             55: ["A4", "B4", "C4"], 66: ["A5", "B5", "C5"],
                             77: ["A6", "B6", "C6"], 88: ["A7", "B7", "C7"]}

    stepsToSwitches = {11: [1, 3, 2, 2, 3], 22: [1, 3, 2, 2, 3],
                       33: [3, 1, 2, 2, 3], 44: [3, 1, 2, 2, 3],
                       55: [2, 2, 1, 3, 2], 66: [2, 2, 1, 3, 2],
                       77: [2, 2, 3, 1, 2], 88: [2, 2, 3, 1, 2]}

    return build_env(
        state,
        pSwitchesTopology=pSwitchesTopology, pSwitchPorts=pSwitchPorts,
        neighborsofEachSwitch=neighborsofEachSwitch,
        numberSlotsSwitches=numberSlotsSwitches, workersTopology=workersTopology,
        pWorkerPorts=pWorkerPorts, fragmentsofEachWorker=fragmentsofEachWorker,
        stepsToSwitches=stepsToSwitches, cutPorts=cutPorts,
        selectedSwitches=selectedSwitches, clusters=clusters)
