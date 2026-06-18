import sys
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
from rclpy.serialization import deserialize_message
from tf2_msgs.msg import TFMessage
from std_msgs.msg import String


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from waypoint_tools.waypoint_routes.routes import ROUTES


BAG_ROOT = Path("../rosbag")
BAG_PATH = BAG_ROOT / "vlm_route_pursuit" / "vlm_route_pursuit_0.db3"
POINT_BAG_PATH = BAG_ROOT / "vlm_route_point" / "vlm_route_point_0.db3"

PLOT_DIR = Path("plot")
PLOT_DIR.mkdir(parents=True, exist_ok=True)

ROUTE_COLORS = {
    "wp1": "#b22222",
    "wp2": "#008000",
    "wp3": "#0000ff",
    "wp4": "#FFD700",
    "wp5": "#8b008b",
}

PURSUIT_TRAJECTORY_COLOR = "#1f77b4"
POINT_TRAJECTORY_COLOR = "#ff7f0e"
ORIGINAL_ROUTE_COLOR = "#008000"
VLM_ROUTE_COLOR = "#8b008b"


def get_topic_id(cursor, topic_name):
    cursor.execute("SELECT id, name FROM topics")
    topics = cursor.fetchall()

    for topic_id, name in topics:
        if name == topic_name:
            return topic_id

    return None


def extract_tf_trajectory_with_time(bag_path):
    conn = sqlite3.connect(str(bag_path))
    cursor = conn.cursor()

    tf_topic_id = get_topic_id(cursor, "/tf")

    if tf_topic_id is None:
        conn.close()
        raise RuntimeError(f"/tf topic not found in rosbag: {bag_path}")

    cursor.execute(
        "SELECT timestamp, data FROM messages WHERE topic_id=? ORDER BY timestamp",
        (tf_topic_id,)
    )

    times = []
    xs = []
    ys = []

    for timestamp, data in cursor.fetchall():
        msg = deserialize_message(data, TFMessage)

        for transform in msg.transforms:
            if (
                transform.header.frame_id == "odom"
                and transform.child_frame_id == "base_link"
            ):
                times.append(timestamp)
                xs.append(transform.transform.translation.x)
                ys.append(transform.transform.translation.y)

    conn.close()

    if len(xs) == 0:
        raise RuntimeError(f"No odom -> base_link transform found: {bag_path}")

    return times, xs, ys


def extract_string_events(bag_path, topic_name):
    conn = sqlite3.connect(str(bag_path))
    cursor = conn.cursor()

    topic_id = get_topic_id(cursor, topic_name)

    if topic_id is None:
        conn.close()
        return []

    cursor.execute(
        "SELECT timestamp, data FROM messages WHERE topic_id=? ORDER BY timestamp",
        (topic_id,)
    )

    events = []

    for timestamp, data in cursor.fetchall():
        msg = deserialize_message(data, String)
        events.append((timestamp, msg.data))

    conn.close()

    return events


def find_nearest_pose(event_time, trajectory_times, xs, ys):
    nearest_idx = min(
        range(len(trajectory_times)),
        key=lambda i: abs(trajectory_times[i] - event_time)
    )

    return xs[nearest_idx], ys[nearest_idx], nearest_idx


