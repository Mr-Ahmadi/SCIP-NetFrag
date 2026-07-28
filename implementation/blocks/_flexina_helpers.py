"""FlexINA per-solve helper used by run_inart_comparison and run_param_sweep."""
from blocks._imports import (
    TimeoutError, _timeout_handler, apply_constraints, create_Fragments, defineModel_selectedSwitches, objective, preProcessMappingY, preProcessMappingZ, signal, solveProblem, time,
)


def _solve_flexina_once(env_tuple, dict_list_items, max_aggregation,
                        T_max_1, T_max_2, percentage, steps_to_switches=None,
                        timeout_sec=60, apply_fn=None, gap=None,
                        Y_Used=None, Z_Used=None):
    """Run one FlexINA SCIP solve for a single dict_list slice.

    Returns (numPacket, Runtime, status, Y_Used, Z_Used, timed_out,
    construction_time). timed_out is True only when NO usable incumbent
    came back.
    """
    if apply_fn is None:
        apply_fn = apply_constraints
    (pSwitchesTopology, pSwitchPorts, neighborsofEachSwitch,
     pSwitchesNumber, numberSlotsSwitches, workersTopology,
     pWorkerPorts, workersNumber, numAllFrags,
     _, _totalWorkers, _stepsToSwitches, cutPorts, selectedSwitches,
     clusters) = env_tuple
    stepsToSwitches = _stepsToSwitches if steps_to_switches is None else steps_to_switches

    Y_Used = set() if Y_Used is None else Y_Used
    Z_Used = set() if Z_Used is None else Z_Used
    timed_out = False
    construction_time = 0.0
    # SCIP's own "limits/time" is the reliable time-limit path. SIGALRM
    # is only a generous safety net (timeout_sec + 5s).
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
        apply_fn(
            defineModel_selectedSwitches, pSwitchesTopology, numberSlotsSwitches,
            usefulIntervalTime, subSets, model, T_max_1, T_max_2,
            Z_Used, Y_Used, neighborsofEachSwitch, pSwitchPorts,
            workersTopology, dict_list_items, pWorkerPorts,
            numAllFrags, clusterSets, switchinClusters, AllClusters,
            Y_Variables, Z_Variables)
        objective(Y_Variables, model)
        construction_time = time.time() - tc0
        Y_Value_One, Z_Value_One, Y_Used, Z_Used, numPacket, Runtime, status = \
            solveProblem(model, Y_Used, Z_Used, time_limit=timeout_sec, gap=gap)
        if not numPacket:
            # Terminal SCIP status with no usable incumbent — failed attempt.
            timed_out = True
    except TimeoutError:
        signal.alarm(0)
        numPacket, Runtime, status = 0, time.time() - tc0, "timeout"
        timed_out = True
        construction_time = time.time() - tc0
    except (IndexError, KeyError, ValueError, AssertionError) as e:
        # Empty/infeasible model — skip so sweep doesn't abort.
        signal.alarm(0)
        numPacket, Runtime, status = 0, time.time() - tc0, f"skip:{type(e).__name__}"
        timed_out = True
        construction_time = time.time() - tc0
    finally:
        signal.alarm(0)
    return numPacket, Runtime, status, Y_Used, Z_Used, timed_out, construction_time


def _no_aggregation_packets(env_tuple, dict_list, T_max_1, T_max_2,
                            timeout_sec=60):
    """Run FlexINA with max_aggregation=1 (no aggregation) for reference packet count."""
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
            return 0, 0.0
    return total_packets, total_runtime
