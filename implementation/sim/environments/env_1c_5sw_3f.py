"""
env_1c_5sw_3f — 1 cluster, 5 switches, 4 active workers, 3 frags/worker.

Topology:
    switches 0,1 : ToR pairs (each hosts 2 workers, dedup'd to 1 by Optimaze)
    switches 2,3 : aggregation layer (each hosts 2 workers, dedup'd)
    switch  4    : spine, carries "PS"

Cluster: {0: [0,1,2,3]} — agg switch 4 is not clustered.
"""
from sim.environments._common import build_env, rank_switches_by_ports


def env_1c_5sw_3f(state):
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
    selectedSwitches = rank_switches_by_ports(pSwitchesTopology, pSwitchPorts)
    cutPorts = {0: {3: 2}, 1: {2: 3}, 2: {4: 4}, 3: {4: 4}, 4: {4: "PS"},
                11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                55: {0: 2}, 66: {0: 2}, 77: {0: 3}, 88: {0: 3}}

    neighborsofEachSwitch = {0: [11, 22, 2, 3], 1: [33, 44, 2, 3],
                             2: [55, 66, 0, 1, 4], 3: [77, 88, 0, 1, 4],
                             4: [2, 3],
                             11: [0], 22: [0], 33: [1], 44: [1],
                             55: [2], 66: [2], 77: [3], 88: [3]}

    numberSlotsSwitches = {0: [], 1: [0], 2: [0], 3: [], 4: [0]}

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
