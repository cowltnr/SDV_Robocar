import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo


class CameraFOVReader(Node):
    def __init__(self, topic_name='/sim/camera/camera_info'):
        super().__init__('camera_fov_reader')

        self.hfov_deg = None

        self.create_subscription(
            CameraInfo,
            topic_name,
            self.callback,
            10
        )

    def callback(self, msg: CameraInfo):
        width = msg.width
        fx = msg.k[0]

        if fx == 0.0:
            return

        hfov = 2 * math.atan(width / (2 * fx))
        self.hfov_deg = math.degrees(hfov)


def get_camera_hfov(topic_name='/sim/camera/camera_info', timeout_sec=5.0):
    rclpy.init()
    node = CameraFOVReader(topic_name)

    try:
        start_time = node.get_clock().now().nanoseconds / 1e9

        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)

            if node.hfov_deg is not None:
                return node.hfov_deg  # HFOV만 반환

            now_time = node.get_clock().now().nanoseconds / 1e9
            if now_time - start_time > timeout_sec:
                raise TimeoutError("CameraInfo not received")

    finally:
        node.destroy_node()
        rclpy.shutdown()