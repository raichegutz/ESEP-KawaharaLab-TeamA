import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image


class GoProNode(Node):
    def __init__(self):
        super().__init__('gopro_node')

        self.declare_parameter('video_device', '/dev/video0')
        self.declare_parameter('frame_id', 'gopro_frame')
        self.declare_parameter('width', 1280)
        self.declare_parameter('height', 720)
        self.declare_parameter('fps', 30.0)

        self.video_device = self.get_parameter('video_device').value
        self.frame_id = self.get_parameter('frame_id').value
        self.width = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)
        self.fps = float(self.get_parameter('fps').value)

        self.bridge = CvBridge()
        self.publisher = self.create_publisher(Image, '/gopro/image_raw', 10)

        self.cap = cv2.VideoCapture(self.video_device, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        if not self.cap.isOpened():
            self.get_logger().error(
                f'Failed to open GoPro video device: {self.video_device}'
            )
            self.cap = None
            return

        timer_period = 1.0 / self.fps
        self.timer = self.create_timer(timer_period, self.publish_frame)
        self.get_logger().info(
            f'GoPro node started on {self.video_device}: '
            f'{self.width}x{self.height}@{self.fps}'
        )

    def publish_frame(self):
        if self.cap is None:
            return

        ok, frame = self.cap.read()
        if not ok:
            self.get_logger().warn('Failed to read frame from GoPro.')
            return

        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        self.publisher.publish(msg)

    def destroy_node(self):
        if getattr(self, 'cap', None) is not None:
            self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = GoProNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
