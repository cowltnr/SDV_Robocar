import sys
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
from rclpy.serialization import deserialize_message
from tf2_msgs.msg import TFMessage


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from waypoint_tools.waypoint_routes.routes import ROUTES


BAG_ROOT = Path("../rosbag")
routes = ROUTES
POINT_COLORS = {
    "wp1": "#b22222",
    "wp2": "#008000",
    "wp3": "#0000ff",
    "wp4": "#FFD700",
    "wp5": "#8b008b",
}

PLOT_DIR = Path("plot")
PLOT_DIR.mkdir(parents=True, exist_ok=True)


def extract_trajectory(bag_path):
    conn = sqlite3.connect(bag_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM topics")
    topics = cursor.fetchall()

    tf_topic_id = None
    for topic_id, name in topics:
        if name == "/tf":
            tf_topic_id = topic_id
            break

    if tf_topic_id is None:
        raise RuntimeError(f"/tf topic not found in rosbag: {bag_path}")

    cursor.execute(
        "SELECT timestamp, data FROM messages WHERE topic_id=? ORDER BY timestamp",
        (tf_topic_id,)
    )

    xs = []
    ys = []

    for timestamp, data in cursor.fetchall():
        msg = deserialize_message(data, TFMessage)

        for transform in msg.transforms:
            if transform.header.frame_id == "odom" and transform.child_frame_id == "base_link":
                xs.append(transform.transform.translation.x)
                ys.append(transform.transform.translation.y)

    conn.close()

    if len(xs) == 0:
        raise RuntimeError(f"No odom -> base_link transform found: {bag_path}")

    return xs, ys


def plot_route(target_route):
    pursuit_bag_path = BAG_ROOT / f"pursuit_{target_route}" / f"pursuit_{target_route}_0.db3"
    point_bag_path = BAG_ROOT / f"point_{target_route}" / f"point_{target_route}_0.db3"

    pursuit_xs, pursuit_ys = extract_trajectory(str(pursuit_bag_path))
    point_xs, point_ys = extract_trajectory(str(point_bag_path))

    print(f"{target_route}: Pursuit poses = {len(pursuit_xs)}")
    print(f"{target_route}: Point poses = {len(point_xs)}")

    plt.figure(figsize=(8, 7))

    # Reference route
    points = routes[target_route]
    rx = [p[0] for p in points]
    ry = [p[1] for p in points]

    plt.plot(
        rx, ry, ":",
        linewidth=5.0,
        label=f"{target_route} reference",
        color=POINT_COLORS[target_route],
        zorder=1
    )
    plt.scatter(
        rx, ry,
        s=60,
        color=POINT_COLORS[target_route],
        edgecolors="black",
        linewidths=0.5,
        zorder=2
    )

    # Point Follower trajectory
    plt.plot(
        point_xs, point_ys,
        linewidth=4.0,
        label="Point Follower trajectory",
        color="#ff7f0e",
        alpha=0.7,
        zorder=3
    )

    # Pure Pursuit trajectory
    plt.plot(
        pursuit_xs, pursuit_ys,
        linewidth=4.0,
        label="Pure Pursuit trajectory",
        color="#1f77b4",
        alpha=0.7,
        zorder=4
    )

    # Start / End markers for Point Follower
    plt.scatter(
        point_xs[0], point_ys[0],
        marker="o",
        s=90,
        label="Point Start",
        facecolors="#ff7f0e",
        edgecolors="black",
        linewidths=1.5,
        alpha=0.7,
        zorder=5
    )
    plt.scatter(
        point_xs[-1], point_ys[-1],
        marker="X",
        s=130,
        label="Point End",
        facecolors="#ff7f0e",
        edgecolors="black",
        linewidths=1.5,
        alpha=0.7,
        zorder=6
    )

    # Start / End markers for Pure Pursuit
    plt.scatter(
        pursuit_xs[0], pursuit_ys[0],
        marker="o",
        s=80,
        label="Pursuit Start",
        facecolors="#1f77b4",
        edgecolors="black",
        linewidths=1.5,
        alpha=0.7,
        zorder=7
    )
    plt.scatter(
        pursuit_xs[-1], pursuit_ys[-1],
        marker="X",
        s=120,
        label="Pursuit End",
        facecolors="#1f77b4",
        edgecolors="black",
        linewidths=1.5,
        alpha=0.7,
        zorder=8
    )

    ax = plt.gca()

    # x, y축 선 두께
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)

    # tick 글씨 크기와 tick 두께
    ax.tick_params(
        axis="both",
        labelsize=14,
        width=1.6,
        length=6
    )

    plt.xlabel("x [m]", fontsize=16)
    plt.ylabel("y [m]", fontsize=16)
    plt.title(f"Point vs Pure Pursuit Trajectory ({target_route})", fontsize=17)
    plt.axis("equal")

    plt.grid(True)
    plt.legend(fontsize=14)
    plt.tight_layout()

    save_name = PLOT_DIR / f"compare_{target_route}_trajectory.png"
    plt.savefig(save_name, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {save_name}")

def plot_all_reference_routes():
    plt.figure(figsize=(8, 7))

    for route_name, points in routes.items():
        rx = [p[0] for p in points]
        ry = [p[1] for p in points]

        plt.plot(
            rx, ry, ":",
            linewidth=5.0,
            label=f"{route_name} reference",
            color=POINT_COLORS[route_name],
            zorder=1
        )

        plt.scatter(
            rx, ry,
            s=60,
            color=POINT_COLORS[route_name],
            edgecolors="black",
            linewidths=0.5,
            zorder=2
        )

    ax = plt.gca()

    for spine in ax.spines.values():
        spine.set_linewidth(1.8)

    ax.tick_params(
        axis="both",
        labelsize=14,
        width=1.6,
        length=6
    )

    plt.xlabel("x [m]", fontsize=16)
    plt.ylabel("y [m]", fontsize=16)
    plt.title("Reference Routes (wp1-wp5)", fontsize=17)
    plt.axis("equal")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    save_name = PLOT_DIR / "reference_routes_wp1_wp5.png"
    plt.savefig(save_name, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {save_name}")


if __name__ == "__main__":
    for target_route in ["wp1", "wp2", "wp3", "wp4", "wp5"]:
        plot_route(target_route)
    plot_all_reference_routes()