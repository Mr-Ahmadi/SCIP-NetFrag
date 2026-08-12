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
  rho_tau_model    — Block #7: train + test (ρ, τ_F) cost-predictor (param_sweep → model + selector eval)
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
| `env_2Clusters`             | 10       | 8       | 3                | Two clusters (`env_2c_10sw_3f`), sparse aggregation slots (only switches {0,1,3,5,8}) |
| `env_2Clusters_Percentages` | 10       | 8       | 6                | Two clusters, more fragments    |
| `env_2Clusters_Zipf15`      | 10       | 8       | 3 (Zipf 1.5)     | Zipf distribution (alpha=1.5)   |
| `env_2Clusters_Zipf2`       | 10       | 8       | 3 (Zipf 2.0)     | Zipf distribution (alpha=2.0)   |

## Experiment Blocks

- **baseline** — Compares optimal model vs FlexINA across aggregation levels (max 1-3). Uses `env_1Cluster_Test`.
- **models** — Compares 4 models (FixR-ToRS, FixR-AS, FlexR-ToRS, FlexINA) across aggregation levels. Uses `env_2c_10sw_3f` (the legacy `env_2Clusters` definition, with aggregation slots only on switches {0,1,3,5,8}).
- **pct_2cluster** — Studies effect of switch selection percentage (10%-70%) on fragments and runtime. Uses `env_2Clusters_Percentages`.
- **pct_1cluster** — Same as pct_2cluster but on the smaller `env_1Cluster_Test` environment.
- **start_time** — Varies the start time window (8-11 slots). Uses `env_2Clusters`.
- **time_window** — Varies the time window percentage (40%-100%). Uses `env_1Cluster_Test`.
- **worker_dist** — Compares uniform vs Zipf worker distributions. Uses all 2-cluster environments.
- **inart** — Compares InArt vs FlexINA. Uses `env_2Clusters`. InArt here is a single-PS structural proxy: FlexINA's own model/routing/scheduling plus InArt's INA constraint (each fragment aggregated in-network at most once, i.e. no chained aggregation) — it does **not** implement InArt's actual multi-PS model-splitting (L-InArt) or randomized-rounding route selection (R-InArt), since every environment here has only one PS. See `blocks/inart_comparison.py`'s module docstring for details.
- **param_sweep** — Block #6 — joint 2-D sweep of switch selection fraction ρ (10%-90% in 10% steps; 9 values) and time-window τ_F (6-12 slots). Sweeps in load-preserving mode across 5 environments spanning the topology/load axes (`env_1c_5sw_3f`, `env_2c_10sw_3f`, `env_2c_10sw_6f`, `env_2c_10sw_skew15`, `env_3c_14sw_4f`). Plots two heatmaps per environment (fragments + runtime, annotated cell-by-cell, fonts scale with grid size) plus, per environment, a trade-off scatter (packet-reduction vs runtime) with the Pareto front drawn inline. When SCIP hits the per-solve time limit but a feasible primal has been found, the cell is filled with the best-effort suboptimal solution (status `timelimit`) rather than left as `nan`, so the heatmap shows the actual exploitable trade-off surface. Saves raw grid, per-cell observations, and a per-sub-solve `per_solve` array (per-slot state + load — the training data for `rho_tau_model`) to `plots/param_sweep_data.json`; saves the standalone trade-off rows to `plots/param_sweep_tradeoff_data.json`.
- **rho_tau_model** — Block #7 — offline (ρ, τ_F) cost-predictor trained on the `per_solve` rows of `param_sweep`, then used as a selector: for each observable state it picks the (ρ, τ_F) minimizing a user-chosen objective (predicted solve time and/or predicted packet count, via `objective` + importance weights `W_RUNTIME`/`W_PACKETS` in `blocks/rho_tau/block.py`) and reports oracle regret / gap-to-worst per environment.

## (ρ, τ_F) Cost-Predictor Model

