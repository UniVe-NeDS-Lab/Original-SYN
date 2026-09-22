import math
import argparse
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.widgets import Slider
import numpy as np


def calculate_default_limits(backlog_size, act_thr, window_ratio=3/8):
    """
    Calculate T_min and T_max window limits centered around the activation threshold.
    """
    center = act_thr * backlog_size
    half_window = (window_ratio / 2) * backlog_size
    
    t_min = math.floor(center - half_window)
    t_max = math.floor(center + half_window) + 1

    if t_min < 0:
        t_max += t_min
        t_min = 0

    return t_min, t_max


def calculate_probabilities(backlog_size, act_thr=None, t_min=None, t_max=None):
    """
    Calculate the probabilities of false positives, false negatives,
    true positives and true negatives based on the given backlog size.
    Allows specifying either or both t_min and t_max limits.
    """

    if act_thr is None:
        act_thr = 3/4
        
    # T_min and T_max defaults if not provided
    default_t_min, default_t_max = calculate_default_limits(backlog_size, act_thr)
    
    if t_min is None:
        t_min = default_t_min
    if t_max is None:
        t_max = default_t_max

    if t_max < t_min:
        return None

    # window size
    w_b = t_max - t_min + 1

    # total sample space
    total_sample_space = w_b**2

    # occurrences of false positives
    n_fp = 0
    for w in range(t_min, t_max + 1):
        for n in range(w + 1, t_max + 1):
            n_fp += 1

    # occurrences of false negatives
    n_fn = 0
    start_w = math.floor(act_thr * backlog_size)
    for w in range(start_w, t_max + 1):
        n_fn += max(0, 1 / 2 * w - t_min + 1)
    n_fn = math.floor(n_fn)

    # occurrences of true positives and true negatives
    n_tp = total_sample_space - n_fn
    n_tn = total_sample_space - n_fp

    # validate occurrences (must be within 0 and total_sample_space)
    if (
        n_fp < 0
        or n_fn < 0
        or n_tp < 0
        or n_tn < 0
        or n_fp > total_sample_space
        or n_fn > total_sample_space
        or n_tp > total_sample_space
        or n_tn > total_sample_space
    ):
        raise Exception(
f"""Invalid values were calculated:
n_fp: {n_fp} (should be >= 0)
n_fn: {n_fn} (should be >= 0)
n_tp: {n_tp} (should be >= 0)
n_tn: {n_tn} (should be >= 0)
n_fp: {n_fp} (should be <= {total_sample_space})
n_fn: {n_fn} (should be <= {total_sample_space})
n_tp: {n_tp} (should be <= {total_sample_space})
n_tn: {n_tn} (should be <= {total_sample_space})
""")


    # probabilities
    p_fp = n_fp / total_sample_space
    p_fn = n_fn / total_sample_space
    p_tp = n_tp / total_sample_space
    p_tn = n_tn / total_sample_space

    return {
        "backlog_size": backlog_size,
        "activation_threshold": act_thr,
        "T_min": t_min,
        "T_max": t_max,
        "window_size": w_b,
        "total_sample_space": total_sample_space,
        "n_fp": n_fp,
        "n_fn": n_fn,
        "n_tp": n_tp,
        "n_tn": n_tn,
        "p_fp": p_fp,
        "p_fn": p_fn,
        "p_tp": p_tp,
        "p_tn": p_tn,
    }


def sweep_window_sizes(backlog_size, act_thr=None, t_min=None, t_max=None):
    """
    Sweep across possible T_min-T_max combinations for the window
    size (fixing t_min and/or t_max if specified) and return the values that
    make the 4 probabilities as close to 0.5 as possible
    """
    best_result = None
    best_score = float("inf")

    t_min_range = [t_min] if t_min is not None else range(0, backlog_size + 1)

    # for all possible combinations
    for tm in t_min_range:
        t_max_range = (
            [t_max] if t_max is not None else range(tm + 1, backlog_size + 1)
        )
        for tx in t_max_range:
            if tx <= tm:
                continue
            result = calculate_probabilities(backlog_size, act_thr=act_thr, t_min=tm, t_max=tx)
            if result is None:
                continue
            probabilities = [
                result["p_fp"],
                result["p_fn"],
                result["p_tp"],
                result["p_tn"],
            ]

            score = sum((p - 0.5) ** 2 for p in probabilities)

            if score < best_score:
                best_score = score
                best_result = result.copy()

    if best_result is None:
        return None

    best_result["score"] = best_score

    # calculate some debug metrics
    probabilities = [
        best_result["p_fp"],
        best_result["p_fn"],
        best_result["p_tp"],
        best_result["p_tn"],
    ]
    best_result["max_distance_from_0.5"] = max(abs(p - 0.5) for p in probabilities)
    best_result["average_distance_from_0.5"] = sum(
        abs(p - 0.5) for p in probabilities
    ) / len(probabilities)

    return best_result