def plot_vlm_route_switching():
    pursuit_times, pursuit_xs, pursuit_ys = extract_tf_trajectory_with_time(BAG_PATH)
    point_times, point_xs, point_ys = extract_tf_trajectory_with_time(POINT_BAG_PATH)

    selected_route_events = extract_string_events(BAG_PATH, "/selected_route")
    navigation_stop_events = extract_string_events(BAG_PATH, "/navigation_stop")

    if len(selected_route_events) < 1:
        raise RuntimeError("No /selected_route messages found")

    original_route = selected_route_events[0][1]

    if len(selected_route_events) >= 2:
        vlm_route = selected_route_events[1][1]
        vlm_event_time = selected_route_events[1][0]
    else:
        vlm_route = None
        vlm_event_time = None

    print("\n/selected_route events")
    for t, route in selected_route_events:
        print(t, route)

    print("\n/navigation_stop events")
    for t, data in navigation_stop_events:
        print(t, data)

    plt.figure(figsize=(15, 4))

    # =========================
    # 1. Original route: solid
    # =========================
    if original_route in ROUTES:
        original_points = ROUTES[original_route]
        ox = [p[0] for p in original_points]
        oy = [p[1] for p in original_points]

        plt.plot(
            ox,
            oy,
            linestyle=":",
            linewidth=4.0,
            color=ORIGINAL_ROUTE_COLOR,
            alpha=0.6,
            label=f"Original route ({original_route})",
            zorder=1
        )

        plt.scatter(
            ox,
            oy,
            s=55,
            color=ORIGINAL_ROUTE_COLOR,
            edgecolors="black",
            linewidths=0.5,
            alpha=0.6,
            zorder=2
        )

        # Original goal point
        goal_x, goal_y = original_points[-1]

        plt.scatter(
            goal_x,
            goal_y,
            marker="X",
            s=180,
            color="red",
            edgecolors="black",
            linewidths=1.5,
            label="User goal",
            zorder=8
        )

        # Obstacle marker at wp2 start point
        if "wp2" in ROUTES:
            obstacle_x, obstacle_y = ROUTES["wp2"][0]

            plt.scatter(
                obstacle_x,
                obstacle_y,
                marker="^",
                s=180,
                color="red",
                edgecolors="black",
                linewidths=1.5,
                label="Obstacle at wp2 start",
                zorder=10
            )

            '''plt.text(
                obstacle_x + 0.3,
                obstacle_y + 0.3,
                "Obstacle",
                fontsize=11,
                color="black",
                zorder=11
            )'''

    # =========================
    # 2. VLM route: dashed
    # =========================
    if vlm_route is not None and vlm_route in ROUTES:
        vlm_points = ROUTES[vlm_route]
        vx = [p[0] for p in vlm_points]
        vy = [p[1] for p in vlm_points]

        plt.plot(
            vx,
            vy,
            linestyle="--",
            linewidth=4.0,
            color=VLM_ROUTE_COLOR,
            alpha=0.8,
            label=f"VLM Suggestion ({vlm_route})",
            zorder=3
        )

        plt.scatter(
            vx,
            vy,
            s=55,
            color=VLM_ROUTE_COLOR,
            edgecolors="black",
            linewidths=0.5,
            alpha=0.8,
            zorder=4
        )

    # =========================
    # 3. Actual trajectories
    # =========================
    plt.plot(
        point_xs,
        point_ys,
        linewidth=3.0,
        color=POINT_TRAJECTORY_COLOR,
        alpha=0.8,
        label="Point Follower trajectory",
        zorder=5
    )

    plt.plot(
        pursuit_xs,
        pursuit_ys,
        linewidth=3.0,
        color=PURSUIT_TRAJECTORY_COLOR,
        alpha=0.8,
        label="Pure Pursuit trajectory",
        zorder=6
    )

    # Point start/end
    plt.scatter(
        point_xs[0],
        point_ys[0],
        marker="o",
        s=100,
        color=POINT_TRAJECTORY_COLOR,
        edgecolors="black",
        linewidths=1.5,
        label="Point Start",
        zorder=7
    )

    plt.scatter(
        point_xs[-1],
        point_ys[-1],
        marker="X",
        s=140,
        color=POINT_TRAJECTORY_COLOR,
        edgecolors="black",
        linewidths=1.5,
        label="Point End",
        zorder=8
    )

    # Pursuit start/end
    plt.scatter(
        pursuit_xs[0],
        pursuit_ys[0],
        marker="o",
        s=100,
        color=PURSUIT_TRAJECTORY_COLOR,
        edgecolors="black",
        linewidths=1.5,
        label="Pursuit Start",
        zorder=9
    )

    plt.scatter(
        pursuit_xs[-1],
        pursuit_ys[-1],
        marker="X",
        s=140,
        color=PURSUIT_TRAJECTORY_COLOR,
        edgecolors="black",
        linewidths=1.5,
        label="Pursuit End",
        zorder=10
    )

    # =========================
    # 4. VLM trigger point
    # =========================
    if navigation_stop_events:
        stop_time = navigation_stop_events[0][0]
        stop_x, stop_y, _ = find_nearest_pose(
            stop_time,
            pursuit_times,
            pursuit_xs,
            pursuit_ys
        )

        plt.scatter(
            stop_x,
            stop_y,
            marker="*",
            s=260,
            color="gold",
            edgecolors="black",
            linewidths=1.2,
            label="VLM trigger",
            zorder=9
        )

        '''plt.text(
            stop_x + 0.3,
            stop_y + 0.3,
            "VLM trigger",
            fontsize=11,
            color="black",
            zorder=10
        )'''

    elif vlm_event_time is not None:
        vlm_x, vlm_y, _ = find_nearest_pose(
            vlm_event_time,
            pursuit_times,
            pursuit_xs,
            pursuit_ys
        )

        plt.scatter(
            vlm_x,
            vlm_y,
            marker="*",
            s=260,
            color="gold",
            edgecolors="black",
            linewidths=1.2,
            label="VLM route event",
            zorder=9
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
    plt.title("(a) VLM-Assisted Route Switching", fontsize=17)
    plt.axis("equal")
    plt.grid(True)
    ax.set_xlim(left=-5)
    ax.legend(
        fontsize=12,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        borderaxespad=0.
    )
    plt.subplots_adjust(right=0.72)
    plt.tight_layout()

    save_name = PLOT_DIR / "vlm_route_suggestion2.png"
    plt.savefig(save_name, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"\nSaved: {save_name}")


if __name__ == "__main__":
    plot_vlm_route_switching()