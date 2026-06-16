from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

PLOT_DIR = Path("plot")
VELOCITY_DIR = PLOT_DIR / "velocity"

image_files = [
    VELOCITY_DIR / "velocity_wp1.png",
    VELOCITY_DIR / "velocity_wp2.png",
    VELOCITY_DIR / "velocity_wp3.png",
    VELOCITY_DIR / "velocity_wp4.png",
    VELOCITY_DIR / "velocity_wp5.png",
]

fig, axes = plt.subplots(2, 3, figsize=(18, 8))
axes = axes.flatten()

for ax, img_path in zip(axes, image_files):
    img = mpimg.imread(img_path)
    ax.imshow(img)
    ax.axis("off")

axes[-1].axis("off")

condition_text = (
    "Conditions | Same start pose, same routes (wp1–wp5), "
    "v_max = 1.5 m/s, w_max = 0.9 rad/s, "
    "goal tolerance = 0.4 m, control rate = 20 Hz"
)

fig.text(
    0.5,
    0.03,
    condition_text,
    ha="center",
    va="center",
    #fontsize=13,
    bbox=dict(
        facecolor="white",
        edgecolor="black",
        boxstyle="round,pad=0.4",
        alpha=0.95
    )
)

plt.tight_layout(rect=[0, 0.07, 1, 1])

save_path = VELOCITY_DIR / "velocity_all_routes_2x3.png"
plt.savefig(save_path, dpi=300, bbox_inches="tight")
plt.close()

print(f"Saved: {save_path}")