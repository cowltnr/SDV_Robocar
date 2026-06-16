import sqlite3
from pathlib import Path

from rclpy.serialization import deserialize_message
from geometry_msgs.msg import Twist


BAG_ROOT = Path("../rosbag")
PLOT_DIR = Path("plot")
PLOT_DIR.mkdir(parents=True, exist_ok=True)

ROUTES = ["wp1", "wp2", "wp3", "wp4", "wp5"]
METHODS = ["point", "pursuit"]

LINEAR_THRESHOLD = 0.05
ANGULAR_THRESHOLD = 0.05
MIN_STOP_DURATION = 0.2


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


def count_full_stops(times, linear_x, angular_z):
    stop_count = 0
    was_moving = False
    stop_start_time = None
    counted_current_stop = False

    for t, v, w in zip(times, linear_x, angular_z):
        # linear와 angular가 모두 작을 때만 완전 정지
        is_moving = abs(v) > LINEAR_THRESHOLD or abs(w) > ANGULAR_THRESHOLD
        is_stopped = not is_moving

        if is_moving:
            was_moving = True
            stop_start_time = None
            counted_current_stop = False

        elif is_stopped and was_moving:
            if stop_start_time is None:
                stop_start_time = t

            stop_duration = t - stop_start_time

            if stop_duration >= MIN_STOP_DURATION and not counted_current_stop:
                stop_count += 1
                counted_current_stop = True

    return stop_count


def count_linear_stops(times, linear_x):
    stop_count = 0
    was_moving = False
    stop_start_time = None
    counted_current_stop = False

    for t, v in zip(times, linear_x):
        # linear.x 기준으로 전진 정지 판단
        is_moving = abs(v) > LINEAR_THRESHOLD
        is_stopped = not is_moving

        if is_moving:
            was_moving = True
            stop_start_time = None
            counted_current_stop = False

        elif is_stopped and was_moving:
            if stop_start_time is None:
                stop_start_time = t

            stop_duration = t - stop_start_time

            if stop_duration >= MIN_STOP_DURATION and not counted_current_stop:
                stop_count += 1
                counted_current_stop = True

    return stop_count


def main():
    rows = []

    print("\nStop Count")
    print("-" * 75)
    print(
        f"{'Route':<8} "
        f"{'Point Full':>12} {'Point Linear':>14} "
        f"{'Pursuit Full':>14} {'Pursuit Linear':>16}"
    )
    print("-" * 75)

    for route in ROUTES:
        row = {"route": route}

        for method in METHODS:
            bag_path = BAG_ROOT / f"{method}_{route}" / f"{method}_{route}_0.db3"

            times, linear_x, angular_z = extract_cmd_vel(str(bag_path))
            full_stop_count = count_full_stops(times, linear_x, angular_z)
            linear_stop_count = count_linear_stops(times, linear_x)

            row[f"{method}_full"] = full_stop_count
            row[f"{method}_linear"] = linear_stop_count

        rows.append(row)

        print(
            f"{route:<8} "
            f"{row['point_full']:>12} {row['point_linear']:>14} "
            f"{row['pursuit_full']:>14} {row['pursuit_linear']:>16}"
        )

    print("-" * 45)

    csv_path = PLOT_DIR / "stop_count_table.csv"

    with open(csv_path, "w") as f:
        f.write("# Stop Count Definition\n")
        f.write("# Full Stop Count: abs(linear.x) <= 0.05 and abs(angular.z) <= 0.05 for at least 0.2 s\n")
        f.write("# Linear Stop Count: abs(linear.x) <= 0.05 for at least 0.2 s\n")
        f.write("# Unit: count\n")
        f.write("\n")

        f.write(
            "Route,"
            "Point Full Stop Count,Point Linear Stop Count,"
            "Pure Pursuit Full Stop Count,Pure Pursuit Linear Stop Count\n"
        )

        for row in rows:
            f.write(
                f"{row['route']},"
                f"{row['point_full']},{row['point_linear']},"
                f"{row['pursuit_full']},{row['pursuit_linear']}\n"
            )

    print(f"\nSaved: {csv_path}")


if __name__ == "__main__":
    main()