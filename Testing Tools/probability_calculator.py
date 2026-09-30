import math
import argparse
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter
from matplotlib.widgets import Slider, CheckButtons
import numpy as np


def parse_limit(val, backlog_size):
    """
    Given the backlog size and the value to parse, calculate the actual
    number for it. E.g. for backlog_size=20:
     - val=0.1  -> ret 2
     - val=50%  -> ret 10
     - val=4    -> ret 4
     - val=None -> ret None
    """
    if val is None:
        return None
    if isinstance(val, str):
        val = float(val.rstrip("%")) / 100.0 if "%" in val else float(val)
    if isinstance(val, float) and val <= 1.0:
        return int(round(val * backlog_size))
    return int(val)


def is_pct_val(val):
    """
    Return True if the given string is a percentage
    """
    if val is None:
        return False
    if isinstance(val, str):
        val = float(val.rstrip("%")) / 100.0 if "%" in val else float(val)
    return isinstance(val, float) and val <= 1.0


def format_pct(val, decimals=2):
    """
    Format a ratio (float value between 0 and 1) as a percentage
    """
    if val is None or val == "INOP":
        return "INOP" if val == "INOP" else "None"
    return f"{float(val) * 100:.{decimals}f}%"


def calculate_default_limits(backlog_size, window_center, window_ratio=3 / 8):
    """
    Calculate T_min and T_max window limits centered around the window center threshold
    """
    center = window_center * backlog_size
    half_window = (window_ratio / 2) * backlog_size

    t_min = math.floor(center - half_window)
    t_max = math.floor(center + half_window) + 1

    if t_min < 0:
        t_max += t_min
        t_min = 0

    if t_max > backlog_size:
        t_min -= t_max - backlog_size
        t_max = backlog_size

    t_min = max(0, t_min)
    # t_max = min(t_max, backlog_size)

    return t_min, t_max


