import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
import tf2_ros
from waypoint_routes.routes import ROUTES, VALID_WPS

class PurePursuitFollower(Node):
    def __init__(self):
        super().__init__('pure_pursuit_follower')

        # ===== 기본 설정 =====
        self.cmd_vel_topic = '/sim/cmd_vel'   # 실제 LIMO면 '/cmd_vel'로 변경
        self.robot_frame = 'base_link'
        self.odom_frame = 'odom'

        # ===== Pure Pursuit 설정 =====
        self.lookahead_distance = 1.0      # 앞을 얼마나 볼지 [m]
        self.goal_tolerance = 0.4          # 마지막 목표 도착 판단 거리 [m]

        self.max_linear = 1.5              # 최대 직진 속도
        self.min_linear = 0.12             # 최소 직진 속도
        self.max_angular = 0.9             # 최대 회전 속도

        self.linear_speed = 1.0            # 기본 직진 속도
        self.angular_k = 1.4               # 회전 gain

        # 방향이 많이 틀어졌을 때 속도 줄이는 정도
        self.heading_slowdown_angle = 1.2  # rad

        # 속도 변화 제한
        self.prev_linear = 0.0
        self.prev_angular = 0.0
        self.max_linear_step = 0.04
        self.max_angular_step = 0.08

        # ===== route 정의 =====
        self.routes = ROUTES

        self.active_route_name = None
        self.active_route = []
        self.is_running = False

        # 현재 경로 진행 segment index
        self.closest_segment_idx = 0

        # ===== ROS pub/sub =====
        self.cmd_pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)

        # Mock VLM 또는 edge_control.py가 선택한 wp 수신
        self.route_sub = self.create_subscription(
            String,
            '/selected_route',
            self.selected_route_callback,
            10
        )

        self.route_goal_sub = self.create_subscription(
            String,
            '/selected_route_goal',
            self.selected_route_goal_callback,
            10
        )

        # intent_server 또는 수동 명령으로 들어오는 goal point 수신
        '''self.goal_sub = self.create_subscription(
            String,
            '/intent_goal',
            self.intent_goal_callback,
            10
        )'''

        # 장애물 감지 시 edge_control.py가 보내는 정지 명령 수신
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

        self.get_logger().info("PurePursuitFollower started.")
        self.get_logger().info("/user_intent_goal -> intent_decision_node | wp1/wp2/wp3/wp4/wp5 | /navigation_stop: stop/resume")

    # =========================
    # Topic callbacks
    # =========================
    def selected_route_callback(self, msg):
        route_name = msg.data.strip()

        if route_name not in self.routes:
            self.get_logger().warn(f"Unknown route: {route_name}")
            self.stop_robot()
            self.is_running = False
            return

        self.active_route_name = route_name
        self.active_route = list(self.routes[route_name])

        # 현재 위치에서 가장 가까운 segment부터 시작
        self.closest_segment_idx = 0
        pose = self.get_robot_pose()
        if pose is None:
            self.get_logger().warn("Robot pose is not available. Start route from first segment.")
            self.closest_segment_idx = 0
        else:
            robot_x, robot_y, _ = pose
            robot_pos = (robot_x, robot_y)
            nearest_idx, nearest_proj, nearest_t = self.find_closest_segment(robot_pos)
            self.closest_segment_idx = nearest_idx
            self.get_logger().info(
                f"Nearest segment selected: segment={nearest_idx + 1}/{len(self.active_route) - 1}, "
                f"projection=({nearest_proj[0]:.2f}, {nearest_proj[1]:.2f}), t={nearest_t:.2f}"
            )

        self.is_running = True
        self.prev_linear = 0.0
        self.prev_angular = 0.0

        self.get_logger().info(f"Selected route: {route_name}")
        self.get_logger().info(f"Route points: {len(self.active_route)}")

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
            self.is_running = False
            return

        pose = self.get_robot_pose()
        if pose is None:
            self.get_logger().warn("Robot pose is not available. Cannot create pure pursuit route to intent goal.")
            self.stop_robot()
            self.is_running = False
            return

        robot_x, robot_y, _ = pose

        # Pure Pursuit는 최소 2개 점이 필요하므로 현재 위치 -> goal로 route 생성
        self.active_route_name = "intent_goal"
        self.active_route = [
            (robot_x, robot_y),
            (goal_x, goal_y),
        ]
        self.closest_segment_idx = 0
        self.is_running = True

        self.prev_linear = 0.0
        self.prev_angular = 0.0

        self.get_logger().info(
            f"Intent goal received: ({goal_x}, {goal_y}), start=({robot_x:.2f}, {robot_y:.2f})"
        )'''

    def navigation_stop_callback(self, msg):
        command = msg.data.strip()

        if command == "stop":
            self.get_logger().warn("Navigation stopped by obstacle detection.")
            self.stop_robot()
            self.is_running = False

        elif command == "resume":
            self.get_logger().info("Navigation resume command received.")
            # resume은 기존 active_route가 남아 있을 때만 다시 시작
            if len(self.active_route) >= 2:
                self.is_running = True
                self.prev_linear = 0.0
                self.prev_angular = 0.0
            else:
                self.get_logger().warn("No active route to resume.")

        else:
            self.get_logger().warn(f"Unknown navigation command: {command}")

    def selected_route_goal_callback(self, msg):
        try:
            raw = msg.data.strip()

            route_part, goal_part = raw.split(";")
            route_name = route_part.strip()

            goal_x_str, goal_y_str = goal_part.split(",")
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
            self.get_logger().warn(f"Unknown route: {route_name}")
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
                f"Goal ({goal_x}, {goal_y}) is not on route {route_name}. "
                f"distance_to_route={dist:.3f}"
            )
            self.stop_robot()
            self.is_running = False
            return

        pose = self.get_robot_pose()
        if pose is None:
            self.get_logger().warn("Robot pose is not available.")
            self.stop_robot()
            self.is_running = False
            return

        robot_x, robot_y, _ = pose

        # Pure Pursuit는 최소 2개 점이 필요
        if len(cut_route) < 2:
            cut_route = [(robot_x, robot_y)] + cut_route

        self.active_route_name = f"{route_name}_to_goal"
        self.active_route = list(cut_route)

        self.closest_segment_idx = 0
        robot_pos = (robot_x, robot_y)
        nearest_idx, nearest_proj, nearest_t = self.find_closest_segment(robot_pos)
        self.closest_segment_idx = nearest_idx

        self.is_running = True
        self.prev_linear = 0.0
        self.prev_angular = 0.0

        self.get_logger().info(
            f"Selected route with goal: {route_name} -> ({goal_x}, {goal_y})"
        )
        self.get_logger().info(
            f"Trimmed route points: {len(self.active_route)}"
        )

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

    def distance(self, p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def project_point_to_segment(self, p, a, b):
        px, py = p
        ax, ay = a
        bx, by = b

        abx = bx - ax
        aby = by - ay
        apx = px - ax
        apy = py - ay

        ab_len_sq = abx * abx + aby * aby

        if ab_len_sq < 1e-6:
            return a, 0.0

        t = (apx * abx + apy * aby) / ab_len_sq
        t = self.clamp(t, 0.0, 1.0)

        proj_x = ax + t * abx
        proj_y = ay + t * aby

        return (proj_x, proj_y), t

    def find_closest_segment(self, robot_pos):
        if len(self.active_route) < 2:
            return 0, self.active_route[0], 0.0

        best_dist = float('inf')
        best_idx = self.closest_segment_idx
        best_proj = self.active_route[0]
        best_t = 0.0

        # 너무 뒤쪽 segment로 돌아가지 않도록 현재 segment 근처부터 탐색
        start_idx = max(0, self.closest_segment_idx - 1)

        for i in range(start_idx, len(self.active_route) - 1):
            a = self.active_route[i]
            b = self.active_route[i + 1]

            proj, t = self.project_point_to_segment(robot_pos, a, b)
            d = self.distance(robot_pos, proj)

            if d < best_dist:
                best_dist = d
                best_idx = i
                best_proj = proj
                best_t = t

        self.closest_segment_idx = best_idx
        return best_idx, best_proj, best_t

    def get_lookahead_point(self, robot_pos):
        seg_idx, proj, _ = self.find_closest_segment(robot_pos)

        remaining = self.lookahead_distance

        current_point = proj
        current_seg_idx = seg_idx

        while current_seg_idx < len(self.active_route) - 1:
            next_point = self.active_route[current_seg_idx + 1]
            seg_len = self.distance(current_point, next_point)

            if seg_len >= remaining:
                ratio = remaining / max(seg_len, 1e-6)

                lx = current_point[0] + ratio * (next_point[0] - current_point[0])
                ly = current_point[1] + ratio * (next_point[1] - current_point[1])

                return lx, ly

            remaining -= seg_len
            current_seg_idx += 1
            current_point = self.active_route[current_seg_idx]

        # 경로 끝까지 lookahead를 못 채우면 마지막 점 반환
        return self.active_route[-1]

    # =========================
    # Main control loop
    # =========================
    def control_loop(self):
        if not self.is_running:
            return

        if len(self.active_route) < 2:
            self.get_logger().warn("Route must have at least 2 points.")
            self.stop_robot()
            self.is_running = False
            return

        pose = self.get_robot_pose()
        if pose is None:
            self.stop_robot()
            return

        robot_x, robot_y, robot_yaw = pose
        robot_pos = (robot_x, robot_y)

        final_goal = self.active_route[-1]
        final_dist = self.distance(robot_pos, final_goal)

        if final_dist < self.goal_tolerance:
            self.get_logger().info(f"Route {self.active_route_name} completed.")
            self.stop_robot()
            self.is_running = False
            return

        lookahead_x, lookahead_y = self.get_lookahead_point(robot_pos)

        dx = lookahead_x - robot_x
        dy = lookahead_y - robot_y

        target_yaw = math.atan2(dy, dx)
        yaw_error = self.normalize_angle(target_yaw - robot_yaw)

        # 방향 오차가 크면 직진 속도를 자동으로 줄임
        heading_factor = max(
            0.0,
            1.0 - abs(yaw_error) / self.heading_slowdown_angle
        )

        # 마지막 목표에 가까워지면 감속
        goal_factor = min(1.0, final_dist / 1.5)

        target_linear = self.linear_speed * heading_factor * goal_factor

        if target_linear > 0.02:
            target_linear = max(target_linear, self.min_linear)

        target_linear = self.clamp(
            target_linear,
            0.0,
            self.max_linear
        )

        target_angular = self.clamp(
            self.angular_k * yaw_error,
            -self.max_angular,
            self.max_angular
        )

        cmd = Twist()

        cmd.linear.x = self.limit_step(
            target_linear,
            self.prev_linear,
            self.max_linear_step
        )

        cmd.angular.z = self.limit_step(
            target_angular,
            self.prev_angular,
            self.max_angular_step
        )

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
    node = PurePursuitFollower()

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