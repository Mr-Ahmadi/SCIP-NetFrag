"""Shared helpers and metadata used across all experiment blocks.

Kept separate so each block module can `from blocks._common import *`
and not have to repeat the boilerplate.
"""
import sys


BLOCKS = {
    "baseline":       "Block #1: baseline comparison",
    "models":         "Block #1b: model comparison (4 models, 2-cluster env)",
    "models_sparse":  "Block #1b-sparse: model comparison (4 models, sparse-slot 2-cluster env)",
    "pct_2cluster":   "Block #1c: switch percentage (2-cluster env)",
    "pct_1cluster":   "Block #1d: switch percentage (1-cluster env)",
    "start_time":     "Block #2: start time experiment",
    "time_window":    "Block #3: time window experiment",
    "worker_dist":    "Block #4: worker distribution experiment",
    "inart":          "Block #5: InArt vs FlexINA comparison",
    "param_sweep":    "Block #6: 2-D (rho x tau_F) sweep - heatmaps + trade-off scatter",
    "rho_tau_model":  "Block #7: train + test (rho, tau_F) cost-predictor (param_sweep -> model + selector eval)",
}


def _prompt_block():
    print("\n=== Experiment Blocks ===\n")
    for key, desc in BLOCKS.items():
        print(f"  {key:15s} — {desc}")
    print()
    choice = input("Enter block to run [baseline]: ").strip()
    if not choice:
        choice = "baseline"
    if choice not in BLOCKS:
        print(f"Unknown block '{choice}', defaulting to 'baseline'")
        choice = "baseline"
    return choice


def _unpack_env(envTemp):
    return envTemp(state='Optimaze')


def _prepare_dict_list(fragmentsofEachWorker, totalWorkers):
    finalWorkers = {k: totalWorkers[k] for k in fragmentsofEachWorker}
    num_dicts = len(next(iter(finalWorkers.values())))
    return [{k: [v[i]] for k, v in finalWorkers.items()} for i in range(num_dicts)]
