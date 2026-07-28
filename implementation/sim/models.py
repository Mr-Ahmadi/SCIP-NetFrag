"""Model builders — SCIP optimization model construction."""
from .helpers import build_frag_to_worker, find_keys_by_value
from .utils import create_Fragments


# Shared cluster helpers

def _setup_clusters(clusters, workersTopology, fragmentsofEachWorker):
    """Compute clustersFragment and AllClusters (shared by all cluster models)."""
    clustersFragment = {}
    AllClusters = []
    for p in clusters:
        for y in clusters[p]:
            AllClusters.append(y)
    for frags, sw in workersTopology.items():
        for cluster in clusters:
            if sw in clusters[cluster]:
                if cluster not in clustersFragment:
                    clustersFragment[cluster] = {}
                clustersFragment[cluster][frags] = fragmentsofEachWorker[frags]
    return clustersFragment, AllClusters


def _compute_allowed_switches(workersTopology, pSwitchesTopology):
    """Compute allowedSwitches = worker switches + PS-connected switches."""
    allowedSwitches = []
    for W in workersTopology:
        if workersTopology[W] not in allowedSwitches:
            allowedSwitches.append(workersTopology[W])
    for S in pSwitchesTopology:
        if "PS" in pSwitchesTopology[S] and S not in allowedSwitches:
            allowedSwitches.append(S)
    return allowedSwitches


def _z_group_infeasible(subSub, target_switch, T_max_1, window_start, frag2worker,
                        stepsToSwitches):
    """True if some fragment in some group of ``subSub`` cannot physically
    reach ``target_switch`` by ``window_start`` — i.e. aggregating this
    partition at that switch during this window is infeasible.

    Checked per atomic fragment (not just singleton groups) since a Z
    variable combines ALL fragments across ALL groups in the partition into
    one packet: every one of them must be able to arrive in time.
    """
    for group in subSub:
        for frag in group:
            worker = frag2worker.get(frag)
            if worker is None or stepsToSwitches[worker][target_switch] + T_max_1 > window_start:
                return True
    return False


# defineModel  (basic — no clusters)

def defineModel(allofSubsets, pSwitchesTopology, pSwitchPorts, T_max_1, T_max_2,
                workersTopology, fragmentsofEachWorker, pWorkerPorts,
                subSets, numberSlotsSwitches, usefulIntervalTime, Y_Used, Z_Used,
                maxAggregation, stepsToSwitches, cutPorts, selectedSwitches):
    from pyscipopt import Model
    model = Model("Accelerating_Machine_Learning")
    _frag2worker = build_frag_to_worker(fragmentsofEachWorker)

    Y_Variables = dict()
    for frags in allofSubsets:
        for fragments in frags:
            for switches in pSwitchesTopology:
                for ports in pSwitchPorts[switches]:
                    for time in range(T_max_1, T_max_2):
                        keyDictY = (frozenset(fragments), switches, ports, time)
                        if len(fragments) == 1:
                            tempWorker = find_keys_by_value(fragments, fragmentsofEachWorker)[0]
                            stepSwitch = stepsToSwitches[tempWorker][switches]
                            if time >= stepSwitch + T_max_1:
                                if keyDictY not in Y_Used:
                                    Y_Variables[keyDictY] = model.addVar(
                                        vtype='B',
                                        name="Y{F},{S},{R},{T}".format(
                                            F=fragments, S=switches, R=ports, T=time))
                        elif keyDictY not in Y_Used:
                            Y_Variables[keyDictY] = model.addVar(
                                vtype='B',
                                name="Y{F},{S},{R},{T}".format(
                                    F=fragments, S=switches, R=ports, T=time))

    for worker in workersTopology:
        for frag in fragmentsofEachWorker[worker]:
            for port in pWorkerPorts[worker]:
                for time in range(T_max_1, T_max_2):
                    fragg = {frag}
                    keyDictY = (frozenset(fragg), worker, port, time)
                    if keyDictY not in Y_Used:
                        Y_Variables[keyDictY] = model.addVar(
                            vtype='B',
                            name="Y{F},{S},{R},{T}".format(
                                F=fragg, S=worker, R=port, T=time))

    Z_Variables = dict()
    for sub in subSets:
        for subSub in sub:
            for switches in pSwitchesTopology:
                for slots in numberSlotsSwitches[switches]:
                    for timesNumber in usefulIntervalTime:
                        flagDec = False
                        set_of_sets = {frozenset(s) for s in subSub}
                        if len(subSub) <= maxAggregation:
                            keyDictZ = (frozenset(set_of_sets), slots, switches,
                                        timesNumber[0], timesNumber[1])
                            flagDec = _z_group_infeasible(
                                subSub, switches, T_max_1, timesNumber[0],
                                _frag2worker, stepsToSwitches)
                            if keyDictZ not in Z_Used:
                                if len(subSub) == 1:
                                    pass
                                elif flagDec == False:
                                    Z_Variables[keyDictZ] = model.addVar(
                                        vtype='B',
                                        name="Z{F},{M},{S},{t1},{t2}".format(
                                            F=subSub, M=slots, S=switches,
                                            t1=timesNumber[0], t2=timesNumber[1]))

    return model, Z_Variables, Y_Variables, len(Y_Variables), len(Z_Variables)


