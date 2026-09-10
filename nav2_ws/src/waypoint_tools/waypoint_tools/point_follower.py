import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
import tf2_ros

from waypoint_tools.waypoint_routes.routes import ROUTES


class PointFollower(Node):
    def __init__(self):
        super().__init__('point_follower')

        # ===== Basic settings =====
        self.cmd_vel_topic = '/sim/cmd_vel'  # 실제 LIMO면 '/cmd_vel'로 변경
        self.robot_frame = 'base_link'
        self.odom_frame = 'odom'

        self.goal_tolerance = 0.4  # waypoint 도착 판단 거리 [m]
        self.linear_k = 2.0        # 직진 속도 gain
        self.angular_k = 0.7       # 회전 속도 gain

        self.max_linear = 1.5
        self.max_angular = 0.9
        self.heading_threshold = 0.5  # 방향 차이가 크면 회전 우선 [rad]

        # ===== Route definition =====
        self.routes = ROUTES
        self.active_route_name = None
        self.active_route = []
        self.current_idx = 0
        self.is_running = False

        # ===== ROS pub/sub =====
        self.cmd_pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)

        # Legacy/simple route command: "wp1", "wp2", ...
        self.route_sub = self.create_subscription(
            String,
            '/selected_route',
            self.selected_route_callback,
            10
        )

        # Goal-aware route command from intent_decision or VLM: "wp_name;x,y"
        self.route_goal_sub = self.create_subscription(
            String,
            '/selected_route_goal',
            self.selected_route_goal_callback,
            10
        )

        # Stop command from obstacle detection
        self.nav_stop_sub = self.create_subscription(
            String,
            '/navigation_stop',
            self.navigation_stop_callback,
            10
        )

        # ===== TF =====
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.timer = self.create_timer(0.05, self.control_loop)  # 20 Hz

        self.get_logger().info('PointFollower started.')
        self.get_logger().info('Route command: /selected_route <- wp1..wp5')
        self.get_logger().info('Goal-aware VLM command: /selected_route_goal <- wp_name;x,y')

    # =========================
    # Topic callbacks
    # =========================
    def selected_route_callback(self, msg):
        raw = msg.data.strip()

        # Safety: if goal-aware format is accidentally published to /selected_route,
        # handle it instead of rejecting it.
        if ';' in raw:
            self.get_logger().warn(
                "Received goal-aware command on /selected_route. "
                "Handling it as /selected_route_goal."
            )
            self.selected_route_goal_callback(msg)
            return

        route_name = raw

        if route_name not in self.routes:
            self.get_logger().warn(f'Unknown route: {route_name}')
            self.stop_robot()
            self.is_running = False
            return

        self.active_route_name = route_name
        self.active_route = list(self.routes[route_name])
        self.current_idx = self.get_start_index_from_current_pose(self.active_route)
        self.is_running = True

        self.get_logger().info(f'Selected full route: {route_name}')
        self.get_logger().info(f'Start waypoint index: {self.current_idx + 1}/{len(self.active_route)}')
        self.get_logger().info(f'Total waypoints: {len(self.active_route)}')

    def selected_route_goal_callback(self, msg):
        try:
            raw = msg.data.strip()
            route_part, goal_part = raw.split(';')
            route_name = route_part.strip()

            goal_x_str, goal_y_str = goal_part.split(',')
            goal_x = float(goal_x_str.strip())
            goal_y = float(goal_y_str.strip())

        except Exception as e:
            self.get_logger().warn(
                f"Invalid /selected_route_goal format: {msg.data}. "
                f"Use 'wp_name;x,y'. error={e}"
            )
            self.stop_robot()
            self.is_running = False
            return

        if route_name not in self.routes:
            self.get_logger().warn(f'Unknown route: {route_name}')
            self.stop_robot()
            self.is_running = False
            return

        full_route = self.routes[route_name]

        cut_route, dist = self.cut_route_until_goal(
            full_route,
            goal_x,
            goal_y,
            tolerance=0.5
        )

        if cut_route is None:
            self.get_logger().warn(
                f'Goal ({goal_x}, {goal_y}) is not on route {route_name}. '
                f'distance_to_route={dist:.3f}'
            )
            self.stop_robot()
            self.is_running = False
            return

        self.active_route_name = f'{route_name}_to_goal'
        self.active_route = list(cut_route)
        self.current_idx = self.get_start_index_from_current_pose(self.active_route)
        self.is_running = True

        self.get_logger().info(
            f'VLM/goal-aware route accepted: {route_name} -> ({goal_x}, {goal_y})'
        )
        self.get_logger().info(f'Trimmed route points: {len(self.active_route)}')
        self.get_logger().info(
            f'Start waypoint index: {self.current_idx + 1}/{len(self.active_route)}'
        )

    def navigation_stop_callback(self, msg):
        command = msg.data.strip()

        if command == 'stop':
            self.get_logger().warn('Navigation stopped by obstacle detection.')
            self.stop_robot()
            self.is_running = False

        elif command == 'resume':
            self.get_logger().info('Navigation resume command received.')
            if len(self.active_route) > 0:
                self.current_idx = self.get_start_index_from_current_pose(self.active_route)
                self.is_running = True
            else:
                self.get_logger().warn('No active route to resume.')

        else:
            self.get_logger().warn(f'Unknown navigation command: {command}')

    # =========================
    # Utility functions
    # =========================
    def get_robot_pose(self):
        try:
            tf = self.tf_buffer.lookup_transform(
                self.odom_frame,
                self.robot_frame,
                rclpy.time.Time()
            )

            x = tf.transform.translation.x
            y = tf.transform.translation.y
            q = tf.transform.rotation

            sin_yaw = 2.0 * (q.w * q.z + q.x * q.y)
            cos_yaw = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
            yaw = math.atan2(sin_yaw, cos_yaw)

            return x, y, yaw

        except Exception as e:
            self.get_logger().warn(f'TF lookup failed: {e}')
            return None

    def normalize_angle(self, angle):
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def clamp(self, value, min_value, max_value):
        return max(min(value, max_value), min_value)

    def find_nearest_waypoint_idx(self, route, robot_x, robot_y):
        min_dist = float('inf')
        nearest_idx = 0

        for i, (wx, wy) in enumerate(route):
            dist = math.hypot(wx - robot_x, wy - robot_y)
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i

        return nearest_idx, min_dist

    def get_start_index_from_current_pose(self, route):
        pose = self.get_robot_pose()

        if pose is None:
            self.get_logger().warn('Robot pose is not available. Start route from first waypoint.')
            return 0

        robot_x, robot_y, _ = pose
        nearest_idx, nearest_dist = self.find_nearest_waypoint_idx(route, robot_x, robot_y)

        if nearest_dist < self.goal_tolerance and nearest_idx < len(route) - 1:
            start_idx = nearest_idx + 1
        else:
            start_idx = nearest_idx

        self.get_logger().info(
            f'Nearest waypoint selected: start_index={start_idx + 1}/{len(route)}, '
            f'nearest_dist={nearest_dist:.2f} m'
        )

        return start_idx

    def point_to_segment_distance(self, px, py, ax, ay, bx, by):
        abx = bx - ax
        aby = by - ay
        apx = px - ax
        apy = py - ay
        ab_len_sq = abx * abx + aby * aby

        if ab_len_sq < 1e-9:
            return math.hypot(px - ax, py - ay), 0.0

        t = (apx * abx + apy * aby) / ab_len_sq
        t = self.clamp(t, 0.0, 1.0)

        proj_x = ax + t * abx
        proj_y = ay + t * aby
        dist = math.hypot(px - proj_x, py - proj_y)

        return dist, t

    def cut_route_until_goal(self, route, goal_x, goal_y, tolerance=0.5):
        best_idx = None
        best_dist = float('inf')

        for i in range(len(route) - 1):
            ax, ay = route[i]
            bx, by = route[i + 1]

            dist, _ = self.point_to_segment_distance(goal_x, goal_y, ax, ay, bx, by)

            if dist < best_dist:
                best_dist = dist
                best_idx = i

        if best_idx is None or best_dist > tolerance:
            return None, best_dist

        cut_route = list(route[:best_idx + 1])
        last_x, last_y = cut_route[-1]

        if math.hypot(goal_x - last_x, goal_y - last_y) > 1e-3:
            cut_route.append((goal_x, goal_y))

        return cut_route, best_dist

    # =========================
    # Main control loop
    # =========================
    def control_loop(self):
        if not self.is_running:
            return

        pose = self.get_robot_pose()
        if pose is None:
            self.stop_robot()
            return

        if self.current_idx >= len(self.active_route):
            self.get_logger().info(f'Route {self.active_route_name} completed.')
            self.stop_robot()
            self.is_running = False
            return

        robot_x, robot_y, robot_yaw = pose
        goal_x, goal_y = self.active_route[self.current_idx]

        dx = goal_x - robot_x
        dy = goal_y - robot_y
        distance = math.hypot(dx, dy)

        target_yaw = math.atan2(dy, dx)
        yaw_error = self.normalize_angle(target_yaw - robot_yaw)

        if distance < self.goal_tolerance:
            self.get_logger().info(
                f'Reached waypoint {self.current_idx + 1}/{len(self.active_route)} '
                f'of {self.active_route_name}'
            )
            self.current_idx += 1

            if self.current_idx >= len(self.active_route):
                self.get_logger().info(f'Route {self.active_route_name} completed.')
                self.stop_robot()
                self.is_running = False

            return

        cmd = Twist()

        if abs(yaw_error) > self.heading_threshold:
            cmd.linear.x = 0.0
            cmd.angular.z = self.clamp(
                self.angular_k * yaw_error,
                -self.max_angular,
                self.max_angular
            )
        else:
            cmd.linear.x = self.clamp(
                self.linear_k * distance,
                0.12,
                self.max_linear
            )
            cmd.angular.z = self.clamp(
                0.5 * self.angular_k * yaw_error,
                -0.5,
                0.5
            )

        self.cmd_pub.publish(cmd)

    def stop_robot(self):
        cmd = Twist()
        cmd.linear.x = 0.0
        cmd.angular.z = 0.0
        self.cmd_pub.publish(cmd)


def main():
    rclpy.init()
    node = PointFollower()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_robot()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
