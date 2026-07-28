"""Centralized Matplotlib style and reusable chart builders."""
import os
from dataclasses import dataclass
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import seaborn as sns


@dataclass
class Style:
    """Single source of truth for plot styling."""

    font_size: int = 18
    label_size: int = 18
    tick_size: int = 14
    legend_size: int = 14
    title_size: int = 18

    figsize: tuple = (8, 6)
    bbox_inches: str = "tight"
    format: str = "pdf"
    dpi: int = 100

    palette: str = "tab20c"
    cmap_fragments: str = "viridis_r"
    cmap_runtime: str = "magma_r"
    cmap_scatter_rho: str = "viridis"
    cmap_scatter_tau: str = "plasma"

    grid_linestyle: str = "--"
    grid_linewidth: float = 0.5
    grid_axis: str = "y"
    axisbelow: bool = True
    scientific_powerlimits: tuple = (-3, 3)

    hatches: tuple = ("/", "o", "*", ".")
    markers: tuple = ("s--", "*--", "^--", "p--")
    marker_size: int = 10
    capsize: int = 5


style = Style()


def apply(override: Optional[dict] = None) -> Style:
    """Apply the project style globally via rcParams."""
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
    s = apply()
    fig, ax = plt.subplots(figsize=figsize or s.figsize)
    return fig, ax


def fmt_axis(ax, axis: str = "y"):
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
    s = style
    ax.grid(axis=axis or s.grid_axis, linestyle=s.grid_linestyle,
            linewidth=s.grid_linewidth)
    ax.set_axisbelow(s.axisbelow)


def save_fig(fig, filename: str, *, show: bool = True, bbox_inches=None):
    s = style
    fig.tight_layout()
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
    fig.savefig(filename, bbox_inches=bbox_inches or s.bbox_inches,
                format=s.format)
    if show:
        plt.show()


def legend(ax, **kwargs):
    kwargs.setdefault("prop", {"size": style.legend_size})
    return ax.legend(**kwargs)


def plot_grouped_bars(labels, data_list, label_list, ylabel, xlabel, filename,
                      color_indices=None, hatch_list=None, width=0.2,
                      figsize=None, fontsize=None, legend_ncol=None,
                      legend_bbox=None, legend_size=None, log_scale=False,
                      xtick_rotation=0, xtick_ha=None):
    """Draw a grouped bar chart with multiple series."""
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
    ha = xtick_ha or ('right' if xtick_rotation else 'center')
    ax.set_xticklabels(labels, rotation=xtick_rotation, ha=ha)
    legend(ax, loc='upper left', bbox_to_anchor=legend_bbox,
           ncol=legend_ncol or n) if legend_bbox else legend(ax)
    fmt_axis(ax)
    grid(ax)
    if log_scale:
        ax.set_yscale('log')
    save_fig(fig, filename)


def plot_errorbar(labels, data_list, error_list, label_list, ylabel, xlabel,
                  filename, fmt_list=None, figsize=None, fontsize=None,
                  legend_bbox=None, legend_size=None,
                  xtick_rotation=0, xtick_ha=None):
    """Draw an error-bar line chart with multiple series."""
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
    if xtick_rotation:
        plt.setp(ax.get_xticklabels(), rotation=xtick_rotation,
                 ha=xtick_ha or 'right')
    fmt_axis(ax)
    grid(ax, axis="both")
    save_fig(fig, filename)


def plot_single_bars(labels, values, ylabel, xlabel, filename, color_index=1,
                     hatch='.', log_scale=False, figsize=None, fontsize=None,
                     std=None, fmt_errorbar=True, xtick_rotation=0, xtick_ha=None):
    """Draw a single-series bar chart, optionally with std errorbars."""
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
    ha = xtick_ha or ('right' if xtick_rotation else 'center')
    ax.set_xticklabels(x, rotation=xtick_rotation, ha=ha)

    grid(ax)
    fmt_axis(ax)
    if log_scale:
        ax.set_yscale('log')
    save_fig(fig, filename)


__all__ = [
    "Style", "style",
    "apply", "new_fig", "fmt_axis", "grid", "save_fig", "legend",
    "plot_grouped_bars", "plot_errorbar", "plot_single_bars",
]
