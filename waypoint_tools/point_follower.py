import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
import tf2_ros
from waypoint_routes.routes import ROUTES, VALID_WPS


class RouteFollower(Node):
    def __init__(self):
        super().__init__('route_follower')

        # ===== 설정 =====
        self.cmd_vel_topic = '/sim/cmd_vel'  # 실제 LIMO면 '/cmd_vel'로 바꾸기
        self.robot_frame = 'base_link'
        self.odom_frame = 'odom'

        self.goal_tolerance = 0.4  # waypoint 도착 판단 거리 [m]
        self.linear_k = 2  # 직진 속도 gain
        self.angular_k = 0.7  # 회전 속도 gain

        self.max_linear = 2.0  # 최대 직진 속도
        self.max_angular = 1.0  # 최대 회전 속도

        self.heading_threshold = 0.5  # 방향 차이가 크면 회전 우선 [rad]

        '''self.goal_sub = self.create_subscription(
            String,
            '/intent_goal',
            self.intent_goal_callback,
            10
        )'''

        self.nav_stop_sub = self.create_subscription(
            String,
            '/navigation_stop',
            self.navigation_stop_callback,
            10
        )

        # ===== wp route 정의 =====
        self.routes = ROUTES

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

        # ===== TF =====
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        self.timer = self.create_timer(0.05, self.control_loop)  # 20Hz

        self.get_logger().info("RouteFollower started.")
        self.get_logger().info("Publish route name to /selected_route: wp1, wp2, wp3, wp4, or wp5")

    def selected_route_callback(self, msg):
        route_name = msg.data.strip()

        if route_name not in self.routes:
            self.get_logger().warn(f"Unknown route: {route_name}")
            self.stop_robot()
            return

        self.active_route_name = route_name
        self.active_route = self.routes[route_name]

        pose = self.get_robot_pose()

        if pose is None:
            self.get_logger().warn(
                "Robot pose is not available. Start route from first waypoint."
            )
            self.current_idx = 0
        else:
            robot_x, robot_y, _ = pose

            nearest_idx, nearest_dist = self.find_nearest_waypoint_idx(
                self.active_route,
                robot_x,
                robot_y
            )

            if nearest_dist < self.goal_tolerance and nearest_idx < len(self.active_route) - 1:
                self.current_idx = nearest_idx + 1
            else:
                self.current_idx = nearest_idx

            self.get_logger().info(
                f"Nearest waypoint selected: start_index={self.current_idx + 1}/"
                f"{len(self.active_route)}, nearest_dist={nearest_dist:.2f} m"
            )

        self.is_running = True

        self.get_logger().info(f"Selected route: {route_name}")
        self.get_logger().info(f"Total waypoints: {len(self.active_route)}")

    '''def intent_goal_callback(self, msg):
        try:
            raw = msg.data.strip()
            x_str, y_str = raw.split(",")
            goal_x = float(x_str)
            goal_y = float(y_str)

        except Exception as e:
            self.get_logger().warn(
                f"Invalid intent goal: {msg.data}. Use 'x,y'. error={e}"
            )
            self.stop_robot()
            return

        self.active_route_name = "intent_goal"
        self.active_route = [(goal_x, goal_y)]
        self.current_idx = 0
        self.is_running = True

        self.get_logger().info(
            f"Intent goal received: ({goal_x}, {goal_y})"
        )'''

    def navigation_stop_callback(self, msg):
        command = msg.data.strip()

        if command == "stop":
            self.get_logger().warn("Navigation stopped by obstacle detection.")
            self.stop_robot()
            self.is_running = False

        elif command == "resume":
            self.get_logger().info("Navigation resume command received.")

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

    def find_nearest_waypoint_idx(self, route, robot_x, robot_y):
        min_dist = float("inf")
        nearest_idx = 0

        for i, (wx, wy) in enumerate(route):
            dx = wx - robot_x
            dy = wy - robot_y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < min_dist:
                min_dist = dist
                nearest_idx = i

        return nearest_idx, min_dist

    def control_loop(self):
        if not self.is_running:
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

        goal_x, goal_y = self.active_route[self.current_idx]

        dx = goal_x - robot_x
        dy = goal_y - robot_y
        distance = math.sqrt(dx * dx + dy * dy)

        target_yaw = math.atan2(dy, dx)
        yaw_error = self.normalize_angle(target_yaw - robot_yaw)

        # waypoint 도착
        if distance < self.goal_tolerance:
            self.get_logger().info(
                f"Reached waypoint {self.current_idx + 1}/{len(self.active_route)} "
                f"of {self.active_route_name}"
            )
            self.current_idx += 1

            if self.current_idx >= len(self.active_route):
                self.stop_robot()

            return

        cmd = Twist()

        # 방향 차이가 크면 회전 먼저
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
                0.08,
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
    node = RouteFollower()

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
