import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys


def create_heatmaps(csv_path, out_path):
    """
    Load the data from the provided CSV file and plot it to the given image file
    """
    df = pd.read_csv(csv_path)

    groups = [32, 64, 128]
    targets = [
        ("target_alive", "Target actually alive"),
        ("target_not_alive", "Target actually dead"),
    ]

    # Calculate the proportions (alive/(alive+not-alive))
    props = {}
    for group in groups:
        for target_key, target_label in targets:
            a = df[f"alive_alive_result_{group}_txt_{target_key}"]
            b = df[f"not_alive_not_alive_result_{group}_txt_{target_key}"]
            props[(group, target_key)] = (a / (a + b)) * 100

    lowers = sorted(df["lower"].unique())
    uppers = sorted(df["upper"].unique())

    fig, axes = plt.subplots(
        2, 3,
        figsize=(17, 9),
        sharex=True,
        sharey=True,
        constrained_layout=True
    )

    for target_idx, (target_key, target_label) in enumerate(targets):
        for group_idx, group in enumerate(groups):
            ax = axes[target_idx, group_idx]

            grid = np.full((len(lowers), len(uppers)), np.nan)

            for i, lower in enumerate(lowers):
                subset = df[df["lower"] == lower].set_index("upper")

                for j, upper in enumerate(uppers):
                    if upper in subset.index:
                        row = subset.loc[upper]
                        alive = row[f"alive_alive_result_{group}_txt_{target_key}"]
                        not_alive = row[f"not_alive_not_alive_result_{group}_txt_{target_key}"]

                        total = alive + not_alive
                        if total != 0:
                            grid[i, j] = 100 * alive / total

            grid_mask = np.ma.masked_invalid(grid) # Hide invalid cells

            im = ax.imshow(
                grid_mask,
                origin="lower",
                aspect="auto",
                cmap="PuOr",
                vmin=0,
                vmax=100
            )

            # Display a percentage in each cell that it's valid
            for i in range(len(lowers)):
                for j in range(len(uppers)):
                    val = grid[i, j]

                    if not np.isnan(val):
                        ax.text(
                            j,
                            i,
                            f"{val:.0f}%",
                            ha="center",
                            va="center",
                            fontsize=10,
                            fontweight="normal"
                        )

            ax.set_title(
                f"{group} columns",
                fontsize=13,
                fontweight="bold"
            )

            ax.set_xticks(range(len(uppers)))
            ax.set_xticklabels(uppers)
            ax.set_yticks(range(len(lowers)))
            ax.set_yticklabels(lowers)

            if target_idx == 1:
                ax.set_xlabel("Upper", fontsize=11)

            if group_idx == 0:
                ax.set_ylabel(
                    "Lower\n" + target_label,
                    fontsize=11
                )

            ax.set_xticks(
                np.arange(-0.5, len(uppers), 1),
                minor=True
            )
            ax.set_yticks(
                np.arange(-0.5, len(lowers), 1),
                minor=True
            )

            ax.grid(
                which="minor",
                color="white",
                linestyle="-",
                linewidth=1.5
            )
            ax.tick_params(
                which="minor",
                bottom=False,
                left=False
            )

    cbar = fig.colorbar(
        im,
        ax=axes,
        shrink=0.85,
        pad=0.02,
        ticks=[0, 25, 50, 75, 100]
    )
    cbar.set_label("Proportion (%)", fontsize=11)

    fig.suptitle(
        "Alive/Not-alive proportions across lower-upper pairs",
        fontsize=17,
        fontweight="bold"
    )

    if out_path:
        fig.savefig(
            out_path,
            dpi=220,
            bbox_inches="tight"
        )

    plt.show()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <input.csv> [output.png]")
        sys.exit(1)

    csv_path = sys.argv[1]

    out_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else "heatmaps_table.png"
    )

    create_heatmaps(csv_path, out_path)