def add_hover_annotation(fig, ax, lines, get_res_fn):
    """Helper function to add hover annotations displaying parameters for plotted lines."""
    annot = ax.annotate(
        "",
        xy=(0, 0),
        xytext=(15, 15),
        textcoords="offset points",
        bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.9),
        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0"),
    )
    annot.set_visible(False)

    def hover(event):
        if event.inaxes == ax:
            for line in lines:
                cont, ind = line.contains(event)
                if cont:
                    idx = ind["ind"][0]
                    res = get_res_fn(idx)
                    if res:
                        x = line.get_xdata()[idx]
                        y = line.get_ydata()[idx]
                        annot.xy = (x, y)
                        text = (
                            f"{line.get_label()}\n"
                            f"Backlog Size: {res['backlog_size']}\n"
                            f"Prob: {y:.4f}\n"
                            f"T_min: {res['T_min']}, T_max: {res['T_max']}\n"
                            f"Act Thr: {res['activation_threshold']}"
                        )
                        annot.set_text(text)
                        annot.set_visible(True)
                        fig.canvas.draw_idle()
                        return
        if annot.get_visible():
            annot.set_visible(False)
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", hover)


def plot_probabilities(max_backlog_size, sweep=False, act_thr=None, t_min=None, t_max=None):
    """
    Works with 2 modes:
    - regular mode: calculate the probabilities with the given (or partial/default)
                    window limits and plot the result. When not given, the
                    limits will be calculated on the fly with the
                    usual proportions
    - sweep mode: sweeps through the backlog sizes from 1 to max_backlog_size,
                  calculating the best score for each (respecting fixed limits if given) 
                  and plotting the result
    """
    start_size = 1

    # when not sweeping and if the t_max argument has been specified,
    # values that are unreasonable, i.e. t_max that is bigger than
    # the backlog size, should not be plotted
    if t_max is not None and not sweep:
        start_size = t_max

    backlog_sizes = list(range(start_size, max_backlog_size + 1))
    valid_sizes = []
    p_tps, p_tns, p_fps, p_fns = [], [], [], []
    results_list = []

    for size in backlog_sizes:
        if sweep:
            res = sweep_window_sizes(size, act_thr=act_thr, t_min=t_min, t_max=t_max)
        else:
            res = calculate_probabilities(size, act_thr=act_thr, t_min=t_min, t_max=t_max)

        if res is None:
            continue

        valid_sizes.append(size)
        results_list.append(res)
        p_tps.append(res["p_tp"])
        p_tns.append(res["p_tn"])
        p_fps.append(res["p_fp"])
        p_fns.append(res["p_fn"])

    if not valid_sizes:
        print("No valid parameter ranges to plot")
        return

    plt.figure(figsize=(10, 6))
    (line_tp,) = plt.plot(
        valid_sizes,
        p_tps,
        label="True Positives P(TP)",
        color="green",
        linewidth=2,
    )
    (line_tn,) = plt.plot(
        valid_sizes,
        p_tns,
        label="True Negatives P(TN)",
        color="blue",
        linewidth=2,
    )
    (line_fp,) = plt.plot(
        valid_sizes,
        p_fps,
        label="False Positives P(FP)",
        color="orange",
        linewidth=2,
        linestyle="--",
    )
    (line_fn,) = plt.plot(
        valid_sizes,
        p_fns,
        label="False Negatives P(FN)",
        color="red",
        linewidth=2,
        linestyle="--",
    )

    add_hover_annotation(plt.gcf(), plt.gca(), [line_tp, line_tn, line_fp, line_fn], lambda i: results_list[i])

    title_act_thr = act_thr if act_thr is not None else "Default"
    if sweep:
        plt.title(f"Probabilities vs Backlog Size (Sweep, Threshold={title_act_thr})", fontsize=14)
    else:
        title_t_min = t_min if t_min is not None else "Dynamic"
        title_t_max = t_max if t_max is not None else "Dynamic"
        plt.title(
            f"Probabilities vs Backlog Size (T_min={title_t_min}, T_max={title_t_max}, Threshold={title_act_thr})",
            fontsize=14,
        )

    plt.xlabel("Backlog Size", fontsize=12)
    plt.ylabel("Probability", fontsize=12)
    plt.ylim(-0.05, 1.05)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plt.show()


