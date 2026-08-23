"""Regenerate all experiment plots from saved JSON data.

Standalone script — does not modify any files under implementation/.
Reads ``implementation/plots/*_data.json`` and writes PDFs to ``plots/``.
Figure sizes/fonts are expressed in *printed* units for the IEEEtran
two-column paper; see :data:`HALF_W_IN` / :data:`FULL_W_IN`.

Usage::

    python replot.py              # regenerate all blocks
    python replot.py baseline     # regenerate one block
"""
import json
import os
import sys
from dataclasses import dataclass

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns

# ---------------------------------------------------------------------------
# Paper geometry — how wide a figure ends up on the printed page
# ---------------------------------------------------------------------------
# IEEEtran (conference): \columnwidth = 252.0pt. Result figures are included
# at width=0.5\linewidth (subfloat pairs) or width=\linewidth.

COLUMN_W_IN = 252.0 / 72.27      # 3.487 in — one IEEE column
HALF_W_IN = 0.5 * COLUMN_W_IN    # 1.743 in — subfloat pair (two per row)
FULL_W_IN = COLUMN_W_IN          # 3.487 in — single figure spanning a column


# ---------------------------------------------------------------------------
# Style — single source of truth for this script
# ---------------------------------------------------------------------------

@dataclass
class Style:
    # Figures are drawn ``scale``x larger than printed and shrunk by
    # \includegraphics; all sizes below are printed sizes.
    scale: float = 4.0

    # Font sizes as printed (pt), roughly the 8 pt of an IEEE caption.
    label_pt: float = 8.0
    tick_pt: float = 7.0
    legend_pt: float = 6.0
    title_pt: float = 8.0
    annot_pt: float = 6.0

    # Line weights and marker sizes as printed (pt).
    axes_lw: float = 0.5
    line_lw: float = 0.9
    grid_lw: float = 0.3
    edge_lw: float = 0.4
    marker_pt: float = 3.0
    scatter_pt: float = 3.0
    capsize_pt: float = 1.5
    tick_len_pt: float = 2.5
    pad_in: float = 0.02

    # One aspect ratio (width / height) for every chart, so a full-column
    # figure is a straight scale-up of a half-column one.
    aspect: float = 1.20

    bbox_inches = None               # keep the page size exactly = figsize
    fmt: str = "pdf"
    dpi: int = 300

    palette: str = "tab20c"
    cmap_fragments: str = "viridis_r"
    cmap_runtime: str = "magma_r"
    cmap_scatter_rho: str = "viridis"

    grid_linestyle: str = "--"
    grid_axis: str = "y"
    # Below 10^4 reads better spelled out.
    scientific_powerlimits: tuple = (-4, 4)

    markers: tuple = ("s--", "*--", "^--", "p--")

    def px(self, value):
        """Convert a printed size to the oversized figure's coordinates."""
        return value * self.scale


STYLE = Style()
OUT_DIR = os.path.join("implementation", "plots")
JSON_DIR = os.path.join("implementation", "plots")

# ---------------------------------------------------------------------------
# Axis-label constants — one canonical spelling per quantity
# ---------------------------------------------------------------------------

YLEN_FRAG = "# Fragments"
YLEN_RUNTIME = "Runtime (s)"
# Short wording: fits big_env_scaling's right-hand axis without overflow.
YLEN_RUNTIME_LOG = r"Runtime (s, $\log_{10}$)"

# Only wording that fits across a half-column figure at 8 pt.
XLEN_AGG = "Max. per switch agg."
XLEN_TOPOLOGY = "Topology"
XLEN_DISTRIBUTION = "Distribution of workers"
XLEN_RHO = r"$\rho$ (switch selection %)"
XLEN_TAU_START = r"$\tau_F$ (slots)"
XLEN_TIME_WINDOW = r"$\tau_S$ (% of $\tau_F$)"
XLEN_TAU_WINDOW = r"$\tau_F$ (time window)"
XLEN_SLOTS = "Slots per switch"
XLEN_REDUCTION = r"Packet reduction (1 $-$ pkts/pkts$_0$)"
XLEN_FRAGS = "Number of fragments"

# Route every axis label through this map so a quantity is labelled
# identically in every figure.
AXIS_LABELS = {
    "max. per switch aggregation": XLEN_AGG,
    "topology": XLEN_TOPOLOGY,
    "worker distribution": XLEN_DISTRIBUTION,
    "ρ (switch selection %)": XLEN_RHO,
    "rho (switch selection %)": XLEN_RHO,
    "τ_f start (slots)": XLEN_TAU_START,
    "tau_f start (slots)": XLEN_TAU_START,
    "τ_f (slots)": XLEN_TAU_START,
    "tau_f (slots)": XLEN_TAU_START,
    "time window (%)": XLEN_TIME_WINDOW,
    "τ_s (% of τ_f)": XLEN_TIME_WINDOW,
    "tau_s (% of tau_f)": XLEN_TIME_WINDOW,
    "τ_f (time window)": XLEN_TAU_WINDOW,
    "number of slots": XLEN_SLOTS,
    "slots per switch": XLEN_SLOTS,
    "number of fragments": XLEN_FRAGS,
    "# fragments": YLEN_FRAG,
    "runtime (s)": YLEN_RUNTIME,
    r"runtime (s, $\log_{10}$ scale)": YLEN_RUNTIME_LOG,
}

# ---------------------------------------------------------------------------
# Display-style constants (mirrors sim/block_io.py)
# ---------------------------------------------------------------------------

MODEL_LABELS = ["FixR-ToRS", "FixR-AS", "FlexR-ToRS", "FlexINA"]
MODEL_COLORS = [5, 9, 13, 1]
MODEL_MARKERS = ["s--", "*--", "^--", "p--"]

BASELINE_LABELS = ["optimal", "FlexINA"]
BASELINE_COLORS = [17, 1]
BASELINE_MARKERS = ["o--", "p--"]

INART_LABELS = ["InArt", "FlexINA"]
# Explicit light red: opposite FlexINA's light blue; entries may be palette
# indices or raw colours.
INART_COLORS = ["#f08080", 1]
INART_MARKERS = ["s--", "p--"]

# Fraction of a category slot covered by a bar group; bars split it evenly.
BAR_GROUP_WIDTH = 0.8

LEGEND_NCOL = 2

SCATTER_LEGEND_NCOL = 3

# One saturated tone per hue (stepping by four) plus a distinct marker per
# environment, so series stay apart in greyscale too. LINTHRESH_S guards the
# symlog branch for any prediction that still lands at 0; RUNTIME_EPS_S is
# the matching log-space floor for R^2.
LINTHRESH_S = 1e-3
RUNTIME_EPS_S = 1e-3

ENV_SCATTER_COLORS = (1, 5, 9, 13, 17, 2, 6, 10)
ENV_SCATTER_MARKERS = ("o", "s", "^", "D", "v", "P", "X", "<")

