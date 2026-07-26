"""
sim.environments — environment (network topology + load) definitions.

Each env is a small, self-contained module that exposes a single
``env_<name>(state)`` function returning the 15-element environment tuple
the rest of the package expects. The shared assembly logic lives in
``_common.build_env`` (and the Optimaze dedup helper
``_common.optimize_env``).

Naming convention: ``env_<clusters>c_<switches>sw_<load>`` where ``<load>``
is ``<n>f`` for a uniform ``n`` fragments per worker, or ``uneven`` /
``skew1`` / ``skew15`` for non-uniform load / worker placement.

Available envs
--------------
1-cluster
~~~~~~~~~
* :func:`env_1c_5sw_3f`   — 5 switches, 3 frags/worker (reference)
* :func:`env_1c_5sw_2f`   — 5 switches, 2 frags/worker (light load)
* :func:`env_1c_3sw_4f`   — compact 3-switch spine-leaf, 4 frags/worker

2-cluster (all share the same 10-switch topology)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* :func:`env_2c_10sw_3f`       — 3 frags/worker (reference)
* :func:`env_2c_10sw_3f_sparse` — 3 frags/worker, sparse aggregation-slot mask (legacy ``env_2Clusters``)
* :func:`env_2c_10sw_6f`       — 6 frags/worker (heavier)
* :func:`env_2c_10sw_8f`       — 8 frags/worker (heavy load)
* :func:`env_2c_10sw_uneven`   — 2 frags (cluster 0) vs 5 frags (cluster 1)
* :func:`env_2c_10sw_skew15`   — 4 cluster-0 workers on switch 0 (Zipf-1.5)
* :func:`env_2c_10sw_skew1`    — all 8 workers on switch 5 (Zipf-2)

Higher cluster count
~~~~~~~~~~~~~~~~~~~~
* :func:`env_3c_14sw_4f`       — 14 switches, 3 clusters, 4 frags/worker
"""
from ._common import build_env, optimize_env

from .env_1c_5sw_3f import env_1c_5sw_3f
from .env_1c_5sw_2f import env_1c_5sw_2f
from .env_1c_3sw_4f import env_1c_3sw_4f

from .env_2c_10sw_3f import env_2c_10sw_3f
from .env_2c_10sw_3f_sparse import env_2c_10sw_3f_sparse
from .env_2c_10sw_6f import env_2c_10sw_6f
from .env_2c_10sw_8f import env_2c_10sw_8f
from .env_2c_10sw_uneven import env_2c_10sw_uneven
from .env_2c_10sw_skew15 import env_2c_10sw_skew15
from .env_2c_10sw_skew1 import env_2c_10sw_skew1

from .env_3c_14sw_4f import env_3c_14sw_4f

__all__ = [
    "build_env", "optimize_env",
    "env_1c_5sw_3f",
    "env_1c_5sw_2f",
    "env_1c_3sw_4f",
    "env_2c_10sw_3f",
    "env_2c_10sw_3f_sparse",
    "env_2c_10sw_6f",
    "env_2c_10sw_8f",
    "env_2c_10sw_uneven",
    "env_2c_10sw_skew15",
    "env_2c_10sw_skew1",
    "env_3c_14sw_4f",
]
