# SCIP-NetFrag

Optimization simulation for network fragment aggregation using SCIP solver.

## Prerequisites

- Python 3.12+
- `pyscipopt` (Python interface to SCIP solver)
- `numpy`, `matplotlib`, `seaborn`, `scikit-learn`

Install dependencies:

```bash
pip install pyscipopt numpy matplotlib seaborn scikit-learn
```

## Usage

```bash
python implementation/main.py
```

You will be prompted to select an experiment block:

```
=== Experiment Blocks ===

  baseline         — Block #1: baseline comparison
  models           — Block #1b: model comparison (4 models, 2-cluster env)
  pct_2cluster     — Block #1c: switch percentage (2-cluster env)
  pct_1cluster     — Block #1d: switch percentage (1-cluster env)
  start_time       — Block #2: start time experiment
  time_window      — Block #3: time window experiment
  worker_dist      — Block #4: worker distribution experiment
  inart            — Block #5: InArt vs FlexINA comparison
  param_sweep      — Block #6: 2-D (ρ × τ_F) sweep — heatmaps + trade-off scatter
  online_model     — Block #7: online adaptive (ρ,τ_F) — k-NN vs SGD
```

## Project Structure

```
SCIP-NetFrag/
├── README.md
├── TODO.md
├── implementation/
│   ├── main.py                 # Entry point — experiment blocks and plotting
│   ├── sim/                    # Core simulation package
│   │   ├── __init__.py         # Package exports
│   │   ├── utils.py            # TimeoutError, timeout helper, set operations, fragment creation
│   │   ├── helpers.py          # Key lookup utilities, data pre-processing
│   │   ├── environments/       # Environment definitions (topology, workers, fragments)
│   │   ├── models.py           # SCIP model builders (optimal, ATP, GRID, FlexINA)
│   │   ├── constraints.py      # Constraint functions for the optimization models
│   │   ├── runner.py           # Constraint application logic (apply_constraints)
│   │   ├── solver.py           # Objective function and solveProblem wrapper
│   │   ├── plot.py             # Centralized Matplotlib style + reusable chart builders
│   │   └── block_io.py         # BlockRun recorder + axis/legend conventions + JSON
│   ├── blocks/                 # Experiment block implementations
│   │   ├── __init__.py         # Block registry + prompt
│   │   ├── _common.py          # Shared helpers (BLOCKS, _prompt_block, etc.)
│   │   ├── _imports.py         # Centralised re-exports for all blocks
│   │   ├── _flexina_helpers.py # FlexINA per-solve helper (InArt + param_sweep)
│   │   ├── baseline.py         # Block #1: baseline comparison
│   │   ├── models.py           # Block #1b: 4-model comparison
│   │   ├── models_sparse.py    # Block #1b-sparse: 4-model sparse-slot comparison
│   │   ├── pct_2cluster.py     # Block #1c: switch percentage (2-cluster)
│   │   ├── pct_1cluster.py     # Block #1d: switch percentage (1-cluster)
│   │   ├── start_time.py       # Block #2: start time experiment
│   │   ├── time_window.py      # Block #3: time window experiment
│   │   ├── worker_dist.py      # Block #4: worker distribution experiment
│   │   ├── inart_comparison.py # Block #5: InArt vs FlexINA
│   │   ├── param_sweep.py      # Block #6: 2-D (rho x tau_F) sweep
│   │   ├── rho_tau_model.py    # Block #7 shim
│   │   └── rho_tau/            # Train + predict for (rho, tau_F) cost-predictor
│   └── plots/                  # Output PDF plots + per-block JSON outputs
└── archive/                    # Original notebook (Accelerating_New.ipynb)
```

## Environments

| Environment                 | Switches | Workers | Fragments/Worker | Description                     |
|-----------------------------|----------|---------|------------------|---------------------------------|
| `env_1Cluster_Test`         | 5        | 8       | 3                | Single cluster, small topology  |
| `env_2Clusters`             | 10       | 8       | 3                | Two clusters                    |
| `env_2Clusters_Sparse`      | 10       | 8       | 3                | Two clusters, sparse aggregation slots (`env_2c_10sw_3f_sparse`) |
| `env_2Clusters_Percentages` | 10       | 8       | 6                | Two clusters, more fragments    |
| `env_2Clusters_Zipf15`      | 10       | 8       | 3 (Zipf 1.5)     | Zipf distribution (alpha=1.5)   |
| `env_2Clusters_Zipf2`       | 10       | 8       | 3 (Zipf 2.0)     | Zipf distribution (alpha=2.0)   |

