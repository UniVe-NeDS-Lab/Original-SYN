import argparse
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, CheckButtons
import numpy as np


def calculate_timeout_probabilities(tm_a, tm_min, tm_max):
    """
    Calculate the probabilities of false positives, false negatives,
    true positives and true negatives based on the given time limits
    and the chosen attacker's timer
    """
    if tm_max <= tm_min:
        return None

    if tm_a <= tm_min:
        p_tp = 0.0
    elif tm_a >= tm_max:
        p_tp = 1.0
    else:
        p_tp = (tm_a - tm_min) / (tm_max - tm_min)

    p_fn = 1.0 - p_tp
    p_fp = 0.0
    p_tn = 1.0

    return {
        "p_tp": p_tp,
        "p_fn": p_fn,
        "p_fp": p_fp,
        "p_tn": p_tn,
        "tm_a": tm_a,
        "tm_min": tm_min,
        "tm_max": tm_max,
    }


def calculate_bayes_probabilities(probs, base_prob=0.5):
    """
    Calculate the attacker's seen statistics using the Bayes theorem, where base_prob
    is basically the percentage of alive victims behind the zombie that the attacker
    will try to guess the state of
    """
    if probs is None:
        return None

    p_tp = probs["p_tp"]
    p_tn = probs["p_tn"]
    p_fp = probs["p_fp"]
    p_fn = probs["p_fn"]

    den_a = (base_prob * p_tp) + ((1.0 - base_prob) * p_fp)
    den_na = (base_prob * p_fn) + ((1.0 - base_prob) * p_tn)

    b_p_aa = (p_tp * base_prob) / den_a if den_a > 0 else 0
    b_p_naa = (p_fp * (1.0 - base_prob)) / den_a if den_a > 0 else 0
    b_p_ana = (p_fn * base_prob) / den_na if den_na > 0 else np.nan
    b_p_nana = (p_tn * (1.0 - base_prob)) / den_na if den_na > 0 else np.nan

    res = probs.copy()
    res.update(
        {
            "b_p_aa": b_p_aa,
            "b_p_naa": b_p_naa,
            "b_p_ana": b_p_ana,
            "b_p_nana": b_p_nana,
            "base_prob": base_prob,
        }
    )
    return res


