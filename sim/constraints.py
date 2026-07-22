"""
Constraint functions — all constraintNum* functions.
Moved verbatim from the original Accelerating_New.py.

IMPORTANT: These functions read Y_Variables, Z_Variables, and workersTopology
as module-level globals.  The caller (runner.py) must set these before calling.
"""
from .helpers import find_keys_by_value

# Module-level globals set by apply_constraints() before any constraint call.
Y_Variables = {}
Z_Variables = {}
workersTopology = {}


# ---------------------------------------------------------------------------
# Constraint 1 — basic
# ---------------------------------------------------------------------------

def constraintNum1(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, Z_Used):
    for switches in pSwitchesTopology:
        for slots in numberSlotsSwitches[switches]:
            for timesNumber in usefulIntervalTime:
                temporarySumArray = []
                for sub in subSets:
                    for subSub in sub:
                        if len(subSub) > 1:
                            set_of_sets = {frozenset(s) for s in subSub}
                            keyDictZ = (frozenset(set_of_sets), slots, switches,
                                        timesNumber[0], timesNumber[1])
                            if keyDictZ not in Z_Used and keyDictZ in Z_Variables.keys():
                                temporarySumArray.append(Z_Variables[keyDictZ])
                if len(temporarySumArray) != 0:
                    model.addCons(sum(temporarySumArray) <= 1)


# ---------------------------------------------------------------------------
# Constraint 1 — selectedSwitches
# ---------------------------------------------------------------------------

def constraintNum1selectedSwitches(pSwitchesTopology, numberSlotsSwitches,
                                   usefulIntervalTime, subSets, model, Z_Used,
                                   clusterSets, switchinClusters, AllClusters):
    for i in range(0, len(switchinClusters)):
        for switches in switchinClusters[i]:
            for slots in numberSlotsSwitches[switches]:
                for timesNumber in clusterSets[i][1][0]:
                    temporarySumArray = []
                    for sub in clusterSets[i][0]:
                        if len(sub) > 1:
                            set_of_sets = {frozenset(s) for s in sub}
                            keyDictZ = (frozenset(set_of_sets), slots, switches,
                                        timesNumber[0], timesNumber[1])
                            if keyDictZ not in Z_Used and keyDictZ in Z_Variables.keys():
                                temporarySumArray.append(Z_Variables[keyDictZ])
                    if len(temporarySumArray) != 0:
                        model.addCons(sum(temporarySumArray) <= 1)
    for switches in pSwitchesTopology:
        if switches not in AllClusters:
            for slots in numberSlotsSwitches[switches]:
                for timesNumber in usefulIntervalTime:
                    temporarySumArray = []
                    for sub in subSets:
                        for subSub in sub:
                            if len(subSub) > 1:
                                set_of_sets = {frozenset(s) for s in subSub}
                                keyDictZ = (frozenset(set_of_sets), slots, switches,
                                            timesNumber[0], timesNumber[1])
                                if keyDictZ not in Z_Used and keyDictZ in Z_Variables.keys():
                                    temporarySumArray.append(Z_Variables[keyDictZ])
                    if len(temporarySumArray) != 0:
                        model.addCons(sum(temporarySumArray) <= 1)


# ---------------------------------------------------------------------------
# Constraint MultiSlots
# ---------------------------------------------------------------------------

def constraintMultiSlots(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                         subSets, model, Z_Used, clusterSets, switchinClusters, AllClusters):
    for i in range(0, len(switchinClusters)):
        for switches in switchinClusters[i]:
            for sub in clusterSets[i][0]:
                temporarySumArray = []
                for slots in numberSlotsSwitches[switches]:
                    for timesNumber in clusterSets[i][1][0]:
                        if len(sub) > 1:
                            set_of_sets = {frozenset(s) for s in sub}
                            keyDictZ = (frozenset(set_of_sets), slots, switches,
                                        timesNumber[0], timesNumber[1])
                            if keyDictZ not in Z_Used and keyDictZ in Z_Variables.keys():
                                temporarySumArray.append(Z_Variables[keyDictZ])
                if len(temporarySumArray) != 0:
                    model.addCons(sum(temporarySumArray) <= 1)
    for switches in pSwitchesTopology:
        if switches not in AllClusters:
            for sub in subSets:
                for subSub in sub:
                    temporarySumArray = []
                    for slots in numberSlotsSwitches[switches]:
                        for timesNumber in usefulIntervalTime:
                            if len(subSub) > 1:
                                set_of_sets = {frozenset(s) for s in subSub}
                                keyDictZ = (frozenset(set_of_sets), slots, switches,
                                            timesNumber[0], timesNumber[1])
                                if keyDictZ not in Z_Used and keyDictZ in Z_Variables.keys():
                                    temporarySumArray.append(Z_Variables[keyDictZ])
                    if len(temporarySumArray) != 0:
                        model.addCons(sum(temporarySumArray) <= 1)


