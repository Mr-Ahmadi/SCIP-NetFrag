"""``rho_tau`` subsystem — trains and serves the (rho, tau_F)
cost-predictor used by the ``rho_tau_model`` experiment block.

Modules:
    train    — offline training CLI; reads param_sweep per-solve rows
               and writes the PyTorch regressor + feature spec to
               ``plots/``. Runnable via ``python -m blocks.rho_tau.train``.
    predict  — inference helper; loads the trained model and picks
               (rho, tau) for a given observable environment state.
               Runnable via ``python -m blocks.rho_tau.predict``.
    block    — the experiment-block entry-point ``run_rho_tau_model``.

Import paths callers should use:
    from blocks.rho_tau.predict import select_rho_tau, load_model
    from blocks.rho_tau.train import (
        CostMLP, NUMERIC_FEATURES, WORKER_HIST_BINS, build_feature_matrix, ...)
    from blocks.rho_tau import run_rho_tau_model      # the block entry-point

``train`` / ``predict`` are intentionally re-exported lazily so the
package init stays cheap and running ``python -m blocks.rho_tau.train``
does not trigger runpy's "found in sys.modules prior to execution"
warning.
"""
from blocks.rho_tau.block import run_rho_tau_model

__all__ = ["run_rho_tau_model"]