ENV_DISPLAY_NAMES = {
    "env_tree_7sw_3f": "Tree (7sw)",
    "env_1c_3sw_4f": "1 Cluster (3sw)",
    "env_1c_5sw_2f": "1 Cluster (5sw, 2f)",
    "env_1c_5sw_3f": "1 Cluster (5sw)",
    "env_1c_5sw_3f_2acc": "1 Cluster (5sw)",
    "env_1c_5sw_3f_m2": "1 Cluster (5sw, 2 slots)",
    "env_1c_5sw_3f_m3": "1 Cluster (5sw, 3 slots)",
    "env_2c_10sw_3f": "2 Clusters (10sw)",
    "env_2c_10sw_3f_sparse": "2 Clusters (Sparse)",
    "env_2c_10sw_6f": "2 Clusters (6f)",
    "env_2c_10sw_8f": "2 Clusters (8f)",
    "env_2c_10sw_skew1": "2 Clusters (Zipf 2)",
    "env_2c_10sw_skew15": "2 Clusters (Zipf 1.5)",
    "env_2c_10sw_uneven": "2 Clusters (Uneven)",
    "env_3c_14sw_4f": "3 Clusters (14sw)",
    "env_3c_15sw_4f": "3 Clusters (15sw)",
    "env_4c_20sw_4f": "4 Clusters (20sw)",
    "env_5c_25sw_4f": "5 Clusters (25sw)",
    "env_6c_30sw_4f": "6 Clusters (30sw)",
}

# Two-line tick abbreviations for environment axes (full names overlap at
# half-column width; spell the abbreviations out in the caption).
ENV_TICK_NAMES = {
    "Tree (7sw)": "Tree\n7sw",
    "1 Cluster (3sw)": "1C\n3sw",
    "1 Cluster (5sw, 2f)": "1C\n5sw,2f",
    "1 Cluster (5sw)": "1C\n5sw",
    "1 Cluster (5sw, 2 slots)": "1C\n5sw,m2",
    "1 Cluster (5sw, 3 slots)": "1C\n5sw,m3",
    "2 Clusters (10sw)": "2C\n10sw",
    "2 Clusters (Sparse)": "2C\nSp.",  # "Sparse" overlaps "Uneven" beside it
    "2 Clusters (6f)": "2C\n6f",
    "2 Clusters (8f)": "2C\n8f",
    "2 Clusters (Zipf 2)": "2C\nZ2",
    "2 Clusters (Zipf 1.5)": "2C\nZ1.5",
    "2 Clusters (Uneven)": "2C\nUneven",
    "3 Clusters (14sw)": "3C\n14sw",
    "3 Clusters (15sw)": "3C\n15sw",
    "4 Clusters (20sw)": "4C\n20sw",
    "5 Clusters (25sw)": "5C\n25sw",
    "6 Clusters (30sw)": "6C\n30sw",
}

# ---------------------------------------------------------------------------
# Plot primitives
# ---------------------------------------------------------------------------

def _apply():
    px = STYLE.px
    plt.rcParams.update({
        "figure.dpi": STYLE.dpi,
        "savefig.dpi": STYLE.dpi,
        "pdf.fonttype": 42,          # embed TrueType, never Type 3
        "ps.fonttype": 42,
        "font.family": "sans-serif",
        "mathtext.fontset": "dejavusans",

        "font.size": px(STYLE.tick_pt),
        "axes.labelsize": px(STYLE.label_pt),
        "axes.titlesize": px(STYLE.title_pt),
        "xtick.labelsize": px(STYLE.tick_pt),
        "ytick.labelsize": px(STYLE.tick_pt),
        "legend.fontsize": px(STYLE.legend_pt),

        "axes.linewidth": px(STYLE.axes_lw),
        "lines.linewidth": px(STYLE.line_lw),
        "lines.markersize": px(STYLE.marker_pt),
        "lines.markeredgewidth": px(STYLE.axes_lw),
        "patch.linewidth": px(STYLE.edge_lw),
        "grid.linewidth": px(STYLE.grid_lw),
        "grid.linestyle": STYLE.grid_linestyle,
        "axes.axisbelow": True,

        "xtick.major.width": px(STYLE.axes_lw),
        "ytick.major.width": px(STYLE.axes_lw),
        "xtick.major.size": px(STYLE.tick_len_pt),
        "ytick.major.size": px(STYLE.tick_len_pt),
        "xtick.major.pad": px(1.5),
        "ytick.major.pad": px(1.5),
        "axes.labelpad": px(2.0),
        "axes.titlepad": px(3.0),

        # Legend spacings are in font-size units, so they need no scaling.
        "legend.handlelength": 1.4,
        "legend.handleheight": 0.9,
        "legend.handletextpad": 0.4,
        "legend.columnspacing": 0.9,
        "legend.labelspacing": 0.3,
        "legend.borderpad": 0.3,
        "legend.borderaxespad": 0.1,
        "legend.framealpha": 1.0,
        "legend.edgecolor": "0.3",
        "legend.fancybox": False,

        "figure.constrained_layout.use": True,
        "figure.constrained_layout.h_pad": px(STYLE.pad_in),
        "figure.constrained_layout.w_pad": px(STYLE.pad_in),
    })


def _new_fig(wide=False, aspect=None, printed_h_in=None):
    """Create a figure whose printed width is one half- or full column."""
    _apply()
    w = (FULL_W_IN if wide else HALF_W_IN) * STYLE.scale
    if printed_h_in:
        h = printed_h_in * STYLE.scale
    else:
        h = w / (aspect or STYLE.aspect)
    return plt.subplots(figsize=(w, h), layout="constrained")


def _axis_label(text):
    """Map a label coming from JSON onto its canonical spelling."""
    if not text:
        return text
    return AXIS_LABELS.get(text.strip().lower(), text)


def _fmt_axis(ax, axis="y"):
    fmt = ticker.ScalarFormatter(useMathText=True)
    fmt.set_powerlimits(STYLE.scientific_powerlimits)
    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(fmt)
        ax.yaxis.offsetText.set_fontsize(STYLE.px(STYLE.tick_pt))
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(fmt)
        ax.xaxis.offsetText.set_fontsize(STYLE.px(STYLE.tick_pt))


def _grid(ax, axis=None):
    ax.grid(axis=axis or STYLE.grid_axis, linestyle=STYLE.grid_linestyle,
            linewidth=STYLE.px(STYLE.grid_lw))
    ax.set_axisbelow(True)


def _legend_above(fig, ax, n_entries, wide=False, handles=None, labels=None,
                  ncol=None):
    """Place the legend outside, above the axes — never over the data.

    Two entries per row by default; ``ncol`` for figures with many
    environment entries. Constrained layout reserves the space.
    """
    if handles is None:
        handles, labels = ax.get_legend_handles_labels()
    return fig.legend(handles, labels, loc="outside upper center",
                      ncol=min(n_entries, ncol or LEGEND_NCOL))


