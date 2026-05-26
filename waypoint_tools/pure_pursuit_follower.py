import math

import rclpy
from rclpy.node import Node

from std_msgs.msg import String
from geometry_msgs.msg import Twist

import tf2_ros


class PurePursuitFollower(Node):
    def __init__(self):
        super().__init__('pure_pursuit_follower')

        # ===== 기본 설정 =====
        self.cmd_vel_topic = '/sim/cmd_vel'   # 실제 LIMO면 '/cmd_vel'로 변경
        self.robot_frame = 'base_link'
        self.odom_frame = 'odom'

        # ===== Pure Pursuit 설정 =====
        self.lookahead_distance = 1.0      # 앞을 얼마나 볼지 [m]
        self.goal_tolerance = 0.35         # 마지막 목표 도착 판단 거리 [m]

        self.max_linear = 1.5             # 최대 직진 속도
        self.min_linear = 0.12             # 최소 직진 속도
        self.max_angular = 0.9             # 최대 회전 속도

        self.linear_speed = 1.0           # 기본 직진 속도
        self.angular_k = 1.4               # 회전 gain

        # 방향이 많이 틀어졌을 때 속도 줄이는 정도
        self.heading_slowdown_angle = 1.2  # rad

        # 속도 변화 제한
        self.prev_linear = 0.0
        self.prev_angular = 0.0
        self.max_linear_step = 0.04
        self.max_angular_step = 0.08

        # ===== route 정의 =====
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
        self.is_running = False

        # 현재 경로 진행 인덱스
        self.closest_segment_idx = 0

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

        self.timer = self.create_timer(0.05, self.control_loop)  # 20 Hz

        self.get_logger().info("PurePursuitFollower started.")
        self.get_logger().info("Publish wp1/wp2/wp3 to /selected_route.")

    def selected_route_callback(self, msg):
        route_name = msg.data.strip()

        if route_name not in self.routes:
            self.get_logger().warn(f"Unknown route: {route_name}")
            self.stop_robot()
            self.is_running = False
            return

        self.active_route_name = route_name
        self.active_route = self.routes[route_name]
        self.closest_segment_idx = 0
        self.is_running = True

        self.prev_linear = 0.0
        self.prev_angular = 0.0

        self.get_logger().info(f"Selected route: {route_name}")
        self.get_logger().info(f"Route points: {len(self.active_route)}")

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
        seg_idx, proj, t = self.find_closest_segment(robot_pos)

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