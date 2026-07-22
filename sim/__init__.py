"""
sim — modular simulation package (FlexINA).

Backward-compatible: all public names are re-exported so that
``from sim import defineModel`` (or any other name) works.
"""

from .utils import (
    TimeoutError,
    _timeout_handler,
    _run_with_timeout,
    normalize_and_compare,
    get_subsets,
    subsets_of_subsets,
    create_Fragments,
)

from .helpers import (
    find_keys_by_value,
    has_common_element,
    remove_matching_pairs,
    preProcessMappingY,
    preProcessMappingZ,
)

from .environments import (
    env_1Cluster_Test,
    env_2Clusters,
    env_2Clusters_Zipf15,
    env_2Clusters_Zipf2,
    env_2Clusters_Percentages,
)

from .models import (
    defineModel,
    defineModel_ATP,
    defineModel_GRID,
    defineModel_ATP_GRID,
    defineModel_selectedSwitches,
    defineModel_InArt,
)

from .constraints import (
    constraintNum1,
    constraintNum1selectedSwitches,
    constraintMultiSlots,
    constraintNum2,
    constraintNum2selectedSwitches,
    constraintNum3,
    constraintNum3selectedSwitches,
    constraintNum3selectedSwitchesATP,
    constraintNum4,
    constraintNum4selectedSwitches,
    constraintNum4selectedSwitchesATP,
    constraintNum5,
    constraintNum5ATP,
    constraintNum6,
    constraintNum7,
    constraintNum7selectedSwitches,
    constraintNum8,
    constraintNum9,
    constraintNum10,
    constraintNum11,
    constraintInArt,
)

from .solver import objective, solveProblem

from .runner import apply_constraints, apply_constraints_basic, apply_constraints_InArt

from .plots import (
    plot_grouped_bars,
    plot_errorbar,
    plot_single_bars,
)
