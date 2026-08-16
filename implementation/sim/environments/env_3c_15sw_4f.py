"""
env_3c_15sw_4f — 3-cluster env, 15 switches, 4 frags/worker.

Same construction as env_4c_20sw_4f / env_5c_25sw_4f, one cluster smaller:
each cluster has 2 ToR pairs (hosting 2 workers each) + 2 aggregation
switches; the 3 clusters are joined by a 3-switch core ring (each core
switch carries "PS"). 3 x 4 + 3 core = 15.

This is the small end of the big_env scaling series (15/20/25 switches) —
unlike env_3c_14sw_4f (2 core switches, cluster 2 wired to ToRs 12/13) it
keeps the exact wiring pattern of the 20- and 25-switch envs so the three
points differ only in cluster count.

Switch IDs are contiguous 0..14 (ToRs/aggregation 0-11, core 12-14) so that
stepsToSwitches rows index directly by switch id. Workers use IDs >= 300 to
avoid collision.
"""
from sim.environments._common import build_env


def env_3c_15sw_4f(state):
    pSwitchesTopology = {
        0: [2, 3], 1: [2, 3],
        2: [0, 1, 12], 3: [0, 1, 14],
        4: [6, 7], 5: [6, 7],
        6: [4, 5, 13], 7: [4, 5, 12],
        8: [10, 11], 9: [10, 11],
        10: [8, 9, 14], 11: [8, 9, 13],
        12: [2, 7, 13, 14, "PS"], 13: [6, 11, 14, 12, "PS"],
        14: [10, 3, 12, 13, "PS"],
    }

    pSwitchPorts = {
        0: {0: 311, 1: 312, 2: 2, 3: 3},
        1: {0: 313, 1: 314, 2: 2, 3: 3},
        2: {0: 0, 1: 1, 2: 12},
        3: {0: 0, 1: 1, 2: 14},
        4: {0: 315, 1: 316, 2: 6, 3: 7},
        5: {0: 317, 1: 318, 2: 6, 3: 7},
        6: {0: 4, 1: 5, 2: 13},
        7: {0: 4, 1: 5, 2: 12},
        8: {0: 319, 1: 320, 2: 10, 3: 11},
        9: {0: 321, 1: 322, 2: 10, 3: 11},
        10: {0: 8, 1: 9, 2: 14},
        11: {0: 8, 1: 9, 2: 13},
        12: {0: 2, 1: 7, 2: 13, 3: 14, 4: "PS"},
        13: {0: 6, 1: 11, 2: 14, 3: 12, 4: "PS"},
        14: {0: 10, 1: 3, 2: 12, 3: 13, 4: "PS"},
        311: {0: 0}, 312: {0: 0}, 313: {0: 1}, 314: {0: 1},
        315: {0: 4}, 316: {0: 4}, 317: {0: 5}, 318: {0: 5},
        319: {0: 8}, 320: {0: 8}, 321: {0: 9}, 322: {0: 9},
    }

    clusters = {0: [0, 1, 2, 3], 1: [4, 5, 6, 7], 2: [8, 9, 10, 11]}
    # Archive ordering convention (cf. env_4c_20sw_4f): per-cluster
    # aggregation switches first, then the PS-facing core, then ToRs.
    selectedSwitches = [2, 3, 6, 7, 10, 11,
                        12, 13, 14,
                        0, 1, 4, 5, 8, 9]

    cutPorts = {
        12: {4: "PS"}, 13: {4: "PS"}, 14: {4: "PS"},
        311: {0: 0}, 312: {0: 0}, 313: {0: 1}, 314: {0: 1},
        315: {0: 4}, 316: {0: 4}, 317: {0: 5}, 318: {0: 5},
        319: {0: 8}, 320: {0: 8}, 321: {0: 9}, 322: {0: 9},
    }
    # cut ports for switches (cluster cut ports pointing at fabric / core).
    cutPorts.update({0: {3: 3}, 1: {3: 3}, 2: {2: 12}, 3: {2: 14},
                     4: {3: 7}, 5: {3: 7}, 6: {2: 13}, 7: {2: 12},
                     8: {3: 11}, 9: {3: 11}, 10: {2: 14}, 11: {2: 13}})

    neighborsofEachSwitch = {
        0: [311, 312, 2, 3], 1: [313, 314, 2, 3],
        2: [0, 1, 12], 3: [0, 1, 14],
        4: [315, 316, 6, 7], 5: [317, 318, 6, 7],
        6: [4, 5, 13], 7: [4, 5, 12],
        8: [319, 320, 10, 11], 9: [321, 322, 10, 11],
        10: [8, 9, 14], 11: [8, 9, 13],
        12: [2, 7, 13, 14], 13: [6, 11, 14, 12], 14: [10, 3, 12, 13],
        311: [0], 312: [0], 313: [1], 314: [1],
        315: [4], 316: [4], 317: [5], 318: [5],
        319: [8], 320: [8], 321: [9], 322: [9],
    }

    numberSlotsSwitches = {0: [0], 1: [0], 2: [0], 3: [0], 4: [0], 5: [0],
                           6: [0], 7: [0], 8: [0], 9: [0], 10: [0], 11: [0],
                           12: [], 13: [], 14: []}

    workersTopology = {311: 0, 312: 0, 313: 1, 314: 1,
                       315: 4, 316: 4, 317: 5, 318: 5,
                       319: 8, 320: 8, 321: 9, 322: 9}

    pWorkerPorts = {311: {0: 0}, 312: {0: 0}, 313: {0: 1}, 314: {0: 1},
                    315: {0: 4}, 316: {0: 4}, 317: {0: 5}, 318: {0: 5},
                    319: {0: 8}, 320: {0: 8}, 321: {0: 9}, 322: {0: 9}}

    fragmentsofEachWorker = {311: ["A0", "B0", "C0", "D0"],
                             312: ["A1", "B1", "C1", "D1"],
                             313: ["A2", "B2", "C2", "D2"],
                             314: ["A3", "B3", "C3", "D3"],
                             315: ["A4", "B4", "C4", "D4"],
                             316: ["A5", "B5", "C5", "D5"],
                             317: ["A6", "B6", "C6", "D6"],
                             318: ["A7", "B7", "C7", "D7"],
                             319: ["A8", "B8", "C8", "D8"],
                             320: ["A9", "B9", "C9", "D9"],
                             321: ["AA", "BA", "CA", "DA"],
                             322: ["AB", "BB", "CB", "DB"]}

    # Hops from each worker to each switch, indexed by switch id (a worker's
    # own ToR is 1), derived by BFS over pSwitchesTopology — same convention
    # as the other envs.
    stepsToSwitches = {
        311: [1, 3, 2, 2, 5, 5, 5, 4, 5, 5, 4, 5, 3, 4, 3],
        312: [1, 3, 2, 2, 5, 5, 5, 4, 5, 5, 4, 5, 3, 4, 3],
        313: [3, 1, 2, 2, 5, 5, 5, 4, 5, 5, 4, 5, 3, 4, 3],
        314: [3, 1, 2, 2, 5, 5, 5, 4, 5, 5, 4, 5, 3, 4, 3],
        315: [5, 5, 4, 5, 1, 3, 2, 2, 5, 5, 5, 4, 3, 3, 4],
        316: [5, 5, 4, 5, 1, 3, 2, 2, 5, 5, 5, 4, 3, 3, 4],
        317: [5, 5, 4, 5, 3, 1, 2, 2, 5, 5, 5, 4, 3, 3, 4],
        318: [5, 5, 4, 5, 3, 1, 2, 2, 5, 5, 5, 4, 3, 3, 4],
        319: [5, 5, 5, 4, 5, 5, 4, 5, 1, 3, 2, 2, 4, 3, 3],
        320: [5, 5, 5, 4, 5, 5, 4, 5, 1, 3, 2, 2, 4, 3, 3],
        321: [5, 5, 5, 4, 5, 5, 4, 5, 3, 1, 2, 2, 4, 3, 3],
        322: [5, 5, 5, 4, 5, 5, 4, 5, 3, 1, 2, 2, 4, 3, 3],
    }

    return build_env(
        state,
        pSwitchesTopology=pSwitchesTopology, pSwitchPorts=pSwitchPorts,
        neighborsofEachSwitch=neighborsofEachSwitch,
        numberSlotsSwitches=numberSlotsSwitches, workersTopology=workersTopology,
        pWorkerPorts=pWorkerPorts, fragmentsofEachWorker=fragmentsofEachWorker,
        stepsToSwitches=stepsToSwitches, cutPorts=cutPorts,
        selectedSwitches=selectedSwitches, clusters=clusters)