def plot_probabilities_3d(max_backlog_size, sweep=False, act_thr=None, t_min=None, t_max=None):
    """
    Plots a 3D graph with 4 surfaces (TP, TN, FP, FN) across a range of backlog
    sizes and activation thresholds.
    """
    start_size = 1
    if t_max is not None and not sweep:
        start_size = t_max

    backlog_sizes = list(range(start_size, max_backlog_size + 1))
    act_thrs = np.linspace(0.01, 0.99, 50) if act_thr is None else [act_thr]

    B, A = np.meshgrid(backlog_sizes, act_thrs)
    Z_tp = np.full_like(B, np.nan, dtype=float)
    Z_tn = np.full_like(B, np.nan, dtype=float)
    Z_fp = np.full_like(B, np.nan, dtype=float)
    Z_fn = np.full_like(B, np.nan, dtype=float)

    for i, a in enumerate(act_thrs):
        for j, b in enumerate(backlog_sizes):
            if sweep:
                res = sweep_window_sizes(b, act_thr=a, t_min=t_min, t_max=t_max)
            else:
                res = calculate_probabilities(b, act_thr=a, t_min=t_min, t_max=t_max)

            if res is not None:
                Z_tp[i, j] = res["p_tp"]
                Z_tn[i, j] = res["p_tn"]
                Z_fp[i, j] = res["p_fp"]
                Z_fn[i, j] = res["p_fn"]

    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection="3d")

    ax.plot_surface(B, A, Z_tp, color="green", alpha=0.7)
    ax.plot_surface(B, A, Z_tn, color="blue", alpha=0.7)
    ax.plot_surface(B, A, Z_fp, color="orange", alpha=0.7)
    ax.plot_surface(B, A, Z_fn, color="red", alpha=0.7)

    legend_elements = [
        Line2D([0], [0], color="green", lw=2, label="True Positives P(TP)"),
        Line2D([0], [0], color="blue", lw=2, label="True Negatives P(TN)"),
        Line2D([0], [0], color="orange", lw=2, label="False Positives P(FP)"),
        Line2D([0], [0], color="red", lw=2, label="False Negatives P(FN)"),
    ]

    ax.set_xlabel("Backlog Size", fontsize=11)
    ax.set_ylabel("Activation Threshold", fontsize=11)
    ax.set_zlabel("Probability", fontsize=11)
    ax.set_zlim(-0.05, 1.05)

    title_mode = "Sweep" if sweep else "Dynamic/Fixed Limits"
    ax.set_title(f"3D Probabilities ({title_mode})", fontsize=14)
    ax.legend(handles=legend_elements, fontsize=10)
    plt.tight_layout()
    plt.show()