The `rho_tau_model` block (block #7) trains an offline **multi-objective** MLP cost-predictor on the `per_solve` rows of `param_sweep`, then uses it as a selector: for each observable state it picks the (ρ, τ_F) minimizing a user-chosen objective — predicted per-slot solve time and/or predicted ILP packet count (the primary objective) — and reports oracle regret.

**Training data** — `plots/param_sweep_data.json` → `per_solve` (one row per sub-solve: `env`, `rho`, `tau`, `ittr`, `slot_idx`, `status`, `packets`, `runtime`, `T_max_1`/`T_max_2`, topology counts, `num_active_frags`, `per_worker_num_frags`).

**Censoring (`timelimit` rows)** — a `timelimit` row is neither a failure nor a normal observation. Its **runtime is right-censored** (the solve was cut off at the budget, so the recorded ≈`timeout_per_solve` seconds is only a lower bound on the true time), while its **packet count is fully observed** (`sim/solver.py` keeps the best-effort primal, so that incumbent is the result the pipeline would actually ship). `--censoring` picks the policy:

| policy | runtime | packets | timeout head |
|---|---|---|---|
| `drop` (default) | excluded | excluded | trained |
| `censored` | one-sided hinge — only *under*prediction of the bound is penalized | trained on the real incumbent | trained |
| `penalty` (legacy) | constant penalty | constant penalty | trained |

`penalty` is kept only for comparison: it labels censored rows with a runtime *below* the observed timeout and a packet count *worse* than the one actually achieved, contradicting the data on both axes. On a held-out grouped split it drives packets R² to **−1.57** (worse than predicting the mean) and the runtime head never places a censored solve above its own bound. `censored` looks better-founded (the ~10% of rows that hit the time limit still contribute a lower bound instead of being thrown away) but measurably costs held-out accuracy on this dataset — a two-seed ablation (`--seed 7`/`--seed 3`, everything else equal) gives val runtime `r2_log1p` 0.924/0.943 vs. **0.951/0.957** for `drop`, and val `mae_s` 6.49/2.66 vs. **3.45/1.97**; the timeout head is a wash either way since it always trains on every row's status regardless of `--censoring`. `--w_censor` (default `0.1`, only relevant under `censored`) sets the hinge weight: raising it makes the runtime head respect the "≥ timeout" bound but drags the shared trunk upward and costs accuracy on solves that did finish — which is exactly the effect that makes `drop` the better default here.

**Features** (`blocks/rho_tau/train.py`, `NUMERIC_FEATURES`): topology (`num_switches`, `num_workers`, `num_all_frags`, `num_clusters`), per-slot load (`num_active_frags`, `num_active_workers`, plus a capped 8-bin histogram of `per_worker_num_frags`), schedule position (`slot_idx`), the two knobs (`rho`, `tau`), and engineered cross terms (`rho_x_active_frags`, `tau_x_workers`, `tau_over_frags`, `active_ratio`, `load_entropy`) plus ILP search-space proxies (`sel_switches` = ρ·`num_switches`, `space_log`, `frags_per_worker`). `T_max_1`/`T_max_2` are deliberately **not** features — each is a deterministic function of `(slot_idx, tau)` which are already inputs (`T_max_1 = slot_idx·int(0.6τ)`, `T_max_2 = τ + T_max_1`); `ittr` is likewise excluded because it is a pure repetition index that re-solves the same state and carries no causal signal. `ittr` is still retained in the data and used as a grouping key at evaluation time so each iteration contributes an independent regret sample.

**Model output** (`CostMLP`, `n_out=3`) — two standardized log1p regressions `[pred_runtime, pred_packets]` (z-scores computed on the train split and stored in the checkpoint as `target_stats`) plus a **timeout logit** `P(this (ρ, τ_F) hits the time limit)`, class-balanced since timeouts are the minority. Loss = masked Huber per regression head + censoring hinge + BCE on the timeout head + a within-state **pairwise ranking loss** (`--w_rank`), because selection consumes the *ordering* of candidates inside one state, which a pure regression loss only optimizes indirectly. Training is mini-batched (`--batch_size`, AdamW, grad clipping) and `--n_models` (default 3) trains a deep ensemble whose predictions are averaged. Old `n_out=1`/`n_out=2` checkpoints still load and degrade gracefully.

**Splitting** — all splits are **grouped by state** (`env`, `ittr`, `slot_idx`), so every (ρ, τ_F) cell of a state stays on one side. A plain row-wise split would put siblings of the same state in both train and val, making validation a memorization test. `--test_env` adds leave-one-env-out on top.

**Selector** — `blocks/rho_tau/predict.py::select_rho_tau` enumerates the (ρ, τ_F) grid, drops candidates whose predicted `P(timeout)` exceeds `--timeout_thresh` (falling back to the least-risky candidate if all are filtered), and minimizes `score = w_runtime·z_runtime + w_packets·z_packets` over the rest. Because the two heads output standardized values, the importance ratio `w_runtime : w_packets` is directly interpretable (units of training-set std). `objective` selects the axes: `'runtime'` → (1, 0), `'packets'` → (0, 1), `'tradeoff'` → the weights. Configure it in `blocks/rho_tau/block.py` via the module constants `OBJECTIVE`, `W_RUNTIME`, `W_PACKETS`, `CENSORING`, `TIMEOUT_THRESH` (recorded in the block config), or per-call via the `predict` CLI. The exact same path is used at train-eval time (`train.evaluate_selector` delegates to it) and in the block's selector evaluation, so the two cannot drift. Because the window is a consequence of the chosen (τ_F, slot), not part of the pre-choice state, the selector needs no window arithmetic: candidate features are reconstructed from the observable state alone.

The `feasibility` argument — a ground-truth mask of which pairs really solved — is **oracle-only**. It is never used on the deployment path; the model's own timeout head is what rules out infeasible regions at inference.

**Winner's-curse de-biasing (report ensemble)** — the (ρ*, τ*) the selector picks is the argmin of the selection ensemble's own score over ~dozens of candidates, so that ensemble's prediction *at its own winner* is biased low: it won partly because that ensemble happened to score it best. `--n_report_models` (block default 4, CLI default 2) trains a second ensemble, each member on an independent **bootstrap resample of the training state groups**, that never participates in the argmin search; `select_rho_tau` re-scores only the already-chosen (ρ*, τ*) with it, so `pred_runtime`/`pred_packets` are an unbiased estimate of the pick's cost, decision unaffected. Bootstrapping the resample matters — a same-data/different-seed ensemble converges to nearly the same function (ensemble std in z-units was ~0.02–0.05 against a target scale of ~1.4, i.e. it barely disagrees with itself) and so barely decorrelates the bias it exists to audit; resampling state groups gave each member genuinely different sampling noise, and bagging's variance-reduction is why more members keep helping: mean bias on `rho_tau_model_pred_vs_actual.pdf` went ≈0.10s (no report ensemble) → ≈0.03s (2 bagged members) → ≈0.026s (4 bagged members), each roughly consistent with the ~1/n_report_models scaling bagging predicts. Falls back to the selection ensemble's own (biased) number if `--n_report_models 0`.

**Evaluation** — `train.py` reports per-head accuracy in real units on the rows each head actually supervises (runtime MAE/median-AE in seconds, R² and Spearman, `frac_at_or_above_bound` for censored rows, packets MAE/R², timeout-head AUC/precision/recall, and mean within-state Spearman — the metric the argmin selector consumes) on both the train split and the held-out val states. `blocks/rho_tau/block.py` groups per-solve rows by observable state, computes the oracle best/worst runtime and best/worst packets within each group, and reports `regret` (chosen − best runtime), `packet_regret`, `gap_to_worst` and `frac_timeout_pick` per environment. A pick that times out is scored with its **real** observed cost rather than discarded, and the block also reports an `oracle_feasibility_upper_bound` variant to quantify what the timeout head still costs.

**CLIs** (both argparse):
```bash
python -m blocks.rho_tau.train --data plots/param_sweep_data.json --epochs 400 --n_models 3 --censoring drop --objective tradeoff --w_runtime 1.0 --w_packets 1.0
python -m blocks.rho_tau.predict --num_switches 5 --num_workers 4 --num_all_frags 4 --num_clusters 1 --per_worker_num_frags '{"11":1,"33":1,"55":1,"77":1}' --objective packets --w_packets 2.0
```

Outputs (in `plots/`): `rho_tau_model.pt`, `rho_tau_model_features.json`, `rho_tau_model_eval.json`, `rho_tau_model_data.json` (block envelope + per-state quality), `rho_tau_model_regret_by_env.pdf`, `rho_tau_model_pred_vs_actual.pdf` / `_packets.pdf` (predicted vs. observed **at the selector's picks only** — small-n and biased low by the "winner's curse" of taking an argmin over ~60 noisy candidates per state, not a measure of raw model accuracy), `rho_tau_model_regression_accuracy.pdf` / `_packets.pdf` (predicted vs. observed over **every** scored row — the honest accuracy plot; log-log for runtime given its multi-decade range).

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
| `rho_tau_model`  | `plots/rho_tau_model_data.json` (+ `rho_tau_model.pt`, `rho_tau_model_features.json`, `rho_tau_model_eval.json`) |

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