def _ticks(ax, positions, labels, rotation=0):
    ax.set_xticks(positions)
    ha = "right" if rotation else "center"
    ax.set_xticklabels(labels, rotation=rotation, ha=ha,
                       rotation_mode="anchor" if rotation else None)


def _save(fig, name):
    path = os.path.join(OUT_DIR, name)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    # No bbox_inches="tight": identical font settings must print at identical
    # sizes, which requires an identical page size.
    fig.savefig(path, bbox_inches=STYLE.bbox_inches, format=STYLE.fmt)
    plt.close(fig)
    print(f"  saved {path}")


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def _col(cmap, idx):
    """A series colour: palette index or an explicit colour string."""
    return idx if isinstance(idx, str) else cmap[idx]


def _grouped_bars(labels, data_list, label_list, ylabel, xlabel, fname,
                  color_indices=None, log_scale=False, xtick_rotation=0,
                  wide=False):
    cmap = sns.color_palette(STYLE.palette)
    n = len(data_list)
    w = BAR_GROUP_WIDTH / n
    ci = color_indices or list(range(n))

    x = np.arange(len(labels))
    fig, ax = _new_fig(wide=wide)

    for i, (data, lbl) in enumerate(zip(data_list, label_list)):
        off = (i - (n - 1) / 2) * w
        ax.bar(x + off, data, w, label=lbl, color=_col(cmap, ci[i]),
               edgecolor="black", linewidth=STYLE.px(STYLE.edge_lw))

    ax.set_ylabel(_axis_label(ylabel))
    ax.set_xlabel(_axis_label(xlabel))
    ax.set_xlim(-0.5, len(labels) - 0.5)
    _ticks(ax, x, labels, xtick_rotation)
    if log_scale:
        ax.set_yscale("log")
    else:
        _fmt_axis(ax)
        ax.margins(y=0.08)
    _grid(ax)
    _legend_above(fig, ax, n, wide=wide)
    _save(fig, fname)


def _grouped_bars_delta(labels, data_list, label_list, ylabel, xlabel, fname,
                        color_indices=None,
                        xtick_rotation=0, wide=False, delta_fmt="{:+.1f}%"):
    """Two-series grouped bars annotated with the relative change per group.

    The label sits above the taller bar of each pair so it never lands on
    ink; a tie prints as ``0.0%`` since "no difference" is a result here.
    """
    cmap = sns.color_palette(STYLE.palette)
    n = len(data_list)
    w = BAR_GROUP_WIDTH / n
    ci = color_indices or list(range(n))

    x = np.arange(len(labels))
    fig, ax = _new_fig(wide=wide)

    for i, (data, lbl) in enumerate(zip(data_list, label_list)):
        off = (i - (n - 1) / 2) * w
        ax.bar(x + off, data, w, label=lbl, color=_col(cmap, ci[i]),
               edgecolor="black", linewidth=STYLE.px(STYLE.edge_lw))

    base = np.asarray(data_list[0], dtype=float)
    other = np.asarray(data_list[-1], dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        delta = np.where(base > 0, 100.0 * (other - base) / base, np.nan)
    top = np.maximum(base, other)
    for xi, (d, t) in enumerate(zip(delta, top)):
        if not np.isfinite(d):
            continue
        # Snap float-noise ties to a plain, signless zero.
        text = "0.0%" if abs(d) < 0.05 else delta_fmt.format(d)
        ax.annotate(text, (xi, t),
                    textcoords="offset points",
                    xytext=(0, STYLE.px(1.6)), ha="center", va="bottom",
                    fontsize=STYLE.px(STYLE.annot_pt))

    ax.set_ylabel(_axis_label(ylabel))
    ax.set_xlabel(_axis_label(xlabel))
    ax.set_xlim(-0.5, len(labels) - 0.5)
    _ticks(ax, x, labels, xtick_rotation)
    _fmt_axis(ax)
    # Headroom for the annotation row on top of the usual 8% margin.
    ax.margins(y=0.18)
    _grid(ax)
    _legend_above(fig, ax, n, wide=wide)
    _save(fig, fname)


def _errorbar(labels, data_list, error_list, label_list, ylabel, xlabel, fname,
              fmt_list=None, color_indices=None, xtick_rotation=0, wide=False):
    cmap = sns.color_palette(STYLE.palette)
    n = len(data_list)
    fi = fmt_list or list(STYLE.markers[:n])
    ci = color_indices or list(range(n))

    x = np.arange(len(labels))
    fig, ax = _new_fig(wide=wide)
    for i, (d, e, lbl, f) in enumerate(
            zip(data_list, error_list, label_list, fi)):
        ax.errorbar(x, d, yerr=e, fmt=f, label=lbl,
                    color=_col(cmap, ci[i]),
                    markersize=STYLE.px(STYLE.marker_pt),
                    capsize=STYLE.px(STYLE.capsize_pt),
                    capthick=STYLE.px(STYLE.axes_lw))

    ax.set_xlabel(_axis_label(xlabel))
    ax.set_ylabel(_axis_label(ylabel))
    _ticks(ax, x, labels, xtick_rotation)
    ax.margins(x=0.10, y=0.08)
    _fmt_axis(ax)
    _grid(ax, axis="both")
    _legend_above(fig, ax, n, wide=wide)
    _save(fig, fname)


def _single_bars(labels, values, ylabel, xlabel, fname, color_index=1,
                 std=None, xtick_rotation=0, wide=False):
    cmap = sns.color_palette(STYLE.palette)
    x = np.arange(len(labels))
    y = np.asarray(values, dtype=float)

    fig, ax = _new_fig(wide=wide)
    ax.bar(x, y, BAR_GROUP_WIDTH, color=cmap[color_index], edgecolor="black",
           linewidth=STYLE.px(STYLE.edge_lw))

    if std is not None:
        ax.errorbar(x, y, yerr=np.asarray(std, dtype=float), fmt="none",
                    ecolor="black", capsize=STYLE.px(STYLE.capsize_pt),
                    capthick=STYLE.px(STYLE.axes_lw),
                    elinewidth=STYLE.px(STYLE.axes_lw))

    ax.set_ylabel(_axis_label(ylabel))
    ax.set_xlabel(_axis_label(xlabel))
    ax.set_xlim(-0.5, len(labels) - 0.5)
    ax.margins(y=0.08)
    _ticks(ax, x, labels, xtick_rotation)
    _grid(ax)
    _fmt_axis(ax)
    _save(fig, fname)


def _line_plot(labels, data_list, label_list, ylabel, xlabel, fname,
               fmt_list=None, color_indices=None, xtick_rotation=0,
               wide=False, log_scale=False):
    cmap = sns.color_palette(STYLE.palette)
    n = len(data_list)
    fi = fmt_list or list(STYLE.markers[:n])
    ci = color_indices or list(range(n))

    x = np.arange(len(labels))
    fig, ax = _new_fig(wide=wide)
    for i, (d, lbl, f) in enumerate(zip(data_list, label_list, fi)):
        ls = "--" if "--" in f else "-"
        marker = f.replace("--", "")
        ax.plot(x, d, ls=ls, marker=marker,
                markersize=STYLE.px(STYLE.marker_pt),
                label=lbl, color=_col(cmap, ci[i]))

    ax.set_xlabel(_axis_label(xlabel))
    ax.set_ylabel(_axis_label(ylabel))
    _ticks(ax, x, labels, xtick_rotation)
    if log_scale:
        ax.set_yscale("log")
    else:
        _fmt_axis(ax, axis="both")
    _grid(ax, axis="both")
    _legend_above(fig, ax, n, wide=wide)
    _save(fig, fname)


def _scaling_plot(labels, packets, runtimes, xlabel, fname,
                  pkt_color=1, rt_color=5):
    """Bars (left axis) + log line (right axis)."""
    cmap = sns.color_palette(STYLE.palette)
    x = np.arange(len(labels))
    fig, ax = _new_fig()

    bars = ax.bar(x, packets, BAR_GROUP_WIDTH, color=cmap[pkt_color],
                  edgecolor="black", linewidth=STYLE.px(STYLE.edge_lw))
    for rect, val in zip(bars, packets):
        ax.annotate(f"{int(val)}",
                    (rect.get_x() + rect.get_width() / 2,
                     rect.get_height()),
                    textcoords="offset points", xytext=(0, 4),
                    ha="center", fontsize=STYLE.px(STYLE.tick_pt))

    ax.set_xlabel(_axis_label(xlabel))
    ax.set_ylabel(YLEN_FRAG)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, max(packets) * 1.18)
    _fmt_axis(ax)
    _grid(ax)

    ax2 = ax.twinx()
    ax2.plot(x, runtimes, ls="dashed", marker="p",
             markersize=STYLE.px(STYLE.marker_pt),
             color=cmap[rt_color], label=YLEN_RUNTIME_LOG)
    ax2.set_yscale("log")
    ax2.set_ylabel(YLEN_RUNTIME_LOG)

    handles = [bars, ax2.get_lines()[0]]
    _legend_above(fig, ax, 2, handles=handles,
                  labels=[YLEN_FRAG, YLEN_RUNTIME_LOG])
    _save(fig, fname)


