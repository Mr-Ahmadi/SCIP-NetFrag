"""
Reusable plotting functions.
Replace the ~20 duplicated bar/errorbar chart blocks in the original.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns


def plot_grouped_bars(labels, data_list, label_list, ylabel, xlabel, filename,
                      color_indices=None, hatch_list=None, width=0.2,
                      figsize=(8, 6), fontsize=20, legend_ncol=None,
                      legend_bbox=None, legend_size=14):
    """
    Draw a grouped bar chart with multiple series.

    Parameters
    ----------
    labels : list[str]       — x-axis labels
    data_list : list[list]   — one list of values per series
    label_list : list[str]   — legend label per series
    ylabel, xlabel : str
    filename : str           — output PDF path
    color_indices : list[int|float] — tab20c palette indices per series
    hatch_list : list[str]   — hatch pattern per series
    """
    cmap = sns.color_palette("tab20c")
    n = len(data_list)
    if color_indices is None:
        color_indices = list(range(n))
    if hatch_list is None:
        hatch_list = ['/', 'o', '*', '.'][:n]

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=figsize)

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
    ax.legend()
    if legend_bbox:
        ncol = legend_ncol or n
        ax.legend(loc=1, bbox_to_anchor=legend_bbox, ncol=ncol,
                  prop={'size': legend_size})
    else:
        ax.legend(prop={'size': legend_size})

    formatter = ticker.ScalarFormatter(useMathText=True)
    formatter.set_powerlimits((-2, 2))
    ax.yaxis.set_major_formatter(formatter)

    plt.grid(axis='y', linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)
    plt.rcParams.update({'font.size': fontsize})
    plt.savefig(filename, bbox_inches="tight", format="pdf")
    plt.show()


def plot_errorbar(labels, data_list, error_list, label_list, ylabel, xlabel,
                  filename, fmt_list=None, figsize=(8, 6), fontsize=22,
                  legend_bbox=None, legend_size=16):
    """
    Draw an error-bar line chart with multiple series.

    Parameters
    ----------
    labels : list[str]       — x-axis labels
    data_list : list[list]   — mean values per series
    error_list : list[list]  — std values per series
    label_list : list[str]   — legend label per series
    """
    if fmt_list is None:
        fmt_list = ['s--', '*--', '^--', 'p--'][:len(data_list)]

    fig, ax = plt.subplots(figsize=figsize)

    for data, err, lbl, fmt in zip(data_list, error_list, label_list, fmt_list):
        plt.errorbar(labels, data, yerr=err, fmt=fmt, markersize=10,
                     capsize=5, label=lbl)

    if legend_bbox:
        ncol = min(2, len(label_list))
        plt.legend(loc='upper center', bbox_to_anchor=legend_bbox, ncol=ncol,
                   prop={'size': legend_size})
    else:
        plt.legend(prop={'size': legend_size})
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    formatter = ticker.ScalarFormatter(useMathText=True)
    formatter.set_powerlimits((-3, 3))
    ax.yaxis.set_major_formatter(formatter)
    fig.tight_layout()
    plt.grid(linestyle='--', linewidth=0.5)
    plt.rcParams.update({'font.size': fontsize})
    plt.savefig(filename, bbox_inches="tight", format="pdf")
    plt.show()


def plot_single_bars(labels, values, ylabel, xlabel, filename, color_index=1,
                     hatch='.', log_scale=False, figsize=(8, 6), fontsize=20):
    """
    Draw a single-series bar chart.
    """
    cmap = sns.color_palette("tab20c")
    x = np.array(labels)
    y = np.array(values)

    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.bar(x, y, color=cmap[color_index], edgecolor='black')
    for bar in bars:
        bar.set_hatch(hatch)

    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.set_xticks(np.arange(len(x)))
    ax.set_xticklabels(x)

    ax.grid(axis='y', linestyle='--', linewidth=0.5)
    formatter = ticker.ScalarFormatter(useMathText=True)
    formatter.set_powerlimits((-3, 3))
    ax.yaxis.set_major_formatter(formatter)
    fig.tight_layout()
    ax.set_axisbelow(True)
    if log_scale:
        ax.set_yscale('log')
    plt.rcParams.update({'font.size': fontsize})
    plt.savefig(filename, bbox_inches="tight", format="pdf")
    plt.show()
