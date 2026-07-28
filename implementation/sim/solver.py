"""Objective function and problem solver."""
import time

import numpy as np


def objective(Y_Variables, model):
    Y_Variables_Array = [Y_Variables[yParam] for yParam in Y_Variables]
    model.setObjective(sum(Y_Variables_Array), "minimize")


# SCIP statuses where a feasible primal may still be available.
_FEASIBLE_STATUSES = ("optimal", "timelimit", "nodelimit", "sollimit",
                      "stallnodelimit", "gaplimit")


def solveProblem(model, Y_Used, Z_Used, time_limit=None, gap=None):
    """
    gap : optional relative MIP-gap tolerance in [0, 1).
    """
    from . import constraints as _cons

    Y_Value_One = []
    Z_Value_One = []
    model.setParam("parallel/maxnthreads", 8)
    if time_limit is not None and time_limit > 0:
        model.setRealParam("limits/time", float(time_limit))
    if gap is not None and gap > 0:
        model.setRealParam("limits/gap", float(gap))
    startTime = time.time()
    model.optimize()
    finishTime = time.time()
    elapsed = finishTime - startTime
    status = model.getStatus()
    has_primal = False
    obj_val = None
    try:
        if status in _FEASIBLE_STATUSES:
            obj_val = model.getObjVal()
            has_primal = (obj_val is not None
                          and np.isfinite(obj_val))
    except Exception:
        has_primal = False
    print(f"  solve: {status} | obj={obj_val if has_primal else 'N/A'} "
          f"| {elapsed:.2f}s | primal={has_primal}")
    if has_primal:
        for key, var in _cons.Y_Variables.items():
            if model.getVal(var) >= 0.9:
                Y_Used.add(key)
        for key, var in _cons.Z_Variables.items():
            if model.getVal(var) >= 0.9:
                Z_Used.add(key)
    if has_primal:
        return (Y_Value_One, Z_Value_One, Y_Used, Z_Used,
                obj_val, elapsed, status)
    # No feasible primal: genuinely infeasible / no solution found.
    return Y_Value_One, Z_Value_One, Y_Used, Z_Used, 0, elapsed, status