def _cell_text(val, is_runtime):
    """Annotation for one heatmap cell — plain decimals, never 3.6e+02."""
    if np.isnan(val):
        return "—"
    if not is_runtime:
        return f"{val:.0f}"
    if val >= 10:
        return f"{val:.0f}"
    if val >= 1:
        return f"{val:.1f}"
    return f"{val:.2f}"


def _heatmap(grid, row_labels, col_labels, title, fname, cbar_label):
    n_rows, n_cols = grid.shape
    # Keep cells close to square.
    axes_w = FULL_W_IN - 1.05
    printed_h = min(4.2, max(1.6, n_rows * (axes_w / n_cols) * 0.85 + 0.55))

    fig, ax = _new_fig(wide=True, printed_h_in=printed_h)
    is_runtime = cbar_label.lower().startswith("runtime")
    im = ax.imshow(grid, origin="lower", aspect="auto",
                   cmap=STYLE.cmap_runtime if is_runtime
                   else STYLE.cmap_fragments,
                   interpolation="nearest")
    ax.set_xticks(np.arange(len(col_labels)))
    ax.set_yticks(np.arange(len(row_labels)))
    ax.set_xticklabels(col_labels)
    ax.set_yticklabels(row_labels)
    ax.set_xlabel(XLEN_TAU_WINDOW)
    ax.set_ylabel(XLEN_RHO)
    ax.set_title(title)
    ax.tick_params(length=0)

    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
    cbar.set_label(_axis_label(cbar_label))
    cbar.ax.tick_params(labelsize=STYLE.px(STYLE.tick_pt),
                        width=STYLE.px(STYLE.axes_lw),
                        length=STYLE.px(STYLE.tick_len_pt))
    cbar.outline.set_linewidth(STYLE.px(STYLE.axes_lw))

    finite = grid[np.isfinite(grid)]
    vmax = float(finite.max()) if finite.size else 0.0
    for i in range(n_rows):
        for j in range(n_cols):
            val = grid[i, j]
            txt = _cell_text(val, is_runtime)
            color = "white" if vmax > 0 and val > 0.55 * vmax else "black"
            ax.text(j, i, txt, ha="center", va="center", color=color,
                    fontsize=STYLE.px(STYLE.annot_pt))
    _save(fig, fname)


def _bar_with_error(labels, means, stds, ylabel, xlabel, fname,
                    color_index=1, wide=False, xtick_rotation=0):
    """Single-series bar chart with error bars (same recipe as _single_bars,
    so it sits alongside the paper's other bar charts)."""
    cmap = sns.color_palette(STYLE.palette)
    x = np.arange(len(labels))
    means = np.asarray(means, dtype=float)
    stds = np.asarray(stds, dtype=float)

    fig, ax = _new_fig(wide=wide)
    ax.bar(x, means, BAR_GROUP_WIDTH, color=cmap[color_index],
           edgecolor="black", linewidth=STYLE.px(STYLE.edge_lw))
    ax.errorbar(x, means, yerr=stds, fmt="none", ecolor="black",
                capsize=STYLE.px(STYLE.capsize_pt),
                capthick=STYLE.px(STYLE.axes_lw),
                elinewidth=STYLE.px(STYLE.axes_lw))

    ax.set_xlabel(_axis_label(xlabel))
    ax.set_ylabel(_axis_label(ylabel))
    ax.set_xlim(-0.5, len(labels) - 0.5)
    # Headroom off the error bars, not the bars alone.
    ax.set_ylim(0, float((means + stds).max()) * 1.12)
    _ticks(ax, x, labels, xtick_rotation)
    _grid(ax)
    _fmt_axis(ax, axis="y")
    _save(fig, fname)


