import math

import rclpy
from rclpy.node import Node

from std_msgs.msg import String
from geometry_msgs.msg import Twist

import tf2_ros


class LookaheadFollower(Node):
    def __init__(self):
        super().__init__('lookahead_follower')

        # ===== 기본 설정 =====
        self.cmd_vel_topic = '/sim/cmd_vel'   # 실제 LIMO면 '/cmd_vel'로 변경
        self.robot_frame = 'base_link'
        self.odom_frame = 'odom'

        # ===== 주행 설정 =====
        self.goal_tolerance = 0.4        # waypoint 도착 판단 거리 [m]
        self.linear_k = 1.2              # 직진 속도 gain
        self.angular_k = 0.7             # 회전 속도 gain

        self.max_linear = 1.5            # 최대 직진 속도
        self.min_linear = 0.08           # 최소 직진 속도
        self.max_angular = 0.8           # 최대 회전 속도

        self.heading_threshold = 0.8     # 이 값보다 방향 차이가 크면 감속
        self.lookahead_steps = 1         # 현재 waypoint보다 몇 개 앞을 볼지. 1 또는 2 추천

        # 속도 변화 제한: 급격한 흔들림 감소
        self.prev_linear = 0.0
        self.prev_angular = 0.0
        self.max_linear_step = 0.06
        self.max_angular_step = 0.08

        # ===== wp route 정의 =====
        self.routes = {
            "wp1": [
                (9.0, 5.0),
                (11.0, 5.0),
                (13.0, 5.0),
                (15.0, 5.0),
                (17.0, 5.0),
                (17.0, 3.0),
                (17.0, 2.0),
                (17.0, 0.0),
                (19.0, 0.0),
                (21.0, 0.0),
                (21.0, 1.0),
            ],
            "wp2": [
                (9.0, 0.0),
                (11.0, 0.0),
                (13.0, 0.0),
                (15.0, 0.0),
                (17.0, 0.0),
                (19.0, 0.0),
                (21.0, 0.0),
                (21.0, 1.0),
            ],
            "wp3": [
                (9.0, -5.0),
                (11.0, -5.0),
                (13.0, -5.0),
                (15.0, -5.0),
                (17.0, -5.0),
                (19.0, -5.0),
                (21.0, -5.0),
                (21.0, -3.0),
                (21.0, -2.0),
                (21.0, 0.0),
                (21.0, 1.0),
            ],
        }

        self.active_route_name = None
        self.active_route = []
        self.current_idx = 0
        self.is_running = False

        # ===== ROS pub/sub =====
        self.cmd_pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)

        self.route_sub = self.create_subscription(
            String,
            '/selected_route',
            self.selected_route_callback,
            10
        )

        self.goal_sub = self.create_subscription(
            String,
            '/intent_goal',
            self.intent_goal_callback,
            10
        )

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

        self.get_logger().info("LookaheadFollower started.")
        self.get_logger().info("/intent_goal: 'x,y' | /selected_route: wp1/wp2/wp3 | /navigation_stop: stop/resume")

    def selected_route_callback(self, msg):
        route_name = msg.data.strip()

        if route_name not in self.routes:
            self.get_logger().warn(f"Unknown route: {route_name}")
            self.stop_robot()
            self.is_running = False
            return

        self.active_route_name = route_name
        self.active_route = self.routes[route_name]

        pose = self.get_robot_pose()
        if pose is None:
            self.get_logger().warn("Robot pose is not available. Start route from first waypoint.")
            self.current_idx = 0
        else:
            robot_x, robot_y, _ = pose
            nearest_idx, nearest_dist = self.find_nearest_waypoint_idx(
                self.active_route,
                robot_x,
                robot_y
            )

            # 이미 가까운 waypoint라면 다음 waypoint부터 시작
            if nearest_dist < self.goal_tolerance and nearest_idx < len(self.active_route) - 1:
                self.current_idx = nearest_idx + 1
            else:
                self.current_idx = nearest_idx

            self.get_logger().info(
                f"Nearest waypoint selected: start_index={self.current_idx + 1}/"
                f"{len(self.active_route)}, nearest_dist={nearest_dist:.2f} m"
            )

        self.is_running = True
        self.prev_linear = 0.0
        self.prev_angular = 0.0

        self.get_logger().info(f"Selected route: {route_name}")
        self.get_logger().info(f"Total waypoints: {len(self.active_route)}")

    def intent_goal_callback(self, msg):
        try:
            raw = msg.data.strip()
            x_str, y_str = raw.split(',')
            goal_x = float(x_str)
            goal_y = float(y_str)
        except Exception as e:
            self.get_logger().warn(f"Invalid intent goal: {msg.data}. Use 'x,y'. error={e}")
            self.stop_robot()
            self.is_running = False
            return

        # intent goal은 현재 위치를 시작점으로 넣어 2점 경로로 구성
        pose = self.get_robot_pose()
        if pose is None:
            self.active_route = [(goal_x, goal_y)]
            self.current_idx = 0
        else:
            robot_x, robot_y, _ = pose
            self.active_route = [(robot_x, robot_y), (goal_x, goal_y)]
            self.current_idx = 1

        self.active_route_name = 'intent_goal'
        self.is_running = True
        self.prev_linear = 0.0
        self.prev_angular = 0.0

        self.get_logger().info(f"Intent goal received: ({goal_x}, {goal_y})")

    def navigation_stop_callback(self, msg):
        command = msg.data.strip()

        if command == 'stop':
            self.get_logger().warn("Navigation stopped by obstacle detection.")
            self.stop_robot()
            self.is_running = False

        elif command == 'resume':
            self.get_logger().info("Navigation resume command received.")
            if self.active_route:
                self.is_running = True

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
            self.get_logger().warn(f"TF lookup failed: {e}")
            return None

    def normalize_angle(self, angle):
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def clamp(self, value, min_value, max_value):
        return max(min(value, max_value), min_value)

    def limit_step(self, target, prev, max_step):
        if target > prev + max_step:
            return prev + max_step
        if target < prev - max_step:
            return prev - max_step
        return target

    def distance_xy(self, x1, y1, x2, y2):
        return math.hypot(x2 - x1, y2 - y1)

    def find_nearest_waypoint_idx(self, route, robot_x, robot_y):
        min_dist = float('inf')
        nearest_idx = 0

        for i, (wx, wy) in enumerate(route):
            dist = self.distance_xy(robot_x, robot_y, wx, wy)
            if dist < min_dist:
                min_dist = dist
                nearest_idx = i

        return nearest_idx, min_dist

    def control_loop(self):
        if not self.is_running:
            return

        if not self.active_route:
            return

        pose = self.get_robot_pose()
        if pose is None:
            self.stop_robot()
            return

        robot_x, robot_y, robot_yaw = pose

        if self.current_idx >= len(self.active_route):
            self.get_logger().info(f"Route {self.active_route_name} completed.")
            self.stop_robot()
            self.is_running = False
            return

        # ===== 1) 도착 판정은 current_idx waypoint 기준 =====
        check_x, check_y = self.active_route[self.current_idx]
        check_distance = self.distance_xy(robot_x, robot_y, check_x, check_y)

        if check_distance < self.goal_tolerance:
            self.get_logger().info(
                f"Reached waypoint {self.current_idx + 1}/{len(self.active_route)} "
                f"of {self.active_route_name}"
            )
            self.current_idx += 1

            if self.current_idx >= len(self.active_route):
                self.get_logger().info(f"Route {self.active_route_name} completed.")
                self.stop_robot()
                self.is_running = False

            return

        # ===== 2) 조향 목표는 current_idx보다 lookahead_steps만큼 앞의 waypoint =====
        target_idx = min(
            self.current_idx + self.lookahead_steps,
            len(self.active_route) - 1
        )

        target_x, target_y = self.active_route[target_idx]

        dx = target_x - robot_x
        dy = target_y - robot_y
        target_distance = math.hypot(dx, dy)

        target_yaw = math.atan2(dy, dx)
        yaw_error = self.normalize_angle(target_yaw - robot_yaw)

        # 방향이 많이 틀어져 있으면 속도 줄임
        heading_factor = max(
            0.0,
            1.0 - abs(yaw_error) / self.heading_threshold
        )

        # 마지막 목적지에 가까워지면 감속
        final_x, final_y = self.active_route[-1]
        final_dist = self.distance_xy(robot_x, robot_y, final_x, final_y)
        goal_factor = min(1.0, final_dist / 1.5)

        target_linear = self.linear_k * target_distance * heading_factor * goal_factor

        if target_linear > 0.02:
            target_linear = max(target_linear, self.min_linear)

        target_linear = self.clamp(target_linear, 0.0, self.max_linear)
        target_angular = self.clamp(
            self.angular_k * yaw_error,
            -self.max_angular,
            self.max_angular
        )

        cmd = Twist()
        cmd.linear.x = self.limit_step(target_linear, self.prev_linear, self.max_linear_step)
        cmd.angular.z = self.limit_step(target_angular, self.prev_angular, self.max_angular_step)

        self.prev_linear = cmd.linear.x
        self.prev_angular = cmd.angular.z

        self.cmd_pub.publish(cmd)

    def stop_robot(self):
        cmd = Twist()
        cmd.linear.x = 0.0
        cmd.angular.z = 0.0
        self.cmd_pub.publish(cmd)

        self.prev_linear = 0.0
        self.prev_angular = 0.0


def main():
    rclpy.init()
    node = LookaheadFollower()

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
