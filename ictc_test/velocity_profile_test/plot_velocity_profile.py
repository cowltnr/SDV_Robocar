import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
from rclpy.serialization import deserialize_message
from geometry_msgs.msg import Twist


BAG_ROOT = Path("../rosbag")

PLOT_DIR = Path("plot/velocity")
PLOT_DIR.mkdir(parents=True, exist_ok=True)

ROUTES = ["wp1", "wp2", "wp3", "wp4", "wp5"]

SUBPLOT_LABELS = {
    "wp1": "(a)",
    "wp2": "(b)",
    "wp3": "(c)",
    "wp4": "(d)",
    "wp5": "(e)",
}

POINT_COLOR = "#ff7f0e"
PURSUIT_COLOR = "#1f77b4"


def extract_cmd_vel(bag_path):
    conn = sqlite3.connect(bag_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM topics")
    topics = cursor.fetchall()

    cmd_topic_id = None
    for topic_id, name in topics:
        if name == "/sim/cmd_vel":
            cmd_topic_id = topic_id
            break

    if cmd_topic_id is None:
        raise RuntimeError(f"/sim/cmd_vel topic not found in rosbag: {bag_path}")

    cursor.execute(
        "SELECT timestamp, data FROM messages WHERE topic_id=? ORDER BY timestamp",
        (cmd_topic_id,)
    )

    rows = cursor.fetchall()
    conn.close()

    if len(rows) == 0:
        raise RuntimeError(f"No /sim/cmd_vel messages found: {bag_path}")

    t0 = rows[0][0]

    times = []
    linear_x = []
    angular_z = []

    for timestamp, data in rows:
        msg = deserialize_message(data, Twist)

        times.append((timestamp - t0) * 1e-9)
        linear_x.append(msg.linear.x)
        angular_z.append(msg.angular.z)

    return times, linear_x, angular_z


def trim_motion_time(times, linear_x, angular_z, threshold=0.01):
    moving_indices = []

    for i, (v, w) in enumerate(zip(linear_x, angular_z)):
        if abs(v) > threshold or abs(w) > threshold:
            moving_indices.append(i)

    if len(moving_indices) == 0:
        return times, linear_x, angular_z

    start_idx = moving_indices[0]
    end_idx = moving_indices[-1]

    times = times[start_idx:end_idx + 1]
    linear_x = linear_x[start_idx:end_idx + 1]
    angular_z = angular_z[start_idx:end_idx + 1]

    t0 = times[0]
    times = [t - t0 for t in times]

    return times, linear_x, angular_z


def style_axis(ax):
    for spine in ax.spines.values():
        spine.set_linewidth(1.8)

    ax.tick_params(
        axis="both",
        labelsize=14,
        width=1.6,
        length=6
    )

    ax.grid(True)


def plot_velocity_profile(target_route):
    pursuit_bag_path = BAG_ROOT / f"pursuit_{target_route}" / f"pursuit_{target_route}_0.db3"
    point_bag_path = BAG_ROOT / f"point_{target_route}" / f"point_{target_route}_0.db3"

    pursuit_t, pursuit_v, pursuit_w = extract_cmd_vel(str(pursuit_bag_path))
    point_t, point_v, point_w = extract_cmd_vel(str(point_bag_path))

    pursuit_t, pursuit_v, pursuit_w = trim_motion_time(
        pursuit_t,
        pursuit_v,
        pursuit_w
    )
    point_t, point_v, point_w = trim_motion_time(
        point_t,
        point_v,
        point_w
    )

    print(f"{target_route}: Pursuit cmd_vel = {len(pursuit_t)}")
    print(f"{target_route}: Point cmd_vel = {len(point_t)}")

    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    # Linear velocity
    axes[0].plot(
        point_t,
        point_v,
        linewidth=3.0,
        label="Point Follower",
        color=POINT_COLOR,
        alpha=0.8
    )
    axes[0].plot(
        pursuit_t,
        pursuit_v,
        linewidth=3.0,
        label="Pure Pursuit",
        color=PURSUIT_COLOR,
        alpha=0.8
    )
    axes[0].set_ylabel("Linear velocity [m/s]", fontsize=16)
    axes[0].set_title(
        f"{SUBPLOT_LABELS[target_route]} Velocity Profile Comparison ({target_route})",
        fontsize=17
    )
    axes[0].legend(fontsize=14)
    style_axis(axes[0])

    # Angular velocity
    axes[1].plot(
        point_t,
        point_w,
        linewidth=3.0,
        label="Point Follower",
        color=POINT_COLOR,
        alpha=0.8
    )
    axes[1].plot(
        pursuit_t,
        pursuit_w,
        linewidth=3.0,
        label="Pure Pursuit",
        color=PURSUIT_COLOR,
        alpha=0.8
    )
    axes[1].set_xlabel("Time [s]", fontsize=16)
    axes[1].set_ylabel("Angular velocity [rad/s]", fontsize=16)
    style_axis(axes[1])

    plt.tight_layout()

    save_name = PLOT_DIR / f"velocity_{target_route}.png"
    plt.savefig(save_name, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {save_name}")


def plot_all_velocity_profiles():
    for target_route in ROUTES:
        plot_velocity_profile(target_route)


if __name__ == "__main__":
    plot_all_velocity_profiles()