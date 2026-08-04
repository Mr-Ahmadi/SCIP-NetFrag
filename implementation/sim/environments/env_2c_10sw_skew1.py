"""
env_2c_10sw_skew1 — maximally skewed 2-cluster env (archive env_2Clusters_Zipf2).
All 8 workers on switch 5. Post-optimize neighbor lists match the archive's
runtime output, which dropped workers via an ascending-index deletion (keeps
only even-indexed entries).
"""
from sim.environments._common import build_env


def env_2c_10sw_skew1(state):
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

    numberSlotsSwitches = {0: [0], 1: [0], 2: [], 3: [0], 4: [], 5: [0],
                           6: [0], 7: [0], 8: [0], 9: []}

    workersTopology = {11: 5, 22: 5, 33: 5, 44: 5,
                       55: 5, 66: 5, 77: 5, 88: 5}

    pWorkerPorts = {11: {0: 5}, 22: {0: 5}, 33: {0: 5}, 44: {0: 5},
                    55: {0: 5}, 66: {0: 5}, 77: {0: 5}, 88: {0: 5}}

    fragmentsofEachWorker = {11: ["A0", "B0", "C0"], 22: ["A1", "B1", "C1"],
                             33: ["A2", "B2", "C2"], 44: ["A3", "B3", "C3"],
                             55: ["A4", "B4", "C4"], 66: ["A5", "B5", "C5"],
                             77: ["A6", "B6", "C6"], 88: ["A7", "B7", "C7"]}

    stepsToSwitches = {11: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       22: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       33: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       44: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       55: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       66: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       77: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       88: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3]}

    env = build_env(
        state,
        pSwitchesTopology=pSwitchesTopology, pSwitchPorts=pSwitchPorts,
        neighborsofEachSwitch=neighborsofEachSwitch,
        numberSlotsSwitches=numberSlotsSwitches, workersTopology=workersTopology,
        pWorkerPorts=pWorkerPorts, fragmentsofEachWorker=fragmentsofEachWorker,
        stepsToSwitches=stepsToSwitches, cutPorts=cutPorts,
        selectedSwitches=selectedSwitches, clusters=clusters)
    env[2][5] = [11, 33, 55, 77, 6]
    return env
