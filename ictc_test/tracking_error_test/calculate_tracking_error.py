import sys
import math
import sqlite3
from pathlib import Path

from rclpy.serialization import deserialize_message
from tf2_msgs.msg import TFMessage


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from waypoint_tools.waypoint_routes.routes import ROUTES


BAG_ROOT = Path("../rosbag")
PLOT_DIR = Path("plot")
PLOT_DIR.mkdir(parents=True, exist_ok=True)

ROUTE_NAMES = ["wp1", "wp2", "wp3", "wp4", "wp5"]
METHODS = ["point", "pursuit"]

EVAL_START_X = 9.0


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

    for _, data in cursor.fetchall():
        msg = deserialize_message(data, TFMessage)

        for transform in msg.transforms:
            if transform.header.frame_id == "odom" and transform.child_frame_id == "base_link":
                xs.append(transform.transform.translation.x)
                ys.append(transform.transform.translation.y)

    conn.close()

    if len(xs) == 0:
        raise RuntimeError(f"No odom -> base_link transform found: {bag_path}")

    return list(zip(xs, ys))


def distance_point_to_segment(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b

    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay

    ab_len_sq = abx * abx + aby * aby

    if ab_len_sq < 1e-9:
        return math.hypot(px - ax, py - ay)

    t = (apx * abx + apy * aby) / ab_len_sq
    t = max(0.0, min(1.0, t))

    closest_x = ax + t * abx
    closest_y = ay + t * aby

    return math.hypot(px - closest_x, py - closest_y)


def distance_point_to_route(point, route_points):
    min_dist = float("inf")

    for i in range(len(route_points) - 1):
        d = distance_point_to_segment(
            point,
            route_points[i],
            route_points[i + 1]
        )
        min_dist = min(min_dist, d)

    return min_dist


def crop_trajectory_from_x(trajectory, start_x=EVAL_START_X):
    """
    Use trajectory points only after the robot reaches x >= start_x.
    This removes the initial approach segment before entering the reference route.
    """
    for i, (x, y) in enumerate(trajectory):
        if x >= start_x:
            return trajectory[i:]

    raise RuntimeError(f"No trajectory point found with x >= {start_x}")


def compute_tracking_error(trajectory, reference_route):
    errors = []

    for p in trajectory:
        e = distance_point_to_route(p, reference_route)
        errors.append(e)

    mean_error = sum(errors) / len(errors)
    max_error = max(errors)
    rmse_error = math.sqrt(sum(e * e for e in errors) / len(errors))

    return mean_error, max_error, rmse_error


def main():
    rows = []

    print("\nTracking Error [m]")
    print("-" * 90)
    print(
        f"{'Route':<8} "
        f"{'Point Mean':>12} {'Point Max':>12} {'Point RMSE':>12} "
        f"{'Pursuit Mean':>14} {'Pursuit Max':>12} {'Pursuit RMSE':>14}"
    )
    print("-" * 90)

    for route_name in ROUTE_NAMES:
        reference_route = ROUTES[route_name]

        row = {"route": route_name}

        for method in METHODS:
            bag_path = BAG_ROOT / f"{method}_{route_name}" / f"{method}_{route_name}_0.db3"

            trajectory = extract_trajectory(str(bag_path))
            trajectory = crop_trajectory_from_x(trajectory, EVAL_START_X)

            mean_error, max_error, rmse_error = compute_tracking_error(
                trajectory,
                reference_route
            )

            row[f"{method}_mean"] = mean_error
            row[f"{method}_max"] = max_error
            row[f"{method}_rmse"] = rmse_error

        rows.append(row)

        print(
            f"{route_name:<8} "
            f"{row['point_mean']:>12.3f} {row['point_max']:>12.3f} {row['point_rmse']:>12.3f} "
            f"{row['pursuit_mean']:>14.3f} {row['pursuit_max']:>12.3f} {row['pursuit_rmse']:>14.3f}"
        )

    print("-" * 90)

    csv_path = PLOT_DIR / "tracking_error_table.csv"

    with open(csv_path, "w") as f:
        f.write("# Tracking Error Definition\n")
        f.write("# Reference: waypoint route segments (piecewise linear path)\n")
        f.write("# Trajectory source: odom -> base_link transform from /tf\n")
        f.write("# Error metric: shortest Euclidean distance from each trajectory point to the reference route\n")
        f.write("# Mean Error: average cross-track error [m]\n")
        f.write("# Max Error: maximum cross-track error [m]\n")
        f.write("# RMSE: root mean square cross-track error [m]\n")
        f.write("# Unit: meter [m]\n")
        f.write("\n")

        f.write(
            "Route,"
            "Point Mean [m],Point Max [m],Point RMSE [m],"
            "Pure Pursuit Mean [m],Pure Pursuit Max [m],Pure Pursuit RMSE [m]\n"
        )

        for row in rows:
            f.write(
                f"{row['route']},"
                f"{row['point_mean']:.3f},"
                f"{row['point_max']:.3f},"
                f"{row['point_rmse']:.3f},"
                f"{row['pursuit_mean']:.3f},"
                f"{row['pursuit_max']:.3f},"
                f"{row['pursuit_rmse']:.3f}\n"
            )

    print(f"\nSaved: {csv_path}")


if __name__ == "__main__":
    main()