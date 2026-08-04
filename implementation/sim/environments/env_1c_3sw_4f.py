"""
env_1c_3sw_4f — compact 3-switch spine-leaf, 1 cluster.

A smaller alternative topology: two ToRs (0,1) each host 2 workers (dedup'd
to 1 by Optimaze), joined through a single spine (2) that also carries "PS".
4 frags/worker — moderate load. This probes how the model handles a much
smaller switch count compared to the 5/10-switch envs.
"""
from sim.environments._common import build_env, rank_switches_by_ports


def env_1c_3sw_4f(state):
    pSwitchesTopology = {0: [1, 2], 1: [0, 2], 2: [0, 1, "PS"]}

    pSwitchPorts = {0: {0: 11, 1: 22, 2: 1, 3: 2},
                    1: {0: 33, 1: 44, 2: 0, 3: 2},
                    2: {0: 0, 1: 1, 2: "PS"},
                    11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1}}

    clusters = {0: [0, 1]}
    selectedSwitches = rank_switches_by_ports(pSwitchesTopology, pSwitchPorts)
    cutPorts = {0: {3: 2}, 1: {3: 2}, 2: {2: "PS"},
                11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1}}

    neighborsofEachSwitch = {0: [11, 22, 1, 2], 1: [33, 44, 0, 2],
                             2: [0, 1],
                             11: [0], 22: [0], 33: [1], 44: [1]}

    numberSlotsSwitches = {0: [0], 1: [0], 2: []}

    workersTopology = {11: 0, 22: 0, 33: 1, 44: 1}

    pWorkerPorts = {11: {0: 0}, 22: {0: 0}, 33: {0: 1}, 44: {0: 1}}

    fragmentsofEachWorker = {11: ["A0", "B0", "C0", "D0"],
                             22: ["A1", "B1", "C1", "D1"],
                             33: ["A2", "B2", "C2", "D2"],
                             44: ["A3", "B3", "C3", "D3"]}

    # Hops from each worker to each switch, indexed by switch id; a worker's
    # own ToR is 1. Switches 0 and 1 are directly linked, so the far ToR is 2.
    stepsToSwitches = {11: [1, 2, 2], 22: [1, 2, 2],
                       33: [2, 1, 2], 44: [2, 1, 2]}

    return build_env(
        state,
        pSwitchesTopology=pSwitchesTopology, pSwitchPorts=pSwitchPorts,
        neighborsofEachSwitch=neighborsofEachSwitch,
        numberSlotsSwitches=numberSlotsSwitches, workersTopology=workersTopology,
        pWorkerPorts=pWorkerPorts, fragmentsofEachWorker=fragmentsofEachWorker,
        stepsToSwitches=stepsToSwitches, cutPorts=cutPorts,
        selectedSwitches=selectedSwitches, clusters=clusters)
