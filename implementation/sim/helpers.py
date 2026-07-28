"""Helper functions — key lookup, set intersection, pre-processing mappings."""


def build_frag_to_worker(fragmentsofEachWorker):
    """Build reverse mapping: fragment id -> worker id."""
    mapping = {}
    for worker, frags in fragmentsofEachWorker.items():
        for frag in frags:
            mapping[frag] = worker
    return mapping


def find_keys_by_value(target_set, data_dict):
    return [key for key, values in data_dict.items()
            if target_set.issubset(set(values))]


def has_common_element(arr1, arr2):
    return not set(arr1).isdisjoint(set(arr2))


def remove_matching_pairs(pairs, numbers):
    removeList = []
    for timeN in pairs:
        tempA = list(range(timeN[0], timeN[1] + 1))
        tempB = list(range(numbers[0], numbers[1] + 1))
        if has_common_element(tempA, tempB):
            removeList.append(timeN)
    return removeList


def preProcessMappingY(Y_Used, allofSubsets):
    if isinstance(Y_Used, list):
        Y_Used = set(Y_Used)
    new_entries = set()
    for used in Y_Used:
        firstKey = used[1]
        secondKey = used[2]
        thirdKey = used[3]
        for subset in allofSubsets:
            new_entries.add((frozenset(subset), firstKey, secondKey, thirdKey))
    Y_Used |= new_entries
    return Y_Used


def preProcessMappingZ(Z_Used, subSets, usefulIntervalTime):
    if isinstance(Z_Used, list):
        Z_Used = set(Z_Used)
    new_entries = set()
    for zused in Z_Used:
        firstKey = zused[1]
        secondKey = zused[2]
        thirdKey = zused[3]
        fourthKey = zused[4]
        removeTimes = remove_matching_pairs(usefulIntervalTime, [thirdKey, fourthKey])
        for sub in subSets:
            for i in sub:
                set_of_sets = frozenset(frozenset(s) for s in i)
                for timeN in usefulIntervalTime:
                    if timeN in removeTimes:
                        new_entries.add(
                            (set_of_sets, firstKey, secondKey, timeN[0], timeN[1]))
    Z_Used |= new_entries
    return Z_Used
