"""Single FlexINA solve on large clustered envs, no time limit.

Runs the standard per-slot FlexINA SCIP solves over each env's dict_list
(one fragment per worker per slot), carrying Y_Used/Z_Used across slots —
no time limit, no iterations, no model sweep — and saves the JSON log.

Envs: env_4c_20sw_4f (20 switches) and env_5c_25sw_4f (25 switches),
solved back to back. rho/tau_F follow the inart run (percentage=0.5,
T_max_2=8, addTime factor 1.0).
"""
from blocks._flexina_helpers import _solve_flexina_once
from blocks._imports import (
    BlockRun, XLEN_TOPOLOGY, YLEN_FRAG, YLEN_RUNTIME, _prepare_dict_list,
    _unpack_env, env_4c_20sw_4f, env_5c_25sw_4f, env_labels, time,
)

ENVS = [env_4c_20sw_4f, env_5c_25sw_4f]
MODEL_LABEL = "FlexINA"
MAX_AGGREGATION = 4
PERCENTAGE = 0.5               # rho per the inart run
T_MAX_1_INIT = 0
T_MAX_2_INIT = 8               # tau_F per the inart run
ADD_TIME_FACTOR = 1.0
SOLVE_TIMEOUT_S = None          # no time limit


def run_big_env():
    x_labels = env_labels(ENVS)

    run = BlockRun("big_env", config={
        "envs": [e.__name__ for e in ENVS],
        "model": MODEL_LABEL,
        "max_aggregation": MAX_AGGREGATION,
        "percentage": PERCENTAGE,
        "T_max_1_init": T_MAX_1_INIT,
        "T_max_2_init": T_MAX_2_INIT,
        "addTime_factor": ADD_TIME_FACTOR,
        "solve_timeout_s": None,
        "note": ("Single FlexINA solve per env: per-slot SCIP solves over "
                 "dict_list (one fragment per worker per slot) with "
                 "Y_Used/Z_Used carried across slots. No time limit. "
                 "rho=0.5 and tau_F=8 (T_max_2_init, addTime factor 1.0) "
                 "follow the inart run."),
    }, axis={"x": XLEN_TOPOLOGY, "y_fragments": YLEN_FRAG,
             "y_runtime": YLEN_RUNTIME, "x_ticks": x_labels})

    block_start = time.time()
    for ENV in ENVS:
        x_label = env_labels([ENV])[0]
        env_tuple = _unpack_env(ENV)
        fragmentsofEachWorker, totalWorkers = env_tuple[9], env_tuple[10]
        dict_list = _prepare_dict_list(fragmentsofEachWorker, totalWorkers)

        T_max_1 = T_MAX_1_INIT
        T_max_2 = T_MAX_2_INIT
        addTime = int(ADD_TIME_FACTOR * T_max_2)
        Y_Used, Z_Used = set(), set()
        numPackets = 0
        RuntimeTotal = 0.0
        construction_total = 0.0
        solve_total = 0.0
        statuses = []
        any_failed = False

        print(f"[big_env] {ENV.__name__} — {len(dict_list)} slot(s), "
              f"max_aggregation={MAX_AGGREGATION}, percentage={PERCENTAGE}, "
              f"no time limit.")
        for items in range(len(dict_list)):
            print(f"  slot={items}/{len(dict_list)} ... ", end="", flush=True)
            (numPacket, Runtime, status, Y_Used, Z_Used,
             timed_out, construction_time) = _solve_flexina_once(
                env_tuple, dict_list[items], MAX_AGGREGATION,
                T_max_1, T_max_2, PERCENTAGE, timeout_sec=SOLVE_TIMEOUT_S)
            construction_total += construction_time
            solve_total += Runtime
            statuses.append(status)
            print(f"{status} pkts={numPacket} {Runtime:.3f}s"
                  + (" (no incumbent)" if timed_out else ""))
            any_failed = any_failed or timed_out

            if not timed_out:
                T_max_1 += addTime
                T_max_2 += addTime
            numPackets += numPacket
            RuntimeTotal += Runtime
            run.observe(
                model=MODEL_LABEL,
                env=ENV.__name__, x=x_label, ittr=0,
                packets=numPackets, runtime=RuntimeTotal,
                construction_time_s=construction_total,
                solve_time_s=solve_total,
                status=",".join(statuses),
                slot=items,
                timed_out_any=any_failed,
                not_proven_optimal_any=any(
                    s in ("timelimit", "gaplimit", "nodelimit",
                          "sollimit", "stallnodelimit")
                    for s in statuses))

        print(f"\n>>> Single FlexINA solve on {ENV.__name__} complete: "
              f"{numPackets} packets, {RuntimeTotal:.2f}s total runtime "
              f"(construction {construction_total:.2f}s).")

    print(f"\n[big_env] all envs done in {time.time() - block_start:.1f}s.")

    summary = run.summary(x_labels, series_order=[MODEL_LABEL],
                          y_fragments=YLEN_FRAG, y_runtime=YLEN_RUNTIME,
                          x_label=XLEN_TOPOLOGY)
    run.save("plots/big_env_data.json", extra={"summary": summary,
                                               "plot_files": []})
    print("Saved plots/big_env_data.json")
