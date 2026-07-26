"""
Block run recorder + shared plot/JSON conventions.

Every experiment block in ``main.py`` produces a set of PDF plots and a
single JSON file that captures *everything* needed to regenerate the
plots offline (per-iteration observations, summary statistics, axis
labels, and general run metadata such as total block wall time and per-
solve construction + solve times).

Conventions enforced here so plots across blocks stay consistent
(edit in ONE place to change all blocks):

* Axis labels      — ``YLEN_FRAG``, ``YLEN_RUNTIME``, ``XLEN_*`` constants.
* Model legend labels & colors & hatches — ``MODEL_STYLE`` (4-model stack),
  ``BASELINE_STYLE`` (optimal vs FlexINA), ``INART_STYLE`` (InArt vs FlexINA).
* Observation row schema — one dict per ``(model, env, axis_value, ittr)``
  spaced / per-cell observation, with both raw ``packets``/``runtime`` and
  timing metrics (``construction_time_s``, ``solve_time_s``).
"""
from __future__ import annotations

import json
import os
import platform
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np

# ---------------------------------------------------------------------
# Axis-label conventions (single source of truth)
# ---------------------------------------------------------------------
YLEN_FRAG = "# fragments"
YLEN_RUNTIME = "runtime (s)"
YLEN_RUNTIME_LOG = "runtime (s, $\\log_{10}$ scale)"

XLEN_AGG = "max. per switch aggregation"
XLEN_TOPOLOGY = "topology"
XLEN_DISTRIBUTION = "worker distribution"
XLEN_RHO = "ρ (switch selection %)"
XLEN_TAU_START = "τ_F start (slots)"
XLEN_TIME_WINDOW = "time window (%)"
XLEN_FRAGS = "number of fragments"
XLEN_SLOTS = "number of slots"


def pct_labels(percents):
    """Pretty x-axis labels for a list of fractions (0.10 -> "10%")."""
    return [f"{int(round(p * 100))}%" for p in percents]


# ---------------------------------------------------------------------
# Legend / geometry layout (single source of truth — every block uses
# these so legend placement, row count, and font size stay consistent)
# ---------------------------------------------------------------------
# Above-the-axes legend for grouped bar charts (one row of N).
LEGEND_BBOX_BARS = (1.015, 1.11)
# Above-the-axes legend for line / errorbar charts.
LEGEND_BBOX_LINE = (0.5, 1.0)
# Single-series bar chart (only one legend entry): below the axes.
LEGEND_BBOX_SINGLE = (1.0, 1.0)

LEGEND_SIZE = 14           # legend font across all plots
LEGEND_NCOL_4 = 4          # 4-model / 2-model grouped bars
LEGEND_NCOL_2 = 2          # 2-model line plots
BAR_WIDTH = 0.2            # grouped-bar group width per series


# ---------------------------------------------------------------------
# Model display styles (label/color/hatch/marker per series)
# ---------------------------------------------------------------------
# Indices into the project's seaborn palette (see sim.plot.style.palette).
MODEL_LABELS = ["FixR-ToRS", "FixR-AS", "FlexR-ToRS", "FlexINA"]
MODEL_COLORS = [5, 9, 13, 1]          # same across all 4-model blocks
MODEL_HATCHES = ["/", "o", "*", "."]
MODEL_MARKERS = ["s--", "*--", "^--", "p--"]

BASELINE_LABELS = ["optimal", "FlexINA"]
BASELINE_COLORS = [17, 1]
BASELINE_HATCHES = ["+", "."]
BASELINE_MARKERS = ["o--", "p--"]

INART_LABELS = ["InArt", "FlexINA"]
INART_COLORS = [5, 1]
INART_HATCHES = ["/", "."]
INART_MARKERS = ["s--", "p--"]


def model_style(keys):
    """Return (labels, colors, hatches, markers) for a subset of style
    arrays, indexed by position 0..3 of MODEL_LABELS."""
    idx = [MODEL_LABELS.index("FixR-ToRS"), MODEL_LABELS.index("FlexR-ToRS"),
           MODEL_LABELS.index("FlexR-AS"), MODEL_LABELS.index("FlexINA")]
    n = len(keys)
    return {
        "labels": [MODEL_LABELS[k] for k in keys],
        "colors": [MODEL_COLORS[k] for k in keys],
        "hatches": [MODEL_HATCHES[k] for k in keys],
        "markers": [MODEL_MARKERS[k] for k in keys],
        "n": n,
    }


# ---------------------------------------------------------------------
# BlockRun — recorder for one block invocation
# ---------------------------------------------------------------------
def block_json_default(o):
    """JSON encoder default for the block-IO schema. Handles numpy
    integers/floats/arrays, Python sets, and ``time.struct_time`` so
    BlockRun payloads (with numpy stats + ndarrays) serialize cleanly."""
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, set):
        try:
            return sorted(o)
        except TypeError:
            return list(o)
    if isinstance(o, time.struct_time):
        return time.strftime("%Y-%m-%dT%H:%M:%S", o)
    return str(o)