# defineModel_ATP  (FixR-ToRS — clusters, cutPorts, allowedSwitches, sequential time)

def defineModel_ATP(allofSubsets, pSwitchesTopology, pSwitchPorts, T_max_1, T_max_2,
                    workersTopology, fragmentsofEachWorker, pWorkerPorts,
                    subSets, numberSlotsSwitches, usefulIntervalTime, Y_Used, Z_Used,
                    maxAggregation, stepsToSwitches, cutPorts, selectedSwitches,
                    percentage, clusters):
    from pyscipopt import Model
    model = Model("Accelerating_Machine_Learning")
    clustersFragment, AllClusters = _setup_clusters(clusters, workersTopology, fragmentsofEachWorker)
    allowedSwitches = _compute_allowed_switches(workersTopology, pSwitchesTopology)
    _frag2worker = build_frag_to_worker(fragmentsofEachWorker)
    hameSwitches = []

    Y_Variables = dict()
    for i in clustersFragment:
        switchesCluster = clusters[i]
        finalSwitches = [ss for ss in allowedSwitches if ss in switchesCluster]
        subSetsss, allofSubsetssss, usefulIntervalTimeeee, fragmentssss = \
            create_Fragments(clustersFragment[i], T_max_1, T_max_2, maxAggregation)
        for frags in allofSubsetssss:
            for fragments in frags:
                for switches in finalSwitches:
                    hameSwitches.append(switches)
                    for ports in cutPorts[switches]:
                        for time in range(T_max_1, T_max_2):
                            keyDictY = (frozenset(fragments), switches, ports, time)
                            if len(fragments) == 1:
                                tempWorker = find_keys_by_value(fragments, fragmentsofEachWorker)[0]
                                stepSwitch = stepsToSwitches[tempWorker][switches]
                                if time >= stepSwitch + T_max_1 - 1:
                                    if keyDictY not in Y_Used:
                                        Y_Variables[keyDictY] = model.addVar(
                                            vtype='B',
                                            name="Y{F},{S},{R},{T}".format(
                                                F=fragments, S=switches, R=ports, T=time))
                            elif keyDictY not in Y_Used:
                                Y_Variables[keyDictY] = model.addVar(
                                    vtype='B',
                                    name="Y{F},{S},{R},{T}".format(
                                        F=fragments, S=switches, R=ports, T=time))

    for frags in allofSubsets:
        for fragments in frags:
            for switches in pSwitchesTopology:
                if switches not in hameSwitches:
                    for ports in cutPorts[switches]:
                        for time in range(T_max_1, T_max_2):
                            keyDictY = (frozenset(fragments), switches, ports, time)
                            if len(fragments) == 1:
                                tempWorker = find_keys_by_value(fragments, fragmentsofEachWorker)[0]
                                stepSwitch = stepsToSwitches[tempWorker][switches]
                                if time >= stepSwitch + T_max_1 - 1:
                                    if keyDictY not in Y_Used:
                                        Y_Variables[keyDictY] = model.addVar(
                                            vtype='B',
                                            name="Y{F},{S},{R},{T}".format(
                                                F=fragments, S=switches, R=ports, T=time))
                            elif keyDictY not in Y_Used:
                                Y_Variables[keyDictY] = model.addVar(
                                    vtype='B',
                                    name="Y{F},{S},{R},{T}".format(
                                        F=fragments, S=switches, R=ports, T=time))

    timeWorker = T_max_1
    for worker in workersTopology:
        for frag in fragmentsofEachWorker[worker]:
            for port in pWorkerPorts[worker]:
                fragg = {frag}
                keyDictY = (frozenset(fragg), worker, port, timeWorker)
                if keyDictY not in Y_Used:
                    Y_Variables[keyDictY] = model.addVar(
                        vtype='B',
                        name="Y{F},{S},{R},{T}".format(
                            F=fragg, S=worker, R=port, T=timeWorker))
                    timeWorker += 1

    clusterSets = []
    switchesCluster = []
    Z_Variables = dict()
    for i in clustersFragment:
        switches11 = clusters[i]
        switchesCluster.append(clusters[i])
        finalSwitches = [ss for ss in allowedSwitches if ss in switches11]
        subSets2, allofSubsets2, usefulIntervalTime2, fragments2 = \
            create_Fragments(clustersFragment[i], T_max_1, T_max_2, maxAggregation)
        temp1, temp2 = [], []
        for sub in subSets2:
            for subSub in sub:
                for switches in finalSwitches:
                    for slots in numberSlotsSwitches[switches]:
                        for timesNumber in usefulIntervalTime2:
                            flagDec = False
                            set_of_sets = {frozenset(s) for s in subSub}
                            if len(subSub) <= maxAggregation:
                                keyDictZ = (frozenset(set_of_sets), slots, switches,
                                            timesNumber[0], timesNumber[1])
                                flagDec = _z_group_infeasible(
                                    subSub, switches, T_max_1, timesNumber[0],
                                    _frag2worker, stepsToSwitches)
                                if keyDictZ not in Z_Used:
                                    if len(subSub) == 1:
                                        temp2.append(usefulIntervalTime)
                                    elif flagDec == False:
                                        temp1.append(subSub)
                                        temp2.append(usefulIntervalTime)
                                        Z_Variables[keyDictZ] = model.addVar(
                                            vtype='B',
                                            name="Z{F},{M},{S},{t1},{t2}".format(
                                                F=subSub, M=slots, S=switches,
                                                t1=timesNumber[0], t2=timesNumber[1]))
        temp11 = []
        for _item in temp1:
            if _item not in temp11:
                temp11.append(_item)
        temp22 = []
        for _item in temp2:
            if _item not in temp22:
                temp22.append(_item)
        clusterSets.append([temp11, temp22])

    for o in pSwitchesTopology:
        if o not in AllClusters and o in allowedSwitches:
            for sub in subSets:
                for subSub in sub:
                    for slots in numberSlotsSwitches[o]:
                        for timesNumber in usefulIntervalTime:
                            flagDec = False
                            set_of_sets = {frozenset(s) for s in subSub}
                            if len(subSub) <= maxAggregation:
                                keyDictZ = (frozenset(set_of_sets), slots, o,
                                            timesNumber[0], timesNumber[1])
                                flagDec = _z_group_infeasible(
                                    subSub, o, T_max_1, timesNumber[0],
                                    _frag2worker, stepsToSwitches)
                                if keyDictZ not in Z_Used:
                                    if len(subSub) == 1:
                                        pass
                                    elif flagDec == False:
                                        Z_Variables[keyDictZ] = model.addVar(
                                            vtype='B',
                                            name="Z{F},{M},{S},{t1},{t2}".format(
                                                F=subSub, M=slots, S=o,
                                                t1=timesNumber[0], t2=timesNumber[1]))

    return (model, Z_Variables, Y_Variables, len(Y_Variables), len(Z_Variables),
            clusterSets, switchesCluster, AllClusters)


