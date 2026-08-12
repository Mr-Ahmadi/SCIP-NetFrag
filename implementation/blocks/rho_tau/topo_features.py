"""Topology-level features for the (rho, tau_F) cost-predictor.

These make environments that are indistinguishable by per-solve load
statistics alone separable: connectivity (switch degree distribution),
aggregation-capacity profile (which switches have aggregation slots),
hop-distance summary, and worker-to-switch attachment. They are constant per
environment and computed from the *collapsed* (OptimazeLoad) env tuple so they
match exactly the topology the solver is invoked on.

At inference time these are knowable from the live network, so unlike an "env"
label they do not leak anything unavailable at deployment.
"""
import numpy as np


TOPOLOGY_FEATURES = [
    # hop-distance summary over surviving workers' rows of stepsToSwitches
    "max_hop", "mean_hop", "std_hop",
    # aggregation-capacity profile from numberSlotsSwitches
    "num_agg_switches", "frac_agg_switches",
    # switch degree distribution from neighborsofEachSwitch
    "mean_degree", "std_degree", "max_degree", "frac_zero_degree",
    # worker-to-switch attachment from workersTopology
    "max_workers_per_switch", "mean_workers_per_switch",
]


def topology_features(env_tuple):
    """Compute the fixed topology feature dict for an env tuple.

    ``env_tuple`` is the 15-element ``build_env(...)`` return value; pass the
    same collapsed state the solver uses (state='OptimazeLoad').
    """
    (pSwitchesTopology, _, neighborsofEachSwitch, _, numberSlotsSwitches,
     workersTopology, _, _, _, _, _, stepsToSwitches, _, _, _) = env_tuple

    switches = list(pSwitchesTopology.keys()) if pSwitchesTopology else []

    hops = np.array(
        [h for w, row in stepsToSwitches.items()
         if w in workersTopology for h in row], dtype=float)

    slots = np.array([len(numberSlotsSwitches.get(s, ())) for s in switches],
                     dtype=float)
    num_agg = int((slots > 0).sum())

    degs = np.array([len(neighborsofEachSwitch.get(s, ())) for s in switches],
                    dtype=float)

    workers_per_switch = {}
    for w, s in workersTopology.items():
        workers_per_switch[s] = workers_per_switch.get(s, 0) + 1
    wps = np.array([workers_per_switch.get(s, 0) for s in switches],
                   dtype=float)

    def _stat(a, fn):
        return float(fn(a)) if a.size else 0.0

    return {
        "max_hop": _stat(hops, np.max),
        "mean_hop": _stat(hops, np.mean),
        "std_hop": _stat(hops, np.std),
        "num_agg_switches": float(num_agg),
        "frac_agg_switches": float(num_agg / len(switches)) if switches else 0.0,
        "mean_degree": _stat(degs, np.mean),
        "std_degree": _stat(degs, np.std),
        "max_degree": _stat(degs, np.max),
        "frac_zero_degree": float((degs == 0).mean()) if degs.size else 0.0,
        "max_workers_per_switch": _stat(wps, np.max),
        "mean_workers_per_switch": _stat(wps, np.mean),
    }
