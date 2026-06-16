import sqlite3
from pathlib import Path

from rclpy.serialization import deserialize_message
from geometry_msgs.msg import Twist


BAG_ROOT = Path("../rosbag")
PLOT_DIR = Path("plot")
PLOT_DIR.mkdir(parents=True, exist_ok=True)

ROUTES = ["wp1", "wp2", "wp3", "wp4", "wp5"]
METHODS = ["point", "pursuit"]

MOVING_THRESHOLD = 0.01


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

    times = []
    linear_x = []
    angular_z = []

    for timestamp, data in rows:
        msg = deserialize_message(data, Twist)
        times.append(timestamp * 1e-9)
        linear_x.append(msg.linear.x)
        angular_z.append(msg.angular.z)

    return times, linear_x, angular_z


def compute_travel_time(times, linear_x, angular_z, threshold=MOVING_THRESHOLD):
    moving_indices = [
        i for i, (v, w) in enumerate(zip(linear_x, angular_z))
        if abs(v) > threshold or abs(w) > threshold
    ]

    if not moving_indices:
        return 0.0

    start_idx = moving_indices[0]
    end_idx = moving_indices[-1]

    return times[end_idx] - times[start_idx]


def main():
    rows = []

    print("\nTravel Time [s]")
    print("-" * 50)
    print(f"{'Route':<8} {'Point [s]':>12} {'Pursuit [s]':>14}")
    print("-" * 50)

    for route in ROUTES:
        result = {"route": route}

        for method in METHODS:
            bag_path = BAG_ROOT / f"{method}_{route}" / f"{method}_{route}_0.db3"

            times, linear_x, angular_z = extract_cmd_vel(str(bag_path))
            travel_time = compute_travel_time(times, linear_x, angular_z)

            result[method] = travel_time

        rows.append(result)

        print(
            f"{route:<8} "
            f"{result['point']:>12.2f} "
            f"{result['pursuit']:>14.2f}"
        )

    print("-" * 50)

    csv_path = PLOT_DIR / "travel_time_table.csv"

    with open(csv_path, "w") as f:
        f.write("Route,Point Follower [s],Pure Pursuit [s]\n")
        for row in rows:
            f.write("# Travel Time Definition\n")
            f.write("# Route set: wp1, wp2, wp3, wp4, wp5\n")
            f.write("# Controllers compared: Point Follower and Pure Pursuit Follower\n")
            f.write("# Start pose: identical for all trials\n")
            f.write("# Same route, same velocity limits, same goal tolerance\n")
            f.write("# Trajectory source: /sim/cmd_vel\n")
            f.write("# Travel Time = elapsed time between first motion command and last motion command\n")
            f.write("# Motion threshold: abs(linear.x) > 0.01 or abs(angular.z) > 0.01\n")
            f.write("# Rosbag recording duration is NOT used\n")
            f.write("# Unit: second [s]\n")
            f.write("\n")

            f.write("Route,Point Follower [s],Pure Pursuit [s]\n")

            for row in rows:
                f.write(
                    f"{row['route']},"
                    f"{row['point']:.2f},"
                    f"{row['pursuit']:.2f}\n"
                )

    print(f"\nSaved: {csv_path}")


if __name__ == "__main__":
    main()