# ---------------------------------------------------------------------------
# Constraint 2 — basic
# ---------------------------------------------------------------------------

def constraintNum2(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, T_max_1, T_max_2, Z_Used):
    for switches in pSwitchesTopology:
        for slots in numberSlotsSwitches[switches]:
            for t in range(T_max_1, T_max_2):
                temporarySumArray = []
                for timesNumber in usefulIntervalTime:
                    if timesNumber[0] <= t <= timesNumber[1]:
                        for sub in subSets:
                            for subSub in sub:
                                if len(subSub) > 1:
                                    set_of_sets = {frozenset(s) for s in subSub}
                                    keyDictZ = (frozenset(set_of_sets), slots, switches,
                                                timesNumber[0], timesNumber[1])
                                    if keyDictZ not in Z_Used and keyDictZ in Z_Variables.keys():
                                        temporarySumArray.append(Z_Variables[keyDictZ])
                if len(temporarySumArray) != 0:
                    model.addCons(sum(temporarySumArray) <= 1)


# ---------------------------------------------------------------------------
# Constraint 2 — selectedSwitches
# ---------------------------------------------------------------------------

def constraintNum2selectedSwitches(pSwitchesTopology, numberSlotsSwitches,
                                   usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                                   Z_Used, clusterSets, switchinClusters, AllClusters):
    for i in range(0, len(switchinClusters)):
        for switches in switchinClusters[i]:
            for slots in numberSlotsSwitches[switches]:
                for t in range(T_max_1, T_max_2):
                    temporarySumArray = []
                    for timesNumber in clusterSets[i][1][0]:
                        if timesNumber[0] <= t <= timesNumber[1]:
                            for sub in clusterSets[i][0]:
                                if len(sub) > 1:
                                    set_of_sets = {frozenset(s) for s in sub}
                                    keyDictZ = (frozenset(set_of_sets), slots, switches,
                                                timesNumber[0], timesNumber[1])
                                    if keyDictZ not in Z_Used and keyDictZ in Z_Variables.keys():
                                        temporarySumArray.append(Z_Variables[keyDictZ])
                    if len(temporarySumArray) != 0:
                        model.addCons(sum(temporarySumArray) <= 1)
    for switches in pSwitchesTopology:
        if switches not in AllClusters:
            for slots in numberSlotsSwitches[switches]:
                for t in range(T_max_1, T_max_2):
                    temporarySumArray = []
                    for timesNumber in usefulIntervalTime:
                        if timesNumber[0] <= t <= timesNumber[1]:
                            for sub in subSets:
                                for subSub in sub:
                                    if len(subSub) > 1:
                                        set_of_sets = {frozenset(s) for s in subSub}
                                        keyDictZ = (frozenset(set_of_sets), slots, switches,
                                                    timesNumber[0], timesNumber[1])
                                        if keyDictZ not in Z_Used and keyDictZ in Z_Variables.keys():
                                            temporarySumArray.append(Z_Variables[keyDictZ])
                    if len(temporarySumArray) != 0:
                        model.addCons(sum(temporarySumArray) <= 1)


# ---------------------------------------------------------------------------
# Constraint 3 — basic
# ---------------------------------------------------------------------------

