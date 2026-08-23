# SCIP-NetFrag

Optimization simulation for network fragment aggregation using the SCIP solver.

## Setup

Requires Python 3.12+.

```bash
pip install pyscipopt numpy matplotlib seaborn scikit-learn torch
```

## Usage

```bash
python implementation/main.py
```

You will be prompted to pick an experiment block:

```
=== Experiment Blocks ===

  baseline         — Block #1: baseline comparison (optimal vs FlexINA, 1-cluster env)
  pct_2cluster     — Block #2: switch percentage rho (2-cluster env)
  pct_1cluster     — Block #3: switch percentage rho (1-cluster env)
  start_time       — Block #4: start time tau_start experiment
  time_window      — Block #5: time window fraction experiment
  worker_dist      — Block #6: worker load distribution experiment
  switch_memory    — Block #7: switch memory (1/2/3 slots per switch, 1-cluster env)
  topologies       — Block #8: topology comparison (7sw tree, 5sw 1-cluster, 10sw 2-cluster)
  inart            — Block #9: InArt vs FlexINA comparison (single-PS structural proxy)
  param_sweep      — Block #10: 2-D (rho x tau_F) sweep - heatmaps + trade-off scatter
  rho_tau_model    — Block #11: train + test (rho, tau_F) cost-predictor
  big_env          — Block #12: FlexINA solve on 15/20/25-switch envs + scaling plot
  models           — Block #13: comparison of 4 formulations
```

Or run a block directly:

```bash
python implementation/main.py baseline
```

## Project Structure

```
SCIP-NetFrag/
├── implementation/
│   ├── main.py                 # Entry point — experiment blocks and plotting
│   ├── sim/                    # Core simulation package
│   │   ├── environments/       # Environment definitions (topology, workers, fragments)
│   │   ├── models.py           # SCIP model builders (optimal, ATP, GRID, FlexINA)
│   │   ├── constraints.py      # Constraint functions for the optimization models
│   │   ├── solver.py           # Objective function and solve wrapper
│   │   └── plot.py             # Matplotlib style + reusable chart builders
│   ├── blocks/                 # Experiment block implementations (#1–#13)
│   │   └── rho_tau/            # Train + predict for the (rho, tau_F) cost-predictor
│   └── plots/                  # Output PDF plots + per-block JSON data
└── archive/                    # Original notebook
```

## Environments

Environments live in `implementation/sim/environments/` and are named
`env_<clusters>c_<switches>sw_<load>` (e.g. `env_2c_10sw_3f` = 2 clusters,
10 switches, 3 fragments per worker). Variants exist for different loads,
skew, memory slots, and larger topologies up to 25 switches.

## Blocks

Blocks #1–#13 are grouped so each section builds on the last:

- **Model validation** — `baseline`: optimal model vs FlexINA.
- **Single-factor sweeps** — `pct_*`, `start_time`, `time_window`, `worker_dist`,
  `switch_memory`, `topologies`: hold every knob fixed except one.
- **Cross-algorithm comparison** — `inart`: InArt proxy vs FlexINA.
- **Tuning pipeline** — `param_sweep`: joint 2-D (ρ × τ_F) sweep;
  `rho_tau_model`: MLP cost-predictor trained on the sweep's per-solve data,
  used as a selector that picks (ρ, τ_F) minimizing predicted cost.
- **Scaling & ablations** — `big_env`: large-topology scaling;
  `models`: comparison of the four formulations.

## Output

Plots are saved as PDFs in `implementation/plots/`. Every block also records its
run statistics into a JSON file there (`<block>_data.json`) containing config,
per-observation rows, summary statistics, and plot paths — so plots can be
regenerated from disk without re-running SCIP. Axis labels, legend placement,
fonts, and colors are centralized in `implementation/sim/block_io.py`.
