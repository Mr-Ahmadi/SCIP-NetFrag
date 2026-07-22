# SCIP-NetFrag

Optimization simulation for network fragment aggregation using SCIP solver.

## Prerequisites

- Python 3.12+
- `pyscipopt` (Python interface to SCIP solver)
- `numpy`, `matplotlib`, `seaborn`

Install dependencies:

```bash
pip install pyscipopt numpy matplotlib seaborn
```

## Usage

```bash
python main.py
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
  all                — run every block
```

## Project Structure

```
SCIP-NetFrag/
├── main.py                 # Entry point — experiment blocks and plotting
├── sim/                    # Core simulation package
│   ├── __init__.py         # Package exports
│   ├── utils.py            # TimeoutError, timeout helper, set operations, fragment creation
│   ├── helpers.py          # Key lookup utilities, data pre-processing
│   ├── environments.py     # Environment definitions (topology, workers, fragments)
│   ├── models.py           # SCIP model builders (optimal, ATP, GRID, FlexINA)
│   ├── constraints.py      # Constraint functions for the optimization models
│   ├── runner.py           # Constraint application logic (apply_constraints)
│   ├── solver.py           # Objective function and solveProblem wrapper
│   └── plots.py            # Reusable plotting helpers (bar charts, error bars)
├── plots/                  # Output PDF plots
├── archive/                # Original notebook (Accelerating_New.ipynb)
└── __pycache__/
```

## Environments

| Environment                 | Switches | Workers | Fragments/Worker | Description                     |
|-----------------------------|----------|---------|------------------|---------------------------------|
| `env_1Cluster_Test`         | 5        | 8       | 3                | Single cluster, small topology  |
| `env_2Clusters`             | 10       | 8       | 3                | Two clusters                    |
| `env_2Clusters_Percentages` | 10       | 8       | 6                | Two clusters, more fragments    |
| `env_2Clusters_Zipf15`      | 10       | 8       | 3 (Zipf 1.5)     | Zipf distribution (alpha=1.5)   |
| `env_2Clusters_Zipf2`       | 10       | 8       | 3 (Zipf 2.0)     | Zipf distribution (alpha=2.0)   |

## Experiment Blocks

- **baseline** — Compares optimal model vs FlexINA across aggregation levels (max 1-3). Uses `env_1Cluster_Test`.
- **models** — Compares 4 models (FixR-ToRS, FixR-AS, FlexR-ToRS, FlexINA) across aggregation levels. Uses `env_2Clusters`.
- **pct_2cluster** — Studies effect of switch selection percentage (10%-70%) on fragments and runtime. Uses `env_2Clusters_Percentages`.
- **pct_1cluster** — Same as pct_2cluster but on the smaller `env_1Cluster_Test` environment.
- **start_time** — Varies the start time window (8-11 slots). Uses `env_2Clusters`.
- **time_window** — Varies the time window percentage (40%-100%). Uses `env_1Cluster_Test`.
- **worker_dist** — Compares uniform vs Zipf worker distributions. Uses all 2-cluster environments.

## Output

Plots are saved as PDF files in the `plots/` directory. Each block generates its own set of plots for fragment counts and runtimes.
