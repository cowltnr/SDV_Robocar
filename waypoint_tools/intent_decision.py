import math
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from waypoint_routes.routes import ROUTES


class IntentDecisionNode(Node):
    def __init__(self):
        super().__init__("intent_decision_node")

        # ===== 설정 =====
        self.goal_match_tolerance = 0.5  # [m] goal이 route 선분에서 이 거리 이내면 해당 wp에 속한다고 판단

        self.user_intent_topic = "/user_intent_goal"
        self.selected_route_topic = "/selected_route"
        self.intent_feedback_topic = "/intent_feedback"

        self.routes = ROUTES

        # ===== ROS pub/sub =====
        self.intent_sub = self.create_subscription(
            String,
            self.user_intent_topic,
            self.intent_callback,
            10
        )

        self.route_pub = self.create_publisher(
            String,
            self.selected_route_topic,
            10
        )

        self.feedback_pub = self.create_publisher(
            String,
            self.intent_feedback_topic,
            10
        )

        self.get_logger().info("IntentDecisionNode started.")
        self.get_logger().info(
            "Publish goal point to /user_intent_goal, example: \"21.0,1.0\""
        )
        self.get_logger().info(
            f"Available routes: {', '.join(self.routes.keys())}"
        )

    def intent_callback(self, msg):
        raw_goal = msg.data.strip()

        goal = self.parse_goal(raw_goal)

        if goal is None:
            feedback = (
                f"Invalid goal format: '{raw_goal}'. "
                "Use 'x,y' format. Example: '21.0,1.0'"
            )
            self.publish_feedback(feedback)
            self.get_logger().warn(feedback)
            return

        goal_x, goal_y = goal

        self.get_logger().info(
            f"Received user intent goal: ({goal_x:.2f}, {goal_y:.2f})"
        )

        candidates = self.find_candidate_routes(goal)

        if not candidates:
            feedback = (
                f"Goal ({goal_x:.2f}, {goal_y:.2f}) is not included in any "
                f"available waypoint route within {self.goal_match_tolerance:.2f} m. "
                "Please enter another intent goal."
            )

            self.publish_feedback(feedback)
            self.get_logger().warn(feedback)
            return

        selected = self.select_best_route(candidates)

        selected_wp = selected["wp"]
        selected_dist = selected["distance"]
        selected_count = selected["point_count"]

        route_msg = String()
        route_msg.data = selected_wp
        self.route_pub.publish(route_msg)

        feedback = (
            f"Goal ({goal_x:.2f}, {goal_y:.2f}) is valid. "
            f"Selected route: {selected_wp} "
            f"(points={selected_count}, distance_to_route={selected_dist:.3f} m)."
        )

        self.publish_feedback(feedback)

        self.get_logger().info(
            f"Candidates: {self.format_candidates(candidates)}"
        )
        self.get_logger().info(feedback)
        self.get_logger().info(
            f"Published /selected_route <- {selected_wp}"
        )

    def parse_goal(self, raw):
        try:
            x_str, y_str = raw.split(",")
            goal_x = float(x_str.strip())
            goal_y = float(y_str.strip())
            return goal_x, goal_y

        except Exception:
            return None

    def find_candidate_routes(self, goal):
        candidates = []

        for wp_name, route in self.routes.items():
            if len(route) < 2:
                continue

            min_dist = self.min_distance_to_route(goal, route)

            if min_dist <= self.goal_match_tolerance:
                candidates.append(
                    {
                        "wp": wp_name,
                        "point_count": len(route),
                        "distance": min_dist,
                    }
                )

        return candidates

    def select_best_route(self, candidates):
        # 1순위: point 수가 적은 route
        # 2순위: goal과 route 사이 거리가 더 가까운 route
        # 3순위: wp 이름 순서
        return min(
            candidates,
            key=lambda item: (
                item["point_count"],
                item["distance"],
                item["wp"]
            )
        )

    def min_distance_to_route(self, goal, route):
        goal_x, goal_y = goal
        min_dist = float("inf")

        for i in range(len(route) - 1):
            ax, ay = route[i]
            bx, by = route[i + 1]

            dist = self.point_to_segment_distance(
                goal_x,
                goal_y,
                ax,
                ay,
                bx,
                by
            )

            if dist < min_dist:
                min_dist = dist

        return min_dist

    def point_to_segment_distance(self, px, py, ax, ay, bx, by):
        abx = bx - ax
        aby = by - ay

        apx = px - ax
        apy = py - ay

        ab_len_sq = abx * abx + aby * aby

        # 선분 길이가 거의 0이면 점-점 거리로 계산
        if ab_len_sq < 1e-9:
            return math.hypot(px - ax, py - ay)

        t = (apx * abx + apy * aby) / ab_len_sq
        t = max(0.0, min(1.0, t))

        proj_x = ax + t * abx
        proj_y = ay + t * aby

        return math.hypot(px - proj_x, py - proj_y)

    def publish_feedback(self, text):
        msg = String()
        msg.data = text
        self.feedback_pub.publish(msg)

    def format_candidates(self, candidates):
        parts = []

        for item in candidates:
            parts.append(
                f"{item['wp']}(points={item['point_count']}, "
                f"dist={item['distance']:.3f})"
            )

        return ", ".join(parts)


def main():
    rclpy.init()
    node = IntentDecisionNode()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()