def _log_axis(ax, axis="both", limits=None):
    """Decade ticks with plain decimal labels — 0.01, not 10^-2 or 1.00.

    With ``axis="both"`` and shared ``limits`` (lo, hi), both axes get the
    same decades so an identity plot reads off one ruler. Never combine with
    _fmt_axis: its ScalarFormatter would clobber the log labels.
    """
    fmt = ticker.FuncFormatter(lambda v, _pos: f"{v:g}")
    names = ("x", "y") if axis == "both" else (axis,)
    # Pick the decades once from the shared limits and give both axes the
    # same ones, thinning to at most five labels.
    matched = None
    if axis == "both" and limits is not None:
        lo, hi = limits
        if lo > 0:
            decs = np.arange(np.ceil(np.log10(lo)), np.floor(np.log10(hi)) + 1)
            if len(decs):
                matched = 10.0 ** decs[::int(np.ceil(len(decs) / 5.0))]
    for name in names:
        a = getattr(ax, f"{name}axis")
        a.set_major_locator(ticker.FixedLocator(matched) if matched is not None
                            else ticker.LogLocator(base=10.0))
        a.set_major_formatter(fmt)
        a.set_minor_locator(ticker.LogLocator(base=10.0, subs=tuple(range(2, 10))))
        a.set_minor_formatter(ticker.NullFormatter())
    ax.tick_params(which="minor", length=STYLE.px(STYLE.tick_len_pt) * 0.5,
                   width=STYLE.px(STYLE.axes_lw))


def _symlog_axis(ax, linthresh, hi, axis="both"):
    """Decade ticks plus an explicit 0 for a symlog axis."""
    # Start a decade above linthresh: the first one overlaps the zero tick.
    decades = np.arange(np.ceil(np.log10(linthresh)) + 1,
                        np.floor(np.log10(hi)) + 1)
    step = 1 if len(decades) <= 4 else 2
    ticks = [0.0] + [10.0 ** d for d in decades[::step]]
    labels = ["0"] + [f"{t:g}" for t in ticks[1:]]
    for name in (("x", "y") if axis == "both" else (axis,)):
        a = getattr(ax, f"{name}axis")
        a.set_major_locator(ticker.FixedLocator(ticks))
        a.set_major_formatter(ticker.FixedFormatter(labels))
        a.set_minor_locator(ticker.NullLocator())


def _identity_limits(values, log_scale, pad=0.06):
    """Shared lower/upper bound for both axes of a predicted-vs-observed plot,
    so y = x runs at 45 degrees and distance from it reads as the error."""
    lo, hi = float(min(values)), float(max(values))
    if log_scale:
        span = np.log10(hi) - np.log10(lo)
        f = 10 ** ((span * pad) or 0.1)   # 0.1 guards a single-value axis
        return lo / f, hi * f
    span = (hi - lo) or abs(hi) or 1.0
    return lo - span * pad, hi + span * pad


def _scatter_identity(xs, ys, envs, xlabel, ylabel, fname, stats=None,
                      log_scale=False, wide=False, alpha=0.85,
                      point_scale=1.0, integer_ticks=False):
    """Predicted vs observed scatter against the y = x line.

    One colour *and* one marker per environment (greyscale printing).
    ``stats`` is a pre-formatted text block parked in the upper-left corner.
    """
    cmap = sns.color_palette(STYLE.palette)
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    envs = np.asarray(envs)
    unique_envs = sorted(set(envs.tolist()))

    # Square axes: on a rectangular box the identity line is not at 45
    # degrees, and readers judge these plots by distance from that line.
    fig, ax = _new_fig(wide=wide, aspect=0.95)

    vals = np.concatenate([xs, ys])
    linthresh = LINTHRESH_S if log_scale and (vals <= 0).any() else None
    if linthresh:
        lo, hi = 0.0, float(vals.max()) * 1.4
    else:
        lo, hi = _identity_limits(vals, log_scale)
    # "$y=x$" is the only identity-line label that fits a half-column legend.
    ax.plot([lo, hi], [lo, hi], ls="--", color="0.45",
            linewidth=STYLE.px(STYLE.line_lw), zorder=1, label="$y=x$")

    for i, e in enumerate(unique_envs):
        sel = envs == e
        ax.scatter(xs[sel], ys[sel],
                   s=(STYLE.px(STYLE.scatter_pt) ** 2) * point_scale,
                   alpha=alpha, zorder=3,
                   color=cmap[ENV_SCATTER_COLORS[i % len(ENV_SCATTER_COLORS)]],
                   marker=ENV_SCATTER_MARKERS[i % len(ENV_SCATTER_MARKERS)],
                   edgecolor="black", linewidth=STYLE.px(STYLE.edge_lw * 0.6),
                   label=e)

    if linthresh:
        ax.set_xscale("symlog", linthresh=linthresh, linscale=0.35)
        ax.set_yscale("symlog", linthresh=linthresh, linscale=0.35)
        _symlog_axis(ax, linthresh, hi, axis="both")
    elif log_scale:
        ax.set_xscale("log")
        ax.set_yscale("log")
        _log_axis(ax, axis="both", limits=(lo, hi))
    else:
        _fmt_axis(ax, axis="both")
        if integer_ticks:
            # Fragments are a count; decided by the caller rather than
            # sniffed from the data.
            ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=5))
            ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=5))
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_box_aspect(1)

    if stats:
        ax.text(0.035, 0.965, stats, transform=ax.transAxes,
                va="top", ha="left", zorder=4,
                fontsize=STYLE.px(STYLE.annot_pt), linespacing=1.35,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.55",
                          lw=STYLE.px(STYLE.axes_lw), alpha=0.92))

    ax.set_xlabel(_axis_label(xlabel))
    ax.set_ylabel(_axis_label(ylabel))
    _grid(ax, axis="both")
    # The identity line rides along with the environments, so the legend is
    # one entry longer than the environment count.
    handles, labels = ax.get_legend_handles_labels()
    order = list(range(1, len(handles))) + [0]
    _legend_above(fig, ax, len(handles), wide=wide,
                  handles=[handles[i] for i in order],
                  labels=[labels[i] for i in order],
                  ncol=SCATTER_LEGEND_NCOL)
    _save(fig, fname)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _load(block):
    path = os.path.join(JSON_DIR, f"{block}_data.json")
    with open(path) as f:
        return json.load(f)


def _series_by_model(summary):
    return {s["model"]: s for s in summary["series"]}


def _env_display(name):
    return ENV_DISPLAY_NAMES.get(name, name)


def _env_ticks(labels):
    return [ENV_TICK_NAMES.get(l, l) for l in labels]


def _env_legend(labels):
    """One-line abbreviations for a legend — "2C 10sw", not "2 Clusters (10sw)"."""
    return [ENV_TICK_NAMES.get(l, l).replace("\n", " ") for l in labels]


# ---------------------------------------------------------------------------
# Per-block replot functions
# ---------------------------------------------------------------------------