def plot_interactive_timeout(
    init_tm_min=0.20,
    init_tm_max=0.80,
    init_tm_a=0.50,
    init_base_prob=0.50,
    init_bayes=False,
):
    """
    Build the graph with sliders for tm_min, tm_max and tm_a, plus a toggle to see the
    probabilities calculated through Bayes
    """
    fig, ax = plt.subplots(figsize=(11, 7))
    plt.subplots_adjust(bottom=0.38)

    tm_a_vec = np.linspace(0.0, 1.0, 500)

    (line_tp_aa,) = ax.plot([], [], label="True Positives P(TP)", color="green", lw=2)
    (line_tn_nana,) = ax.plot([], [], label="True Negatives P(TN)", color="blue", lw=2)
    (line_fp_naa,) = ax.plot(
        [], [], label="False Positives P(FP)", color="orange", lw=2, ls="--"
    )
    (line_fn_ana,) = ax.plot(
        [], [], label="False Negatives P(FN)", color="red", lw=2, ls="--"
    )

    (point_tp_aa,) = ax.plot([], [], "o", color="green", ms=7)
    (point_tn_nana,) = ax.plot([], [], "o", color="blue", ms=7)
    (point_fp_naa,) = ax.plot([], [], "o", color="orange", ms=7)
    (point_fn_ana,) = ax.plot([], [], "o", color="red", ms=7)

    lines = [line_tp_aa, line_tn_nana, line_fp_naa, line_fn_ana]
    points = [point_tp_aa, point_tn_nana, point_fp_naa, point_fn_ana]

    vmarker = ax.axvline(
        init_tm_a, color="black", linestyle=":", alpha=0.6, label="tm_a (Attacker's Timer)"
    )

    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("tm_a", fontsize=11)
    ax.set_ylabel("Probability", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.6)

    ax_tm_min = plt.axes([0.22, 0.24, 0.48, 0.03])
    ax_tm_max = plt.axes([0.22, 0.19, 0.48, 0.03])
    ax_tm_a = plt.axes([0.22, 0.14, 0.48, 0.03])
    ax_base_p = plt.axes([0.22, 0.09, 0.48, 0.03])

    slider_tm_min = Slider(
        ax_tm_min, "tm_min", 0.0, 1.0, valinit=init_tm_min, valstep=0.01, valfmt="%0.2f"
    )
    slider_tm_max = Slider(
        ax_tm_max, "tm_max", 0.0, 1.0, valinit=init_tm_max, valstep=0.01, valfmt="%0.2f"
    )
    slider_tm_a = Slider(
        ax_tm_a,
        "tm_a",
        0.0,
        1.0,
        valinit=init_tm_a,
        valstep=0.01,
        valfmt="%0.2f",
    )
    slider_base_p = Slider(
        ax_base_p,
        "Base P(Alive) Probability",
        0.01,
        0.99,
        valinit=init_base_prob,
        valstep=0.01,
        valfmt="%0.2f",
    )

    ax_check = plt.axes([0.76, 0.14, 0.18, 0.12])
    check = CheckButtons(ax_check, ["Use Bayes"], [init_bayes])

    def get_probs(tm_a, tm_min, tm_max, base_prob, bayes_mode):
        probs = calculate_timeout_probabilities(tm_a, tm_min, tm_max)
        if probs and bayes_mode:
            probs = calculate_bayes_probabilities(probs, base_prob)
        if not probs:
            return [np.nan] * 4
        keys = (
            ("b_p_aa", "b_p_nana", "b_p_naa", "b_p_ana")
            if bayes_mode
            else ("p_tp", "p_tn", "p_fp", "p_fn")
        )
        return [probs[k] for k in keys]

    def update(val):
        tm_min = slider_tm_min.val
        tm_max = slider_tm_max.val
        tm_a = slider_tm_a.val
        base_p = slider_base_p.val
        bayes_mode = check.get_status()[0]

        vmarker.set_xdata([tm_a, tm_a])

        curves = np.array(
            [get_probs(t, tm_min, tm_max, base_p, bayes_mode) for t in tm_a_vec]
        ).T
        single_pts = get_probs(tm_a, tm_min, tm_max, base_p, bayes_mode)

        for line, point, curve, pt in zip(lines, points, curves, single_pts):
            line.set_data(tm_a_vec, curve)
            point.set_data([tm_a], [pt])

        labels = (
            [
                "P(Alive | Class. Alive)",
                "P(Not Alive | Class. Not Alive)",
                "P(Not Alive | Class. Alive)",
                "P(Alive | Class. Not Alive)",
            ]
            if bayes_mode
            else [
                "True Positives P(TP)",
                "True Negatives P(TN)",
                "False Positives P(FP)",
                "False Negatives P(FN)",
            ]
        )

        for line, label, pt in zip(lines, labels, single_pts):
            line.set_label(f"{label}: {pt:.4f}" if not np.isnan(pt) else label)

        if not bayes_mode:
            ax.set_title(
                f"[Timeout] Base Probabilities\n"
                f"tm_min={tm_min:.2f}, tm_max={tm_max:.2f}, tm_a={tm_a:.2f}",
                fontsize=12,
            )
        else:
            ax.set_title(
                f"[Timeout] Bayes Probabilities (Attacker's View)\n"
                f"tm_min={tm_min:.2f}, tm_max={tm_max:.2f}, tm_a={tm_a:.2f}, Prior P(Alive)={base_p:.2f}",
                fontsize=12,
            )

        ax.legend(loc="upper right", fontsize=10)
        fig.canvas.draw_idle()

    slider_tm_min.on_changed(update)
    slider_tm_max.on_changed(update)
    slider_tm_a.on_changed(update)
    slider_base_p.on_changed(update)
    check.on_clicked(update)

    update(None)
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Plot for the mitigation using timeouts. All times are represented as "percentages"'
    )
    parser.add_argument(
        "--tm_min",
        type=float,
        default=0.20,
        help="Minimum threshold for the timer (default 0.20)",
    )
    parser.add_argument(
        "--tm_max",
        type=float,
        default=0.80,
        help="Maximum threshold for the timer (default 0.80)",
    )
    parser.add_argument(
        "--tm_a",
        type=float,
        default=0.50,
        help="Wait time for before the attacker sends the probes (default 0.50)",
    )
    parser.add_argument(
        "--base_prob",
        type=float,
        default=0.50,
        help="Base probability for a victim of being alive, used for Bayes (default 0.50)",
    )
    parser.add_argument(
        "--bayes", action="store_true", help="Show the Bayes probabilities"
    )

    args = parser.parse_args()

    plot_interactive_timeout(
        init_tm_min=args.tm_min,
        init_tm_max=args.tm_max,
        init_tm_a=args.tm_a,
        init_base_prob=args.base_prob,
        init_bayes=args.bayes,
    )
