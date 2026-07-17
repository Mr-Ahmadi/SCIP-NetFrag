"""
Objective function and problem solver.
Moved verbatim from the original Accelerating_New.py.
"""
import time


def objective(Y_Variables, model):
    Y_Variables_Array = [Y_Variables[yParam] for yParam in Y_Variables]
    model.setObjective(sum(Y_Variables_Array), "minimize")


def solveProblem(model, Y_Used, Z_Used):
    from . import constraints as _cons

    Y_Value_One = []
    Z_Value_One = []
    model.setParam("parallel/maxnthreads", 8)
    startTime = time.time()
    model.optimize()
    finishTime = time.time()
    elapsed = finishTime - startTime
    status = model.getStatus()
    print(f"  solve: {status} | obj={model.getObjVal() if status == 'optimal' else 'N/A'} | {elapsed:.2f}s")
    if status == "optimal":
        for key, var in _cons.Y_Variables.items():
            if model.getVal(var) >= 0.9:
                Y_Used.append(key)
        for key, var in _cons.Z_Variables.items():
            if model.getVal(var) >= 0.9:
                Z_Used.append(key)
    if status == "optimal":
        return Y_Value_One, Z_Value_One, Y_Used, Z_Used, model.getObjVal(), elapsed, status
    else:
        return Y_Value_One, Z_Value_One, Y_Used, Z_Used, 0, elapsed, "infeasible"