def calculate_probabilities(
    backlog_size, act_thr=None, window_center=None, t_min=None, t_max=None
):
    """
    Calculate the probabilities of false positives, false negatives,
    true positives and true negatives based on the given backlog size.
    Allows specifying either or both t_min and t_max limits as well as a separate
    window_center for dynamic limit calculations.
    """
    t_min = parse_limit(t_min, backlog_size)
    t_max = parse_limit(t_max, backlog_size)

    if act_thr is None:
        act_thr = 18 / 32

    if window_center is None:
        window_center = act_thr

    # flag set when the automatic t_min/t_max centering was used
    center_inop = t_min is not None and t_max is not None

    # T_min and T_max defaults if not provided
    default_t_min, default_t_max = calculate_default_limits(backlog_size, window_center)

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
        raise Exception(f"""Invalid values were calculated:
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
        "window_center": "INOP" if center_inop else window_center,
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


def calculate_probabilities_timeout(
    backlog_size, act_thr=None, window_center=None, t_min=None, t_max=None
):
    """
    Calculate the probabilities for the 'window_timeout' scenario using
    the provided formula based on the window size w(B).
    """
    t_min = parse_limit(t_min, backlog_size)
    t_max = parse_limit(t_max, backlog_size)

    if act_thr is None:
        act_thr = 18 / 32

    if window_center is None:
        window_center = act_thr

    center_inop = t_min is not None and t_max is not None

    default_t_min, default_t_max = calculate_default_limits(backlog_size, window_center)

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

    # probabilities derived directly from the formulas
    p_tp = 0.5 - (1 / (2 * w_b))
    p_fn = (1 / (2 * w_b)) + 0.5
    p_fp = 0.5 - (1 / (2 * w_b))
    p_tn = (1 / (2 * w_b)) + 0.5

    # deriving the corresponding occurrences matching the sample space proportion
    n_tp = int((w_b * (w_b - 1)) / 2)
    n_fp = int((w_b * (w_b - 1)) / 2)
    n_fn = int((w_b * (w_b + 1)) / 2)
    n_tn = int((w_b * (w_b + 1)) / 2)

    return {
        "backlog_size": backlog_size,
        "activation_threshold": act_thr,
        "window_center": "INOP" if center_inop else window_center,
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


def calculate_bayes_probabilities(results, base_prob=0.5):
    """
    Calculates the Bayesian probabilities for the attacker's perspective
    given a base prior probability: P(Alive) = base_prob, P(Not Alive) = 1 - base_prob
    Note that this appends the inferences to the results dictionary!
    """
    if results is None:
        return None

    if isinstance(base_prob, str):
        base_prob = (
            float(base_prob.rstrip("%")) / 100.0
            if "%" in base_prob
            else float(base_prob)
        )

    p_tp = results["p_tp"]
    p_tn = results["p_tn"]
    p_fp = results["p_fp"]
    p_fn = results["p_fn"]

    # How the probabilities are "arranged"
    #
    #                                - p_tp -> Classified Alive (TP)
    #                               /
    #      base_prob  ->   Alive   -
    #   /                           \
    #  /                             - p_fn -> Classified Not Alive (FN)
    # -
    #  \                             - p_fp -> Classified Alive (FP)
    #   \                           /
    #     1-base_prob -> Not Alive -
    #                               \
    #                                - p_tn -> Classified Not Alive (TN)

    # Denominators
    den_a = (base_prob * p_tp) + ((1.0 - base_prob) * p_fp)
    den_na = (base_prob * p_fn) + ((1.0 - base_prob) * p_tn)

    # P(Alive | Classified Alive)
    results["b_p_aa"] = (p_tp * base_prob) / den_a if den_a > 0 else float("nan")
    # P(Not Alive | Classified Alive)
    results["b_p_naa"] = (
        (p_fp * (1.0 - base_prob)) / den_a if den_a > 0 else float("nan")
    )
    # P(Alive | Classified Not Alive)
    results["b_p_ana"] = (p_fn * base_prob) / den_na if den_na > 0 else float("nan")
    # P(Not Alive | Classified Not Alive)
    results["b_p_nana"] = (
        (p_tn * (1.0 - base_prob)) / den_na if den_na > 0 else float("nan")
    )

    results["b_base_prob"] = base_prob

    return results


def sweep_window_sizes(
    backlog_size, act_thr=None, window_center=None, t_min=None, t_max=None
):
    """
    Sweep across possible T_min-T_max size combinations for the window
    size (fixing t_min and/or t_max if specified) and return the values that
    make the 4 probabilities as close to 0.5 as possible
    """
    t_min = parse_limit(t_min, backlog_size)
    t_max = parse_limit(t_max, backlog_size)

    best_result = None
    best_score = float("inf")

    t_min_range = [t_min] if t_min is not None else range(0, backlog_size + 1)

    # for all possible combinations
    for tm in t_min_range:
        t_max_range = [t_max] if t_max is not None else range(tm + 1, backlog_size + 1)
        for tx in t_max_range:
            if tx <= tm:
                continue
            result = calculate_probabilities(
                backlog_size,
                act_thr=act_thr,
                window_center=window_center,
                t_min=tm,
                t_max=tx,
            )
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


def sweep_window_sizes_timeout(
    backlog_size, act_thr=None, window_center=None, t_min=None, t_max=None
):
    """
    Sweep for the window_timeout scenario, returning the values that
    make the 4 probabilities as close to 0.5 as possible
    """
    t_min = parse_limit(t_min, backlog_size)
    t_max = parse_limit(t_max, backlog_size)

    best_result = None
    best_score = float("inf")

    t_min_range = [t_min] if t_min is not None else range(0, backlog_size + 1)

    # for all possible combinations
    for tm in t_min_range:
        t_max_range = [t_max] if t_max is not None else range(tm + 1, backlog_size + 1)
        for tx in t_max_range:
            if tx <= tm:
                continue
            result = calculate_probabilities_timeout(
                backlog_size,
                act_thr=act_thr,
                window_center=window_center,
                t_min=tm,
                t_max=tx,
            )
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
                            f"Act Thr: {format_pct(res['activation_threshold'])}\n"
                            f"Window Center: {format_pct(res.get('window_center', res['activation_threshold']))}"
                        )
                        annot.set_text(text)
                        annot.set_visible(True)
                        fig.canvas.draw_idle()
                        return
        if annot.get_visible():
            annot.set_visible(False)
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", hover)


def plot_probabilities(
    max_backlog_size,
    scenario="window",
    sweep=False,
    act_thr=None,
    window_center=None,
    t_min=None,
    t_max=None,
):
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
    scen_data = SCENARIOS[scenario]

    # when not sweeping and if the t_max argument has been specified,
    # values that are unreasonable, i.e. t_max that is bigger than
    # the backlog size and isn't a percentage, should not be plotted
    if t_max is not None and not sweep and not is_pct_val(t_max):
        start_size = parse_limit(t_max, max_backlog_size)

    backlog_sizes = list(range(start_size, max_backlog_size + 1))
    valid_sizes = []
    p_tps, p_tns, p_fps, p_fns = [], [], [], []
    results_list = []

    for size in backlog_sizes:
        if sweep:
            res = scen_data["sweep_fn"](
                size,
                act_thr=act_thr,
                window_center=window_center,
                t_min=t_min,
                t_max=t_max,
            )
        else:
            res = scen_data["calc_fn"](
                size,
                act_thr=act_thr,
                window_center=window_center,
                t_min=t_min,
                t_max=t_max,
            )

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

    add_hover_annotation(
        plt.gcf(),
        plt.gca(),
        [line_tp, line_tn, line_fp, line_fn],
        lambda i: results_list[i],
    )

    title_act_thr = format_pct(act_thr) if act_thr is not None else "Default"
    if window_center is not None:
        title_window_center = format_pct(window_center)
    elif act_thr is not None:
        title_window_center = format_pct(act_thr)
    else:
        title_window_center = "Default"
    if sweep:
        plt.title(
            f"[{scen_data['title']}] Probabilities vs Backlog Size (Sweep, Threshold={title_act_thr})",
            fontsize=14,
        )
    else:
        title_t_min = t_min if t_min is not None else "Dynamic"
        title_t_max = t_max if t_max is not None else "Dynamic"
        plt.title(
            f"[{scen_data['title']}] Probabilities vs Backlog Size (T_min={title_t_min}, T_max={title_t_max}, Threshold={title_act_thr}, Window Center={title_window_center})",
            fontsize=14,
        )

    plt.xlabel("Backlog Size", fontsize=12)
    plt.ylabel("Probability", fontsize=12)
    plt.ylim(-0.05, 1.05)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plt.show()


def plot_probabilities_bayes(
    max_backlog_size,
    scenario="window",
    sweep=False,
    act_thr=None,
    window_center=None,
    t_min=None,
    t_max=None,
    base_prob=0.5,
):
    """
    Plots the probabilities from the attacker's perspective using Bayes' theorem given a base probability.
    """
    start_size = 1
    scen_data = SCENARIOS[scenario]

    # when not sweeping and if the t_max argument has been specified,
    # values that are unreasonable, i.e. t_max that is bigger than
    # the backlog size and isn't a percentage, should not be plotted
    if t_max is not None and not sweep and not is_pct_val(t_max):
        start_size = parse_limit(t_max, max_backlog_size)

    backlog_sizes = list(range(start_size, max_backlog_size + 1))
    valid_sizes = []

    # Bayesian perspective probabilities
    b_p_aa, b_p_naa, b_p_ana, b_p_nana = [], [], [], []
    results_list = []

    for size in backlog_sizes:
        if sweep:
            res = scen_data["sweep_fn"](
                size,
                act_thr=act_thr,
                window_center=window_center,
                t_min=t_min,
                t_max=t_max,
            )
        else:
            res = scen_data["calc_fn"](
                size,
                act_thr=act_thr,
                window_center=window_center,
                t_min=t_min,
                t_max=t_max,
            )

        if res is None:
            continue

        res = calculate_bayes_probabilities(res, base_prob=base_prob)

        valid_sizes.append(size)
        results_list.append(res)

        b_p_aa.append(res["b_p_aa"])
        b_p_naa.append(res["b_p_naa"])
        b_p_ana.append(res["b_p_ana"])
        b_p_nana.append(res["b_p_nana"])

    if not valid_sizes:
        print("No valid parameter ranges to plot")
        return

    plt.figure(figsize=(10, 6))
    (line_aa,) = plt.plot(
        valid_sizes,
        b_p_aa,
        label="P(Alive | Classified Alive)",
        color="green",
        linewidth=2,
    )
    (line_nana,) = plt.plot(
        valid_sizes,
        b_p_nana,
        label="P(Not Alive | Classified Not Alive)",
        color="blue",
        linewidth=2,
    )
    (line_naa,) = plt.plot(
        valid_sizes,
        b_p_naa,
        label="P(Not Alive | Classified Alive)",
        color="orange",
        linewidth=2,
        linestyle="--",
    )
    (line_ana,) = plt.plot(
        valid_sizes,
        b_p_ana,
        label="P(Alive | Classified Not Alive)",
        color="red",
        linewidth=2,
        linestyle="--",
    )

    add_hover_annotation(
        plt.gcf(),
        plt.gca(),
        [line_aa, line_nana, line_naa, line_ana],
        lambda i: results_list[i],
    )

    title_act_thr = format_pct(act_thr) if act_thr is not None else "Default"
    if window_center is not None:
        title_window_center = format_pct(window_center)
    elif act_thr is not None:
        title_window_center = format_pct(act_thr)
    else:
        title_window_center = "Default"

    if sweep:
        plt.title(
            f"[{scen_data['title']}] Attacker Inference (Bayes) vs Backlog Size\n"
            f"(Sweep, Threshold={title_act_thr})",
            fontsize=14,
        )
    else:
        title_t_min = t_min if t_min is not None else "Dynamic"
        title_t_max = t_max if t_max is not None else "Dynamic"
        plt.title(
            f"[{scen_data['title']}] Attacker Inference (Bayes) vs Backlog Size\n"
            f"(T_min={title_t_min}, T_max={title_t_max}, Thr={title_act_thr}, Center={title_window_center})",
            fontsize=14,
        )

    plt.xlabel("Backlog Size", fontsize=12)
    plt.ylabel("Inferred Probability (Attacker View)", fontsize=12)
    plt.ylim(-0.05, 1.05)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plt.show()

def plot_whiskers(
    backlog_size,
    scenario="window",
    max_delta_pct=0.20,
    t_min=None,
    t_max=None,
):
    """
    Plots probabilities against threshold percentage (X axis) with a shaded range (whisker/delta band)
    obtained by sweeping T_min and T_max in [threshold - delta, threshold + delta] with delta up to 20%.
    """
    scen_data = SCENARIOS[scenario]
    act_thrs = np.linspace(0.01, 0.99, 100)

    nominal_tp, nominal_tn, nominal_fp, nominal_fn = [], [], [], []
    min_tp, max_tp = [], []
    min_tn, max_tn = [], []
    min_fp, max_fp = [], []
    min_fn, max_fn = [], []

    for thr in act_thrs:
        # Reminder that the act_thr will be used to center the window with 
        # automatically calculated t_min/t_max values when not specified
        res_nom = scen_data["calc_fn"](
            backlog_size, act_thr=thr, t_min=t_min, t_max=t_max
        )
        if res_nom is not None:
            nominal_tp.append(res_nom["p_tp"])
            nominal_tn.append(res_nom["p_tn"])
            nominal_fp.append(res_nom["p_fp"])
            nominal_fn.append(res_nom["p_fn"])
        else:
            nominal_tp.append(np.nan)
            nominal_tn.append(np.nan)
            nominal_fp.append(np.nan)
            nominal_fn.append(np.nan)

        # Sweep bounds for t_min/t_max with ±20% of delta
        lower_bound = max(0, int(math.floor((thr - max_delta_pct) * backlog_size)))
        upper_bound = min(
            backlog_size, int(math.ceil((thr + max_delta_pct) * backlog_size))
        )

        # Get samples for all the probabilities calculated with the various thresholds
        tps, tns, fps, fns = [], [], [], []

        for tm in range(lower_bound, upper_bound + 1):
            for tx in range(tm + 1, upper_bound + 1):
                res = scen_data["calc_fn"](
                    backlog_size, act_thr=thr, t_min=tm, t_max=tx
                )
                if res is not None:
                    tps.append(res["p_tp"])
                    tns.append(res["p_tn"])
                    fps.append(res["p_fp"])
                    fns.append(res["p_fn"])

        min_tp.append(min(tps))
        max_tp.append(max(tps))
        min_tn.append(min(tns))
        max_tn.append(max(tns))
        min_fp.append(min(fps))
        max_fp.append(max(fps))
        min_fn.append(min(fns))
        max_fn.append(max(fns))

    x_pct = act_thrs * 100

    plt.figure(figsize=(10, 6))

    plt.plot(x_pct, nominal_tp, label="True Positives P(TP)", color="green", linewidth=2)
    plt.fill_between(x_pct, min_tp, max_tp, color="green", alpha=0.2)

    plt.plot(x_pct, nominal_tn, label="True Negatives P(TN)", color="blue", linewidth=2)
    plt.fill_between(x_pct, min_tn, max_tn, color="blue", alpha=0.2)

    plt.plot(
        x_pct,
        nominal_fp,
        label="False Positives P(FP)",
        color="orange",
        linewidth=2,
        linestyle="--",
    )
    plt.fill_between(x_pct, min_fp, max_fp, color="orange", alpha=0.2)

    plt.plot(
        x_pct,
        nominal_fn,
        label="False Negatives P(FN)",
        color="red",
        linewidth=2,
        linestyle="--",
    )
    plt.fill_between(x_pct, min_fn, max_fn, color="red", alpha=0.2)

    plt.title(
        f"[{scen_data['title']}] Probabilities vs Threshold Percentage\n"
        f"(Backlog Size={backlog_size}, Delta=±20%)",
        fontsize=14,
    )
    plt.xlabel("Activation Threshold (%)", fontsize=12)
    plt.ylabel("Probability", fontsize=12)
    plt.ylim(-0.05, 1.05)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(fontsize=11)
    plt.tight_layout()
    plt.show()

def plot_probabilities_3d(
    max_backlog_size,
    scenario="window",
    sweep=False,
    act_thr=None,
    window_center=None,
    t_min=None,
    t_max=None,
):
    """
    Plots a 3D graph with 4 surfaces (TP, TN, FP, FN) across a range of backlog
    sizes and activation thresholds.
    """
    start_size = 1
    scen_data = SCENARIOS[scenario]

    if t_max is not None and not sweep and not is_pct_val(t_max):
        start_size = parse_limit(t_max, max_backlog_size)

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
                res = scen_data["sweep_fn"](
                    b, act_thr=a, window_center=window_center, t_min=t_min, t_max=t_max
                )
            else:
                res = scen_data["calc_fn"](
                    b, act_thr=a, window_center=window_center, t_min=t_min, t_max=t_max
                )

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
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_zlabel("Probability", fontsize=11)
    ax.set_zlim(-0.05, 1.05)

    title_mode = "Sweep" if sweep else "Dynamic/Fixed Limits"
    if window_center is not None:
        title_center = format_pct(window_center)
    elif act_thr is not None:
        title_center = format_pct(act_thr)
    else:
        title_center = "Default"
    ax.set_title(
        f"[{scen_data['title']}] 3D Probabilities ({title_mode}) "
        f"(Window Center={title_center})",
        fontsize=14,
    )
    ax.legend(handles=legend_elements, fontsize=10)
    plt.tight_layout()
    plt.show()


def plot_sliders(
    max_backlog_size,
    scenario="window",
    sweep=False,
    act_thr=None,
    window_center=None,
    t_min=None,
    t_max=None,
):
    """
    Uses Matplotlib sliders to "slice" through activation thresholds and window centers
    of the plot in order to plot the 2D probability curves dynamically
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    plt.subplots_adjust(bottom=0.35)

    scen_data = SCENARIOS[scenario]
    start_size = 1
    backlog_sizes = list(range(start_size, max_backlog_size + 1))
    initial_thr = act_thr if act_thr is not None else 18 / 32
    initial_center = window_center if window_center is not None else initial_thr

    initial_is_pct = is_pct_val(t_min) or is_pct_val(t_max)

    def to_init_val(v, default, is_pct):
        if v is None:
            return default
        if isinstance(v, str):
            v = float(v.rstrip("%")) / 100.0 if "%" in v else float(v)
        return float(v) if is_pct else parse_limit(v, max_backlog_size)

    initial_t_min = to_init_val(t_min, 0.0 if initial_is_pct else 0, initial_is_pct)
    initial_t_max = to_init_val(
        t_max, 1.0 if initial_is_pct else max_backlog_size, initial_is_pct
    )
    initial_use_t = t_min is not None or t_max is not None

    (line_tp,) = ax.plot([], [], label="True Positives P(TP)", color="green", lw=2)
    (line_tn,) = ax.plot([], [], label="True Negatives P(TN)", color="blue", lw=2)
    (line_fp,) = ax.plot(
        [], [], label="False Positives P(FP)", color="orange", lw=2, ls="--"
    )
    (line_fn,) = ax.plot(
        [], [], label="False Negatives P(FN)", color="red", lw=2, ls="--"
    )

    current_results = []

    ax.set_xlim(start_size, max_backlog_size)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Backlog Size", fontsize=12)
    ax.set_ylabel("Probability", fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="upper right", fontsize=11)

    ax_slider_thr = plt.axes([0.25, 0.25, 0.48, 0.03])
    slider_thr = Slider(
        ax=ax_slider_thr,
        label="Activation Thr",
        valmin=0.01,
        valmax=0.99,
        valinit=initial_thr,
        valstep=0.01,
        valfmt="%0.2f",
    )

    ax_slider_center = plt.axes([0.25, 0.20, 0.48, 0.03])
    slider_center = Slider(
        ax=ax_slider_center,
        label="Window Center",
        valmin=0.01,
        valmax=0.99,
        valinit=initial_center,
        valstep=0.01,
        valfmt="%0.2f",
    )

    ax_slider_t_min = plt.axes([0.25, 0.15, 0.48, 0.03])
    slider_t_min = Slider(
        ax=ax_slider_t_min,
        label="T_min",
        valmin=0.0 if initial_is_pct else 0,
        valmax=1.0 if initial_is_pct else max_backlog_size,
        valinit=initial_t_min,
        valstep=0.01 if initial_is_pct else 1,
        valfmt="%0.2f" if initial_is_pct else "%d",
    )

    ax_slider_t_max = plt.axes([0.25, 0.10, 0.48, 0.03])
    slider_t_max = Slider(
        ax=ax_slider_t_max,
        label="T_max",
        valmin=0.0 if initial_is_pct else 0,
        valmax=1.0 if initial_is_pct else max_backlog_size,
        valinit=initial_t_max,
        valstep=0.01 if initial_is_pct else 1,
        valfmt="%0.2f" if initial_is_pct else "%d",
    )

    ax_check = plt.axes([0.78, 0.10, 0.18, 0.18])
    check = CheckButtons(
        ax=ax_check,
        labels=["Sweep", "Specify T_min/T_max", "T_min/T_max %"],
        actives=[sweep, initial_use_t, initial_is_pct],
    )

    prev_is_pct = initial_is_pct

    def set_slider_state(slider, active):
        slider.set_active(active)
        color = "black" if active else "0.6"
        slider.label.set_color(color)
        slider.valtext.set_color(color)
        if hasattr(slider, "track"):
            slider.track.set_facecolor("0.9" if active else "0.85")
        if hasattr(slider, "poly"):
            slider.poly.set_facecolor("0.25" if active else "0.7")
        if not active:
            slider.valtext.set_text("INOP")
        else:
            slider.valtext.set_text(slider.valfmt % slider.val)

    def update(val):
        nonlocal current_results, prev_is_pct
        is_sweep, is_spec_t, is_pct = check.get_status()

        if not is_spec_t:  # disable T_min/T_max percentage toggle when not needed
            if is_pct:
                check.eventson = False
                check.set_active(2)
                check.eventson = True
                is_pct = False
            check.labels[2].set_color("0.6")
        else:
            check.labels[2].set_color("black")

        if is_pct != prev_is_pct:
            prev_is_pct = is_pct
            if is_pct:
                new_min = slider_t_min.val / max_backlog_size
                new_max = slider_t_max.val / max_backlog_size
                (
                    slider_t_min.valmin,
                    slider_t_min.valmax,
                    slider_t_min.valstep,
                    slider_t_min.valfmt,
                ) = (0.0, 1.0, 0.01, "%0.2f")
                (
                    slider_t_max.valmin,
                    slider_t_max.valmax,
                    slider_t_max.valstep,
                    slider_t_max.valfmt,
                ) = (0.0, 1.0, 0.01, "%0.2f")
                slider_t_min.ax.set_xlim(0.0, 1.0)
                slider_t_max.ax.set_xlim(0.0, 1.0)
                slider_t_min.set_val(new_min)
                slider_t_max.set_val(new_max)
            else:
                new_min = int(round(slider_t_min.val * max_backlog_size))
                new_max = int(round(slider_t_max.val * max_backlog_size))
                (
                    slider_t_min.valmin,
                    slider_t_min.valmax,
                    slider_t_min.valstep,
                    slider_t_min.valfmt,
                ) = (0, max_backlog_size, 1, "%d")
                (
                    slider_t_max.valmin,
                    slider_t_max.valmax,
                    slider_t_max.valstep,
                    slider_t_max.valfmt,
                ) = (0, max_backlog_size, 1, "%d")
                slider_t_min.ax.set_xlim(0, max_backlog_size)
                slider_t_max.ax.set_xlim(0, max_backlog_size)
                slider_t_min.set_val(new_min)
                slider_t_max.set_val(new_max)

        curr_thr = slider_thr.val
        curr_center = slider_center.val
        curr_t_min = slider_t_min.val if is_pct else int(slider_t_min.val)
        curr_t_max = slider_t_max.val if is_pct else int(slider_t_max.val)

        set_slider_state(slider_thr, True)
        set_slider_state(slider_center, not is_sweep and not is_spec_t)
        set_slider_state(slider_t_min, not is_sweep and is_spec_t)
        set_slider_state(slider_t_max, not is_sweep and is_spec_t)

        p_tps, p_tns, p_fps, p_fns = [], [], [], []
        current_results = []

        for size in backlog_sizes:
            if is_sweep:
                res = scen_data["sweep_fn"](size, act_thr=curr_thr)
            elif is_spec_t:
                actual_t_max = parse_limit(curr_t_max, size)
                if size < actual_t_max:
                    res = None
                else:
                    res = scen_data["calc_fn"](
                        size, act_thr=curr_thr, t_min=curr_t_min, t_max=curr_t_max
                    )
            else:
                res = scen_data["calc_fn"](
                    size, act_thr=curr_thr, window_center=curr_center
                )

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

        if is_sweep:
            mode_str = "Sweep"
        elif is_spec_t:
            t_min_str = f"{(curr_t_min*100):.2f}%" if is_pct else f"{curr_t_min}"
            t_max_str = f"{(curr_t_max*100):.2f}%" if is_pct else f"{curr_t_max}"
            mode_str = f"Fixed Limits (T_min={t_min_str}, T_max={t_max_str})"
        else:
            mode_str = "Dynamic Limits"

        ax.set_title(
            f"[{scen_data['title']}] 2D Slice ({mode_str}) - "
            f"Activation Threshold: {format_pct(curr_thr)}, "
            f"Window Center: {format_pct(curr_center)}",
            fontsize=14,
        )
        fig.canvas.draw_idle()

    add_hover_annotation(
        fig,
        ax,
        [line_tp, line_tn, line_fp, line_fn],
        lambda i: current_results[i] if i < len(current_results) else None,
    )

    slider_thr.on_changed(update)
    slider_center.on_changed(update)
    slider_t_min.on_changed(update)
    slider_t_max.on_changed(update)
    check.on_clicked(update)
    update(None)
    plt.show()


def print_results(results, title="Calculation Results"):
    if not results:
        print("No valid results found!")
        return

    print(f"--- {title} ---")
    print(f"Backlog Size: {results['backlog_size']}")
    if "activation_threshold" in results:
        print(f"Activation Threshold: {format_pct(results['activation_threshold'])}")
    if "window_center" in results:
        print(f"Window Center: {format_pct(results['window_center'])}")
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

    if "b_p_aa" in results:
        print("-" * 25)
        print(
            f"--- Attacker Inference (Bayes, target alive with probability {results["b_base_prob"]*100}%) ---"
        )
        print(f"P(Alive | Classified Alive):         {results['b_p_aa']:.6f}")
        print(f"P(Not Alive | Classified Alive):     {results['b_p_naa']:.6f}")
        print(f"P(Alive | Classified Not Alive):     {results['b_p_ana']:.6f}")
        print(f"P(Not Alive | Classified Not Alive): {results['b_p_nana']:.6f}")

    print("-" * 25)
    total = results["total_sample_space"]
    print(
        "                    CLASSIFIED AS ALIVE                    CLASSIFIED AS OFFLINE"
    )
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






SCENARIOS = {
    "window": {
        "calc_fn": calculate_probabilities,
        "sweep_fn": sweep_window_sizes,
        "title": "Window",
    },
    "window_timeout": {
        "calc_fn": calculate_probabilities_timeout,
        "sweep_fn": sweep_window_sizes_timeout,
        "title": "Window Timeout",
    },
}


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Calculate probabilities based on backlog size",
        epilog="""
Examples:

  \033[1;36m1. Calculate the probabilities and t_min/t_max backlog size limits automatically\033[0m
     python3 probability_calculator.py 32

  \033[1;36m2. Calculate the probabilities with one or more specified t_min/t_max backlog size limits\033[0m
     python3 probability_calculator.py 64 --t_min 10 --t_max 40
     python3 probability_calculator.py 64 --t_min 0.2 --t_max 0.8
     python3 probability_calculator.py 64 --t_min 20% --t_max 80%

  \033[1;36m3. Calculate the probabilities with a custom activation threshold and/or window center\033[0m
     python3 probability_calculator.py 64 --act_thr 0.5
     python3 probability_calculator.py 64 --act_thr 0.75 --window_center 0.5

  \033[1;36m4. Calculate the best possible limits (optionally fixing one) for the given backlog size\033[0m
     python3 probability_calculator.py 128 --sweep
     python3 probability_calculator.py 128 --sweep --t_min 10

  \033[1;36m5. Plot the backlog sizes from 1 to 32 with dynamically calculated limits based on each backlog size\033[0m
     python3 probability_calculator.py 32 --plot

  \033[1;36m6. Plot the backlog sizes from 40 to 64, given specified backlog size limits\033[0m
     python3 probability_calculator.py 64 --plot --t_min 10 --t_max 40

  \033[1;36m7. For each backlog size, find the best t_min/t_max backlog size limits for it, then plot each one of them\033[0m
     python3 probability_calculator.py 64 --plot --sweep

  \033[1;36m8. Plot 3D surface graph across backlog sizes and activation thresholds\033[0m
     python3 probability_calculator.py 32 --plot_3d
     python3 probability_calculator.py 32 --plot_3d --sweep

  \033[1;36m9. Interactive 2D slice tool with sliders for activation thresholds and automatic centering for t_min/t_max (this last feature is not available when using the sweep function) \033[0m
     python3 probability_calculator.py 64 --sliders
     python3 probability_calculator.py 64 --sliders --sweep

  \033[1;36m10. Run calculations with the alternate 'window_timeout' scenario\033[0m
     python3 probability_calculator.py 32 --scenario window_timeout

  \033[1;36m11. Calculate/plot Bayesian probabilities with a custom base probability (e.g., 0.5% or 0.005)\033[0m
     python3 probability_calculator.py 32 --bayes_base_prob 0.5%
     python3 probability_calculator.py 32 --plot_bayes --bayes_base_prob 0.005

  \033[1;36m12. Plot the graph with whiskers, i.e. the one that shows the probability change for the possible t_min/t_max vaules in a delta and all possible activation thresholds\033[0m
     python3 probability_calculator.py 128 --plot_whiskers
     python3 probability_calculator.py 128 --plot_whiskers --scenario window_timeout

Notes:
  \033[2m--plot\033[0m            Plot the 2D results
  \033[2m--plot_3d\033[0m         Plot the 3D surface results
  \033[2m--sliders\033[0m         Interactive 2D view along sliders to change the values
  \033[2m--sweep\033[0m           Search for the best t_min/t_max backlog size limits
  \033[2m--bayes_base_prob\033[0m Base probability for Bayesian calculations (default: 0.5)
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("backlog_size", type=int, help="size of the backlog queue")

    parser.add_argument(
        "--scenario",
        type=str,
        choices=["window", "window_timeout"],
        default="window",
        help='choose the calculation scenario (the default is "window")',
    )

    parser.add_argument(
        "--t_min",
        type=str,
        required=False,
        help="lower limit for the backlog window size (int, ratio float <= 1.0, or percentage)",
    )

    parser.add_argument(
        "--t_max",
        type=str,
        required=False,
        help="upper limit for the backlog window size (int, ratio float <= 1.0, or percentage)",
    )

    parser.add_argument(
        "--act_thr",
        type=float,
        required=False,
        help="activation threshold of the mitigation. Defaults to 0.5625 (or 18/32)",
    )

    parser.add_argument(
        "--window_center",
        type=float,
        required=False,
        help="threshold ratio used to center t_min/t_max backlog size limits automatically when they are not specified directly by the user. Defaults to act_thr if not given",
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
        "--plot_whiskers",
        action="store_true",
        help="Plot probabilities vs threshold percentage with a sweep between ±20%% of delta for T_min/T_max",
    )

    parser.add_argument(
        "--plot_bayes",
        action="store_true",
        help="Plot the probabilities from the attacker's perspective (Bayesian ones)",
    )

    parser.add_argument(
        "--bayes_base_prob",
        "--base_prob",
        type=str,
        default="0.5",
        help="base probability P(Alive) for Bayesian calculations (float or percentage, defaults to 0.5)",
    )

    parser.add_argument(
        "--plot_3d",
        action="store_true",
        help="Plot 3D surface graph of probabilities across backlog sizes and activation thresholds",
    )

    parser.add_argument(
        "--sliders",
        action="store_true",
        help="Open an interactive plot tool with sliders for activation thresholds",
    )

    args = parser.parse_args()

    if args.plot_3d:
        plot_probabilities_3d(
            args.backlog_size,
            scenario=args.scenario,
            sweep=args.sweep,
            act_thr=args.act_thr,
            window_center=args.window_center,
            t_min=args.t_min,
            t_max=args.t_max,
        )
    elif args.sliders:
        plot_sliders(
            args.backlog_size,
            scenario=args.scenario,
            sweep=args.sweep,
            act_thr=args.act_thr,
            window_center=args.window_center,
            t_min=args.t_min,
            t_max=args.t_max,
        )
    elif args.plot:
        plot_probabilities(
            args.backlog_size,
            scenario=args.scenario,
            sweep=args.sweep,
            act_thr=args.act_thr,
            window_center=args.window_center,
            t_min=args.t_min,
            t_max=args.t_max,
        )
    elif args.plot_whiskers:
        plot_whiskers(
            args.backlog_size,
            scenario=args.scenario,
            t_min=args.t_min,
            t_max=args.t_max,
        )
    elif args.plot_bayes:
        plot_probabilities_bayes(
            args.backlog_size,
            scenario=args.scenario,
            sweep=args.sweep,
            act_thr=args.act_thr,
            window_center=args.window_center,
            t_min=args.t_min,
            t_max=args.t_max,
            base_prob=args.bayes_base_prob,
        )
    elif args.sweep:
        results = SCENARIOS[args.scenario]["sweep_fn"](
            args.backlog_size,
            act_thr=args.act_thr,
            window_center=args.window_center,
            t_min=args.t_min,
            t_max=args.t_max,
        )
        results = calculate_bayes_probabilities(results, base_prob=args.bayes_base_prob)
        print_results(
            results,
            title=f"Best Window From Sweep [{SCENARIOS[args.scenario]['title']}]",
        )
    else:
        results = SCENARIOS[args.scenario]["calc_fn"](
            args.backlog_size,
            act_thr=args.act_thr,
            window_center=args.window_center,
            t_min=args.t_min,
            t_max=args.t_max,
        )
        results = calculate_bayes_probabilities(results, base_prob=args.bayes_base_prob)
        print_results(
            results, title=f"Calculation Results [{SCENARIOS[args.scenario]['title']}]"
        )
