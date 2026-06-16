from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch


CSV_PATH = Path("plot/stop_count_table.csv")
PLOT_DIR = Path("plot")
PLOT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV_PATH, comment="#")

routes = df["Route"].values
point = df["Point Linear Stop Count"].values
pursuit = df["Pure Pursuit Linear Stop Count"].values

x = np.arange(len(routes))
width = 0.35

fig, axes = plt.subplots(
    1,
    2,
    figsize=(14, 6),
    gridspec_kw={"width_ratios": [2.2, 1.0]}
)

# =========================
# (a) Route-wise stop count
# =========================
axes[0].bar(
    x - width / 2,
    point,
    width,
    label="Point Follower",
    color="#ff7f0e",
    edgecolor="black",
    linewidth=1.2
)

axes[0].bar(
    x + width / 2,
    pursuit,
    width,
    label="Pure Pursuit",
    color="#1f77b4",
    edgecolor="black",
    linewidth=1.2
)

for i, v in enumerate(point):
    axes[0].text(i - width / 2, v + 1, str(v), ha="center", fontsize=12)

for i, v in enumerate(pursuit):
    axes[0].text(i + width / 2, v + 1, str(v), ha="center", fontsize=12)

axes[0].set_xticks(x)
axes[0].set_xticklabels(routes, fontsize=13)
axes[0].set_xlabel("Route", fontsize=15)
axes[0].set_ylabel("Linear Stop Count", fontsize=15)
axes[0].set_title("(a) Route-wise Stop Count", fontsize=16)
axes[0].grid(axis="y", linestyle="--", alpha=0.5)
axes[0].legend(fontsize=12)


# =========================
# (b) Average stop count - compact horizontal bar
# =========================
avg_labels = ["Point Follower", "Pure Pursuit"]
avg_values = [point.mean(), pursuit.mean()]
avg_colors = ["#ff7f0e", "#1f77b4"]

y_pos = np.arange(len(avg_labels))

axes[1].barh(
    y_pos,
    avg_values,
    height=0.35,
    color=avg_colors,
    edgecolor="black",
    linewidth=1.2
)

max_avg = max(avg_values)
if max_avg == 0:
    max_avg = 1.0

axes[1].set_xlim(0, max_avg * 1.18)

axes[1].set_yticks(y_pos)
axes[1].set_yticklabels(avg_labels, fontsize=14)
axes[1].set_xlabel("Average Linear Stop Count", fontsize=15)
axes[1].set_title("(b) Average Stop Count", fontsize=16)

for i, v in enumerate(avg_values):
    axes[1].text(
        v + max_avg * 0.03,
        i,
        f"{v:.1f}",
        va="center",
        fontsize=14
    )

legend_handles = [
    Patch(facecolor="#ff7f0e", edgecolor="black", label="Point Follower"),
    Patch(facecolor="#1f77b4", edgecolor="black", label="Pure Pursuit"),
]

axes[1].legend(
    handles=legend_handles,
    fontsize=12,
    loc="lower right"
)

axes[1].invert_yaxis()
axes[1].grid(axis="x", linestyle="--", alpha=0.5)

for ax in axes:
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)

    ax.tick_params(
        axis="both",
        labelsize=13,
        width=1.4,
        length=5
    )

plt.suptitle("Linear Stop Count Comparison", fontsize=18)

definition_text = (
    "Definition | Full Stop: |linear.x| ≤ 0.05 and |angular.z| ≤ 0.05 for ≥ 0.2 s; "
    "Linear Stop: |linear.x| ≤ 0.05 for ≥ 0.2 s; Unit: count"
)

fig.text(
    0.5,
    0.02,
    definition_text,
    ha="center",
    va="center",
    fontsize=11,
    bbox=dict(
        facecolor="white",
        edgecolor="black",
        boxstyle="round,pad=0.35",
        alpha=0.95
    )
)

plt.tight_layout(rect=[0, 0.08, 1, 0.95])

save_path = PLOT_DIR / "linear_stop_count_1x2.png"
plt.savefig(save_path, dpi=300, bbox_inches="tight")
plt.close()

print(f"Saved: {save_path}")