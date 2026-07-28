"""Common imports re-exported for all block modules."""
from sim import (
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
    defineModel,
    defineModel_ATP,
    defineModel_GRID,
    defineModel_ATP_GRID,
    defineModel_selectedSwitches,
    create_Fragments,
    preProcessMappingY,
    preProcessMappingZ,
    TimeoutError,
    _timeout_handler,
)
from sim.runner import (
    apply_constraints, apply_constraints_basic, apply_constraints_InArt,
)
from sim.solver import objective, solveProblem
from sim.plot import (
    style, apply as apply_plot_style, new_fig,
    fmt_axis, grid as plot_grid, save_fig,
    legend as plot_legend,
    plot_grouped_bars, plot_errorbar, plot_single_bars,
)
from sim.block_io import (
    BlockRun,
    block_json_default as _block_json_default,
    # Axis-label conventions
    YLEN_FRAG, YLEN_RUNTIME, YLEN_RUNTIME_LOG,
    XLEN_AGG, XLEN_TOPOLOGY, XLEN_DISTRIBUTION,
    XLEN_RHO, XLEN_TAU_START, XLEN_TIME_WINDOW, XLEN_FRAGS, XLEN_SLOTS,
    pct_labels, env_labels, ENV_DISPLAY_NAMES,
    # Model styles
    MODEL_LABELS, MODEL_COLORS, MODEL_HATCHES, MODEL_MARKERS,
    BASELINE_LABELS, BASELINE_COLORS, BASELINE_HATCHES, BASELINE_MARKERS,
    INART_LABELS, INART_COLORS, INART_HATCHES, INART_MARKERS,
    # Legend / geometry
    LEGEND_BBOX_BARS, LEGEND_BBOX_LINE, LEGEND_BBOX_SINGLE,
    LEGEND_SIZE, LEGEND_NCOL_4, LEGEND_NCOL_2, BAR_WIDTH,
)
from blocks._common import _unpack_env, _prepare_dict_list

# Common packages used by all blocks.
import time
import signal
import json
import os

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns

# Re-export all names (including underscore-prefixed) for wildcard import.
__all__ = [n for n in dir()
           if not n.startswith("__") and n != "__all__"]