def replot_baseline():
    data = _load("baseline")
    sm = data["summary"]
    labels = sm["labels"]
    ax_x = sm["axis"]["x"]
    sbm = _series_by_model(sm)

    pk = [sbm[m]["packets_mean"] for m in BASELINE_LABELS]
    _grouped_bars(labels, pk, BASELINE_LABELS, YLEN_FRAG, ax_x,
                  "baseline_fragments.pdf",
                  color_indices=BASELINE_COLORS)
    _grouped_bars(labels, pk, BASELINE_LABELS, YLEN_FRAG, ax_x,
                  "basic_fragments_vs_aggregation.pdf",
                  color_indices=BASELINE_COLORS)

    re_pk = [sbm[m]["packets_std"] for m in BASELINE_LABELS]
    _errorbar(labels, pk, re_pk, BASELINE_LABELS, YLEN_FRAG, ax_x,
              "basic_fragments_vs_aggregation_errorbar.pdf",
              fmt_list=BASELINE_MARKERS, color_indices=BASELINE_COLORS)

    rt = [sbm[m]["runtime_mean"] for m in BASELINE_LABELS]
    re = [sbm[m]["runtime_std"] for m in BASELINE_LABELS]
    _errorbar(labels, rt, re, BASELINE_LABELS, YLEN_RUNTIME, ax_x,
              "baseline_runtime_errorbar.pdf",
              fmt_list=BASELINE_MARKERS, color_indices=BASELINE_COLORS)
    _errorbar(labels, rt, re, BASELINE_LABELS, YLEN_RUNTIME, ax_x,
              "basic_runtime_vs_aggregation_errorbar.pdf",
              fmt_list=BASELINE_MARKERS, color_indices=BASELINE_COLORS)

    _grouped_bars(labels, rt, BASELINE_LABELS, YLEN_RUNTIME, ax_x,
                  "baseline_runtime.pdf",
                  color_indices=BASELINE_COLORS)
    _grouped_bars(labels, rt, BASELINE_LABELS, YLEN_RUNTIME, ax_x,
                  "basic_runtime_vs_aggregation_bars.pdf",
                  color_indices=BASELINE_COLORS)

    _line_plot(labels, rt, BASELINE_LABELS, YLEN_RUNTIME, ax_x,
               "basic_runtime_vs_aggregation.pdf",
               fmt_list=BASELINE_MARKERS, color_indices=BASELINE_COLORS)


def replot_models():
    data = _load("models")
    sm = data["summary"]
    labels = sm["labels"]
    ax_x = sm["axis"]["x"]
    sbm = _series_by_model(sm)

    pk = [sbm[m]["packets_mean"] for m in MODEL_LABELS]
    _grouped_bars(labels, pk, MODEL_LABELS, YLEN_FRAG, ax_x,
                  "models_fragments.pdf",
                  color_indices=MODEL_COLORS)

    rt = [sbm[m]["runtime_mean"] for m in MODEL_LABELS]
    re = [sbm[m]["runtime_std"] for m in MODEL_LABELS]
    _errorbar(labels, rt, re, MODEL_LABELS, YLEN_RUNTIME, ax_x,
              "models_runtime_errorbar.pdf",
              fmt_list=MODEL_MARKERS, color_indices=MODEL_COLORS)

    _grouped_bars(labels, pk, MODEL_LABELS, YLEN_FRAG, XLEN_FRAGS,
                  "models_fragments_vs_slots.pdf",
                  color_indices=MODEL_COLORS)

    _errorbar(labels, rt, re, MODEL_LABELS, YLEN_RUNTIME, XLEN_FRAGS,
              "models_runtime_vs_slots_errorbar.pdf",
              fmt_list=MODEL_MARKERS, color_indices=MODEL_COLORS)

    tree = data.get("config", {}).get("scalability_tree", {})
    frag = data.get("config", {}).get("scalability_fragments", {})
    if tree:
        _single_bars(tree["labels"], tree["runtime_s"], YLEN_RUNTIME,
                     XLEN_FRAGS, "models_scalability_tree.pdf",
                     color_index=1)
    if frag:
        _single_bars(frag["labels"], frag["runtime_s"], YLEN_RUNTIME,
                     XLEN_FRAGS, "models_scalability_fragments.pdf",
                     color_index=1)


def replot_start_time():
    data = _load("start_time")
    sm = data["summary"]
    labels = sm["labels"]
    ax_x = sm["axis"]["x"]
    sbm = _series_by_model(sm)

    pk = [sbm[m]["packets_mean"] for m in MODEL_LABELS]
    _grouped_bars(labels, pk, MODEL_LABELS, YLEN_FRAG, ax_x,
                  "starttime_fragments.pdf",
                  color_indices=MODEL_COLORS)

    rt = [sbm[m]["runtime_mean"] for m in MODEL_LABELS]
    re = [sbm[m]["runtime_std"] for m in MODEL_LABELS]
    _errorbar(labels, rt, re, MODEL_LABELS, YLEN_RUNTIME, ax_x,
              "starttime_runtime.pdf",
              fmt_list=MODEL_MARKERS, color_indices=MODEL_COLORS)


def replot_time_window():
    data = _load("time_window")
    sm = data["summary"]
    labels = sm["labels"]
    ax_x = sm["axis"]["x"]
    sbm = _series_by_model(sm)

    pk = [sbm[m]["packets_mean"] for m in MODEL_LABELS]
    _grouped_bars(labels, pk, MODEL_LABELS, YLEN_FRAG, ax_x,
                  "timewindow_fragments.pdf",
                  color_indices=MODEL_COLORS)

    rt = [sbm[m]["runtime_mean"] for m in MODEL_LABELS]
    re = [sbm[m]["runtime_std"] for m in MODEL_LABELS]
    _errorbar(labels, rt, re, MODEL_LABELS, YLEN_RUNTIME, ax_x,
              "timewindow_runtime.pdf",
              fmt_list=MODEL_MARKERS, color_indices=MODEL_COLORS)


def replot_worker_dist():
    _replot_four_model_block("worker_dist", "distribution")


def _replot_four_model_block(block, prefix):
    """Fragments + runtime for a 4-model block on a small categorical axis
    (worker_dist / switch_memory / topologies share this shape)."""
    data = _load(block)
    sm = data["summary"]
    # Environment-valued x axes (topologies) get two-line abbreviations; for
    # plain categorical axes _env_ticks is the identity.
    labels = _env_ticks(sm["labels"])
    ax_x = sm["axis"]["x"]
    sbm = _series_by_model(sm)

    pk = [sbm[m]["packets_mean"] for m in MODEL_LABELS]
    _grouped_bars(labels, pk, MODEL_LABELS, YLEN_FRAG, ax_x,
                  f"{prefix}_fragments.pdf",
                  color_indices=MODEL_COLORS)

    rt = [sbm[m]["runtime_mean"] for m in MODEL_LABELS]
    _grouped_bars(labels, rt, MODEL_LABELS, YLEN_RUNTIME_LOG, ax_x,
                  f"{prefix}_runtime.pdf",
                  color_indices=MODEL_COLORS,
                  log_scale=True)

    re = [sbm[m]["runtime_std"] for m in MODEL_LABELS]
    _errorbar(labels, rt, re, MODEL_LABELS, YLEN_RUNTIME, ax_x,
              f"{prefix}_runtime_errorbar.pdf",
              fmt_list=MODEL_MARKERS, color_indices=MODEL_COLORS)


