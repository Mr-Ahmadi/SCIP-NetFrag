"""
Environment (network topology + load) definitions.

Naming: env_<clusters>c_<switches>sw_<load> where <load> is <n>f for
uniform n fragments/worker, or uneven/skew1/skew15 for non-uniform.
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
