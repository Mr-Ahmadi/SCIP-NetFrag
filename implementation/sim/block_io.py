"""Block run recorder and shared plot/JSON conventions."""
from __future__ import annotations

import json
import os
import platform
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np

# Axis-label constants (single source of truth)
YLEN_FRAG = "# fragments"
YLEN_RUNTIME = "runtime (s)"
YLEN_RUNTIME_LOG = "runtime (s, $\\log_{10}$ scale)"

XLEN_AGG = "max. per switch aggregation"
XLEN_TOPOLOGY = "topology"
XLEN_DISTRIBUTION = "worker distribution"
XLEN_RHO = "ρ (switch selection %)"
XLEN_TAU_START = "τ_F (slots)"
XLEN_TIME_WINDOW = "τ_S (% of τ_F)"
XLEN_TAU_WINDOW = "τ_F (time window)"
XLEN_REDUCTION = "Packet reduction (1 − pkts/pkts₀)"
XLEN_FRAGS = "number of fragments"
XLEN_SLOTS = "number of slots"


def pct_labels(percents):
    """Pretty x-axis labels for a list of fractions (0.10 -> "10%")."""
    return [f"{int(round(p * 100))}%" for p in percents]


# Pretty x-axis labels for env_* functions.
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


def env_labels(envs):
    """Pretty x-axis labels for a list of env_* functions."""
    return [ENV_DISPLAY_NAMES.get(e.__name__, e.__name__) for e in envs]


# Legend / geometry layout (single source of truth)
LEGEND_BBOX_BARS = (1.015, 1.11)
LEGEND_BBOX_LINE = (0.5, 1.0)
LEGEND_BBOX_SINGLE = (1.0, 1.0)

LEGEND_SIZE = 14           # legend font across all plots
LEGEND_NCOL_4 = 4          # 4-model / 2-model grouped bars
LEGEND_NCOL_2 = 2          # 2-model line plots
BAR_WIDTH = 0.2            # grouped-bar group width per series


# Model display styles (label/color/hatch/marker per series)
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


def block_json_default(o):
    """JSON encoder default for numpy scalars, sets, and struct_time."""
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
    """Accumulate observations and metadata for one experiment block run."""

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
        self._summary: dict | None = None

    # -- recording
    def observe(self, *, model: str, env: str, x, ittr: int,
                packets: float | None, runtime: float | None,
                construction_time_s: float | None = None,
                solve_time_s: float | None = None,
                status: str | None = None, **extra):
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

    # -- summary computation
    def summary(self, x_labels, series_order, *,
                y_fragments=YLEN_FRAG, y_runtime=YLEN_RUNTIME,
                x_label=None):
        """Compute mean/std per (model, x_label) bucket."""
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

    # -- build + save
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
