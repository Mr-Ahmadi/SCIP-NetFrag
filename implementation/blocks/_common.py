"""Shared helpers and metadata used across all experiment blocks."""
import sys


BLOCKS = {
    # -- Model validation ---------------------------------------------------
    "baseline":       "Block #1: baseline comparison (optimal vs FlexINA, 1-cluster env)",
    # -- Single-factor sweeps -----------------------------------------------
    "pct_2cluster":   "Block #2: switch percentage rho (2-cluster env)",
    "pct_1cluster":   "Block #3: switch percentage rho (1-cluster env)",
    "start_time":     "Block #4: start time tau_start experiment",
    "time_window":    "Block #5: time window fraction experiment",
    "worker_dist":    "Block #6: worker load distribution experiment",
    "switch_memory":  "Block #7: switch memory (1/2/3 slots per switch, 1-cluster env)",
    "topologies":     "Block #8: topology comparison (7sw tree, 5sw 1-cluster, 10sw 2-cluster)",
    # -- Cross-algorithm comparison ------------------------------------------
    "inart":          "Block #9: InArt vs FlexINA comparison (single-PS structural proxy, not full InArt algorithm)",
    # -- Tuning pipeline ------------------------------------------------------
    "param_sweep":    "Block #10: 2-D (rho x tau_F) sweep - heatmaps + trade-off scatter",
    "rho_tau_model":  "Block #11: train + test (rho, tau_F) cost-predictor (param_sweep -> model + selector eval)",
    # -- Scaling & ablations --------------------------------------------------
    "big_env":        "Block #12: single FlexINA solve on the 15-, 20- and 25-switch envs (no time limit) + scaling plot",
    "models":         "Block #13: model comparison - 4 formulations (inverted-ranking env, 2c-10sw-3f-sp)",
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


def _unpack_env(envTemp, load=False):
    return envTemp(state='OptimazeLoad' if load else 'Optimaze')


# FlexINA per-slot window factor (param_sweep addTime = ADD_TIME_FACTOR * tau_F);
# shared with the other 0.6-factor blocks (start_time).
ADD_TIME_FACTOR = 0.6


def _prepare_dict_list(fragmentsofEachWorker, totalWorkers):
    finalWorkers = {k: totalWorkers[k] for k in fragmentsofEachWorker}
    num_dicts = max(len(v) for v in finalWorkers.values())
    return [{k: [v[i]] for k, v in finalWorkers.items() if i < len(v)}
            for i in range(num_dicts)]