def replot_switch_memory():
    _replot_four_model_block("switch_memory", "switch_memory")


def replot_topologies():
    _replot_four_model_block("topologies", "topologies")


def _replot_pct(block, prefix):
    data = _load(block)
    sm = data["summary"]
    labels = sm["labels"]
    ax_x = sm["axis"]["x"]
    s = _series_by_model(sm)[MODEL_LABELS[-1]]

    _single_bars(labels, s["packets_mean"], YLEN_FRAG, ax_x,
                 f"{prefix}_fragments.pdf",
                 color_index=1, std=s["packets_std"])

    _single_bars(labels, s["runtime_mean"], YLEN_RUNTIME, ax_x,
                 f"{prefix}_runtime.pdf",
                 color_index=1, std=s["runtime_std"])


def replot_pct_1cluster():
    _replot_pct("pct_1cluster", "percentage_1cluster")


def replot_pct_2cluster():
    _replot_pct("pct_2cluster", "percentage_2cluster")


def replot_inart():
    data = _load("inart")
    sm = data["summary"]
    labels = _env_ticks(sm["labels"])
    ax_x = sm["axis"]["x"]
    sbm = _series_by_model(sm)

    pk = [sbm[m]["packets_mean"] for m in INART_LABELS]
    # Print the per-topology reduction on the bars rather than leave it to be
    # read off two bars a few points apart.
    _grouped_bars_delta(labels, pk, INART_LABELS, YLEN_FRAG, ax_x,
                        "inart_fragments.pdf",
                         color_indices=INART_COLORS)

    rt = [sbm[m]["runtime_mean"] for m in INART_LABELS]
    re = [sbm[m]["runtime_std"] for m in INART_LABELS]
    _errorbar(labels, rt, re, INART_LABELS, YLEN_RUNTIME, ax_x,
              "inart_runtime_errorbar.pdf",
              fmt_list=INART_MARKERS, color_indices=INART_COLORS)

    _line_plot(labels, rt, INART_LABELS, YLEN_RUNTIME, ax_x,
               "inart_runtime.pdf",
               fmt_list=INART_MARKERS, color_indices=INART_COLORS,
               xtick_rotation=20)


def replot_big_env():
    data = _load("big_env")
    sm = data["summary"]
    labels = _env_ticks(sm["labels"])
    ax_x = sm["axis"]["x"]
    s = sm["series"][0]

    _single_bars(labels, s["packets_mean"], YLEN_FRAG, ax_x,
                 "big_env_fragments.pdf",
                 color_index=1,
                 std=s.get("packets_std"))

    # Match the styling of the other single-series bar figures; the runtime
    # line keeps its own colour on the twin-axis scaling plot below.
    _single_bars(labels, s["runtime_mean"], YLEN_RUNTIME, ax_x,
                 "big_env_runtime.pdf",
                 color_index=1,
                 std=s.get("runtime_std"))

    _scaling_plot(labels, s["packets_mean"], s["runtime_mean"], ax_x,
                  "big_env_scaling.pdf",
                  pkt_color=1, rt_color=5)


def replot_param_sweep():
    data = _load("param_sweep")
    rho_labels = data.get("rho_labels", [])
    tau_labels = data.get("tau_labels", [])
    grids = data.get("grids", {})

    for env_name, g in grids.items():
        pkt = np.array(g["packets"], dtype=float)
        rt = np.array(g["runtime"], dtype=float)
        dname = _env_display(env_name)

        # Dash, not nesting: the env names already carry parentheses.
        _heatmap(pkt, rho_labels, tau_labels,
                 f"# Fragments — {dname}",
                 f"param_sweep_fragments_heatmap_{env_name}.pdf",
                 YLEN_FRAG)
        _heatmap(rt, rho_labels, tau_labels,
                 f"Runtime — {dname}",
                 f"param_sweep_runtime_heatmap_{env_name}.pdf",
                 YLEN_RUNTIME)

    tradeoff_rows = data.get("tradeoff_rows", [])
    by_env = {}
    for r in tradeoff_rows:
        by_env.setdefault(r["env"], []).append(r)

    for env_name, rows in by_env.items():
        ok = [r for r in rows
              if r.get("reduction") is not None
              and np.isfinite(r["reduction"])
              and r.get("runtime") is not None]
        if not ok:
            continue
        xs = [r["reduction"] for r in ok]
        ys = [r["runtime"] for r in ok]
        rhos = [r["rho"] for r in ok]

        fig, ax = _new_fig(wide=True)
        sc = ax.scatter(xs, ys, c=rhos, cmap=STYLE.cmap_scatter_rho,
                        s=STYLE.px(STYLE.scatter_pt) ** 2, edgecolor="black",
                        linewidth=STYLE.px(STYLE.axes_lw))

        pts = sorted(zip(xs, ys), key=lambda p: (-p[0], p[1]))
        pareto, best_rt = [], float("inf")
        for px_, py_ in pts:
            if py_ < best_rt:
                pareto.append((px_, py_))
                best_rt = py_
        if pareto:
            fx, fy = zip(*pareto)
            ax.plot(fx, fy, "r--", lw=STYLE.px(STYLE.line_lw),
                    label="Pareto front")

        cbar = fig.colorbar(sc, ax=ax, fraction=0.045, pad=0.02)
        cbar.set_label(r"$\rho$")
        cbar.ax.tick_params(labelsize=STYLE.px(STYLE.tick_pt),
                            width=STYLE.px(STYLE.axes_lw),
                            length=STYLE.px(STYLE.tick_len_pt))
        cbar.outline.set_linewidth(STYLE.px(STYLE.axes_lw))
        ax.set_xlabel(XLEN_REDUCTION)
        ax.set_ylabel(YLEN_RUNTIME)
        ax.set_title(f"Trade-off — {_env_display(env_name)}")
        _grid(ax, axis="both")
        _fmt_axis(ax, axis="both")
        if pareto:
            # Title present, so the single-entry legend goes in the (empty)
            # upper-left corner instead of above it.
            ax.legend(loc="upper left")
        _save(fig, f"param_sweep_tradeoff_{env_name}.pdf")


def _regression_rows(data, kind):
    """Held-out predicted/observed pairs, or None on a pre-fix block JSON.

    ``regression_rows`` is stored columnwise by blocks/rho_tau/block.py;
    unsupervised rows carry None (see ``_scored_masks`` there).
    """
    rr = data.get("regression_rows")
    if not rr:
        return None
    pk = "pred_runtime" if kind == "runtime" else "pred_packets"
    ok = "runtime" if kind == "runtime" else "packets"
    keep = [i for i, (p, o, s) in enumerate(zip(rr[pk], rr[ok], rr["split"]))
            if p is not None and o is not None and s == "val"]
    if len(keep) < 2:
        return None
    return (np.array([rr[pk][i] for i in keep], dtype=float),
            np.array([rr[ok][i] for i in keep], dtype=float),
            _env_legend([_env_display(rr["env"][i]) for i in keep]))


