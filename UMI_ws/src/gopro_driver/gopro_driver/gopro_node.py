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
        self.declare_parameter('pixel_format', 'MJPG')

        self.video_device = self.get_parameter('video_device').value
        self.frame_id = self.get_parameter('frame_id').value
        self.width = int(self.get_parameter('width').value)
        self.height = int(self.get_parameter('height').value)
        self.fps = float(self.get_parameter('fps').value)
        self.pixel_format = str(self.get_parameter('pixel_format').value).strip().upper()

        self.bridge = CvBridge()
        self.publisher = self.create_publisher(Image, '/gopro/image_raw', 10)

        self.cap = cv2.VideoCapture(self.video_device, cv2.CAP_V4L2)
        '''
        if self.pixel_format:
            if len(self.pixel_format) != 4:
                self.get_logger().warn(
                    f'Expected a 4-character pixel_format, got {self.pixel_format!r}.'
                )
            fourcc = cv2.VideoWriter_fourcc(*self.pixel_format[:4])
            self.cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        '''
        self.cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)
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
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        actual_fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
        actual_fourcc_str = ''.join(
            chr((actual_fourcc >> 8 * i) & 0xFF) for i in range(4)
        )
        self.get_logger().info(
            f'GoPro node started on {self.video_device}: '
            f'requested {self.width}x{self.height}@{self.fps} {self.pixel_format}; '
            f'actual {actual_width}x{actual_height}@{actual_fps:.2f} {actual_fourcc_str}'
        )

    def publish_frame(self):
        if self.cap is None:
            return

        #receive split second frame from camera and stamp
        ok = self.cap.grab()
        rx_stamp = self.get_clock().now().to_msg()
        
        if not ok:
            self.get_logger().warn('Failed to read frame from GoPro.')
            return

        #decode frame after stamping
        ok, frame = self.cap.retrieve()
        if not ok:
            return
        
        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = rx_stamp
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