## Experiment Blocks

- **baseline** — Compares optimal model vs FlexINA across aggregation levels (max 1-3). Uses `env_1Cluster_Test`.
- **models** — Compares 4 models (FixR-ToRS, FixR-AS, FlexR-ToRS, FlexINA) across aggregation levels. Uses `env_2c_10sw_3f`.
- **models_sparse** — Same 4-model comparison as `models`, but over `env_2c_10sw_3f_sparse`, the legacy `env_2Clusters` definition (only switches {0,1,3,5,8} expose an aggregation slot). Use to reproduce the archive's "models" block. Outputs `plots/models_sparse_*.pdf` and `plots/models_sparse_data.json` alongside `run_models`'s `plots/aggregation_*.pdf` / `plots/models_data.json`.
- **pct_2cluster** — Studies effect of switch selection percentage (10%-70%) on fragments and runtime. Uses `env_2Clusters_Percentages`.
- **pct_1cluster** — Same as pct_2cluster but on the smaller `env_1Cluster_Test` environment.
- **start_time** — Varies the start time window (8-11 slots). Uses `env_2Clusters`.
- **time_window** — Varies the time window percentage (40%-100%). Uses `env_1Cluster_Test`.
- **worker_dist** — Compares uniform vs Zipf worker distributions. Uses all 2-cluster environments.
- **inart** — Compares InArt vs FlexINA. Uses `env_2Clusters`.
- **param_sweep** — Block #6 — joint 2-D sweep of switch selection fraction ρ (10%-90% in 10% steps; 9 values) and time-window τ_F (6-14 slots). Sweeps across 3 environments (`env_1Cluster_Test`, `env_2Clusters`, `env_2Clusters_Percentages`). Plots two heatmaps per environment (fragments + runtime, annotated cell-by-cell, fonts scale with grid size) plus, per environment, a trade-off scatter (packet-reduction vs runtime) with the Pareto front drawn inline. When SCIP hits the per-solve time limit but a feasible primal has been found, the cell is filled with the best-effort suboptimal solution (status `timelimit`) rather than left as `nan`, so the heatmap shows the actual exploitable trade-off surface. Saves raw grid and per-cell observations to `plots/param_sweep_data.json`; saves the standalone trade-off rows to `plots/param_sweep_tradeoff_data.json`.
- **online_model** — Block #8 — Online adaptive (ρ, τ_F) controller that updates per step. Compares two online regressors (k-NN vs linear SGD) on identical episode streams for a fair online comparison. Plots learning-curve, action trace, and runtime trace; saves raw log as `plots/online_model_log.json`.

## Online Adaptive (ρ, τ_F) Model

