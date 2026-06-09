import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point
from waypoint_routes.routes import ROUTES, VALID_WPS

class WaypointViewer(Node):
    def __init__(self):
        super().__init__('waypoint_viewer')

        self.pub = self.create_publisher(MarkerArray, '/waypoint_markers', 10)
        self.timer = self.create_timer(1.0, self.publish_routes)

        self.routes = ROUTES

        self.colors = {
            "wp1": (1.0, 0.0, 0.0),
            "wp2": (0.0, 1.0, 0.0),
            "wp3": (0.0, 0.0, 1.0),
            "wp4": (1.0, 1.0, 0.0),
            "wp5": (1.0, 0.0, 1.0),
        }

        # marker 시각화용 offset
        # 실제 waypoint 좌표는 바뀌지 않음
        self.visual_offsets = {
            "wp1": 0.08,
            "wp2": -0.08,
            "wp3": -0.16,
            "wp4": 0.16,
            "wp5": -0.24,
        }

        # 지정한 위치에만 wp 이름 표시
        self.wp_name_labels = {
            (8.5, 4.0): "wp1",
            (8.5, 0.0): "wp2",
            (8.5, -5.0): "wp3",
            (8.5, 5.0): "wp4",
            (8.5, -6.0): "wp5",
        }

    def get_color(self, name):
        return self.colors[name]

    def make_marker(self, name, marker_id, marker_type, points):
        marker = Marker()
        marker.header.frame_id = "odom"
        marker.header.stamp = self.get_clock().now().to_msg()

        marker.ns = name
        marker.id = marker_id
        marker.type = marker_type
        marker.action = Marker.ADD

        marker.pose.orientation.w = 1.0

        r, g, b = self.get_color(name)
        marker.color.r = r
        marker.color.g = g
        marker.color.b = b

        if marker_type == Marker.POINTS:
            marker.scale.x = 0.30
            marker.scale.y = 0.30
            marker.color.a = 0.65
        else:
            marker.scale.x = 0.12
            marker.color.a = 0.45

        offset_y = self.visual_offsets[name]

        for x, y in points:
            p = Point()
            p.x = float(x)
            p.y = float(y) + offset_y
            p.z = 0.1
            marker.points.append(p)

        return marker

    def make_text_marker(self, marker_id, ns, x, y, text, color, z, y_offset=0.0):
        marker = Marker()
        marker.header.frame_id = "odom"
        marker.header.stamp = self.get_clock().now().to_msg()

        marker.ns = ns
        marker.id = marker_id
        marker.type = Marker.TEXT_VIEW_FACING
        marker.action = Marker.ADD

        marker.pose.orientation.w = 1.0

        marker.pose.position.x = float(x)
        marker.pose.position.y = float(y) + y_offset
        marker.pose.position.z = z

        marker.text = text
        marker.scale.z = 0.30

        marker.color.r = color[0]
        marker.color.g = color[1]
        marker.color.b = color[2]
        marker.color.a = 1.0

        return marker

    def publish_routes(self):
        msg = MarkerArray()
        route_names = ["wp1", "wp2", "wp3", "wp4", "wp5"]

        marker_id = 0

        # 선과 점 표시
        for name in route_names:
            points = self.routes[name]

            msg.markers.append(
                self.make_marker(name, marker_id, Marker.LINE_STRIP, points)
            )
            marker_id += 1

            msg.markers.append(
                self.make_marker(name, marker_id, Marker.POINTS, points)
            )
            marker_id += 1

        # wp 이름 표시: 지정한 5개 위치에만 표시
        for (x, y), wp_name in self.wp_name_labels.items():
            msg.markers.append(
                self.make_text_marker(
                    marker_id=marker_id,
                    ns="wp_name_text",
                    x=x,
                    y=y,
                    text=wp_name,
                    color=self.get_color(wp_name),
                    z=0.75,
                    y_offset=0.35,
                )
            )
            marker_id += 1

        # 모든 point 좌표 표시
        # 같은 좌표가 여러 route에 있어도 한 번만 표시
        shown_coords = set()

        for name in route_names:
            for x, y in self.routes[name]:
                coord_key = (float(x), float(y))

                if coord_key in shown_coords:
                    continue

                shown_coords.add(coord_key)

                msg.markers.append(
                    self.make_text_marker(
                        marker_id=marker_id,
                        ns="coord_text",
                        x=x,
                        y=y,
                        text=f"({x:.1f},{y:.1f})",
                        color=(1.0, 1.0, 1.0),
                        z=0.45,
                        y_offset=-0.35,
                    )
                )
                marker_id += 1

        self.pub.publish(msg)


def main():
    rclpy.init()
    node = WaypointViewer()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()