def plot_slice_2d(max_backlog_size, sweep=False, act_thr=None, t_min=None, t_max=None):
    """
    Interactive 2D slice tool. Uses a Matplotlib slider to slice 
    through activation thresholds and plot 2D probability curves dynamically.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    plt.subplots_adjust(bottom=0.20)

    start_size = t_max if (t_max is not None and not sweep) else 1
    backlog_sizes = list(range(start_size, max_backlog_size + 1))
    initial_thr = act_thr if act_thr is not None else 0.75

    (line_tp,) = ax.plot([], [], label="True Positives P(TP)", color="green", lw=2)
    (line_tn,) = ax.plot([], [], label="True Negatives P(TN)", color="blue", lw=2)
    (line_fp,) = ax.plot([], [], label="False Positives P(FP)", color="orange", lw=2, ls="--")
    (line_fn,) = ax.plot([], [], label="False Negatives P(FN)", color="red", lw=2, ls="--")

    current_results = []

    ax.set_xlim(start_size, max_backlog_size)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Backlog Size", fontsize=12)
    ax.set_ylabel("Probability", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="upper right", fontsize=11)

    ax_slider = plt.axes([0.20, 0.05, 0.65, 0.03])
    slider = Slider(
        ax=ax_slider,
        label="Activation Thr",
        valmin=0.01,
        valmax=0.99,
        valinit=initial_thr,
        valstep=0.01,
    )

    def update(val):
        nonlocal current_results
        current_thr = slider.val
        p_tps, p_tns, p_fps, p_fns = [], [], [], []
        current_results = []

        for size in backlog_sizes:
            if sweep:
                res = sweep_window_sizes(size, act_thr=current_thr, t_min=t_min, t_max=t_max)
            else:
                res = calculate_probabilities(size, act_thr=current_thr, t_min=t_min, t_max=t_max)

            if res is None:
                p_tps.append(np.nan)
                p_tns.append(np.nan)
                p_fps.append(np.nan)
                p_fns.append(np.nan)
                current_results.append(None)
            else:
                p_tps.append(res["p_tp"])
                p_tns.append(res["p_tn"])
                p_fps.append(res["p_fp"])
                p_fns.append(res["p_fn"])
                current_results.append(res)

        line_tp.set_data(backlog_sizes, p_tps)
        line_tn.set_data(backlog_sizes, p_tns)
        line_fp.set_data(backlog_sizes, p_fps)
        line_fn.set_data(backlog_sizes, p_fns)

        mode_str = "Sweep" if sweep else "Dynamic Limits"
        ax.set_title(f"2D Slice ({mode_str}) - Activation Threshold: {current_thr:.2f}", fontsize=14)
        fig.canvas.draw_idle()

    add_hover_annotation(fig, ax, [line_tp, line_tn, line_fp, line_fn], lambda i: current_results[i] if i < len(current_results) else None)

    slider.on_changed(update)
    update(initial_thr)
    plt.show()


def print_results(results, title="Calculation Results"):
    if not results:
        print("No valid results found!")
        return

    print(f"--- {title} ---")
    print(f"Backlog Size: {results['backlog_size']}")
    if "activation_threshold" in results:
        print(f"Activation Threshold: {results['activation_threshold']}")
    print(f"T_min: {results['T_min']}")
    print(f"T_max: {results['T_max']}")
    print(f"Window Size: {results['window_size']}")
    print(f"Total Sample Space: {results['total_sample_space']}")

    print("-" * 25)
    print("--- Occurrences ---")
    print(f"False Positives (n(FP)): {results['n_fp']}")
    print(f"False Negatives (n(FN)): {results['n_fn']}")
    print(f"True Positives (n(TP)):  {results['n_tp']}")
    print(f"True Negatives (n(TN)):  {results['n_tn']}")

    print("-" * 25)
    print("--- Probabilities ---")
    print(f"P(FP): {results['p_fp']:.6f}")
    print(f"P(FN): {results['p_fn']:.6f}")
    print(f"P(TP): {results['p_tp']:.6f}")
    print(f"P(TN): {results['p_tn']:.6f}")

    print("-" * 25)
    total = results["total_sample_space"]
    print("                    CLASSIFIED AS ALIVE                    CLASSIFIED AS OFFLINE")
    print(
        f"Target ALIVE    TP: {results['n_tp']} / {total} "
        f"({results['p_tp']:.6f} = {results['p_tp'] * 100:.2f}%)    "
        f"FN: {results['n_fn']} / {total} "
        f"({results['p_fn']:.6f} = {results['p_fn'] * 100:.2f}%)"
    )
    print(
        f"Target OFFLINE  FP: {results['n_fp']} / {total} "
        f"({results['p_fp']:.6f} = {results['p_fp'] * 100:.2f}%)    "
        f"TN: {results['n_tn']} / {total} "
        f"({results['p_tn']:.6f} = {results['p_tn'] * 100:.2f}%)"
    )

    if "score" in results:
        print("-" * 25)
        print("--- Sweep Score ---")
        print(f"Sum squared error:       {results['score']:.10f}")
        print(f"Max distance from 0.5:   " f"{results['max_distance_from_0.5']:.6f}")
        print(
            f"Average distance:        " f"{results['average_distance_from_0.5']:.6f}"
        )

    print("--------------------------")



if __name__ == "__main__":
    # results = calculate_probabilities(
    #         30, 3/4
    #     )
    # results = calculate_probabilities(
    #     1, 3/4, 0, 0
    # )
    # print_results(results)

    # exit()

    parser = argparse.ArgumentParser(
        description="Calculate probabilities based on backlog size",
        epilog="""
