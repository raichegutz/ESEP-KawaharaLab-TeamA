import rclpy
from geometry_msgs.msg import WrenchStamped
from rclpy.node import Node
from sensor_msgs.msg import Image

from message_filters import ApproximateTimeSynchronizer, Subscriber


class SynchronizedPublisher(Node):
    '''
    A ROS2 node that synchronizes the publishing of multiple sensor topics in real-time.
    PLease see recorder_node.py for dataset creation and offline synchronization.
    '''
    def __init__(self):
        super().__init__('synchronized_publisher')
        
        #subscribe to sensor topics
        self.sub_image_left = Subscriber(
            self,
            Image,
            "/gelsight/left/image_raw",
        )
        self.sub_image_right = Subscriber(
            self,
            Image,
            "/gelsight/right/image_raw",
        )

        self.sub_force_left = Subscriber(
            self,
            WrenchStamped,
            "/force_torque/left",
        )
        self.sub_force_right = Subscriber(
            self,
            WrenchStamped,
            "/force_torque/right",
        )

        self.sub_gopro = Subscriber(
            self,
            Image,
            "/gopro/image_raw",
        )
 

        #create synchronized publishers
        self.gelsight_left_sync = self.create_publisher(
            Image,
             "/gelsight/left/image_raw/sync",
            1
        )
        self.gelsight_right_sync = self.create_publisher(
            Image,
            "/gelsight/right/image_raw/sync",
            1
        )

        self.force_left_sync = self.create_publisher(
            WrenchStamped,
            "/force_torque/left/sync",
            10
        )
        self.force_right_sync = self.create_publisher(
            WrenchStamped,
            "/force_torque/right/sync",
            10
        )

        self.gopro_sync = self.create_publisher(
            Image,
            "/gopro/image_raw/sync",
            10
        )

        #initalize time synchronizer
        queue_size = 50
        max_delay = 0.025
        self.time_sync = ApproximateTimeSynchronizer([self.sub_image_left, self.sub_image_right, self.sub_force_left, self.sub_force_right, self.sub_gopro],
                                                     queue_size, max_delay)
        self.time_sync.registerCallback(self.sync_callback)

    def sync_callback(self, image_left, image_right, force_left, force_right, gopro):
        # publish synchronized messages
        times = [
            image_left.header.stamp.sec + image_left.header.stamp.nanosec * 1e-9,
            image_right.header.stamp.sec + image_right.header.stamp.nanosec * 1e-9,
            force_left.header.stamp.sec + force_left.header.stamp.nanosec * 1e-9,
            force_right.header.stamp.sec + force_right.header.stamp.nanosec * 1e-9,
            gopro.header.stamp.sec + gopro.header.stamp.nanosec * 1e-9,
        ]
        spread = max(times) - min(times)
        self.get_logger().info(f"Timestamp spread: {spread*1000:.2f} ms")
        self.gelsight_left_sync.publish(image_left)
        self.gelsight_right_sync.publish(image_right)
        self.force_left_sync.publish(force_left)
        self.force_right_sync.publish(force_right)
        self.gopro_sync.publish(gopro)


def main(args=None):
    rclpy.init(args=args)
    node = SynchronizedPublisher() 

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()
