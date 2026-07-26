"""
Runner — constraint application dispatcher.

apply_constraints() replaces the ~30-line repeated constraint-call block
that was copy-pasted in every execution block.
"""
from . import constraints as _cons
from .constraints import (
    constraintNum1selectedSwitches,
    constraintNum2selectedSwitches,
    constraintNum3selectedSwitches,
    constraintNum3selectedSwitchesATP,
    constraintNum4selectedSwitches,
    constraintNum4selectedSwitchesATP,
    constraintNum5,
    constraintNum5ATP,
    constraintNum6,
    constraintNum7selectedSwitches,
    constraintNum8,
    constraintNum9,
    constraintNum10,
    constraintNum11,
    constraintNum1,
    constraintNum2,
    constraintNum3,
    constraintNum4,
    constraintNum7,
)
from .models import (
    defineModel_ATP,
    defineModel_GRID,
    defineModel_ATP_GRID,
    defineModel_selectedSwitches,
)

_ATP_MODELS = (defineModel_ATP, defineModel_GRID)


def apply_constraints(modelSolve, pSwitchesTopology, numberSlotsSwitches,
                      usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                      Z_Used, Y_Used, neighborsofEachSwitch, pSwitchPorts,
                      workersTopology, fragmentsofEachWorker, pWorkerPorts,
                      numAllFrags, clusterSets, switchinClusters, AllClusters,
                      Y_Variables, Z_Variables):
    """
    Apply all constraints based on model type.
    Replaces the repeated if/else constraint-application blocks.
    """
    _cons.Y_Variables = Y_Variables
    _cons.Z_Variables = Z_Variables
    _cons.workersTopology = workersTopology

    is_atp = modelSolve in _ATP_MODELS

    # Constraints 1 & 2 (per-switch slot & time capacity over the selected-
    # switch Z variables) are required for the FlexINA cluster path — without
    # them the cluster aggregated-fragments are unbounded and the model can
    # over-aggregate (returning a packet count below the true optimum).
    # Mirrors the archive reference's defineModel_selectedSwitches block.
    constraintNum1selectedSwitches(
        pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
        subSets, model, Z_Used, clusterSets, switchinClusters, AllClusters)
    constraintNum2selectedSwitches(
        pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
        subSets, model, T_max_1, T_max_2, Z_Used, clusterSets,
        switchinClusters, AllClusters)

    if is_atp:
        constraintNum3selectedSwitches(
            pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
            subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
            pSwitchPorts, Z_Used, clusterSets, switchinClusters, AllClusters)
        constraintNum4selectedSwitchesATP(
            pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
            subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
            pSwitchPorts, Z_Used, clusterSets, switchinClusters, AllClusters)
    else:
        constraintNum3selectedSwitches(
            pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
            subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
            pSwitchPorts, Z_Used, clusterSets, switchinClusters, AllClusters)
        constraintNum4selectedSwitches(
            pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
            subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
            pSwitchPorts, Z_Used, clusterSets, switchinClusters, AllClusters)

    constraintNum7selectedSwitches(
        pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
        subSets, model, T_max_1, T_max_2, pSwitchPorts, Z_Used, Y_Used,
        clusterSets, switchinClusters, AllClusters)

    if is_atp:
        constraintNum5ATP(workersTopology, fragmentsofEachWorker,
                          pWorkerPorts, model, T_max_1, T_max_2, Y_Used)
    else:
        constraintNum5(workersTopology, fragmentsofEachWorker,
                       pWorkerPorts, model, T_max_1, T_max_2, Y_Used)

    constraintNum6(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
                   pSwitchPorts, Z_Used, Y_Used)

    if not is_atp:
        constraintNum9(pSwitchesTopology, subSets, model, T_max_1, T_max_2,
                       neighborsofEachSwitch, pSwitchPorts, Y_Used)

    constraintNum8(pSwitchesTopology, subSets, model, T_max_1, T_max_2,
                   neighborsofEachSwitch, pSwitchPorts, Y_Used)
    constraintNum10(pSwitchesTopology, subSets, model, T_max_1, T_max_2,
                    neighborsofEachSwitch, pSwitchPorts, numAllFrags, Y_Used)
    constraintNum11(pSwitchesTopology, subSets, model, workersTopology,
                    pSwitchPorts, Y_Used, T_max_1)


