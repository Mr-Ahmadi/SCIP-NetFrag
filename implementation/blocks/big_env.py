"""Single FlexINA solve on large clustered envs, no time limit.

Runs the standard per-slot FlexINA SCIP solves over each env's dict_list
(one fragment per worker per slot), carrying Y_Used/Z_Used across slots —
no time limit, no iterations, no model sweep — and saves the JSON log.

Envs: env_3c_15sw_4f (15 switches), env_4c_20sw_4f (20 switches) and
env_5c_25sw_4f (25 switches), solved back to back. All three share the same
wiring pattern (2 ToR pairs + 2 aggregation switches per cluster, one core
switch per cluster carrying "PS"), so the series isolates topology size.
rho/tau_F follow the inart run (percentage=0.5, T_max_2=8, addTime factor
1.0).

Emits one scaling plot: packets (bars, left axis) and total solve runtime
(line, right axis, log) versus topology size.
"""
from blocks._flexina_helpers import _solve_flexina_once
from blocks._imports import (
    BlockRun, LEGEND_SIZE, XLEN_TOPOLOGY, YLEN_FRAG, YLEN_RUNTIME_LOG,
    _prepare_dict_list, _unpack_env, apply_plot_style, env_3c_15sw_4f,
    env_4c_20sw_4f, env_5c_25sw_4f, env_labels, fmt_axis, new_fig, np,
    plot_grid, plot_legend, save_fig, sns, style, time,
)

ENVS = [env_3c_15sw_4f, env_4c_20sw_4f, env_5c_25sw_4f]
MODEL_LABEL = "FlexINA"
MAX_AGGREGATION = 4
PERCENTAGE = 0.5               # rho per the inart run
T_MAX_1_INIT = 0
T_MAX_2_INIT = 8               # tau_F per the inart run
ADD_TIME_FACTOR = 1.0
SOLVE_TIMEOUT_S = None          # no time limit

PACKET_COLOR = 1                # FlexINA color across all blocks
RUNTIME_COLOR = 5
PACKET_HATCH = "."
PLOT_FILE = "plots/big_env_scaling.pdf"


def _plot_scaling(x_labels, packets, runtimes):
    """One figure: packets as bars (left), runtime as a log line (right)."""
    apply_plot_style()
    cmap = sns.color_palette(style.palette)
    fig, ax = new_fig()

    x = np.arange(len(x_labels))
    bars = ax.bar(x, packets, 0.5, color=cmap[PACKET_COLOR],
                  edgecolor='black', hatch=PACKET_HATCH, label=YLEN_FRAG)
    for rect, val in zip(bars, packets):
        ax.annotate(f"{int(val)}", (rect.get_x() + rect.get_width() / 2,
                                    rect.get_height()),
                    textcoords="offset points", xytext=(0, 4),
                    ha='center', fontsize=style.tick_size)

    ax.set_xlabel(XLEN_TOPOLOGY)
    ax.set_ylabel(YLEN_FRAG)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels)
    ax.set_ylim(0, max(packets) * 1.18)
    fmt_axis(ax)
    plot_grid(ax)

    ax2 = ax.twinx()
    line, = ax2.plot(x, runtimes, ls='dashed', marker='p',
                     markersize=style.marker_size, color=cmap[RUNTIME_COLOR],
                     label=YLEN_RUNTIME_LOG)
    ax2.set_yscale('log')
    ax2.set_ylabel(YLEN_RUNTIME_LOG)

    plot_legend(ax, handles=[bars, line], labels=[YLEN_FRAG, YLEN_RUNTIME_LOG],
                loc='upper left', size=LEGEND_SIZE)
    save_fig(fig, PLOT_FILE)


def run_big_env():
    x_labels = env_labels(ENVS)
    packets_by_env, runtime_by_env, switches_by_env = [], [], []

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
             "y_runtime": YLEN_RUNTIME_LOG, "x_ticks": x_labels})

    block_start = time.time()
    for ENV in ENVS:
        x_label = env_labels([ENV])[0]
        env_tuple = _unpack_env(ENV)
        fragmentsofEachWorker, totalWorkers = env_tuple[9], env_tuple[10]
        pSwitchesNumber = env_tuple[3]
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

        packets_by_env.append(numPackets)
        runtime_by_env.append(RuntimeTotal)
        switches_by_env.append(pSwitchesNumber)

        print(f"\n>>> Single FlexINA solve on {ENV.__name__} complete: "
              f"{numPackets} packets, {RuntimeTotal:.2f}s total runtime "
              f"(construction {construction_total:.2f}s).")

    print(f"\n[big_env] all envs done in {time.time() - block_start:.1f}s.")

    _plot_scaling(x_labels, packets_by_env, runtime_by_env)

    # The per-slot rows are cumulative, so the plotted totals are the last row
    # per env — record them explicitly rather than letting summary() average.
    summary = {
        "labels": list(x_labels),
        "series": [{
            "model": MODEL_LABEL,
            "packets_mean": packets_by_env,
            "packets_std": [0.0] * len(packets_by_env),
            "runtime_mean": runtime_by_env,
            "runtime_std": [0.0] * len(runtime_by_env),
        }],
        "switches": switches_by_env,
        "axis": {"x": XLEN_TOPOLOGY, "y_fragments": YLEN_FRAG,
                 "y_runtime": YLEN_RUNTIME_LOG},
    }
    run.save("plots/big_env_data.json", extra={"summary": summary,
                                               "plot_files": [PLOT_FILE]})
    print(f"Saved plots/big_env_data.json and {PLOT_FILE}")