def constraintNum3(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
                   pSwitchPorts, Z_Used):
    for switches in pSwitchesTopology:
        for slots in numberSlotsSwitches[switches]:
            for timesNumber in usefulIntervalTime:
                for sub in subSets:
                    for subSub in sub:
                        if len(subSub) > 1:
                            set_of_sets = {frozenset(s) for s in subSub}
                            Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                        timesNumber[0], timesNumber[1])
                            if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                Z_Var = Z_Variables[Z_Var_Id]
                            for subSubSub in subSub:
                                keyDictNeighborsY = []
                                for t in range(max(timesNumber[0] - 1, 0), timesNumber[1]):
                                    for neighbor in neighborsofEachSwitch[switches]:
                                        try:
                                            portNeighborSwitch = pSwitchPorts[neighbor]
                                        except Exception:
                                            pass
                                        for portt in portNeighborSwitch:
                                            if portNeighborSwitch[portt] == switches:
                                                keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                try:
                                                    keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                except Exception:
                                                    pass
                                if len(keyDictNeighborsY) > 0:
                                    try:
                                        model.addCons(Z_Var <= sum(keyDictNeighborsY))
                                    except Exception:
                                        pass
                                else:
                                    try:
                                        model.addCons(Z_Var <= 0)
                                    except Exception:
                                        pass


# ---------------------------------------------------------------------------
# Constraint 3 — selectedSwitches
# ---------------------------------------------------------------------------

def constraintNum3selectedSwitches(pSwitchesTopology, numberSlotsSwitches,
                                   usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                                   neighborsofEachSwitch, pSwitchPorts, Z_Used,
                                   clusterSets, switchinClusters, AllClusters):
    for i in range(0, len(switchinClusters)):
        for switches in switchinClusters[i]:
            for slots in numberSlotsSwitches[switches]:
                for timesNumber in clusterSets[i][1][0]:
                    for sub in clusterSets[i][0]:
                        if len(sub) > 1:
                            set_of_sets = {frozenset(s) for s in sub}
                            Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                        timesNumber[0], timesNumber[1])
                            if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                Z_Var = Z_Variables[Z_Var_Id]
                            for subSubSub in sub:
                                keyDictNeighborsY = []
                                for t in range(max(timesNumber[0] - 1, 0), timesNumber[1]):
                                    for neighbor in neighborsofEachSwitch[switches]:
                                        try:
                                            portNeighborSwitch = pSwitchPorts[neighbor]
                                        except Exception:
                                            pass
                                        for portt in portNeighborSwitch:
                                            if portNeighborSwitch[portt] == switches:
                                                keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                try:
                                                    keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                except Exception:
                                                    pass
                                if len(keyDictNeighborsY) > 0:
                                    try:
                                        model.addCons(Z_Var <= sum(keyDictNeighborsY))
                                    except Exception:
                                        pass
                                else:
                                    try:
                                        model.addCons(Z_Var <= 0)
                                    except Exception:
                                        pass

    for switches in pSwitchesTopology:
        if switches not in AllClusters:
            for slots in numberSlotsSwitches[switches]:
                for timesNumber in usefulIntervalTime:
                    for sub in subSets:
                        for subSub in sub:
                            if len(subSub) > 1:
                                set_of_sets = {frozenset(s) for s in subSub}
                                Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                            timesNumber[0], timesNumber[1])
                                if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                    Z_Var = Z_Variables[Z_Var_Id]
                                for subSubSub in subSub:
                                    keyDictNeighborsY = []
                                    for t in range(max(timesNumber[0] - 1, 0), timesNumber[1]):
                                        for neighbor in neighborsofEachSwitch[switches]:
                                            try:
                                                portNeighborSwitch = pSwitchPorts[neighbor]
                                            except Exception:
                                                pass
                                            for portt in portNeighborSwitch:
                                                if portNeighborSwitch[portt] == switches:
                                                    keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                    try:
                                                        keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                    except Exception:
                                                        pass
                                    if len(keyDictNeighborsY) > 0:
                                        try:
                                            model.addCons(Z_Var <= sum(keyDictNeighborsY))
                                        except Exception:
                                            pass
                                    else:
                                        try:
                                            model.addCons(Z_Var <= 0)
                                        except Exception:
                                            pass


# ---------------------------------------------------------------------------
# Constraint 3 — selectedSwitches ATP
# ---------------------------------------------------------------------------