The `online_model` block (block #8) trains two **incremental online** regressors side-by-side to adaptively select the FlexINA parameters (ρ — switch selection fraction, τ_F — time-window size) per slot, using only quantities a real controller can observe *before* dispatching a slot.

**State features (`implementation/sim/online_model.extract_state_features`):**
- `num_switches`, `num_workers`, `num_clusters` (topology, known at setup)
- `num_active_frags` (fragments active in the current slot)
- `avg_steps_to_switch` (topology-derived)
- `iteration_index`, `T_max_2_current` (schedule position)

No realized runtime/packets are fed back into the state — that would leak the reward and inflate reported performance.

**Models (fair online comparison):**
1. **`OnlineKNN`** — action-conditioned incremental k-NN. For each candidate (ρ, τ), averages inverse-distance-weighted past runtimes of observations using the *same* action; never-tried actions get an optimistic estimate so they get explored.
2. **`OnlineSGD`** — one `sklearn.linear_model.SGDRegressor` per action, updated via `partial_fit` after every realized runtime. Truly incremental.

**Control policy (`OnlineController`):** ε-greedy with decay (`ε ← max(ε_min, ε·decay^t)`); picks the action with the smallest predicted runtime (reward = −runtime). Bad solves (infeasible / timeout / SCIP time-limit triggered) commit to both models as a large penalty runtime so they learn to avoid those (ρ, τ) at that state.

Outputs (in `plots/`): `online_model_learning_curve.pdf`, `online_model_action_trace.pdf`, `online_model_runtime_trace.pdf`, and `online_model_log.json` (raw per-step log).

## Output

Plots are saved as PDF files in the `plots/` directory. Each block generates its own set of plots for fragment counts and runtimes.

### Plot & JSON conventions (consistent across all blocks)

All axis labels, legend placement, fonts, marker/hatch colors, and bar widths live in one place — `implementation/sim/block_io.py` — so plots look identical across blocks. Edit constants there (e.g., `YLEN_RUNTIME`, `LEGEND_BBOX_BARS`, `MODEL_COLORS`, `BAR_WIDTH`) to re-theme every block at once.

Convention enforced across blocks:

| Quantity        | Label                                    | Where defined                |
|-----------------|------------------------------------------|------------------------------|
| y-axis (frag)   | `# fragments`                            | `YLEN_FRAG`                  |
| y-axis (rt)     | `runtime (s)`                            | `YLEN_RUNTIME`               |
| y-axis (rt log) | `runtime (s, $\log_{10}$ scale)`         | `YLEN_RUNTIME_LOG`           |
| x-axis (agg)    | `max. per switch aggregation`            | `XLEN_AGG`                   |
| x-axis (ρ)      | `ρ (switch selection %)`                 | `XLEN_RHO`                   |
| x-axis (τ_F)    | `τ_F start (slots)`                      | `XLEN_TAU_START`             |
| x-axis (win %)  | `time window (%)`                        | `XLEN_TIME_WINDOW`           |
| x-axis (topo)   | `topology`                               | `XLEN_TOPOLOGY`              |
| x-axis (dist)   | `worker distribution`                    | `XLEN_DISTRIBUTION`          |

Legend/font geometry: `LEGEND_BBOX_BARS = (1.015, 1.11)`, `LEGEND_BBOX_LINE = (0.5, 1.0)`, `LEGEND_SIZE = 14`, `BAR_WIDTH = 0.2`, `LEGEND_NCOL_4 = 4`, `LEGEND_NCOL_2 = 2` (all in `implementation/sim/block_io.py`). Figure size, font sizes & rcParams come from `implementation/sim/plot.py` (the `Style` dataclass + `apply`).

### Per-block JSON outputs (regenerate plots from disk)

Every block records its run statistics into a single JSON file in `plots/`, complete with everything needed to regenerate the PDF plots offline without re-running SCIP:

| Block            | JSON file                          |
|------------------|------------------------------------|
| `baseline`       | `plots/baseline_data.json`        |
| `models`         | `plots/models_data.json`           |
| `pct_2cluster`   | `plots/pct_2cluster_data.json`     |
| `pct_1cluster`   | `plots/pct_1cluster_data.json`     |
| `start_time`     | `plots/start_time_data.json`       |
| `time_window`    | `plots/time_window_data.json`      |
| `worker_dist`    | `plots/worker_dist_data.json`      |
| `inart`          | `plots/inart_data.json`            |
| `param_sweep`    | `plots/param_sweep_data.json` (with the `per_solve`/`grids` keys still present for use by `blocks/rho_tau/train.py`) and standalone `param_sweep_tradeoff_data.json` |

Each JSON file contains the same general-information envelope (provided by `sim.block_io.BlockRun`):

```json
{
  "block":           "<block name>",
  "timestamp":       "<ISO-8601 UTC of block start>",
  "host":            "<hostname>",
  "python":          "<python version>",
  "block_runtime_s": <total wall time (s) for the entire block>,
  "config":          <fixed inputs to the block: envs, models, maxAggregate, ittrNum, percentage, T_max_2_init, addTime_factor, ...>,
  "axis":            <axis-label metadata used on each plot>,
  "per_observation": [ <one row per (model, env, x-tick, ittr) iteration,
                        with packets, runtime, construction_time_s,
                        solve_time_s, summary status string> ],
  "summary":         { "labels": [...], "series": [{ "model": ...,
                        "packets_mean/std": [...],
                        "runtime_mean/std": [...] }], "axis": {...} },
  "plot_files":      ["plots/foo.pdf", "..."]
}
```

Platform-agnostic JSON encoder (`sim.block_io.block_json_default`) handles numpy `int`/`float`/`ndarray`, Python `set`s, and `struct_time`s.
