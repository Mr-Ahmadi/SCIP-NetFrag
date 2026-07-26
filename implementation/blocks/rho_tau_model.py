"""Backward-compat shim.

The rho-tau cost-predictor lives in the :mod:`blocks.rho_tau` sub-package
(``blocks/rho_tau/block.py``). This module simply re-exports its public
entry-point so that ``blocks/__init__.py`` and any external importer that
still does ``from blocks.rho_tau_model import run_rho_tau_model`` keeps
working unchanged.
"""
from blocks.rho_tau.block import run_rho_tau_model

__all__ = ["run_rho_tau_model"]
