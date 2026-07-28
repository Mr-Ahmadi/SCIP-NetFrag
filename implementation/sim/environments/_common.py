"""
Shared optimization helper for environment definitions.

Each env_* function defines a raw network (switches, ports, workers, fragments)
and then optionally passes it through ``optimize_env`` ("Optimaze" state) to
collapse duplicate workers on the same switch into one, rebuilding the
port / neighbor / topology / fragment structures consistently.
"""


def rank_switches_by_ports(pSwitchesTopology, pSwitchPorts):
    """Rank switches by descending port count (FlexINA Phase 2 filtration).

    Per the FlexINA paper (Sec. IV-B): "FlexINA ranks switches by port
    count and selects the top rho%" — a higher port count means more
    routing paths under the flexible routing model, improving the odds
    of encountering and aggregating fragments. Ties are broken by each
    switch's insertion order in ``pSwitchesTopology`` for determinism.
    """
    return sorted(pSwitchesTopology, key=lambda s: -len(pSwitchPorts[s]))


def optimize_env(pSwitchPorts, neighborsofEachSwitch, workersTopology,
                 pWorkerPorts, fragmentsofEachWorker):
    """Collapse duplicate workers per switch and rebuild ports/neighbors/fragments."""
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
        # Delete in *reverse* order so earlier deletions don't shift
        # the indices of later deletions.
        for delete in sorted(NeighborDelete, reverse=True):
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


def build_env(state, *, pSwitchesTopology, pSwitchPorts,
              neighborsofEachSwitch, numberSlotsSwitches, workersTopology,
              pWorkerPorts, fragmentsofEachWorker, stepsToSwitches,
              cutPorts, selectedSwitches, clusters):
    """Assemble the 15-element environment tuple. Deduplicates workers if state=="Optimaze"."""
    pSwitchesNumber = len(pSwitchesTopology)
    workersNumber = len(workersTopology)
    totalWorkers = fragmentsofEachWorker.copy()
    numAllFrags = sum(len(v) for v in fragmentsofEachWorker.values())

    if state == "Optimaze":
        (pSwitchPorts, neighborsofEachSwitch, workersTopology,
         pWorkerPorts, workersNumber, fragmentsofEachWorker,
         numAllFrags) = optimize_env(pSwitchPorts, neighborsofEachSwitch,
                                     workersTopology, pWorkerPorts,
                                     fragmentsofEachWorker)

    return (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
            pSwitchesNumber, numberSlotsSwitches, workersTopology,
            pWorkerPorts, workersNumber, numAllFrags,
            fragmentsofEachWorker, totalWorkers, stepsToSwitches,
            cutPorts, selectedSwitches, clusters)
