from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

PLOT_DIR = Path("plot")

image_files = [
    #PLOT_DIR / "reference_routes_wp1_wp5.png",
    PLOT_DIR / "compare_wp1_trajectory.png",
    PLOT_DIR / "compare_wp2_trajectory.png",
    PLOT_DIR / "compare_wp3_trajectory.png",
    PLOT_DIR / "compare_wp4_trajectory.png",
    PLOT_DIR / "compare_wp5_trajectory.png",
]

fig, axes = plt.subplots(2, 3, figsize=(18, 12))
axes = axes.flatten()

for ax, img_path in zip(axes, image_files):
    img = mpimg.imread(img_path)
    ax.imshow(img)
    ax.axis("off")

axes[-1].axis("off")

condition_text = (
    "Conditions | Isaac Sim 4.5.0, LIMO ROS2, wp1–wp5, "
    "control rate: 20 Hz, goal tolerance: 0.4 m, "
    "max linear: 1.5 m/s, max angular: 0.9 rad/s, "
    "topics: /tf, /sim/cmd_vel"
)

fig.text(
    0.5,
    0.03,
    condition_text,
    ha="center",
    va="center",
    fontsize=13,
    bbox=dict(facecolor="white", edgecolor="black", boxstyle="round,pad=0.4", alpha=0.95)
)

plt.tight_layout(rect=[0, 0.07, 1, 1])

plt.tight_layout()
save_path = PLOT_DIR / "compare_all_routes_2x3.png"
plt.savefig(save_path, dpi=300, bbox_inches="tight")
plt.close()

print(f"Saved: {save_path}")