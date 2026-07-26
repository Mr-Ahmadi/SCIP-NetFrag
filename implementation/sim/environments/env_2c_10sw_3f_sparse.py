"""
env_2c_10sw_3f_sparse — sparse-slot variant of the 2-cluster reference env.

Identical network (topology, ports, workers, fragments, steps-to-switches,
clusters, selectedSwitches, cutPorts) to :func:`env_2c_10sw_3f`, with one
difference: only a subset of switches expose an aggregation slot, matching
the legacy ``env_2Clusters`` definition preserved in ``archive/Untitled.py``.

Sparse-slot mask (switches with empty ``numberSlotsSwitches[sw]``):

    switches 2, 4, 6, 7, 9   — no aggregation slot
    switches 0, 1, 3, 5, 8   — one aggregation slot (``[0]``)

Use this env from ``run_models_sparse`` to reproduce the archive's "models"
block behaviour, in contrast to ``run_models`` which uses ``env_2c_10sw_3f``
where *every* switch carries an aggregation slot.
"""
from sim.environments._common import build_env


def env_2c_10sw_3f_sparse(state):
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
    clusters = {0: [0, 1, 2, 3], 1: [4, 5, 6, 7]}

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

    # Sparse aggregation-slot availability — only switches {0,1,3,5,8}
    # can host an aggregation slot. Switches {2,4,6,7,9} carry no slot,
    # mirroring the legacy ``env_2Clusters`` definition (see module
    # docstring).
    numberSlotsSwitches = {0: [0], 1: [0], 2: [], 3: [0], 4: [], 5: [0],
                           6: [], 7: [], 8: [0], 9: []}

    workersTopology = {11: 0, 22: 0, 33: 1, 44: 1,
                       55: 4, 66: 4, 77: 5, 88: 5}

    pWorkerPorts = {11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1},
                    55: {0: 4}, 66: {0: 4}, 77: {0: 5}, 88: {0: 5}}

    fragmentsofEachWorker = {11: ["A0", "B0", "C0"], 22: ["A1", "B1", "C1"],
                              33: ["A2", "B2", "C2"], 44: ["A3", "B3", "C3"],
                              55: ["A4", "B4", "C4"], 66: ["A5", "B5", "C5"],
                              77: ["A6", "B6", "C6"], 88: ["A7", "B7", "C7"]}

    stepsToSwitches = {11: [1, 3, 2, 2, 5, 5, 6, 4, 3, 3],
                       22: [1, 3, 2, 2, 5, 5, 6, 4, 3, 3],
                       33: [3, 1, 2, 2, 5, 5, 6, 4, 3, 3],
                       44: [3, 1, 2, 2, 5, 5, 6, 4, 3, 3],
                       55: [5, 5, 4, 6, 1, 3, 2, 2, 3, 3],
                       66: [5, 5, 4, 6, 1, 3, 2, 2, 3, 3],
                       77: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3],
                       88: [5, 5, 4, 6, 3, 1, 2, 2, 3, 3]}

    return build_env(
        state,
        pSwitchesTopology=pSwitchesTopology, pSwitchPorts=pSwitchPorts,
        neighborsofEachSwitch=neighborsofEachSwitch,
        numberSlotsSwitches=numberSlotsSwitches, workersTopology=workersTopology,
        pWorkerPorts=pWorkerPorts, fragmentsofEachWorker=fragmentsofEachWorker,
        stepsToSwitches=stepsToSwitches, cutPorts=cutPorts,
        selectedSwitches=selectedSwitches, clusters=clusters)
