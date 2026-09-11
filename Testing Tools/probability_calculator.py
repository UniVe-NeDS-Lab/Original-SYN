import math
import argparse
import matplotlib.pyplot as plt


def calculate_default_limits(backlog_size):
    """
    Calculate the T_min and T_max window limits based on the given backlog size
    """
    t_min = math.floor(3 / 8 * backlog_size)
    t_max = math.floor(6 / 8 * backlog_size) + 1
    return t_min, t_max


def calculate_probabilities(backlog_size, t_min=None, t_max=None):
    """
    Calculate the probabilities of false positives, false negatives,
    true positives and true negatives based on the given backlog size
    """
    # T_min and T_max
    if t_min is None or t_max is None:
        t_min, t_max = calculate_default_limits(backlog_size)

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
    start_w = math.floor(3 / 4 * backlog_size)
    for w in range(start_w, t_max + 1):
        n_fn += 1 / 2 * w - t_min + 1
    n_fn = math.floor(n_fn)

    # occurrences of true positives and true negatives
    n_tp = total_sample_space - n_fn
    n_tn = total_sample_space - n_fp

    # probabilities
    p_fp = n_fp / total_sample_space
    p_fn = n_fn / total_sample_space
    p_tp = n_tp / total_sample_space
    p_tn = n_tn / total_sample_space

    return {
        "backlog_size": backlog_size,
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


def sweep_window_sizes(backlog_size):
    """
    Sweep across all possible T_min-T_max combinations for the window
    size and return the values that make the 4 probabilities as close
    to 0.5 as possible
    """
    best_result = None
    best_score = float("inf")

    # for all possible combinations
    for t_min in range(0, backlog_size + 1):
        for t_max in range(t_min + 1, backlog_size + 1):
            result = calculate_probabilities(backlog_size, t_min=t_min, t_max=t_max)
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


def plot_probabilities(max_backlog_size, sweep=False, t_min=None, t_max=None):
    """
    Works with 2 modes:
    - regular mode: calculate the probabilities with the given (or not)
                    window limits and plot the result. When not given, the
                    limits will be calculated on the fly with the
                    usual proportions
    - sweep mode: sweeps through the backlog sizes from 1 to max_backlog_size,
                  calculate the best score for each and plot the result
    """
    start_size = 1

    # when not sweeping and if the t_max argument has been specified,
    # values that are unreasonable, i.e. t_max that is bigger than
    # the backlog size, should not be plotted
    if t_max is not None and not sweep:
        start_size = t_max

    backlog_sizes = list(range(start_size, max_backlog_size + 1))
    p_tps, p_tns, p_fps, p_fns = [], [], [], []

    for size in backlog_sizes:
        if sweep:
            res = sweep_window_sizes(size)
        else:
            res = calculate_probabilities(size, t_min, t_max)

        p_tps.append(res["p_tp"])
        p_tns.append(res["p_tn"])
        p_fps.append(res["p_fp"])
        p_fns.append(res["p_fn"])

    plt.figure(figsize=(10, 6))
    plt.plot(
        backlog_sizes,
        p_tps,
        label="True Positives P(TP)",
        color="green",
        linewidth=2,
    )
    plt.plot(
        backlog_sizes,
        p_tns,
        label="True Negatives P(TN)",
        color="blue",
        linewidth=2,
    )
    plt.plot(
        backlog_sizes,
        p_fps,
        label="False Positives P(FP)",
        color="orange",
        linewidth=2,
        linestyle="--",
    )
    plt.plot(
        backlog_sizes,
        p_fns,
        label="False Negatives P(FN)",
        color="red",
        linewidth=2,
        linestyle="--",
    )

    if sweep:
        plt.title(f"Probabilities vs Backlog Size (Sweep)", fontsize=14)
    else:
        title_t_min = t_min if t_min is not None else "Dynamic"
        title_t_max = t_max if t_max is not None else "Dynamic"
        plt.title(
            f"Probabilities vs Backlog Size (T_min={title_t_min}, T_max={title_t_max})",
            fontsize=14,
        )

    plt.xlabel("Backlog Size", fontsize=12)
    plt.ylabel("Probability", fontsize=12)
    plt.ylim(-0.05, 1.05)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plt.show()


def print_results(results, title="Calculation Results"):
    print(f"--- {title} ---")
    print(f"Backlog Size: {results['backlog_size']}")
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
    print("                 ALIVE                                  OFFLINE")
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
    parser = argparse.ArgumentParser(
        description="Calculate probabilities based on backlog size",
        epilog="""
Examples:

  \033[1;36m1. Calculate the probabilities and t_min/t_max limits automatically\033[0m
     python3 probability_calculator.py 32

  \033[1;36m2. Calculate the probabilities with specified t_min/t_max limits\033[0m
     python3 probability_calculator.py 64 --t_min 10 --t_max 40

  \033[1;36m3. Calculate the best possible limits for the given backlog size, then print the found limits and probabilities\033[0m
     python3 probability_calculator.py 128 --sweep

  \033[1;36m4. Plot the backlog sizes from 1 to 32 with dynamically calculated limits based on each backlog size\033[0m
     python3 probability_calculator.py 32 --plot

  \033[1;36m5. Plot the backlog sizes from 40 to 64, given that t_min and t_max were specified and the other values would have been wrong\033[0m
     python3 probability_calculator.py 64 --plot --t_min 10 --t_max 40

  \033[1;36m6. For each backlog size, find the best t_min/t_max limits for it, then plot each one of them\033[0m
     python3 probability_calculator.py 64 --plot --sweep

Notes:
  \033[2m--plot\033[0m   Plot the results
  \033[2m--sweep\033[0m  Search for the best t_min/t_max limits
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
        "--sweep",
        action="store_true",
        help="try all possible window sizes and find the probabilities closest to 0.5",
    )

    parser.add_argument(
        "--plot",
        action="store_true",
        help="Go through all the possible backlog sizes and plot TP, TN, FP, and FN probabilities",
    )

    args = parser.parse_args()

    if args.plot:
        plot_probabilities(
            args.backlog_size,
            sweep=args.sweep,
            t_min=args.t_min,
            t_max=args.t_max,
        )
    elif args.sweep:
        results = sweep_window_sizes(args.backlog_size)
        print_results(results, title="Best Window From Sweep")
    else:
        results = calculate_probabilities(args.backlog_size, args.t_min, args.t_max)
        print_results(results)