def constraintNum3selectedSwitchesATP(pSwitchesTopology, numberSlotsSwitches,
                                      usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                                      neighborsofEachSwitch, pSwitchPorts, Z_Used,
                                      clusterSets, switchinClusters, AllClusters):
    for i in range(0, len(switchinClusters)):
        for switches in switchinClusters[i]:
            for slots in numberSlotsSwitches[switches]:
                for timesNumber in clusterSets[i][1][0]:
                    for sub in clusterSets[i][0]:
                        if len(sub) > 1:
                            set_of_sets = {frozenset(s) for s in sub}
                            Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                        timesNumber[0], timesNumber[1])
                            if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                Z_Var = Z_Variables[Z_Var_Id]
                            for subSubSub in sub:
                                keyDictNeighborsY = []
                                for t in range(T_max_1, timesNumber[1]):
                                    for neighbor in neighborsofEachSwitch[switches]:
                                        try:
                                            portNeighborSwitch = pSwitchPorts[neighbor]
                                        except Exception:
                                            pass
                                        for portt in portNeighborSwitch:
                                            if portNeighborSwitch[portt] == switches:
                                                keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                if neighbor in workersTopology:
                                                    if t == T_max_1:
                                                        try:
                                                            keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                        except Exception:
                                                            pass
                                                else:
                                                    try:
                                                        keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                    except Exception:
                                                        pass
                                if len(keyDictNeighborsY) > 0:
                                    try:
                                        model.addCons(Z_Var <= sum(keyDictNeighborsY))
                                    except Exception:
                                        pass
                                else:
                                    try:
                                        model.addCons(Z_Var <= 0)
                                    except Exception:
                                        pass

    for switches in pSwitchesTopology:
        if switches not in AllClusters:
            for slots in numberSlotsSwitches[switches]:
                for timesNumber in usefulIntervalTime:
                    for sub in subSets:
                        for subSub in sub:
                            if len(subSub) > 1:
                                set_of_sets = {frozenset(s) for s in subSub}
                                Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                            timesNumber[0], timesNumber[1])
                                if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                    Z_Var = Z_Variables[Z_Var_Id]
                                for subSubSub in subSub:
                                    keyDictNeighborsY = []
                                    for t in range(T_max_1, timesNumber[1]):
                                        for neighbor in neighborsofEachSwitch[switches]:
                                            try:
                                                portNeighborSwitch = pSwitchPorts[neighbor]
                                            except Exception:
                                                pass
                                            for portt in portNeighborSwitch:
                                                if portNeighborSwitch[portt] == switches:
                                                    if neighbor in workersTopology:
                                                        if t == T_max_1:
                                                            keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                            try:
                                                                keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                            except Exception:
                                                                pass
                                                    else:
                                                        keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                        try:
                                                            keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                        except Exception:
                                                                pass
                                    if len(keyDictNeighborsY) > 0:
                                        try:
                                            model.addCons(Z_Var <= sum(keyDictNeighborsY))
                                        except Exception:
                                            pass
                                    else:
                                        try:
                                            model.addCons(Z_Var <= 0)
                                        except Exception:
                                            pass


# ---------------------------------------------------------------------------
# Constraint 4 — basic
# ---------------------------------------------------------------------------

def constraintNum4(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
                   pSwitchPorts, Z_Used):
    M = 100
    for switches in pSwitchesTopology:
        for sub in subSets:
            for subSub in sub:
                if len(subSub) > 1:
                    for slots in numberSlotsSwitches[switches]:
                        for timesNumber in usefulIntervalTime:
                            set_of_sets = {frozenset(s) for s in subSub}
                            Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                        timesNumber[0], timesNumber[1])
                            if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                Z_Var = Z_Variables[Z_Var_Id]
                                for t in range(max(0, timesNumber[0] - 1), timesNumber[1]):
                                    keyDictNeighborsY = []
                                    for neighbor in neighborsofEachSwitch[switches]:
                                        try:
                                            portNeighborSwitch = pSwitchPorts[neighbor]
                                        except Exception:
                                            pass
                                        for portt in portNeighborSwitch:
                                            if portNeighborSwitch[portt] == switches:
                                                for subSubSub in subSub:
                                                    keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                    try:
                                                        keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                    except Exception:
                                                        pass
                                    model.addCons(sum(keyDictNeighborsY) <= Z_Var + (1 - Z_Var) * M)


# ---------------------------------------------------------------------------
# Constraint 4 — selectedSwitches
# ---------------------------------------------------------------------------

