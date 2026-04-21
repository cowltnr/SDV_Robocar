import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class LidarLengthReader(Node):
    def __init__(self, topic_name='/sim/scan'):
        super().__init__('lidar_length_reader')

        self.topic_name = topic_name
        self.actual_length = None
        self.expected_length = None

        self.subscription = self.create_subscription(
            LaserScan,
            self.topic_name,
            self.scan_callback,
            10
        )

    def scan_callback(self, msg: LaserScan):
        # 실제 LiDAR 길이: ranges 개수
        self.actual_length = len(msg.ranges)

        # angle 값으로 계산한 예상 길이
        if msg.angle_increment != 0.0:
            self.expected_length = int(
                round((msg.angle_max - msg.angle_min) / msg.angle_increment)
            ) + 1
        else:
            self.expected_length = None


def get_lidar_length(topic_name='/sim/scan', timeout_sec=5.0, return_expected=False):
    """
    ROS2 /sim/scan 토픽을 직접 구독해서 LiDAR length 반환
    - return_expected=False: len(msg.ranges) 반환
    - return_expected=True : angle 기반 계산값 반환
    """
    rclpy.init()
    node = LidarLengthReader(topic_name=topic_name)

    try:
        start_time = node.get_clock().now().nanoseconds / 1e9

        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)

            now_time = node.get_clock().now().nanoseconds / 1e9
            if now_time - start_time > timeout_sec:
                raise TimeoutError(f"No LaserScan message received from {topic_name}")

            if node.actual_length is not None:
                if return_expected:
                    return node.expected_length
                return node.actual_length

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    lidar_len = get_lidar_length('/sim/scan')
    print(f"LIDAR_LEN = {lidar_len}")