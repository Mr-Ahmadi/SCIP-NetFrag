"""
sim.plot — centralized Matplotlib style + reusable chart builders.

This module is the single source of truth for *every* visual aspect of
the project's plots:

* ``Style``                         — dataclass holding all style state
                                      (font sizes, palette, figsize, hatches,
                                       markers, etc.). Edit values there
                                      and every plot in the project updates.
* ``apply`` / ``new_fig`` / ...     — low-level figure helpers that
                                      consume ``Style``.
* ``plot_grouped_bars`` / ``plot_errorbar`` / ``plot_single_bars`` —
                                      chart-type builders shared by all
                                      experiment blocks in ``main.py``.

Usage::

    from sim.plot import style, apply, new_fig, save_fig, plot_grouped_bars
    apply()                                  # populates rcParams
    fig, ax = new_fig()
    plot_grouped_bars(...)                    # uses Style defaults
    save_fig(fig, "plots/foo.pdf")
"""
import os
from dataclasses import dataclass
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns


# =====================================================================
# Style — single source of truth for plot styling.
# =====================================================================
@dataclass
class Style:
    """Single source of truth for plot styling. Edit values here to
    re-theme every plot in the project."""

    # ---- Fonts ------------------------------------------------------
    font_size: int = 18              # base rcParams font.size
    label_size: int = 18             # axis labels
    tick_size: int = 14             # tick labels
    legend_size: int = 14
    title_size: int = 18

    # ---- Figure geometry -------------------------------------------
    figsize: tuple = (8, 6)
    bbox_inches: str = "tight"
    format: str = "pdf"
    dpi: int = 100

    # ---- Colors / palette ------------------------------------------
    # seaborn tab20c is the existing project palette; keep it.
    palette: str = "tab20c"
    # Heatmap colormaps — split by content type so callers don't pass
    # cmap names around as magic strings.
    cmap_fragments: str = "viridis_r"
    cmap_runtime: str = "magma_r"
    cmap_scatter_rho: str = "viridis"
    cmap_scatter_tau: str = "plasma"

    # ---- Grid / axes ------------------------------------------------
    grid_linestyle: str = "--"
    grid_linewidth: float = 0.5
    grid_axis: str = "y"            # 'y' for bar charts, 'both' for line plots
    axisbelow: bool = True
    scientific_powerlimits: tuple = (-3, 3)  # ScalarFormatter range

    # ---- Bar-chart hatches (cycle through for B/W friendliness) -----
    hatches: tuple = ("/", "o", "*", ".")

    # ---- Errorbar / line markers -----------------------------------
    markers: tuple = ("s--", "*--", "^--", "p--")
    marker_size: int = 10
    capsize: int = 5


style = Style()


# =====================================================================
# Low-level figure helpers (consume Style)
# =====================================================================
def apply(override: Optional[dict] = None) -> Style:
    """Apply the project style globally via rcParams and return the
    active :class:`Style`. Optional ``override`` lets a call site tweak
    one or two values for a single figure without mutating the global
    style, e.g. ``apply({"font_size": 22})``.
    """
    s = style
    if override:
        from dataclasses import replace
        s = replace(style, **override)
    plt.rcParams.update({
        "font.size": s.font_size,
        "axes.labelsize": s.label_size,
        "xtick.labelsize": s.tick_size,
        "ytick.labelsize": s.tick_size,
        "legend.fontsize": s.legend_size,
        "axes.titlesize": s.title_size,
        "figure.dpi": s.dpi,
        "savefig.dpi": s.dpi,
    })
    return s


def new_fig(figsize: Optional[tuple] = None):
    """Create a figure with the project's default size (or override)."""
    s = apply()
    fig, ax = plt.subplots(figsize=figsize or s.figsize)
    return fig, ax


def fmt_axis(ax, axis: str = "y"):
    """Attach the project's scientific ScalarFormatter."""
    formatter = ticker.ScalarFormatter(useMathText=True)
    formatter.set_powerlimits(style.scientific_powerlimits)
    if axis == "y":
        ax.yaxis.set_major_formatter(formatter)
    elif axis == "x":
        ax.xaxis.set_major_formatter(formatter)
    elif axis == "both":
        ax.yaxis.set_major_formatter(formatter)
        ax.xaxis.set_major_formatter(formatter)


def grid(ax, axis: Optional[str] = None):
    """Project-style grid."""
    s = style
    ax.grid(axis=axis or s.grid_axis, linestyle=s.grid_linestyle,
            linewidth=s.grid_linewidth)
    ax.set_axisbelow(s.axisbelow)


def save_fig(fig, filename: str, *, show: bool = True, bbox_inches=None):
    """Save with the project defaults and optionally show the figure."""
    s = style
    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    fig.savefig(filename, bbox_inches=bbox_inches or s.bbox_inches,
                format=s.format)
    if show:
        plt.show()


