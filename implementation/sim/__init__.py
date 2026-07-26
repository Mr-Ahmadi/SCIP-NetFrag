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
    env_1c_5sw_3f,
    env_1c_5sw_2f,
    env_1c_3sw_4f,
    env_2c_10sw_3f,
    env_2c_10sw_3f_sparse,
    env_2c_10sw_6f,
    env_2c_10sw_8f,
    env_2c_10sw_uneven,
    env_2c_10sw_skew15,
    env_2c_10sw_skew1,
    env_3c_14sw_4f,
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

from .plot import (
    style,
    apply as apply_plot_style,
    new_fig,
    fmt_axis,
    grid as plot_grid,
    save_fig,
    legend as plot_legend,
    plot_grouped_bars,
    plot_errorbar,
    plot_single_bars,
)

from .block_io import BlockRun, block_json_default