def constraintNum4selectedSwitches(pSwitchesTopology, numberSlotsSwitches,
                                   usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                                   neighborsofEachSwitch, pSwitchPorts, Z_Used,
                                   clusterSets, switchinClusters, AllClusters):
    for i in range(0, len(switchinClusters)):
        M = 100
        for switches in switchinClusters[i]:
            for sub in clusterSets[i][0]:
                if len(sub) > 1:
                    for slots in numberSlotsSwitches[switches]:
                        for timesNumber in clusterSets[i][1][0]:
                            set_of_sets = {frozenset(s) for s in sub}
                            Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                        timesNumber[0], timesNumber[1])
                            if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                Z_Var = Z_Variables[Z_Var_Id]
                                for t in range(max(0, timesNumber[0] - 1), timesNumber[1]):
                                    keyDictNeighborsY = []
                                    for neighbor in neighborsofEachSwitch[switches]:
                                        try:
                                            portNeighborSwitch = pSwitchPorts[neighbor]
                                        except Exception:
                                            pass
                                        for portt in portNeighborSwitch:
                                            if portNeighborSwitch[portt] == switches:
                                                for subSubSub in sub:
                                                    keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                    try:
                                                        keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                    except Exception:
                                                        pass
                                    model.addCons(sum(keyDictNeighborsY) <= Z_Var + (1 - Z_Var) * M)
    M = 100
    for switches in pSwitchesTopology:
        if switches not in AllClusters:
            for sub in subSets:
                for subSub in sub:
                    if len(subSub) > 1:
                        for slots in numberSlotsSwitches[switches]:
                            for timesNumber in usefulIntervalTime:
                                set_of_sets = {frozenset(s) for s in subSub}
                                Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                            timesNumber[0], timesNumber[1])
                                if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                    Z_Var = Z_Variables[Z_Var_Id]
                                    for t in range(max(0, timesNumber[0] - 1), timesNumber[1]):
                                        keyDictNeighborsY = []
                                        for neighbor in neighborsofEachSwitch[switches]:
                                            try:
                                                portNeighborSwitch = pSwitchPorts[neighbor]
                                            except Exception:
                                                pass
                                            for portt in portNeighborSwitch:
                                                if portNeighborSwitch[portt] == switches:
                                                    for subSubSub in subSub:
                                                        keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                        try:
                                                            keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                        except Exception:
                                                            pass
                                        model.addCons(sum(keyDictNeighborsY) <= Z_Var + (1 - Z_Var) * M)


# ---------------------------------------------------------------------------
# Constraint 4 — selectedSwitches ATP
# ---------------------------------------------------------------------------

def constraintNum4selectedSwitchesATP(pSwitchesTopology, numberSlotsSwitches,
                                      usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                                      neighborsofEachSwitch, pSwitchPorts, Z_Used,
                                      clusterSets, switchinClusters, AllClusters):
    for i in range(0, len(switchinClusters)):
        M = 100
        for switches in switchinClusters[i]:
            for sub in clusterSets[i][0]:
                if len(sub) > 1:
                    for slots in numberSlotsSwitches[switches]:
                        for timesNumber in clusterSets[i][1][0]:
                            set_of_sets = {frozenset(s) for s in sub}
                            Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                        timesNumber[0], timesNumber[1])
                            if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                Z_Var = Z_Variables[Z_Var_Id]
                                for t in range(T_max_1, timesNumber[1]):
                                    keyDictNeighborsY = []
                                    for neighbor in neighborsofEachSwitch[switches]:
                                        try:
                                            portNeighborSwitch = pSwitchPorts[neighbor]
                                        except Exception:
                                            pass
                                        for portt in portNeighborSwitch:
                                            if portNeighborSwitch[portt] == switches:
                                                if neighbor in workersTopology:
                                                    if t == T_max_1:
                                                        for subSubSub in sub:
                                                            keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                            try:
                                                                keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                            except Exception:
                                                                pass
                                                else:
                                                    for subSubSub in sub:
                                                        keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                        try:
                                                            keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                        except Exception:
                                                            pass
                                    model.addCons(sum(keyDictNeighborsY) <= Z_Var + (1 - Z_Var) * M)
    M = 100
    for switches in pSwitchesTopology:
        if switches not in AllClusters:
            for sub in subSets:
                for subSub in sub:
                    if len(subSub) > 1:
                        for slots in numberSlotsSwitches[switches]:
                            for timesNumber in usefulIntervalTime:
                                set_of_sets = {frozenset(s) for s in subSub}
                                Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                            timesNumber[0], timesNumber[1])
                                if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                    Z_Var = Z_Variables[Z_Var_Id]
                                    for t in range(T_max_1, timesNumber[1]):
                                        keyDictNeighborsY = []
                                        for neighbor in neighborsofEachSwitch[switches]:
                                            try:
                                                portNeighborSwitch = pSwitchPorts[neighbor]
                                            except Exception:
                                                pass
                                            for portt in portNeighborSwitch:
                                                if portNeighborSwitch[portt] == switches:
                                                    if neighbor in workersTopology:
                                                        if t == T_max_1:
                                                            for subSubSub in subSub:
                                                                keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                                try:
                                                                    keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                                except Exception:
                                                                    pass
                                                    else:
                                                        for subSubSub in subSub:
                                                            keyDictY = (frozenset(subSubSub), neighbor, portt, t)
                                                            try:
                                                                keyDictNeighborsY.append(Y_Variables[keyDictY])
                                                            except Exception:
                                                                pass
                                        model.addCons(sum(keyDictNeighborsY) <= Z_Var + (1 - Z_Var) * M)


