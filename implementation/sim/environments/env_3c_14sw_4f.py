"""
env_3c_14sw_4f — 3-cluster env, 14 switches, 4 frags/worker.

Workers use IDs >= 200 to avoid collision with switch IDs.
"""
from sim.environments._common import build_env


def env_3c_14sw_4f(state):
    pSwitchesTopology = {
        0: [2, 3], 1: [2, 3],
        2: [0, 1, 10], 3: [0, 1, 11],
        4: [6, 7], 5: [6, 7],
        6: [4, 5, 10], 7: [4, 5, 11],
        8: [12, 13], 9: [12, 13],
        12: [8, 9, 10], 13: [8, 9, 11],
        10: [2, 6, 12, "PS"], 11: [3, 7, 13, "PS"],
    }

    pSwitchPorts = {
        0: {0: 211, 1: 212, 2: 2, 3: 3},
        1: {0: 213, 1: 214, 2: 2, 3: 3},
        2: {0: 0, 1: 1, 2: 10},
        3: {0: 0, 1: 1, 2: 11},
        4: {0: 215, 1: 216, 2: 6, 3: 7},
        5: {0: 217, 1: 218, 2: 6, 3: 7},
        6: {0: 4, 1: 5, 2: 10},
        7: {0: 4, 1: 5, 2: 11},
        8: {0: 219, 1: 220, 2: 12, 3: 13},
        9: {0: 221, 1: 222, 2: 12, 3: 13},
        12: {0: 8, 1: 9, 2: 10},
        13: {0: 8, 1: 9, 2: 11},
        10: {0: 2, 1: 6, 2: 12, 3: "PS"},
        11: {0: 3, 1: 7, 2: 13, 3: "PS"},
        211: {0: 0}, 212: {0: 0}, 213: {0: 1}, 214: {0: 1},
        215: {0: 4}, 216: {0: 4}, 217: {0: 5}, 218: {0: 5},
        219: {0: 8}, 220: {0: 8}, 221: {0: 9}, 222: {0: 9},
    }

    clusters = {0: [0, 1, 2, 3], 1: [4, 5, 6, 7], 2: [8, 9, 12, 13]}
    # Archive ordering convention: aggregation switches first, then the
    # PS-facing cores, then ToRs (port-count ranking would starve FlexINA).
    selectedSwitches = [2, 3, 6, 7, 12, 13, 10, 11, 0, 1, 4, 5, 8, 9]

    cutPorts = {
        10: {3: "PS"}, 11: {3: "PS"},
        211: {0: 0}, 212: {0: 0}, 213: {0: 1}, 214: {0: 1},
        215: {0: 4}, 216: {0: 4}, 217: {0: 5}, 218: {0: 5},
        219: {0: 8}, 220: {0: 8}, 221: {0: 9}, 222: {0: 9},
    }
    # cut ports for switches (cluster cut ports pointing at fabric).
    cutPorts.update({0: {3: 3}, 1: {2: 2}, 2: {2: 10}, 3: {2: 11},
                     4: {3: 7}, 5: {2: 6}, 6: {2: 10}, 7: {2: 11},
                     12: {2: 10}, 13: {2: 11}})

    neighborsofEachSwitch = {
        0: [211, 212, 2, 3], 1: [213, 214, 2, 3],
        2: [0, 1, 10], 3: [0, 1, 11],
        4: [215, 216, 6, 7], 5: [217, 218, 6, 7],
        6: [4, 5, 10], 7: [4, 5, 11],
        8: [219, 220, 12, 13], 9: [221, 222, 12, 13],
        12: [8, 9, 10], 13: [8, 9, 11],
        10: [2, 6, 12], 11: [3, 7, 13],
        211: [0], 212: [0], 213: [1], 214: [1],
        215: [4], 216: [4], 217: [5], 218: [5],
        219: [8], 220: [8], 221: [9], 222: [9],
    }

    numberSlotsSwitches = {0: [0], 1: [0], 2: [0], 3: [0], 4: [0], 5: [0],
                           6: [0], 7: [0], 8: [0], 9: [0], 10: [], 11: [],
                           12: [0], 13: [0]}

    workersTopology = {211: 0, 212: 0, 213: 1, 214: 1,
                       215: 4, 216: 4, 217: 5, 218: 5,
                       219: 8, 220: 8, 221: 9, 222: 9}

    pWorkerPorts = {211: {0: 0}, 212: {0: 0}, 213: {0: 1}, 214: {0: 1},
                    215: {0: 4}, 216: {0: 4}, 217: {0: 5}, 218: {0: 5},
                    219: {0: 8}, 220: {0: 8}, 221: {0: 9}, 222: {0: 9}}

    fragmentsofEachWorker = {211: ["A0", "B0", "C0", "D0"],
                             212: ["A1", "B1", "C1", "D1"],
                             213: ["A2", "B2", "C2", "D2"],
                             214: ["A3", "B3", "C3", "D3"],
                             215: ["A4", "B4", "C4", "D4"],
                             216: ["A5", "B5", "C5", "D5"],
                             217: ["A6", "B6", "C6", "D6"],
                             218: ["A7", "B7", "C7", "D7"],
                             219: ["A8", "B8", "C8", "D8"],
                             220: ["A9", "B9", "C9", "D9"],
                             221: ["AA", "BA", "CA", "DA"],
                             222: ["AB", "BB", "CB", "DB"]}

    # Hops from each worker to each switch (own ToR = 1), BFS-derived; a
    # flat [1]*n table would disable arrival-time pruning in the models.
    stepsToSwitches = {
        211: [1, 3, 2, 2, 5, 5, 4, 4, 5, 5, 3, 3, 4, 4],
        212: [1, 3, 2, 2, 5, 5, 4, 4, 5, 5, 3, 3, 4, 4],
        213: [3, 1, 2, 2, 5, 5, 4, 4, 5, 5, 3, 3, 4, 4],
        214: [3, 1, 2, 2, 5, 5, 4, 4, 5, 5, 3, 3, 4, 4],
        215: [5, 5, 4, 4, 1, 3, 2, 2, 5, 5, 3, 3, 4, 4],
        216: [5, 5, 4, 4, 1, 3, 2, 2, 5, 5, 3, 3, 4, 4],
        217: [5, 5, 4, 4, 3, 1, 2, 2, 5, 5, 3, 3, 4, 4],
        218: [5, 5, 4, 4, 3, 1, 2, 2, 5, 5, 3, 3, 4, 4],
        219: [5, 5, 4, 4, 5, 5, 4, 4, 1, 3, 3, 3, 2, 2],
        220: [5, 5, 4, 4, 5, 5, 4, 4, 1, 3, 3, 3, 2, 2],
        221: [5, 5, 4, 4, 5, 5, 4, 4, 3, 1, 3, 3, 2, 2],
        222: [5, 5, 4, 4, 5, 5, 4, 4, 3, 1, 3, 3, 2, 2],
    }

    return build_env(
        state,
        pSwitchesTopology=pSwitchesTopology, pSwitchPorts=pSwitchPorts,
        neighborsofEachSwitch=neighborsofEachSwitch,
        numberSlotsSwitches=numberSlotsSwitches, workersTopology=workersTopology,
        pWorkerPorts=pWorkerPorts, fragmentsofEachWorker=fragmentsofEachWorker,
        stepsToSwitches=stepsToSwitches, cutPorts=cutPorts,
        selectedSwitches=selectedSwitches, clusters=clusters)