def apply_constraints_basic(modelSolve, pSwitchesTopology, numberSlotsSwitches,
                            usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                            Z_Used, Y_Used, neighborsofEachSwitch, pSwitchPorts,
                            workersTopology, fragmentsofEachWorker, pWorkerPorts,
                            numAllFrags, Y_Variables, Z_Variables):
    """
    Apply constraints for the basic (non-cluster) defineModel path.
    """
    _cons.Y_Variables = Y_Variables
    _cons.Z_Variables = Z_Variables
    _cons.workersTopology = workersTopology

    constraintNum1(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, Z_Used)
    constraintNum2(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, T_max_1, T_max_2, Z_Used)
    constraintNum3(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
                   pSwitchPorts, Z_Used)
    constraintNum4(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
                   pSwitchPorts, Z_Used)
    constraintNum5(workersTopology, fragmentsofEachWorker,
                   pWorkerPorts, model, T_max_1, T_max_2, Y_Used)
    constraintNum6(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
                   pSwitchPorts, Z_Used, Y_Used)
    constraintNum7(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, T_max_1, T_max_2, pSwitchPorts, Z_Used, Y_Used)
    constraintNum9(pSwitchesTopology, subSets, model, T_max_1, T_max_2,
                   neighborsofEachSwitch, pSwitchPorts, Y_Used)
    constraintNum8(pSwitchesTopology, subSets, model, T_max_1, T_max_2,
                   neighborsofEachSwitch, pSwitchPorts, Y_Used)
    constraintNum10(pSwitchesTopology, subSets, model, T_max_1, T_max_2,
                    neighborsofEachSwitch, pSwitchPorts, numAllFrags, Y_Used)
    constraintNum11(pSwitchesTopology, subSets, model, workersTopology,
                    pSwitchPorts, Y_Used, T_max_1)


def apply_constraints_InArt(modelSolve, pSwitchesTopology, numberSlotsSwitches,
                            usefulIntervalTime, subSets, model, T_max_1, T_max_2,
                            Z_Used, Y_Used, neighborsofEachSwitch, pSwitchPorts,
                            workersTopology, fragmentsofEachWorker, pWorkerPorts,
                            numAllFrags, clusterSets, switchinClusters, AllClusters,
                            Y_Variables, Z_Variables):
    """
    Apply constraints for the InArt baseline.
    Same as FlexINA cluster constraints + InArt single-aggregation constraint.
    """
    _cons.Y_Variables = Y_Variables
    _cons.Z_Variables = Z_Variables
    _cons.workersTopology = workersTopology

    constraintNum3selectedSwitches(
        pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
        subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
        pSwitchPorts, Z_Used, clusterSets, switchinClusters, AllClusters)

    constraintNum4selectedSwitches(
        pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
        subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
        pSwitchPorts, Z_Used, clusterSets, switchinClusters, AllClusters)

    constraintNum7selectedSwitches(
        pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
        subSets, model, T_max_1, T_max_2, pSwitchPorts, Z_Used, Y_Used,
        clusterSets, switchinClusters, AllClusters)

    constraintNum5(workersTopology, fragmentsofEachWorker,
                   pWorkerPorts, model, T_max_1, T_max_2, Y_Used)

    constraintNum6(pSwitchesTopology, numberSlotsSwitches, usefulIntervalTime,
                   subSets, model, T_max_1, T_max_2, neighborsofEachSwitch,
                   pSwitchPorts, Z_Used, Y_Used)

    constraintNum9(pSwitchesTopology, subSets, model, T_max_1, T_max_2,
                   neighborsofEachSwitch, pSwitchPorts, Y_Used)

    constraintNum8(pSwitchesTopology, subSets, model, T_max_1, T_max_2,
                   neighborsofEachSwitch, pSwitchPorts, Y_Used)
    constraintNum10(pSwitchesTopology, subSets, model, T_max_1, T_max_2,
                    neighborsofEachSwitch, pSwitchPorts, numAllFrags, Y_Used)
    constraintNum11(pSwitchesTopology, subSets, model, workersTopology,
                    pSwitchPorts, Y_Used, T_max_1)

    from .constraints import constraintInArt
    constraintInArt(subSets, model, Z_Used, workersTopology, fragmentsofEachWorker)