# ---------------------------------------------------------------------------
# Constraint 5
# ---------------------------------------------------------------------------

def constraintNum5(workersTopology, fragmentsofEachWorker, pWorkerPorts,
                   model, T_max_1, T_max_2, Y_Used):
    for worker in workersTopology:
        for frag in fragmentsofEachWorker[worker]:
            tempArray = []
            for port in pWorkerPorts[worker]:
                for time in range(T_max_1, T_max_2):
                    fragg = {frag}
                    keyDictY = (frozenset(fragg), worker, port, time)
                    if keyDictY not in Y_Used:
                        tempArray.append(Y_Variables[keyDictY])
            model.addCons(sum(tempArray) == 1)


# ---------------------------------------------------------------------------
# Constraint 5 ATP
# ---------------------------------------------------------------------------

def constraintNum5ATP(workersTopology, fragmentsofEachWorker, pWorkerPorts,
                      model, T_max_1, T_max_2, Y_Used):
    time = T_max_1
    for worker in workersTopology:
        for frag in fragmentsofEachWorker[worker]:
            tempArray = []
            for port in pWorkerPorts[worker]:
                fragg = {frag}
                keyDictY = (frozenset(fragg), worker, port, time)
                if keyDictY not in Y_Used:
                    tempArray.append(Y_Variables[keyDictY])
                    time += 1
            model.addCons(sum(tempArray) == 1)


# ---------------------------------------------------------------------------
# Constraint 6
# ---------------------------------------------------------------------------

def constraintNum6(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
                   pSwitchPorts, Z_Used, Y_Used):
    all_subsets = set()
    for sub in subSets:
        for subSub in sub:
            set_of_sets = {frozenset(s) for s in subSub}
            union_set = frozenset().union(*set_of_sets)
            all_subsets.add(union_set)

    for switches in pSwitchesTopology:
        for ports in pSwitchPorts[switches]:
            for union_set in all_subsets:
                for time in range(T_max_1, T_max_2):
                    keyDictY = (frozenset(union_set), switches, ports, time)
                    if keyDictY not in Y_Used:
                        try:
                            Specific_Y = Y_Variables[keyDictY]
                        except Exception:
                            pass
                    tempArray5 = []
                    for sub2 in subSets:
                        for subSub2 in sub2:
                            set_of_sets2 = {frozenset(s) for s in subSub2}
                            union_set2 = frozenset().union(*set_of_sets2)
                            if union_set2 == union_set:
                                for t in range(0, time):
                                    for slots in numberSlotsSwitches[switches]:
                                        keyDictZ = (frozenset(set_of_sets2), slots, switches, t, time)
                                        try:
                                            tempArray5.append(Z_Variables[keyDictZ])
                                        except Exception:
                                            pass
                    keyDictNeighborsY = []
                    if time != 0:
                        for neighbor in neighborsofEachSwitch[switches]:
                            try:
                                portNeighborSwitch = pSwitchPorts[neighbor]
                            except Exception:
                                pass
                            for portt in portNeighborSwitch:
                                if portNeighborSwitch[portt] == switches:
                                    keyDictY2 = (frozenset(union_set), neighbor, portt, time - 1)
                                    if keyDictY2 in Y_Variables:
                                        keyDictNeighborsY.append(Y_Variables[keyDictY2])
                    try:
                        model.addCons(Specific_Y <= sum(keyDictNeighborsY) + sum(tempArray5))
                    except Exception:
                        pass