# defineModel_GRID  (FixR-AS — clusters, cutPorts, cluster switches only, sequential time)

def defineModel_GRID(allofSubsets, pSwitchesTopology, pSwitchPorts, T_max_1, T_max_2,
                     workersTopology, fragmentsofEachWorker, pWorkerPorts,
                     subSets, numberSlotsSwitches, usefulIntervalTime, Y_Used, Z_Used,
                     maxAggregation, stepsToSwitches, cutPorts, selectedSwitches,
                     percentage, clusters):
    from pyscipopt import Model
    model = Model("Accelerating_Machine_Learning")
    clustersFragment, AllClusters = _setup_clusters(clusters, workersTopology, fragmentsofEachWorker)
    _frag2worker = build_frag_to_worker(fragmentsofEachWorker)
    hameSwitches = []

    Y_Variables = dict()
    for i in clustersFragment:
        switchesCluster = clusters[i]
        subSetsss, allofSubsetssss, usefulIntervalTimeeee, fragmentssss = \
            create_Fragments(clustersFragment[i], T_max_1, T_max_2, maxAggregation)
        for frags in allofSubsetssss:
            for fragments in frags:
                for switches in switchesCluster:
                    hameSwitches.append(switches)
                    for ports in cutPorts[switches]:
                        for time in range(T_max_1, T_max_2):
                            keyDictY = (frozenset(fragments), switches, ports, time)
                            if len(fragments) == 1:
                                tempWorker = find_keys_by_value(fragments, fragmentsofEachWorker)[0]
                                stepSwitch = stepsToSwitches[tempWorker][switches]
                                if time >= stepSwitch + T_max_1:
                                    if keyDictY not in Y_Used:
                                        Y_Variables[keyDictY] = model.addVar(
                                            vtype='B',
                                            name="Y{F},{S},{R},{T}".format(
                                                F=fragments, S=switches, R=ports, T=time))
                            elif keyDictY not in Y_Used:
                                Y_Variables[keyDictY] = model.addVar(
                                    vtype='B',
                                    name="Y{F},{S},{R},{T}".format(
                                        F=fragments, S=switches, R=ports, T=time))

    for frags in allofSubsets:
        for fragments in frags:
            for switches in pSwitchesTopology:
                if switches not in hameSwitches:
                    for ports in cutPorts[switches]:
                        for time in range(T_max_1, T_max_2):
                            keyDictY = (frozenset(fragments), switches, ports, time)
                            if len(fragments) == 1:
                                tempWorker = find_keys_by_value(fragments, fragmentsofEachWorker)[0]
                                stepSwitch = stepsToSwitches[tempWorker][switches]
                                if time >= stepSwitch + T_max_1:
                                    if keyDictY not in Y_Used:
                                        Y_Variables[keyDictY] = model.addVar(
                                            vtype='B',
                                            name="Y{F},{S},{R},{T}".format(
                                                F=fragments, S=switches, R=ports, T=time))
                            elif keyDictY not in Y_Used:
                                Y_Variables[keyDictY] = model.addVar(
                                    vtype='B',
                                    name="Y{F},{S},{R},{T}".format(
                                        F=fragments, S=switches, R=ports, T=time))

    timeWorker = T_max_1
    for worker in workersTopology:
        for frag in fragmentsofEachWorker[worker]:
            for port in pWorkerPorts[worker]:
                fragg = {frag}
                keyDictY = (frozenset(fragg), worker, port, timeWorker)
                if keyDictY not in Y_Used:
                    Y_Variables[keyDictY] = model.addVar(
                        vtype='B',
                        name="Y{F},{S},{R},{T}".format(
                            F=fragg, S=worker, R=port, T=timeWorker))
                    timeWorker += 1

    clusterSets = []
    switchesCluster = []
    Z_Variables = dict()
    for i in clustersFragment:
        switches11 = clusters[i]
        switchesCluster.append(clusters[i])
        subSets2, allofSubsets2, usefulIntervalTime2, fragments2 = \
            create_Fragments(clustersFragment[i], T_max_1, T_max_2, maxAggregation)
        temp1, temp2 = [], []
        for sub in subSets2:
            for subSub in sub:
                for switches in switches11:
                    for slots in numberSlotsSwitches[switches]:
                        for timesNumber in usefulIntervalTime2:
                            flagDec = False
                            set_of_sets = {frozenset(s) for s in subSub}
                            if len(subSub) <= maxAggregation:
                                keyDictZ = (frozenset(set_of_sets), slots, switches,
                                            timesNumber[0], timesNumber[1])
                                flagDec = _z_group_infeasible(
                                    subSub, switches, T_max_1, timesNumber[0],
                                    _frag2worker, stepsToSwitches)
                                if keyDictZ not in Z_Used:
                                    if len(subSub) == 1:
                                        temp2.append(usefulIntervalTime2)
                                    elif flagDec == False:
                                        temp1.append(subSub)
                                        temp2.append(usefulIntervalTime2)
                                        Z_Variables[keyDictZ] = model.addVar(
                                            vtype='B',
                                            name="Z{F},{M},{S},{t1},{t2}".format(
                                                F=subSub, M=slots, S=switches,
                                                t1=timesNumber[0], t2=timesNumber[1]))
        temp11 = []
        for _item in temp1:
            if _item not in temp11:
                temp11.append(_item)
        temp22 = []
        for _item in temp2:
            if _item not in temp22:
                temp22.append(_item)
        clusterSets.append([temp11, temp22])

    for o in pSwitchesTopology:
        if o not in AllClusters:
            for sub in subSets:
                for subSub in sub:
                    for slots in numberSlotsSwitches[o]:
                        for timesNumber in usefulIntervalTime:
                            flagDec = False
                            set_of_sets = {frozenset(s) for s in subSub}
                            if len(subSub) <= maxAggregation:
                                keyDictZ = (frozenset(set_of_sets), slots, o,
                                            timesNumber[0], timesNumber[1])
                                flagDec = _z_group_infeasible(
                                    subSub, o, T_max_1, timesNumber[0],
                                    _frag2worker, stepsToSwitches)
                                if keyDictZ not in Z_Used:
                                    if len(subSub) == 1:
                                        pass
                                    elif flagDec == False:
                                        Z_Variables[keyDictZ] = model.addVar(
                                            vtype='B',
                                            name="Z{F},{M},{S},{t1},{t2}".format(
                                                F=subSub, M=slots, S=o,
                                                t1=timesNumber[0], t2=timesNumber[1]))

    return (model, Z_Variables, Y_Variables, len(Y_Variables), len(Z_Variables),
            clusterSets, switchesCluster, AllClusters)


