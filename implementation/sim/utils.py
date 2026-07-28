"""Utility functions — timeout handling, set operations, fragment creation."""
import ast
import itertools
import threading
from itertools import combinations


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("iteration timed out")


def _run_with_timeout(func, timeout_sec):
    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout_sec)
    if t.is_alive():
        raise TimeoutError("iteration timed out (thread)")
    if exception[0] is not None:
        raise exception[0]
    return result[0]


def normalize_and_compare(s1, s2):
    parsed1 = ast.literal_eval(s1)
    parsed2 = ast.literal_eval(s2)
    normalized1 = (frozenset(parsed1[0]),) + parsed1[1:]
    normalized2 = (frozenset(parsed2[0]),) + parsed2[1:]
    return normalized1 == normalized2


def get_subsets(input_set):
    subsets = []
    for r in range(len(input_set) + 1):
        subsets.extend(itertools.combinations(input_set, r))
    del subsets[0]
    for i in range(0, len(subsets)):
        if len(subsets[i]) != 0:
            subsets[i] = set(subsets[i])
    return subsets


def subsets_of_subsets(s, max_size=10):
    s = list(s)
    if len(s) > max_size:
        return [[set(s)]]

    def partitions(s):
        if len(s) == 1:
            yield [s]
            return
        first = s[0]
        for smaller in partitions(s[1:]):
            for n, subset in enumerate(smaller):
                yield smaller[:n] + [[first] + subset] + smaller[n + 1:]
            yield [[first]] + smaller

    result = []
    for partition in partitions(s):
        result.append([set(subset) for subset in partition])
    return result


def create_Fragments(fragmentsofEachWorker, T_max_1, T_max_2, maxAggregation):
    maxLength = max(len(v) for v in fragmentsofEachWorker.values())
    fragments = [set() for _ in range(maxLength)]
    for worker_fragments in fragmentsofEachWorker.values():
        for i, fragment in enumerate(worker_fragments):
            fragments[i].add(fragment)
    allofSubsets = [get_subsets(f) for f in fragments]
    times = list(range(T_max_1, T_max_2))
    # Per JINA (Eqs. 3-4), a Z window ranges freely over the per-fragment horizon.
    usefulIntervalTime = [sorted(interval) for interval in combinations(times, 2)]
    subSets = [[sub for sub in subsets_of_subsets(subset)]
               for subset_list in allofSubsets for subset in subset_list]
    return subSets, allofSubsets, usefulIntervalTime, fragments