# ---------------------------------------------------------------------------
# Constraint 7 — basic
# ---------------------------------------------------------------------------

def constraintNum7(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, T_max_1, T_max_2, pSwitchPorts, Z_Used, Y_Used):
    for switches in pSwitchesTopology:
        for ports in pSwitchPorts[switches]:
            for sub in subSets:
                for subSub in sub:
                    if len(subSub) > 1:
                        for timesNumber in usefulIntervalTime:
                            set_of_sets = {frozenset(s) for s in subSub}
                            for slots in numberSlotsSwitches[switches]:
                                Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                            timesNumber[0], timesNumber[1])
                                if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                    Z_Var = Z_Variables[Z_Var_Id]
                            for subSubSub in subSub:
                                for t in range(timesNumber[0], T_max_2):
                                    Y_Var_Id = (frozenset(subSubSub), switches, ports, t)
                                    if Y_Var_Id not in Y_Used:
                                        if Y_Var_Id in Y_Variables:
                                            try:
                                                model.addCons(Y_Variables[Y_Var_Id] <= 1 - Z_Var)
                                            except Exception:
                                                pass


# ---------------------------------------------------------------------------
# Constraint 7 — selectedSwitches
# ---------------------------------------------------------------------------

def constraintNum7selectedSwitches(pSwitchesTopology, numberSlotsSwitches,
                                   usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                                   pSwitchPorts, Z_Used, Y_Used, clusterSets,
                                   switchinClusters, AllClusters):
    for i in range(0, len(switchinClusters)):
        for switches in switchinClusters[i]:
            for ports in pSwitchPorts[switches]:
                for sub in clusterSets[i][0]:
                    if len(sub) > 1:
                        for timesNumber in clusterSets[i][1][0]:
                            set_of_sets = {frozenset(s) for s in sub}
                            for slots in numberSlotsSwitches[switches]:
                                Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                            timesNumber[0], timesNumber[1])
                                if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                    Z_Var = Z_Variables[Z_Var_Id]
                            for subSubSub in sub:
                                for t in range(timesNumber[0], T_max_2):
                                    Y_Var_Id = (frozenset(subSubSub), switches, ports, t)
                                    if Y_Var_Id not in Y_Used:
                                        if Y_Var_Id in Y_Variables:
                                            try:
                                                model.addCons(Y_Variables[Y_Var_Id] <= 1 - Z_Var)
                                            except Exception:
                                                pass
    for switches in pSwitchesTopology:
        if switches not in AllClusters:
            for ports in pSwitchPorts[switches]:
                for sub in subSets:
                    for subSub in sub:
                        if len(subSub) > 1:
                            for timesNumber in usefulIntervalTime:
                                set_of_sets = {frozenset(s) for s in subSub}
                                for slots in numberSlotsSwitches[switches]:
                                    Z_Var_Id = (frozenset(set_of_sets), slots, switches,
                                                timesNumber[0], timesNumber[1])
                                    if Z_Var_Id not in Z_Used and Z_Var_Id in Z_Variables.keys():
                                        Z_Var = Z_Variables[Z_Var_Id]
                                for subSubSub in subSub:
                                    for t in range(timesNumber[0], T_max_2):
                                        Y_Var_Id = (frozenset(subSubSub), switches, ports, t)
                                        if Y_Var_Id not in Y_Used:
                                            if Y_Var_Id in Y_Variables:
                                                try:
                                                    model.addCons(Y_Variables[Y_Var_Id] <= 1 - Z_Var)
                                                except Exception:
                                                    pass


# ---------------------------------------------------------------------------
# Constraint 8
# ---------------------------------------------------------------------------