def _fit_stats(pred, obs, log_scale, n_label=None, held_out=False):
    """R^2 and Spearman over the points actually drawn, as a text block."""
    pred, obs = np.asarray(pred, float), np.asarray(obs, float)
    # Score runtime in the head's own target space: log(y + 1 ms), not log1p.
    tx, ty = ((np.log(pred + RUNTIME_EPS_S), np.log(obs + RUNTIME_EPS_S))
              if log_scale else (pred, obs))
    r2 = 1 - np.sum((tx - ty) ** 2) / np.sum((ty - ty.mean()) ** 2)
    rx = np.argsort(np.argsort(tx)).astype(float)
    ry = np.argsort(np.argsort(ty)).astype(float)
    rho = float(np.corrcoef(rx, ry)[0, 1])
    # Label the set the numbers cover (picks vs held-out split).
    return (f"{'held-out' if held_out else 'picks'}, "
            f"$n$={n_label or len(pred)}\n"
            f"$R^2${'(log)' if log_scale else ''}={r2:.2f}\n"
            f"Spearman={rho:.2f}")


def _held_out_stats(held_out, kind):
    """Same text block, but from the held-out split in the eval JSON."""
    if not held_out or kind not in held_out:
        return None
    h = held_out[kind]
    log = kind == "runtime"
    # r2_log is the current key; older eval reports wrote r2_log1p.
    r2 = float((h.get("r2_log", h.get("r2_log1p"))) if log else h["r2"])
    return (f"held-out, $n$={int(h.get('n', 0))}\n"
            f"$R^2${'(log)' if log else ''}={r2:.2f}\n"
            f"Spearman={float(h.get('spearman', float('nan'))):.2f}")


def replot_rho_tau_model():
    data_path = os.path.join(JSON_DIR, "rho_tau_model_data.json")
    eval_path = os.path.join(JSON_DIR, "rho_tau_model_eval.json")
    if not os.path.exists(data_path):
        return
    with open(data_path) as f:
        data = json.load(f)
    qualities = data.get("per_state_quality", [])
    if not qualities:
        return

    # Load held-out eval metrics if available.
    held_out = {}
    if os.path.exists(eval_path):
        with open(eval_path) as f:
            held_out = json.load(f).get("regression_val", {})

    # --- regret by env ---
    envs = sorted({q["env"] for q in qualities})
    means, stds = [], []
    for e in envs:
        regrets = [q["regret"] for q in qualities
                   if q["env"] == e and q["regret"] is not None]
        means.append(float(np.mean(regrets)) if regrets else 0.0)
        stds.append(float(np.std(regrets)) if regrets else 0.0)
    # Two-line abbreviations, as on every other environment axis.
    _bar_with_error(_env_ticks([_env_display(e) for e in envs]), means, stds,
                    "Regret (s)", XLEN_TOPOLOGY,
                    "rho_tau_model_regret_by_env.pdf",
                    color_index=1)

    def _pts(pred_key, obs_key):
        rows = [q for q in qualities
                if q.get(pred_key) is not None and q.get(obs_key) is not None]
        return (np.array([q[pred_key] for q in rows], dtype=float),
                np.array([q[obs_key] for q in rows], dtype=float),
                _env_legend([_env_display(q["env"]) for q in rows]))

    # --- pred vs actual at the selector's pick ---
    # The stats box quotes the held-out split; the figure shows where the
    # picks' errors land.
    xs, ys, env_arr = _pts("pred_runtime", "chosen_runtime")
    if len(xs):
        _scatter_identity(
            xs, ys, env_arr, "Predicted runtime (s)", "Observed runtime (s)",
            "rho_tau_model_pred_vs_actual.pdf",
            stats=_held_out_stats(held_out, "runtime")
            or _fit_stats(xs, ys, True),
            log_scale=True)

    xs, ys, env_arr = _pts("pred_packets", "chosen_packets")
    if len(xs):
        _scatter_identity(
            xs, ys, env_arr, "Predicted fragments", "Observed fragments",
            "rho_tau_model_pred_vs_actual_packets.pdf",
            stats=_held_out_stats(held_out, "packets")
            or _fit_stats(xs, ys, False),
            log_scale=False, integer_ticks=True)

    # --- regression accuracy ---
    # Every held-out scored row, not the handful the selector picked (their
    # collapsed spread makes R^2 over picks meaningless).
    for kind, log, xlab, ylab, fname in (
            ("runtime", True, "Predicted runtime (s)", "Observed runtime (s)",
             "rho_tau_model_regression_accuracy.pdf"),
            ("packets", False, "Predicted fragments", "Observed fragments",
             "rho_tau_model_regression_accuracy_packets.pdf")):
        rows = _regression_rows(data, kind)
        if rows is None:
            # Pre-regression_rows JSON: fall back to the selector's picks.
            pk = "pred_runtime" if kind == "runtime" else "pred_packets"
            ck = "chosen_runtime" if kind == "runtime" else "chosen_packets"
            xs, ys, env_arr = _pts(pk, ck)
            if not len(xs):
                continue
            stats = _fit_stats(xs, ys, log)
        else:
            xs, ys, env_arr = rows
            stats = _fit_stats(xs, ys, log, held_out=True)
        _scatter_identity(
            xs, ys, env_arr, xlab, ylab, fname, stats=stats, log_scale=log,
            alpha=0.55, point_scale=0.45, integer_ticks=(kind == "packets"))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BLOCKS = {
    "baseline": replot_baseline,
    "start_time": replot_start_time,
    "time_window": replot_time_window,
    "worker_dist": replot_worker_dist,
    "switch_memory": replot_switch_memory,
    "topologies": replot_topologies,
    "pct_1cluster": replot_pct_1cluster,
    "pct_2cluster": replot_pct_2cluster,
    "inart": replot_inart,
    "big_env": replot_big_env,
    "param_sweep": replot_param_sweep,
    "rho_tau_model": replot_rho_tau_model,
    "models": replot_models,
}

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(OUT_DIR, exist_ok=True)

    requested = sys.argv[1:] or list(BLOCKS)
    unknown = [b for b in requested if b not in BLOCKS]
    if unknown:
        print(f"Unknown block(s): {', '.join(unknown)}")
        print(f"Available: {', '.join(BLOCKS)}")
        sys.exit(1)

    for block in requested:
        json_path = os.path.join(JSON_DIR, f"{block}_data.json")
        if not os.path.exists(json_path):
            print(f"  skipped {block} ({json_path} not found)")
            continue
        print(f"[{block}]")
        try:
            BLOCKS[block]()
        except Exception as exc:
            print(f"  ERROR: {exc}")

    print(f"\nDone — plots written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