Examples:

  \033[1;36m1. Calculate the probabilities and t_min/t_max limits automatically\033[0m
     python3 probability_calculator.py 32

  \033[1;36m2. Calculate the probabilities with one or more specified t_min/t_max limits\033[0m
     python3 probability_calculator.py 64 --t_min 10 --t_max 40
     python3 probability_calculator.py 64 --t_min 10

  \033[1;36m3. Calculate the probabilities with a custom activation threshold for the mitigatioj\033[0m
     python3 probability_calculator.py 64 --act_thr 0.5 40

  \033[1;36m4. Calculate the best possible limits (optionally fixing one) for the given backlog size\033[0m
     python3 probability_calculator.py 128 --sweep
     python3 probability_calculator.py 128 --sweep --t_min 10

  \033[1;36m5. Plot the backlog sizes from 1 to 32 with dynamically calculated limits based on each backlog size\033[0m
     python3 probability_calculator.py 32 --plot

  \033[1;36m6. Plot the backlog sizes from 40 to 64, given specified limits\033[0m
     python3 probability_calculator.py 64 --plot --t_min 10 --t_max 40

  \033[1;36m7. For each backlog size, find the best t_min/t_max limits for it, then plot each one of them\033[0m
     python3 probability_calculator.py 64 --plot --sweep

  \033[1;36m8. Plot 3D surface graph across backlog sizes and activation thresholds\033[0m
     python3 probability_calculator.py 32 --plot_3d
     python3 probability_calculator.py 32 --plot_3d --sweep

  \033[1;36m. Interactive 2D slice tool with a slider for activation thresholds\033[0m
     python3 probability_calculator.py 64 --slice
     python3 probability_calculator.py 64 --slice --sweep

Notes:
  \033[2m--plot\033[0m      Plot the 2D results
  \033[2m--plot_3d\033[0m   Plot the 3D surface results
  \033[2m--slice\033[0m     Interactive 2D slice view along activation thresholds
  \033[2m--sweep\033[0m     Search for the best t_min/t_max limits
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )


    parser.add_argument("backlog_size", type=int, help="size of the backlog queue")

    parser.add_argument(
        "--t_min",
        type=int,
        required=False,
        help="lower limit for the window size",
    )

    parser.add_argument(
        "--t_max",
        type=int,
        required=False,
        help="upper limit for the window size",
    )

    parser.add_argument(
        "--act_thr",
        type=float,
        required=False,
        help="activation threshold of the mitigation. Defaults to 0.75 (or 3/4)",
    )

    parser.add_argument(
        "--sweep",
        action="store_true",
        help="try all possible window sizes and find the probabilities closest to 0.5",
    )

    parser.add_argument(
        "--plot",
        action="store_true",
        help="Go through all the possible backlog sizes and plot TP, TN, FP, and FN probabilities",
    )

    parser.add_argument(
        "--plot_3d",
        action="store_true",
        help="Plot 3D surface graph of probabilities across backlog sizes and activation thresholds",
    )

    parser.add_argument(
        "--slice",
        action="store_true",
        help="Open an interactive 2D slice tool with a slider for activation thresholds",
    )

    args = parser.parse_args()

    if args.plot_3d:
        plot_probabilities_3d(
            args.backlog_size,
            sweep=args.sweep,
            act_thr=args.act_thr,
            t_min=args.t_min,
            t_max=args.t_max,
        )
    elif args.slice:
        plot_slice_2d(
            args.backlog_size,
            sweep=args.sweep,
            act_thr=args.act_thr,
            t_min=args.t_min,
            t_max=args.t_max,
        )
    elif args.plot:
        plot_probabilities(
            args.backlog_size,
            sweep=args.sweep,
            act_thr=args.act_thr,
            t_min=args.t_min,
            t_max=args.t_max,
        )
    elif args.sweep:
        results = sweep_window_sizes(
            args.backlog_size, act_thr=args.act_thr, t_min=args.t_min, t_max=args.t_max
        )
        print_results(results, title="Best Window From Sweep")
    else:
        results = calculate_probabilities(
            args.backlog_size, args.act_thr, args.t_min, args.t_max
        )
        print_results(results)