def constraintNum8(pSwitchesTopology, subSets, model, T_max_1, T_max_2,
                   neighborsofEachSwitch, pSwitchPorts, Y_Used):
    all_subsets = set()
    for sub in subSets:
        for subSub in sub:
            set_of_sets = {frozenset(s) for s in subSub}
            union_set = frozenset().union(*set_of_sets)
            all_subsets.add(union_set)

    for switches in pSwitchesTopology:
        for t in range(T_max_1, T_max_2):
            for sub in all_subsets:
                temporarySumArray = []
                for ports in pSwitchPorts[switches]:
                    Y_Var_Id = (frozenset(sub), switches, ports, t)
                    if Y_Var_Id not in Y_Used:
                        if Y_Var_Id in Y_Variables:
                            temporarySumArray.append(Y_Variables[Y_Var_Id])
                if len(temporarySumArray) != 0:
                    model.addCons(sum(temporarySumArray) <= 1)


# ---------------------------------------------------------------------------
# Constraint 9
# ---------------------------------------------------------------------------

def constraintNum9(pSwitchesTopology, subSets, model, T_max_1, T_max_2,
                   neighborsofEachSwitch, pSwitchPorts, Y_Used):
    all_subsets = set()
    for sub in subSets:
        for subSub in sub:
            set_of_sets = {frozenset(s) for s in subSub}
            union_set = frozenset().union(*set_of_sets)
            all_subsets.add(union_set)

    for switches in pSwitchesTopology:
        for time in range(T_max_1, T_max_2):
            for ports in pSwitchPorts[switches]:
                temporarySumArray = []
                for sub in all_subsets:
                    keyDictY = (frozenset(sub), switches, ports, time)
                    if keyDictY not in Y_Used:
                        if keyDictY in Y_Variables:
                            temporarySumArray.append(Y_Variables[keyDictY])
                if len(temporarySumArray) != 0:
                    model.addCons(sum(temporarySumArray) <= 1)


# ---------------------------------------------------------------------------
# Constraint 10
# ---------------------------------------------------------------------------

def constraintNum10(pSwitchesTopology, subSets, model, T_max_1, T_max_2,
                    neighborsofEachSwitch, pSwitchPorts, numAllFrags, Y_Used):
    all_subsets = set()
    for sub in subSets:
        for subSub in sub:
            set_of_sets = {frozenset(s) for s in subSub}
            union_set = frozenset().union(*set_of_sets)
            all_subsets.add(union_set)

    keyDictYSum = []
    for switches in pSwitchesTopology:
        for ports in pSwitchPorts[switches]:
            if pSwitchPorts[switches][ports] == "PS":
                for sub in all_subsets:
                    for time in range(T_max_1, T_max_2):
                        keyDictY = (frozenset(sub), switches, ports, time)
                        if keyDictY not in Y_Used:
                            if keyDictY in Y_Variables:
                                keyDictYSum.append(Y_Variables[keyDictY] * len(sub))
    model.addCons(sum(keyDictYSum) == numAllFrags)


# ---------------------------------------------------------------------------
# Constraint 11
# ---------------------------------------------------------------------------

def constraintNum11(pSwitchesTopology, subSets, model, workersTopology,
                    pSwitchPorts, Y_Used, T_max_1):
    for switches in pSwitchesTopology:
        if switches not in workersTopology:
            for ports in pSwitchPorts[switches]:
                for sub in subSets:
                    for subSub in sub:
                        for subSubSub in subSub:
                            keyDictY = (frozenset(subSubSub), switches, ports, T_max_1)
                            if keyDictY not in Y_Used:
                                if keyDictY in Y_Variables:
                                    model.addCons(Y_Variables[keyDictY] == 0)


# ---------------------------------------------------------------------------
# Constraint InArt — single aggregation per fragment (InArt assumption)
# Each fragment can be aggregated at AT MOST ONE switch globally.
# This enforces: for each fragment f, sum of all Z_vars involving f <= 1.
# ---------------------------------------------------------------------------

def constraintInArt(subSets, model, Z_Used, workersTopology, fragmentsofEachWorker):
    all_fragments = set()
    for worker in fragmentsofEachWorker:
        for frag in fragmentsofEachWorker[worker]:
            all_fragments.add(frag)

    for frag in all_fragments:
        frag_set = frozenset({frag})
        z_vars_for_frag = []
        for key, var in Z_Variables.items():
            if key in Z_Used:
                continue
            subset_of_sets = key[0]
            for sub_frozen in subset_of_sets:
                if frag_set <= sub_frozen:
                    z_vars_for_frag.append(var)
                    break
        if len(z_vars_for_frag) > 0:
            model.addCons(sum(z_vars_for_frag) <= 1)
