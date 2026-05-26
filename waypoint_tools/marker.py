import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point


class WaypointViewer(Node):
    def __init__(self):
        super().__init__('waypoint_viewer')
        self.pub = self.create_publisher(MarkerArray, '/waypoint_markers', 10)
        self.timer = self.create_timer(1.0, self.publish_routes)
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

    def make_marker(self, name, marker_id, marker_type, points):
        marker = Marker()
        marker.header.frame_id = "odom"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.ns = name
        marker.id = marker_id
        marker.type = marker_type
        marker.action = Marker.ADD
        marker.pose.orientation.w = 1.0
        marker.color.a = 1.0

        colors = {
            "wp1": (1.0, 0.0, 0.0),
            "wp2": (0.0, 1.0, 0.0),
            "wp3": (0.0, 0.0, 1.0),
        }
        marker.color.r, marker.color.g, marker.color.b = colors[name]

        if marker_type == Marker.POINTS:
            marker.scale.x = 0.35
            marker.scale.y = 0.35
        else:
            marker.scale.x = 0.12

        for x, y in points:
            p = Point()
            p.x = float(x)
            p.y = float(y)
            p.z = 0.1
            marker.points.append(p)

        return marker

    def publish_routes(self):
        msg = MarkerArray()
        route_names = ["wp1", "wp2", "wp3"]

        for i, name in enumerate(route_names):
            points = self.routes[name]
            msg.markers.append(self.make_marker(name, i * 2, Marker.LINE_STRIP, points))
            msg.markers.append(self.make_marker(name, i * 2 + 1, Marker.POINTS, points))

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