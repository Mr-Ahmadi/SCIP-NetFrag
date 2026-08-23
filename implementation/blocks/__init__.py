"""Experiment blocks — each run_<name> is selectable from main.py."""
from blocks._common import BLOCKS, _prompt_block
from blocks.baseline import run_baseline
from blocks.pct_2cluster import run_pct_2cluster
from blocks.pct_1cluster import run_pct_1cluster
from blocks.start_time import run_start_time
from blocks.time_window import run_time_window
from blocks.worker_dist import run_worker_dist
from blocks.switch_memory import run_switch_memory
from blocks.topologies import run_topologies
from blocks.inart_comparison import run_inart_comparison
from blocks.param_sweep import run_param_sweep
from blocks.rho_tau_model import run_rho_tau_model
from blocks.big_env import run_big_env
from blocks.models import run_models

# Backward-compat alias kept for scripts that referenced the old name.
run_tradeoff = run_param_sweep

BLOCK_RUNNERS = {
    "baseline":       run_baseline,
    "pct_2cluster":   run_pct_2cluster,
    "pct_1cluster":   run_pct_1cluster,
    "start_time":     run_start_time,
    "time_window":    run_time_window,
    "worker_dist":    run_worker_dist,
    "switch_memory":  run_switch_memory,
    "topologies":     run_topologies,
    "inart":          run_inart_comparison,
    "param_sweep":    run_param_sweep,
    "rho_tau_model":  run_rho_tau_model,
    "big_env":        run_big_env,
    "models":         run_models,
}

__all__ = [
    "BLOCKS", "_prompt_block", "BLOCK_RUNNERS",
    "run_baseline",
    "run_pct_2cluster", "run_pct_1cluster",
    "run_start_time", "run_time_window", "run_worker_dist",
    "run_switch_memory", "run_topologies",
    "run_inart_comparison", "run_param_sweep", "run_tradeoff",
    "run_rho_tau_model", "run_big_env", "run_models",
]