class BlockRun:
    """Accumulate observations and metadata for one experiment block run,
    then save as a single clean JSON file under plots/.

    Schema (clean, stable, and enough to regenerate all of the block's
    plots offline)::

        {
          "block":           "...",
          "timestamp":       "2026-07-25T...Z",
          "host":            "...",
          "python":          "...",
          "block_runtime_s": 12.34,         # total wall time
          "config": {                       # fixed inputs to the block
              ...
          },
          "axis": {                          # labels used on plots
              "x": "...", "x_ticks": [...],
              "y_fragments": "...", "y_runtime": "..."
          },
          "per_observation": [               # one row per iteration
              {
                "model": "...", "env": "...", "x": "...", "ittr": 0,
                "packets": ..., "runtime": ...,
                "construction_time_s": ...,  # build phase
                "solve_time_s": ...,         # SCIP optimize
                "status": "..."
              }, ...
          ],
          "summary": {                       # ready to feed to plot_*
              "labels":      [...],          # x-axis tick labels
              "series": [                    # one per model/env in plot
                  {
                    "model": "...",
                    "packets_mean": [...], "packets_std": [...],
                    "runtime_mean": [...], "runtime_std": [...]
                  }, ...
              ],
              "axis": {"x": "...", "y_fragments": "...", "y_runtime": "..."}
          }
        }
    """

    def __init__(self, block: str, config: dict | None = None,
                 axis: dict | None = None):
        self.block = block
        self.start = time.time()
        self.host = platform.node()
        self.python = platform.python_version()
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.config = dict(config or {})
        self.axis = dict(axis or {})
        self.observations: list[dict] = []
        # Per-model summary cache (labels + series dicts).
        self._summary: dict | None = None

    # -- recording -------------------------------------------------
    def observe(self, *, model: str, env: str, x, ittr: int,
                packets: float | None, runtime: float | None,
                construction_time_s: float | None = None,
                solve_time_s: float | None = None,
                status: str | None = None, **extra):
        """Append one observation row (one bar/point in a single iteration)."""
        row = {
            "model": model,
            "env": env,
            "x": x,
            "ittr": int(ittr),
            "packets": packets,
            "runtime": runtime,
            "construction_time_s": construction_time_s,
            "solve_time_s": solve_time_s,
            "status": status,
        }
        row.update(extra)
        self.observations.append(row)

    # -- summary computation --------------------------------------
    def summary(self, x_labels, series_order, *,
                y_fragments=YLEN_FRAG, y_runtime=YLEN_RUNTIME,
                x_label=None):
        """Compute mean/std per ``(model, x_label)`` bucket.

        ``series_order`` is the ordered list of model/series names that
        will appear in the plot (so the JSON summary mirrors what the PDF
        shows). Returns a dict with ``labels`` (x-axis ticks) and
        ``series`` (one entry per series with mean+std arrays for both
        packets and runtime).
        """
        # Group by (model, x).
        buckets: dict[tuple, list[dict]] = {}
        for o in self.observations:
            buckets.setdefault((o["model"], o["x"]), []).append(o)

        series = []
        for model in series_order:
            pkt_mean, pkt_std = [], []
            rt_mean, rt_std = [], []
            for x in x_labels:
                rows = buckets.get((model, x), [])
                pkts = [r["packets"] for r in rows
                        if r["packets"] is not None]
                rts = [r["runtime"] for r in rows
                       if r["runtime"] is not None]
                pkt_mean.append(float(np.mean(pkts)) if pkts else None)
                pkt_std.append(float(np.std(pkts)) if pkts else None)
                rt_mean.append(float(np.mean(rts)) if rts else None)
                rt_std.append(float(np.std(rts)) if rts else None)
            series.append({
                "model": model,
                "packets_mean": pkt_mean,
                "packets_std": pkt_std,
                "runtime_mean": rt_mean,
                "runtime_std": rt_std,
            })
        return {
            "labels": list(x_labels),
            "series": series,
            "axis": {
                "x": x_label or self.axis.get("x"),
                "y_fragments": y_fragments,
                "y_runtime": y_runtime,
            },
        }

    # -- build + save ---------------------------------------------
    def to_dict(self) -> dict:
        return {
            "block": self.block,
            "timestamp": self.timestamp,
            "host": self.host,
            "python": self.python,
            "block_runtime_s": round(time.time() - self.start, 4),
            "config": self.config,
            "axis": self.axis,
            "per_observation": self.observations,
            "n_observations": len(self.observations),
        }

    def save(self, path: str, extra: dict | None = None):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        payload = self.to_dict()
        if extra:
            payload.update(extra)
        with open(path, "w") as f:
            json.dump(payload, f, indent=2, default=block_json_default)
        return path