# defineModel_ATP_GRID  (FlexR-ToRS — clusters, pSwitchPorts, allowedSwitches, full time)

def defineModel_ATP_GRID(allofSubsets, pSwitchesTopology, pSwitchPorts, T_max_1, T_max_2,
                         workersTopology, fragmentsofEachWorker, pWorkerPorts,
                         subSets, numberSlotsSwitches, usefulIntervalTime, Y_Used, Z_Used,
                         maxAggregation, stepsToSwitches, cutPorts, selectedSwitches,
                         percentage, clusters):
    from pyscipopt import Model
    model = Model("Accelerating_Machine_Learning")
    clustersFragment, AllClusters = _setup_clusters(clusters, workersTopology, fragmentsofEachWorker)
    allowedSwitches = _compute_allowed_switches(workersTopology, pSwitchesTopology)
    _frag2worker = build_frag_to_worker(fragmentsofEachWorker)
    hameSwitches = []

    Y_Variables = dict()
    for i in clustersFragment:
        switchesCluster = clusters[i]
        finalSwitches = [ss for ss in allowedSwitches if ss in switchesCluster]
        subSetsss, allofSubsetssss, usefulIntervalTimeeee, fragmentssss = \
            create_Fragments(clustersFragment[i], T_max_1, T_max_2, maxAggregation)
        for frags in allofSubsetssss:
            for fragments in frags:
                for switches in finalSwitches:
                    hameSwitches.append(switches)
                    for ports in pSwitchPorts[switches]:
                        for time in range(T_max_1, T_max_2):
                            keyDictY = (frozenset(fragments), switches, ports, time)
                            if len(fragments) == 1:
                                tempWorker = find_keys_by_value(fragments, fragmentsofEachWorker)[0]
                                stepSwitch = stepsToSwitches[tempWorker][switches]
                                if time >= stepSwitch + T_max_1:
                                    if keyDictY not in Y_Used:
                                        Y_Variables[keyDictY] = model.addVar(
                                            vtype='B',
                                            name="Y{F},{S},{R},{T}".format(
                                                F=fragments, S=switches, R=ports, T=time))
                            elif keyDictY not in Y_Used:
                                Y_Variables[keyDictY] = model.addVar(
                                    vtype='B',
                                    name="Y{F},{S},{R},{T}".format(
                                        F=fragments, S=switches, R=ports, T=time))

    for frags in allofSubsets:
        for fragments in frags:
            for switches in pSwitchesTopology:
                if switches not in hameSwitches:
                    for ports in pSwitchPorts[switches]:
                        for time in range(T_max_1, T_max_2):
                            keyDictY = (frozenset(fragments), switches, ports, time)
                            if len(fragments) == 1:
                                tempWorker = find_keys_by_value(fragments, fragmentsofEachWorker)[0]
                                stepSwitch = stepsToSwitches[tempWorker][switches]
                                if time >= stepSwitch + T_max_1:
                                    if keyDictY not in Y_Used:
                                        Y_Variables[keyDictY] = model.addVar(
                                            vtype='B',
                                            name="Y{F},{S},{R},{T}".format(
                                                F=fragments, S=switches, R=ports, T=time))
                            elif keyDictY not in Y_Used:
                                Y_Variables[keyDictY] = model.addVar(
                                    vtype='B',
                                    name="Y{F},{S},{R},{T}".format(
                                        F=fragments, S=switches, R=ports, T=time))

    for worker in workersTopology:
        for frag in fragmentsofEachWorker[worker]:
            for port in pWorkerPorts[worker]:
                for time in range(T_max_1, T_max_2):
                    fragg = {frag}
                    keyDictY = (frozenset(fragg), worker, port, time)
                    if keyDictY not in Y_Used:
                        Y_Variables[keyDictY] = model.addVar(
                            vtype='B',
                            name="Y{F},{S},{R},{T}".format(
                                F=fragg, S=worker, R=port, T=time))

    clusterSets = []
    switchesCluster = []
    Z_Variables = dict()
    for i in clustersFragment:
        switches11 = clusters[i]
        switchesCluster.append(clusters[i])
        finalSwitches = [ss for ss in allowedSwitches if ss in switches11]
        subSets2, allofSubsets2, usefulIntervalTime2, fragments2 = \
            create_Fragments(clustersFragment[i], T_max_1, T_max_2, maxAggregation)
        temp1, temp2 = [], []
        for sub in subSets2:
            for subSub in sub:
                for switches in finalSwitches:
                    for slots in numberSlotsSwitches[switches]:
                        for timesNumber in usefulIntervalTime2:
                            flagDec = False
                            set_of_sets = {frozenset(s) for s in subSub}
                            if len(subSub) <= maxAggregation:
                                keyDictZ = (frozenset(set_of_sets), slots, switches,
                                            timesNumber[0], timesNumber[1])
                                flagDec = _z_group_infeasible(
                                    subSub, switches, T_max_1, timesNumber[0],
                                    _frag2worker, stepsToSwitches)
                                if keyDictZ not in Z_Used:
                                    if len(subSub) == 1:
                                        temp2.append(usefulIntervalTime)
                                    elif flagDec == False:
                                        temp1.append(subSub)
                                        temp2.append(usefulIntervalTime)
                                        Z_Variables[keyDictZ] = model.addVar(
                                            vtype='B',
                                            name="Z{F},{M},{S},{t1},{t2}".format(
                                                F=subSub, M=slots, S=switches,
                                                t1=timesNumber[0], t2=timesNumber[1]))
        temp11 = []
        for _item in temp1:
            if _item not in temp11:
                temp11.append(_item)
        temp22 = []
        for _item in temp2:
            if _item not in temp22:
                temp22.append(_item)
        clusterSets.append([temp11, temp22])

    for o in pSwitchesTopology:
        if o not in AllClusters and o in allowedSwitches:
            for sub in subSets:
                for subSub in sub:
                    for slots in numberSlotsSwitches[o]:
                        for timesNumber in usefulIntervalTime:
                            flagDec = False
                            set_of_sets = {frozenset(s) for s in subSub}
                            if len(subSub) <= maxAggregation:
                                keyDictZ = (frozenset(set_of_sets), slots, o,
                                            timesNumber[0], timesNumber[1])
                                flagDec = _z_group_infeasible(
                                    subSub, o, T_max_1, timesNumber[0],
                                    _frag2worker, stepsToSwitches)
                                if keyDictZ not in Z_Used:
                                    if len(subSub) == 1:
                                        pass
                                    elif flagDec == False:
                                        Z_Variables[keyDictZ] = model.addVar(
                                            vtype='B',
                                            name="Z{F},{M},{S},{t1},{t2}".format(
                                                F=subSub, M=slots, S=o,
                                                t1=timesNumber[0], t2=timesNumber[1]))

    return (model, Z_Variables, Y_Variables, len(Y_Variables), len(Z_Variables),
            clusterSets, switchesCluster, AllClusters)


