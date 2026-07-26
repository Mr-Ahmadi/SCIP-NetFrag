"""FlexINA per-solve helper used by run_inart_comparison and run_param_sweep.

Kept in a dedicated module so the InArt comparison block and the (ρ × τ_F)
parameter sweep block can both call into one implementation without
introducing a circular dependency between the two block modules.
"""
from blocks._imports import (
    TimeoutError, _timeout_handler, apply_constraints, create_Fragments, defineModel_selectedSwitches, objective, preProcessMappingY, preProcessMappingZ, signal, solveProblem, time,
)


def _solve_flexina_once(env_tuple, dict_list_items, max_aggregation,
                        T_max_1, T_max_2, percentage, steps_to_switches=None,
                        timeout_sec=60):
    """
    Run one FlexINA SCIP solve for a single dict_list slice.

    Parameters
    ----------
    env_tuple       : unpacked environment tuple (15-element)
    dict_list_items : dict[worker]->list[frag] for this slot
    max_aggregation : max aggregation level (passed to create_Fragments)
    T_max_1, T_max_2: current time-window bounds (τ_F ≈ T_max_2 - T_max_1)
    percentage      : ρ, switch selection fraction

    Returns
    -------
    (numPacket, Runtime, status, Y_Used, Z_Used, timed_out, construction_time)
    where ``construction_time`` is the wall time spent in create_Fragments
    + define* + apply_constraints + objective (i.e. everything *before*
    the SCIP optimize call) — used by callers for JSON-recorded timing
    breakdowns.
    """
    (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
     pSwitchesNumber, numberSlotsSwitches, workersTopology,
     pWorkerPorts, workersNumber, numAllFrags,
     _, _totalWorkers, _stepsToSwitches, cutPorts, selectedSwitches,
     clusters) = env_tuple
    stepsToSwitches = _stepsToSwitches if steps_to_switches is None else steps_to_switches

    Y_Used, Z_Used = set(), set()
    timed_out = False
    construction_time = 0.0
    # The reliable time-limit path is SCIP's own "limits/time" (set inside
    # solveProblem via time_limit=timeout_sec). We keep the SIGALRM only as
    # a generous safety net (timeout_sec + 5s) so a frozen C call doesn't
    # wedge the sweep forever; SIGALRM cannot interrupt SCIP's C optimize
    # anyway, so the alarm only fires *after* optimize returns to Python.
    if timeout_sec and timeout_sec > 0:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(int(timeout_sec) + 5)
    tc0 = time.time()
    try:
        subSets, allofSubsets, usefulIntervalTime, fragments = \
            create_Fragments(dict_list_items, T_max_1, T_max_2, max_aggregation)
        Y_Used = preProcessMappingY(Y_Used, allofSubsets[0])
        Z_Used = preProcessMappingZ(Z_Used, subSets, usefulIntervalTime)
        (model, Z_Variables, Y_Variables, Prm1, Prm2,
         clusterSets, switchinClusters, AllClusters) = \
            defineModel_selectedSwitches(
                allofSubsets, pSwitchesTopology, pSwitchPorts,
                T_max_1, T_max_2, workersTopology, dict_list_items,
                pWorkerPorts, subSets, numberSlotsSwitches,
                usefulIntervalTime, Y_Used, Z_Used, max_aggregation,
                stepsToSwitches, cutPorts, selectedSwitches, percentage, clusters)
        apply_constraints(
            defineModel_selectedSwitches, pSwitchesTopology, numberSlotsSwitches,
            usefulIntervalTime, subSets, model, T_max_1, T_max_2,
            Z_Used, Y_Used, neighborsofEachSwitch, pSwitchPorts,
            workersTopology, dict_list_items, pWorkerPorts,
            numAllFrags, clusterSets, switchinClusters, AllClusters,
            Y_Variables, Z_Variables)
        objective(Y_Variables, model)
        construction_time = time.time() - tc0
        Y_Value_One, Z_Value_One, Y_Used, Z_Used, numPacket, Runtime, status = \
            solveProblem(model, Y_Used, Z_Used, time_limit=timeout_sec)
    except TimeoutError:
        # SIGALRM-only safety net (should be rare with limits/time set).
        # The alarm was armed for timeout_sec + 5s; if it fired we record
        # that elapsed time honestly instead of 0, so callers (and
        # downstream statistics) see the true cost of the failed solve.
        signal.alarm(0)
        numPacket, Runtime, status = 0, time.time() - tc0, "timeout"
        timed_out = True
        construction_time = time.time() - tc0
    except (IndexError, KeyError, ValueError, AssertionError) as e:
        # Some (ρ, τ) combos produce an empty/infeasible SCIP model.
        # Treat as a skip so the sweep doesn't abort. Charge real elapsed
        # time (the construction work up to the failure was still spent),
        # so callers can compare (ρ, τ) cells honestly.
        signal.alarm(0)
        numPacket, Runtime, status = 0, time.time() - tc0, f"skip:{type(e).__name__}"
        timed_out = True
        construction_time = time.time() - tc0
    finally:
        signal.alarm(0)
    return numPacket, Runtime, status, Y_Used, Z_Used, timed_out, construction_time


# Reference (no aggregation) packets, computed once per env+window.
# Used to define "packet reduction" for the trade-off scatter: reduction = 1 - pkts/pkts_optimal
def _no_aggregation_packets(env_tuple, dict_list, T_max_1, T_max_2,
                            timeout_sec=60):
    """Run FlexINA with max_aggregation=1 (i.e. no in-network aggregation)
    to count the packets that would be sent without aggregation.

    Accepts any feasible primal (not just provably-optimal), so the
    reference value is available even if the no-aggregation ILP reaches
    the time limit with only a primal bound.
    """
    total_packets = 0
    total_runtime = 0.0
    for items in dict_list:
        numPacket, Runtime, status, _, _, _, _ = _solve_flexina_once(
            env_tuple, items, max_aggregation=1,
            T_max_1=T_max_1, T_max_2=T_max_2, percentage=1.0,
            timeout_sec=timeout_sec)
        if numPacket and numPacket > 0:
            total_packets += numPacket
            total_runtime += Runtime
        else:
            # No primal of any kind: cannot define a reference for this env.
            return 0, 0.0
    return total_packets, total_runtime


# ============================================================
# Block #6 — 2-D (ρ × τ_F) sweep: heatmaps + trade-off scatter
# ============================================================