def legend(ax, **kwargs):
    """Project-style legend. Caller-supplied kwargs win (e.g. ``loc=...``)."""
    kwargs.setdefault("prop", {"size": style.legend_size})
    return ax.legend(**kwargs)


# =====================================================================
# Chart-type builders (consume Style + low-level helpers above)
# =====================================================================
def plot_grouped_bars(labels, data_list, label_list, ylabel, xlabel, filename,
                      color_indices=None, hatch_list=None, width=0.2,
                      figsize=None, fontsize=None, legend_ncol=None,
                      legend_bbox=None, legend_size=None, log_scale=False):
    """
    Draw a grouped bar chart with multiple series.

    Parameters
    ----------
    labels : list[str]       — x-axis labels
    data_list : list[list]   — one list of values per series
    label_list : list[str]   — legend label per series
    ylabel, xlabel : str
    filename : str           — output PDF path
    color_indices : list[int|float] — palette indices per series
    hatch_list : list[str]   — hatch pattern per series
    log_scale : bool         — log10-scale the y axis (use with
                               ylabel='runtime (s, $\\log_{10}$ scale)')
    """
    s = apply({"font_size": fontsize} if fontsize else {})
    cmap = sns.color_palette(s.palette)
    n = len(data_list)
    if color_indices is None:
        color_indices = list(range(n))
    if hatch_list is None:
        hatch_list = list(s.hatches[:n])

    x = np.arange(len(labels))
    fig, ax = new_fig(figsize)

    rects_all = []
    for i, (data, lbl) in enumerate(zip(data_list, label_list)):
        offset = (i - (n - 1) / 2) * width
        rects = ax.bar(x + offset, data, width, label=lbl,
                       color=cmap[color_indices[i]], hatch=hatch_list[i])
        rects_all.append(rects)

    for rect in rects_all:
        for r in rect:
            r.set_edgecolor('black')

    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    legend(ax, loc='upper left', bbox_to_anchor=legend_bbox,
           ncol=legend_ncol or n) if legend_bbox else legend(ax)
    fmt_axis(ax)
    grid(ax)
    if log_scale:
        ax.set_yscale('log')
    save_fig(fig, filename)


def plot_errorbar(labels, data_list, error_list, label_list, ylabel, xlabel,
                  filename, fmt_list=None, figsize=None, fontsize=None,
                  legend_bbox=None, legend_size=None):
    """
    Draw an error-bar line chart with multiple series.
    """
    s = apply({"font_size": fontsize} if fontsize else {})
    if fmt_list is None:
        fmt_list = list(s.markers[:len(data_list)])

    fig, ax = new_fig(figsize)

    for data, err, lbl, fmt in zip(data_list, error_list, label_list, fmt_list):
        ax.errorbar(labels, data, yerr=err, fmt=fmt,
                    markersize=s.marker_size, capsize=s.capsize, label=lbl)

    legend(ax, loc='upper center', bbox_to_anchor=legend_bbox,
           ncol=min(2, len(label_list))) if legend_bbox else legend(ax)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    fmt_axis(ax)
    grid(ax, axis="both")
    save_fig(fig, filename)


def plot_single_bars(labels, values, ylabel, xlabel, filename, color_index=1,
                     hatch='.', log_scale=False, figsize=None, fontsize=None,
                     std=None, fmt_errorbar=True):
    """
    Draw a single-series bar chart, optionally with std errorbars.

    Parameters
    ----------
    labels, values : list       — x-axis labels & bar heights.
    ylabel, xlabel : str
    color_index    : int        — palette index (see :class:`Style`).
    hatch          : str        — bar hatch pattern.
    log_scale      : bool        — log10-scale the y axis.
    std            : list|None  — per-bar std; if given AND fmt_errorbar,
                                  drawn as errorbar caps on the bars.
    fmt_errorbar   : bool        — toggle drawing of `std` (so callers can
                                  still record std without plotting it).
    """
    s = apply({"font_size": fontsize} if fontsize else {})
    cmap = sns.color_palette(s.palette)
    x = np.array(labels)
    y = np.array(values)

    fig, ax = new_fig(figsize)
    bars = ax.bar(x, y, color=cmap[color_index], edgecolor='black')
    for bar in bars:
        bar.set_hatch(hatch)

    if fmt_errorbar and std is not None:
        ax.errorbar(x, y, yerr=np.array(std), fmt='none', ecolor='black',
                    capsize=s.capsize)

    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.set_xticks(np.arange(len(x)))
    ax.set_xticklabels(x)

    grid(ax)
    fmt_axis(ax)
    if log_scale:
        ax.set_yscale('log')
    save_fig(fig, filename)


# =====================================================================
# Public re-export surface.
# =====================================================================
__all__ = [
    "Style", "style",
    "apply", "new_fig", "fmt_axis", "grid", "save_fig", "legend",
    "plot_grouped_bars", "plot_errorbar", "plot_single_bars",
]