# defineModel_selectedSwitches  (FlexINA — clusters, pSwitchPorts, percentage)

def defineModel_selectedSwitches(allofSubsets1, pSwitchesTopology, pSwitchPorts,
                                 T_max_1, T_max_2, workersTopology,
                                 fragmentsofEachWorker, pWorkerPorts,
                                 subSets1, numberSlotsSwitches, usefulIntervalTime1,
                                 Y_Used, Z_Used, maxAggregation, stepsToSwitches,
                                 cutPorts, selectedSwitches, Persentage, clusters):
    from pyscipopt import Model
    model = Model("Accelerating_Machine_Learning")
    clustersFragment, AllClusters = _setup_clusters(clusters, workersTopology, fragmentsofEachWorker)
    _frag2worker = build_frag_to_worker(fragmentsofEachWorker)
    hameSwitches = []

    Y_Variables = dict()
    for i in clustersFragment:
        switchesCluster = clusters[i]
        subSetsss, allofSubsetssss, usefulIntervalTimeeee, fragmentssss = \
            create_Fragments(clustersFragment[i], T_max_1, T_max_2, maxAggregation)
        for frags in allofSubsetssss:
            for fragments in frags:
                for switches in switchesCluster:
                    hameSwitches.append(switches)
                    for ports in pSwitchPorts[switches]:
                        for time in range(T_max_1, T_max_2):
                            keyDictY = (frozenset(fragments), switches, ports, time)
                            if len(fragments) == 1:
                                tempWorker = find_keys_by_value(fragments, fragmentsofEachWorker)[0]
                                stepSwitch = stepsToSwitches[tempWorker][switches]
                                if time >= stepSwitch + T_max_1:
                                    if keyDictY not in Y_Used:
                                        Y_Variables[keyDictY] = model.addVar(
                                            vtype='B',
                                            name="Y{F},{S},{R},{T}".format(
                                                F=fragments, S=switches, R=ports, T=time))
                            elif keyDictY not in Y_Used:
                                Y_Variables[keyDictY] = model.addVar(
                                    vtype='B',
                                    name="Y{F},{S},{R},{T}".format(
                                        F=fragments, S=switches, R=ports, T=time))

    for frags in allofSubsets1:
        for fragments in frags:
            for switches in pSwitchesTopology:
                if switches not in hameSwitches:
                    for ports in pSwitchPorts[switches]:
                        for time in range(T_max_1, T_max_2):
                            keyDictY = (frozenset(fragments), switches, ports, time)
                            if len(fragments) == 1:
                                tempWorker = find_keys_by_value(fragments, fragmentsofEachWorker)[0]
                                stepSwitch = stepsToSwitches[tempWorker][switches]
                                if time >= stepSwitch + T_max_1:
                                    if keyDictY not in Y_Used:
                                        Y_Variables[keyDictY] = model.addVar(
                                            vtype='B',
                                            name="Y{F},{S},{R},{T}".format(
                                                F=fragments, S=switches, R=ports, T=time))
                            elif keyDictY not in Y_Used:
                                Y_Variables[keyDictY] = model.addVar(
                                    vtype='B',
                                    name="Y{F},{S},{R},{T}".format(
                                        F=fragments, S=switches, R=ports, T=time))

    for worker in workersTopology:
        for frag in fragmentsofEachWorker[worker]:
            for port in pWorkerPorts[worker]:
                for time in range(T_max_1, T_max_2):
                    fragg = {frag}
                    keyDictY = (frozenset(fragg), worker, port, time)
                    if keyDictY not in Y_Used:
                        Y_Variables[keyDictY] = model.addVar(
                            vtype='B',
                            name="Y{F},{S},{R},{T}".format(
                                F=fragg, S=worker, R=port, T=time))

    Z_Variables = dict()
    lenSelectedSwitches = int(Persentage * len(selectedSwitches))
    selectedSwitches1 = selectedSwitches[0:lenSelectedSwitches]

    clusterSets = []
    switchinClusters = []
    for i in clustersFragment:
        switches11 = []
        switchesCluster = clusters[i]
        for ss in switchesCluster:
            if ss in selectedSwitches1:
                switches11.append(ss)
        switchinClusters.append(switches11)
        subSets, allofSubsets, usefulIntervalTime, fragments = \
            create_Fragments(clustersFragment[i], T_max_1, T_max_2, maxAggregation)
        temp1, temp2 = [], []
        for sub in subSets:
            for subSub in sub:
                set_of_sets = {frozenset(s) for s in subSub}
                for switches in switches11:
                    for slots in numberSlotsSwitches[switches]:
                        for timesNumber in usefulIntervalTime:
                            flagDec = False
                            if len(subSub) <= maxAggregation:
                                keyDictZ = (frozenset(set_of_sets), slots, switches,
                                            timesNumber[0], timesNumber[1])
                                flagDec = _z_group_infeasible(
                                    subSub, switches, T_max_1, timesNumber[0],
                                    _frag2worker, stepsToSwitches)
                                if keyDictZ not in Z_Used:
                                    if len(subSub) == 1:
                                        temp2.append(usefulIntervalTime)
                                    elif flagDec == False:
                                        temp1.append(subSub)
                                        temp2.append(usefulIntervalTime)
                                        Z_Variables[keyDictZ] = model.addVar(
                                            vtype='B',
                                            name="Z{F},{M},{S},{t1},{t2}".format(
                                                F=subSub, M=slots, S=switches,
                                                t1=timesNumber[0], t2=timesNumber[1]))
        temp11 = []
        for _item in temp1:
            if _item not in temp11:
                temp11.append(_item)
        temp22 = []
        for _item in temp2:
            if _item not in temp22:
                temp22.append(_item)
        clusterSets.append([temp11, temp22])

    for o in selectedSwitches1:
        if o not in AllClusters:
            for sub in subSets1:
                for subSub in sub:
                    for slots in numberSlotsSwitches[o]:
                        for timesNumber in usefulIntervalTime1:
                            flagDec = False
                            set_of_sets = {frozenset(s) for s in subSub}
                            if len(subSub) <= maxAggregation:
                                keyDictZ = (frozenset(set_of_sets), slots, o,
                                            timesNumber[0], timesNumber[1])
                                flagDec = _z_group_infeasible(
                                    subSub, o, T_max_1, timesNumber[0],
                                    _frag2worker, stepsToSwitches)
                                if keyDictZ not in Z_Used:
                                    if len(subSub) == 1:
                                        pass
                                    elif flagDec == False:
                                        Z_Variables[keyDictZ] = model.addVar(
                                            vtype='B',
                                            name="Z{F},{M},{S},{t1},{t2}".format(
                                                F=subSub, M=slots, S=o,
                                                t1=timesNumber[0], t2=timesNumber[1]))

    return (model, Z_Variables, Y_Variables, len(Y_Variables), len(Z_Variables),
            clusterSets, switchinClusters, AllClusters)
